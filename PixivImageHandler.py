# -*- coding: utf-8 -*-
import datetime
import gc
import os
import re
import sys
import traceback
import urllib

import datetime_z
import PixivBrowserFactory
import PixivConstant
from PixivException import PixivException
import PixivHelper
import PixivDownloadHandler


def process_image(caller,
                  artist=None,
                  image_id=None,
                  user_dir='',
                  bookmark=False,
                  search_tags='',
                  title_prefix="",
                  bookmark_count=-1,
                  image_response_count=-1,
                  notification_handler=None,
                  job_option=None):
    # caller function/method
    # TODO: ideally to be removed or passed as argument
    db = caller.__dbManager__
    config = caller.__config__

    if notification_handler is None:
        notification_handler = PixivHelper.print_and_log

    # override the config source if job_option is give for filename formats
    format_src = config
    if job_option is not None:
        format_src = job_option

    parse_medium_page = None
    image = None
    result = None
    referer = f'https://www.pixiv.net/artworks/{image_id}'
    filename = f'no-filename-{image_id}.tmp'

    try:
        notification_handler(None, f'Processing Image Id: {image_id}')

        # check if already downloaded. images won't be downloaded twice - needed in process_image to catch any download
        r = db.selectImageByImageId(image_id, cols='save_name')
        exists = False
        in_db = False
        if r is not None:
            exists = db.cleanupFileExists(r[0])
            in_db = True

        # skip if already recorded in db and alwaysCheckFileSize is disabled and overwrite is disabled.
        if in_db and not config.alwaysCheckFileSize and not config.overwrite:
            notification_handler(None, f'Already downloaded in DB: {image_id}')
            gc.collect()
            return PixivConstant.PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT

        # get the medium page
        try:
            (image, parse_medium_page) = PixivBrowserFactory.getBrowser().getImagePage(image_id=image_id,
                                                                                       parent=artist,
                                                                                       from_bookmark=bookmark,
                                                                                       bookmark_count=bookmark_count)
            if len(title_prefix) > 0:
                caller.set_console_title(f"{title_prefix} ImageId: {image.imageId}")
            else:
                caller.set_console_title(f"MemberId: {image.artist.artistId} ImageId: {image.imageId}")

        except PixivException as ex:
            caller.ERROR_CODE = ex.errorCode
            caller.__errorList.append(dict(type="Image", id=str(image_id), message=ex.message, exception=ex))
            if ex.errorCode == PixivException.UNKNOWN_IMAGE_ERROR:
                notification_handler('error', ex.message)
            elif ex.errorCode == PixivException.SERVER_ERROR:
                notification_handler('error', f'Giving up image_id (medium): {image_id}')
            elif ex.errorCode > 2000:
                notification_handler('error', f'Image Error for {image_id}: {ex.message}')
            if parse_medium_page is not None:
                dump_filename = f'Error medium page for image {image_id}.html'
                PixivHelper.dump_html(dump_filename, parse_medium_page)
                notification_handler('error', f'Dumping html to: {dump_filename}')
            else:
                notification_handler('error', f'Image ID ({image_id}): {ex}')
            notification_handler('error', f'Stack Trace: {sys.exc_info()}')
            return PixivConstant.PIXIVUTIL_NOT_OK
        except Exception as ex:
            notification_handler('error', f'Image ID ({image_id}): {ex}')
            if parse_medium_page is not None:
                dump_filename = f'Error medium page for image {image_id}.html'
                PixivHelper.dump_html(dump_filename, parse_medium_page)
                notification_handler('error', f'Dumping html to: {dump_filename}')
            notification_handler('error', f'Stack Trace: {sys.exc_info()}')
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            return PixivConstant.PIXIVUTIL_NOT_OK

        download_image_flag = True

        # date validation and blacklist tag validation
        if config.dateDiff > 0:
            if image.worksDateDateTime != datetime.datetime.fromordinal(1).replace(tzinfo=datetime_z.utc):
                if image.worksDateDateTime < (datetime.datetime.today() - datetime.timedelta(config.dateDiff)).replace(tzinfo=datetime_z.utc):
                    notification_handler('info', f'Skipping image_id: {image_id} because contains older than: {config.dateDiff} day(s).')
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_OLDER

        if config.useBlacklistTags:
            for item in caller.__blacklistTags:
                if item in image.imageTags:
                    notification_handler('info', f'Skipping image_id: {image_id} because contains blacklisted tags: {item}')
                    download_image_flag = False
                    result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST
                    break

        if config.useBlacklistMembers:
            if str(image.originalArtist.artistId) in caller.__blacklistMembers:
                notification_handler('info', f'Skipping image_id: {image_id} because contains blacklisted member id: {image.originalArtist.artistId}')
                download_image_flag = False
                result = PixivConstant.PIXIVUTIL_SKIP_BLACKLIST

        if download_image_flag and not caller.DEBUG_SKIP_DOWNLOAD_IMAGE:
            if artist is None:
                notification_handler(None, f'Member Name  : {image.artist.artistName}')
                notification_handler(None, f'Member Avatar: {image.artist.artistAvatar}')
                notification_handler(None, f'Member Token : {image.artist.artistToken}')
                notification_handler(None, f'Member Background : {image.artist.artistBackground}')
            notification_handler(None, f"Title: {image.imageTitle}")
            tags_str = ', '.join(image.imageTags)
            notification_handler(None, f"Tags : {tags_str}")
            notification_handler(None, f"Date : {image.worksDateDateTime}")
            notification_handler(None, f"Mode : {image.imageMode}")

            # get bookmark count
            if ("%bookmark_count%" in format_src.filenameFormat or "%image_response_count%" in format_src.filenameFormat) and image.bookmark_count == -1:
                notification_handler(None, "Parsing bookmark page", end=' ')
                bookmark_url = f'https://www.pixiv.net/bookmark_detail.php?illust_id={image_id}'
                parse_bookmark_page = PixivBrowserFactory.getBrowser().getPixivPage(bookmark_url)
                image.ParseBookmarkDetails(parse_bookmark_page)
                parse_bookmark_page.decompose()
                del parse_bookmark_page
                notification_handler(None, f"Bookmark Count : {image.bookmark_count}")
                caller.__br__.back()

            if config.useSuppressTags:
                for item in caller.__suppressTags:
                    if item in image.imageTags:
                        image.imageTags.remove(item)

            # get manga page
            if image.imageMode == 'manga':
                notification_handler(None, f"Page Count : {image.imageCount}")

            if user_dir == '':  # Yavos: use config-options
                target_dir = format_src.rootDirectory
            else:  # Yavos: use filename from list
                target_dir = user_dir

            result = PixivConstant.PIXIVUTIL_OK
            manga_files = list()
            page = 0

            # Issue #639
            source_urls = image.imageUrls
            if config.downloadResized:
                source_urls = image.imageResizedUrls

            for img in source_urls:
                notification_handler(None, f'Image URL : {img}')
                url = os.path.basename(img)
                split_url = url.split('.')
                if split_url[0].startswith(str(image_id)):

                    filename_format = format_src.filenameFormat
                    if image.imageMode == 'manga':
                        filename_format = format_src.filenameMangaFormat

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
                        manga_page = caller.__re_manga_page.findall(filename)
                        if len(manga_page) > 0:
                            splitted_filename = filename.split(manga_page[0][0], 1)
                            splitted_manga_page = manga_page[0][0].split("_p", 1)
                            # filename = splitted_filename[0] + splitted_manga_page[0] + os.sep + "_p" + splitted_manga_page[1] + splitted_filename[1]
                            filename = f"{splitted_filename[0]}{splitted_manga_page[0]}{os.sep}_p{splitted_manga_page[1]}{splitted_filename[1]}"

                    notification_handler('info', f'Filename  : {filename}')

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
                                                                                 notification_handler)

                        if result == PixivConstant.PIXIVUTIL_NOT_OK:
                            notification_handler('error', f'Image url not found/failed to download: {image.imageId}')
                        elif result == PixivConstant.PIXIVUTIL_ABORTED:
                            raise KeyboardInterrupt()

                        manga_files.append((image_id, page, filename))
                        page = page + 1

                    except urllib.error.URLError:
                        notification_handler('error', f'Error when download_image(), giving up url: {img}')
                    notification_handler(None, '')

            if config.writeImageInfo or config.writeImageJSON:
                filename_info_format = format_src.filenameInfoFormat or format_src.filenameFormat
                # Issue #575
                if image.imageMode == 'manga':
                    filename_info_format = format_src.filenameMangaInfoFormat or format_src.filenameMangaFormat or filename_info_format
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
                    image.WriteJSON(info_filename + ".json")

            if image.imageMode == 'ugoira_view':
                if config.writeUgoiraInfo:
                    image.WriteUgoiraData(filename + ".js")
                # Handle #451
                if config.createUgoira and (result in (PixivConstant.PIXIVUTIL_OK, PixivConstant.PIXIVUTIL_SKIP_DUPLICATE)):
                    PixivDownloadHandler.handle_ugoira(image, filename, config, notification_handler)

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
                notification_handler('error', f'Failed to insert image id:{image.imageId} to DB')

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
        notification_handler(None, '\n')

        return result
    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        caller.ERROR_CODE = getattr(ex, 'errorCode', -1)
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        notification_handler('error', f'Error at process_image(): {image_id}')
        notification_handler('error', f'Exception: {sys.exc_info()}')

        if parse_medium_page is not None:
            dump_filename = f'Error medium page for image {image_id}.html'
            PixivHelper.dump_html(dump_filename, parse_medium_page)
            notification_handler('error', f'Dumping html to: {dump_filename}')

        raise
