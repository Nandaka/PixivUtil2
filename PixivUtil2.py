#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import sys
import os
import re
import traceback
import gc
import time
import datetime
import urllib2
import getpass
import httplib
import codecs

from BeautifulSoup import BeautifulSoup

if os.name == 'nt':
    # enable unicode support on windows console.
    import win_unicode_console
    win_unicode_console.enable()

import PixivConstant
import PixivConfig
import PixivDBManager
import PixivHelper
from PixivModel import PixivArtist, PixivImage, PixivListItem, PixivBookmark, PixivTags
from PixivModel import PixivNewIllustBookmark, PixivGroup
from PixivException import PixivException
import PixivBrowserFactory

from optparse import OptionParser

script_path = PixivHelper.module_path()

np_is_valid = False
np = 0
op = ''
DEBUG_SKIP_PROCESS_IMAGE = False
ERROR_CODE = 0

gc.enable()
# gc.set_debug(gc.DEBUG_LEAK)

import mechanize
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

# http://www.pixiv.net/member_illust.php?mode=medium&illust_id=18830248
__re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
__re_manga_page = re.compile(r'(\d+(_big)?_p\d+)')


# -T04------For download file
def download_image(url, filename, referer, overwrite, max_retry, backup_old_file=False, image_id=None, page=None):
    global ERROR_CODE
    tempErrorCode = None
    retry_count = 0
    while retry_count <= max_retry:
        res = None
        req = None
        try:
            try:
                if not overwrite and not __config__.alwaysCheckFileSize:
                    print 'Checking local filename...',
                    if os.path.exists(filename) and os.path.isfile(filename):
                        PixivHelper.printAndLog('info', "File exists: {0}".format(filename.encode('utf-8')))
                        return PixivConstant.PIXIVUTIL_SKIP_DUPLICATE

                print 'Getting remote filesize...'
                # open with HEAD method
                req = PixivHelper.createCustomRequest(url, __config__, referer, head=True)
                res = __br__.open_novisit(req)

                # get file size
                file_size = -1
                try:
                    file_size = int(res.info()['Content-Length'])
                except KeyError:
                    file_size = -1
                    PixivHelper.printAndLog('info', "\tNo file size information!")
                print "Remote filesize = {0} ({1} Bytes)".format(PixivHelper.sizeInStr(file_size), file_size)

                # check if existing file exists
                if os.path.exists(filename) and os.path.isfile(filename) and not filename.endswith(".zip"):
                    old_size = os.path.getsize(filename)
                    checkResult = PixivHelper.checkFileExists(overwrite, filename, file_size, old_size, backup_old_file)
                    if checkResult != 1:
                        return checkResult

                # check for ugoira file
                if filename.endswith(".zip"):
                    ugoName = filename[:-4] + ".ugoira"
                    gifName = filename[:-4] + ".gif"
                    apngName = filename[:-4] + ".png"
                    # non-converted zip (no animation.json)
                    if os.path.exists(filename) and os.path.isfile(filename):
                        # not sure what is the proper handling, currently it will throw error after download due to file already exists.
                        pass
                    # converted to ugoira (has animation.json)
                    if os.path.exists(ugoName) and os.path.isfile(ugoName):
                        old_size = PixivHelper.getUgoiraSize(ugoName)
                        checkResult = PixivHelper.checkFileExists(overwrite, ugoName, file_size, old_size, backup_old_file)
                        if checkResult != 1:
                            # try to convert existing file.
                            if __config__.createGif and not os.path.exists(gifName):
                                PixivHelper.ugoira2gif(ugoName, gifName)
                            if __config__.createApng and not os.path.exists(apngName):
                                PixivHelper.ugoira2apng(ugoName, apngName)

                            return checkResult

                # check based on filename stored in DB using image id
                if image_id is not None:
                    db_filename = None
                    if page is not None:
                        row = __dbManager__.selectImageByImageIdAndPage(image_id, page)
                        if row is not None:
                            db_filename = row[2]
                    else:
                        row = __dbManager__.selectImageByImageId(image_id)
                        if row is not None:
                            db_filename = row[3]
                    if db_filename is not None and os.path.exists(db_filename) and os.path.isfile(db_filename):
                        old_size = os.path.getsize(db_filename)
                        checkResult = PixivHelper.checkFileExists(overwrite, db_filename, file_size, old_size, backup_old_file)
                        if checkResult != 1:
                            ugoName = None
                            if db_filename.endswith(".zip"):
                                ugoName = db_filename[:-4] + ".ugoira"
                                gifName = db_filename[:-4] + ".gif"
                                apngName = db_filename[:-4] + ".png"
                            if db_filename.endswith(".ugoira"):
                                ugoName = db_filename
                                gifName = db_filename[:-7] + ".gif"
                                apngName = db_filename[:-7] + ".png"

                            if ugoName is not None and os.path.exists(ugoName) and os.path.isfile(ugoName):
                                # try to convert existing file.
                                if __config__.createGif and not os.path.exists(gifName):
                                    PixivHelper.ugoira2gif(ugoName, gifName)
                                if __config__.createApng and not os.path.exists(apngName):
                                    PixivHelper.ugoira2apng(ugoName, apngName)

                            return checkResult

                # actual download
                print 'Start downloading...',
                req = PixivHelper.createCustomRequest(url, __config__, referer)
                res = __br__.open_novisit(req)
                downloadedSize = PixivHelper.downloadImage(url, filename, res, file_size, overwrite)

                # check the downloaded file size again
                if file_size > 0 and downloadedSize != file_size:
                    raise PixivException("Incomplete Downloaded for {0}".format(url), PixivException.DOWNLOAD_FAILED_OTHER)
                elif __config__.verifyImage and (filename.endswith(".jpg") or filename.endswith(".png") or filename.endswith(".gif")):
                    fp = None
                    try:
                        from PIL import Image
                        fp = open(filename, "rb")
                        img = Image.open(fp)
                        img.load()
                        fp.close()
                        PixivHelper.printAndLog('info', ' Image verified.')
                    except:
                        if fp is not None:
                            fp.close()
                        PixivHelper.printAndLog('info', ' Image invalid, deleting...')
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
                        PixivHelper.printAndLog('info', ' Image verified.')
                    except:
                        if fp is not None:
                            fp.close()
                        PixivHelper.printAndLog('info', ' Image invalid, deleting...')
                        os.remove(filename)
                        raise
                else:
                    PixivHelper.printAndLog('info', ' done.')

                # write to downloaded lists
                if start_iv or __config__.createDownloadLists:
                    dfile = codecs.open(dfilename, 'a+', encoding='utf-8')
                    dfile.write(filename + "\n")
                    dfile.close()

                return PixivConstant.PIXIVUTIL_OK

            except urllib2.HTTPError as httpError:
                PixivHelper.printAndLog('error', '[download_image()] HTTP Error: {0} at {1}'.format(str(httpError), url))
                if httpError.code == 404 or httpError.code == 502:
                    return PixivConstant.PIXIVUTIL_NOT_OK
                tempErrorCode = PixivException.DOWNLOAD_FAILED_NETWORK
                raise
            except urllib2.URLError as urlError:
                PixivHelper.printAndLog('error', '[download_image()] URL Error: {0} at {1}'.format(str(urlError), url))
                tempErrorCode = PixivException.DOWNLOAD_FAILED_NETWORK
                raise
            except IOError as ioex:
                if ioex.errno == 28:
                    PixivHelper.printAndLog('error', ioex.message)
                    raw_input("Press Enter to retry.")
                    return PixivConstant.PIXIVUTIL_NOT_OK
                tempErrorCode = PixivException.DOWNLOAD_FAILED_IO
                raise
            except KeyboardInterrupt:
                PixivHelper.printAndLog('info', 'Aborted by user request => Ctrl-C')
                return PixivConstant.PIXIVUTIL_ABORTED
            finally:
                if res is not None:
                    del res
                if req is not None:
                    del req

        except:
            if tempErrorCode is None:
                tempErrorCode = PixivException.DOWNLOAD_FAILED_OTHER
            ERROR_CODE = tempErrorCode
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            PixivHelper.printAndLog('error', 'Error at download_image(): {0} at {1} ({2})'.format(str(sys.exc_info()), url, ERROR_CODE))

            if retry_count < max_retry:
                retry_count = retry_count + 1
                print "Retrying [{0}]...".format(retry_count)
                PixivHelper.printDelay(__config__.retryWait)
            else:
                raise


#  Start of main processing logic
def process_list(mode, list_file_name=None, tags=None):
    global ERROR_CODE

    result = None
    try:
        # Getting the list
        if __config__.processFromDb:
            PixivHelper.printAndLog('info', 'Processing from database.')
            if __config__.dayLastUpdated == 0:
                result = __dbManager__.selectAllMember()
            else:
                print 'Select only last', __config__.dayLastUpdated, 'days.'
                result = __dbManager__.selectMembersByLastDownloadDate(__config__.dayLastUpdated)
        else:
            PixivHelper.printAndLog('info', 'Processing from list file: {0}'.format(list_file_name))
            result = PixivListItem.parseList(list_file_name, __config__.rootDirectory)

        if os.path.exists("ignore_list.txt"):
            PixivHelper.printAndLog('info', 'Processing ignore list for member: {0}'.format("ignore_list.txt"))
            ignoreList = PixivListItem.parseList("ignore_list.txt", __config__.rootDirectory)
            for ignore in ignoreList:
                for item in result:
                    if item.memberId == ignore.memberId:
                        result.remove(item)
                        break

        print "Found " + str(len(result)) + " items."

        for item in result:
            retry_count = 0
            while True:
                try:
                    process_member(mode, item.memberId, item.path, tags=tags)
                    break
                except KeyboardInterrupt:
                    raise
                except:
                    if retry_count > __config__.retry:
                        PixivHelper.printAndLog('error', 'Giving up member_id: ' + str(item.memberId))
                        break
                    retry_count = retry_count + 1
                    print 'Something wrong, retrying after 2 second (', retry_count, ')'
                    time.sleep(2)

            __br__.clear_history()
            print 'done.'
    except KeyboardInterrupt:
        raise
    except Exception as ex:
        ERROR_CODE = getattr(ex, 'errorCode', -1)
        print 'Error at process_list():', sys.exc_info()
        print 'Failed'
        __log__.exception('Error at process_list(): ' + str(sys.exc_info()))
        raise


def process_member(mode, member_id, user_dir='', page=1, end_page=0, bookmark=False, tags=None):
    global __errorList
    global ERROR_CODE

    PixivHelper.printAndLog('info', 'Processing Member Id: ' + str(member_id))
    if page != 1:
        PixivHelper.printAndLog('info', 'Start Page: ' + str(page))
    if end_page != 0:
        PixivHelper.printAndLog('info', 'End Page: ' + str(end_page))
        if __config__.numberOfPage != 0:
            PixivHelper.printAndLog('info', 'Number of page setting will be ignored')
    elif np != 0:
        PixivHelper.printAndLog('info', 'End Page from command line: ' + str(np))
    elif __config__.numberOfPage != 0:
        PixivHelper.printAndLog('info', 'End Page from config: ' + str(__config__.numberOfPage))

    __config__.loadConfig(path=configfile)
    list_page = None

    # calculate the offset for display properties
    offset = 20
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
            print 'Page ', page
            set_console_title("MemberId: " + str(member_id) + " Page: " + str(page))
            # Try to get the member page
            while True:
                try:
                    (artist, list_page) = PixivBrowserFactory.getBrowser().getMemberPage(member_id, page, bookmark, tags)
                    break
                except PixivException as ex:
                    ERROR_CODE = ex.errorCode
                    PixivHelper.printAndLog('info', 'Member ID (' + str(member_id) + '): ' + str(ex))
                    if ex.errorCode == PixivException.NO_IMAGES:
                        pass
                    else:
                        if list_page is not None:
                            PixivHelper.dumpHtml("Dump for " + str(member_id) + " Error Code " + str(ex.errorCode) + ".html", list_page)
                        if ex.errorCode == PixivException.USER_ID_NOT_EXISTS or ex.errorCode == PixivException.USER_ID_SUSPENDED:
                            __dbManager__.setIsDeletedFlagForMemberId(int(member_id))
                            PixivHelper.printAndLog('info', 'Set IsDeleted for MemberId: ' + str(member_id) + ' not exist.')
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
                    PixivHelper.printAndLog('error', 'Error at processing Artist Info: ' + str(sys.exc_info()))
                    __log__.exception('Error at processing Artist Info: ' + str(member_id))

            PixivHelper.safePrint('Member Name  : ' + artist.artistName)
            print 'Member Avatar:', artist.artistAvatar
            print 'Member Token :', artist.artistToken

            if artist.artistAvatar.find('no_profile') == -1 and not is_avatar_downloaded and __config__.downloadAvatar:
                if user_dir == '':
                    target_dir = __config__.rootDirectory
                else:
                    target_dir = user_dir

                avatar_filename = PixivHelper.createAvatarFilename(artist, target_dir)
                if not DEBUG_SKIP_PROCESS_IMAGE:
                    # hardcode the referer to pixiv main site
                    download_image(artist.artistAvatar, avatar_filename, "http://www.pixiv.net/", __config__.overwrite,
                                   __config__.retry, __config__.backupOldFile)
                is_avatar_downloaded = True

            __dbManager__.updateMemberName(member_id, artist.artistName)

            if not artist.haveImages:
                PixivHelper.printAndLog('info', "No image found for: " + str(member_id))
                flag = False
                continue

            result = PixivConstant.PIXIVUTIL_NOT_OK
            for image_id in artist.imageList:
                print '#' + str(no_of_images)
                if mode == PixivConstant.PIXIVUTIL_MODE_UPDATE_ONLY:
                    r = __dbManager__.selectImageByMemberIdAndImageId(member_id, image_id)
                    if r is not None and not __config__.alwaysCheckFileSize:
                        print 'Already downloaded:', image_id
                        updated_limit_count = updated_limit_count + 1
                        if updated_limit_count > __config__.checkUpdatedLimit:
                            if __config__.checkUpdatedLimit != 0:
                                print 'Skipping member:', member_id
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
                        title_prefix = "MemberId: {0} Page: {1} Image {2}+{3} of {4}".format(member_id,
                                                                                             page,
                                                                                             no_of_images,
                                                                                             updated_limit_count,
                                                                                             total_image_page_count)
                        if not DEBUG_SKIP_PROCESS_IMAGE:
                            result = process_image(mode, artist, image_id, user_dir, bookmark, title_prefix=title_prefix)  # Yavos added dir-argument to pass

                        break
                    except KeyboardInterrupt:
                        result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                        break
                    except:
                        if retry_count > __config__.retry:
                            PixivHelper.printAndLog('error', "Giving up image_id: " + str(image_id))
                            return
                        retry_count = retry_count + 1
                        print "Stuff happened, trying again after 2 second (", retry_count, ")"
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
                        __log__.exception('Error at process_member(): ' + str(sys.exc_info()) + ' Member Id: ' + str(member_id))
                        time.sleep(2)

                no_of_images = no_of_images + 1

                if result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                    choice = raw_input("Keyboard Interrupt detected, continue to next image (Y/N)")
                    if choice.upper() == 'N':
                        PixivHelper.printAndLog("info", "Member: " + str(member_id) + ", processing aborted")
                        flag = False
                        break
                    else:
                        continue

                # return code from process image
                if result == PixivConstant.PIXIVUTIL_SKIP_OLDER:
                    PixivHelper.printAndLog("info", "Reached older images, skippin to next member.")
                    flag = False
                    break

            if artist.isLastPage:
                print "Last Page"
                flag = False

            page = page + 1

            # page limit checking
            if end_page > 0 and page > end_page:
                print "Page limit reached (from endPage limit =" + str(end_page) + ")"
                flag = False
            else:
                if np_is_valid:  # Yavos: overwriting config-data
                    if page > np and np > 0:
                        print "Page limit reached (from command line =" + str(np) + ")"
                        flag = False
                elif page > __config__.numberOfPage and __config__.numberOfPage > 0:
                    print "Page limit reached (from config =" + str(__config__.numberOfPage) + ")"
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
        print 'Done.\n'
        __log__.info('Member_id: ' + str(member_id) + ' complete, ' + log_message)
    except KeyboardInterrupt:
        raise
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        PixivHelper.printAndLog('error', 'Error at process_member(): ' + str(sys.exc_info()))
        __log__.exception('Error at process_member(): ' + str(member_id))
        try:
            if list_page is not None:
                dump_filename = 'Error page for member ' + str(member_id) + '.html'
                PixivHelper.dumpHtml(dump_filename, list_page)
                PixivHelper.printAndLog('error', "Dumping html to: " + dump_filename)
        except:
            PixivHelper.printAndLog('error', 'Cannot dump page for member_id:' + str(member_id))
        raise


def process_image(mode, artist=None, image_id=None, user_dir='', bookmark=False, search_tags='', title_prefix=None, bookmark_count=-1, image_response_count=-1):
    global __errorList
    global ERROR_CODE

    parse_big_image = None
    parse_medium_page = None
    image = None
    result = None
    referer = 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=' + str(image_id)

    try:
        filename = 'N/A'
        print 'Processing Image Id:', image_id

        # check if already downloaded. images won't be downloaded twice - needed in process_image to catch any download
        r = __dbManager__.selectImageByImageId(image_id)
        if r is not None and not __config__.alwaysCheckFileSize:
            if mode == PixivConstant.PIXIVUTIL_MODE_UPDATE_ONLY:
                print 'Already downloaded:', image_id
                gc.collect()
                return

        # get the medium page
        try:
            (image, parse_medium_page) = PixivBrowserFactory.getBrowser().getImagePage(imageId=image_id,
                                                                                       parent=artist,
                                                                                       fromBookmark=bookmark,
                                                                                       bookmark_count=bookmark_count)
            if title_prefix is not None:
                set_console_title(title_prefix + " ImageId: {0}".format(image.imageId))
            else:
                set_console_title('MemberId: ' + str(image.artist.artistId) + ' ImageId: ' + str(image.imageId))

        except PixivException as ex:
            ERROR_CODE = ex.errorCode
            __errorList.append(dict(type="Image", id=str(image_id), message=ex.message, exception=ex))
            if ex.errorCode == PixivException.UNKNOWN_IMAGE_ERROR:
                PixivHelper.safePrint(ex.message)
            elif ex.errorCode == PixivException.SERVER_ERROR:
                PixivHelper.printAndLog('error', 'Giving up image_id (medium): ' + str(image_id))
            elif ex.errorCode > 2000:
                PixivHelper.printAndLog('error', 'Image Error for ' + str(image_id) + ': ' + ex.message)

            if parse_medium_page is not None:
                dump_filename = 'Error medium page for image ' + str(image_id) + '.html'
                PixivHelper.dumpHtml(dump_filename, parse_medium_page)
                PixivHelper.printAndLog('error', 'Dumping html to: ' + dump_filename)
            else:
                PixivHelper.printAndLog('info', 'Image ID (' + str(image_id) + '): ' + str(ex))
            return PixivConstant.PIXIVUTIL_NOT_OK
        except Exception as ex:
            PixivHelper.printAndLog('info', 'Image ID (' + str(image_id) + '): ' + str(ex))
            if parse_medium_page is not None:
                dump_filename = 'Error medium page for image ' + str(image_id) + '.html'
                PixivHelper.dumpHtml(dump_filename, parse_medium_page)
                PixivHelper.printAndLog('error', 'Dumping html to: ' + dump_filename)
            return PixivConstant.PIXIVUTIL_NOT_OK

        download_image_flag = True

        # date validation and blacklist tag validation
        if __config__.dateDiff > 0:
            if image.worksDateDateTime != datetime.datetime.fromordinal(1):
                if image.worksDateDateTime < datetime.datetime.today() - datetime.timedelta(__config__.dateDiff):
                    PixivHelper.printAndLog('info', 'Skipping image_id: ' + str(image_id) + ' because contains older than: ' + str(__config__.dateDiff) + ' day(s).')
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_OLDER

        if __config__.useBlacklistTags:
            for item in __blacklistTags:
                if item in image.imageTags:
                    PixivHelper.printAndLog('info', 'Skipping image_id: ' + str(image_id) + ' because contains blacklisted tags: ' + item)
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST
                    break

        if __config__.useBlacklistMembers:
            if str(image.originalArtist.artistId) in __blacklistMembers:
                PixivHelper.printAndLog('info', 'Skipping image_id: ' + str(image_id) + ' because contains blacklisted member id: ' + str(image.originalArtist.artistId))
                download_image_flag = False
                result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST

        if download_image_flag:
            PixivHelper.safePrint("Title: " + image.imageTitle)
            PixivHelper.safePrint("Tags : " + ', '.join(image.imageTags))
            PixivHelper.safePrint("Date : " + str(image.worksDateDateTime))
            print "Mode :", image.imageMode

            # get bookmark count
            if ("%bookmark_count%" in __config__.filenameFormat or "%image_response_count%" in __config__.filenameFormat) and image.bookmark_count == -1:
                print "Parsing bookmark page",
                bookmark_url = 'http://www.pixiv.net/bookmark_detail.php?illust_id=' + str(image_id)
                parse_bookmark_page = PixivBrowserFactory.getBrowser().getPixivPage(bookmark_url)
                image.ParseBookmarkDetails(parse_bookmark_page)
                parse_bookmark_page.decompose()
                del parse_bookmark_page
                print "Bookmark Count :", str(image.bookmark_count)
                __br__.back()

            if __config__.useSuppressTags:
                for item in __suppressTags:
                    if item in image.imageTags:
                        image.imageTags.remove(item)

            # get manga page
            if image.imageMode == 'manga' or image.imageMode == 'big':
                while True:
                    try:
                        big_url = 'http://www.pixiv.net/member_illust.php?mode={0}&illust_id={1}'.format(image.imageMode, image_id)
                        parse_big_image = PixivBrowserFactory.getBrowser().getPixivPage(big_url, referer)
                        if parse_big_image is not None:
                            image.ParseImages(page=parse_big_image, _br=PixivBrowserFactory.getExistingBrowser())
                            parse_big_image.decompose()
                            del parse_big_image
                        break
                    except Exception as ex:
                        __errorList.append(dict(type="Image", id=str(image_id), message=ex.message, exception=ex))
                        PixivHelper.printAndLog('info', 'Image ID (' + str(image_id) + '): ' + str(traceback.format_exc()))
                        try:
                            if parse_big_image is not None:
                                dump_filename = 'Error Big Page for image ' + str(image_id) + '.html'
                                PixivHelper.dumpHtml(dump_filename, parse_big_image)
                                PixivHelper.printAndLog('error', 'Dumping html to: ' + dump_filename)
                        except:
                            PixivHelper.printAndLog('error', 'Cannot dump big page for image_id: ' + str(image_id))
                        return PixivConstant.PIXIVUTIL_NOT_OK

                if image.imageMode == 'manga':
                    print "Page Count :", image.imageCount

            if user_dir == '':  # Yavos: use config-options
                target_dir = __config__.rootDirectory
            else:  # Yavos: use filename from list
                target_dir = user_dir

            result = PixivConstant.PIXIVUTIL_OK
            mangaFiles = dict()
            page = 0
            for img in image.imageUrls:
                print 'Image URL :', img
                url = os.path.basename(img)
                splitted_url = url.split('.')
                if splitted_url[0].startswith(str(image_id)):
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

                    PixivHelper.safePrint('Filename  : ' + filename)
                    result = PixivConstant.PIXIVUTIL_NOT_OK
                    try:
                        overwrite = False
                        if mode == PixivConstant.PIXIVUTIL_MODE_OVERWRITE:
                            overwrite = True

                        result = download_image(img, filename, referer, overwrite, __config__.retry, __config__.backupOldFile, image_id, page)

                        mangaFiles[page] = filename
                        page = page + 1

                        if result == PixivConstant.PIXIVUTIL_NOT_OK:
                            PixivHelper.printAndLog('error', 'Image url not found/failed to download: ' + str(image.imageId))
                        elif result == PixivConstant.PIXIVUTIL_ABORTED:
                            raise KeyboardInterrupt()

                    except urllib2.URLError:
                        PixivHelper.printAndLog('error', 'Giving up url: ' + str(img))
                        __log__.exception('Error when download_image(): ' + str(img))
                    print ''

            if __config__.writeImageInfo or __config__.writeImageJSON:
                filename_info_format = __config__.filenameInfoFormat
                info_filename = PixivHelper.makeFilename(filename_info_format, image, tagsSeparator=__config__.tagsSeparator,
                                                    tagsLimit=__config__.tagsLimit, fileUrl=url, appendExtension=False, bookmark=bookmark,
                                                    searchTags=search_tags)
                info_filename = PixivHelper.sanitizeFilename(info_filename, target_dir)
                # trim _pXXX
                info_filename = re.sub('_p?\d+$', '', info_filename)
                if __config__.writeImageInfo:
                    image.WriteInfo(info_filename + ".txt")
                if __config__.writeImageJSON:
                    image.WriteJSON(info_filename + ".json")
            
            if image.imageMode == 'ugoira_view':
                if __config__.writeUgoiraInfo:
                    image.WriteUgoiraData(filename + ".js")
                if __config__.createUgoira and result == PixivConstant.PIXIVUTIL_OK:
                    ugo_name = filename[:-4] + ".ugoira"
                    PixivHelper.printAndLog('info', "Creating ugoira archive => " + ugo_name)
                    image.CreateUgoira(filename)
                    if __config__.deleteZipFile:
                        PixivHelper.printAndLog('info', "Deleting zip file => " + filename)
                        os.remove(filename)

                    if __config__.createGif:
                        gif_filename = ugo_name[:-7] + ".gif"
                        PixivHelper.ugoira2gif(ugo_name, gif_filename)
                    if __config__.createApng:
                        gif_filename = ugo_name[:-7] + ".png"
                        PixivHelper.ugoira2apng(ugo_name, gif_filename)

            if __config__.writeUrlInDescription:
                PixivHelper.writeUrlInDescription(image, __config__.urlBlacklistRegex, __config__.urlDumpFilename)

        # Only save to db if all images is downloaded completely
        if result == PixivConstant.PIXIVUTIL_OK or result == PixivConstant.PIXIVUTIL_SKIP_DUPLICATE or result == PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER:
            try:
                __dbManager__.insertImage(image.artist.artistId, image.imageId, image.imageMode)
            except:
                pass
            __dbManager__.updateImage(image.imageId, image.imageTitle, filename, image.imageMode)

            if image.imageMode == 'manga':
                for page in mangaFiles:
                    __dbManager__.insertMangaImage(image_id, page, mangaFiles[page])

            # map back to PIXIVUTIL_OK (because of ugoira file check)
            result = 0

        if image is not None:
            del image
        gc.collect()
        # clearall()
        print '\n'
        return result
    except KeyboardInterrupt:
        raise
    except Exception as ex:
        ERROR_CODE = getattr(ex, 'errorCode', -1)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        PixivHelper.printAndLog('error', 'Error at process_image(): ' + str(sys.exc_info()))
        __log__.exception('Error at process_image(): ' + str(image_id))

        if parse_medium_page is not None:
            dump_filename = 'Error medium page for image ' + str(image_id) + '.html'
            PixivHelper.dumpHtml(dump_filename, parse_medium_page)
            PixivHelper.printAndLog('error', 'Dumping html to: ' + dump_filename)

        raise


def process_tags(mode, tags, page=1, end_page=0, wild_card=True, title_caption=False,
               start_date=None, end_date=None, use_tags_as_dir=False, member_id=None,
               bookmark_count=None, oldest_first=False):

    search_page = None
    try:
        __config__.loadConfig(path=configfile)  # Reset the config for root directory

        search_tags = PixivHelper.decode_tags(tags)

        if use_tags_as_dir:
            print "Save to each directory using query tags."
            __config__.rootDirectory += os.sep + PixivHelper.sanitizeFilename(search_tags)

        tags = PixivHelper.encode_tags(tags)

        i = page
        images = 1
        last_image_id = -1
        skipped_count = 0

        offset = 20
        if __br__._isWhitecube:
            offset = 50
        start_offset = (page - 1) * offset
        stop_offset = end_page * offset

        PixivHelper.printAndLog('info', 'Searching for: (' + search_tags + ") " + tags)
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
                print 'No more images'
                flag = False
            else:
                for item in t.itemList:
                    last_image_id = item.imageId
                    print 'Image #' + str(images)
                    print 'Image Id:', str(item.imageId)
                    print 'Bookmark Count:', str(item.bookmarkCount)
                    if bookmark_count is not None and bookmark_count > item.bookmarkCount:
                        PixivHelper.printAndLog('info', 'Skipping imageId= {0} because less than bookmark count limit ({1} > {2}).'.format(item.imageId, bookmark_count, item.bookmarkCount))
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
                            if not DEBUG_SKIP_PROCESS_IMAGE:
                                process_image(mode, None, item.imageId, search_tags=search_tags, title_prefix=title_prefix, bookmark_count=item.bookmarkCount, image_response_count=item.imageResponse)
                            break
                        except KeyboardInterrupt:
                            result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                            break
                        except httplib.BadStatusLine:
                            print "Stuff happened, trying again after 2 second..."
                            time.sleep(2)

                    images = images + 1

                    if result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                        choice = raw_input("Keyboard Interrupt detected, continue to next image (Y/N)")
                        if choice.upper() == 'N':
                            PixivHelper.printAndLog("info", "Tags: " + tags + ", processing aborted")
                            flag = False
                            break
                        else:
                            continue

            __br__.clear_history()

            i = i + 1

            del search_page

            if end_page != 0 and end_page < i:
                PixivHelper.printAndLog('info', "End Page reached: " + str(end_page))
                flag = False
            if t.isLastPage:
                PixivHelper.printAndLog('info', "Last page: " + str(i - 1))
                flag = False
            if __config__.enableInfiniteLoop and i == 1001 and not oldest_first:
                if last_image_id > 0:
                    # get the last date
                    PixivHelper.printAndLog('info', "Hit page 1000, trying to get workdate for last image id: " + str(last_image_id))
                    referer = 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id=' + str(last_image_id)
                    parse_medium_page = PixivBrowserFactory.getBrowser().getPixivPage(referer)
                    image = PixivImage(iid=last_image_id, page=parse_medium_page, dateFormat=__config__.dateFormat)
                    _last_date = image.worksDateDateTime.strftime("%Y-%m-%d")
                    # hit the last page
                    PixivHelper.printAndLog('info', "Hit page 1000, looping back to page 1 with ecd: " + str(_last_date))
                    i = 1
                    end_date = _last_date
                    flag = True
                    last_image_id = -1
                else:
                    PixivHelper.printAndLog('info', "No more image in the list.")
                    flag = False

        print 'done'
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at process_tags():', sys.exc_info()
        __log__.exception('Error at process_tags(): ' + str(sys.exc_info()))
        try:
            if search_page is not None:
                dump_filename = 'Error page for search tags ' + tags + '.html'
                PixivHelper.dumpHtml(dump_filename, search_page)
                PixivHelper.printAndLog('error', "Dumping html to: " + dump_filename)
        except:
            PixivHelper.printAndLog('error', 'Cannot dump page for search tags:' + search_tags)
        raise


def process_tags_list(mode, filename, page=1, end_page=0, wild_card=True, oldest_first=False, bookmark_count=None):
    global ERROR_CODE

    try:
        print "Reading:", filename
        l = PixivTags.parseTagsList(filename)
        for tag in l:
            process_tags(mode, tag, page=page, end_page=end_page, wild_card=wild_card,
                         use_tags_as_dir=__config__.useTagsAsDir, oldest_first=oldest_first, bookmark_count=bookmark_count)
    except KeyboardInterrupt:
        raise
    except Exception as ex:
        ERROR_CODE = getattr(ex, 'errorCode', -1)
        print 'Error at process_tags_list():', sys.exc_info()
        __log__.exception('Error at process_tags_list(): ' + str(sys.exc_info()))
        raise


def process_image_bookmark(mode, hide='n', start_page=1, end_page=0, tag=''):
    global np_is_valid
    global np
    try:
        print "Importing image bookmarks..."
        totalList = list()
        image_count = 1

        if hide == 'n':
            totalList.extend(get_image_bookmark(False, start_page, end_page, tag))
        elif hide == 'y':
            # public and private image bookmarks
            totalList.extend(get_image_bookmark(False, start_page, end_page, tag))
            totalList.extend(get_image_bookmark(True, start_page, end_page, tag))
        else:
            totalList.extend(get_image_bookmark(True, start_page, end_page, tag))

        PixivHelper.printAndLog('info', "Found " + str(len(totalList)) + " image(s).")
        for item in totalList:
            print "Image #" + str(image_count)
            process_image(mode, artist=None, image_id=item)
            image_count = image_count + 1

        print "Done.\n"
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at process_image_bookmark():', sys.exc_info()
        __log__.exception('Error at process_image_bookmark(): ' + str(sys.exc_info()))
        raise


def get_image_bookmark(hide, start_page=1, end_page=0, tag=''):
    """Get user's image bookmark"""
    total_list = list()
    i = start_page
    while True:
        if end_page != 0 and i > end_page:
            print "Page Limit reached: " + str(end_page)
            break

        url = 'http://www.pixiv.net/bookmark.php?p=' + str(i)
        if hide:
            url = url + "&rest=hide"
        if tag is not None and len(tag) > 0:
            url = url + '&tag=' + PixivHelper.encode_tags(tag)

        PixivHelper.printAndLog('info', "Importing user's bookmarked image from page " + str(i))
        PixivHelper.printAndLog('info', "Source URL: " + url)

        page = __br__.open(url)
        parse_page = BeautifulSoup(page.read())
        l = PixivBookmark.parseImageBookmark(parse_page)
        total_list.extend(l)
        if len(l) == 0:
            print "No more images."
            break
        else:
            print " found " + str(len(l)) + " images."

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
            print 'Limit reached'
            break
        PixivHelper.printAndLog('info', 'Exporting page ' + str(i))
        url = 'http://www.pixiv.net/bookmark.php?type=user&p=' + str(i)
        if hide:
            url = url + "&rest=hide"
        if member_id:
            url = url + "&id=" + member_id
        PixivHelper.printAndLog('info', "Source URL: " + url)

        page = __br__.open(url)
        parse_page = BeautifulSoup(page.read())
        l = PixivBookmark.parseBookmark(parse_page)
        if len(l) == 0:
            print 'No more data'
            break
        total_list.extend(l)
        i = i + 1
        print str(len(l)), 'items'
    return total_list


def process_bookmark(mode, hide='n', start_page=1, end_page=0):
    try:
        total_list = list()
        if hide != 'o':
            print "Importing Bookmarks..."
            total_list.extend(get_bookmarks(False, start_page, end_page))
        if hide != 'n':
            print "Importing Private Bookmarks..."
            total_list.extend(get_bookmarks(True, start_page, end_page))
        print "Result: ", str(len(total_list)), "items."
        for item in total_list:
            process_member(mode, item.memberId, item.path)
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at process_bookmark():', sys.exc_info()
        __log__.exception('Error at process_bookmark(): ' + str(sys.exc_info()))
        raise


def export_bookmark(filename, hide='n', start_page=1, end_page=0, member_id=None):
    try:
        total_list = list()
        if hide != 'o':
            print "Importing Bookmarks..."
            total_list.extend(get_bookmarks(False, start_page, end_page, member_id))
        if hide != 'n':
            print "Importing Private Bookmarks..."
            total_list.extend(get_bookmarks(True, start_page, end_page, member_id))
        print "Result: ", str(len(total_list)), "items."
        PixivBookmark.exportList(total_list, filename)
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at export_bookmark():', sys.exc_info()
        __log__.exception('Error at export_bookmark(): ' + str(sys.exc_info()))
        raise


def process_new_illust_from_bookmark(mode, page_num=1, end_page_num=0):
    try:
        print "Processing New Illust from bookmark"
        i = page_num
        image_count = 1
        flag = True
        while flag:
            print "Page #" + str(i)
            url = 'http://www.pixiv.net/bookmark_new_illust.php?p=' + str(i)
            if __config__.r18mode:
                url = 'http://www.pixiv.net/bookmark_new_illust_r18.php?p=' + str(i)

            PixivHelper.printAndLog('info', "Source URL: " + url)
            page = __br__.open(url)
            parsed_page = BeautifulSoup(page.read())
            pb = PixivNewIllustBookmark(parsed_page)
            if not pb.haveImages:
                print "No images!"
                break

            for image_id in pb.imageList:
                print "Image #" + str(image_count)
                result = process_image(mode, artist=None, image_id=int(image_id))
                image_count = image_count + 1

                if result == PixivConstant.PIXIVUTIL_SKIP_OLDER:
                    flag = False
                    break
            i = i + 1

            parsed_page.decompose()
            del parsed_page

            # Non premium is only limited to 100 page
            # Premium user might be limited to 5000, refer to issue #112
            if (end_page_num != 0 and i > end_page_num) or i > 5000 or pb.isLastPage:
                print "Limit or last page reached."
                flag = False

        print "Done."
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at process_new_illust_from_bookmark():', sys.exc_info()
        __log__.exception('Error at process_new_illust_from_bookmark(): ' + str(sys.exc_info()))
        raise


def process_from_group(mode, group_id, limit=0, process_external=True):
    try:
        print "Download by Group Id"
        if limit != 0:
            print "Limit: {0}".format(limit)
        if process_external:
            print "Include External Image: {0}".format(process_external)

        max_id = 0
        image_count = 0
        flag = True
        while flag:
            url = "http://www.pixiv.net/group/images.php?format=json&max_id={0}&id={1}".format(max_id, group_id)
            PixivHelper.printAndLog('info', "Getting images from: {0}".format(url))
            json_response = __br__.open(url)
            group_data = PixivGroup(json_response)
            max_id = group_data.maxId
            if group_data.imageList is not None and len(group_data.imageList) > 0:
                for image in group_data.imageList:
                    if image_count > limit and limit != 0:
                        flag = False
                        break
                    print "Image #{0}".format(image_count)
                    print "ImageId: {0}".format(image)
                    process_image(mode, image_id=image)
                    image_count = image_count + 1

            if process_external and group_data.externalImageList is not None and len(group_data.externalImageList) > 0:
                for image_data in group_data.externalImageList:
                    if image_count > limit and limit != 0:
                        flag = False
                        break
                    print "Image #{0}".format(image_count)
                    print "Member Id   : {0}".format(image_data.artist.artistId)
                    PixivHelper.safePrint("Member Name  : " + image_data.artist.artistName)
                    print "Member Token : {0}".format(image_data.artist.artistToken)
                    print "Image Url   : {0}".format(image_data.imageUrls[0])

                    filename = PixivHelper.makeFilename(__config__.filenameFormat, imageInfo=image_data,
                                                        tagsSeparator=__config__.tagsSeparator,
                                                        tagsLimit=__config__.tagsLimit, fileUrl=image_data.imageUrls[0])
                    filename = PixivHelper.sanitizeFilename(filename, __config__.rootDirectory)
                    PixivHelper.safePrint("Filename  : " + filename)
                    download_image(image_data.imageUrls[0], filename, url, __config__.overwrite, __config__.retry,
                                   __config__.backupOldFile)
                    image_count = image_count + 1

            if (group_data.imageList is None or len(group_data.imageList) == 0) and \
               (group_data.externalImageList is None or len(group_data.externalImageList) == 0):
                flag = False
            print ""

    except:
        print 'Error at process_from_group():', sys.exc_info()
        __log__.exception('Error at process_from_group(): ' + str(sys.exc_info()))
        raise


def header():
    print 'PixivDownloader2 version', PixivConstant.PIXIVUTIL_VERSION
    print PixivConstant.PIXIVUTIL_LINK
    print 'Donate at', PixivConstant.PIXIVUTIL_DONATE


def get_start_and_end_number(start_only=False):
    global np_is_valid
    global np

    page_num = raw_input('Start Page (default=1): ') or 1
    try:
        page_num = int(page_num)
    except:
        print "Invalid page number:", page_num
        raise

    end_page_num = 0
    if np_is_valid:
        end_page_num = np
    else:
        end_page_num = __config__.numberOfPage

    if not start_only:
        end_page_num = raw_input('End Page (default=' + str(end_page_num) + ', 0 for no limit): ') or end_page_num
        try:
            end_page_num = int(end_page_num)
            if page_num > end_page_num and end_page_num != 0:
                print "page_num is bigger than end_page_num, assuming as page count."
                end_page_num = page_num + end_page_num
        except:
            print "Invalid end page number:", end_page_num
            raise

    return page_num, end_page_num


def get_start_and_end_number_from_args(args, offset=0, start_only=False):
    global np_is_valid
    global np
    page_num = 1
    if len(args) > 0 + offset:
        try:
            page_num = int(args[0 + offset])
            print "Start Page =", str(page_num)
        except:
            print "Invalid page number:", args[0 + offset]
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
                    print "page_num is bigger than end_page_num, assuming as page count."
                    end_page_num = page_num + end_page_num
                print "End Page =", str(end_page_num)
            except:
                print "Invalid end page number:", args[1 + offset]
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
            start_date = raw_input('Start Date [YYYY-MM-DD]: ') or None
            if start_date is not None:
                start_date = check_date_time(start_date)
            break
        except Exception as e:
            print str(e)

    while True:
        try:
            end_date = raw_input('End Date [YYYY-MM-DD]: ') or None
            if end_date is not None:
                end_date = check_date_time(end_date)
            break
        except Exception as e:
            print str(e)

    return start_date, end_date


def menu():
    set_console_title()
    header()
    print '1. Download by member_id'
    print '2. Download by image_id'
    print '3. Download by tags'
    print '4. Download from list'
    print '5. Download from bookmarked artists (bookmark.php?type=user)'
    print '6. Download from bookmarked images (bookmark.php)'
    print '7. Download from tags list'
    print '8. Download new illust from bookmarked members (bookmark_new_illust.php)'
    print '9. Download by Title/Caption'
    print '10. Download by Tag and Member Id'
    print '11. Download Member Bookmark'
    print '12. Download by Group Id'
    print '------------------------'
    print 'd. Manage database'
    print 'e. Export online bookmark'
    print 'm. Export online user bookmark'
    print 'r. Reload config.ini'
    print 'p. Print config.ini'
    print 'x. Exit'

    return raw_input('Input: ').strip()


def menu_download_by_member_id(mode, opisvalid, args):
    __log__.info('Member id mode.')
    page = 1
    end_page = 0
    if opisvalid and len(args) > 0:
        for member_id in args:
            try:
                test_id = int(member_id)
                process_member(mode, test_id)
            except:
                PixivHelper.printAndLog('error', "Member ID: {0} is not valid".format(member_id))
                continue
    else:
        member_ids = raw_input('Member ids: ')
        (page, end_page) = get_start_and_end_number()

        member_ids = PixivHelper.getIdsFromCsv(member_ids, sep=" ")
        for member_id in member_ids:
            process_member(mode, member_id, page=page, end_page=end_page)


def menu_download_by_member_bookmark(mode, opisvalid, args):
    __log__.info('Member Bookmark mode.')
    page = 1
    end_page = 0
    if opisvalid and len(args) > 0:
        for member_id in args:
            try:
                test_id = int(member_id)
                process_member(mode, test_id)
            except:
                PixivHelper.printAndLog('error', "Member ID: {0} is not valid".format(member_id))
                continue
    else:
        member_id = raw_input('Member id: ')
        tags = raw_input('Filter Tags: ')
        (page, end_page) = get_start_and_end_number()
        process_member(mode, member_id.strip(), page=page, end_page=end_page, bookmark=True, tags=tags)


def menu_download_by_image_id(mode, opisvalid, args):
    __log__.info('Image id mode.')
    if opisvalid and len(args) > 0:
        for image_id in args:
            try:
                test_id = int(image_id)
                process_image(mode, None, test_id)
            except:
                PixivHelper.printAndLog('error', "Image ID: {0} is not valid".format(image_id))
                continue
    else:
        image_ids = raw_input('Image ids: ')
        image_ids = PixivHelper.getIdsFromCsv(image_ids, sep=" ")
        for image_id in image_ids:
            process_image(mode, None, int(image_id))


def menu_download_by_tags(mode, opisvalid, args):
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
        bookmark_count = raw_input('Bookmark Count: ') or None
        wildcard = raw_input('Use Partial Match (s_tag) [y/n]: ') or 'n'
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        oldest_first = raw_input('Oldest first[y/n]: ') or 'n'
        if oldest_first.lower() == 'y':
            oldest_first = True
        else:
            oldest_first = False

        (page, end_page) = get_start_and_end_number()
        (start_date, end_date) = get_start_and_end_date()
    if bookmark_count is not None:
        bookmark_count = int(bookmark_count)
    process_tags(mode, tags.strip(), page, end_page, wildcard, start_date=start_date, end_date=end_date,
                use_tags_as_dir=__config__.useTagsAsDir, bookmark_count=bookmark_count, oldest_first=oldest_first)


def menu_download_by_title_caption(mode, opisvalid, args):
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

    process_tags(mode, tags.strip(), page, end_page, wild_card=False, title_caption=True, start_date=start_date, end_date=end_date, use_tags_as_dir=__config__.useTagsAsDir)


def menu_download_by_tag_and_member_id(mode, opisvalid, args):
    __log__.info('Tag and MemberId mode.')
    member_id = 0
    tags = None

    if opisvalid and len(args) >= 2:
        member_id = int(args[0])
        (page, end_page) = get_start_and_end_number_from_args(args, 1)
        tags = " ".join(args[3:])
        PixivHelper.safePrint("Looking tags: " + tags + " from memberId: " + str(member_id))
    else:
        member_id = raw_input('Member Id: ')
        tags = PixivHelper.uni_input('Tag      : ')

    process_tags(mode, tags.strip(), member_id=int(member_id), use_tags_as_dir=__config__.useTagsAsDir)


def menu_download_from_list(mode, opisvalid, args):
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
        PixivHelper.safePrint(u"Processing member id from {0} for tags: {1}".format(list_file_name, tags))
    else:
        PixivHelper.safePrint("Processing member id from {0}".format(list_file_name))

    process_list(mode, list_file_name, tags)


def menu_download_from_online_user_bookmark(mode, opisvalid, args):
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
                print "Invalid args: ", args
                return
            (start_page, end_page) = get_start_and_end_number_from_args(args, offset=1)
    else:
        arg = raw_input("Include Private bookmarks [y/n/o]: ") or 'n'
        arg = arg.lower()
        if arg == 'y' or arg == 'n' or arg == 'o':
            hide = arg
        else:
            print "Invalid args: ", arg
            return
        (start_page, end_page) = get_start_and_end_number()
    process_bookmark(mode, hide, start_page, end_page)


def menu_download_from_online_image_bookmark(mode, opisvalid, args):
    __log__.info("User's Image Bookmark mode.")
    start_page = 1
    end_page = 0
    hide = False
    tag = ''

    if opisvalid and len(args) > 0:
        arg = args[0].lower()
        if arg == 'y' or arg == 'n' or arg == 'o':
            hide = arg
        else:
            print "Invalid args: ", args
            return
        (start_page, end_page) = get_start_and_end_number_from_args(args, offset=1)
    else:
        arg = raw_input("Include Private bookmarks [y/n/o]: ") or 'n'
        arg = arg.lower()
        if arg == 'y' or arg == 'n' or arg == 'o':
            hide = arg
        else:
            print "Invalid args: ", arg
            return
        tag = raw_input("Tag (default=All Images): ") or ''
        (start_page, end_page) = get_start_and_end_number()

    process_image_bookmark(mode, hide, start_page, end_page, tag)


def menu_download_from_tags_list(mode, opisvalid, args):
    __log__.info('Taglist mode.')
    page = 1
    end_page = 0
    oldest_first = False
    wildcard = True
    bookmark_count = None

    if opisvalid and len(args) > 0:
        filename = args[0]
        (page, end_page) = get_start_and_end_number_from_args(args, offset=1)
    else:
        filename = raw_input("Tags list filename [tags.txt]: ") or './tags.txt'
        wildcard = raw_input('Use Wildcard[y/n]: ') or 'n'
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        oldest_first = raw_input('Oldest first[y/n]: ') or 'n'
        if oldest_first.lower() == 'y':
            oldest_first = True
        else:
            oldest_first = False
        bookmark_count = raw_input('Bookmark Count: ') or None
        (page, end_page) = get_start_and_end_number()
    if bookmark_count is not None:
        bookmark_count = int(bookmark_count)
    process_tags_list(mode, filename, page, end_page, wild_card=wildcard, oldest_first=oldest_first, bookmark_count=bookmark_count)


def menu_download_new_illust_from_bookmark(mode, opisvalid, args):
    __log__.info('New Illust from Bookmark mode.')

    if opisvalid:
        (page_num, end_page_num) = get_start_and_end_number_from_args(args, offset=0)
    else:
        (page_num, end_page_num) = get_start_and_end_number()

    process_new_illust_from_bookmark(mode, page_num, end_page_num)


def menu_download_by_group_id(mode, opisvalid, args):
    __log__.info('Group mode.')
    process_external = False
    limit = 0

    if opisvalid and len(args) > 0:
        group_id = args[0]
        limit = int(args[1])
        if args[2].lower() == 'y':
            process_external = True
    else:
        group_id = raw_input("Group Id: ")
        limit = int(raw_input("Limit: "))
        arg = raw_input("Process External Image [y/n]: ") or 'n'
        arg = arg.lower()
        if arg == 'y':
            process_external = True

    process_from_group(mode, group_id, limit, process_external)


def menu_export_online_bookmark(mode, opisvalid, args):
    __log__.info('Export Bookmark mode.')
    hide = False
    filename = raw_input("Filename: ")
    arg = raw_input("Include Private bookmarks [y/n/o]: ") or 'n'
    arg = arg.lower()
    if arg == 'y' or arg == 'n' or arg == 'o':
        hide = arg
    else:
        print "Invalid args: ", arg
    export_bookmark(filename, hide)


def menu_export_online_user_bookmark(mode, opisvalid, args):
    __log__.info('Export Bookmark mode.')
    member_id = ''
    filename = raw_input("Filename: ")
    arg = raw_input("Member Id: ") or ''
    arg = arg.lower()
    if arg.isdigit():
        member_id = arg
    else:
        print "Invalid args: ", arg
    export_bookmark(filename, 'n', 1, 0, member_id)


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
    parser = OptionParser()
    parser.add_option('-s', '--startaction', dest='startaction',
                      help='Action you want to load your program with:            ' +
                            '1 - Download by member_id                              ' +
                            '2 - Download by image_id                              ' +
                            '3 - Download by tags                                    ' +
                            '4 - Download from list                                 ' +
                            '5 - Download from user bookmark                        ' +
                            '6 - Download from user\'s image bookmark               ' +
                            '7 - Download from tags list                           ' +
                            '8 - Download new illust from bookmark                  ' +
                            '9 - Download by Title/Caption                           ' +
                            '10 - Download by Tag and Member Id                     ' +
                            '11 - Download images from Member Bookmark               ' +
                            '12 - Download images by Group Id                        ' +
                            'e - Export online bookmark                              ' +
                            'm - Export online user bookmark                         ' +
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
def main_loop(ewd, mode, op_is_valid, selection, np_is_valid, args):
    global __errorList
    global ERROR_CODE

    while True:
        try:
            if len(__errorList) > 0:
                print "Unknown errors from previous operation"
                for err in __errorList:
                    message = err["type"] + ": " + str(err["id"]) + " ==> " + err["message"]
                    PixivHelper.printAndLog('error', message)
                __errorList = list()
                ERROR_CODE = 1

            if op_is_valid:  # Yavos (next 3 lines): if commandline then use it
                selection = op
            else:
                selection = menu()

            if selection == '1':
                menu_download_by_member_id(mode, op_is_valid, args)
            elif selection == '2':
                menu_download_by_image_id(mode, op_is_valid, args)
            elif selection == '3':
                menu_download_by_tags(mode, op_is_valid, args)
            elif selection == '4':
                menu_download_from_list(mode, op_is_valid, args)
            elif selection == '5':
                menu_download_from_online_user_bookmark(mode, op_is_valid, args)
            elif selection == '6':
                menu_download_from_online_image_bookmark(mode, op_is_valid, args)
            elif selection == '7':
                menu_download_from_tags_list(mode, op_is_valid, args)
            elif selection == '8':
                menu_download_new_illust_from_bookmark(mode, op_is_valid, args)
            elif selection == '9':
                menu_download_by_title_caption(mode, op_is_valid, args)
            elif selection == '10':
                menu_download_by_tag_and_member_id(mode, op_is_valid, args)
            elif selection == '11':
                menu_download_by_member_bookmark(mode, op_is_valid, args)
            elif selection == '12':
                menu_download_by_group_id(mode, op_is_valid, args)
            elif selection == 'e':
                menu_export_online_bookmark(mode, op_is_valid, args)
            elif selection == 'm':
                menu_export_online_user_bookmark(mode, op_is_valid, args)
            elif selection == 'd':
                __dbManager__.main()
            elif selection == 'r':
                menu_reload_config()
            elif selection == 'p':
                menu_print_config()
            elif selection == '-all':
                if not np_is_valid:
                    np_is_valid = True
                    np = 0
                    print 'download all mode activated'
                else:
                    np_is_valid = False
                    print 'download mode reset to', __config__.numberOfPage, 'pages'
            elif selection == 'x':
                break

            if ewd:  # Yavos: added lines for "exit when done"
                break
            op_is_valid = False  # Yavos: needed to prevent endless loop
        except KeyboardInterrupt:
            PixivHelper.printAndLog("info", "Keyboard Interrupt pressed, selection: {0}".format(selection))
            PixivHelper.clearScreen()
            print "Restarting..."
            selection = menu()
    return np_is_valid, op_is_valid, selection


def doLogin(password, username):
    result = False
    try:
        if len(__config__.cookie) > 0:
            result = PixivBrowserFactory.getBrowser(config=__config__).loginUsingCookie()

        if not result:
            result = PixivBrowserFactory.getBrowser(config=__config__).login(username, password)
    except:
        PixivHelper.printAndLog('error', 'Error at doLogin(): {0}'.format(str(sys.exc_info())))
        raise PixivException("Cannot Login!", PixivException.CANNOT_LOGIN)
    return result


def main():
    set_console_title()
    header()

    # Option Parser
    global np_is_valid  # used in process image bookmark
    global np  # used in various places for number of page overwriting
    global start_iv  # used in download_image
    global op
    global __br__
    global configfile
    global ERROR_CODE
    global __dbManager__

    parser = setup_option_parser()
    (options, args) = parser.parse_args()

    op = options.startaction
    if op in ('1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', 'd', 'e'):
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
    except:
        np_is_valid = False
        parser.error('Value %s used for numberOfPage is not an integer.' % options.numberofpages)
        # Yavos: use print option instead when program should be running even with this error
        ### end new lines by Yavos ###

    __log__.info('###############################################################')
    __log__.info('Starting...')
    try:
        __config__.loadConfig(path=configfile)
        PixivHelper.setConfig(__config__)
    except:
        print 'Failed to read configuration.'
        __log__.exception('Failed to read configuration.')

    PixivHelper.setLogLevel(__config__.logLevel)
    if __br__ is None:
        __br__ = PixivBrowserFactory.getBrowser(config=__config__)

    selection = None
    global dfilename

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
        __log__.info('Creating directory: ' + directory)

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
            print "Updated " + str(len(list_txt)) + " items."

        if __config__.overwrite:
            msg = 'Overwrite enabled.'
            print msg
            __log__.info(msg)

        if __config__.dayLastUpdated != 0 and __config__.processFromDb:
            PixivHelper.printAndLog('info',
                                    'Only process member where day last updated >= ' + str(__config__.dayLastUpdated))

        if __config__.dateDiff > 0:
            PixivHelper.printAndLog('info', 'Only process image where day last updated >= ' + str(__config__.dateDiff))

        if __config__.useBlacklistTags:
            global __blacklistTags
            __blacklistTags = PixivTags.parseTagsList("blacklist_tags.txt")
            PixivHelper.printAndLog('info', 'Using Blacklist Tags: ' + str(len(__blacklistTags)) + " items.")

        if __config__.useBlacklistMembers:
            global __blacklistMembers
            __blacklistMembers = PixivTags.parseTagsList("blacklist_members.txt")
            PixivHelper.printAndLog('info', 'Using Blacklist Members: ' + str(len(__blacklistMembers)) + " members.")

        if __config__.useSuppressTags:
            global __suppressTags
            __suppressTags = PixivTags.parseTagsList("suppress_tags.txt")
            PixivHelper.printAndLog('info', 'Using Suppress Tags: ' + str(len(__suppressTags)) + " items.")

        username = __config__.username
        if username == '':
            username = raw_input('Username ? ')
        else:
            msg = 'Using Username: ' + username
            print msg
            __log__.info(msg)

        password = __config__.password
        if password == '':
            password = getpass.getpass('Password ? ')

        if np_is_valid and np != 0:  # Yavos: overwrite config-data
            msg = 'Limit up to: ' + str(np) + ' page(s). (set via commandline)'
            print msg
            __log__.info(msg)
        elif __config__.numberOfPage != 0:
            msg = 'Limit up to: ' + str(__config__.numberOfPage) + ' page(s).'
            print msg
            __log__.info(msg)

        result = doLogin(password, username)

        if result:
            if __config__.overwrite:
                mode = PixivConstant.PIXIVUTIL_MODE_OVERWRITE
            else:
                mode = PixivConstant.PIXIVUTIL_MODE_UPDATE_ONLY

            np_is_valid, op_is_valid, selection = main_loop(ewd, mode, op_is_valid, selection, np_is_valid, args)

            if start_iv:  # Yavos: adding start_irfan_view-handling
                PixivHelper.startIrfanView(dfilename, __config__.IrfanViewPath, start_irfan_slide, start_irfan_view)
        else:
            ERROR_CODE = PixivException.NOT_LOGGED_IN
    except PixivException as pex:
        PixivHelper.printAndLog('error', pex.message)
        ERROR_CODE = pex.errorCode
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        __log__.exception('Unknown Error: ' + str(exc_value))
        ERROR_CODE = getattr(ex, 'errorCode', -1)
    finally:
        __dbManager__.close()
        if not ewd:  # Yavos: prevent input on exitwhendone
            if selection is None or selection != 'x':
                raw_input('press enter to exit.')
        __log__.setLevel("INFO")
        __log__.info('EXIT: ' + str(ERROR_CODE))
        __log__.info('###############################################################')
        sys.exit(ERROR_CODE)


if __name__ == '__main__':
    main()
