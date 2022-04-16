# -*- coding: utf-8 -*-
import datetime
import gc
import os
import re
import sys
import traceback
import pathlib
import urllib

from colorama import Fore, Style

import datetime_z
import PixivBrowserFactory
import PixivConstant
import PixivDownloadHandler
import PixivHelper
from PixivDBManager import PixivDBManager
from PixivException import PixivException

__re_manga_page = re.compile(r'(\d+(_big)?_p\d+)')


def process_image(caller,
                  config,
                  artist=None,
                  image_id=None,
                  user_dir='',
                  bookmark=False,
                  search_tags='',
                  title_prefix="",
                  bookmark_count=-1,
                  image_response_count=-1,
                  notifier=None,
                  useblacklist=True,
                  manga_series_order=-1,
                  manga_series_parent=None) -> int:
    # caller function/method
    # TODO: ideally to be removed or passed as argument
    db: PixivDBManager = caller.__dbManager__

    if notifier is None:
        notifier = PixivHelper.dummy_notifier

    # override the config source if job_option is give for filename formats
    extension_filter = None
    if hasattr(config, "extensionFilter"):
        extension_filter = config.extensionFilter

    parse_medium_page = None
    image = None
    result = None
    referer = f'https://www.pixiv.net/artworks/{image_id}'
    filename = f'no-filename-{image_id}.tmp'

    try:
        msg = Fore.YELLOW + Style.NORMAL + f'Processing Image Id: {image_id}' + Style.RESET_ALL
        PixivHelper.print_and_log(None, msg)
        notifier(type="IMAGE", message=msg)

        # check if already downloaded. images won't be downloaded twice - needed in process_image to catch any download
        r = db.selectImageByImageId(image_id, cols='save_name')
        exists = False
        in_db = False
        if r is not None:
            exists = db.cleanupFileExists(r[0])
            in_db = True

        # skip if already recorded in db and alwaysCheckFileSize is disabled and overwrite is disabled.
        if in_db and not config.alwaysCheckFileSize and not config.overwrite:
            PixivHelper.print_and_log(None, f'Already downloaded in DB: {image_id}')
            gc.collect()
            return PixivConstant.PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT

        # get the medium page
        try:
            (image, parse_medium_page) = PixivBrowserFactory.getBrowser().getImagePage(image_id=image_id,
                                                                                       parent=artist,
                                                                                       from_bookmark=bookmark,
                                                                                       bookmark_count=bookmark_count,
                                                                                       manga_series_order=manga_series_order,
                                                                                       manga_series_parent=manga_series_parent)
            if len(title_prefix) > 0:
                caller.set_console_title(f"{title_prefix} ImageId: {image.imageId}")
            else:
                caller.set_console_title(f"MemberId: {image.artist.artistId} ImageId: {image.imageId}")

        except PixivException as ex:
            caller.ERROR_CODE = ex.errorCode
            caller.__errorList.append(dict(type="Image", id=str(image_id), message=ex.message, exception=ex))
            if ex.errorCode == PixivException.UNKNOWN_IMAGE_ERROR:
                PixivHelper.print_and_log('error', ex.message)
            elif ex.errorCode == PixivException.SERVER_ERROR:
                PixivHelper.print_and_log('error', f'Giving up image_id (medium): {image_id}')
            elif ex.errorCode > 2000:
                PixivHelper.print_and_log('error', f'Image Error for {image_id}: {ex.message}')
            if parse_medium_page is not None:
                dump_filename = f'Error medium page for image {image_id}.html'
                PixivHelper.dump_html(dump_filename, parse_medium_page)
                PixivHelper.print_and_log('error', f'Dumping html to: {dump_filename}')
            else:
                PixivHelper.print_and_log('error', f'Image ID ({image_id}): {ex}')
            PixivHelper.print_and_log('error', f'Stack Trace: {sys.exc_info()}')
            return PixivConstant.PIXIVUTIL_NOT_OK
        except Exception as ex:
            PixivHelper.print_and_log('error', f'Image ID ({image_id}): {ex}')
            if parse_medium_page is not None:
                dump_filename = f'Error medium page for image {image_id}.html'
                PixivHelper.dump_html(dump_filename, parse_medium_page)
                PixivHelper.print_and_log('error', f'Dumping html to: {dump_filename}')
            PixivHelper.print_and_log('error', f'Stack Trace: {sys.exc_info()}')
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            return PixivConstant.PIXIVUTIL_NOT_OK

        download_image_flag = True

        # date validation and blacklist tag validation
        if config.dateDiff > 0:
            if image.worksDateDateTime != datetime.datetime.fromordinal(1).replace(tzinfo=datetime_z.utc):
                if image.worksDateDateTime < (datetime.datetime.today() - datetime.timedelta(config.dateDiff)).replace(tzinfo=datetime_z.utc):
                    PixivHelper.print_and_log('warn', f'Skipping image_id: {image_id} – it\'s older than: {config.dateDiff} day(s).')
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_OLDER

        if useblacklist:
            if config.useBlacklistMembers and download_image_flag:
                if str(image.originalArtist.artistId) in caller.__blacklistMembers:
                    PixivHelper.print_and_log('warn', f'Skipping image_id: {image_id} – blacklisted member id: {image.originalArtist.artistId}')
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST

            if config.useBlacklistTags and download_image_flag:
                for item in caller.__blacklistTags:
                    if item in image.imageTags:
                        PixivHelper.print_and_log('warn', f'Skipping image_id: {image_id} – blacklisted tag: {item}')
                        download_image_flag = False
                        result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST
                        break

            if config.useBlacklistTitles and download_image_flag:
                if config.useBlacklistTitlesRegex:
                    for item in caller.__blacklistTitles:
                        if re.search(rf"{item}", image.imageTitle):
                            PixivHelper.print_and_log('warn', f'Skipping image_id: {image_id} – Title matched: {item}')
                            download_image_flag = False
                            result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST
                            break
                else:
                    for item in caller.__blacklistTitles:
                        if item in image.imageTitle:
                            PixivHelper.print_and_log('warn', f'Skipping image_id: {image_id} – Title contained: {item}')
                            download_image_flag = False
                            result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST
                            break

        # Issue #726
        if extension_filter is not None and len(extension_filter) > 0:
            for url in image.imageUrls:
                ext = PixivHelper.get_extension_from_url(url)

                # add alias for ugoira
                if "ugoira" in extension_filter:
                    extension_filter = f"{extension_filter}|zip"

                if re.search(extension_filter, ext) is None:
                    download_image_flag = False
                    PixivHelper.print_and_log('warn', f'Skipping image_id: {image_id} - url is not in the filter: {extension_filter} => {url}')
                    break

        # issue #1027 filter by bookmark count
        if bookmark_count is not None and int(bookmark_count) > -1 and int(image.bookmark_count) < int(bookmark_count):
            download_image_flag = False
            PixivHelper.print_and_log('warn', f'Skipping image_id: {image_id} - post bookmark count {image.bookmark_count} is less than: {bookmark_count}')

        if download_image_flag:
            if artist is None:
                PixivHelper.print_and_log(None, f'Member Name  : {image.artist.artistName}')
                PixivHelper.print_and_log(None, f'Member Avatar: {image.artist.artistAvatar}')
                PixivHelper.print_and_log(None, f'Member Token : {image.artist.artistToken}')
                PixivHelper.print_and_log(None, f'Member Background : {image.artist.artistBackground}')

            PixivHelper.print_and_log(None, f"Title: {image.imageTitle}")
            if len(image.translated_work_title) > 0:
                PixivHelper.print_and_log(None, f"Translated Title: {image.translated_work_title}")
            tags_str = ', '.join(image.imageTags)
            PixivHelper.print_and_log(None, f"Tags : {tags_str}")
            PixivHelper.print_and_log(None, f"Date : {image.worksDateDateTime}")
            PixivHelper.print_and_log(None, f"Mode : {image.imageMode}")
            PixivHelper.print_and_log(None, f"Bookmark Count : {image.bookmark_count}")

            if config.useSuppressTags:
                for item in caller.__suppressTags:
                    if item in image.imageTags:
                        image.imageTags.remove(item)

            # get manga page
            if image.imageMode == 'manga':
                PixivHelper.print_and_log(None, f"Page Count : {image.imageCount}")

            if user_dir == '':  # Yavos: use config-options
                target_dir = config.rootDirectory
            else:  # Yavos: use filename from list
                target_dir = user_dir

            result = PixivConstant.PIXIVUTIL_OK
            manga_files = list()
            page = 0

            # Issue #639
            source_urls = image.imageUrls
            if config.downloadResized:
                source_urls = image.imageResizedUrls

            # debugging purpose, to avoid actual download
            if caller.DEBUG_SKIP_DOWNLOAD_IMAGE:
                return PixivConstant.PIXIVUTIL_OK

            for img in source_urls:
                PixivHelper.print_and_log(None, f'Image URL : {img}')
                url = os.path.basename(img)
                split_url = url.split('.')
                if split_url[0].startswith(str(image_id)):

                    filename_format = config.filenameFormat
                    if image.imageMode == 'manga':
                        filename_format = config.filenameMangaFormat

                    filename = PixivHelper.make_filename(filename_format,
                                                         image,
                                                         tagsSeparator=config.tagsSeparator,
                                                         tagsLimit=config.tagsLimit,
                                                         fileUrl=url,
                                                         bookmark=bookmark,
                                                         searchTags=search_tags,
                                                         useTranslatedTag=config.useTranslatedTag,
                                                         tagTranslationLocale=config.tagTranslationLocale)
                    filename = PixivHelper.sanitize_filename(filename, target_dir)

                    if image.imageMode == 'manga' and config.createMangaDir:
                        manga_page = __re_manga_page.findall(filename)
                        if len(manga_page) > 0:
                            splitted_filename = filename.split(manga_page[0][0], 1)
                            splitted_manga_page = manga_page[0][0].split("_p", 1)
                            # filename = splitted_filename[0] + splitted_manga_page[0] + os.sep + "_p" + splitted_manga_page[1] + splitted_filename[1]
                            filename = f"{splitted_filename[0]}{splitted_manga_page[0]}{os.sep}_p{splitted_manga_page[1]}{splitted_filename[1]}"

                    PixivHelper.print_and_log('info', f'Filename  : {filename}')

                    result = PixivConstant.PIXIVUTIL_NOT_OK
                    try:
                        (result, filename) = PixivDownloadHandler.download_image(caller,
                                                                                 img,
                                                                                 filename,
                                                                                 referer,
                                                                                 config.overwrite,
                                                                                 config.retry,
                                                                                 config.backupOldFile,
                                                                                 image,
                                                                                 page,
                                                                                 notifier)

                        if result == PixivConstant.PIXIVUTIL_NOT_OK:
                            PixivHelper.print_and_log('error', f'Image url not found/failed to download: {image.imageId}')
                        elif result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                            raise KeyboardInterrupt()

                        manga_files.append((image_id, page, filename))
                        page = page + 1

                    except urllib.error.URLError:
                        PixivHelper.print_and_log('error', f'Error when download_image(), giving up url: {img}')
                    PixivHelper.print_and_log(None, '')

                    if config.writeImageXMPPerImage:
                        filename_info_format = config.filenameInfoFormat or config.filenameFormat
                        # Issue #575
                        if image.imageMode == 'manga':
                            filename_info_format = config.filenameMangaInfoFormat or config.filenameMangaFormat or filename_info_format
                        info_filename = PixivHelper.make_filename(filename_info_format,
                                                                image,
                                                                tagsSeparator=config.tagsSeparator,
                                                                tagsLimit=config.tagsLimit,
                                                                fileUrl=url,
                                                                appendExtension=False,
                                                                bookmark=bookmark,
                                                                searchTags=search_tags,
                                                                useTranslatedTag=config.useTranslatedTag,
                                                                tagTranslationLocale=config.tagTranslationLocale)
                        info_filename = PixivHelper.sanitize_filename(info_filename, target_dir)
                        image.WriteXMP(info_filename + ".xmp")

            if config.writeImageInfo or config.writeImageJSON or config.writeImageXMP:
                filename_info_format = config.filenameInfoFormat or config.filenameFormat
                # Issue #575
                if image.imageMode == 'manga':
                    filename_info_format = config.filenameMangaInfoFormat or config.filenameMangaFormat or filename_info_format
                info_filename = PixivHelper.make_filename(filename_info_format,
                                                          image,
                                                          tagsSeparator=config.tagsSeparator,
                                                          tagsLimit=config.tagsLimit,
                                                          fileUrl=url,
                                                          appendExtension=False,
                                                          bookmark=bookmark,
                                                          searchTags=search_tags,
                                                          useTranslatedTag=config.useTranslatedTag,
                                                          tagTranslationLocale=config.tagTranslationLocale)
                info_filename = PixivHelper.sanitize_filename(info_filename, target_dir)
                # trim _pXXX
                info_filename = re.sub(r'_p?\d+$', '', info_filename)
                if config.writeImageInfo:
                    image.WriteInfo(info_filename + ".txt")
                if config.writeImageJSON:
                    image.WriteJSON(info_filename + ".json", config.RawJSONFilter)
                if config.includeSeriesJSON and image.seriesNavData and image.seriesNavData['seriesId'] not in caller.__seriesDownloaded:
                    json_filename = PixivHelper.make_filename(config.filenameSeriesJSON,
                                                              image,
                                                              fileUrl=url,
                                                              appendExtension=False
                                                              )
                    json_filename = PixivHelper.sanitize_filename(json_filename, target_dir)
                    # trim _pXXX
                    json_filename = re.sub(r'_p?\d+$', '', json_filename)
                    image.WriteSeriesData(image.seriesNavData['seriesId'], caller.__seriesDownloaded, json_filename + ".json")
                if config.writeImageXMP and not config.writeImageXMPPerImage:
                    image.WriteXMP(info_filename + ".xmp")

            if image.imageMode == 'ugoira_view':
                if config.writeUgoiraInfo:
                    image.WriteUgoiraData(filename + ".js")
                # Handle #451
                if config.createUgoira and (result in (PixivConstant.PIXIVUTIL_OK, PixivConstant.PIXIVUTIL_SKIP_DUPLICATE)):
                    PixivDownloadHandler.handle_ugoira(image, filename, config, notifier)

            if config.writeUrlInDescription:
                PixivHelper.write_url_in_description(image, config.urlBlacklistRegex, config.urlDumpFilename)

        if in_db and not exists:
            result = PixivConstant.PIXIVUTIL_CHECK_DOWNLOAD  # There was something in the database which had not been downloaded

        # Only save to db if all images is downloaded completely
        if result in (PixivConstant.PIXIVUTIL_OK,
                      PixivConstant.PIXIVUTIL_SKIP_DUPLICATE,
                      PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER):
            try:
                db.insertImage(image.artist.artistId, image.imageId, image.imageMode)
            except BaseException:
                PixivHelper.print_and_log('error', f'Failed to insert image id:{image.imageId} to DB')

            db.updateImage(image.imageId, image.imageTitle, filename, image.imageMode)

            if len(manga_files) > 0:
                db.insertMangaImages(manga_files)

            # map back to PIXIVUTIL_OK (because of ugoira file check)
            result = 0

        if image is not None:
            del image
        if parse_medium_page is not None:
            del parse_medium_page
        gc.collect()
        PixivHelper.print_and_log(None, '\n')

        return result
    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        caller.ERROR_CODE = getattr(ex, 'errorCode', -1)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        PixivHelper.print_and_log('error', f'Error at process_image(): {image_id}')
        PixivHelper.print_and_log('error', f'Exception: {sys.exc_info()}')

        if parse_medium_page is not None:
            dump_filename = f'Error medium page for image {image_id}.html'
            PixivHelper.dump_html(dump_filename, parse_medium_page)
            PixivHelper.print_and_log('error', f'Dumping html to: {dump_filename}')

        raise


def process_manga_series(caller,
                         config,
                         manga_series_id: int,
                         start_page: int = 1,
                         end_page: int = 0,
                         notifier=None):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier
    try:
        msg = Fore.YELLOW + Style.NORMAL + f'Processing Manga Series Id: {manga_series_id}' + Style.RESET_ALL
        PixivHelper.print_and_log(None, msg)
        notifier(type="MANGA_SERIES", message=msg)

        if start_page != 1:
            PixivHelper.print_and_log('info', 'Start Page: ' + str(start_page))
        if end_page != 0:
            PixivHelper.print_and_log('info', 'End Page: ' + str(end_page))

        flag = True
        current_page = start_page
        while flag:
            manga_series = PixivBrowserFactory.getBrowser().getMangaSeries(manga_series_id, current_page)
            for (image_id, order) in manga_series.pages_with_order:
                result = process_image(caller,
                                       config,
                                       artist=manga_series.artist,
                                       image_id=image_id,
                                       user_dir='',
                                       bookmark=False,
                                       search_tags='',
                                       title_prefix="",
                                       bookmark_count=-1,
                                       image_response_count=-1,
                                       notifier=notifier,
                                       useblacklist=True,
                                       manga_series_order=order,
                                       manga_series_parent=manga_series)
                PixivHelper.wait(result, config)
            current_page += 1
            if manga_series.is_last_page:
                PixivHelper.print_and_log('info', f'Last Page {manga_series.current_page}')
                flag = False
            if current_page > end_page and end_page != 0:
                PixivHelper.print_and_log('info', f'End Page reached {end_page}')
                flag = False
            if manga_series.pages_with_order is None or len(manga_series.pages_with_order) == 0:
                PixivHelper.print_and_log('info', 'No more works.')
                flag = False

    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        caller.ERROR_CODE = getattr(ex, 'errorCode', -1)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        PixivHelper.print_and_log('error', f'Error at process_manga_series(): {manga_series_id}')
        PixivHelper.print_and_log('error', f'Exception: {sys.exc_info()}')
        raise

def process_ugoira_local(caller, config):
    directory = config.rootDirectory
    counter = 0

    try:
        print('')
        counter = 0
        for zip in pathlib.Path(directory).rglob('*.zip'):
            counter += 1
            PixivHelper.print_and_log(None, f"# Ugoira {counter}")
            zip_name = os.path.splitext(os.path.basename(zip))[0]
            PixivHelper.print_and_log("info", f"Deleting old ugoira files ...", newline = False)
            for file in pathlib.Path(os.path.dirname(zip)).rglob(f'{zip_name}.*'):
                file_ext = os.path.splitext(os.path.basename(file))[1]
                if  ((("ugoira" in file_ext) and (config.createUgoira))     or
                    (("gif" in file_ext) and (config.createGif))            or
                    (("png" in file_ext) and (config.createApng))           or
                    (("webm" in file_ext) and (config.createWebm))          or
                    (("webp" in file_ext) and (config.createWebp))):
                    abs_file_path = os.path.abspath(file)
                    PixivHelper.print_and_log("debug", f"Deleting {abs_file_path}")
                    os.remove(abs_file_path)
            PixivHelper.print_and_log(None, f" done.")
            # Get id artwork
            image_id = zip_name.partition("_")[0]
            process_image(  caller,
                            config,
                            artist=None,
                            image_id=image_id,
                            useblacklist=False)
        if counter == 0:
            PixivHelper.print_and_log('info', "No zip file found for re-encoding ugoira.")

    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        PixivHelper.print_and_log('error', 'Error at process_ugoira_local(): %s' %str(sys.exc_info()))
        PixivHelper.print_and_log('error', 'failed')
        raise
