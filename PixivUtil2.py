#!/usr/bin/env python
# -*- coding: utf-8 -*-
# flake8: noqa:E501,E128,E127
import codecs
import datetime
import gc
import getpass
import os
import re
import subprocess
import sys
import time
import traceback
from optparse import OptionParser

from bs4 import BeautifulSoup

import datetime_z
import PixivArtistHandler
import PixivBatchHandler
import PixivBrowserFactory
import PixivConfig
import PixivConstant
import PixivDownloadHandler
import PixivHelper
import PixivImageHandler
import PixivModelFanbox
import PixivTagsHandler
from PixivBookmark import PixivBookmark, PixivNewIllustBookmark
from PixivDBManager import PixivDBManager
from PixivException import PixivException
from PixivGroup import PixivGroup
from PixivListItem import PixivListItem
from PixivTags import PixivTags

DEBUG_SKIP_PROCESS_IMAGE = False
DEBUG_SKIP_DOWNLOAD_IMAGE = False

if os.name == 'nt':
    # patch getpass.getpass() for windows to show '*'
    def win_getpass_with_mask(prompt='Password: ', stream=None):
        """Prompt for password with echo off, using Windows getch()."""
        if sys.stdin is not sys.__stdin__:
            return getpass.fallback_getpass(prompt, stream)
        import msvcrt
        for c in prompt:
            msvcrt.putch(c.encode())
        pw = ""
        while 1:
            c = msvcrt.getch().decode()
            if c == '\r' or c == '\n':
                break
            if c == '\003':
                raise KeyboardInterrupt
            if c == '\b':
                pw = pw[:-1]
                print("\b \b", end="")
            else:
                pw = pw + c
                print("*", end="")
        msvcrt.putch('\r'.encode())
        msvcrt.putch('\n'.encode())
        return pw

    getpass.getpass = win_getpass_with_mask

script_path = PixivHelper.module_path()

np_is_valid = False
np = 0
op = ''
ERROR_CODE = 0
UTF8_FS = None

__config__ = PixivConfig.PixivConfig()
configfile = "config.ini"
__dbManager__ = None
__br__ = None
__blacklistTags = list()
__suppressTags = list()
__log__ = PixivHelper.get_logger()
__errorList = list()
__blacklistMembers = list()
__blacklistTitles = list()
__valid_options = ()

start_iv = False
dfilename = ""

# http://www.pixiv.net/member_illust.php?mode=medium&illust_id=18830248
__re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
__re_manga_page = re.compile(r'(\d+(_big)?_p\d+)')


# -T04------For download file
def download_image(url, filename, referer, overwrite, max_retry, backup_old_file=False, image=None, page=None):
    return PixivDownloadHandler.download_image(sys.modules[__name__],
                                               url,
                                               filename,
                                               referer,
                                               overwrite,
                                               max_retry,
                                               backup_old_file=backup_old_file,
                                               image=image,
                                               page=page)


#  Start of main processing logic
def process_list(list_file_name=None, tags=None):
    global ERROR_CODE

    result = None
    try:
        # Getting the list
        if __config__.processFromDb:
            PixivHelper.print_and_log('info', 'Processing from database.')
            if __config__.dayLastUpdated == 0:
                result = __dbManager__.selectAllMember()
            else:
                print('Select only last', __config__.dayLastUpdated, 'days.')
                result = __dbManager__.selectMembersByLastDownloadDate(__config__.dayLastUpdated)
        else:
            PixivHelper.print_and_log('info', 'Processing from list file: {0}'.format(list_file_name))
            result = PixivListItem.parseList(list_file_name, __config__.rootDirectory)

        if os.path.exists("ignore_list.txt"):
            PixivHelper.print_and_log('info', 'Processing ignore list for member: {0}'.format("ignore_list.txt"))
            ignore_list = PixivListItem.parseList("ignore_list.txt", __config__.rootDirectory)
            for ignore in ignore_list:
                for item in result:
                    if item.memberId == ignore.memberId:
                        result.remove(item)
                        break

        PixivHelper.print_and_log('info', f"Found {len(result)} items.")
        current_member = 1
        for item in result:
            retry_count = 0
            while True:
                try:
                    prefix = "[{0} of {1}] ".format(current_member, len(result))
                    process_member(item.memberId, item.path, tags=tags, title_prefix=prefix)
                    current_member = current_member + 1
                    break
                except KeyboardInterrupt:
                    raise
                except BaseException:
                    if retry_count > __config__.retry:
                        PixivHelper.print_and_log('error', 'Giving up member_id: ' + str(item.memberId))
                        break
                    retry_count = retry_count + 1
                    print('Something wrong, retrying after 2 second (', retry_count, ')')
                    time.sleep(2)

            __br__.clear_history()
            print('done.')
    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        ERROR_CODE = getattr(ex, 'errorCode', -1)
        PixivHelper.print_and_log('error', 'Error at process_list(): {0}'.format(sys.exc_info()))
        print('Failed')
        raise


def process_member(member_id, user_dir='', page=1, end_page=0, bookmark=False, tags=None, title_prefix=""):
    PixivArtistHandler.process_member(sys.modules[__name__],
                                      member_id,
                                      user_dir=user_dir,
                                      page=page,
                                      end_page=end_page,
                                      bookmark=bookmark,
                                      tags=tags,
                                      title_prefix=title_prefix)


def process_image(artist=None, image_id=None, user_dir='', bookmark=False, search_tags='', title_prefix="", bookmark_count=-1, image_response_count=-1):
    return PixivImageHandler.process_image(sys.modules[__name__],
                                           artist=artist,
                                           image_id=image_id,
                                           user_dir=user_dir,
                                           bookmark=bookmark,
                                           search_tags=search_tags,
                                           title_prefix=title_prefix,
                                           bookmark_count=bookmark_count,
                                           image_response_count=image_response_count)


def process_tags(tags, page=1, end_page=0, wild_card=True, title_caption=False,
               start_date=None, end_date=None, use_tags_as_dir=False, member_id=None,
               bookmark_count=None, oldest_first=False, type_mode=None):
    PixivTagsHandler.process_tags(sys.modules[__name__],
                                  tags,
                                  page=page,
                                  end_page=end_page,
                                  wild_card=wild_card,
                                  title_caption=title_caption,
                                  start_date=start_date,
                                  end_date=end_date,
                                  use_tags_as_dir=use_tags_as_dir,
                                  member_id=member_id,
                                  bookmark_count=bookmark_count,
                                  oldest_first=oldest_first,
                                  type_mode=type_mode)


def process_tags_list(filename, page=1, end_page=0, wild_card=True,
                      oldest_first=False, bookmark_count=None,
                      start_date=None, end_date=None):
    global ERROR_CODE

    try:
        print("Reading:", filename)
        tags = PixivTags.parseTagsList(filename)
        for tag in tags:
            process_tags(tag,
                         page=page,
                         end_page=end_page,
                         wild_card=wild_card,
                         use_tags_as_dir=__config__.useTagsAsDir,
                         oldest_first=oldest_first,
                         bookmark_count=bookmark_count,
                         start_date=start_date,
                         end_date=end_date)
    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        ERROR_CODE = getattr(ex, 'errorCode', -1)
        PixivHelper.print_and_log('error', 'Error at process_tags_list(): {0}'.format(sys.exc_info()))
        raise


def process_image_bookmark(hide='n', start_page=1, end_page=0, tag=None, sorting=None):
    global np_is_valid
    global np
    try:
        print("Importing image bookmarks...")
        totalList = list()
        image_count = 1

        if hide == 'n':
            totalList.extend(get_image_bookmark(False, start_page, end_page, tag, sorting))
        elif hide == 'y':
            # public and private image bookmarks
            totalList.extend(get_image_bookmark(False, start_page, end_page, tag, sorting))
            totalList.extend(get_image_bookmark(True, start_page, end_page, tag, sorting))
        else:
            totalList.extend(get_image_bookmark(True, start_page, end_page, tag, sorting))

        PixivHelper.print_and_log('info', "Found " + str(len(totalList)) + " image(s).")
        for item in totalList:
            print("Image #" + str(image_count))
            result = process_image(artist=None, image_id=item, search_tags=tag)
            image_count = image_count + 1
            PixivHelper.wait(result, __config__)

        print("Done.\n")
    except KeyboardInterrupt:
        raise
    except BaseException:
        PixivHelper.print_and_log('error', 'Error at process_image_bookmark(): {0}'.format(sys.exc_info()))
        raise


def get_image_bookmark(hide, start_page=1, end_page=0, tag=None, sorting=None):
    """Get user's image bookmark"""
    total_list = list()
    i = start_page
    offset = 0
    limit = 48
    member_id = __br__._myId

    while True:
        if end_page != 0 and i > end_page:
            print("Page Limit reached: " + str(end_page))
            break

        # https://www.pixiv.net/ajax/user/189816/illusts/bookmarks?tag=&offset=0&limit=48&rest=show
        show = "show"
        if hide:
            show = "hide"

        # # Implement #468 default is desc, only for your own bookmark.
        # not available in current api
        # if sorting in ('asc', 'date_d', 'date'):
        #     url = url + "&order=" + sorting

        if tag is not None and len(tag) > 0:
            tag = PixivHelper.encode_tags(tag)
        offset = limit * (i - 1)
        url = f"https://www.pixiv.net/ajax/user/{member_id}/illusts/bookmarks?tag={tag}&offset={offset}&limit={limit}&rest={show}"

        PixivHelper.print_and_log('info', f"Importing user's bookmarked image from page {i}")
        PixivHelper.print_and_log('info', f"Source URL: {url}")

        page = __br__.open(url)
        page_str = page.read().decode('utf8')
        page.close()

        bookmarks = PixivBookmark.parseImageBookmark(page_str)
        total_list.extend(bookmarks)
        if len(bookmarks) == 0:
            print("No more images.")
            break
        else:
            print(" found " + str(len(bookmarks)) + " images.")

        i = i + 1

        # Issue#569
        PixivHelper.wait(config=__config__)

    return total_list


def get_bookmarks(hide, start_page=1, end_page=0, member_id=None):
    """Get User's bookmarked artists """
    total_list = list()
    i = start_page
    limit = 24
    offset = 0
    is_json = False

    while True:
        if end_page != 0 and i > end_page:
            print('Limit reached')
            break
        PixivHelper.print_and_log('info', f'Exporting page {i}')
        if member_id:
            is_json = True
            offset = limit * (i - 1)
            url = f'https://www.pixiv.net/ajax/user/{member_id}/following?offset={offset}&limit={limit}'
        else:
            url = f'https://www.pixiv.net/bookmark.php?type=user&p={i}'
        if hide:
            url = url + "&rest=hide"
        else:
            url = url + "&rest=show"

        PixivHelper.print_and_log('info', f"Source URL: {url}")

        page = __br__.open_with_retry(url)
        page_str = page.read().decode('utf8')
        page.close()

        bookmarks = PixivBookmark.parseBookmark(page_str,
                                                root_directory=__config__.rootDirectory,
                                                db_path=__config__.dbPath,
                                                locale=__br__._locale,
                                                is_json=is_json)

        if len(bookmarks) == 0:
            print('No more data')
            break
        total_list.extend(bookmarks)
        i = i + 1
        print(str(len(bookmarks)), 'items')
        PixivHelper.wait(config=__config__)
    return total_list


def process_bookmark(hide='n', start_page=1, end_page=0):
    try:
        total_list = list()
        print(f"My Member Id = {__br__._myId}")
        if hide != 'o':
            print("Importing Bookmarks...")
            total_list.extend(get_bookmarks(False, start_page, end_page, __br__._myId))
        if hide != 'n':
            print("Importing Private Bookmarks...")
            total_list.extend(get_bookmarks(True, start_page, end_page, __br__._myId))
        print(f"Result: {str(len(total_list))} items.")
        i = 0
        current_member = 1
        for item in total_list:
            print("%d/%d\t%f %%" % (i, len(total_list), 100.0 * i / float(len(total_list))))
            i += 1
            prefix = "[{0} of {1}]".format(current_member, len(total_list))
            process_member(item.memberId, item.path, title_prefix=prefix)
            current_member = current_member + 1

        if len(total_list) > 0:
            print("%d/%d\t%f %%" % (i, len(total_list), 100.0 * i / float(len(total_list))))
        else:
            print("Cannot find any followed member.")
    except KeyboardInterrupt:
        raise
    except BaseException:
        PixivHelper.print_and_log('error', 'Error at process_bookmark(): {0}'.format(sys.exc_info()))
        raise


def export_bookmark(filename, hide='n', start_page=1, end_page=0, member_id=None):
    try:
        total_list = list()
        if hide != 'o':
            print("Importing Bookmarks...")
            total_list.extend(get_bookmarks(False, start_page, end_page, member_id))
        if hide != 'n':
            print("Importing Private Bookmarks...")
            total_list.extend(get_bookmarks(True, start_page, end_page, member_id))
        print("Result: ", str(len(total_list)), "items.")
        PixivBookmark.exportList(total_list, filename)
    except KeyboardInterrupt:
        raise
    except BaseException:
        PixivHelper.print_and_log('error', 'Error at export_bookmark(): {0}'.format(sys.exc_info()))
        raise


def process_new_illust_from_bookmark(page_num=1, end_page_num=0):
    try:
        print("Processing New Illust from bookmark")
        i = page_num
        image_count = 1
        flag = True
        while flag:
            print("Page #" + str(i))
            url = 'https://www.pixiv.net/bookmark_new_illust.php?p=' + str(i)
            if __config__.r18mode:
                url = 'https://www.pixiv.net/bookmark_new_illust_r18.php?p=' + str(i)

            PixivHelper.print_and_log('info', "Source URL: " + url)
            page = __br__.open(url)
            parsed_page = BeautifulSoup(page.read().decode("utf-8"), features="html5lib")
            pb = PixivNewIllustBookmark(parsed_page)
            if not pb.haveImages:
                print("No images!")
                break

            for image_id in pb.imageList:
                print("Image #" + str(image_count))
                result = process_image(artist=None, image_id=int(image_id))
                image_count = image_count + 1

                if result == PixivConstant.PIXIVUTIL_SKIP_OLDER:
                    flag = False
                    break

                PixivHelper.wait(result, __config__)
            i = i + 1

            page.close()
            parsed_page.decompose()
            del parsed_page

            # Non premium is only limited to 100 page
            # Premium user might be limited to 5000, refer to issue #112
            if (end_page_num != 0 and i > end_page_num) or i > 5000 or pb.isLastPage:
                print("Limit or last page reached.")
                flag = False

        print("Done.")
    except KeyboardInterrupt:
        raise
    except BaseException:
        PixivHelper.print_and_log('error', 'Error at process_new_illust_from_bookmark(): {0}'.format(sys.exc_info()))
        raise


def process_from_group(group_id, limit=0, process_external=True):
    try:
        print("Download by Group Id")
        if limit != 0:
            print("Limit: {0}".format(limit))
        if process_external:
            print("Include External Image: {0}".format(process_external))

        max_id = 0
        image_count = 0
        flag = True
        while flag:
            url = "https://www.pixiv.net/group/images.php?format=json&max_id={0}&id={1}".format(max_id, group_id)
            PixivHelper.print_and_log('info', "Getting images from: {0}".format(url))
            json_response = __br__.open(url)
            group_data = PixivGroup(json_response)
            json_response.close()
            max_id = group_data.maxId
            if group_data.imageList is not None and len(group_data.imageList) > 0:
                for image in group_data.imageList:
                    if image_count > limit and limit != 0:
                        flag = False
                        break
                    print("Image #{0}".format(image_count))
                    print("ImageId: {0}".format(image))
                    result = process_image(image_id=image)
                    image_count = image_count + 1
                    PixivHelper.wait(result, __config__)

            if process_external and group_data.externalImageList is not None and len(group_data.externalImageList) > 0:
                for image_data in group_data.externalImageList:
                    if image_count > limit and limit != 0:
                        flag = False
                        break
                    print("Image #{0}".format(image_count))
                    print("Member Id   : {0}".format(image_data.artist.artistId))
                    PixivHelper.safePrint("Member Name  : " + image_data.artist.artistName)
                    print("Member Token : {0}".format(image_data.artist.artistToken))
                    print("Image Url   : {0}".format(image_data.imageUrls[0]))

                    filename = PixivHelper.make_filename(__config__.filenameFormat,
                                                        imageInfo=image_data,
                                                        tagsSeparator=__config__.tagsSeparator,
                                                        tagsLimit=__config__.tagsLimit,
                                                        fileUrl=image_data.imageUrls[0],
                                                        useTranslatedTag=__config__.useTranslatedTag,
                                                        tagTranslationLocale=__config__.tagTranslationLocale)
                    filename = PixivHelper.sanitize_filename(filename, __config__.rootDirectory)
                    PixivHelper.safePrint("Filename  : " + filename)
                    (result, filename) = download_image(image_data.imageUrls[0], filename, url, __config__.overwrite, __config__.retry, __config__.backupOldFile)
                    PixivHelper.get_logger().debug("Download %s result: %s", filename, result)
                    if __config__.setLastModified and filename is not None and os.path.isfile(filename):
                        ts = time.mktime(image_data.worksDateDateTime.timetuple())
                        os.utime(filename, (ts, ts))

                    image_count = image_count + 1

            if (group_data.imageList is None or len(group_data.imageList) == 0) and \
               (group_data.externalImageList is None or len(group_data.externalImageList) == 0):
                flag = False
            print("")

    except BaseException:
        PixivHelper.print_and_log('error', 'Error at process_from_group(): {0}'.format(sys.exc_info()))
        raise


def header():
    print('PixivDownloader2 version', PixivConstant.PIXIVUTIL_VERSION)
    print(PixivConstant.PIXIVUTIL_LINK)
    print('Donate at', PixivConstant.PIXIVUTIL_DONATE)


def get_start_and_end_number_from_args(args, offset=0, start_only=False):
    global np_is_valid
    global np
    page_num = 1
    if len(args) > 0 + offset:
        try:
            page_num = int(args[0 + offset])
            print("Start Page =", str(page_num))
        except BaseException:
            print("Invalid page number:", args[0 + offset])
            raise

    end_page_num = 0
    if np_is_valid:
        end_page_num = np
    else:
        end_page_num = __config__.numberOfPage

    if not start_only:
        if len(args) > 1 + offset:
            try:
                end_page_num = int(args[1 + offset])
                if page_num > end_page_num and end_page_num != 0:
                    print("page_num is bigger than end_page_num, assuming as page count.")
                    end_page_num = page_num + end_page_num
                print("End Page =", str(end_page_num))
            except BaseException:
                print("Invalid end page number:", args[1 + offset])
                raise
    return page_num, end_page_num


def menu():
    set_console_title()
    header()
    print('1. Download by member_id')
    print('2. Download by image_id')
    print('3. Download by tags')
    print('4. Download from list')
    print('5. Download from bookmarked artists (/bookmark.php?type=user)')
    print('6. Download from bookmarked images (/bookmark.php)')
    print('7. Download from tags list')
    print('8. Download new illust from bookmarked members (/bookmark_new_illust.php)')
    print('9. Download by Title/Caption')
    print('10. Download by Tag and Member Id')
    print('11. Download Member Bookmark (/bookmark.php?id=)')
    print('12. Download by Group Id')
    print('------------------------')
    print('f1. Download from supporting list (FANBOX)')
    print('f2. Download by artist/creator id (FANBOX)')
    print('f3. Download by post id (FANBOX)')
    print('f4. Download from following list (FANBOX)')
    print('------------------------')
    print('b. Batch Download from batch_job.json (experimental)')
    print('------------------------')
    print('d. Manage database')
    print('e. Export online bookmark')
    print('m. Export online user bookmark')
    print('i. Import list file')
    print('r. Reload config.ini')
    print('p. Print config.ini')
    print('x. Exit')

    sel = input('Input: ').rstrip("\r")
    return sel


def menu_download_by_member_id(opisvalid, args):
    __log__.info('Member id mode.')
    current_member = 1
    page = 1
    end_page = 0

    if opisvalid and len(args) > 0:
        for member_id in args:
            try:
                prefix = "[{0} of {1}] ".format(current_member, len(args))
                test_id = int(member_id)
                process_member(test_id, title_prefix=prefix)
                current_member = current_member + 1
            except BaseException:
                PixivHelper.print_and_log('error', "Member ID: {0} is not valid".format(member_id))
                global ERROR_CODE
                ERROR_CODE = -1
                continue
    else:
        member_ids = input('Member ids: ').rstrip("\r")
        (page, end_page) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)

        member_ids = PixivHelper.get_ids_from_csv(member_ids, sep=" ")
        PixivHelper.print_and_log('info', "Member IDs: {0}".format(member_ids))
        for member_id in member_ids:
            try:
                prefix = "[{0} of {1}] ".format(current_member, len(member_ids))
                process_member(member_id, page=page, end_page=end_page, title_prefix=prefix)
                current_member = current_member + 1
            except PixivException as ex:
                print(ex)


def menu_download_by_member_bookmark(opisvalid, args):
    __log__.info('Member Bookmark mode.')
    page = 1
    end_page = 0
    i = 0
    current_member = 1
    if opisvalid and len(args) > 0:
        valid_ids = list()
        for member_id in args:
            print("%d/%d\t%f %%" % (i, len(args), 100.0 * i / float(len(args))))
            i += 1
            try:
                test_id = int(member_id)
                valid_ids.append(test_id)
            except BaseException:
                PixivHelper.print_and_log('error', "Member ID: {0} is not valid".format(member_id))
                global ERROR_CODE
                ERROR_CODE = -1
                continue
        if __br__._myId in valid_ids:
            PixivHelper.print_and_log('error', "Member ID: {0} is your own id, use option 6 instead.".format(__br__._myId))
        for mid in valid_ids:
            prefix = "[{0} of {1}] ".format(current_member, len(valid_ids))
            process_member(mid, bookmark=True, tags=None, title_prefix=prefix)
            current_member = current_member + 1

    else:
        member_id = input('Member id: ').rstrip("\r")
        tags = input('Filter Tags: ').rstrip("\r")
        (page, end_page) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)
        if __br__._myId == int(member_id):
            PixivHelper.print_and_log('error', "Member ID: {0} is your own id, use option 6 instead.".format(member_id))
        else:
            process_member(member_id.strip(), page=page, end_page=end_page, bookmark=True, tags=tags)


def menu_download_by_image_id(opisvalid, args):
    __log__.info('Image id mode.')
    if opisvalid and len(args) > 0:
        for image_id in args:
            try:
                test_id = int(image_id)
                process_image(None, test_id)
            except BaseException:
                PixivHelper.print_and_log('error', "Image ID: {0} is not valid".format(image_id))
                global ERROR_CODE
                ERROR_CODE = -1
                continue
    else:
        image_ids = input('Image ids: ').rstrip("\r")
        image_ids = PixivHelper.get_ids_from_csv(image_ids, sep=" ")
        for image_id in image_ids:
            process_image(None, int(image_id))


def menu_download_by_tags(opisvalid, args):
    __log__.info('tags mode.')
    page = 1
    end_page = 0
    start_date = None
    end_date = None
    bookmark_count = None
    oldest_first = False
    wildcard = True
    type_mode = "a"

    if opisvalid and len(args) > 0:
        wildcard = args[0]
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        (page, end_page) = get_start_and_end_number_from_args(args, 1)
        tags = " ".join(args[3:])
    else:
        tags = input('Tags: ')
        bookmark_count = input('Bookmark Count: ').rstrip("\r") or None
        wildcard = input('Use Partial Match (s_tag) [y/n]: ').rstrip("\r") or 'n'
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        oldest_first = input('Oldest first[y/n]: ').rstrip("\r") or 'n'
        if oldest_first.lower() == 'y':
            oldest_first = True
        else:
            oldest_first = False

        (page, end_page) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)
        (start_date, end_date) = PixivHelper.get_start_and_end_date()

        while True:
            type_mode = input("Search type [a-all|i-Illustration and Ugoira|m-manga: ").rstrip("\r") or "a"
            if type_mode in {'a', 'i', 'm'}:
                break
            else:
                print("Valid values are 'a', 'i', or 'm'.")

    if bookmark_count is not None:
        bookmark_count = bookmark_count.strip()
        if len(bookmark_count) > 0:
            bookmark_count = int(bookmark_count)

    process_tags(tags.strip(),
                 page, end_page,
                 wildcard,
                 start_date=start_date,
                 end_date=end_date,
                 use_tags_as_dir=__config__.useTagsAsDir,
                 bookmark_count=bookmark_count,
                 oldest_first=oldest_first,
                 type_mode=type_mode)


def menu_download_by_title_caption(opisvalid, args):
    __log__.info('Title/Caption mode.')
    page = 1
    end_page = 0
    start_date = None
    end_date = None
    if opisvalid and len(args) > 0:
        (page, end_page) = get_start_and_end_number_from_args(args)
        tags = " ".join(args[2:])
    else:
        tags = input('Title/Caption: ')
        (page, end_page) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)
        (start_date, end_date) = PixivHelper.get_start_and_end_date()

    process_tags(tags.strip(),
                 page,
                 end_page,
                 wild_card=False,
                 title_caption=True,
                 start_date=start_date,
                 end_date=end_date,
                 use_tags_as_dir=__config__.useTagsAsDir)


def menu_download_by_tag_and_member_id(opisvalid, args):
    __log__.info('Tag and MemberId mode.')
    member_id = 0
    tags = None
    page = 1
    end_page = 0

    if opisvalid and len(args) >= 2:
        try:
            member_id = int(args[0])
        except BaseException:
            PixivHelper.print_and_log('error', "Member ID: {0} is not valid".format(member_id))
            global ERROR_CODE
            ERROR_CODE = -1
            return

        (page, end_page) = get_start_and_end_number_from_args(args, 1)
        tags = " ".join(args[3:])
        PixivHelper.safePrint("Looking tags: " + tags + " from memberId: " + str(member_id))
    else:
        member_id = input('Member Id: ').rstrip("\r")
        tags = input('Tag      : ')
        (page, end_page) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)

    process_tags(tags.strip(),
                 page,
                 end_page,
                 member_id=int(member_id),
                 use_tags_as_dir=__config__.useTagsAsDir)


def menu_download_from_list(opisvalid, args):
    __log__.info('Batch mode.')
    global op
    global __config__

    list_file_name = __config__.downloadListDirectory + os.sep + 'list.txt'
    tags = None
    if opisvalid and op == '4' and len(args) > 0:
        test_file_name = __config__.downloadListDirectory + os.sep + args[0]
        if os.path.exists(test_file_name):
            list_file_name = test_file_name
        if len(args) > 1:
            tags = args[1]
    else:
        test_tags = input('Tag : ')
        if len(test_tags) > 0:
            tags = test_tags

    # if tags is not None and len(tags) > 0:
    #     PixivHelper.safePrint(u"Processing member id from {0} for tags: {1}".format(list_file_name, tags))
    # else:
    #     PixivHelper.safePrint("Processing member id from {0}".format(list_file_name))

    process_list(list_file_name, tags)


def menu_download_from_online_user_bookmark(opisvalid, args):
    __log__.info('User Bookmarked Artist mode.')
    start_page = 1
    end_page = 0
    hide = 'n'
    if opisvalid:
        if len(args) > 0:
            arg = args[0].lower()
            if arg == 'y' or arg == 'n' or arg == 'o':
                hide = arg
            else:
                print("Invalid args: ", args)
                return
            (start_page, end_page) = get_start_and_end_number_from_args(args, offset=1)
    else:
        arg = input("Include Private bookmarks [y/n/o]: ").rstrip("\r") or 'n'
        arg = arg.lower()
        if arg == 'y' or arg == 'n' or arg == 'o':
            hide = arg
        else:
            print("Invalid args: ", arg)
            return
        (start_page, end_page) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)
    process_bookmark(hide, start_page, end_page)


def menu_download_from_online_image_bookmark(opisvalid, args):
    __log__.info("User's Image Bookmark mode.")
    start_page = 1
    end_page = 0
    hide = 'n'
    tag = ''
    sorting = 'desc'

    if opisvalid and len(args) > 0:
        hide = args[0].lower()
        if hide not in ('y', 'n', 'o'):
            print("Invalid args: ", args)
            return
        (start_page, end_page) = get_start_and_end_number_from_args(args, offset=1)
        if len(args) > 3:
            tag = args[3]
        if len(args) > 4:
            sorting = args[4].lower()
            if sorting not in ('asc', 'desc', 'date', 'date_d'):
                print("Invalid sorting order: ", sorting)
                return
    else:
        hide = input("Include Private bookmarks [y/n/o]: ").rstrip("\r") or 'n'
        hide = hide.lower()
        if hide not in ('y', 'n', 'o'):
            print("Invalid args: ", hide)
            return
        tag = input("Tag (press enter for all images): ").rstrip("\r") or ''
        (start_page, end_page) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)
        # sorting = input("Sort Order [asc/desc/date/date_d]: ").rstrip("\r") or 'desc'
        # sorting = sorting.lower()
        # if sorting not in ('asc', 'desc', 'date', 'date_d'):
        #     print("Invalid sorting order: ", sorting)
        #     return

    process_image_bookmark(hide, start_page, end_page, tag, sorting)


def menu_download_from_tags_list(opisvalid, args):
    __log__.info('Taglist mode.')
    page = 1
    end_page = 0
    oldest_first = False
    wildcard = True
    bookmark_count = None
    start_date = None
    end_date = None

    if opisvalid and len(args) > 0:
        filename = args[0]
        (page, end_page) = get_start_and_end_number_from_args(args, offset=1)
    else:
        filename = input("Tags list filename [tags.txt]: ").rstrip("\r") or './tags.txt'
        wildcard = input('Use Wildcard[y/n]: ').rstrip("\r") or 'n'
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        oldest_first = input('Oldest first[y/n]: ').rstrip("\r") or 'n'
        if oldest_first.lower() == 'y':
            oldest_first = True
        else:
            oldest_first = False
        bookmark_count = input('Bookmark Count: ').rstrip("\r") or None
        (page, end_page) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)
        (start_date, end_date) = PixivHelper.get_start_and_end_date()
    if bookmark_count is not None:
        bookmark_count = int(bookmark_count)

    process_tags_list(filename, page, end_page, wild_card=wildcard, oldest_first=oldest_first,
                      bookmark_count=bookmark_count, start_date=start_date, end_date=end_date)


def menu_download_new_illust_from_bookmark(opisvalid, args):
    __log__.info('New Illust from Bookmark mode.')

    if opisvalid:
        (page_num, end_page_num) = get_start_and_end_number_from_args(args, offset=0)
    else:
        (page_num, end_page_num) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)

    process_new_illust_from_bookmark(page_num, end_page_num)


def menu_download_by_group_id(opisvalid, args):
    __log__.info('Group mode.')
    process_external = False
    limit = 0

    if opisvalid and len(args) > 0:
        group_id = args[0]
        limit = int(args[1])
        if args[2].lower() == 'y':
            process_external = True
    else:
        group_id = input("Group Id: ").rstrip("\r")
        limit = int(input("Limit: ").rstrip("\r"))
        arg = input("Process External Image [y/n]: ").rstrip("\r") or 'n'
        arg = arg.lower()
        if arg == 'y':
            process_external = True

    process_from_group(group_id, limit, process_external)


def menu_export_online_bookmark(opisvalid, args):
    __log__.info('Export Bookmark mode.')
    hide = "y"  # y|n|o
    filename = "export.txt"

    if opisvalid and len(args) > 0:
        arg = args[0]
        if len(args) > 1:
            filename = args[1]
    else:
        filename = input("Filename: ").rstrip("\r")
        arg = input("Include Private bookmarks [y/n/o]: ").rstrip("\r") or 'n'
        arg = arg.lower()

    if arg == 'y' or arg == 'n' or arg == 'o':
        hide = arg
    else:
        print("Invalid args: ", arg)

    export_bookmark(filename, hide)


def menu_export_online_user_bookmark(opisvalid, args):
    __log__.info('Export Bookmark mode.')
    member_id = ''
    filename = "export-user.txt"

    if opisvalid and len(args) > 0:
        arg = args[0]
        if len(args) > 1:
            filename = args[1]
        else:
            filename = "export-user-{0}.txt".format(arg)
    else:
        filename = input("Filename: ").rstrip("\r") or filename
        arg = input("Member Id: ").rstrip("\r") or ''
        arg = arg.lower()

    if arg.isdigit():
        member_id = arg
    else:
        print("Invalid args: ", arg)

    export_bookmark(filename, 'n', 1, 0, member_id)


def menu_fanbox_download_from_list(op_is_valid, via, args):
    via_type = ""
    if via == PixivModelFanbox.FanboxArtist.SUPPORTING:
        via_type = "supporting"
    elif via == PixivModelFanbox.FanboxArtist.FOLLOWING:
        via_type = "following"

    __log__.info(f'Download FANBOX {via_type.capitalize()} list mode.')
    end_page = 0

    if op_is_valid and len(args) > 0:
        end_page = int(args[0])
    else:
        end_page = input("Max Page = ").rstrip("\r") or 0
        end_page = int(end_page)

    ids = __br__.fanboxGetArtistList(via)
    if len(ids) == 0:
        PixivHelper.print_and_log("info", f"No artist in {via_type} list!")
        return
    PixivHelper.print_and_log("info", f"Found {len(ids)} artist(s) in {via_type} list")
    PixivHelper.print_and_log(None, f"{ids}")

    for index, id in enumerate(ids, start=1):
        # Issue #567
        try:
            processFanboxArtistById(id, end_page, f"{index} of {len(ids)}")
        except PixivException as pex:
            PixivHelper.print_and_log("error", f"Error processing FANBOX Artist in {via_type} list: {id} ==> {pex.message}")


def menu_fanbox_download_by_post_id(op_is_valid, args):
    __log__.info('Download FANBOX by post id mode.')
    if op_is_valid and len(args) > 0:
        post_ids = args
    else:
        post_ids = input("Post ids = ").rstrip("\r") or 0

    post_ids = PixivHelper.get_ids_from_csv(post_ids, sep=" ")
    for post_id in post_ids:
        post_id = int(post_id)
        post = __br__.fanboxGetPostById(post_id)
        try:
            processFanboxPost(post, post.parent)
        except PixivException as pex:
            PixivHelper.print_and_log("error", "Error processing FANBOX post: {0} ==> {1}".format(post_id, pex.message))
        del post


def processFanboxArtistById(id, end_page, title_prefix=""):
    __config__.loadConfig(path=configfile)
    artist = __br__.fanboxGetArtistById(id)
    current_page = 1
    next_url = None
    image_count = 1
    while (True):
        PixivHelper.print_and_log("info", "Processing {0}, page {1}".format(artist, current_page))
        set_console_title(f"{title_prefix}Artist {artist}, page {current_page}")
        try:
            posts = __br__.fanboxGetPostsFromArtist(artist, next_url)
        except PixivException as pex:
            print(pex)
            break

        for post in posts:
            print("#{0}".format(image_count))
            post.printPost()

            # images
            if post.type in PixivModelFanbox.FanboxPost._supportedType:
                processFanboxPost(post, artist)
            image_count = image_count + 1
            PixivHelper.wait(__config__)

        if not artist.hasNextPage:
            PixivHelper.print_and_log("info", "No more post for {0}".format(artist))
            break
        current_page = current_page + 1
        if end_page > 0 and current_page > end_page:
            PixivHelper.print_and_log("info", "Reaching page limit for {0}, limit {1}".format(artist, end_page))
            break
        next_url = artist.nextUrl
        if next_url is None:
            PixivHelper.print_and_log("info", "No more next page for {0}".format(artist))
            break


def processFanboxPost(post, artist):
    __dbManager__.insertPost(artist.artistId, post.imageId, post.imageTitle,
                             post.feeRequired, post.worksDate, post.type)

    post_files = []

    flag_processed = False
    if __config__.checkDBProcessHistory:
        result = __dbManager__.selectPostByPostId(post.imageId)
        if result:
            updated_date = result[5]
            if updated_date is not None and post.updatedDateDatetime <= datetime_z.parse_datetime(updated_date):
                flag_processed = True

    try:
        if not post.is_restricted and not flag_processed:
            __br__.fanboxUpdatePost(post)

        if ((not post.is_restricted) or __config__.downloadCoverWhenRestricted) and (not flag_processed):
            # cover image
            if post.coverImageUrl is not None:
                # fake the image_url for filename compatibility, add post id and pagenum
                fake_image_url = post.coverImageUrl.replace("{0}/cover/".format(post.imageId),
                                                            "{0}_".format(post.imageId))
                filename = PixivHelper.make_filename(__config__.filenameFormatFanboxCover,
                                                     post,
                                                     artistInfo=artist,
                                                     tagsSeparator=__config__.tagsSeparator,
                                                     tagsLimit=__config__.tagsLimit,
                                                     fileUrl=fake_image_url,
                                                     bookmark=None,
                                                     searchTags='',
                                                     useTranslatedTag=__config__.useTranslatedTag,
                                                     tagTranslationLocale=__config__.tagTranslationLocale)
                filename = PixivHelper.sanitize_filename(filename, __config__.rootDirectory)
                post.linkToFile[post.coverImageUrl] = filename

                print("Downloading cover from {0}".format(post.coverImageUrl))
                print("Saved to {0}".format(filename))

                referer = "https://www.pixiv.net/fanbox/creator/{0}/post/{1}".format(artist.artistId, post.imageId)
                # don't pass the post id and page number to skip db check
                (result, filename) = download_image(post.coverImageUrl,
                                                    filename,
                                                    referer,
                                                    __config__.overwrite,
                                                    __config__.retry,
                                                    __config__.backupOldFile)
                post_files.append((post.imageId, -1, filename))
                PixivHelper.get_logger().debug("Download %s result: %s", filename, result)
            else:
                PixivHelper.print_and_log("info", "No Cover Image for post: {0}.".format(post.imageId))

        if post.is_restricted:
            PixivHelper.print_and_log("info", "Skipping post: {0} due to restricted post.".format(post.imageId))
            return

        if flag_processed:
            PixivHelper.print_and_log("info", "Skipping post: {0} bacause it was downloaded before.".format(post.imageId))
            return

        if post.images is None or len(post.images) == 0:
            PixivHelper.print_and_log("info", "No Image available in post: {0}.".format(post.imageId))
        else:
            current_page = 0
            print("Image Count = {0}".format(len(post.images)))
            for image_url in post.images:
                # fake the image_url for filename compatibility, add post id and pagenum
                fake_image_url = image_url.replace("{0}/".format(post.imageId),
                                                   "{0}_p{1}_".format(post.imageId, current_page))
                filename = PixivHelper.make_filename(__config__.filenameFormatFanboxContent,
                                                     post,
                                                     artistInfo=artist,
                                                     tagsSeparator=__config__.tagsSeparator,
                                                     tagsLimit=__config__.tagsLimit,
                                                     fileUrl=fake_image_url,
                                                     bookmark=None,
                                                     searchTags='',
                                                     useTranslatedTag=__config__.useTranslatedTag,
                                                     tagTranslationLocale=__config__.tagTranslationLocale)

                filename = PixivHelper.sanitize_filename(filename, __config__.rootDirectory)

                post.linkToFile[image_url] = filename

                referer = "https://www.pixiv.net/fanbox/creator/{0}/post/{1}".format(artist.artistId, post.imageId)

                print("Downloading image {0} from {1}".format(current_page, image_url))
                print("Saved to {0}".format(filename))

                # filesize detection and overwrite issue
                _oldvalue = __config__.alwaysCheckFileSize
                __config__.alwaysCheckFileSize = False
                # don't pass the post id and page number to skip db check
                (result, filename) = download_image(image_url,
                                                    filename,
                                                    referer,
                                                    False,  # __config__.overwrite somehow unable to get remote filesize
                                                    __config__.retry,
                                                    __config__.backupOldFile)
                post_files.append((post.imageId, current_page, filename))

                PixivHelper.get_logger().debug("Download %s result: %s", filename, result)

                __config__.alwaysCheckFileSize = _oldvalue
                current_page = current_page + 1

        # Implement #447
        filename = PixivHelper.make_filename(__config__.filenameFormatFanboxInfo,
                                             post,
                                             artistInfo=artist,
                                             tagsSeparator=__config__.tagsSeparator,
                                             tagsLimit=__config__.tagsLimit,
                                             fileUrl="{0}".format(post.imageId),
                                             bookmark=None,
                                             searchTags='',
                                             useTranslatedTag=__config__.useTranslatedTag,
                                             tagTranslationLocale=__config__.tagTranslationLocale)

        filename = PixivHelper.sanitize_filename(filename, __config__.rootDirectory)
        if __config__.writeImageInfo:
            post.WriteInfo(filename + ".txt")
        if __config__.writeHtml:
            if post.type == "article" or (len(post.images) >= __config__.minImageCountForNonArticle and len(post.body_text) > __config__.minTextLengthForNonArticle):
                html_template = PixivConstant.HTML_TEMPLATE
                if os.path.isfile("template.html"):
                    reader = PixivHelper.open_text_file("template.html")
                    html_template = reader.read()
                    reader.close()
                post.WriteHtml(html_template, __config__.useAbsolutePathsInHtml, filename + ".html")
    finally:
        if len(post_files) > 0:
            __dbManager__.insertPostImages(post_files)

    __dbManager__.updatePostUpdateDate(post.imageId, post.updatedDate)


def menu_fanbox_download_by_id(op_is_valid, args):
    __log__.info('Download FANBOX by Artist or Creator ID mode.')
    end_page = 0
    id = ''

    if op_is_valid and len(args) > 0:
        id = args[0]
        if len(args) > 1:
            end_page = args[1]
    else:
        id = input("Artist/Creator ID = ").rstrip("\r")
        end_page = input("Max Page = ").rstrip("\r") or 0

    end_page = int(end_page)
    processFanboxArtistById(id, end_page)


def menu_reload_config():
    __log__.info('Manual Reload Config.')
    __config__.loadConfig(path=configfile)


def menu_print_config():
    __log__.info('Manual Reload Config.')
    __config__.printConfig()


def set_console_title(title=''):
    set_title = 'PixivDownloader {0} {1}'.format(PixivConstant.PIXIVUTIL_VERSION, title)
    PixivHelper.set_console_title(set_title)


def setup_option_parser():
    global __valid_options
    __valid_options = ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'f1', 'f2', 'f3', 'f4', 'd', 'e', 'm', 'b')
    parser = OptionParser()
    parser.add_option('-s', '--startaction', dest='startaction',
                      help='''Action you want to load your program with:
 1 - Download by member_id
 2 - Download by image_id
 3 - Download by tags
 4 - Download from list
 5 - Download from user bookmark
 6 - Download from user's image bookmark
 7 - Download from tags list
 8 - Download new illust from bookmark
 9 - Download by Title/Caption
10 - Download by Tag and Member Id
11 - Download images from Member Bookmark
12 - Download images by Group Id
f1 - Download from supporting list (FANBOX)
f2 - Download by artist/creator id (FANBOX)
f3 - Download by post id (FANBOX)
f4 - Download from following list (FANBOX)
 b - Batch Download from batch_job.json (experimental)
 e - Export online bookmark
 m - Export online user bookmark
 d - Manage database''')
    parser.add_option('-x', '--exitwhendone', dest='exitwhendone',
                      help='Exit programm when done. (only useful when not using DB-Manager)',
                      action='store_true', default=False)
    parser.add_option('-i', '--irfanview', dest='start_iv',
                      help='start IrfanView after downloading images using downloaded_on_%date%.txt',
                      action='store_true', default=False)
    parser.add_option('-n', '--numberofpages', dest='numberofpages',
                      help='temporarily overwrites numberOfPage set in config.ini')
    parser.add_option('-c', '--config', dest='configlocation',
                      help='load the config file from a custom location',
                      default=None)

    return parser


# Main thread #
def main_loop(ewd, op_is_valid, selection, np_is_valid_local, args):
    global __errorList
    global ERROR_CODE
    global np

    while True:
        try:
            if len(__errorList) > 0:
                print("Unknown errors from previous operation")
                for err in __errorList:
                    message = err["type"] + ": " + str(err["id"]) + " ==> " + err["message"]
                    PixivHelper.print_and_log('error', message)
                __errorList = list()
                ERROR_CODE = 1

            if op_is_valid:  # Yavos (next 3 lines): if commandline then use it
                selection = op
            else:
                selection = menu()

            if selection == '1':
                menu_download_by_member_id(op_is_valid, args)
            elif selection == '2':
                menu_download_by_image_id(op_is_valid, args)
            elif selection == '3':
                menu_download_by_tags(op_is_valid, args)
            elif selection == '4':
                menu_download_from_list(op_is_valid, args)
            elif selection == '5':
                menu_download_from_online_user_bookmark(op_is_valid, args)
            elif selection == '6':
                menu_download_from_online_image_bookmark(op_is_valid, args)
            elif selection == '7':
                menu_download_from_tags_list(op_is_valid, args)
            elif selection == '8':
                menu_download_new_illust_from_bookmark(op_is_valid, args)
            elif selection == '9':
                menu_download_by_title_caption(op_is_valid, args)
            elif selection == '10':
                menu_download_by_tag_and_member_id(op_is_valid, args)
            elif selection == '11':
                menu_download_by_member_bookmark(op_is_valid, args)
            elif selection == '12':
                menu_download_by_group_id(op_is_valid, args)
            elif selection == 'b':
                PixivBatchHandler.process_batch_job(sys.modules[__name__])
            elif selection == 'e':
                menu_export_online_bookmark(op_is_valid, args)
            elif selection == 'm':
                menu_export_online_user_bookmark(op_is_valid, args)
            elif selection == 'd':
                __dbManager__.main()
            elif selection == 'r':
                menu_reload_config()
            elif selection == 'p':
                menu_print_config()
            elif selection == 'i':
                menu_import_list()
            # PIXIV FANBOX
            elif selection == 'f1':
                menu_fanbox_download_from_list(op_is_valid, PixivModelFanbox.FanboxArtist.SUPPORTING, args)
            elif selection == 'f2':
                menu_fanbox_download_by_id(op_is_valid, args)
            elif selection == 'f3':
                menu_fanbox_download_by_post_id(op_is_valid, args)
            elif selection == 'f4':
                menu_fanbox_download_from_list(op_is_valid, PixivModelFanbox.FanboxArtist.FOLLOWING, args)
            # END PIXIV FANBOX
            elif selection == '-all':
                if not np_is_valid_local:
                    np_is_valid_local = True
                    np = 0
                    print('download all mode activated')
                else:
                    np_is_valid_local = False
                    print('download mode reset to', __config__.numberOfPage, 'pages')
            elif selection == 'x':
                break

            if ewd:  # Yavos: added lines for "exit when done"
                break
            op_is_valid = False  # Yavos: needed to prevent endless loop
        except KeyboardInterrupt:
            PixivHelper.print_and_log("info", "Keyboard Interrupt pressed, selection: {0}".format(selection))
            PixivHelper.clearScreen()
            print("Restarting...")
            selection = menu()
        except PixivException as ex:
            if ex.htmlPage is not None:
                filename = PixivHelper.sanitize_filename(ex.value)
                PixivHelper.dump_html("Dump for {0}.html".format(filename), ex.htmlPage)
            raise  # keep old behaviour

    return np_is_valid_local, op_is_valid, selection


def doLogin(password, username):
    global __br__
    result = False
    # store username/password for oAuth in case not stored in config.ini
    if username is not None and len(username) > 0:
        __br__._username = username
    if password is not None and len(password) > 0:
        __br__._password = password

    try:
        if len(__config__.cookie) > 0:
            result = __br__.loginUsingCookie()

        if not result:
            result = __br__.login(username, password)

    except BaseException:
        PixivHelper.print_and_log('error', 'Error at doLogin(): {0}'.format(str(sys.exc_info())))
        raise PixivException("Cannot Login!", PixivException.CANNOT_LOGIN)
    return result


def import_list(list_name='list.txt'):
    list_path = __config__.downloadListDirectory + os.sep + list_name
    if(os.path.exists(list_path)):
        list_txt = PixivListItem.parseList(list_path, __config__.rootDirectory)
        __dbManager__.importList(list_txt)
        print("Updated " + str(len(list_txt)) + " items.")
    else:
        msg = "List file not found: {0}".format(list_path)
        PixivHelper.print_and_log('warn', msg)


def menu_import_list():
    __log__.info('Import List mode.')
    list_name = input("List filename = ").rstrip("\r")
    if len(list_name) == 0:
        list_name = "list.txt"
    import_list(list_name)


def main():
    set_console_title()
    header()

    # Option Parser
    global np_is_valid  # used in process image bookmark
    global np  # used in various places for number of page overwriting
    global start_iv  # used in download_image
    global dfilename
    global op
    global __br__
    global configfile
    global ERROR_CODE
    global __dbManager__
    global __valid_options

    parser = setup_option_parser()
    (options, args) = parser.parse_args()

    op = options.startaction
    if op in __valid_options:
        op_is_valid = True
    elif op is None:
        op_is_valid = False
    else:
        op_is_valid = False
        parser.error('%s is not valid operation' % op)
        # Yavos: use print option instead when program should be running even with this error

    ewd = options.exitwhendone
    configfile = options.configlocation

    try:
        if options.numberofpages is not None:
            np = int(options.numberofpages)
            np_is_valid = True
        else:
            np_is_valid = False
    except BaseException:
        np_is_valid = False
        parser.error('Value %s used for numberOfPage is not an integer.' % options.numberofpages)
        # Yavos: use print option instead when program should be running even with this error
        # end new lines by Yavos

    __log__.info('###############################################################')
    if len(sys.argv) == 0:
        __log__.info('Starting with no argument..')
    else:
        __log__.info('Starting with argument: [%s].', " ".join(sys.argv))
    try:
        __config__.loadConfig(path=configfile)
        PixivHelper.set_config(__config__)
    except BaseException:
        print('Failed to read configuration.')
        __log__.exception('Failed to read configuration.')

    PixivHelper.set_log_level(__config__.logLevel)
    if __br__ is None:
        __br__ = PixivBrowserFactory.getBrowser(config=__config__)

    if __config__.checkNewVersion:
        PixivHelper.check_version(__br__, config=__config__)

    selection = None

    # Yavos: adding File for downloadlist
    now = datetime.date.today()
    dfilename = __config__.downloadListDirectory + os.sep + 'Downloaded_on_' + now.strftime('%Y-%m-%d') + '.txt'
    if not re.match(r'[a-zA-Z]:', dfilename):
        dfilename = sys.path[0] + os.sep + dfilename
        # dfilename = sys.path[0].rsplit('\\',1)[0] + '\\' + dfilename #Yavos: only useful for myself
    dfilename = dfilename.replace('\\\\', '\\')
    dfilename = dfilename.replace('\\', os.sep)
    dfilename = dfilename.replace(os.sep + 'library.zip' + os.sep + '.', '')

    directory = os.path.dirname(dfilename)
    if not os.path.exists(directory):
        os.makedirs(directory)
        __log__.info('Creating directory: %s', directory)

    # write BOM
    if start_iv or __config__.createDownloadLists:
        if not os.path.isfile(dfilename) or os.path.getsize(dfilename) == 0:
            dfile = codecs.open(dfilename, 'a+', encoding='utf-8')
            dfile.write(u'\ufeff')
            dfile.close()

    # Yavos: adding IrfanView-Handling
    start_irfan_slide = False
    start_irfan_view = False
    if __config__.startIrfanSlide or __config__.startIrfanView:
        start_iv = True
        start_irfan_slide = __config__.startIrfanSlide
        start_irfan_view = __config__.startIrfanView
    elif options.start_iv is not None:
        start_iv = options.start_iv
        start_irfan_view = True
        start_irfan_slide = False

    try:
        __dbManager__ = PixivDBManager(root_directory=__config__.rootDirectory, target=__config__.dbPath)
        __dbManager__.createDatabase()

        if __config__.useList:
            import_list('list.txt')

        if __config__.overwrite:
            msg = 'Overwrite enabled.'
            PixivHelper.print_and_log('info', msg)

        if __config__.dayLastUpdated != 0 and __config__.processFromDb:
            PixivHelper.print_and_log('info',
                                    'Only process members where the last update is >= ' + str(__config__.dayLastUpdated) + ' days ago')

        if __config__.dateDiff > 0:
            PixivHelper.print_and_log('info', 'Only process image where day last updated >= ' + str(__config__.dateDiff))

        if __config__.useBlacklistTags:
            global __blacklistTags
            __blacklistTags = PixivTags.parseTagsList("blacklist_tags.txt")
            PixivHelper.print_and_log('info', 'Using Blacklist Tags: ' + str(len(__blacklistTags)) + " items.")

        if __config__.useBlacklistMembers:
            global __blacklistMembers
            __blacklistMembers = PixivTags.parseTagsList("blacklist_members.txt")
            PixivHelper.print_and_log('info', 'Using Blacklist Members: ' + str(len(__blacklistMembers)) + " members.")

        if __config__.useBlacklistTitles:
            global __blacklistTitles
            __blacklistTitles = PixivTags.parseTagsList("blacklist_titles.txt")
            PixivHelper.print_and_log('info', 'Using Blacklist Titles: ' + str(len(__blacklistTitles)) + " items.")

        if __config__.useSuppressTags:
            global __suppressTags
            __suppressTags = PixivTags.parseTagsList("suppress_tags.txt")
            PixivHelper.print_and_log('info', 'Using Suppress Tags: ' + str(len(__suppressTags)) + " items.")

        if __config__.createWebm:
            import shlex
            cmd = u"{0} -encoders".format(__config__.ffmpeg)
            ffmpeg_args = shlex.split(cmd)
            try:
                p = subprocess.run(ffmpeg_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, check=True)
                buff = p.stdout
                if buff.find(__config__.ffmpegCodec) == 0:
                    __config__.createWebm = False
                    PixivHelper.print_and_log('error', '{0}'.format("#" * 80))
                    PixivHelper.print_and_log('error', 'Missing {0} encoder, createWebm disabled.'.format(__config__.ffmpegCodec))
                    PixivHelper.print_and_log('error', 'Command used: {0}.'.format(cmd))
                    PixivHelper.print_and_log('info', 'Please download ffmpeg with {0} encoder enabled.'.format(__config__.ffmpegCodec))
                    PixivHelper.print_and_log('error', '{0}'.format("#" * 80))
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                __config__.createWebm = False
                PixivHelper.print_and_log('error', '{0}'.format("#" * 80))
                PixivHelper.print_and_log('error', 'Failed to load ffmpeg, createWebm disabled: {0}'.format(exc_value))
                PixivHelper.print_and_log('error', 'Command used: {0}.'.format(cmd))
                PixivHelper.print_and_log('info', 'Please download ffmpeg with {0} encoder enabled.'.format(__config__.ffmpegCodec))
                PixivHelper.print_and_log('error', '{0}'.format("#" * 80))

        if __config__.useLocalTimezone:
            PixivHelper.print_and_log("info", "Using local timezone: {0}".format(PixivHelper.LocalUTCOffsetTimezone()))

        username = __config__.username
        if username == '':
            username = input('Username ? ').rstrip("\r")
        else:
            msg = 'Using Username: ' + username
            print(msg)
            __log__.info(msg)

        password = __config__.password
        if password == '':
            password = getpass.getpass('Password ? ')

        if np_is_valid and np != 0:  # Yavos: overwrite config-data
            msg = 'Limit up to: ' + str(np) + ' page(s). (set via commandline)'
            print(msg)
            __log__.info(msg)
        elif __config__.numberOfPage != 0:
            msg = 'Limit up to: ' + str(__config__.numberOfPage) + ' page(s).'
            print(msg)
            __log__.info(msg)

        result = doLogin(password, username)

        if result:
            np_is_valid, op_is_valid, selection = main_loop(ewd, op_is_valid, selection, np_is_valid, args)

            if start_iv:  # Yavos: adding start_irfan_view-handling
                PixivHelper.start_irfanview(dfilename, __config__.IrfanViewPath, start_irfan_slide, start_irfan_view)
        else:
            ERROR_CODE = PixivException.NOT_LOGGED_IN
    except PixivException as pex:
        PixivHelper.print_and_log('error', pex.message)
        ERROR_CODE = pex.errorCode
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        __log__.exception('Unknown Error: %s', str(exc_value))
        ERROR_CODE = getattr(ex, 'errorCode', -1)
    finally:
        __dbManager__.close()
        if not ewd:  # Yavos: prevent input on exitwhendone
            if selection is None or selection != 'x':
                input('press enter to exit.')
        __log__.setLevel("INFO")
        __log__.info('EXIT: %s', ERROR_CODE)
        __log__.info('###############################################################')
        sys.exit(ERROR_CODE)


if __name__ == '__main__':
    if not sys.version_info >= (3, 7):
        print("Require Python 3.7++")
    else:
        gc.enable()
        # gc.set_debug(gc.DEBUG_STATS)
        main()
        gc.collect()
        gc.collect()
