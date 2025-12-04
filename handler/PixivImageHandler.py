# -*- coding: utf-8 -*-
import datetime
import gc
import os
import re
import sys
import shutil
import tempfile
import time
import traceback
import pathlib
from typing import Dict
from urllib.error import URLError
import zipfile

from colorama import Fore, Style

import common.datetime_z as datetime_z
import common.PixivBrowserFactory as PixivBrowserFactory
import common.PixivConstant as PixivConstant
import handler.PixivDownloadHandler as PixivDownloadHandler
import common.PixivHelper as PixivHelper
from PixivDBManager import PixivDBManager
from common.PixivException import PixivException

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
                  reencoding=False,
                  manga_series_order=-1,
                  manga_series_parent=None,
                  ui_prefix="",
                  is_unlisted=False) -> int:
    # caller function/method
    # TODO: ideally to be removed or passed as argument
    db: PixivDBManager = caller.__dbManager__
    relative_download_dir: str = None                           # relative path to the archive root directory for downloaded files

    # Pixiv archive mode specific configuration extraction.
    is_archive_mode: bool = bool(config.createPixivArchive)
    archive_mode_compression_type: str = config.createPixivArchiveCompressionType
    archive_mode_compression_level: int = config.createPixivArchiveCompressionLevel
    archive_mode_zip_filepath: str = None                       # actual archive path that we're downloading to
    archive_mode_temp_dir: str = None                           # temp directory for everything
    archive_mode_temp_download_root_dir: str = None             # temp root directory for downloaded files
    archive_mode_temp_zip_filepath: str = None                  # temp zip archive for downloaded files
    archive_mode_update_manga_image_paths: bool = False         # whether to update manga image paths instead of ignore
    page_number_to_filename_map: Dict[int, str] = {}            # map of page number to filename (in the temp directory)
    page_number_to_database_path_map: Dict[int, str] = {}       # map of page number to database path

    if notifier is None:
        notifier = PixivHelper.dummy_notifier

    # If downloading to an archive, setup temporary root and download directories.
    # build the archive path.
    if is_archive_mode:

        # Sanity checks
        # acceptable formats for filenameFormat and filenameMangaFormat
        # %member_id%_%image_id%/page_%page_number%
        # %member_id%/%image_id%/page_%page_number%
        for __format in [config.filenameFormat, config.filenameMangaFormat]:
            if os.sep not in __format:
                # Archive mode requires separation between the archive file and the file contents in it.
                # Generally, page numbers should be included in the filename.
                raise ValueError("filenameFormat must contain a path separator when using archive mode.")
            if "%page_number%" not in __format.split(os.sep)[-1]:
                # If some user decides to put page_number in a directory, then I don't know what I'm going to do.
                raise ValueError("filenameFormat must contain %page_no% in filename when using archive mode.")

        archive_mode_temp_dir = tempfile.mkdtemp(prefix='pixivutil_archive_')
        archive_mode_temp_download_root_dir = os.path.join(archive_mode_temp_dir, 'download')
        archive_mode_temp_zip_filepath = os.path.join(archive_mode_temp_dir, 'archive.zip')
        os.makedirs(archive_mode_temp_download_root_dir, exist_ok=True)

    # override the config source if job_option is give for filename formats
    extension_filter = None
    if hasattr(config, "extensionFilter"):
        extension_filter = config.extensionFilter

    parse_medium_page = None
    image = None
    result = None
    if not is_unlisted:
        # https://www.pixiv.net/en/artworks/76656661
        referer = f"https://www.pixiv.net/artworks/{image_id}"
    else:
        # https://www.pixiv.net/artworks/unlisted/SbliQHtJS5MMu3elqDFZ
        referer = f"https://www.pixiv.net/artworks/unlisted/{image_id}"
    filename = f'no-filename-{image_id}.tmp'

    try:
        msg = ui_prefix + Fore.YELLOW + Style.NORMAL + f'Processing Image Id: {image_id}' + Style.RESET_ALL
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
        if in_db and not config.alwaysCheckFileSize and not config.overwrite and not reencoding:
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
                                                                                       manga_series_parent=manga_series_parent,
                                                                                       is_unlisted=is_unlisted)
            if len(title_prefix) > 0:
                caller.set_console_title(f"{title_prefix} ImageId: {image.imageId}")
            else:
                assert (image.artist is not None)
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

        # feature #1189 AI filtering
        if config.aiDisplayFewer and image.ai_type == 2:
            PixivHelper.print_and_log('warn', f'Skipping image_id: {image_id} – blacklisted due to aiDisplayFewer is set to True and aiType = {image.ai_type}.')
            download_image_flag = False
            result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST

        # date validation and blacklist tag validation
        if config.dateDiff > 0:
            if image.worksDateDateTime is not None and image.worksDateDateTime != datetime.datetime.fromordinal(1).replace(tzinfo=datetime_z.utc):
                if image.worksDateDateTime < (datetime.datetime.today() - datetime.timedelta(config.dateDiff)).replace(tzinfo=datetime_z.utc):
                    PixivHelper.print_and_log('warn', f'Skipping image_id: {image_id} – it\'s older than: {config.dateDiff} day(s).')
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_OLDER

        if useblacklist:
            if config.useBlacklistMembers and download_image_flag:
                if image.originalArtist is not None and str(image.originalArtist.artistId) in caller.__blacklistMembers:
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

            # Issue #439
            if config.r18Type == 1 and download_image_flag:
                # only download R18 if r18Type = 1
                if 'R-18G' in (tag.upper() for tag in image.imageTags):
                    PixivHelper.print_and_log('warn', f'Skipping image_id: {image_id} because it has R-18G tag.')
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST
            elif config.r18Type == 2 and download_image_flag:
                # only download R18G if r18Type = 2
                if 'R-18' in (tag.upper() for tag in image.imageTags):
                    PixivHelper.print_and_log('warn', f'Skipping image_id: {image_id} because it has R-18 tag.')
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST

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
            if artist is None and image.artist is not None:
                PixivHelper.print_and_log(None, f'{Fore.LIGHTCYAN_EX}{"Member Name":14}:{Style.RESET_ALL} {image.artist.artistName}')
                PixivHelper.print_and_log(None, f'{Fore.LIGHTCYAN_EX}{"Member Avatar":14}:{Style.RESET_ALL} {image.artist.artistAvatar}')
                PixivHelper.print_and_log(None, f'{Fore.LIGHTCYAN_EX}{"Member Token":14}:{Style.RESET_ALL} {image.artist.artistToken}')
                PixivHelper.print_and_log(None, f'{Fore.LIGHTCYAN_EX}{"Member Backgrd":14}:{Style.RESET_ALL} {image.artist.artistBackground}')

            PixivHelper.print_and_log(None, f"{Fore.LIGHTCYAN_EX}{'Title':10}:{Style.RESET_ALL} {image.imageTitle}")
            if len(image.translated_work_title) > 0:
                PixivHelper.print_and_log(None, f"{Fore.LIGHTCYAN_EX}{'TL-ed Title':10}: {image.translated_work_title}")
            tags_str = ', '.join(image.imageTags).replace("AI-generated", f"{Fore.LIGHTYELLOW_EX}AI-generated{Style.RESET_ALL}")
            PixivHelper.print_and_log(None, f"{Fore.LIGHTCYAN_EX}{'Tags':10}:{Style.RESET_ALL} {tags_str}")
            PixivHelper.print_and_log(None, f"{Fore.LIGHTCYAN_EX}{'Date':10}:{Style.RESET_ALL} {image.worksDateDateTime}")
            PixivHelper.print_and_log(None, f"{Fore.LIGHTCYAN_EX}{'Mode':10}:{Style.RESET_ALL} {image.imageMode}")
            PixivHelper.print_and_log(None, f"{Fore.LIGHTCYAN_EX}{'Bookmarks':10}:{Style.RESET_ALL} {image.bookmark_count}")

            if config.useSuppressTags:
                for item in caller.__suppressTags:
                    if item in image.imageTags:
                        image.imageTags.remove(item)

            # get manga page
            if image.imageMode == 'manga':
                PixivHelper.print_and_log(None, f"{Fore.LIGHTCYAN_EX}{'Pages':10}:{Style.RESET_ALL} {image.imageCount}")

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

            # Get all the directory-related archive-mode info we can right now.
            # TODO: this is kind of a hack so we can get relative path
            relative_download_dir = os.path.dirname(PixivHelper.make_filename(config.filenameFormat,
                                                    image,
                                                    tagsSeparator=config.tagsSeparator,
                                                    tagsLimit=config.tagsLimit,
                                                    fileUrl=source_urls[0],
                                                    bookmark=bookmark,
                                                    searchTags=search_tags,
                                                    useTranslatedTag=config.useTranslatedTag,
                                                    tagTranslationLocale=config.tagTranslationLocale))
            archive_mode_zip_filepath = os.path.abspath(os.path.join(target_dir, relative_download_dir + ".zip"))
            # if not config.overwrite and os.path.exists(archive_mode_zip_filepath):
            #     PixivHelper.print_and_log('info', f'Archive exists for image {image_id}, skipping download.')
            #     return PixivConstant.PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT
            target_download_dir = os.path.join(target_dir, relative_download_dir)
            if is_archive_mode:
                target_dir = archive_mode_temp_download_root_dir  # this needs to be root dir so that the later make_filename logic is consistent.
            if in_db:
                _filepath_from_db: str = r[0]
                if is_archive_mode:
                    # If the archive is already downloaded, put its contents into the download directory
                    # this will be the "pretend" directory that PixivUtil is downloading to, so we get feature parity.
                    # e.g. skip downloaded files, etc.
                    # TODO: figure out how to skip downloaded ugoira files. Currently database will only show the zip file, so
                    # non-zip files like .gif will be downloaded again.
                    archive_mode_download_dir = os.path.join(archive_mode_temp_download_root_dir, relative_download_dir)
                    if archive_mode_zip_filepath != _filepath_from_db:
                        # This can happen if the user changes the filename format, causing the calculated archive path to be different
                        # from what is in the database. In this case, we should just download the archive as if it were a new download,
                        # even if it might be slower. This is because changes in the filename format may also result in changes in the actual
                        # image filenames too.
                        PixivHelper.print_and_log('warn', f'Archive path mismatch for image {image_id}, expected {archive_mode_zip_filepath} but got {_filepath_from_db}.')
                        in_db = False
                        archive_mode_update_manga_image_paths = True
                    elif zipfile.is_zipfile(_filepath_from_db) and exists:
                        PixivHelper.print_and_log('info', f'Archive exists for image {image_id}, extracting contents to {archive_mode_download_dir}')
                        with zipfile.ZipFile(archive_mode_zip_filepath, 'r') as zip_file:
                            zip_file.extractall(archive_mode_download_dir)
                            for __zip_info in zip_file.infolist():
                                if not __zip_info.is_dir():
                                    __extracted_path = os.path.join(archive_mode_download_dir, __zip_info.filename)
                                    __timestamp = time.mktime(__zip_info.date_time + (0, 0, -1))
                                    os.utime(__extracted_path, (__timestamp, __timestamp))
                            PixivHelper.print_and_log('debug', f'Extracted archive contents to {archive_mode_download_dir}')
                            existing_images = db.selectImagesByImageId(image_id)
                            for __image in existing_images:
                                save_name = __image[2]
                                _extracted_filepath = os.path.join(archive_mode_download_dir, save_name)
                                if os.path.exists(_extracted_filepath) and os.path.isfile(_extracted_filepath):
                                    PixivHelper.print_and_log('debug', f"Copied {save_name} to {_extracted_filepath}")
                                    page_number_to_database_path_map[__image[1]] = save_name
                                    page_number_to_filename_map[__image[1]] = _extracted_filepath
                            # get rid of files that are not in the database.
                            for __file in os.listdir(archive_mode_download_dir):
                                __filepath = os.path.join(archive_mode_download_dir, __file)
                                if os.path.isfile(__filepath) and __filepath not in page_number_to_filename_map.values():
                                    os.remove(__filepath)
                                    PixivHelper.print_and_log('info', f"Removed orphan file {__filepath}.")
                    elif os.path.isdir(os.path.dirname(_filepath_from_db)):
                        # A non-zip file exists. This is probably an artwork directory from a previous run.
                        # In this case, we will attempt to use existing files in the same directory to populate the archive, and use it to save
                        # download time. HOWEVER, this means we have both an archive and a directory for the same image.
                        # Maybe the user should be responsible for cleaning up the duplicate, or we could delete the archive...?
                        # If the user ALSO changes filenameformat, then we are truly screwed...
                        # The ideal solution would be to run archive mode on a clean directory, or manually migrate between modes.
                        if not exists:
                            PixivHelper.print_and_log('info', f"File in database {_filepath_from_db} does not exist in local filesystem.")
                            in_db = False
                        PixivHelper.print_and_log('info', f"Getting existing artwork images from database with image ID {image_id}")
                        os.makedirs(archive_mode_download_dir, exist_ok=True)
                        archive_mode_update_manga_image_paths = True
                        existing_images = db.selectImagesByImageId(image_id)
                        if len(existing_images) == 0:
                            PixivHelper.print_and_log('warn', f"No images found for image {image_id} in database.")
                            in_db = False
                        for __image in existing_images:
                            save_name = __image[2]
                            if os.path.exists(save_name) and os.path.isfile(save_name):
                                shutil.copy2(save_name, archive_mode_download_dir)
                                PixivHelper.print_and_log('info', f"Copied {save_name} to {archive_mode_download_dir}")
                                page_number_to_database_path_map[__image[1]] = save_name
                                page_number_to_filename_map[__image[1]] = os.path.join(archive_mode_download_dir, os.path.basename(save_name))
                    elif exists:
                        raise TypeError(f"Existing object is not a zip file or directory: {_filepath_from_db}")
                    else:
                        # We should just mark everything as if we are downloading for the first time.
                        PixivHelper.print_and_log('warn', f"File in database {_filepath_from_db} does not exist in local filesystem. Downloading from scratch.")
                        in_db = False
                        archive_mode_update_manga_image_paths = True
                else:
                    # On the other hand, if archive mode is False but we have an archive in the database, we should also use the archive, and
                    # rewrite the manga save names to point to their place in the directory.
                    if exists and zipfile.is_zipfile(_filepath_from_db):
                        PixivHelper.print_and_log('info', f"Archive exists for image {image_id}, attempting to extract contents to {target_download_dir}...")
                        with zipfile.ZipFile(_filepath_from_db, 'r') as zip_file:
                            zip_file.extractall(target_download_dir)
                            for __zip_info in zip_file.infolist():
                                if not __zip_info.is_dir():
                                    __extracted_path = os.path.join(target_download_dir, __zip_info.filename)
                                    __timestamp = time.mktime(__zip_info.date_time + (0, 0, -1))
                                    os.utime(__extracted_path, (__timestamp, __timestamp))
                            PixivHelper.print_and_log('info', f'Extracted archive contents to {target_download_dir}')
                            archive_mode_update_manga_image_paths = True
                    elif _filepath_from_db.lower().endswith('.zip') and not exists:
                        # If the user previously downloaded an artwork as an archive but deleted it for some reason,
                        # we should consider it as a new download and mark in_db = False, and also change the manga save names.
                        # We can also remove it from database via db.deleteImage(image_id), but
                        # this would also remove metadata, so let's not do that.
                        PixivHelper.print_and_log('info', f"Archive {_filepath_from_db} existed in database but is no longer in filesystem.")
                        in_db = False
                        archive_mode_update_manga_image_paths = True
                del _filepath_from_db

            current_img = 1
            total = len(source_urls)
            for img in source_urls:
                prefix = f"{Fore.CYAN}[{current_img}/{total}]{Style.RESET_ALL} "
                PixivHelper.print_and_log(None, f'{prefix}Image URL : {img}')
                url = os.path.basename(img)
                # split_url = url.split('.')
                # if split_url[0].startswith(str(image_id)):
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

                PixivHelper.print_and_log('info', f'{prefix}Filename  : {filename}')

                # Handle changes to filename format.
                if is_archive_mode and page in page_number_to_filename_map:
                    if filename != page_number_to_filename_map[page]:
                        PixivHelper.print_and_log('info', f'Database filename changed from {os.path.basename(page_number_to_database_path_map[page])} to {os.path.basename(filename)}')
                        archive_mode_update_manga_image_paths = True
                        shutil.move(page_number_to_filename_map[page], filename)

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

                    if is_archive_mode:
                        # set file path relative to its containing archive.
                        # for some reason .gif files are saved as .zip files, but it's also the same in non-archive mode, so
                        # not much to do about it.
                        manga_files.append((image_id, page, os.path.basename(filename)))
                    else:
                        manga_files.append((image_id, page, filename))
                    page = page + 1

                except URLError:
                    PixivHelper.print_and_log('error', f'Error when download_image(), giving up url: {img}')
                PixivHelper.print_and_log(None, '')

                # XMP image info per images
                if config.writeImageXMPPerImage:
                    filename_info_format = config.filenameInfoFormat or config.filenameFormat
                    # Issue #575
                    if image.imageMode == 'manga':
                        filename_info_format = config.filenameMangaInfoFormat or config.filenameMangaFormat or filename_info_format
                    # If we are creating an ugoira, we need to create side-car metadata for each converted file.
                    if image.imageMode == 'ugoira_view':
                        def get_info_filename(extension):
                            fileUrl = os.path.splitext(url)[0] + "." + extension
                            info_filename = PixivHelper.make_filename(filename_info_format,
                                            image,
                                            tagsSeparator=config.tagsSeparator,
                                            tagsLimit=config.tagsLimit,
                                            fileUrl=fileUrl,
                                            appendExtension=False,
                                            bookmark=bookmark,
                                            searchTags=search_tags,
                                            useTranslatedTag=config.useTranslatedTag,
                                            tagTranslationLocale=config.tagTranslationLocale)
                            return PixivHelper.sanitize_filename(info_filename + ".xmp", target_dir)
                        if config.createGif:
                            info_filename = get_info_filename("gif")
                            image.WriteXMP(info_filename, config.useTranslatedTag, config.tagTranslationLocale)
                        if config.createApng:
                            info_filename = get_info_filename("apng")
                            image.WriteXMP(info_filename, config.useTranslatedTag, config.tagTranslationLocale)
                        if config.createAvif:
                            info_filename = get_info_filename("avif")
                            image.WriteXMP(info_filename, config.useTranslatedTag, config.tagTranslationLocale)
                        if config.createWebm:
                            info_filename = get_info_filename("webm")
                            image.WriteXMP(info_filename, config.useTranslatedTag, config.tagTranslationLocale)
                        if config.createWebp:
                            info_filename = get_info_filename("webp")
                            image.WriteXMP(info_filename, config.useTranslatedTag, config.tagTranslationLocale)
                        if config.createMkv:
                            info_filename = get_info_filename("mkv")
                            image.WriteXMP(info_filename, config.useTranslatedTag, config.tagTranslationLocale)
                        if not config.deleteZipFile:
                            info_filename = get_info_filename("zip")
                            image.WriteXMP(info_filename, config.useTranslatedTag, config.tagTranslationLocale)
                        if not config.deleteUgoira:
                            info_filename = get_info_filename("ugoira")
                            image.WriteXMP(info_filename, config.useTranslatedTag, config.tagTranslationLocale)
                    else:
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
                        info_filename = PixivHelper.sanitize_filename(info_filename + ".xmp", target_dir)
                        image.WriteXMP(info_filename, config.useTranslatedTag, config.tagTranslationLocale)
                current_img = current_img + 1

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
                if image.imageMode == 'manga':
                    # trim _pXXX for manga
                    info_filename = re.sub(r'_p?\d+$', '', info_filename)
                info_filename = PixivHelper.sanitize_filename(info_filename + ".infoext", target_dir)
                if config.writeImageInfo:
                    image.WriteInfo(info_filename[:-8] + ".txt")
                if config.writeImageJSON:
                    image.WriteJSON(info_filename[:-8] + ".json", config.RawJSONFilter, config.useTranslatedTag, config.tagTranslationLocale)
                if config.includeSeriesJSON and image.seriesNavData and image.seriesNavData['seriesId'] not in caller.__seriesDownloaded:
                    json_filename = PixivHelper.make_filename(config.filenameSeriesJSON, image, fileUrl=url, appendExtension=False)
                    if image.imageMode == 'manga':
                        # trim _pXXX for manga
                        json_filename = re.sub(r'_p?\d+$', '', json_filename)
                    json_filename = PixivHelper.sanitize_filename(json_filename + ".json", target_dir)
                    image.WriteSeriesData(image.seriesNavData['seriesId'], caller.__seriesDownloaded, json_filename)
                if config.writeImageXMP and not config.writeImageXMPPerImage:
                    image.WriteXMP(info_filename[:-8] + ".xmp", config.useTranslatedTag, config.tagTranslationLocale)

            if image.imageMode == 'ugoira_view':
                if config.writeUgoiraInfo:
                    image.WriteUgoiraData(filename + ".js")
                # Handle #451
                if config.createUgoira and (result in (PixivConstant.PIXIVUTIL_OK, PixivConstant.PIXIVUTIL_SKIP_DUPLICATE)):
                    PixivDownloadHandler.handle_ugoira(image, filename, config, notifier)

            if config.writeUrlInDescription:
                PixivHelper.write_url_in_description(image, config.urlBlacklistRegex, config.urlDumpFilename)

            if is_archive_mode:
                # Move the files from the temp download directory to a temp zip archive, then move temp zip archive to original target directory.
                # Make sure that the compression type and level are correct combinations otherwise you'll probably get a RuntimeError.
                filename = archive_mode_zip_filepath
                os.makedirs(os.path.dirname(archive_mode_zip_filepath), exist_ok=True)
                archived_count = 0
                compression = zipfile.ZIP_STORED
                match archive_mode_compression_type:
                    case "ZIP_STORED":
                        compression = zipfile.ZIP_STORED
                    case "ZIP_DEFLATED":
                        compression = zipfile.ZIP_DEFLATED
                    case "ZIP_BZIP2":
                        compression = zipfile.ZIP_BZIP2
                    case "ZIP_LZMA":
                        compression = zipfile.ZIP_LZMA
                    case _:
                        raise ValueError(f'Invalid compression type: {archive_mode_compression_type}')
                with zipfile.ZipFile(archive_mode_temp_zip_filepath, 'w', compression=compression, compresslevel=archive_mode_compression_level) as zip_file:
                    _downloaded_dir = os.path.join(archive_mode_temp_download_root_dir, relative_download_dir)
                    for file in os.listdir(_downloaded_dir):
                        if not os.path.isfile(os.path.join(_downloaded_dir, file)):
                            continue
                        zip_file.write(os.path.join(_downloaded_dir, file), file)
                        PixivHelper.print_and_log('debug', f'Archived: {file}')
                        archived_count += 1
                if archived_count == total:
                    PixivHelper.print_and_log('info', f'Moved {archived_count} files to archive: {archive_mode_zip_filepath}')
                    shutil.move(archive_mode_temp_zip_filepath, archive_mode_zip_filepath)
                    if in_db and not exists:
                        # This can happen if the user previously downloaded an artwork as a directory, deleted some images, then downloads
                        # the artwork as an archive.
                        # Because the database saves the last image path, it is possible that in_db = True but exists = False.
                        # We need to tell the database that yes the archive exists and download is complete, otherwise it triggers
                        # PixivConstant.PIXIVUTIL_CHECK_DOWNLOAD error.
                        exists = True
                else:
                    PixivHelper.print_and_log('error', f"Files archived does not match total. Expected {total} but got {archived_count}.")
                    result = PixivConstant.PIXIVUTIL_NOT_OK

        # Save AI type to DB
        db.insertAiInfo(image_id, image.ai_type)

        if in_db and not exists:
            result = PixivConstant.PIXIVUTIL_CHECK_DOWNLOAD  # There was something in the database which had not been downloaded

        # Only save to db if all images is downloaded completely
        if result in (PixivConstant.PIXIVUTIL_OK,
                      PixivConstant.PIXIVUTIL_SKIP_DUPLICATE,
                      PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER):
            caption = image.imageCaption if config.autoAddCaption else ""
            try:
                assert (image.artist is not None)
                db.insertImage(image.artist.artistId, image.imageId, image.imageMode, caption=caption)
            except BaseException:
                PixivHelper.print_and_log('error', f'Failed to insert image id:{image.imageId} to DB')

            db.updateImage(image.imageId, image.imageTitle, filename, image.imageMode)

            if len(manga_files) > 0:
                if archive_mode_update_manga_image_paths:
                    # Rewrite manga save names to point to their place in the archive.
                    db.upsertMangaImage(manga_files)
                else:
                    db.insertMangaImages(manga_files)

            # Save tags if enabled
            if config.autoAddTag:
                tags = image.tags
                if tags:
                    for tag_data in tags:
                        tag_id = tag_data.tag
                        if tag_id:
                            db.insertTag(tag_id)
                            db.insertImageToTag(image_id, tag_id)
                            if tag_data.romaji:
                                db.insertTagTranslation(tag_id, 'romaji', tag_data.romaji)
                            if tag_data.translation_data:
                                for locale in tag_data.translation_data:
                                    db.insertTagTranslation(tag_id, locale, tag_data.translation_data[locale])

            # Save series data if enabled.
            if config.autoAddSeries and (seriesNavData := image.seriesNavData):
                seriesId = seriesNavData.get("seriesId")
                seriesType = seriesNavData.get("seriesType")
                seriesTitle = seriesNavData.get("title")
                seriesOrder = seriesNavData.get("order")
                if isinstance(seriesId, str) and seriesId.isdigit() and seriesType and seriesTitle and isinstance(seriesOrder, int):
                    seriesId = int(seriesId)
                    db.insertSeries(seriesId, seriesTitle, seriesType)
                    db.insertImageToSeries(image_id, seriesId, seriesOrder)

            # Save member data if enabled
            if image.artist is not None and config.autoAddMember:
                member_id = image.artist.artistId
                member_token = image.artist.artistToken
                member_name = image.artist.artistName
                if member_id and member_token and member_name:
                    db.insertNewMember(int(member_id), member_token=member_token)
                    db.updateMemberName(member_id, member_name, member_token)

            # map back to PIXIVUTIL_OK (because of ugoira file check)
            result = 0

        if image is not None:
            del image
        if parse_medium_page is not None:
            del parse_medium_page
        gc.collect()

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
    finally:
        # Image handling cleanup logic
        if archive_mode_temp_dir and os.path.isdir(archive_mode_temp_dir):
            PixivHelper.print_and_log('debug', f'Cleaning up temporary directory: {archive_mode_temp_dir} ...')
            shutil.rmtree(archive_mode_temp_dir)


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
    d = ""
    res = None
    counter = 0
    list_done = list()

    try:
        print('')
        for extension in ["ugoira", "zip"]:  # always ugoira then zip
            for zip in pathlib.Path(directory).rglob(f'*.{extension}'):
                zip_name = os.path.splitext(os.path.basename(zip))[0]
                zip_dir = os.path.dirname(zip)
                image_id = zip_name.partition("_")[0]
                if 'ugoira' in zip_name and image_id not in list_done:
                    counter += 1
                    PixivHelper.print_and_log(None, f"# Ugoira {counter}")
                    PixivHelper.print_and_log("info", "Deleting old animated files ...", newline=False)
                    d = PixivHelper.create_temp_dir(prefix="reencoding")

                    # List and move all files related to the image_id
                    for file in os.listdir(zip_dir):
                        if os.path.isfile(os.path.join(zip_dir, file)) and zip_name in file:
                            file_basename = os.path.basename(file)
                            file_ext = os.path.splitext(file_basename)[1]
                            if ((("gif" in file_ext) and (config.createGif))
                               or (("mkv" in file_ext) and (config.createMkv))
                               or (("png" in file_ext) and (config.createApng))
                               or (("avif" in file_ext) and (config.createAvif))
                               or (("webm" in file_ext) and (config.createWebm))
                               or (("webp" in file_ext) and (config.createWebp))
                               or (("ugoira" in file_ext) and (config.createUgoira))
                               or ("zip" in file_ext)):
                                abs_file_path = os.path.abspath(os.path.join(zip_dir, file))
                                PixivHelper.print_and_log("debug", f"Moving {abs_file_path} to {d}")
                                if ("zip" in file_ext) or ("ugoira" in file_ext):
                                    shutil.copy2(abs_file_path, os.path.join(d, file_basename))
                                else:
                                    shutil.move(abs_file_path, os.path.join(d, file_basename))
                    PixivHelper.print_and_log(None, " done.")

                    # Process artwork locally
                    if "ugoira" in extension and not config.overwrite:
                        try:
                            msg = Fore.YELLOW + Style.NORMAL + f'Processing Image Id: {image_id}' + Style.RESET_ALL
                            PixivHelper.print_and_log(None, msg)
                            PixivDownloadHandler.handle_ugoira(None, str(zip), config, None)
                            res = PixivConstant.PIXIVUTIL_OK
                        except PixivException as ex:
                            PixivHelper.print_and_log('error', f'PixivException for Image ID ({image_id}): {ex}')
                            PixivHelper.print_and_log('error', f'Stack Trace: {sys.exc_info()}')
                            res = PixivConstant.PIXIVUTIL_NOT_OK
                        except Exception as ex:
                            PixivHelper.print_and_log('error', f'Exception for Image ID ({image_id}): {ex}')
                            PixivHelper.print_and_log('error', f'Stack Trace: {sys.exc_info()}')
                            exc_type, exc_value, exc_traceback = sys.exc_info()
                            traceback.print_exception(exc_type, exc_value, exc_traceback)
                            res = PixivConstant.PIXIVUTIL_NOT_OK
                        finally:
                            if res == PixivConstant.PIXIVUTIL_NOT_OK:
                                PixivHelper.print_and_log('warn', f'Failed to process Image ID {image_id} locally: will retry with online infos')
                                PixivHelper.print_and_log('debug', f'Removing corrupted ugoira {zip}')
                                os.remove(zip)

                    # Process artwork with online infos
                    if "zip" in extension or res == PixivConstant.PIXIVUTIL_NOT_OK or ("ugoira" in extension and config.overwrite):
                        res = process_image(caller,
                                            config,
                                            artist=None,
                                            image_id=image_id,
                                            useblacklist=False,
                                            reencoding=True)
                        if res == PixivConstant.PIXIVUTIL_NOT_OK:
                            PixivHelper.print_and_log("warn", f"Cannot process Image Id: {image_id}, restoring old animated files...", newline=False)
                            for file_name in os.listdir(d):
                                PixivHelper.print_and_log("debug", f"Moving back {os.path.join(d, file_name)} to {os.path.join(zip_dir, file_name)}")
                                shutil.move(os.path.join(d, file_name), os.path.join(zip_dir, file_name))  # overwrite corrupted file generated
                            PixivHelper.print_and_log(None, " done.")
                            print('')

                    # Checking result
                    list_file_zipdir = os.listdir(zip_dir)
                    for file_name in os.listdir(d):
                        file_ext = os.path.splitext(file_name)[1]
                        if file_name not in list_file_zipdir and config.backupOldFile:
                            if ((config.createUgoira and not config.deleteUgoira and "ugoira" in file_ext)
                                 or (not config.deleteZipFile and "zip" in file_ext)
                                 or (config.createGif and "gif" in file_ext)
                                 or (config.createApng and "png" in file_ext)
                                 or (config.createAvif and "avif" in file_ext)
                                 or (config.createWebm and "webm" in file_ext)
                                 or (config.createWebp and "webp" in file_ext)):
                                split_name = file_name.rsplit(".", 1)
                                new_name = file_name + "." + str(int(time.time()))
                                if len(split_name) == 2:
                                    new_name = split_name[0] + "." + str(int(time.time())) + "." + split_name[1]
                                PixivHelper.print_and_log('warn', f"Could not found the animated file re-encoded ==> {file_name}, backing up to: {new_name}")
                                PixivHelper.print_and_log('warn', "The new encoded file may have another name or the artist may have change its name.")
                                PixivHelper.print_and_log("debug", f"Rename and move {os.path.join(d, file_name)} to {os.path.join(zip_dir, new_name)}")
                                shutil.move(os.path.join(d, file_name), os.path.join(zip_dir, new_name))
                    print('')

                    # Delete temp path
                    if os.path.exists(d) and d != "":
                        PixivHelper.print_and_log("debug", f"Deleting path {d}")
                        shutil.rmtree(d)
                    list_done.append(image_id)
        if counter == 0:
            PixivHelper.print_and_log('info', "No zip file or ugoira found to re-encode animated files.")

    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        PixivHelper.print_and_log('error', 'Error at process_ugoira_local(): %s' % str(sys.exc_info()))
        PixivHelper.print_and_log('error', 'failed')
        raise
    finally:
        if os.path.exists(d) and d != "":
            PixivHelper.print_and_log("debug", f"Deleting path {d} in finally")
            shutil.rmtree(d)
