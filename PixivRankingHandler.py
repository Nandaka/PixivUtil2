import os
import sys

from colorama import Fore, Style

import PixivConfig
import PixivConstant
import PixivException
import PixivHelper
import PixivImageHandler
from PixivBrowserFactory import PixivBrowser
from PixivListItem import PixivListItem


def process_ranking(caller, config, mode, content, start_page=1, end_page=0, date="", filter=None, notifier=None):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier
    msg = Fore.YELLOW + Style.NORMAL + f'Processing Pixiv Ranking: {mode}.' + Style.RESET_ALL
    PixivHelper.print_and_log(None, msg)
    br: PixivBrowser = caller.__br__

    try:
        # get rank data
        curr_page = start_page
        i = 1
        while(True):
            title_prefix = f"Pixiv Ranking: {mode} page {curr_page} and date {date}"
            PixivHelper.print_and_log(None, title_prefix)
            ranks = br.getPixivRanking(mode, curr_page, date, content, filter)
            print(f"Mode : {ranks.mode}")
            print(f"Total: {ranks.rank_total}")
            print(f"Next Page: {ranks.next_page}")
            print(f"Next Date: {ranks.next_date}")

            ignore_file_list = "ignore_list.txt"
            if os.path.exists(ignore_file_list):
                PixivHelper.print_and_log('info', f'Using ignore list for member: {ignore_file_list}')
                ignore_list = PixivListItem.parseList(ignore_file_list, config.rootDirectory)
                for ignore in ignore_list:
                    for item in ranks.contents:
                        if item["user_id"] == ignore.memberId:
                            ranks.remove(item)
                            break

            for post in ranks.contents:
                try:
                    result = PixivConstant.PIXIVUTIL_OK
                    if not caller.DEBUG_SKIP_PROCESS_IMAGE:
                        print(f"{Fore.YELLOW} #{i}.{Style.RESET_ALL}")
                        result = PixivImageHandler.process_image(caller,
                                                                config,
                                                                None,
                                                                post["illust_id"],
                                                                user_dir=config.rootDirectory,
                                                                title_prefix=title_prefix,
                                                                image_response_count=post["rating_count"],
                                                                notifier=notifier)
                    PixivHelper.wait(result, config)
                    i = i + 1
                except PixivException as pex:
                    PixivHelper.print_and_log("error", f"Failed to process PixivRanking for {post.illust_id} ==> {pex.message}")

            curr_page = curr_page + 1
            if end_page > 0 and curr_page > end_page:
                PixivHelper.print_and_log("info", f"Reach max page {end_page}")
                break
            if type(ranks.next_page) is not int:
                PixivHelper.print_and_log("info", "Reaching last page.")
                break

    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        caller.ERROR_CODE = getattr(ex, 'errorCode', -1)
        PixivHelper.print_and_log('error', f'Error at process_ranking(): {sys.exc_info()}')
        print('Failed')
        raise


def process_new_illusts(caller, config: PixivConfig, type_mode="illust", max_page=0, notifier=None):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier
    br: PixivBrowser = caller.__br__

    msg = Fore.YELLOW + Style.NORMAL + f'Processing Pixiv Ranking: RR-18={config.r18mode}.' + Style.RESET_ALL
    PixivHelper.print_and_log(None, msg)
    last_id = 0
    current_page = 1
    i = 1
    while True:
        result = br.getNewIllust(last_id, type_mode=type_mode, r18=config.r18mode)
        title_prefix = f"Pixiv New Illusts: RR-18={config.r18mode} - page {current_page}."
        PixivHelper.print_and_log(None, title_prefix)

        for image in result.images:
            try:
                dl_result = PixivConstant.PIXIVUTIL_OK
                image_id = image["id"]
                print(f"{Fore.YELLOW} #{i} - {image_id}.{Style.RESET_ALL}")
                if not caller.DEBUG_SKIP_PROCESS_IMAGE:
                    dl_result = PixivImageHandler.process_image(caller,
                                                            config,
                                                            None,
                                                            image_id,
                                                            user_dir=config.rootDirectory,
                                                            title_prefix=title_prefix,
                                                            notifier=notifier)
                PixivHelper.wait(dl_result, config)
                i = i + 1
            except PixivException as pex:
                PixivHelper.print_and_log("error", f"Failed to process Pixiv New Illusts for {image_id} ==> {pex.message}")

        last_id = result.last_id
        current_page = current_page + 1

        if max_page != 0 and current_page > max_page:
            PixivHelper.print_and_log("info", f"Reached max page = {max_page}.")
            break
        elif last_id == 0 or len(result.images) == 0:
            PixivHelper.print_and_log("info", "No more images!")
            break
