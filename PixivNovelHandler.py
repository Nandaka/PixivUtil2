from colorama.ansi import Fore, Style
import PixivHelper
import PixivNovel


def process_novel(caller,
                  config,
                  novel_id,
                  notifier=None):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier

    msg = Fore.YELLOW + Style.BRIGHT + f'Processing Novel details: {novel_id}' + Style.RESET_ALL
    PixivHelper.print_and_log('info', msg)

    novel = caller.__br__.getNovelPage(novel_id)
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
    novel.write_content(filename)

    print()


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
    while(flag):
        PixivHelper.print_and_log(None, f"Getting page = {page}")
        novel_series = caller.__br__.getNovelSeriesContent(novel_series, current_page=page)
        page = page + 1
        if end_page > 0 and page > end_page:
            PixivHelper.print_and_log(None, f"Page limit reached = {end_page}.")
            flag = False
        if (page * PixivNovel.MAX_LIMIT) >= novel_series.total:
            PixivHelper.print_and_log(None, "No more novel.")
            flag = False

    for novel in novel_series.series_list:
        process_novel(caller,
                      config,
                      novel_id=novel["id"],
                      notifier=notifier)

    print()
