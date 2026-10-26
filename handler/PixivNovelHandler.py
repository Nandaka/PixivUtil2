import os
import time

from colorama.ansi import Fore, Style

import common.PixivConstant as PixivConstant
import common.PixivHelper as PixivHelper
import model.PixivNovel as PixivNovel


def process_novel(caller,
                  config,
                  novel_id,
                  notifier=None):
    ''' Download a novel; PIXIVUTIL_SKIP_DUPLICATE when the database
    holds it already, else PIXIVUTIL_OK.'''
    if notifier is None:
        notifier = PixivHelper.dummy_notifier

    msg = Fore.YELLOW + Style.BRIGHT + f'Processing Novel details: {novel_id}' + Style.RESET_ALL
    PixivHelper.print_and_log('info', msg)

    # check if already downloaded before and overwrite is not enabled
    db_result = caller.__dbManager__.selectNovelPostByPostId(novel_id)
    if db_result is not None and not config.overwrite and not config.checkLastModified and not config.alwaysCheckFileSize:
        save_name = db_result[2]  # save_name
        PixivHelper.print_and_log('warn', f"Novel already downloaded : {save_name}")
        return PixivConstant.PIXIVUTIL_SKIP_DUPLICATE

    novel = caller.__br__.getNovelPage(novel_id)
    novel.theme = "dark" if config.novelDarkMode else "light"
    if config.downloadNovelImages:
        novel.images = caller.__br__.getNovelImages(novel)
        PixivHelper.print_and_log(None, f"Images : {len(novel.images)} of {1 + len(novel.embeddedImages) + len(novel.pixivImages)}"
                                        " (the cover, uploaded and pixiv images)")
    PixivHelper.print_and_log(None, f"Title : {novel.imageTitle}")
    PixivHelper.print_and_log(None, f'Member Name  : {novel.artist.artistName}')
    PixivHelper.print_and_log(None, f'Member Avatar: {novel.artist.artistAvatar}')
    PixivHelper.print_and_log(None, f'Member Token : {novel.artist.artistToken}')
    PixivHelper.print_and_log(None, f'Member Background : {novel.artist.artistBackground}')
    tags_str = ', '.join(novel.imageTags)
    PixivHelper.print_and_log(None, f"Tags : {tags_str}")
    PixivHelper.print_and_log(None, f"Date : {novel.worksDateDateTime}")
    PixivHelper.print_and_log(None, f"Mode : {novel.imageMode}")
    PixivHelper.print_and_log(None, f"Bookmark Count : {novel.bookmark_count}")

    # fake the fileUrl
    fileUrl = f"https://www.pixiv.net/ajax/novel/{novel_id}.html"
    filename = PixivHelper.make_filename(config.filenameFormatNovel,
                                         novel,
                                         tagsSeparator=config.tagsSeparator,
                                         tagsLimit=config.tagsLimit,
                                         fileUrl=fileUrl,
                                         bookmark=False,
                                         searchTags="",
                                         useTranslatedTag=config.useTranslatedTag,
                                         tagTranslationLocale=config.tagTranslationLocale)
    filename = PixivHelper.sanitize_filename(filename, config.rootDirectory)
    PixivHelper.print_and_log(None, f"Filename : {filename}")

    # checking logic
    if os.path.exists(filename):
        if config.checkLastModified:
            local_timestamp = os.path.getmtime(filename)
            remote_timestamp = time.mktime(novel.worksDateDateTime.timetuple())
            if local_timestamp == remote_timestamp:
                PixivHelper.print_and_log('warn', f"\rLocal file timestamp match with remote: {filename} => {novel.worksDateDateTime}")
                return PixivConstant.PIXIVUTIL_SKIP_DUPLICATE
        if config.alwaysCheckFileSize:
            temp_filename = filename + ".!tmp"
            novel.write_content(temp_filename)
            file_size = os.path.getsize(temp_filename)
            old_size = os.path.getsize(filename)
            result = PixivHelper.check_file_exists(config, filename, file_size, old_size)
            if result == PixivConstant.PIXIVUTIL_OK:
                os.rename(temp_filename, filename)
            else:
                os.remove(temp_filename)
    else:
        novel.write_content(filename)

    if config.setLastModified and filename is not None and os.path.isfile(filename):
        ts = time.mktime(novel.worksDateDateTime.timetuple())
        os.utime(filename, (ts, ts))

    caller.__dbManager__.insertNovelPost(novel, filename)

    print()
    return PixivConstant.PIXIVUTIL_OK


def process_member_novels(caller,
                          config,
                          member_id,
                          title_prefix="",
                          notifier=None):
    ''' Download a member's novels, newest first. As for the member's
    images, the walk stops after checkUpdatedLimit novels the database
    holds already (0: never).'''
    msg = Fore.YELLOW + Style.NORMAL + f'{title_prefix}Processing novels of member id: {member_id}' + Style.RESET_ALL
    PixivHelper.print_and_log('info', msg)
    try:
        novel_ids = caller.__br__.getMemberNovelIds(member_id)
    except Exception as ex:
        PixivHelper.print_and_log('error', f"Cannot get the novels of member id {member_id}: {ex}")
        return
    PixivHelper.print_and_log(None, f"Novels: {len(novel_ids)}")

    known = 0
    for novel_id in novel_ids:
        result = process_novel(caller, config, novel_id, notifier=notifier)
        if result == PixivConstant.PIXIVUTIL_SKIP_DUPLICATE:
            known = known + 1
            if config.checkUpdatedLimit != 0 and known >= config.checkUpdatedLimit:
                PixivHelper.print_and_log(None, f"Skipping the rest of member {member_id}'s novels.")
                return
        else:
            PixivHelper.wait(result, config)


def process_novel_series(caller,
                         config,
                         series_id,
                         start_page=1,
                         end_page=0,
                         notifier=None):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier
    msg = Fore.YELLOW + Style.BRIGHT + f'Processing Novel Series: {series_id}' + Style.RESET_ALL
    PixivHelper.print_and_log('info', msg)

    novel_series = caller.__br__.getNovelSeries(series_id)
    PixivHelper.print_and_log(None, f'Series Name : {novel_series.series_name}')
    PixivHelper.print_and_log(None, f'Total Novel : {novel_series.total}')

    page = start_page
    flag = True
    while (flag):
        PixivHelper.print_and_log(None, f"Getting page = {page}")
        novel_series = caller.__br__.getNovelSeriesContent(novel_series, current_page=page)
        if end_page > 0 and page > end_page:
            PixivHelper.print_and_log(None, f"Page limit reached = {end_page}.")
            flag = False
        if (page * PixivNovel.MAX_LIMIT) >= novel_series.total:
            PixivHelper.print_and_log(None, "No more novel.")
            flag = False
        page = page + 1

    for novel in novel_series.series_list:
        process_novel(caller,
                      config,
                      novel_id=novel["id"],
                      notifier=notifier)

    print()
