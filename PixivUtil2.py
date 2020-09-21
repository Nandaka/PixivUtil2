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

import colorama
from colorama import Back, Fore, Style

import PixivArtistHandler
import PixivBatchHandler
import PixivBookmarkHandler
import PixivBrowserFactory
import PixivConfig
import PixivConstant
import PixivDownloadHandler
import PixivFanboxHandler
import PixivHelper
import PixivImageHandler
import PixivListHandler
import PixivModelFanbox
import PixivSketchHandler
import PixivTagsHandler
from PixivDBManager import PixivDBManager
from PixivException import PixivException
from PixivTags import PixivTags

colorama.init()
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


def header():
    print(Fore.YELLOW + Back.BLACK + Style.BRIGHT + f"PixivDownloader2 version {PixivConstant.PIXIVUTIL_VERSION}" + Style.RESET_ALL)
    print(Fore.CYAN + Back.BLACK + Style.BRIGHT + PixivConstant.PIXIVUTIL_LINK + Style.RESET_ALL)
    print(Fore.YELLOW + Back.BLACK + Style.BRIGHT + f"Donate at {Fore.CYAN}{Style.BRIGHT}{PixivConstant.PIXIVUTIL_DONATE}" + Style.RESET_ALL)


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
    PADDING = 40
    set_console_title()
    header()
    print('--Pixiv'.ljust(PADDING, "-"))
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
    print('--FANBOX'.ljust(PADDING, "-"))
    print('f1. Download from supporting list (FANBOX)')
    print('f2. Download by artist/creator id (FANBOX)')
    print('f3. Download by post id (FANBOX)')
    print('f4. Download from following list (FANBOX)')
    print('--Sketch'.ljust(PADDING, "-"))
    print('s1. Download by creator id (Sketch)')
    print('s2. Download by post id (Sketch)')
    print('--Batch Download'.ljust(PADDING, "-"))
    print('b. Batch Download from batch_job.json (experimental)')
    print('--Others'.ljust(PADDING, "-"))
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
    __log__.info('Member id mode (1).')
    current_member = 1
    page = 1
    end_page = 0
    include_sketch = False

    if opisvalid and len(args) > 0:
        # first argument is either y/n followed by member ids.
        include_sketch = args[0].lower()
        if include_sketch == 'y' or include_sketch == 'n':
            include_sketch = True if include_sketch == 'y' else False
            args = args[1:]

        for member_id in args:
            try:
                prefix = "[{0} of {1}] ".format(current_member, len(args))
                test_id = int(member_id)
                PixivArtistHandler.process_member(sys.modules[__name__],
                                                  __config__,
                                                  test_id,
                                                  title_prefix=prefix)
                current_member = current_member + 1
            except BaseException:
                PixivHelper.print_and_log('error', "Member ID: {0} is not valid".format(member_id))
                global ERROR_CODE
                ERROR_CODE = -1
                continue
    else:
        member_ids = input('Member ids: ').rstrip("\r")
        (page, end_page) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)
        include_sketch = input('Include Pixiv Sketch [y/n]?') or 'n'
        if include_sketch.lower() == 'y':
            include_sketch = True

        member_ids = PixivHelper.get_ids_from_csv(member_ids, sep=" ")
        PixivHelper.print_and_log('info', "Member IDs: {0}".format(member_ids))
        for member_id in member_ids:
            try:
                prefix = "[{0} of {1}] ".format(current_member, len(member_ids))
                PixivArtistHandler.process_member(sys.modules[__name__],
                                                  __config__,
                                                  member_id,
                                                  page=page,
                                                  end_page=end_page,
                                                  title_prefix=prefix)
                # Issue #793
                if include_sketch:
                    prefix = "[{0} of {1}] ".format(current_member, len(member_ids))
                    PixivSketchHandler.process_sketch_artists(sys.modules[__name__],
                                                              __config__,
                                                              member_id,
                                                              page,
                                                              end_page)

                current_member = current_member + 1
            except PixivException as ex:
                print(ex)


def menu_download_by_member_bookmark(opisvalid, args):
    __log__.info('Member Bookmark mode (11).')
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
            PixivArtistHandler.process_member(sys.modules[__name__],
                                              __config__,
                                              mid,
                                              page=page,
                                              end_page=end_page,
                                              bookmark=True,
                                              tags=None,
                                              title_prefix=prefix)
            current_member = current_member + 1

    else:
        member_id = input('Member id: ').rstrip("\r")
        tags = input('Filter Tags: ').rstrip("\r")
        (page, end_page) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)
        if __br__._myId == int(member_id):
            PixivHelper.print_and_log('error', "Member ID: {0} is your own id, use option 6 instead.".format(member_id))
        else:
            PixivArtistHandler.process_member(sys.modules[__name__],
                                              __config__,
                                              member_id.strip(),
                                              page=page,
                                              end_page=end_page,
                                              bookmark=True,
                                              tags=tags)


def menu_download_by_image_id(opisvalid, args):
    __log__.info('Image id mode (2).')
    if opisvalid and len(args) > 0:
        for image_id in args:
            try:
                test_id = int(image_id)
                PixivImageHandler.process_image(sys.modules[__name__],
                                                __config__,
                                                artist=None,
                                                image_id=test_id,
                                                useblacklist=False)
            except BaseException:
                PixivHelper.print_and_log('error', "Image ID: {0} is not valid".format(image_id))
                global ERROR_CODE
                ERROR_CODE = -1
                continue
    else:
        image_ids = input('Image ids: ').rstrip("\r")
        image_ids = PixivHelper.get_ids_from_csv(image_ids, sep=" ")
        for image_id in image_ids:
            PixivImageHandler.process_image(sys.modules[__name__],
                                            __config__,
                                            artist=None,
                                            image_id=int(image_id),
                                            useblacklist=False)


def menu_download_by_tags(opisvalid, args):
    __log__.info('Tags mode (3).')
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

    PixivTagsHandler.process_tags(sys.modules[__name__],
                                  tags.strip(),
                                  page=page,
                                  end_page=end_page,
                                  wild_card=wildcard,
                                  start_date=start_date,
                                  end_date=end_date,
                                  use_tags_as_dir=__config__.useTagsAsDir,
                                  bookmark_count=bookmark_count,
                                  oldest_first=oldest_first,
                                  type_mode=type_mode)


def menu_download_by_title_caption(opisvalid, args):
    __log__.info('Title/Caption mode (9).')
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

    PixivTagsHandler.process_tags(sys.modules[__name__],
                                  tags.strip(),
                                  page=page,
                                  end_page=end_page,
                                  wild_card=False,
                                  title_caption=True,
                                  start_date=start_date,
                                  end_date=end_date,
                                  use_tags_as_dir=__config__.useTagsAsDir)


def menu_download_by_tag_and_member_id(opisvalid, args):
    __log__.info('Tag and MemberId mode (10).')
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

    PixivTagsHandler.process_tags(sys.modules[__name__],
                                  tags.strip(),
                                  page=page,
                                  end_page=end_page,
                                  use_tags_as_dir=__config__.useTagsAsDir,
                                  member_id=int(member_id))


def menu_download_from_list(opisvalid, args):
    __log__.info('Batch mode from list (4).')
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

    PixivListHandler.process_list(sys.modules[__name__],
                                  __config__,
                                  list_file_name,
                                  tags)


def menu_download_from_online_user_bookmark(opisvalid, args):
    __log__.info('User Bookmarked Artist mode (5).')
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
    PixivBookmarkHandler. process_bookmark(sys.modules[__name__], __config__, hide, start_page, end_page)


def menu_download_from_online_image_bookmark(opisvalid, args):
    __log__.info("User's Image Bookmark mode (6).")
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

    PixivBookmarkHandler.process_image_bookmark(sys.modules[__name__],
                                                __config__,
                                                hide=hide,
                                                start_page=start_page,
                                                end_page=end_page,
                                                tag=tag,
                                                sorting=sorting)


def menu_download_from_tags_list(opisvalid, args):
    __log__.info('Taglist mode (7).')
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

    PixivListHandler.process_tags_list(sys.modules[__name__],
                                       __config__,
                                       filename,
                                       page,
                                       end_page,
                                       wild_card=wildcard,
                                       oldest_first=oldest_first,
                                       bookmark_count=bookmark_count,
                                       start_date=start_date,
                                       end_date=end_date)


def menu_download_new_illust_from_bookmark(opisvalid, args):
    __log__.info('New Illust from Bookmark mode (8).')

    if opisvalid:
        (page_num, end_page_num) = get_start_and_end_number_from_args(args, offset=0)
    else:
        (page_num, end_page_num) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)

    PixivBookmarkHandler.process_new_illust_from_bookmark(sys.modules[__name__],
                                                          __config__,
                                                          page_num=page_num,
                                                          end_page_num=end_page_num)


def menu_download_by_group_id(opisvalid, args):
    __log__.info('Group mode (12).')
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

    PixivBookmarkHandler.process_from_group(sys.modules[__name__],
                                            __config__,
                                            group_id,
                                            limit=limit,
                                            process_external=process_external)


def menu_export_online_bookmark(opisvalid, args):
    __log__.info('Export Bookmark mode (e).')
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

    PixivBookmarkHandler.export_bookmark(sys.modules[__name__], __config__, filename, hide)


def menu_export_online_user_bookmark(opisvalid, args):
    __log__.info('Export Bookmark mode (m).')
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

    PixivBookmarkHandler.export_bookmark(sys.modules[__name__], __config__, filename, 'n', 1, 0, member_id)


def menu_fanbox_download_from_list(op_is_valid, via, args):
    via_type = ""
    if via == PixivModelFanbox.FanboxArtist.SUPPORTING:
        via_type = "supporting"
    elif via == PixivModelFanbox.FanboxArtist.FOLLOWING:
        via_type = "following"

    __log__.info(f'Download FANBOX {via_type.capitalize()} list mode (f1/f4).')
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

    for index, artist_id in enumerate(ids, start=1):
        # Issue #567
        try:
            PixivFanboxHandler.process_fanbox_artist_by_id(sys.modules[__name__],
                                                           __config__,
                                                           artist_id,
                                                           end_page,
                                                           title_prefix=f"{index} of {len(ids)}")
        except PixivException as pex:
            PixivHelper.print_and_log("error", f"Error processing FANBOX Artist in {via_type} list: {artist_id} ==> {pex.message}")


def menu_fanbox_download_by_post_id(op_is_valid, args):
    __log__.info('Download FANBOX by post id mode (f3).')
    if op_is_valid and len(args) > 0:
        post_ids = args
    else:
        post_ids = input("Post ids = ").rstrip("\r") or 0

    post_ids = PixivHelper.get_ids_from_csv(post_ids, sep=" ")
    for post_id in post_ids:
        post_id = int(post_id)
        try:
            post = __br__.fanboxGetPostById(post_id)
            PixivFanboxHandler.process_fanbox_post(sys.modules[__name__], __config__, post, post.parent)
            del post
        except KeyboardInterrupt:
            choice = input("Keyboard Interrupt detected, continue to next post (Y/N)").rstrip("\r")
            if choice.upper() == 'N':
                PixivHelper.print_and_log("info", f"Post id: {post_id}, processing aborted")
                break
            else:
                continue
        except PixivException as pex:
            PixivHelper.print_and_log("error", "Error processing FANBOX post: {0} ==> {1}".format(post_id, pex.message))


def menu_fanbox_download_by_id(op_is_valid, args):
    __log__.info('Download FANBOX by Artist or Creator ID mode (f2).')
    end_page = 0
    artist_id = ''

    if op_is_valid and len(args) > 0:
        artist_id = args[0]
        if len(args) > 1:
            end_page = args[1]
    else:
        artist_id = input("Artist/Creator ID = ").rstrip("\r")
        end_page = input("Max Page = ").rstrip("\r") or 0

    end_page = int(end_page)
    PixivFanboxHandler.process_fanbox_artist_by_id(sys.modules[__name__],
                                                   __config__,
                                                   artist_id,
                                                   end_page)


def menu_sketch_download_by_artist_id(opisvalid, args):
    __log__.info('Download Sketch by Artist ID mode (s1).')
    current_member = 1
    page = 1
    end_page = 0

    if opisvalid and len(args) > 0:
        for member_id in args:
            try:
                prefix = "[{0} of {1}] ".format(current_member, len(args))
                PixivSketchHandler.process_sketch_artists(sys.modules[__name__],
                                                         __config__,
                                                         member_id,
                                                         page,
                                                         end_page)
                current_member = current_member + 1
            except PixivException as ex:
                PixivHelper.print_and_log("error", f"Error when processing Pixiv Sketch:{member_id}", ex)
                continue
    else:
        member_ids = input('Artist ids: ').rstrip("\r")
        (page, end_page) = PixivHelper.get_start_and_end_number(np_is_valid=np_is_valid, np=np)

        member_ids = PixivHelper.get_ids_from_csv(member_ids, sep=" ", is_string=True)
        PixivHelper.print_and_log('info', "Artist IDs: {0}".format(member_ids))
        for member_id in member_ids:
            try:
                prefix = "[{0} of {1}] ".format(current_member, len(member_ids))
                PixivSketchHandler.process_sketch_artists(sys.modules[__name__],
                                                         __config__,
                                                         member_id,
                                                         page,
                                                         end_page)
                current_member = current_member + 1
            except PixivException as ex:
                PixivHelper.print_and_log("error", f"Error when processing Pixiv Sketch:{member_id}", ex)


def menu_sketch_download_by_post_id(opisvalid, args):
    __log__.info('Download Sketch by Post ID mode (s2).')
    if opisvalid and len(args) > 0:
        for image_id in args:
            try:
                test_id = int(image_id)
                PixivSketchHandler.process_sketch_post(sys.modules[__name__],
                                                        __config__,
                                                        image_id)
            except BaseException:
                PixivHelper.print_and_log('error', "Image ID: {0} is not valid".format(image_id))
                global ERROR_CODE
                ERROR_CODE = -1
                continue
    else:
        image_ids = input('Post ids: ').rstrip("\r")
        image_ids = PixivHelper.get_ids_from_csv(image_ids, sep=" ")
        for image_id in image_ids:
            PixivSketchHandler.process_sketch_post(sys.modules[__name__],
                                                   __config__,
                                                   image_id)


def menu_reload_config():
    __log__.info('Manual Reload Config (r).')
    __config__.loadConfig(path=configfile)


def menu_print_config():
    __log__.info('Print Current Config (p).')
    __config__.printConfig()


def set_console_title(title=''):
    set_title = 'PixivDownloader {0} {1}'.format(PixivConstant.PIXIVUTIL_VERSION, title)
    PixivHelper.set_console_title(set_title)


def setup_option_parser():
    global __valid_options
    __valid_options = ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'f1', 'f2', 'f3', 'f4', 's1', 's2', 'd', 'e', 'm', 'b')
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
s1 - Download by creator id (Sketch)')
s2 - Download by post id (Sketch)')
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
            # PIXIV Sketch
            elif selection == 's1':
                menu_sketch_download_by_artist_id(op_is_valid, args)
            elif selection == 's2':
                menu_sketch_download_by_post_id(op_is_valid, args)
            # END PIXIV Sketch
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


def menu_import_list():
    __log__.info('Import List mode (i).')
    list_name = input("List filename = ").rstrip("\r")
    if len(list_name) == 0:
        list_name = "list.txt"
    PixivListHandler.import_list(sys.modules[__name__], __config__, list_name)


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
            PixivListHandler.import_list(sys.modules[__name__], __config__, 'list.txt')

        if __config__.overwrite:
            msg = 'Overwrite enabled.'
            PixivHelper.print_and_log('info', msg)

        if __config__.dayLastUpdated != 0 and __config__.processFromDb:
            PixivHelper.print_and_log('info', 'Only process members where the last update is >= ' + str(__config__.dayLastUpdated) + ' days ago')

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
