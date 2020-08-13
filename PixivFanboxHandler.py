# -*- coding: utf-8 -*-
import os

import datetime_z
import PixivBrowserFactory
import PixivConstant
import PixivDownloadHandler
import PixivHelper
import PixivModelFanbox
from PixivException import PixivException


def process_fanbox_artist_by_id(caller, config, artist_id, end_page, title_prefix=""):
    config.loadConfig(path=caller.configfile)
    br = PixivBrowserFactory.getBrowser()

    caller.set_console_title(title_prefix)
    try:
        artist = br.fanboxGetArtistById(artist_id)
    except PixivException as pex:
        PixivHelper.print_and_log("error", "Error gettting FANBOX artist by id: {0} ==> {1}".format(artist_id, pex.message))
        return

    current_page = 1
    next_url = None
    image_count = 1
    while True:
        PixivHelper.print_and_log("info", "Processing {0}, page {1}".format(artist, current_page))
        caller.set_console_title(f"{title_prefix} FANBOX Artist {artist}, page {current_page}")
        try:
            posts = br.fanboxGetPostsFromArtist(artist, next_url)
        except PixivException as pex:
            PixivHelper.print_and_log("error", "Error getting FANBOX posts of artist: {0} ==> {1}".format(artist, pex.message))
            break

        for post in posts:
            print("#{0}".format(image_count))
            post.printPost()

            # images
            if post.type in PixivModelFanbox.FanboxPost._supportedType:
                try:
                    process_fanbox_post(caller, config, post, artist)
                except KeyboardInterrupt:
                    choice = input("Keyboard Interrupt detected, continue to next post (Y/N)").rstrip("\r")
                    if choice.upper() == 'N':
                        PixivHelper.print_and_log("info", f"FANBOX artist: {artist}, processing aborted")
                        break
                    else:
                        continue
            image_count += 1
            PixivHelper.wait(config)

        if not artist.hasNextPage:
            PixivHelper.print_and_log("info", "No more post for {0}".format(artist))
            break
        current_page += 1
        if end_page > 0 and current_page > end_page:
            PixivHelper.print_and_log("info", "Reaching page limit for {0}, limit {1}".format(artist, end_page))
            break
        next_url = artist.nextUrl
        if next_url is None:
            PixivHelper.print_and_log("info", "No more next page for {0}".format(artist))
            break


def process_fanbox_post(caller, config, post, artist):
    # caller function/method
    # TODO: ideally to be removed or passed as argument
    db = caller.__dbManager__
    # config.loadConfig(path=caller.configfile)
    br = PixivBrowserFactory.getBrowser()

    db.insertPost(artist.artistId, post.imageId, post.imageTitle, post.feeRequired, post.worksDate, post.type)

    post_files = []

    flag_processed = False
    if config.checkDBProcessHistory:
        result = db.selectPostByPostId(post.imageId)
        if result:
            updated_date = result[5]
            if updated_date is not None and post.updatedDateDatetime <= datetime_z.parse_datetime(updated_date):
                flag_processed = True

    try:
        if not post.is_restricted and not flag_processed:
            br.fanboxUpdatePost(post)

        if ((not post.is_restricted) or config.downloadCoverWhenRestricted) and (not flag_processed):
            # cover image
            if post.coverImageUrl is not None:
                # fake the image_url for filename compatibility, add post id and pagenum
                fake_image_url = post.coverImageUrl.replace("{0}/cover/".format(post.imageId),
                                                            "{0}_".format(post.imageId))
                filename = PixivHelper.make_filename(config.filenameFormatFanboxCover,
                                                     post,
                                                     artistInfo=artist,
                                                     tagsSeparator=config.tagsSeparator,
                                                     tagsLimit=config.tagsLimit,
                                                     fileUrl=fake_image_url,
                                                     bookmark=None,
                                                     searchTags='',
                                                     useTranslatedTag=config.useTranslatedTag,
                                                     tagTranslationLocale=config.tagTranslationLocale)
                filename = PixivHelper.sanitize_filename(filename, config.rootDirectory)
                post.linkToFile[post.coverImageUrl] = filename

                print("Downloading cover from {0}".format(post.coverImageUrl))
                print("Saved to {0}".format(filename))

                referer = "https://www.pixiv.net/fanbox/creator/{0}/post/{1}".format(artist.artistId, post.imageId)
                # don't pass the post id and page number to skip db check
                (result, filename) = PixivDownloadHandler.download_image(caller,
                                                                         post.coverImageUrl,
                                                                         filename,
                                                                         referer,
                                                                         config.overwrite,
                                                                         config.retry,
                                                                         config.backupOldFile,
                                                                         image=post)
                post_files.append((post.imageId, -1, filename))
                PixivHelper.get_logger().debug("Download %s result: %s", filename, result)
            else:
                PixivHelper.print_and_log("info", "No Cover Image for post: {0}.".format(post.imageId))

        if post.is_restricted:
            PixivHelper.print_and_log("info", "Skipping post: {0} due to restricted post.".format(post.imageId))
            return

        if flag_processed:
            PixivHelper.print_and_log("info", "Skipping post: {0} because it was downloaded before.".format(post.imageId))
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
                filename = PixivHelper.make_filename(config.filenameFormatFanboxContent,
                                                     post,
                                                     artistInfo=artist,
                                                     tagsSeparator=config.tagsSeparator,
                                                     tagsLimit=config.tagsLimit,
                                                     fileUrl=fake_image_url,
                                                     bookmark=None,
                                                     searchTags='',
                                                     useTranslatedTag=config.useTranslatedTag,
                                                     tagTranslationLocale=config.tagTranslationLocale)

                filename = PixivHelper.sanitize_filename(filename, config.rootDirectory)

                post.linkToFile[image_url] = filename

                referer = "https://www.pixiv.net/fanbox/creator/{0}/post/{1}".format(artist.artistId, post.imageId)

                print("Downloading image {0} from {1}".format(current_page, image_url))
                print("Saved to {0}".format(filename))

                # filesize detection and overwrite issue
                _oldvalue = config.alwaysCheckFileSize
                config.alwaysCheckFileSize = False
                # don't pass the post id and page number to skip db check
                (result, filename) = PixivDownloadHandler.download_image(caller,
                                                                         image_url,
                                                                         filename,
                                                                         referer,
                                                                         False,  # config.overwrite somehow unable to get remote filesize
                                                                         config.retry,
                                                                         config.backupOldFile,
                                                                         image=post)
                if result == PixivConstant.PIXIVUTIL_ABORTED:
                    raise KeyboardInterrupt()
                post_files.append((post.imageId, current_page, filename))

                PixivHelper.get_logger().debug("Download %s result: %s", filename, result)

                config.alwaysCheckFileSize = _oldvalue
                current_page = current_page + 1

        # Implement #447
        filename = PixivHelper.make_filename(config.filenameFormatFanboxInfo,
                                             post,
                                             artistInfo=artist,
                                             tagsSeparator=config.tagsSeparator,
                                             tagsLimit=config.tagsLimit,
                                             fileUrl="{0}".format(post.imageId),
                                             bookmark=None,
                                             searchTags='',
                                             useTranslatedTag=config.useTranslatedTag,
                                             tagTranslationLocale=config.tagTranslationLocale)

        filename = PixivHelper.sanitize_filename(filename, config.rootDirectory)
        if config.writeImageInfo:
            post.WriteInfo(filename + ".txt")
        if config.writeHtml:
            if post.type == "article" or (len(post.images) >= config.minImageCountForNonArticle and len(post.body_text) > config.minTextLengthForNonArticle):
                html_template = PixivConstant.HTML_TEMPLATE
                if os.path.isfile("template.html"):
                    reader = PixivHelper.open_text_file("template.html")
                    html_template = reader.read()
                    reader.close()
                post.WriteHtml(html_template, config.useAbsolutePathsInHtml, filename + ".html")
    finally:
        if len(post_files) > 0:
            db.insertPostImages(post_files)

    db.updatePostUpdateDate(post.imageId, post.updatedDate)
