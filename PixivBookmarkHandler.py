import os
import sys
from datetime import time

import PixivArtistHandler
import PixivConstant
import PixivDownloadHandler
import PixivHelper
import PixivImageHandler
from PixivBookmark import PixivBookmark
from PixivBrowserFactory import PixivBrowser
from PixivGroup import PixivGroup


def process_bookmark(caller,
                     config,
                     hide='n',
                     start_page=1,
                     end_page=0,
                     bookmark_count=-1):
    br: PixivBrowser = caller.__br__

    try:
        total_list = list()
        print(f"My Member Id = {br._myId}")
        if hide != 'o':
            print("Importing Bookmarks...")
            total_list.extend(get_bookmarks(caller, config, False, start_page, end_page, br._myId))
        if hide != 'n':
            print("Importing Private Bookmarks...")
            total_list.extend(get_bookmarks(caller, config, True, start_page, end_page, br._myId))
        print(f"Result: {str(len(total_list))} items.")
        i = 0
        current_member = 1
        for item in total_list:
            print("%d/%d\t%f %%" % (i, len(total_list), 100.0 * i / float(len(total_list))))
            i += 1
            prefix = "[{0} of {1}]".format(current_member, len(total_list))

            if str(item.memberId) in caller.__blacklistMembers:
                PixivHelper.print_and_log('warn', f'Skipping member id: {item.memberId} by blacklist_members.txt.')
            else:
                PixivArtistHandler.process_member(caller,
                                                  config,
                                                  item.memberId,
                                                  user_dir=item.path,
                                                  title_prefix=prefix,
                                                  bookmark_count=bookmark_count)

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


def process_image_bookmark(caller,
                           config,
                           hide='n',
                           start_page=1,
                           end_page=0,
                           tag=None,
                           use_image_tag=False):
    try:
        print("Importing image bookmarks...")
        totalList = list()
        private_list = list()
        public_list = list()
        image_count = 1
        total_bookmark_count = 0

        if hide == 'n':
            (public_list, total_bookmark_count) = get_image_bookmark(caller, config, False, start_page, end_page, tag, use_image_tag)
        elif hide == 'y':
            # public and private image bookmarks
            (public_list, total_bookmark_count_pub) = get_image_bookmark(caller, config, False, start_page, end_page, tag, use_image_tag)
            (private_list, total_bookmark_count_priv) = get_image_bookmark(caller, config, True, start_page, end_page, tag, use_image_tag)
            total_bookmark_count = total_bookmark_count_pub + total_bookmark_count_priv
        else:
            (private_list, total_bookmark_count) = get_image_bookmark(caller, config, True, start_page, end_page, tag, use_image_tag)
        totalList.extend(private_list)
        totalList.extend(public_list)

        PixivHelper.print_and_log('info', f"Found {len(totalList)} of {total_bookmark_count} possible image(s) .")
        for item in totalList:
            print(f"Image # {image_count}")
            result = PixivImageHandler.process_image(caller,
                                                     config,
                                                     artist=None,
                                                     image_id=item,
                                                     search_tags=tag)
            image_count = image_count + 1
            PixivHelper.wait(result, config)

        print("Done.\n")
    except KeyboardInterrupt:
        raise
    except BaseException:
        PixivHelper.print_and_log('error', 'Error at process_image_bookmark(): {0}'.format(sys.exc_info()))
        raise


def process_new_illust_from_bookmark(caller,
                                     config,
                                     page_num=1,
                                     end_page_num=0,
                                     bookmark_count=-1):
    br: PixivBrowser = caller.__br__
    parsed_page = None
    try:
        print("Processing New Illust from bookmark")
        i = page_num
        image_count = 1
        flag = True
        while flag:
            print(f"Page #{i}")
            mode = "all"
            if config.r18mode:
                mode = "r18"
            pb = br.getFollowedNewIllusts(mode, current_page=i)

            for image_id in pb.imageList:
                print(f"Image #{image_count}")
                result = PixivImageHandler.process_image(caller,
                                                         config,
                                                         artist=None,
                                                         image_id=int(image_id),
                                                         bookmark_count=bookmark_count)
                image_count = image_count + 1

                if result == PixivConstant.PIXIVUTIL_SKIP_OLDER:
                    flag = False
                    break

                PixivHelper.wait(result, config)
            i = i + 1

            # page.close()
            # parsed_page.decompose()
            # del parsed_page

            if (end_page_num != 0 and i > end_page_num) or pb.isLastPage:
                print("Limit or last page reached.")
                flag = False

        print("Done.")
    except KeyboardInterrupt:
        raise
    except BaseException:
        PixivHelper.print_and_log('error', 'Error at process_new_illust_from_bookmark(): {0}'.format(sys.exc_info()))
        if parsed_page is not None:
            filename = "Dump for New Illust from bookmark.html"
            PixivHelper.dump_html(filename, parsed_page)
        raise


def process_from_group(caller,
                       config,
                       group_id,
                       limit=0,
                       process_external=True):
    br: PixivBrowser = caller.__br__
    json_response = None
    try:
        print("Download by Group Id")
        if limit != 0:
            print(f"Limit: {limit}")
        if process_external:
            print(f"Include External Image: {process_external}")

        max_id = 0
        image_count = 0
        flag = True
        while flag:
            url = f"https://www.pixiv.net/group/images.php?format=json&max_id={max_id}&id={group_id}"
            PixivHelper.print_and_log('info', f"Getting images from: {url}")
            response = br.open(url)
            json_response = response.read()
            response.close()
            group_data = PixivGroup(json_response)
            max_id = group_data.maxId
            if group_data.imageList is not None and len(group_data.imageList) > 0:
                for image in group_data.imageList:
                    if image_count > limit and limit != 0:
                        flag = False
                        break
                    print(f"Image #{image_count}")
                    print(f"ImageId: {image}")
                    result = PixivImageHandler.process_image(caller,
                                                             config,
                                                             image_id=image)
                    image_count = image_count + 1
                    PixivHelper.wait(result, config)

            if process_external and group_data.externalImageList is not None and len(group_data.externalImageList) > 0:
                for image_data in group_data.externalImageList:
                    if image_count > limit and limit != 0:
                        flag = False
                        break
                    print(f"Image #{image_count}")
                    print(f"Member Id    : {image_data.artist.artistId}")
                    PixivHelper.safePrint(f"Member Name  : {image_data.artist.artistName}")
                    print(f"Member Token : {image_data.artist.artistToken}")
                    print(f"Image Url    : {image_data.imageUrls[0]}")

                    filename = PixivHelper.make_filename(config.filenameFormat,
                                                         imageInfo=image_data,
                                                         tagsSeparator=config.tagsSeparator,
                                                         tagsLimit=config.tagsLimit,
                                                         fileUrl=image_data.imageUrls[0],
                                                         useTranslatedTag=config.useTranslatedTag,
                                                         tagTranslationLocale=config.tagTranslationLocale)
                    filename = PixivHelper.sanitize_filename(filename, config.rootDirectory)
                    PixivHelper.safePrint(f"Filename  : {filename}")
                    (result, filename) = PixivDownloadHandler.download_image(caller,
                                                                             image_data.imageUrls[0],
                                                                             filename,
                                                                             url,
                                                                             config.overwrite,
                                                                             config.retry,
                                                                             backup_old_file=config.backupOldFile)
                    PixivHelper.get_logger().debug("Download %s result: %s", filename, result)
                    if config.setLastModified and filename is not None and os.path.isfile(filename):
                        ts = time.mktime(image_data.worksDateDateTime.timetuple())
                        os.utime(filename, (ts, ts))

                    image_count = image_count + 1

            if (group_data.imageList is None or len(group_data.imageList) == 0) and \
               (group_data.externalImageList is None or len(group_data.externalImageList) == 0):
                flag = False
            print("")

    except BaseException:
        PixivHelper.print_and_log('error', 'Error at process_from_group(): {0}'.format(sys.exc_info()))
        if json_response is not None:
            filename = f"Dump for Download by Group {group_id}.json"
            PixivHelper.dump_html(filename, json_response)
        raise


def export_bookmark(caller,
                    config,
                    filename,
                    hide='n',
                    start_page=1,
                    end_page=0,
                    member_id=None):
    try:
        total_list = list()
        if hide != 'o':
            print("Importing Bookmarks...")
            total_list.extend(get_bookmarks(caller, config, False, start_page, end_page, member_id))
        if hide != 'n':
            print("Importing Private Bookmarks...")
            total_list.extend(get_bookmarks(caller, config, True, start_page, end_page, member_id))
        print(f"Result: {len(total_list)} items.")
        PixivBookmark.exportList(total_list, filename)
    except KeyboardInterrupt:
        raise
    except BaseException:
        PixivHelper.print_and_log('error', 'Error at export_bookmark(): {0}'.format(sys.exc_info()))
        raise


def export_image_bookmark(caller,
                          config,
                          hide='n',
                          start_page=1,
                          end_page=0,
                          tag=None,
                          use_image_tag=False,
                          filename='exported_images.txt'):
    try:
        print("Getting image bookmarks...")
        total_list = list()
        private_list = list()
        public_list = list()
        total_bookmark_count = 0

        if hide == 'n':
            (public_list, total_bookmark_count) = get_image_bookmark(caller, config, False, start_page, end_page, tag, use_image_tag)
        elif hide == 'y':
            # public and private image bookmarks
            (public_list, total_bookmark_count_pub) = get_image_bookmark(caller, config, False, start_page, end_page, tag, use_image_tag)
            (private_list, total_bookmark_count_priv) = get_image_bookmark(caller, config, True, start_page, end_page, tag, use_image_tag)
            total_bookmark_count = total_bookmark_count_pub + total_bookmark_count_priv
        else:
            (private_list, total_bookmark_count) = get_image_bookmark(caller, config, True, start_page, end_page, tag, use_image_tag)
        total_list.extend(private_list)
        total_list.extend(public_list)

        PixivBookmark.export_image_list(total_list, filename)

        PixivHelper.print_and_log('info', f"Found {len(total_list)} of {total_bookmark_count} possible image(s) .")

        print("Done.\n")
    except KeyboardInterrupt:
        raise
    except BaseException:
        PixivHelper.print_and_log('error', 'Error at export_image_bookmark(): {0}'.format(sys.exc_info()))
        raise


def export_image_table(caller, filename, pixiv, fanbox, sketch):
    export_list = list()
    table = list()
    try:
        if pixiv == 'o':
            table.append("Pixiv")
        elif fanbox == 'o':
            table.append("Fanbox")
        elif sketch == 'o':
            table.append("Sketch")
        else:
            if pixiv == 'y':
                table.append("Pixiv")
            if fanbox == 'y':
                table.append("Fanbox")
            if sketch == 'y':
                table.append("Sketch")
        for t in table:
            export_list = caller.__dbManager__.exportImageTable(t)
            PixivBookmark.export_image_list(export_list, f"{filename}-{t}")
    except KeyboardInterrupt:
        raise
    except BaseException:
        PixivHelper.print_and_log('error', 'Error at export_image_table(): {0}'.format(sys.exc_info()))
        raise


def get_bookmarks(caller, config, hide, start_page=1, end_page=0, member_id=None):
    br: PixivBrowser = caller.__br__

    """Get User's bookmarked artists """
    total_list = list()
    i = start_page
    limit = 48
    offset = 0
    is_json = False
    locale = "&lang=en"
    if br._locale is not None and len(br._locale) > 0:
        locale = f"&lang={br._locale}"

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
            # Issue #942
            member_id = br._myId
            is_json = True
            url = f'https://www.pixiv.net/ajax/user/{member_id}/following?offset={offset}&limit={limit}'
        if hide:
            url = url + "&rest=hide"
        else:
            url = url + "&rest=show"
        url = url + locale

        PixivHelper.print_and_log('info', f"Source URL: {url}")

        page = br.open_with_retry(url)
        page_str = page.read().decode('utf8')
        page.close()

        bookmarks = PixivBookmark.parseBookmark(page_str,
                                                root_directory=config.rootDirectory,
                                                db_path=config.dbPath,
                                                locale=br._locale,
                                                is_json=is_json)

        if len(bookmarks) == 0:
            print('No more data')
            break
        total_list.extend(bookmarks)
        i = i + 1
        print(str(len(bookmarks)), 'items')
        PixivHelper.wait(config=config)
    return total_list


def get_image_bookmark(caller, config, hide, start_page=1, end_page=0, tag=None, use_image_tag=False):
    """Get user's image bookmark"""
    br: PixivBrowser = caller.__br__
    total_list = list()
    i = start_page
    offset = 0
    limit = 48
    member_id = br._myId
    total_bookmark_count = 0
    encoded_tag = ''

    while True:
        if end_page != 0 and i > end_page:
            print(f"Page Limit reached: {end_page}")
            break

        # https://www.pixiv.net/ajax/user/189816/illusts/bookmarks?tag=&offset=0&limit=48&rest=show
        show = "show"
        if hide:
            show = "hide"

        if tag is not None and len(tag) > 0:
            encoded_tag = PixivHelper.encode_tags(tag)
        offset = limit * (i - 1)
        PixivHelper.print_and_log('info', f"Importing user's bookmarked image from page {i}")

        url = f"https://www.pixiv.net/ajax/user/{member_id}/illusts/bookmarks?tag={encoded_tag}&offset={offset}&limit={limit}&rest={show}"
        if use_image_tag:  # don't filter based on user's bookmark tag
            url = f"https://www.pixiv.net/ajax/user/{member_id}/illusts/bookmarks?tag=&offset={offset}&limit={limit}&rest={show}"
            PixivHelper.print_and_log('info', f"Using image tag: {tag}")

        PixivHelper.print_and_log('info', f"Source URL: {url}")
        page = br.open(url)
        page_str = page.read().decode('utf8')
        page.close()

        if use_image_tag:
            (bookmarks, total_bookmark_count) = PixivBookmark.parseImageBookmark(page_str, image_tags_filter=tag)
        else:
            (bookmarks, total_bookmark_count) = PixivBookmark.parseImageBookmark(page_str)

        total_list.extend(bookmarks)
        if len(bookmarks) == 0 and not use_image_tag:
            print("No more images.")
            break
        elif use_image_tag and total_bookmark_count / limit < i:
            print("Last page reached.")
            break
        else:
            print(f" found {len(bookmarks)} images.")

        i = i + 1

        # Issue#569
        PixivHelper.wait(config=config)

    return (total_list, total_bookmark_count)
