#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import datetime
import gc
import getpass
import os
import platform
import re
import subprocess
import sys
import traceback
from optparse import OptionParser

import colorama
from colorama import Back, Fore, Style

import common.PixivBrowserFactory as PixivBrowserFactory
import common.PixivConfig as PixivConfig
import common.PixivConstant as PixivConstant
import common.PixivHelper as PixivHelper
import handler.PixivArtistHandler as PixivArtistHandler
import handler.PixivBatchHandler as PixivBatchHandler
import handler.PixivBookmarkHandler as PixivBookmarkHandler
import handler.PixivFanboxHandler as PixivFanboxHandler
import handler.PixivImageHandler as PixivImageHandler
import handler.PixivListHandler as PixivListHandler
import handler.PixivNovelHandler as PixivNovelHandler
import handler.PixivRankingHandler as PixivRankingHandler
import handler.PixivSketchHandler as PixivSketchHandler
import handler.PixivTagsHandler as PixivTagsHandler
import model.PixivModelFanbox as PixivModelFanbox
from common.PixivException import PixivException
from model.PixivTags import PixivTags
from PixivDBManager import PixivDBManager

colorama.init()
DEBUG_SKIP_PROCESS_IMAGE = False
DEBUG_SKIP_DOWNLOAD_IMAGE = False

if platform.system() == "Windows":
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
    platform_encoding = 'utf-8-sig'
else:
    platform_encoding = 'utf-8'


script_path = PixivHelper.module_path()

op = ''
ERROR_CODE = 0
UTF8_FS = None

__config__ = PixivConfig.PixivConfig()
configfile = "./config.ini"
__dbManager__ = None
__br__: PixivBrowserFactory.PixivBrowser = None
__blacklistTags = list()
__suppressTags = list()
__log__ = None
__errorList = list()
__blacklistMembers = list()
__blacklistTitles = list()
__valid_options = ()
__seriesDownloaded = []

start_iv = False
dfilename = ""


def header():
    PADDING = 60
    print("┌" + "".ljust(PADDING - 2, "─") + "┐")
    print("│ " + Fore.YELLOW + Back.BLACK + Style.BRIGHT + f"PixivDownloader2 version {PixivConstant.PIXIVUTIL_VERSION}".ljust(PADDING - 3, " ") + Style.RESET_ALL + "│")
    print("│ " + Fore.CYAN + Back.BLACK + Style.BRIGHT + PixivConstant.PIXIVUTIL_LINK.ljust(PADDING - 3, " ") + Style.RESET_ALL + "│")
    print("│ " + Fore.YELLOW + Back.BLACK + Style.BRIGHT + f"Donate at {Fore.CYAN}{Style.BRIGHT}{PixivConstant.PIXIVUTIL_DONATE}".ljust(PADDING + 6, " ") + Style.RESET_ALL + "│")
    print("└" + "".ljust(PADDING - 2, "─") + "┘")


def get_start_and_end_page_from_options(options):
    ''' Try to parse start and end page from options.'''
    page_num = 1
    if options.start_page is not None:
        try:
            page_num = int(options.start_page)
            print(f"Start Page = {page_num}")
        except BaseException:
            print(f"Invalid page number: {options.start_page}")
            raise

    end_page_num = 0
    if options.end_page is not None:
        try:
            end_page_num = int(options.end_page)
            print(f"End Page = {end_page_num}")
        except BaseException:
            print(f"Invalid end page number: {options.end_page}")
            raise
    elif options.number_of_pages is not None:
        end_page_num = options.number_of_pages
    else:
        end_page_num = __config__.numberOfPage

    if page_num > end_page_num and end_page_num != 0:
        print(f"Start Page ({page_num}) is bigger than End Page ({end_page_num}), assuming as page count ({page_num + end_page_num}).")
        end_page_num = page_num + end_page_num

    return page_num, end_page_num


def get_list_file_from_options(options, default_list_file):
    list_file_name = default_list_file
    if options.list_file is not None:
        if os.path.isabs(options.list_file):
            test_file_name = options.list_file
        else:
            test_file_name = __config__.downloadListDirectory + os.sep + options.list_file
        test_file_name = os.path.abspath(test_file_name)
        if os.path.exists(test_file_name):
            list_file_name = test_file_name
        else:
            PixivHelper.print_and_log("warn", f"The given list file [{test_file_name}] doesn't exists, using default list file [{list_file_name}].")

    return list_file_name


def menu():
    PADDING = 60
    set_console_title()
    header()
    print(Style.BRIGHT + '── Pixiv '.ljust(PADDING, "─") + Style.RESET_ALL)
    print(' 1.  Download by member_id')
    print(' 2.  Download by image_id')
    print(' 3.  Download by tags')
    print(' 4.  Download from list')
    print(' 5.  Download from followed artists (/bookmark.php?type=user)')
    print(' 5a. Preheat followed members (fetch profiles and backfill total_images)')
    print(' 5b. Scan local followed artists and mark completed members (new)')
    print(' 6.  Download from bookmarked images (/bookmark.php)')
    print(' 7.  Download from tags list')
    print(' 8.  Download new illust from bookmarked members (/bookmark_new_illust.php)')
    print(' 9.  Download by Title/Caption')
    print(' 10. Download by Tag and Member Id')
    print(' 11. Download Member Bookmark (/bookmark.php?id=)')
    print(' 12. Download by Group Id')
    print(' 13. Download by Manga Series Id')
    print(' 14. Download by Novel Id')
    print(' 15. Download by Novel Series Id')
    print(' 16. Download by Rank')
    print(' 17. Download by Rank R-18')
    print(' 18. Download by New Illusts')
    print(' 19. Download by Unlisted image_id')
    print(Style.BRIGHT + '── FANBOX '.ljust(PADDING, "─") + Style.RESET_ALL)
    print(' f1. Download from supporting list (FANBOX)')
    print(' f2. Download by artist/creator id (FANBOX)')
    print(' f3. Download by post id (FANBOX)')
    print(' f4. Download from following list (FANBOX)')
    print(' f5. Download from custom list (FANBOX)')
    print(' f6. Download Pixiv by FANBOX Artist ID')
    print(Style.BRIGHT + '── Sketch '.ljust(PADDING, "─") + Style.RESET_ALL)
    print(' s1. Download by creator id (Sketch)')
    print(' s2. Download by post id (Sketch)')
    print(Style.BRIGHT + '── Batch Download '.ljust(PADDING, "─") + Style.RESET_ALL)
    print(' b. Batch Download from batch_job.json (experimental)')
    print(Style.BRIGHT + '── Others '.ljust(PADDING, "─") + Style.RESET_ALL)
    print(' d. Manage database')
    print(' l. Export local database.')
    print(' e. Export online followed artist.')
    print(' m. Export online other\'s followed artist.')
    print(' p. Export online image bookmarks.')
    print(' i. Import list file')
    print(' u. Ugoira re-encode')
    print(' r. Reload config.ini')
    print(' c. Print config.ini')
    print(' x. Exit')

    read_lists()

    sel = input('Input: ').rstrip("\r")
    return sel


def menu_download_by_member_id(opisvalid, args, options):
    __log__.info('Member id mode (1).')
    current_member = 1
    page = 1
    end_page = 0
    include_sketch = False
    member_ids = list()

    if opisvalid and len(args) > 0:
        include_sketch = options.include_sketch
        if include_sketch:
            print("Including Pixiv Sketch.")

        (page, end_page) = get_start_and_end_page_from_options(options)

        for member_id in args:
            if member_id.isdigit():
                member_ids.append(int(member_id))
            else:
                print(f"Possible invalid member id = {member_id}")

    else:
        member_ids = input('Member ids: ').rstrip("\r")
        (page, end_page) = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
        skipSketchPrompt = __config__.defaultSketchOption

        if skipSketchPrompt.lower() == 'y':
            print("Including Pixiv Sketch.")
            include_sketch = True
        elif skipSketchPrompt.lower() == 'n':
            print("Excluding Pixiv Sketch.")
        else:
            include_sketch_ask = input('Include Pixiv Sketch [y/n, default is no]? ').rstrip("\r") or 'n'
            if include_sketch_ask.lower() == 'y':
                include_sketch = True

        member_ids = PixivHelper.get_ids_from_csv(member_ids)
        PixivHelper.print_and_log('info', f"Member IDs: {member_ids}")

    for member_id in member_ids:
        try:
            prefix = f"[{current_member} of {len(member_ids)}] "
            PixivArtistHandler.process_member(sys.modules[__name__],
                                                __config__,
                                                member_id,
                                                page=page,
                                                end_page=end_page,
                                                title_prefix=prefix)
            # Issue #793
            if include_sketch:
                # fetching artist token...
                (artist_model, _) = __br__.getMemberPage(member_id)
                prefix = f"[{current_member} ({artist_model.artistToken}) of {len(member_ids)}] "
                PixivSketchHandler.process_sketch_artists(sys.modules[__name__],
                                                            __config__,
                                                            artist_model.artistToken,
                                                            page,
                                                            end_page,
                                                            title_prefix=prefix)

            current_member = current_member + 1
        except PixivException as ex:
            PixivHelper.print_and_log('error', f"Member ID: {member_id} is not valid")
            global ERROR_CODE
            ERROR_CODE = -1
            continue


def menu_download_by_member_bookmark(opisvalid, args, options):
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
                PixivHelper.print_and_log('error', f"Member ID: {member_id} is not valid")
                global ERROR_CODE
                ERROR_CODE = -1
                continue
        if __br__._myId in valid_ids:
            PixivHelper.print_and_log('error', f"Member ID: {__br__._myId} is your own id, use option 6 instead.")
        for mid in valid_ids:
            prefix = f"[{current_member} of {len(valid_ids)}] "
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
        (page, end_page) = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
        if __br__._myId == int(member_id):
            PixivHelper.print_and_log('error', f"Member ID: {member_id} is your own id, use option 6 instead.")
        else:
            PixivArtistHandler.process_member(sys.modules[__name__],
                                              __config__,
                                              member_id.strip(),
                                              page=page,
                                              end_page=end_page,
                                              bookmark=True,
                                              tags=tags)


def menu_download_by_image_id(opisvalid, args, options):
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
                PixivHelper.print_and_log('error', f"Image ID: {image_id} is not valid")
                global ERROR_CODE
                ERROR_CODE = -1
                continue
    else:
        image_ids = input('Image ids: ').rstrip("\r")
        image_ids = PixivHelper.get_ids_from_csv(image_ids)
        for image_id in image_ids:
            PixivImageHandler.process_image(sys.modules[__name__],
                                            __config__,
                                            artist=None,
                                            image_id=int(image_id),
                                            useblacklist=False)


def menu_download_by_tags(opisvalid, args, options):
    __log__.info('Tags mode (3).')
    page = 1
    end_page = 0
    start_date = None
    end_date = None
    bookmark_count = None
    # oldest_first = False
    sort_order = 'date_d'
    wildcard = False
    type_mode = "a"

    if opisvalid and len(args) > 0:
        wildcard = options.use_wildcard_tag
        sort_order = options.tag_sort_order
        start_date = options.start_date
        end_date = options.end_date
        bookmark_count = options.bookmark_count_limit
        (page, end_page) = get_start_and_end_page_from_options(options)
        tags = " ".join(args)
    else:
        tags = input('Tags: ').rstrip("\r")
        bookmark_count = input('Bookmark Count: ').rstrip("\r") or None
        wildcard = input('Use Partial Match (s_tag) [y/n, default is no]: ').rstrip("\r") or 'n'
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False

        # Issue #834
        if __br__._isPremium:
            msg = 'Sorting Order [date_d|date|popular_d|popular_male_d|popular_female_d]? '
            sort_order = input(msg).rstrip("\r") or 'date_d'
        else:
            oldest_first = input('Oldest first[y/n, default is no]: ').rstrip("\r") or 'n'
            if oldest_first.lower() == 'y':
                sort_order = 'date'

        (page, end_page) = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
        (start_date, end_date) = PixivHelper.get_start_and_end_date()

        while True:
            type_mode = input("Search type [a-all|i-Illustration and Ugoira|m-manga, default is all: ").rstrip("\r") or "a"
            if type_mode in {'a', 'i', 'm'}:
                break
            else:
                print("Valid values are 'a', 'i', or 'm'.")

    if bookmark_count is not None and bookmark_count != -1 and len(bookmark_count) > 0:
        bookmark_count = int(bookmark_count)

    PixivTagsHandler.process_tags(sys.modules[__name__],
                                  __config__,
                                  tags.strip(),
                                  page=page,
                                  end_page=end_page,
                                  wild_card=wildcard,
                                  start_date=start_date,
                                  end_date=end_date,
                                  use_tags_as_dir=__config__.useTagsAsDir,
                                  bookmark_count=bookmark_count,
                                  sort_order=sort_order,
                                  type_mode=type_mode)


def menu_download_by_title_caption(opisvalid, args, options):
    __log__.info('Title/Caption mode (9).')
    page = 1
    end_page = 0
    start_date = None
    end_date = None
    if opisvalid and len(args) > 0:
        start_date = options.start_date
        end_date = options.end_date
        (page, end_page) = get_start_and_end_page_from_options(options)
        tags = " ".join(args)
    else:
        tags = input('Title/Caption: ').rstrip("\r")
        (page, end_page) = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
        (start_date, end_date) = PixivHelper.get_start_and_end_date()

    PixivTagsHandler.process_tags(sys.modules[__name__],
                                  __config__,
                                  tags.strip(),
                                  page=page,
                                  end_page=end_page,
                                  wild_card=False,
                                  title_caption=True,
                                  start_date=start_date,
                                  end_date=end_date,
                                  use_tags_as_dir=__config__.useTagsAsDir)


def menu_download_by_tag_and_member_id(opisvalid, args, options):
    __log__.info('Tag and MemberId mode (10).')
    member_id = 0
    tags = None
    page = 1
    end_page = 0

    if opisvalid and len(args) >= 2:
        (page, end_page) = get_start_and_end_page_from_options(options)
        try:
            member_id = int(args[0])
        except BaseException:
            PixivHelper.print_and_log('error', f"Member ID: {member_id} is not valid")
            global ERROR_CODE
            ERROR_CODE = -1
            return

        tags = " ".join(args[1:])
        PixivHelper.safePrint(f"Looking tags: {tags} from memberId: {member_id}")
    else:
        member_id = input('Member Id: ').rstrip("\r")
        tags = input('Tag      : ').rstrip("\r")
        (page, end_page) = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)

    PixivTagsHandler.process_tags(sys.modules[__name__],
                                  __config__,
                                  tags.strip(),
                                  page=page,
                                  end_page=end_page,
                                  use_tags_as_dir=__config__.useTagsAsDir,
                                  member_id=int(member_id))


def menu_download_from_list(opisvalid, args, options):
    __log__.info('Batch mode from list (4).')
    global op
    global __config__
    include_sketch = False

    list_file_name = __config__.downloadListDirectory + os.sep + 'list.txt'
    tags = None
    if opisvalid:
        include_sketch = options.include_sketch
        list_file_name = get_list_file_from_options(options, list_file_name)
        # get one tag from input parameter
        if len(args) > 0:
            tags = args[0]
    else:
        test_tags = input('Tag : ').rstrip("\r")
        include_sketch_ask = input('Include Pixiv Sketch [y/n, default is no]? ').rstrip("\r") or 'n'
        if include_sketch_ask.lower() == 'y':
            include_sketch = True
        if len(test_tags) > 0:
            tags = test_tags

    PixivListHandler.process_list(sys.modules[__name__],
                                  __config__,
                                  list_file_name=list_file_name,
                                  tags=tags,
                                  include_sketch=include_sketch)


def menu_download_from_online_user_bookmark(opisvalid, args, options):
    __log__.info('User Bookmarked Artist mode (5).')
    start_page = 1
    end_page = 0
    hide = 'n'
    bookmark_count = None

    if opisvalid:
        if options.bookmark_flag is not None:
            hide = options.bookmark_flag.lower()
            if hide not in ('y', 'n', 'o'):
                PixivHelper.print_and_log("error", f"Invalid args for bookmark_flag: {args}, valid values are [y/n/o].")
                return
            (start_page, end_page) = get_start_and_end_page_from_options(options)
            bookmark_count = options.bookmark_count_limit
    else:
        arg = input("Include Private bookmarks [y/n/o, default is no]: ").rstrip("\r") or 'n'
        arg = arg.lower()
        if arg == 'y' or arg == 'n' or arg == 'o':
            hide = arg
        else:
            print("Invalid args: ", arg)
            return
        (start_page, end_page) = PixivHelper.get_start_and_end_number(total_number_of_page=options.number_of_pages)
        bookmark_count = input('Bookmark Count: ').rstrip("\r") or None

    if bookmark_count is not None and bookmark_count != -1 and len(bookmark_count) > 0:
        bookmark_count = int(bookmark_count)

    PixivBookmarkHandler.process_bookmark(sys.modules[__name__],
                                          __config__,
                                          hide,
                                          start_page,
                                          end_page,
                                          bookmark_count=bookmark_count)


def menu_preheat_followed_members(opisvalid, args, options):
    __log__.info('Preheat followed members (5a).')
    list_file = None
    hide = 'n'
    if opisvalid and len(args) > 0:
        list_file = args[0]
    else:
        list_file = input('Followed list file (leave blank to use config.followedArtistListFile): ').rstrip('\r') or None
        arg = input("Include Private followed artists [y/n, default is no]: ").rstrip('\r') or 'n'
        if arg.lower() in ('y', 'n', 'o'):
            hide = arg.lower()
        else:
            print("Invalid arg, using public only.")

    # optional override for delay
    try:
        delay = float(input(f"Preheat delay seconds (press Enter to use config or default {__config__.preheatDelaySeconds if hasattr(__config__, 'preheatDelaySeconds') else __config__.preheatDelay}): ").strip() or 0)
    except Exception:
        delay = None

    progress_file = None
    if delay is not None and delay > 0:
        PixivBookmarkHandler.preheat_followed_members(sys.modules[__name__], __config__, list_file=list_file, hide=hide, delay_seconds=delay, progress_file=progress_file)
    else:
        PixivBookmarkHandler.preheat_followed_members(sys.modules[__name__], __config__, list_file=list_file, hide=hide, progress_file=progress_file)


# New menu handler for scanning local folders and marking completed members
def menu_scan_and_mark_complete(opisvalid, args, options):
    __log__.info('Scan local followed artists and mark completed (5b).')
    list_file = None
    if opisvalid and len(args) > 0:
        list_file = args[0]
    else:
        list_file = input('Followed list file (leave blank to use config.followedArtistListFile): ').rstrip('\\r') or None

    progress_file = input('Progress file to write (leave blank to use <list_file>.preheat_progress.json): ').rstrip('\\r') or None

    print("\\n--- Scanning Parameters ---")
    compare_remote_in = input('Compare against remote (fetch remote IDs / update DB total_images)? [Y/n]: ').rstrip('\\r') or 'y'
    compare_remote_flag = (compare_remote_in.lower() != 'n')

    # 只有 compare_remote=True 时才允许下载缺失（需要 remote_ids 才能安全下载）
    if compare_remote_flag:
        download_missing_in = input('Download missing images (requires remote IDs)? [Y/n]: ').rstrip('\\r') or 'y'
        download_missing_flag = (download_missing_in.lower() != 'n')
    else:
        print('Note: Remote compare disabled => will NOT download missing images (no remote IDs).')
        download_missing_flag = False

    print("\\nIMPORTANT: To generate progress/completion marker file, answer YES to execute (default).")
    print("           Answer NO only if you want to preview without saving.")
    execute_in = input('Execute and save progress file? [Y/n]: ').rstrip('\\r') or 'y'

    download_limit_in = input('Download limit per member (blank = no limit): ').rstrip('\\r')
    download_limit = None
    if download_limit_in.strip():
        try:
            download_limit = int(download_limit_in.strip())
        except Exception:
            PixivHelper.print_and_log('warn', f'Invalid download_limit: {download_limit_in}, using no limit.')
            download_limit = None

    # candidate set selection (simple names as in config)
    valid_candidates = [
        'downloaded','followed','remote','downloaded_and_remote',
        'followed_not_done','downloaded_not_done','remote_not_downloaded','done'
    ]
    default_candidate = getattr(__config__, 'menu5CandidateSet', 'downloaded')
    candidate_in = input(f"Candidate set [{default_candidate}]: ").rstrip('\r') or default_candidate
    if candidate_in not in valid_candidates:
        PixivHelper.print_and_log('warn', f'Invalid candidate set: {candidate_in}, using default: {default_candidate}')
        candidate_in = default_candidate

    compare_remote_flag = (compare_remote_in.lower() != 'n')
    # FIX: dry_run should be True ONLY when user says 'n' (no execution)
    # Default and 'y' = execute (dry_run=False)
    # 'n' = preview only (dry_run=True)
    dry_run_flag = (execute_in.lower() == 'n')
    download_missing_flag = (download_missing_in.lower() != 'n')

    PixivBookmarkHandler.scan_and_mark_completed_members(
        sys.modules[__name__],
        __config__,
        list_file=list_file,
        progress_file=progress_file,
        compare_remote=compare_remote_flag,
        dry_run=dry_run_flag,
        download_missing=download_missing_flag,
        download_limit=download_limit,
        candidate_set=candidate_in,
    )


def menu_download_by_rank(op_is_valid, args, options, valid_modes=None):
    if valid_modes is None:
        __log__.info('Download Ranking by Post ID mode (15).')
        valid_modes = ["daily", "weekly", "monthly", "rookie", "original", "male", "female"]
    valid_contents = ["all", "illust", "ugoira", "manga"]
    mode = ""
    date = ""
    content = "all"
    start_page = 1
    end_page = 0

    if op_is_valid and len(args) > 0:
        (start_page, end_page) = get_start_and_end_page_from_options(options)
        mode = options.rank_mode
        if mode not in valid_modes:
            print(f"Invalid mode: {mode}, valid modes are {', '.join(valid_modes)}.")
        content = options.rank_content
        if content not in valid_contents:
            print(f"Invalid type: {content}, valid content types are {', '.join(valid_contents)}.")
    else:
        while True:
            print(f"Valid Modes are: {', '.join(valid_modes)}")
            mode = input('Mode: ').rstrip("\r").lower()
            if mode in valid_modes:
                break
            else:
                print("Invalid mode.")
        while True:
            print(f"Valid Content Types are: {', '.join(valid_contents)}")
            content = input('Type: ').rstrip("\r").lower()
            if content in valid_contents:
                break
            else:
                print("Invalid Content Type.")
        while True:
            print(f"Specify the ranking date, valid type is YYYYMMDD (default: today)")
            date = input('Date: ').rstrip("\r").lower()
            try:
                if date != '':
                    datetime.datetime.strptime(date, "%Y%m%d")
            except Exception as ex:
                PixivHelper.print_and_log("error", f"Invalid format for ranking date: {date}.")
            else:
                break
        (start_page, end_page) = PixivHelper.get_start_and_end_number()

    PixivRankingHandler.process_ranking(sys.modules[__name__],
                                        __config__,
                                        mode,
                                        content,
                                        start_page,
                                        end_page,
                                        date=date,
                                        filter=None)


def menu_download_by_rank_r18(op_is_valid, args, options):
    __log__.info('Download R-18 Ranking by Post ID mode (16).')
    valid_modes = ["daily_r18", "weekly_r18", "male_r18", "female_r18"]
    menu_download_by_rank(op_is_valid, args, options, valid_modes)


def menu_download_new_illusts(op_is_valid, args, options):
    __log__.info('Download New Illust mode (17).')
    valid_modes = ["illust", "manga"]
    type_mode = "illusts"
    max_page = 0

    if op_is_valid and len(args) > 0:
        mode = options.rank_mode
        if mode not in valid_modes:
            print(f"Invalid mode: {mode}, valid modes are {', '.join(valid_modes)}.")
        max_page = options.end_page
    else:
        while True:
            print(f"Valid Modes are: {', '.join(valid_modes)}")
            type_mode = input('Mode: ').rstrip("\r").lower()
            if type_mode in valid_modes:
                break
            else:
                print("Invalid mode.")
        max_page = int(input('Max Page: ').rstrip("\r").lower()) or 0

    PixivRankingHandler.process_new_illusts(sys.modules[__name__],
                                            __config__,
                                            type_mode,
                                            max_page)


def menu_reload_config():
    __log__.info('Manual Reload Config (r).')
    __config__.loadConfig(path=configfile)


def menu_print_config():
    __log__.info('Print Current Config (p).')
    __config__.printConfig()


def set_console_title(title=''):
    set_title = f'PixivDownloader {PixivConstant.PIXIVUTIL_VERSION} {title}'
    PixivHelper.set_console_title(set_title)


def setup_option_parser():

    global __valid_options
    __valid_options = ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19',
                       'f1', 'f2', 'f3', 'f4', 'f5',
                       's1', 's2',
                       'l', 'd', 'e', 'm', 'b', 'p', 'c')
    parser = OptionParser()

    # need to keep the whitespace to adjust the output for --help
    parser.add_option('-s', '--start_action', dest='start_action',
                      help='''Action you want to load your program with:          \n
1  - Download by member_id                          \n
2  - Download by image_id                           \n
3  - Download by tags                               \n
4  - Download from list                             \n
5  - Download from user bookmark                    \n
6  - Download from user's image bookmark            \n
7  - Download from tags list                        \n
8  - Download new illust from bookmark              \n
9  - Download by Title/Caption                      \n
10 - Download by Tag and Member Id                  \n
11 - Download images from Member Bookmark           \n
12 - Download images by Group Id                    \n
f1 - Download from supporting list (FANBOX)         \n
f2 - Download by artist/creator id (FANBOX)         \n
f3 - Download by post id (FANBOX)                   \n
f4 - Download from following list (FANBOX)          \n
f5 - Download from custom list (FANBOX)             \n
s1 - Download by creator id (Sketch)')              \n
s2 - Download by post id (Sketch)')                 \n
b  - Batch Download from batch_job.json             \n
l  - Export local database (image_id)               \n
e  - Export online bookmark                         \n
m  - Export online user bookmark                    \n
p  - Export online image bookmark                   \n
d  - Manage database''')
    parser.add_option('-x', '--exit_when_done',
                      dest='exit_when_done',
                      default=False,
                      help='Exit program when done. (only useful when not using DB-Manager)',
                      action='store_true')
    parser.add_option('-i', '--irfanview',
                      dest='start_iv',
                      default=False,
                      help='Start IrfanView after downloading images using downloaded_on_%date%.txt',
                      action='store_true')
    parser.add_option('-n', '--number_of_pages',
                      dest='number_of_pages',
                      help='Temporarily overwrites numberOfPage set in config.ini')
    parser.add_option('-c', '--config', dest='configlocation',
                      default=None,
                      help='Load the config file from a custom location')
    parser.add_option('--bf', '--batch_file',
                      dest='batch_file',
                      default=None,
                      help='Json file for batch job (b).')
    parser.add_option('--sp', '--start_page',
                      dest='start_page',
                      default=None,
                      help='''Starting page in integer.                             \n
Used in option 1, 3, 5, 6, 7, 8, 9, and 10.''')
    parser.add_option('--ep', '--end_page',
                      dest='end_page',
                      default=None,
                      help='''End page in integer.                                  \n
If start page is given and it is larger than end page, it will be assumed as
number of page instead (start page + end page).
This take priority from '-n', '--number_of_pages' for calculation.
Used in option 1, 3, 5, 6, 7, 8, 9, and 10.
See get_start_and_end_page_from_options()''')
    parser.add_option('--is', '--include_sketch',
                      dest='include_sketch',
                      default=False,
                      action='store_true',
                      help='''Include Pixiv Sketch when processing member id (1). Default is False.''')
    parser.add_option('--wt', '--use_wildcard_tag',
                      dest='use_wildcard_tag',
                      default=False,
                      help='Use wildcard when downloading by tag (3) or tag list (7). Default is False.',
                      action='store_true')
    parser.add_option('-f', '--list_file',
                      dest='list_file',
                      default=None,
                      help='''List file for download by list (4) or tag list (7).   \n
If using relative path, it will be prefixed with [downloadlistdirectory] in config.ini.''')
    parser.add_option('-p', '--bookmark_flag',
                      dest='bookmark_flag',
                      default=None,
                      help='''Include private bookmark flag for option 5 and 6.     \n
 y - include private bookmark.                      \n
 n - don't include private bookmark.                \n
 o - only get from private bookmark.''')
    parser.add_option('-o', '--sort_order',
                      dest='sort_order',
                      default=None,
                      help='''Sorting order for option 6.                           \n
 asc - sort by bookmark.                            \n
 desc - sort by bookmark in descending order.       \n
 date - sort by date.                               \n
 date_d - sort by date in descending order.''')

    parser.add_option('--tag_sort_order',
                      dest='tag_sort_order',
                      default='date_d',
                      help='''Sorting order for option 3 and 7.                     \n
 date - sort by date.                               \n
 date_d - sort by date in descending order.         \n
 PREMIUM ONLY:                                      \n
 popular_d - overall popularity                     \n
 popular_male_d - popular among male users          \n
 popular_female_d - popular among female users''')

    parser.add_option('--start_date',
                      dest='start_date',
                      default=None,
                      help='''Start Date for option 3, 7 and 9.                     \n
 Format must follow YYYY-MM-DD.''')
    parser.add_option('--end_date',
                      dest='end_date',
                      default=None,
                      help='''End Date for option 3, 7 and 9.                       \n
 Format must follow YYYY-MM-DD.''')
    parser.add_option('--uit', '--use_image_tag',
                      dest='use_image_tag',
                      default=False,
                      action='store_true',
                      help='''Use Image Tag for filtering in option (6). Default is False.''')
    parser.add_option('--bcl', '--bookmark_count_limit',
                      dest='bookmark_count_limit',
                      default=-1,
                      help='''Bookmark count limit in integer.                       \n
Used in option 3, 5, 7, and 8.''')
    parser.add_option('--rm', '--rank_mode',
                      dest='rank_mode',
                      default="daily",
                      help='''Ranking Mode.''')
    parser.add_option('--rc', '--rank_content',
                      dest='rank_content',
                      default="all",
                      help='''Ranking Content Type.''')
    parser.add_option('--ef', '--export_filename',
                      dest='export_filename',
                      default="export.txt",
                      help='''Filename for exporting members/images.                    \n
Used in option e, m, p''')
    parser.add_option('--up', '--use_pixiv',
                      dest='use_pixiv',
                      default=None,
                      help='''Use Pixiv table for export.                               \n
 y - include pixiv database.                        \n
 n - don't include pixiv database.                     \n
 o - only export pixiv database.''')
    parser.add_option('--uf', '--use_fanbox',
                      dest='use_fanbox',
                      default=None,
                      help='''Use Fanbox table for export.                              \n
 y - include fanbox database.                       \n
 n - don't include fanbox database.                 \n
 o - only export fanbox database.''')
    parser.add_option('--us', '--use_sketch',
                      dest='use_sketch',
                      default=None,
                      help='''Use Sketch table for export.                              \n
 y - include sketch database.                       \n
 n - don't include sketch database.                 \n
 o - only export sketch database.''')
    parser.add_option('--db-file', dest='db_file', help='Use a specific sqlite DB file for this run (overrides config dbPath)')
    return parser


# Main thread #
def main_loop(ewd, op_is_valid, selection, np_is_valid_local, args, options):
    global __errorList
    global ERROR_CODE

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
                menu_download_by_member_id(op_is_valid, args, options)
            elif selection == '2':
                menu_download_by_image_id(op_is_valid, args, options)
            elif selection == '3':
                menu_download_by_tags(op_is_valid, args, options)
            elif selection == '4':
                menu_download_from_list(op_is_valid, args, options)
            elif selection == '5':
                menu_download_from_online_user_bookmark(op_is_valid, args, options)
            elif selection == '6':
                menu_download_from_online_image_bookmark(op_is_valid, args, options)
            elif selection == '7':
                menu_download_from_tags_list(op_is_valid, args, options)
            elif selection == '8':
                menu_download_new_illust_from_bookmark(op_is_valid, args, options)
            elif selection == '9':
                menu_download_by_title_caption(op_is_valid, args, options)
            elif selection == '10':
                menu_download_by_tag_and_member_id(op_is_valid, args, options)
            elif selection == '11':
                menu_download_by_member_bookmark(op_is_valid, args, options)
            elif selection == '12':
                menu_download_by_group_id(op_is_valid, args, options)
            elif selection == '13':
                menu_download_by_manga_series_id(op_is_valid, args, options)
            elif selection == '14':
                menu_download_by_novel_id(op_is_valid, args, options)
            elif selection == '15':
                menu_download_by_novel_series_id(op_is_valid, args, options)
            elif selection == '16':
                menu_download_by_rank(op_is_valid, args, options)
            elif selection == '17':
                menu_download_by_rank_r18(op_is_valid, args, options)
            elif selection == '18':
                menu_download_new_illusts(op_is_valid, args, options)
            elif selection == '19':
                menu_download_by_unlisted_image_id(op_is_valid, args, options)
            elif selection == "l":
                menu_export_database_images(op_is_valid, args, options)
            elif selection == 'b':
                PixivBatchHandler.process_batch_job(sys.modules[__name__], batch_file=options.batch_file)
            elif selection == 'e':
                menu_export_online_bookmark(op_is_valid, args, options)
            elif selection == 'm':
                menu_export_online_user_bookmark(op_is_valid, args, options)
            elif selection == 'p':
                menu_export_from_online_image_bookmark(op_is_valid, args, options)
            elif selection == 'u':
                menu_ugoira_reencode(op_is_valid, args, options)
            elif selection == 'd':
                PixivHelper.clearScreen()
                __dbManager__.main()
            elif selection == 'r':
                menu_reload_config()
            elif selection == 'c':
                menu_print_config()
            elif selection == 'i':
                menu_import_list()
            elif selection == '5a':
                menu_preheat_followed_members(op_is_valid, args, options)
            elif selection == '5b':
                menu_scan_and_mark_complete(op_is_valid, args, options)

            # PIXIV FANBOX
            elif selection == 'f1':
                menu_fanbox_download_from_list(op_is_valid, PixivModelFanbox.FanboxArtist.SUPPORTING, args, options)
            elif selection == 'f2':
                menu_fanbox_download_by_id(op_is_valid, args, options)
            elif selection == 'f3':
                menu_fanbox_download_by_post_id(op_is_valid, args, options)
            elif selection == 'f4':
                menu_fanbox_download_from_list(op_is_valid, PixivModelFanbox.FanboxArtist.FOLLOWING, args, options)
            elif selection == 'f5':
                menu_fanbox_download_from_list(op_is_valid, PixivModelFanbox.FanboxArtist.CUSTOM, args, options)
            elif selection == 'f6':
                menu_fanbox_download_pixiv_by_fanbox_id(op_is_valid, args, options)
            # END PIXIV FANBOX
            # PIXIV Sketch
            elif selection == 's1':
                menu_sketch_download_by_artist_id(op_is_valid, args, options)
            elif selection == 's2':
                menu_sketch_download_by_post_id(op_is_valid, args, options)
            # END PIXIV Sketch
            elif selection == '-all':
                if not np_is_valid_local:
                    np_is_valid_local = True
                    options.number_of_pages = 0
                    print('download all mode activated')
                else:
                    np_is_valid_local = False
                    print(f'download mode reset to {__config__.numberOfPage} pages')
            elif selection == 'x':
                break

            if ewd:  # Yavos: added lines for "exit when done"
                break
            op_is_valid = False  # Yavos: needed to prevent endless loop
        except KeyboardInterrupt:
            PixivHelper.print_and_log("info", f"Keyboard Interrupt pressed, selection: {selection}")
            PixivHelper.clearScreen()
            print("Restarting...")
            selection = menu()
        except EOFError:
            selection = 'x'
            break
        except PixivException as ex:
            if ex.htmlPage is not None:
                filename = f"Dump for {PixivHelper.sanitize_filename(ex.value)}.html"
                PixivHelper.dump_html(filename, ex.htmlPage)
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

        # if not result:
        #     result = __br__.login(username, password)

    except BaseException:
        PixivHelper.print_and_log('error', f'Error at doLogin(): {sys.exc_info()}')
        PixivHelper.print_and_log('error', f'{traceback.format_exc()}')
        raise PixivException("Cannot Login!", PixivException.CANNOT_LOGIN)
    return result


def menu_import_list():
    __log__.info('Import List mode (i).')
    list_name = input("List filename = ").rstrip("\r")
    if len(list_name) == 0:
        list_name = "list.txt"
    PixivListHandler.import_list(sys.modules[__name__], __config__, list_name)


def read_lists():
    # Implement #797
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


def main():
    set_console_title()
    header()

    # Option Parser
    global start_iv  # used in download_image
    global dfilename
    global op
    global __br__
    global configfile
    global ERROR_CODE
    global __dbManager__
    global __valid_options
    global __log__

    parser = setup_option_parser()
    (options, args) = parser.parse_args()

    op = options.start_action
    if op in __valid_options:
        op_is_valid = True
    elif op is None:
        op_is_valid = False
    else:
        op_is_valid = False
        parser.error('%s is not valid operation' % op)
        # Yavos: use print option instead when program should be running even with this error

    ewd = options.exit_when_done
    configfile = options.configlocation

    try:
        if options.number_of_pages is not None:
            options.number_of_pages = int(options.number_of_pages)
            np_is_valid = True
        else:
            np_is_valid = False
    except BaseException:
        np_is_valid = False
        parser.error('Value %s used for numberOfPage is not an integer.' % options.number_of_pages)
        # Yavos: use print option instead when program should be running even with this error
        # end new lines by Yavos

    # load the configuration before start using logging!
    try:
        __config__.loadConfig(path=configfile)
        PixivHelper.set_config(__config__)
        __log__ = PixivHelper.get_logger(reload=True)
    except BaseException:
        PixivHelper.print_and_log("error", f'Failed to read configuration from {configfile}.')

    __log__.info('###############################################################')
    if len(sys.argv) == 0:
        __log__.info('Starting with no argument..')
    else:
        __log__.info('Starting with argument: [%s].', " ".join(sys.argv))

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

    if __config__.enablePostProcessing and len(__config__.postProcessingCmd) > 0:
        PixivHelper.print_and_log("warn", f"Post Processing after download is enabled: {__config__.postProcessingCmd}")

    try:
        # if CLI provided db_file, override config dbPath
        if getattr(options, 'db_file', None):
            __config__.dbPath = options.db_file
        # support folderDatabase placeholder
        if getattr(__config__, 'folderDatabase', None):
            fd = str(__config__.folderDatabase)
            fd = fd.replace('{rootDirectory}', __config__.rootDirectory)
            if fd:
                __config__.dbPath = fd

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

        read_lists()

        # check ffmpeg if ugoira conversion is enabled
        if __config__.createGif or \
           __config__.createApng or \
           __config__.createWebm or \
           __config__.createWebp:

            # if not os.path.exists(os.path.abspath(__config__.ffmpeg)):
            #     raise PixivException(f"Cannot find ffmpeg executables at {os.path.abspath(__config__.ffmpeg)}, please update the path (including.exe) in config.ini")

            import shlex
            cmd = f"{__config__.ffmpeg} -encoders"
            ffmpeg_args = shlex.split(cmd, posix=False)
            try:
                p = subprocess.run(ffmpeg_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, check=True)
                buff = p.stdout
                if buff.find(__config__.ffmpegCodec) == 0:
                    __config__.createWebm = False
                    PixivHelper.print_and_log('error', f'{"#" * 80}')
                    PixivHelper.print_and_log('error', f'Missing {__config__.ffmpegCodec} encoder, createWebm disabled.')
                    PixivHelper.print_and_log('error', f'Command used: {cmd}')
                    PixivHelper.print_and_log('info', f'Please download ffmpeg with {__config__.ffmpegCodec} encoder enabled.')
                    PixivHelper.print_and_log('error', f'{"#" * 80}')
                if p.returncode != 0:
                    PixivHelper.print_and_log('warn', f'Failed to run ffmpeg succesfully, returned exit code = {p.returncode}, expected to return 0.')
            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                PixivHelper.print_and_log('error', f'{"#" * 80}')
                PixivHelper.print_and_log('error', f'Failed to load ffmpeg: {exc_value}')
                PixivHelper.print_and_log('error', f'Command used: [{cmd}]')
                ffmpeg_url = Back.LIGHTWHITE_EX + Fore.BLUE + "https://ffmpeg.org/download.html#get-packages" + Style.RESET_ALL
                PixivHelper.print_and_log('info', f'Please update your config.ini and/or download latest ffmpeg executables from {ffmpeg_url}.')
                PixivHelper.print_and_log('error', f'{"#" * 80}')
                return

        if __config__.useLocalTimezone:
            PixivHelper.print_and_log("info", f"Using local timezone: {PixivHelper.LocalUTCOffsetTimezone()}")

        print(f"{Fore.RED}{Style.BRIGHT}Username login is broken, use Cookies to log in.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{Style.BRIGHT}See Q3. at {Fore.CYAN}{Style.BRIGHT}https://github.com/Nandaka/PixivUtil2?tab=readme-ov-file#a-usage{Style.RESET_ALL}")

        username = __config__.username
        password = __config__.password
        if not username or not password:
            print(f"{Fore.RED}{Style.BRIGHT}No username and/or password found in config.ini{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{Style.BRIGHT}See {Fore.CYAN}{Style.BRIGHT}https://github.com/Nandaka/PixivUtil2?tab=readme-ov-file#authentication{Style.RESET_ALL}")

        if np_is_valid and options.number_of_pages != 0:  # Yavos: overwrite config-data
            PixivHelper.print_and_log("info", f'Limit up to: {options.number_of_pages} page(s). (set via commandline)')
        elif __config__.numberOfPage != 0:
            PixivHelper.print_and_log("info", f'Limit up to: {__config__.numberOfPage} page(s).')

        result = doLogin(password, username)

        if result:
            np_is_valid, op_is_valid, selection = main_loop(ewd, op_is_valid, selection, np_is_valid, args, options)

            if start_iv:  # Yavos: adding start_irfan_view-handling
                PixivHelper.start_irfanview(dfilename, __config__.IrfanViewPath, start_irfan_slide, start_irfan_view)
        else:
            ERROR_CODE = PixivException.NOT_LOGGED_IN
    except PixivException as pex:
        PixivHelper.print_and_log('error', pex.message)
        ERROR_CODE = pex.errorCode
    except Exception as ex:
        if __config__.logLevel == "DEBUG":
            import traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            __log__.exception('Unknown Error: %s', str(exc_value))
        PixivHelper.print_and_log("error", f"Unknown Error, please check the log file: {sys.exc_info()}")
        ERROR_CODE = getattr(ex, 'errorCode', -1)
    finally:
        __dbManager__.close()
        if not ewd:  # Yavos: prevent input on exit_when_done
            if selection is None or selection != 'x':
                input('press enter to exit.').rstrip("\r")
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
