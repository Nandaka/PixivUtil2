# -*- coding: utf-8 -*-
from colorama import Fore, Style

import PixivBrowserFactory
import PixivHelper
import PixivDownloadHandler


def process_sketch_post(caller, config, post_id):
    # db = caller.__dbManager__
    config.loadConfig(path=caller.configfile)
    br = PixivBrowserFactory.getBrowser()

    msg = Fore.YELLOW + Style.NORMAL + f'Processing Post Id: {post_id}' + Style.RESET_ALL
    PixivHelper.print_and_log(None, msg)
    post = br.sketch_get_post_by_post_id(post_id)
    download_post(caller, config, post)


def process_sketch_artists(caller, config, artist_id, start_page=0, end_page=0):
    config.loadConfig(path=caller.configfile)
    br = PixivBrowserFactory.getBrowser()
    title_prefix = f"Pixiv Sketch - Processing Artist Id: {artist_id}"
    caller.set_console_title(title_prefix)
    msg = Fore.YELLOW + Style.NORMAL + f'Processing Artist Id: {artist_id}' + Style.RESET_ALL
    PixivHelper.print_and_log(None, msg)
    artist = br.sketch_get_posts_by_artist_id(artist_id, end_page)

    POST_PER_PAGE = 10
    start_idx = POST_PER_PAGE * (start_page - 1)
    end_idx = POST_PER_PAGE * (end_page)
    if end_page == 0 or end_idx > len(artist.posts):
        end_idx = len(artist.posts)
    msg = Fore.YELLOW + Style.NORMAL + f'Processing from post #{start_idx} to #{end_idx}' + Style.RESET_ALL
    PixivHelper.print_and_log(None, msg)
    post_to_process = artist.posts[start_idx:end_idx]

    current_post = 1
    for item in post_to_process:
        caller.set_console_title(f"{title_prefix} - Post {current_post} of {len(post_to_process)}")
        PixivHelper.print_and_log(None, f'Post #: {current_post}')
        PixivHelper.print_and_log('info', f'Post ID   : {item.imageId}')
        download_post(caller, config, item)
        current_post = current_post + 1


def download_post(caller, config, post):
    referer = f"https://sketch.pixiv.net/items/{post.imageId}"
    for url in post.imageUrls:
        filename = PixivHelper.make_filename(config.filenameFormat,
                                            post,
                                            artistInfo=post.artist,
                                            tagsSeparator=config.tagsSeparator,
                                            tagsLimit=config.tagsLimit,
                                            fileUrl=url,
                                            bookmark=None,
                                            searchTags='',
                                            useTranslatedTag=config.useTranslatedTag,
                                            tagTranslationLocale=config.tagTranslationLocale)
        filename = PixivHelper.sanitize_filename(filename, config.rootDirectory)

        PixivHelper.print_and_log(None, f'Image URL : {url}')
        PixivHelper.print_and_log('info', f'Filename  : {filename}')
        (result, filename) = PixivDownloadHandler.download_image(caller,
                                                                url,
                                                                filename,
                                                                referer,
                                                                config.overwrite,
                                                                config.retry,
                                                                config.backupOldFile)
