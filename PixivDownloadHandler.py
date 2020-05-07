# -*- coding: utf-8 -*-
import codecs
import gc
import os
import sys
import time
import traceback
import urllib

import mechanize

import PixivBrowserFactory
import PixivConstant
from PixivException import PixivException
import PixivHelper


def download_image(caller,
                   url,
                   filename,
                   referer,
                   overwrite,
                   max_retry,
                   backup_old_file=False,
                   image=None,
                   page=None,
                   notifier=None):
    '''return download result and filename if ok'''
    # caller function/method
    # TODO: ideally to be removed or passed as argument
    db = caller.__dbManager__
    config = caller.__config__

    if notifier is None:
        notifier = PixivHelper.dummy_notifier

    temp_error_code = None
    retry_count = 0

    # Issue #548
    filename_save = filename

    # test once and set the result
    if caller.UTF8_FS is None:
        filename_test = os.path.dirname(filename_save) + os.sep + "あいうえお"
        try:
            PixivHelper.makeSubdirs(filename_test)
            test_utf = open(filename_test + '.test', "wb")
            test_utf.close()
            os.remove(filename_test + '.test')
            caller.UTF8_FS = True
        except UnicodeEncodeError:
            caller.UTF8_FS = False

    if not caller.UTF8_FS:
        filename_save = filename.encode('utf-8')  # For file operations, force the usage of a utf-8 encode filename

    while retry_count <= max_retry:
        res = None
        req = None
        try:
            try:
                if not overwrite and not config.alwaysCheckFileSize:
                    PixivHelper.print_and_log(None, '\rChecking local filename...', newline=False)
                    if os.path.isfile(filename_save):
                        PixivHelper.print_and_log('info', f"\rLocal file exists: {filename}")
                        return (PixivConstant.PIXIVUTIL_SKIP_DUPLICATE, filename_save)

                remote_file_size = get_remote_filesize(url, referer, config, notifier)

                # 576
                if remote_file_size > 0:
                    if config.minFileSize != 0 and remote_file_size <= config.minFileSize:
                        result = PixivConstant.PIXIVUTIL_SIZE_LIMIT_SMALLER
                        return (result, filename_save)
                    if config.maxFileSize != 0 and remote_file_size >= config.maxFileSize:
                        result = PixivConstant.PIXIVUTIL_SIZE_LIMIT_LARGER
                        return (result, filename_save)

                # check if existing ugoira file exists
                if filename.endswith(".zip"):
                    # non-converted zip (no animation.json)
                    if os.path.isfile(filename_save):
                        old_size = os.path.getsize(filename_save)
                        # update for #451, always return identical?
                        check_result = PixivHelper.check_file_exists(overwrite, filename_save, remote_file_size, old_size, backup_old_file)
                        if config.createUgoira:
                            handle_ugoira(image, filename_save, config, notifier)
                        return (check_result, filename)
                    # converted to ugoira (has animation.json)
                    ugo_name = filename[:-4] + ".ugoira"
                    if os.path.isfile(ugo_name):
                        old_size = PixivHelper.get_ugoira_size(ugo_name)
                        check_result = PixivHelper.check_file_exists(overwrite, ugo_name, remote_file_size, old_size, backup_old_file)
                        if check_result != PixivConstant.PIXIVUTIL_OK:
                            # try to convert existing file.
                            handle_ugoira(image, filename_save, config, notifier)

                            return (check_result, filename)
                elif os.path.isfile(filename_save):
                    # other image? files
                    old_size = os.path.getsize(filename_save)
                    check_result = PixivHelper.check_file_exists(overwrite, filename, remote_file_size, old_size, backup_old_file)
                    if check_result != PixivConstant.PIXIVUTIL_OK:
                        return (check_result, filename)

                # check based on filename stored in DB using image id
                if image is not None:
                    db_filename = None
                    if page is not None:
                        row = db.selectImageByImageIdAndPage(image.imageId, page)
                        if row is not None:
                            db_filename = row[2]
                    else:
                        row = db.selectImageByImageId(image.imageId)
                        if row is not None:
                            db_filename = row[3]
                    if db_filename is not None and os.path.isfile(db_filename):
                        old_size = os.path.getsize(db_filename)
                        # if file_size < 0:
                        #     file_size = get_remote_filesize(url, referer)
                        check_result = PixivHelper.check_file_exists(overwrite, db_filename, remote_file_size, old_size, backup_old_file)
                        if check_result != PixivConstant.PIXIVUTIL_OK:
                            ugo_name = None
                            if db_filename.endswith(".zip"):
                                ugo_name = filename[:-4] + ".ugoira"
                                if config.createUgoira:
                                    handle_ugoira(image, db_filename, config, notifier)
                            if db_filename.endswith(".ugoira"):
                                ugo_name = db_filename
                                handle_ugoira(image, db_filename, config, notifier)

                            return (check_result, db_filename)

                # actual download
                notifier(type="DOWNLOAD", message=f"Start downloading {url} to {filename_save}")
                (downloadedSize, filename_save) = perform_download(url, remote_file_size, filename_save, overwrite, config, referer)
                # set last-modified and last-accessed timestamp
                if image is not None and config.setLastModified and filename_save is not None and os.path.isfile(filename_save):
                    ts = time.mktime(image.worksDateDateTime.timetuple())
                    os.utime(filename_save, (ts, ts))

                # check the downloaded file size again
                if remote_file_size > 0 and downloadedSize != remote_file_size:
                    raise PixivException(f"Incomplete Downloaded for {url}", PixivException.DOWNLOAD_FAILED_OTHER)
                elif config.verifyImage and filename_save.endswith((".jpg", ".png", ".gif")):
                    fp = None
                    try:
                        from PIL import Image, ImageFile
                        fp = open(filename_save, "rb")
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
                        os.remove(filename_save)
                        raise
                elif config.verifyImage and filename_save.endswith((".ugoira", ".zip")):
                    fp = None
                    try:
                        import zipfile
                        fp = open(filename_save, "rb")
                        zf = zipfile.ZipFile(fp)
                        check_result = None
                        try:
                            check_result = zf.testzip()
                        except RuntimeError as e:
                            if 'encrypted' in str(e):
                                PixivHelper.print_and_log('info', ' archive is encrypted, cannot verify.')
                            else:
                                raise
                        fp.close()
                        if check_result is None:
                            PixivHelper.print_and_log('info', ' Image verified.')
                        else:
                            PixivHelper.print_and_log('info', f' Corrupted file in archive: {check_result}.')
                            raise PixivException(f"Incomplete Downloaded for {url}", PixivException.DOWNLOAD_FAILED_OTHER)
                    except BaseException:
                        if fp is not None:
                            fp.close()
                        PixivHelper.print_and_log('info', ' Image invalid, deleting...')
                        os.remove(filename_save)
                        raise
                else:
                    PixivHelper.print_and_log('info', ' done.')

                # write to downloaded lists
                if caller.start_iv or config.createDownloadLists:
                    dfile = codecs.open(caller.dfilename, 'a+', encoding='utf-8')
                    dfile.write(filename + "\n")
                    dfile.close()

                return (PixivConstant.PIXIVUTIL_OK, filename)

            except urllib.error.HTTPError as httpError:
                PixivHelper.print_and_log('error', f'[download_image()] HTTP Error: {httpError} at {url}')
                if httpError.code == 404 or httpError.code == 502 or httpError.code == 500:
                    return (PixivConstant.PIXIVUTIL_NOT_OK, None)
                temp_error_code = PixivException.DOWNLOAD_FAILED_NETWORK
                raise
            except urllib.error.URLError as urlError:
                PixivHelper.print_and_log('error', f'[download_image()] URL Error: {urlError} at {url}')
                temp_error_code = PixivException.DOWNLOAD_FAILED_NETWORK
                raise
            except IOError as ioex:
                if ioex.errno == 28:
                    PixivHelper.print_and_log('error', str(ioex))
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
            caller.ERROR_CODE = temp_error_code
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            PixivHelper.print_and_log('error', f'Error at download_image(): {sys.exc_info()} at {url} ({caller.ERROR_CODE})')

            if retry_count < max_retry:
                retry_count = retry_count + 1
                PixivHelper.print_and_log(None, f"\rRetrying [{retry_count}]...", newline=False)
                PixivHelper.print_delay(config.retryWait)
            else:
                raise


def perform_download(url, file_size, filename, overwrite, config, referer=None, notifier=None):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier

    if referer is None:
        referer = config.referer
    # actual download
    PixivHelper.print_and_log(None, '\rStart downloading...', newline=False)
    # fetch filesize
    req = PixivHelper.create_custom_request(url, config, referer)
    br = PixivBrowserFactory.getBrowser(config=config)
    res = br.open_novisit(req)
    if file_size < 0:
        try:
            content_length = res.info()['Content-Length']
            if content_length is not None:
                file_size = int(content_length)
        except KeyError:
            file_size = -1
            PixivHelper.print_and_log('info', "\tNo file size information!")
    (downloadedSize, filename) = PixivHelper.download_image(url, filename, res, file_size, overwrite)
    res.close()
    gc.collect()
    return (downloadedSize, filename)


# issue #299
def get_remote_filesize(url, referer, config, notifier=None):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier

    PixivHelper.print_and_log(None, 'Getting remote filesize...')
    # open with HEAD method, might be expensive
    req = PixivHelper.create_custom_request(url, config, referer, head=True)
    file_size = -1

    try:
        br = PixivBrowserFactory.getBrowser(config=config)
        res = br.open_novisit(req)
        content_length = res.info()['Content-Length']
        if content_length is not None:
            file_size = int(content_length)
        else:
            PixivHelper.print_and_log('info', "\tNo file size information!")
        res.close()
    except KeyError:
        PixivHelper.print_and_log('info', "\tNo file size information!")
    except mechanize.HTTPError as e:
        # fix Issue #503
        # handle http errors explicit by code
        if int(e.code) in (404, 500):
            PixivHelper.print_and_log('info', "\tNo file size information!")
        else:
            raise

    PixivHelper.print_and_log(None, f"Remote filesize = {PixivHelper.size_in_str(file_size)} ({file_size} Bytes)")
    return file_size


def handle_ugoira(image, filename, config, notifier):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier

    if filename.endswith(".zip"):
        ugo_name = filename[:-4] + ".ugoira"
    else:
        ugo_name = filename
    if not os.path.exists(ugo_name):
        PixivHelper.print_and_log('info', "Creating ugoira archive => " + ugo_name)
        image.CreateUgoira(filename)
        # set last-modified and last-accessed timestamp
        if config.setLastModified and ugo_name is not None and os.path.isfile(ugo_name):
            ts = time.mktime(image.worksDateDateTime.timetuple())
            os.utime(ugo_name, (ts, ts))

    if config.deleteZipFile and os.path.exists(filename):
        PixivHelper.print_and_log('info', "Deleting zip file => " + filename)
        os.remove(filename)

    if config.createGif:
        gif_filename = ugo_name[:-7] + ".gif"
        if not os.path.exists(gif_filename):
            PixivHelper.ugoira2gif(ugo_name, gif_filename, config.deleteUgoira, image=image)
    if config.createApng:
        gif_filename = ugo_name[:-7] + ".png"
        if not os.path.exists(gif_filename):
            PixivHelper.ugoira2apng(ugo_name, gif_filename, config.deleteUgoira, image=image)
    if config.createWebm:
        gif_filename = ugo_name[:-7] + ".webm"
        if not os.path.exists(gif_filename):
            PixivHelper.ugoira2webm(ugo_name,
                                gif_filename,
                                config.deleteUgoira,
                                config.ffmpeg,
                                config.ffmpegCodec,
                                config.ffmpegParam,
                                "webm",
                                image)
    if config.createWebp:
        gif_filename = ugo_name[:-7] + ".webp"
        if not os.path.exists(gif_filename):
            PixivHelper.ugoira2webm(ugo_name,
                                gif_filename,
                                config.deleteUgoira,
                                config.ffmpeg,
                                config.webpCodec,
                                config.webpParam,
                                "webp",
                                image)
