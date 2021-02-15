import PixivHelper
import PixivNovel


def process_novel(caller,
                  config,
                  novel_id,
                  notifier=None):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier

    PixivHelper.print_and_log(None, f"Processing Novel details = {novel_id}")
    novel = caller.__br__.getNovelPage(novel_id)
    PixivHelper.print_and_log(None, f"Title = {novel.title}")
    filename = f"novel-{novel_id}.html"
    PixivHelper.print_and_log(None, f"Saving Novel details to = {filename}")
    novel.write_content(filename)


def process_novel_series(caller,
                         config,
                         series_id,
                         start_page=1,
                         end_page=0,
                         notifier=None):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier
    PixivHelper.print_and_log(None, f"Processing Novel Series = {series_id}")

    novel_series = caller.__br__.getNovelSeries(series_id)
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
        print(novel["id"])
        # process_novel(caller,
        #               config,
        #               novel_id=novel["id"],
        #               notifier=notifier)
