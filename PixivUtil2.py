#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302, W0602, W0603, W0703, R0102, R1702, R0912, R0915


import codecs
import datetime
import gc
import getpass
import http.client
import mechanize
import os
import random
import re
import subprocess
import sys
import time
import traceback
import urllib.request, urllib.error, urllib.parse
from bs4 import BeautifulSoup
from optparse import OptionParser

import datetime_z
import PixivBrowserFactory
import PixivConfig
import PixivConstant
import PixivDBManager
import PixivHelper
import PixivModelFanbox
from PixivException import PixivException
from PixivModel import (PixivBookmark, PixivGroup, PixivImage, PixivListItem,
                        PixivNewIllustBookmark, PixivTags)

try:
    stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
    reload(sys)
    sys.stdin, sys.stdout, sys.stderr = stdin, stdout, stderr
    sys.setdefaultencoding("utf-8")
except Exception as e:
    pass  # swallow the exception

if os.name == 'nt':
    # enable unicode support on windows console.
    import win_unicode_console

    # monkey patch for #305
    from ctypes import byref, c_ulong
    from win_unicode_console.streams import set_last_error, ERROR_SUCCESS, ReadConsoleW, get_last_error, ERROR_OPERATION_ABORTED, WinError
    from win_unicode_console.buffer import get_buffer
    EOF = b"\x1a\x00"

    def readinto_patch(self, b):
        bytes_to_be_read = len(b)
        if not bytes_to_be_read:
            return 0
        elif bytes_to_be_read % 2:
            raise ValueError("cannot read odd number of bytes from UTF-16-LE encoded console")

        buffers = get_buffer(b, writable=True)
        code_units_to_be_read = bytes_to_be_read // 2
        code_units_read = c_ulong()

        set_last_error(ERROR_SUCCESS)
        ReadConsoleW(self.handle, buffers, code_units_to_be_read, byref(code_units_read), None)
        last_error = get_last_error()
        if last_error == ERROR_OPERATION_ABORTED:
            time.sleep(0.1)  # wait for KeyboardInterrupt
        if last_error != ERROR_SUCCESS:
            raise WinError(last_error)

        if buffers[:len(EOF)] == EOF:
            return 0
        else:
            return 2 * code_units_read.value  # bytes read

    win_unicode_console.streams.WindowsConsoleRawReader.readinto = readinto_patch
    win_unicode_console.enable()

    # patch getpass.getpass() for windows to show '*'
    def win_getpass_with_mask(prompt='Password: ', stream=None):
        """Prompt for password with echo off, using Windows getch()."""
        if sys.stdin is not sys.__stdin__:
            return getpass.fallback_getpass(prompt, stream)
        import msvcrt
        for c in prompt:
            msvcrt.putch(c)
        pw = ""
        while 1:
            c = msvcrt.getch()
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
        msvcrt.putch('\r')
        msvcrt.putch('\n')
        return pw

    getpass.getpass = win_getpass_with_mask

script_path = PixivHelper.module_path()

np_is_valid = False
np = 0
op = ''
DEBUG_SKIP_PROCESS_IMAGE = False
ERROR_CODE = 0

gc.enable()
# gc.set_debug(gc.DEBUG_LEAK)

# replace unenscape_charref implementation with our implementation due to bug.
mechanize._html.unescape_charref = PixivHelper.unescape_charref

__config__ = PixivConfig.PixivConfig()
configfile = "config.ini"
__dbManager__ = None
__br__ = None
__blacklistTags = list()
__suppressTags = list()
__log__ = PixivHelper.GetLogger()
__errorList = list()
__blacklistMembers = list()
__valid_options = ()

start_iv = False
dfilename = ""

# http://www.pixiv.net/member_illust.php?mode=medium&illust_id=18830248
__re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
__re_manga_page = re.compile(r'(\d+(_big)?_p\d+)')


# issue #299
def get_remote_filesize(url, referer):
    print('Getting remote filesize...')
    # open with HEAD method, might be expensive
    req = PixivHelper.create_custom_request(url, __config__, referer, head=True)
    try:
        res = __br__.open_novisit(req)
        file_size = int(res.info()['Content-Length'])
    except KeyError:
        file_size = -1
        PixivHelper.print_and_log('info', "\tNo file size information!")
    except mechanize.HTTPError as e:
        # fix Issue #503
        # handle http errors explicit by code
        if int(e.code) in (404, 500):
            file_size = -1
            PixivHelper.print_and_log('info', "\tNo file size information!")
        else:
            raise

    print("Remote filesize = {0} ({1} Bytes)".format(PixivHelper.sizeInStr(file_size), file_size))
    return file_size


# -T04------For download file
def download_image(url, filename, referer, overwrite, max_retry, backup_old_file=False, image=None, page=None):
    '''return download result and filename if ok'''
    global ERROR_CODE
    temp_error_code = None
    retry_count = 0
    while retry_count <= max_retry:
        res = None
        req = None
        try:
            try:
                if not overwrite and not __config__.alwaysCheckFileSize:
                    print('\rChecking local filename...', end=' ')
                    if os.path.exists(filename) and os.path.isfile(filename):
                        PixivHelper.print_and_log('info', "\rLocal file exists: {0}".format(filename.encode('utf-8')))
                        return (PixivConstant.PIXIVUTIL_SKIP_DUPLICATE, filename)

                file_size = get_remote_filesize(url, referer)

                # check if existing ugoira file exists
                if filename.endswith(".zip"):
                    # non-converted zip (no animation.json)
                    if os.path.exists(filename) and os.path.isfile(filename):
                        old_size = os.path.getsize(filename)
                        # update for #451, always return identical?
                        check_result = PixivHelper.checkFileExists(overwrite, filename, file_size, old_size, backup_old_file)
                        if __config__.createUgoira:
                            handle_ugoira(image, filename)
                        return (check_result, filename)
                    # converted to ugoira (has animation.json)
                    ugo_name = filename[:-4] + ".ugoira"
                    if os.path.exists(ugo_name) and os.path.isfile(ugo_name):
                        old_size = PixivHelper.getUgoiraSize(ugo_name)
                        check_result = PixivHelper.checkFileExists(overwrite, ugo_name, file_size, old_size, backup_old_file)
                        if check_result != PixivConstant.PIXIVUTIL_OK:
                            # try to convert existing file.
                            handle_ugoira(image, filename)

                            return (check_result, filename)
                elif os.path.exists(filename) and os.path.isfile(filename):
                    # other image? files
                    old_size = os.path.getsize(filename)
                    check_result = PixivHelper.checkFileExists(overwrite, filename, file_size, old_size, backup_old_file)
                    if check_result != PixivConstant.PIXIVUTIL_OK:
                        return (check_result, filename)

                # check based on filename stored in DB using image id
                if image is not None:
                    db_filename = None
                    if page is not None:
                        row = __dbManager__.selectImageByImageIdAndPage(image.imageId, page)
                        if row is not None:
                            db_filename = row[2]
                    else:
                        row = __dbManager__.selectImageByImageId(image.imageId)
                        if row is not None:
                            db_filename = row[3]
                    if db_filename is not None and os.path.exists(db_filename) and os.path.isfile(db_filename):
                        old_size = os.path.getsize(db_filename)
                        if file_size < 0:
                            file_size = get_remote_filesize(url, referer)
                        check_result = PixivHelper.checkFileExists(overwrite, db_filename, file_size, old_size, backup_old_file)
                        if check_result != PixivConstant.PIXIVUTIL_OK:
                            ugo_name = None
                            if db_filename.endswith(".zip"):
                                ugo_name = filename[:-4] + ".ugoira"
                                if __config__.createUgoira:
                                    handle_ugoira(image, db_filename)
                            if db_filename.endswith(".ugoira"):
                                ugo_name = db_filename
                                handle_ugoira(image, db_filename)

                            return (check_result, db_filename)

                # actual download
                (downloadedSize, filename) = perform_download(url, file_size, filename, overwrite, referer)
                # set last-modified and last-accessed timestamp
                if image is not None and __config__.setLastModified and filename is not None and os.path.isfile(filename):
                    ts = time.mktime(image.worksDateDateTime.timetuple())
                    os.utime(filename, (ts, ts))

                # check the downloaded file size again
                if file_size > 0 and downloadedSize != file_size:
                    raise PixivException("Incomplete Downloaded for {0}".format(url), PixivException.DOWNLOAD_FAILED_OTHER)
                elif __config__.verifyImage and (filename.endswith(".jpg") or filename.endswith(".png") or filename.endswith(".gif")):
                    fp = None
                    try:
                        from PIL import Image, ImageFile
                        fp = open(filename, "rb")
                        # Fix Issue #269, refer to https://stackoverflow.com/a/42682508
                        ImageFile.LOAD_TRUNCATED_IMAGES = True
                        img = Image.open(fp)
                        img.load()
                        fp.close()
                        PixivHelper.print_and_log('info', ' Image verified.')
                    except BaseException:
                        if fp is not None:
                            fp.close()
                        PixivHelper.print_and_log('info', ' Image invalid, deleting...')
                        os.remove(filename)
                        raise
                elif __config__.verifyImage and (filename.endswith(".ugoira") or filename.endswith(".zip")):
                    fp = None
                    try:
                        import zipfile
                        fp = open(filename, "rb")
                        zf = zipfile.ZipFile(fp)
                        zf.testzip()
                        fp.close()
                        PixivHelper.print_and_log('info', ' Image verified.')
                    except BaseException:
                        if fp is not None:
                            fp.close()
                        PixivHelper.print_and_log('info', ' Image invalid, deleting...')
                        os.remove(filename)
                        raise
                else:
                    PixivHelper.print_and_log('info', ' done.')

                # write to downloaded lists
                if start_iv or __config__.createDownloadLists:
                    dfile = codecs.open(dfilename, 'a+', encoding='utf-8')
                    dfile.write(filename + "\n")
                    dfile.close()

                return (PixivConstant.PIXIVUTIL_OK, filename)

            except urllib.error.HTTPError as httpError:
                PixivHelper.print_and_log('error', '[download_image()] HTTP Error: {0} at {1}'.format(str(httpError), url))
                if httpError.code == 404 or httpError.code == 502 or httpError.code == 500:
                    return (PixivConstant.PIXIVUTIL_NOT_OK, None)
                temp_error_code = PixivException.DOWNLOAD_FAILED_NETWORK
                raise
            except urllib.error.URLError as urlError:
                PixivHelper.print_and_log('error', '[download_image()] URL Error: {0} at {1}'.format(str(urlError), url))
                temp_error_code = PixivException.DOWNLOAD_FAILED_NETWORK
                raise
            except IOError as ioex:
                if ioex.errno == 28:
                    PixivHelper.print_and_log('error', ioex.message)
                    input("Press Enter to retry.")
                    return (PixivConstant.PIXIVUTIL_NOT_OK, None)
                temp_error_code = PixivException.DOWNLOAD_FAILED_IO
                raise
            except KeyboardInterrupt:
                PixivHelper.print_and_log('info', 'Aborted by user request => Ctrl-C')
                return (PixivConstant.PIXIVUTIL_ABORTED, None)
            finally:
                if res is not None:
                    del res
                if req is not None:
                    del req

        except BaseException:
            if temp_error_code is None:
                temp_error_code = PixivException.DOWNLOAD_FAILED_OTHER
            ERROR_CODE = temp_error_code
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            PixivHelper.print_and_log('error', 'Error at download_image(): {0} at {1} ({2})'.format(str(sys.exc_info()), url, ERROR_CODE))

            if retry_count < max_retry:
                retry_count = retry_count + 1
                print("\rRetrying [{0}]...".format(retry_count), end=' ')
                PixivHelper.printDelay(__config__.retryWait)
            else:
                raise


def perform_download(url, file_size, filename, overwrite, referer=None):
    if referer is None:
        referer = __config__, referer
    # actual download
    print('\rStart downloading...', end=' ')
    # fetch filesize
    req = PixivHelper.create_custom_request(url, __config__, referer)
    res = __br__.open_novisit(req)
    if file_size < 0:
        try:
            file_size = int(res.info()['Content-Length'])
        except KeyError:
            file_size = -1
            PixivHelper.print_and_log('info', "\tNo file size information!")
    (downloadedSize, filename) = PixivHelper.downloadImage(url, filename, res, file_size, overwrite)
    return (downloadedSize, filename)


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

        print("Found " + str(len(result)) + " items.")
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
    except KeyboardInterrupt:
        raise
    except Exception as ex:
        ERROR_CODE = getattr(ex, 'errorCode', -1)
        PixivHelper.print_and_log('error', 'Error at process_list(): {0}'.format(sys.exc_info()))
        print('Failed')
        raise


def process_member(member_id, user_dir='', page=1, end_page=0, bookmark=False, tags=None, title_prefix=""):
    global __errorList
    global ERROR_CODE
    list_page = None

    PixivHelper.print_and_log('info', 'Processing Member Id: ' + str(member_id))
    if page != 1:
        PixivHelper.print_and_log('info', 'Start Page: ' + str(page))
    if end_page != 0:
        PixivHelper.print_and_log('info', 'End Page: ' + str(end_page))
        if __config__.numberOfPage != 0:
            PixivHelper.print_and_log('info', 'Number of page setting will be ignored')
    elif np != 0:
        PixivHelper.print_and_log('info', 'End Page from command line: ' + str(np))
    elif __config__.numberOfPage != 0:
        PixivHelper.print_and_log('info', 'End Page from config: ' + str(__config__.numberOfPage))

    __config__.loadConfig(path=configfile)

    # calculate the offset for display properties
    offset = 24  # new offset for AJAX call
    if __br__._isWhitecube:
        offset = 50
    offset_start = (page - 1) * offset
    offset_stop = end_page * offset

    try:
        no_of_images = 1
        is_avatar_downloaded = False
        flag = True
        updated_limit_count = 0
        image_id = -1

        while flag:
            print('Page ', page)
            set_console_title("{0}MemberId: {1} Page: {2}".format(title_prefix, member_id, page))
            # Try to get the member page
            while True:
                try:
                    (artist, list_page) = PixivBrowserFactory.getBrowser().getMemberPage(member_id, page, bookmark, tags)
                    break
                except PixivException as ex:
                    ERROR_CODE = ex.errorCode
                    PixivHelper.print_and_log('info', 'Member ID (' + str(member_id) + '): ' + str(ex))
                    if ex.errorCode == PixivException.NO_IMAGES:
                        pass
                    else:
                        if list_page is None:
                            list_page = ex.htmlPage
                        if list_page is not None:
                            PixivHelper.dumpHtml("Dump for " + str(member_id) + " Error Code " + str(ex.errorCode) + ".html", list_page)
                        if ex.errorCode == PixivException.USER_ID_NOT_EXISTS or ex.errorCode == PixivException.USER_ID_SUSPENDED:
                            __dbManager__.setIsDeletedFlagForMemberId(int(member_id))
                            PixivHelper.print_and_log('info', 'Set IsDeleted for MemberId: ' + str(member_id) + ' not exist.')
                            # __dbManager__.deleteMemberByMemberId(member_id)
                            # PixivHelper.printAndLog('info', 'Deleting MemberId: ' + str(member_id) + ' not exist.')
                        if ex.errorCode == PixivException.OTHER_MEMBER_ERROR:
                            PixivHelper.safePrint(ex.message)
                            __errorList.append(dict(type="Member", id=str(member_id), message=ex.message, exception=ex))
                    return
                except AttributeError:
                    # Possible layout changes, try to dump the file below
                    raise
                except Exception:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exception(exc_type, exc_value, exc_traceback)
                    PixivHelper.print_and_log('error', 'Error at processing Artist Info: {0}'.format(sys.exc_info()))

            PixivHelper.safePrint('Member Name  : ' + artist.artistName)
            print('Member Avatar:', artist.artistAvatar)
            print('Member Token :', artist.artistToken)
            print('Member Background :', artist.artistBackground)
            print_offset_stop = offset_stop if offset_stop < artist.totalImages and offset_stop != 0 else artist.totalImages
            print('Processing images from {0} to {1} of {2}'.format(offset_start + 1, print_offset_stop, artist.totalImages))

            if not is_avatar_downloaded and __config__.downloadAvatar:
                if user_dir == '':
                    target_dir = __config__.rootDirectory
                else:
                    target_dir = str(user_dir)

                avatar_filename = PixivHelper.createAvatarFilename(artist, target_dir)
                if not DEBUG_SKIP_PROCESS_IMAGE:
                    if artist.artistAvatar.find('no_profile') == -1:
                        download_image(artist.artistAvatar,
                                       avatar_filename,
                                       "https://www.pixiv.net/",
                                       __config__.overwrite,
                                       __config__.retry,
                                       __config__.backupOldFile)
                    # Issue #508
                    if artist.artistBackground is not None and artist.artistBackground.startswith("http"):
                        bg_name = PixivHelper.createBackgroundFilenameFromAvatarFilename(avatar_filename)
                        download_image(artist.artistBackground,
                                       bg_name, "https://www.pixiv.net/",
                                       __config__.overwrite,
                                       __config__.retry,
                                       __config__.backupOldFile)
                is_avatar_downloaded = True

            __dbManager__.updateMemberName(member_id, artist.artistName)

            if not artist.haveImages:
                PixivHelper.print_and_log('info', "No image found for: " + str(member_id))
                flag = False
                continue

            result = PixivConstant.PIXIVUTIL_NOT_OK
            for image_id in artist.imageList:
                print('#' + str(no_of_images))
                if not __config__.overwrite:
                    r = __dbManager__.selectImageByMemberIdAndImageId(member_id, image_id)
                    if r is not None and not __config__.alwaysCheckFileSize:
                        print('Already downloaded:', image_id)
                        updated_limit_count = updated_limit_count + 1
                        if updated_limit_count > __config__.checkUpdatedLimit:
                            if __config__.checkUpdatedLimit != 0 and not __config__.alwaysCheckFileExists:
                                print('Skipping member:', member_id)
                                __dbManager__.updateLastDownloadedImage(member_id, image_id)

                                del list_page
                                __br__.clear_history()
                                return
                        gc.collect()
                        continue

                retry_count = 0
                while True:
                    try:
                        if artist.totalImages > 0:
                            # PixivHelper.safePrint("Total Images = " + str(artist.totalImages))
                            total_image_page_count = artist.totalImages
                            if(offset_stop > 0 and offset_stop < total_image_page_count):
                                total_image_page_count = offset_stop
                            total_image_page_count = total_image_page_count - offset_start
                            # PixivHelper.safePrint("Total Images Offset = " + str(total_image_page_count))
                        else:
                            total_image_page_count = ((page - 1) * 20) + len(artist.imageList)
                        title_prefix_img = "{0}MemberId: {1} Page: {2} Image {3}+{4} of {5}".format(title_prefix,
                                                                                                    member_id,
                                                                                                    page,
                                                                                                    no_of_images,
                                                                                                    updated_limit_count,
                                                                                                    total_image_page_count)
                        if not DEBUG_SKIP_PROCESS_IMAGE:
                            result = process_image(artist, image_id, user_dir, bookmark, title_prefix=title_prefix_img)
                            wait()

                        break
                    except KeyboardInterrupt:
                        result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                        break
                    except BaseException:
                        if retry_count > __config__.retry:
                            PixivHelper.print_and_log('error', "Giving up image_id: " + str(image_id))
                            return
                        retry_count = retry_count + 1
                        print("Stuff happened, trying again after 2 second (", retry_count, ")")
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
                        __log__.exception('Error at process_member(): ' + str(sys.exc_info()) + ' Member Id: ' + str(member_id))
                        time.sleep(2)

                no_of_images = no_of_images + 1

                if result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                    choice = input("Keyboard Interrupt detected, continue to next image (Y/N)")
                    if choice.upper() == 'N':
                        PixivHelper.print_and_log("info", "Member: " + str(member_id) + ", processing aborted")
                        flag = False
                        break
                    else:
                        continue

                # return code from process image
                if result == PixivConstant.PIXIVUTIL_SKIP_OLDER:
                    PixivHelper.print_and_log("info", "Reached older images, skippin to next member.")
                    flag = False
                    break

            if artist.isLastPage:
                print("Last Page")
                flag = False

            page = page + 1

            # page limit checking
            if end_page > 0 and page > end_page:
                print("Page limit reached (from endPage limit =" + str(end_page) + ")")
                flag = False
            else:
                if np_is_valid:  # Yavos: overwriting config-data
                    if page > np and np > 0:
                        print("Page limit reached (from command line =" + str(np) + ")")
                        flag = False
                elif page > __config__.numberOfPage and __config__.numberOfPage > 0:
                    print("Page limit reached (from config =" + str(__config__.numberOfPage) + ")")
                    flag = False

            del artist
            del list_page
            __br__.clear_history()
            gc.collect()

        if image_id > 0:
            __dbManager__.updateLastDownloadedImage(member_id, image_id)
            log_message = 'last image_id: ' + str(image_id)
        else:
            log_message = 'no images were found'
        print('Done.\n')
        __log__.info('Member_id: ' + str(member_id) + ' complete, ' + log_message)
    except KeyboardInterrupt:
        raise
    except BaseException:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        PixivHelper.print_and_log('error', 'Error at process_member(): {0}'.format(sys.exc_info()))
        try:
            if list_page is not None:
                dump_filename = 'Error page for member {0} at page {1}.html'.format(member_id, page)
                PixivHelper.dumpHtml(dump_filename, list_page)
                PixivHelper.print_and_log('error', "Dumping html to: {0}".format(dump_filename))
        except BaseException:
            PixivHelper.print_and_log('error', 'Cannot dump page for member_id: {0}'.format(member_id))
        raise


def process_image(artist=None, image_id=None, user_dir='', bookmark=False, search_tags='', title_prefix="", bookmark_count=-1, image_response_count=-1):
    global __errorList
    global ERROR_CODE

    parse_big_image = None
    parse_medium_page = None
    image = None
    result = None
    referer = 'https://www.pixiv.net/member_illust.php?mode=medium&illust_id=' + str(image_id)
    filename = 'no-filename-{0}.tmp'.format(image_id)

    try:
        print('Processing Image Id:', image_id)

        # check if already downloaded. images won't be downloaded twice - needed in process_image to catch any download
        r = __dbManager__.selectImageByImageId(image_id, cols='save_name')
        exists = False
        in_db = False
        if r is not None:
            exists = True
            in_db = True
        if r is not None and __config__.alwaysCheckFileExists:
            exists = __dbManager__.cleanupFileExists(r[0])

        if r is not None and not __config__.alwaysCheckFileSize and exists:
            if not __config__.overwrite and exists:
                print('Already downloaded:', image_id)
                gc.collect()
                return PixivConstant.PIXIVUTIL_SKIP_DUPLICATE

        # get the medium page
        try:
            (image, parse_medium_page) = PixivBrowserFactory.getBrowser().getImagePage(image_id=image_id,
                                                                                       parent=artist,
                                                                                       from_bookmark=bookmark,
                                                                                       bookmark_count=bookmark_count)
            if len(title_prefix) > 0:
                set_console_title("{0} ImageId: {1}".format(title_prefix, image.imageId))
            else:
                set_console_title("MemberId: {0} ImageId: {1}".format(image.artist.artistId, image.imageId))

        except PixivException as ex:
            ERROR_CODE = ex.errorCode
            __errorList.append(dict(type="Image", id=str(image_id), message=ex.message, exception=ex))
            if ex.errorCode == PixivException.UNKNOWN_IMAGE_ERROR:
                PixivHelper.safePrint(ex.message)
            elif ex.errorCode == PixivException.SERVER_ERROR:
                PixivHelper.print_and_log('error', 'Giving up image_id (medium): ' + str(image_id))
            elif ex.errorCode > 2000:
                PixivHelper.print_and_log('error', 'Image Error for ' + str(image_id) + ': ' + ex.message)
            if parse_medium_page is not None:
                dump_filename = 'Error medium page for image ' + str(image_id) + '.html'
                PixivHelper.dumpHtml(dump_filename, parse_medium_page)
                PixivHelper.print_and_log('error', 'Dumping html to: ' + dump_filename)
            else:
                PixivHelper.print_and_log('error', 'Image ID (' + str(image_id) + '): ' + str(ex))
            PixivHelper.print_and_log('error', 'Stack Trace: {0}'.format(str(sys.exc_info())))
            return PixivConstant.PIXIVUTIL_NOT_OK
        except Exception as ex:
            PixivHelper.print_and_log('error', 'Image ID (' + str(image_id) + '): ' + str(ex))
            if parse_medium_page is not None:
                dump_filename = 'Error medium page for image ' + str(image_id) + '.html'
                PixivHelper.dumpHtml(dump_filename, parse_medium_page)
                PixivHelper.print_and_log('error', 'Dumping html to: ' + dump_filename)
            PixivHelper.print_and_log('error', 'Stack Trace: {0}'.format(str(sys.exc_info())))
            return PixivConstant.PIXIVUTIL_NOT_OK

        download_image_flag = True

        # date validation and blacklist tag validation
        if __config__.dateDiff > 0:
            if image.worksDateDateTime != datetime.datetime.fromordinal(1).replace(tzinfo=datetime_z.utc):
                if image.worksDateDateTime < (datetime.datetime.today() - datetime.timedelta(__config__.dateDiff)).replace(tzinfo=datetime_z.utc):
                    PixivHelper.print_and_log('info', 'Skipping image_id: ' + str(image_id) + ' because contains older than: ' + str(__config__.dateDiff) + ' day(s).')
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_OLDER

        if __config__.useBlacklistTags:
            for item in __blacklistTags:
                if item in image.imageTags:
                    PixivHelper.print_and_log('info', 'Skipping image_id: ' + str(image_id) + ' because contains blacklisted tags: ' + item)
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST
                    break

        if __config__.useBlacklistMembers:
            if str(image.originalArtist.artistId) in __blacklistMembers:
                PixivHelper.print_and_log('info', 'Skipping image_id: ' + str(image_id) + ' because contains blacklisted member id: ' + str(image.originalArtist.artistId))
                download_image_flag = False
                result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST

        if download_image_flag:
            if artist is None:
                PixivHelper.safePrint('Member Name  : ' + image.artist.artistName)
                print('Member Avatar:', image.artist.artistAvatar)
                print('Member Token :', image.artist.artistToken)
                print('Member Background :', image.artist.artistBackground)
            PixivHelper.safePrint("Title: " + image.imageTitle)
            PixivHelper.safePrint("Tags : " + ', '.join(image.imageTags))
            PixivHelper.safePrint("Date : " + str(image.worksDateDateTime))
            print("Mode :", image.imageMode)

            # get bookmark count
            if ("%bookmark_count%" in __config__.filenameFormat or "%image_response_count%" in __config__.filenameFormat) and image.bookmark_count == -1:
                print("Parsing bookmark page", end=' ')
                bookmark_url = 'https://www.pixiv.net/bookmark_detail.php?illust_id=' + str(image_id)
                parse_bookmark_page = PixivBrowserFactory.getBrowser().getPixivPage(bookmark_url)
                image.ParseBookmarkDetails(parse_bookmark_page)
                parse_bookmark_page.decompose()
                del parse_bookmark_page
                print("Bookmark Count :", str(image.bookmark_count))
                __br__.back()

            if __config__.useSuppressTags:
                for item in __suppressTags:
                    if item in image.imageTags:
                        image.imageTags.remove(item)

            # get manga page
            if image.imageMode == 'manga' or image.imageMode == 'big':
                while True:
                    try:
                        big_url = 'https://www.pixiv.net/member_illust.php?mode={0}&illust_id={1}'.format(image.imageMode, image_id)
                        parse_big_image = PixivBrowserFactory.getBrowser().getPixivPage(big_url, referer)
                        if parse_big_image is not None:
                            image.ParseImages(page=parse_big_image, _br=PixivBrowserFactory.getExistingBrowser())
                            parse_big_image.decompose()
                            del parse_big_image
                        break
                    except Exception as ex:
                        __errorList.append(dict(type="Image", id=str(image_id), message=ex.message, exception=ex))
                        PixivHelper.print_and_log('info', 'Image ID (' + str(image_id) + '): ' + str(traceback.format_exc()))
                        try:
                            if parse_big_image is not None:
                                dump_filename = 'Error Big Page for image ' + str(image_id) + '.html'
                                PixivHelper.dumpHtml(dump_filename, parse_big_image)
                                PixivHelper.print_and_log('error', 'Dumping html to: ' + dump_filename)
                        except BaseException:
                            PixivHelper.print_and_log('error', 'Cannot dump big page for image_id: ' + str(image_id))
                        return PixivConstant.PIXIVUTIL_NOT_OK

                if image.imageMode == 'manga':
                    print("Page Count :", image.imageCount)

            if user_dir == '':  # Yavos: use config-options
                target_dir = __config__.rootDirectory
            else:  # Yavos: use filename from list
                target_dir = str(user_dir)

            result = PixivConstant.PIXIVUTIL_OK
            manga_files = dict()
            page = 0
            for img in image.imageUrls:
                print('Image URL :', img)
                url = os.path.basename(img)
                split_url = url.split('.')
                if split_url[0].startswith(str(image_id)):
                    # Yavos: filename will be added here if given in list
                    filename_format = __config__.filenameFormat
                    if image.imageMode == 'manga':
                        filename_format = __config__.filenameMangaFormat

                    filename = PixivHelper.makeFilename(filename_format, image, tagsSeparator=__config__.tagsSeparator, tagsLimit=__config__.tagsLimit, fileUrl=url, bookmark=bookmark, searchTags=search_tags)
                    filename = PixivHelper.sanitizeFilename(filename, target_dir)

                    if image.imageMode == 'manga' and __config__.createMangaDir:
                        manga_page = __re_manga_page.findall(filename)
                        if len(manga_page) > 0:
                            splitted_filename = filename.split(manga_page[0][0], 1)
                            splitted_manga_page = manga_page[0][0].split("_p", 1)
                            filename = splitted_filename[0] + splitted_manga_page[0] + os.sep + "_p" + splitted_manga_page[1] + splitted_filename[1]

                    PixivHelper.print_and_log('info', 'Filename  : {0}'.format(filename))

                    result = PixivConstant.PIXIVUTIL_NOT_OK
                    try:
                        (result, filename) = download_image(img, filename, referer, __config__.overwrite, __config__.retry, __config__.backupOldFile, image, page)

                        if result == PixivConstant.PIXIVUTIL_NOT_OK:
                            PixivHelper.print_and_log('error', 'Image url not found/failed to download: ' + str(image.imageId))
                        elif result == PixivConstant.PIXIVUTIL_ABORTED:
                            raise KeyboardInterrupt()

                        manga_files[page] = filename
                        page = page + 1

                    except urllib.error.URLError:
                        PixivHelper.print_and_log('error', 'Error when download_image(), giving up url: {0}'.format(img))
                    print('')

            if __config__.writeImageInfo or __config__.writeImageJSON:
                filename_info_format = __config__.filenameInfoFormat or __config__.filenameFormat
                info_filename = PixivHelper.makeFilename(filename_info_format, image, tagsSeparator=__config__.tagsSeparator,
                                                    tagsLimit=__config__.tagsLimit, fileUrl=url, appendExtension=False, bookmark=bookmark,
                                                    searchTags=search_tags)
                info_filename = PixivHelper.sanitizeFilename(info_filename, target_dir)
                # trim _pXXX
                info_filename = re.sub(r'_p?\d+$', '', info_filename)
                if __config__.writeImageInfo:
                    image.WriteInfo(info_filename + ".txt")
                if __config__.writeImageJSON:
                    image.WriteJSON(info_filename + ".json")

            if image.imageMode == 'ugoira_view':
                if __config__.writeUgoiraInfo:
                    image.WriteUgoiraData(filename + ".js")
                # Handle #451
                if __config__.createUgoira and (result == PixivConstant.PIXIVUTIL_OK or result == PixivConstant.PIXIVUTIL_SKIP_DUPLICATE):
                    handle_ugoira(image, filename)

            if __config__.writeUrlInDescription:
                PixivHelper.writeUrlInDescription(image, __config__.urlBlacklistRegex, __config__.urlDumpFilename)

        if in_db and not exists:
            result = PixivConstant.PIXIVUTIL_CHECK_DOWNLOAD  # There was something in the database which had not been downloaded

        # Only save to db if all images is downloaded completely
        if result == PixivConstant.PIXIVUTIL_OK or result == PixivConstant.PIXIVUTIL_SKIP_DUPLICATE or result == PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER:
            try:
                __dbManager__.insertImage(image.artist.artistId, image.imageId, image.imageMode)
            except BaseException:
                PixivHelper.print_and_log('error', 'Failed to insert image id:{0} to DB'.format(image.imageId))

            __dbManager__.updateImage(image.imageId, image.imageTitle, filename, image.imageMode)

            if len(manga_files) > 0:
                for page in manga_files:
                    __dbManager__.insertMangaImage(image_id, page, manga_files[page])

            # map back to PIXIVUTIL_OK (because of ugoira file check)
            result = 0

        if image is not None:
            del image
        gc.collect()
        # clearall()
        print('\n')
        return result
    except KeyboardInterrupt:
        raise
    except Exception as ex:
        ERROR_CODE = getattr(ex, 'errorCode', -1)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        PixivHelper.print_and_log('error', 'Error at process_image(): {0}'.format(image_id))
        PixivHelper.print_and_log('error', 'Exception: {0}'.format(sys.exc_info()))

        if parse_medium_page is not None:
            dump_filename = 'Error medium page for image ' + str(image_id) + '.html'
            PixivHelper.dumpHtml(dump_filename, parse_medium_page)
            PixivHelper.print_and_log('error', 'Dumping html to: {0}'.format(dump_filename))

        raise


def handle_ugoira(image, filename):
    if filename.endswith(".zip"):
        ugo_name = filename[:-4] + ".ugoira"
    else:
        ugo_name = filename
    if not os.path.exists(ugo_name):
        PixivHelper.print_and_log('info', "Creating ugoira archive => " + ugo_name)
        image.CreateUgoira(filename)
        # set last-modified and last-accessed timestamp
        if __config__.setLastModified and ugo_name is not None and os.path.isfile(ugo_name):
            ts = time.mktime(image.worksDateDateTime.timetuple())
            os.utime(ugo_name, (ts, ts))

    if __config__.deleteZipFile and os.path.exists(filename):
        PixivHelper.print_and_log('info', "Deleting zip file => " + filename)
        os.remove(filename)

    if __config__.createGif:
        gif_filename = ugo_name[:-7] + ".gif"
        if not os.path.exists(gif_filename):
            PixivHelper.ugoira2gif(ugo_name, gif_filename, __config__.deleteUgoira, image=image)
    if __config__.createApng:
        gif_filename = ugo_name[:-7] + ".png"
        if not os.path.exists(gif_filename):
            PixivHelper.ugoira2apng(ugo_name, gif_filename, __config__.deleteUgoira, image=image)
    if __config__.createWebm:
        gif_filename = ugo_name[:-7] + ".webm"
        if not os.path.exists(gif_filename):
            PixivHelper.ugoira2webm(ugo_name,
                                gif_filename,
                                __config__.deleteUgoira,
                                __config__.ffmpeg,
                                __config__.ffmpegCodec,
                                __config__.ffmpegParam,
                                "webm",
                                image)
    if __config__.createWebp:
        gif_filename = ugo_name[:-7] + ".webp"
        if not os.path.exists(gif_filename):
            PixivHelper.ugoira2webm(ugo_name,
                                gif_filename,
                                __config__.deleteUgoira,
                                __config__.ffmpeg,
                                __config__.webpCodec,
                                __config__.webpParam,
                                "webp",
                                image)


def process_tags(tags, page=1, end_page=0, wild_card=True, title_caption=False,
               start_date=None, end_date=None, use_tags_as_dir=False, member_id=None,
               bookmark_count=None, oldest_first=False):

    search_page = None
    i = page
    updated_limit_count = 0

    try:
        __config__.loadConfig(path=configfile)  # Reset the config for root directory

        search_tags = PixivHelper.decode_tags(tags)

        if use_tags_as_dir:
            print("Save to each directory using query tags.")
            __config__.rootDirectory += os.sep + PixivHelper.sanitizeFilename(search_tags)

        tags = PixivHelper.encode_tags(tags)

        images = 1
        last_image_id = -1
        skipped_count = 0

        offset = 20
        if __br__._isWhitecube:
            offset = 50
        start_offset = (page - 1) * offset
        stop_offset = end_page * offset

        PixivHelper.print_and_log('info', 'Searching for: (' + search_tags + ") " + tags)
        flag = True
        while flag:
            (t, search_page) = __br__.getSearchTagPage(tags, i,
                                                  wild_card,
                                                  title_caption,
                                                  start_date,
                                                  end_date,
                                                  member_id,
                                                  oldest_first,
                                                  page)
            if len(t.itemList) == 0:
                print('No more images')
                flag = False
            else:
                for item in t.itemList:
                    last_image_id = item.imageId
                    print('Image #' + str(images))
                    print('Image Id:', str(item.imageId))
                    print('Bookmark Count:', str(item.bookmarkCount))
                    if bookmark_count is not None and bookmark_count > item.bookmarkCount:
                        PixivHelper.print_and_log('info', 'Skipping imageId= {0} because less than bookmark count limit ({1} > {2}).'.format(item.imageId, bookmark_count, item.bookmarkCount))
                        skipped_count = skipped_count + 1
                        continue
                    result = 0
                    while True:
                        try:
                            if t.availableImages > 0:
                                # PixivHelper.safePrint("Total Images: " + str(t.availableImages))
                                total_image = t.availableImages
                                if(stop_offset > 0 and stop_offset < total_image):
                                    total_image = stop_offset
                                total_image = total_image - start_offset
                                # PixivHelper.safePrint("Total Images Offset: " + str(total_image))
                            else:
                                total_image = ((i - 1) * 20) + len(t.itemList)
                            title_prefix = "Tags:{0} Page:{1} Image {2}+{3} of {4}".format(tags, i, images, skipped_count, total_image)
                            if member_id is not None:
                                title_prefix = "MemberId: {0} Tags:{1} Page:{2} Image {3}+{4} of {5}".format(member_id,
                                                                                                              tags, i,
                                                                                                              images,
                                                                                                              skipped_count,
                                                                                                              total_image)
                            result = PixivConstant.PIXIVUTIL_OK
                            if not DEBUG_SKIP_PROCESS_IMAGE:
                                result = process_image(None, item.imageId, search_tags=search_tags, title_prefix=title_prefix, bookmark_count=item.bookmarkCount, image_response_count=item.imageResponse)
                                wait()
                            break
                        except KeyboardInterrupt:
                            result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                            break
                        except http.client.BadStatusLine:
                            print("Stuff happened, trying again after 2 second...")
                            time.sleep(2)

                    images = images + 1
                    if result == PixivConstant.PIXIVUTIL_SKIP_DUPLICATE or result == PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER:
                        updated_limit_count = updated_limit_count + 1
                        if updated_limit_count > __config__.checkUpdatedLimit:
                            if __config__.checkUpdatedLimit != 0 and not __config__.alwaysCheckFileExists:
                                PixivHelper.safePrint("Skipping tags: {0}".format(tags))
                                __br__.clear_history()
                                return
                        gc.collect()
                        continue
                    elif result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                        choice = input("Keyboard Interrupt detected, continue to next image (Y/N)")
                        if choice.upper() == 'N':
                            PixivHelper.print_and_log("info", "Tags: " + tags + ", processing aborted")
                            flag = False
                            break
                        else:
                            continue

            __br__.clear_history()

            i = i + 1

            del search_page

            if end_page != 0 and end_page < i:
                PixivHelper.print_and_log('info', "End Page reached: " + str(end_page))
                flag = False
            if t.isLastPage:
                PixivHelper.print_and_log('info', "Last page: " + str(i - 1))
                flag = False
            if __config__.enableInfiniteLoop and i == 1001 and not oldest_first:
                if last_image_id > 0:
                    # get the last date
                    PixivHelper.print_and_log('info', "Hit page 1000, trying to get workdate for last image id: " + str(last_image_id))
                    referer = 'https://www.pixiv.net/member_illust.php?mode=medium&illust_id=' + str(last_image_id)
                    parse_medium_page = PixivBrowserFactory.getBrowser().getPixivPage(referer)
                    image = PixivImage(iid=last_image_id, page=parse_medium_page, dateFormat=__config__.dateFormat)
                    _last_date = image.worksDateDateTime.strftime("%Y-%m-%d")
                    # hit the last page
                    PixivHelper.print_and_log('info', "Hit page 1000, looping back to page 1 with ecd: " + str(_last_date))
                    i = 1
                    end_date = _last_date
                    flag = True
                    last_image_id = -1
                else:
                    PixivHelper.print_and_log('info', "No more image in the list.")
                    flag = False

        print('done')
    except KeyboardInterrupt:
        raise
    except BaseException:
        msg = 'Error at process_tags() at page {0}: {1}'.format(i, sys.exc_info())
        PixivHelper.print_and_log('error', msg)
        try:
            if search_page is not None:
                dump_filename = 'Error page for search tags {0} at page {1}.html'.format(tags, i)
                PixivHelper.dumpHtml(dump_filename, search_page)
                PixivHelper.print_and_log('error', "Dumping html to: " + dump_filename)
        except BaseException:
            PixivHelper.print_and_log('error', 'Cannot dump page for search tags:' + search_tags)
        raise


def process_tags_list(filename, page=1, end_page=0, wild_card=True,
                      oldest_first=False, bookmark_count=None,
                      start_date=None, end_date=None):
    global ERROR_CODE

    try:
        print("Reading:", filename)
        l = PixivTags.parseTagsList(filename)
        for tag in l:
            process_tags(tag, page=page, end_page=end_page, wild_card=wild_card,
                         use_tags_as_dir=__config__.useTagsAsDir, oldest_first=oldest_first,
                         bookmark_count=bookmark_count, start_date=start_date, end_date=end_date)
    except KeyboardInterrupt:
        raise
    except Exception as ex:
        ERROR_CODE = getattr(ex, 'errorCode', -1)
        PixivHelper.print_and_log('error', 'Error at process_tags_list(): {0}'.format(sys.exc_info()))
        raise


def process_image_bookmark(hide='n', start_page=1, end_page=0, tag='', sorting=None):
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
            process_image(artist=None, image_id=item)
            image_count = image_count + 1
            wait()

        print("Done.\n")
    except KeyboardInterrupt:
        raise
    except BaseException:
        PixivHelper.print_and_log('error', 'Error at process_image_bookmark(): {0}'.format(sys.exc_info()))
        raise


def get_image_bookmark(hide, start_page=1, end_page=0, tag='', sorting=None):
    """Get user's image bookmark"""
    total_list = list()
    i = start_page
    while True:
        if end_page != 0 and i > end_page:
            print("Page Limit reached: " + str(end_page))
            break

        url = 'https://www.pixiv.net/bookmark.php?p=' + str(i)
        if hide:
            url = url + "&rest=hide"
        # Implement #468 default is desc, only for your own bookmark.
        if sorting in ('asc', 'date_d', 'date'):
            url = url + "&order=" + sorting
        if tag is not None and len(tag) > 0:
            url = url + '&tag=' + PixivHelper.encode_tags(tag)
        PixivHelper.print_and_log('info', "Importing user's bookmarked image from page " + str(i))
        PixivHelper.print_and_log('info', "Source URL: " + url)

        page = __br__.open(url)
        parse_page = BeautifulSoup(page.read())
        l = PixivBookmark.parseImageBookmark(parse_page)
        total_list.extend(l)
        if len(l) == 0:
            print("No more images.")
            break
        else:
            print(" found " + str(len(l)) + " images.")

        i = i + 1

        parse_page.decompose()
        del parse_page

    return total_list


def get_bookmarks(hide, start_page=1, end_page=0, member_id=None):
    """Get User's bookmarked artists """
    total_list = list()
    i = start_page
    while True:
        if end_page != 0 and i > end_page:
            print('Limit reached')
            break
        PixivHelper.print_and_log('info', 'Exporting page ' + str(i))
        url = 'https://www.pixiv.net/bookmark.php?type=user&p=' + str(i)
        if hide:
            url = url + "&rest=hide"
        if member_id:
            url = url + "&id=" + member_id
        PixivHelper.print_and_log('info', "Source URL: " + url)

        page = __br__.open_with_retry(url)
        parse_page = BeautifulSoup(page.read())
        l = PixivBookmark.parseBookmark(parse_page)
        if len(l) == 0:
            print('No more data')
            break
        total_list.extend(l)
        i = i + 1
        print(str(len(l)), 'items')
    return total_list


def process_bookmark(hide='n', start_page=1, end_page=0):
    try:
        total_list = list()
        if hide != 'o':
            print("Importing Bookmarks...")
            total_list.extend(get_bookmarks(False, start_page, end_page))
        if hide != 'n':
            print("Importing Private Bookmarks...")
            total_list.extend(get_bookmarks(True, start_page, end_page))
        print("Result: ", str(len(total_list)), "items.")
        i = 0
        current_member = 1
        for item in total_list:
            print("%d/%d\t%f %%" % (i, len(total_list), 100.0 * i / float(len(total_list))))
            i += 1
            prefix = "[{0} of {1}]".format(current_member, len(total_list))
            process_member(item.memberId, item.path, title_prefix=prefix)
            current_member = current_member + 1
        print("%d/%d\t%f %%" % (i, len(total_list), 100.0 * i / float(len(total_list))))
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
            parsed_page = BeautifulSoup(page.read())
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

                wait()
            i = i + 1

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
            max_id = group_data.maxId
            if group_data.imageList is not None and len(group_data.imageList) > 0:
                for image in group_data.imageList:
                    if image_count > limit and limit != 0:
                        flag = False
                        break
                    print("Image #{0}".format(image_count))
                    print("ImageId: {0}".format(image))
                    process_image(image_id=image)
                    image_count = image_count + 1
                    wait()

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

                    filename = PixivHelper.makeFilename(__config__.filenameFormat, imageInfo=image_data,
                                                        tagsSeparator=__config__.tagsSeparator,
                                                        tagsLimit=__config__.tagsLimit, fileUrl=image_data.imageUrls[0])
                    filename = PixivHelper.sanitizeFilename(filename, __config__.rootDirectory)
                    PixivHelper.safePrint("Filename  : " + filename)
                    (result, filename) = download_image(image_data.imageUrls[0], filename, url, __config__.overwrite, __config__.retry, __config__.backupOldFile)
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


def get_start_and_end_number(start_only=False):
    global np_is_valid
    global np

    page_num = input('Start Page (default=1): ') or 1
    try:
        page_num = int(page_num)
    except BaseException:
        print("Invalid page number:", page_num)
        raise

    end_page_num = 0
    if np_is_valid:
        end_page_num = np
    else:
        end_page_num = __config__.numberOfPage

    if not start_only:
        end_page_num = input('End Page (default=' + str(end_page_num) + ', 0 for no limit): ') or end_page_num
        try:
            end_page_num = int(end_page_num)
            if page_num > end_page_num and end_page_num != 0:
                print("page_num is bigger than end_page_num, assuming as page count.")
                end_page_num = page_num + end_page_num
        except BaseException:
            print("Invalid end page number:", end_page_num)
            raise

    return page_num, end_page_num


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


def check_date_time(input_date):
    split = input_date.split("-")
    return datetime.date(int(split[0]), int(split[1]), int(split[2])).isoformat()


def get_start_and_end_date():
    start_date = None
    end_date = None
    while True:
        try:
            start_date = input('Start Date [YYYY-MM-DD]: ') or None
            if start_date is not None:
                start_date = check_date_time(start_date)
            break
        except Exception as e:
            print(str(e))

    while True:
        try:
            end_date = input('End Date [YYYY-MM-DD]: ') or None
            if end_date is not None:
                end_date = check_date_time(end_date)
            break
        except Exception as e:
            print(str(e))

    return start_date, end_date


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
    print('f1. Download from supported artists (FANBOX)')
    print('f2. Download by artist id (FANBOX)')
    print('------------------------')
    print('d. Manage database')
    print('e. Export online bookmark')
    print('m. Export online user bookmark')
    print('r. Reload config.ini')
    print('p. Print config.ini')
    print('x. Exit')

    return input('Input: ').strip()


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
        member_ids = input('Member ids: ')
        (page, end_page) = get_start_and_end_number()

        member_ids = PixivHelper.getIdsFromCsv(member_ids, sep=" ")
        PixivHelper.print_and_log('info', "Member IDs: {0}".format(member_ids))
        for member_id in member_ids:
            prefix = "[{0} of {1}] ".format(current_member, len(member_ids))
            process_member(member_id, page=page, end_page=end_page, title_prefix=prefix)
            current_member = current_member + 1


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
        member_id = input('Member id: ')
        tags = input('Filter Tags: ')
        (page, end_page) = get_start_and_end_number()
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
        image_ids = input('Image ids: ')
        image_ids = PixivHelper.getIdsFromCsv(image_ids, sep=" ")
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
    if opisvalid and len(args) > 0:
        wildcard = args[0]
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        (page, end_page) = get_start_and_end_number_from_args(args, 1)
        tags = " ".join(args[3:])
    else:
        tags = PixivHelper.uni_input('Tags: ')
        bookmark_count = input('Bookmark Count: ') or None
        wildcard = input('Use Partial Match (s_tag) [y/n]: ') or 'n'
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        oldest_first = input('Oldest first[y/n]: ') or 'n'
        if oldest_first.lower() == 'y':
            oldest_first = True
        else:
            oldest_first = False

        (page, end_page) = get_start_and_end_number()
        (start_date, end_date) = get_start_and_end_date()
    if bookmark_count is not None:
        bookmark_count = int(bookmark_count)
    process_tags(tags.strip(), page, end_page, wildcard, start_date=start_date, end_date=end_date,
                use_tags_as_dir=__config__.useTagsAsDir, bookmark_count=bookmark_count, oldest_first=oldest_first)


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
        tags = PixivHelper.uni_input('Title/Caption: ')
        (page, end_page) = get_start_and_end_number()
        (start_date, end_date) = get_start_and_end_date()

    process_tags(tags.strip(), page, end_page, wild_card=False, title_caption=True, start_date=start_date, end_date=end_date, use_tags_as_dir=__config__.useTagsAsDir)


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
        member_id = input('Member Id: ')
        tags = PixivHelper.uni_input('Tag      : ')
        (page, end_page) = get_start_and_end_number()

    process_tags(tags.strip(), page, end_page, member_id=int(member_id), use_tags_as_dir=__config__.useTagsAsDir)


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
        test_tags = PixivHelper.uni_input('Tag : ')
        if len(test_tags) > 0:
            tags = test_tags

    if tags is not None and len(tags) > 0:
        PixivHelper.safePrint("Processing member id from {0} for tags: {1}".format(list_file_name, tags))
    else:
        PixivHelper.safePrint("Processing member id from {0}".format(list_file_name))

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
        arg = input("Include Private bookmarks [y/n/o]: ") or 'n'
        arg = arg.lower()
        if arg == 'y' or arg == 'n' or arg == 'o':
            hide = arg
        else:
            print("Invalid args: ", arg)
            return
        (start_page, end_page) = get_start_and_end_number()
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
        hide = input("Include Private bookmarks [y/n/o]: ") or 'n'
        hide = hide.lower()
        if hide not in ('y', 'n', 'o'):
            print("Invalid args: ", hide)
            return
        tag = input("Tag (default=All Images): ") or ''
        (start_page, end_page) = get_start_and_end_number()
        sorting = input("Sort Order [asc/desc/date/date_d]: ") or 'desc'
        sorting = sorting.lower()
        if sorting not in ('asc', 'desc', 'date', 'date_d'):
            print("Invalid sorting order: ", sorting)
            return

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
        filename = input("Tags list filename [tags.txt]: ") or './tags.txt'
        wildcard = input('Use Wildcard[y/n]: ') or 'n'
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        oldest_first = input('Oldest first[y/n]: ') or 'n'
        if oldest_first.lower() == 'y':
            oldest_first = True
        else:
            oldest_first = False
        bookmark_count = input('Bookmark Count: ') or None
        (page, end_page) = get_start_and_end_number()
        (start_date, end_date) = get_start_and_end_date()
    if bookmark_count is not None:
        bookmark_count = int(bookmark_count)

    process_tags_list(filename, page, end_page, wild_card=wildcard, oldest_first=oldest_first,
                      bookmark_count=bookmark_count, start_date=start_date, end_date=end_date)


def menu_download_new_illust_from_bookmark(opisvalid, args):
    __log__.info('New Illust from Bookmark mode.')

    if opisvalid:
        (page_num, end_page_num) = get_start_and_end_number_from_args(args, offset=0)
    else:
        (page_num, end_page_num) = get_start_and_end_number()

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
        group_id = input("Group Id: ")
        limit = int(input("Limit: "))
        arg = input("Process External Image [y/n]: ") or 'n'
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
        filename = input("Filename: ")
        arg = input("Include Private bookmarks [y/n/o]: ") or 'n'
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
        filename = input("Filename: ") or filename
        arg = input("Member Id: ") or ''
        arg = arg.lower()

    if arg.isdigit():
        member_id = arg
    else:
        print("Invalid args: ", arg)

    export_bookmark(filename, 'n', 1, 0, member_id)


def menu_fanbox_download_supported_artist(op_is_valid, args):
    __log__.info('Download FANBOX Supported Artists mode.')
    end_page = 0

    if op_is_valid and len(args) > 0:
        end_page = int(args[0])
    else:
        end_page = input("Max Page = ") or 0
        end_page = int(end_page)

    result = __br__.fanboxGetSupportedUsers()
    if len(result.supportedArtist) == 0:
        PixivHelper.print_and_log("info", "No supported artist!")
        return
    PixivHelper.print_and_log("info", "Found {0} supported artist(s)".format(len(result.supportedArtist)))
    print(result.supportedArtist)

    for artist_id in result.supportedArtist:
        processFanboxArtist(artist_id, end_page)


def processFanboxArtist(artist_id, end_page):
    current_page = 1
    next_url = None
    image_count = 1
    while(True):
        PixivHelper.print_and_log("info", "Processing {0}, page {1}".format(artist_id, current_page))
        result_artist = __br__.fanboxGetPostsFromArtist(artist_id, next_url)

        for post in result_artist.posts:
            print("#{0}".format(image_count))
            print("Post  = {0}".format(post.imageId))
            print("Title = {0}".format(post.imageTitle))
            print("Type  = {0}".format(post.type))
            print("Created Date  = {0}".format(post.worksDate))
            print("Is Restricted = {0}".format(post.is_restricted))
            # cover image
            if post.coverImageUrl is not None:
                # fake the image_url for filename compatibility, add post id and pagenum
                fake_image_url = post.coverImageUrl.replace("{0}/cover/".format(post.imageId), "{0}_".format(post.imageId))
                filename = PixivHelper.makeFilename(__config__.filenameFormat,
                                                    post,
                                                    artistInfo=result_artist,
                                                    tagsSeparator=__config__.tagsSeparator,
                                                    tagsLimit=__config__.tagsLimit,
                                                    fileUrl=fake_image_url,
                                                    bookmark=None,
                                                    searchTags='')
                filename = PixivHelper.sanitizeFilename(filename, __config__.rootDirectory)

                print("Downloading cover from {0}".format(post.coverImageUrl))
                print("Saved to {0}".format(filename))

                referer = "https://www.pixiv.net/fanbox/creator/{0}/post/{1}".format(artist_id, post.imageId)
                # don't pass the post id and page number to skip db check
                (result, filename) = download_image(post.coverImageUrl,
                                                    filename,
                                                    referer,
                                                    __config__.overwrite,
                                                    __config__.retry,
                                                    __config__.backupOldFile)

            else:
                PixivHelper.print_and_log("info", "No Cover Image for post: {0}.".format(post.imageId))

            # images
            if post.type in PixivModelFanbox.FanboxPost._supportedType:
                processFanboxImages(post, result_artist)
            image_count = image_count + 1

        if not result_artist.hasNextPage:
            PixivHelper.print_and_log("info", "No more post for {0}".format(artist_id))
            break
        current_page = current_page + 1
        if end_page > 0 and current_page > end_page:
            PixivHelper.print_and_log("info", "Reaching page limit for {0}, limit {1}".format(artist_id, end_page))
            break
        next_url = result_artist.nextUrl
        if next_url is None:
            PixivHelper.print_and_log("info", "No more next page for {0}".format(artist_id))
            break


def processFanboxImages(post, result_artist):
    if post.is_restricted:
        PixivHelper.print_and_log("info", "Skipping post: {0} due to restricted post.".format(post.imageId))
        return
    if post.images is None or len(post.images) == 0:
        PixivHelper.print_and_log("info", "No Image available in post: {0}.".format(post.imageId))
        # return
    else:
        current_page = 0
        print("Image Count = {0}".format(len(post.images)))
        for image_url in post.images:
            # fake the image_url for filename compatibility, add post id and pagenum
            fake_image_url = image_url.replace("{0}/".format(post.imageId), "{0}_p{1}_".format(post.imageId, current_page))
            filename = PixivHelper.makeFilename(__config__.filenameMangaFormat,
                                                post,
                                                artistInfo=result_artist,
                                                tagsSeparator=__config__.tagsSeparator,
                                                tagsLimit=__config__.tagsLimit,
                                                fileUrl=fake_image_url,
                                                bookmark=None,
                                                searchTags='')

            filename = PixivHelper.sanitizeFilename(filename, __config__.rootDirectory)
            referer = "https://www.pixiv.net/fanbox/creator/{0}/post/{1}".format(result_artist.artistId, post.imageId)

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

            __config__.alwaysCheckFileSize = _oldvalue
            current_page = current_page + 1

    # Implement #447
    if __config__.writeImageInfo:
        filename = PixivHelper.makeFilename(__config__.filenameInfoFormat,
                                            post,
                                            artistInfo=result_artist,
                                            tagsSeparator=__config__.tagsSeparator,
                                            tagsLimit=__config__.tagsLimit,
                                            fileUrl="{0}".format(post.imageId),
                                            bookmark=None,
                                            searchTags='')

        filename = PixivHelper.sanitizeFilename(filename, __config__.rootDirectory)
        post.WriteInfo(filename + ".txt")


def menu_fanbox_download_by_artist_id(op_is_valid, args):
    __log__.info('Download FANBOX by Artist ID mode.')
    end_page = 0
    artist_id = ''

    if op_is_valid and len(args) > 0:
        artist_id = str(int(args[0]))
        if len(args) > 1:
            end_page = args[1]
    else:
        artist_id = input("Artist ID = ")
        end_page = input("Max Page = ") or 0

    end_page = int(end_page)

    processFanboxArtist(artist_id, end_page)


def menu_reload_config():
    __log__.info('Manual Reload Config.')
    __config__.loadConfig(path=configfile)


def menu_print_config():
    __log__.info('Manual Reload Config.')
    __config__.printConfig()


def set_console_title(title=''):
    set_title = 'PixivDownloader {0} {1}'.format(PixivConstant.PIXIVUTIL_VERSION, title)
    PixivHelper.setConsoleTitle(set_title)


def setup_option_parser():
    global __valid_options
    __valid_options = ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'f1', 'f2', 'd', 'e', 'm')
    parser = OptionParser()
    parser.add_option('-s', '--startaction', dest='startaction',
                      help='Action you want to load your program with:       ' +
                            '1 - Download by member_id                       ' +
                            '2 - Download by image_id                        ' +
                            '3 - Download by tags                            ' +
                            '4 - Download from list                          ' +
                            '5 - Download from user bookmark                 ' +
                            '6 - Download from user\'s image bookmark        ' +
                            '7 - Download from tags list                     ' +
                            '8 - Download new illust from bookmark           ' +
                            '9 - Download by Title/Caption                   ' +
                            '10 - Download by Tag and Member Id              ' +
                            '11 - Download images from Member Bookmark       ' +
                            '12 - Download images by Group Id                ' +
                            'f1 - Download from supported artists (FANBOX)   ' +
                            'f2 - Download by artist id (FANBOX)             ' +
                            'e - Export online bookmark                      ' +
                            'm - Export online user bookmark                 ' +
                            'd - Manage database')
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
            # PIXIV FANBOX
            elif selection == 'f1':
                menu_fanbox_download_supported_artist(op_is_valid, args)
            elif selection == 'f2':
                menu_fanbox_download_by_artist_id(op_is_valid, args)
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
                filename = PixivHelper.sanitizeFilename(ex.value)
                PixivHelper.dumpHtml("Dump for {0}.html".format(filename), ex.htmlPage)
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


def wait():
    # Issue#276: add random delay for each post.
    if __config__.downloadDelay > 0:
        delay = random.random() * __config__.downloadDelay
        print("Wait for {0:.3}s".format(delay))
        time.sleep(delay)


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
        ### end new lines by Yavos ###

    __log__.info('###############################################################')
    if len(sys.argv) == 0:
        __log__.info('Starting with no argument..')
    else:
        __log__.info('Starting with argument: [%s].', " ".join(sys.argv))
    try:
        __config__.loadConfig(path=configfile)
        PixivHelper.setConfig(__config__)
    except BaseException:
        print('Failed to read configuration.')
        __log__.exception('Failed to read configuration.')

    PixivHelper.setLogLevel(__config__.logLevel)
    if __br__ is None:
        __br__ = PixivBrowserFactory.getBrowser(config=__config__)

    if __config__.checkNewVersion:
        PixivHelper.check_version()

    selection = None

    # Yavos: adding File for downloadlist
    now = datetime.date.today()
    dfilename = __config__.downloadListDirectory + os.sep + 'Downloaded_on_' + now.strftime('%Y-%m-%d') + '.txt'
    if not re.match(r'[a-zA-Z]:', dfilename):
        dfilename = PixivHelper.toUnicode(sys.path[0], encoding=sys.stdin.encoding) + os.sep + dfilename
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

    try:
        __dbManager__ = PixivDBManager.PixivDBManager(target=__config__.dbPath, config=__config__)
        __dbManager__.createDatabase()

        if __config__.useList:
            list_txt = PixivListItem.parseList(__config__.downloadListDirectory + os.sep + 'list.txt', __config__.rootDirectory)
            __dbManager__.importList(list_txt)
            print("Updated " + str(len(list_txt)) + " items.")

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

        if __config__.useSuppressTags:
            global __suppressTags
            __suppressTags = PixivTags.parseTagsList("suppress_tags.txt")
            PixivHelper.print_and_log('info', 'Using Suppress Tags: ' + str(len(__suppressTags)) + " items.")

        if __config__.createWebm:
            import shlex
            cmd = "{0} -encoders".format(__config__.ffmpeg)
            ffmpeg_args = shlex.split(cmd)
            try:
                p = subprocess.Popen(ffmpeg_args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                buff = p.stdout.read()
                if buff.find(__config__.ffmpegCodec) == 0:
                    __config__.createWebm = False
                    PixivHelper.print_and_log('error', '{0}'.format("#" * 80))
                    PixivHelper.print_and_log('error', 'Missing {0} encoder, createWebm disabled.'.format(__config__.ffmpegCodec))
                    PixivHelper.print_and_log('error', 'Command used: {0}.'.format(cmd))
                    PixivHelper.print_and_log('info', 'Please download ffmpeg with {0} encoder enabled.'.format(__config__.ffmpegCodec))
                    PixivHelper.print_and_log('error', '{0}'.format("#" * 80))
            except Exception as ex:
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
            username = input('Username ? ')
        else:
            msg = 'Using Username: ' + username
            print(msg)
            __log__.info(msg)

        password = __config__.password
        if password == '':
            if os.name == 'nt':
                win_unicode_console.disable()
            password = getpass.getpass('Password ? ')
            if os.name == 'nt':
                win_unicode_console.enable()

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
                PixivHelper.startIrfanView(dfilename, __config__.IrfanViewPath, start_irfan_slide, start_irfan_view)
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
    main()
