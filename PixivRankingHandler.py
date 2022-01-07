import os
import sys

from colorama import Fore, Style

import PixivHelper
from PixivListItem import PixivListItem
import PixivConstant
import PixivException
import PixivImageHandler
from PixivBrowserFactory import PixivBrowser


def process_ranking(caller, config, mode, start_page=1, end_page=0, date="", filter=None, notifier=None):
    if notifier is None:
        notifier = PixivHelper.dummy_notifier
    msg = Fore.YELLOW + Style.NORMAL + f'Processing Pixiv Ranking: {mode}.' + Style.RESET_ALL
    PixivHelper.print_and_log(None, msg)
    br: PixivBrowser = caller.__br__

    try:
        # get rank data
        curr_page = start_page
        while(True):
            title_prefix = f"Pixiv Ranking: {mode} page {curr_page} and date {date}"
            PixivHelper.print_and_log(None, title_prefix)
            result = br.getPixivRanking(mode, curr_page, date, filter)
            print(f"Mode : {result.mode}")
            print(f"Total: {result.rank_total}")
            print(f"Next Page: {result.next_page}")
            print(f"Next Date: {result.next_date}")

            ignore_file_list = "ignore_list.txt"
            if os.path.exists(ignore_file_list):
                PixivHelper.print_and_log('info', f'Using ignore list for member: {ignore_file_list}')
                ignore_list = PixivListItem.parseList(ignore_file_list, config.rootDirectory)
                for ignore in ignore_list:
                    for item in result.contents:
                        if item["user_id"] == ignore.memberId:
                            result.remove(item)
                            break

            for content in result.contents:
                try:
                    result = PixivConstant.PIXIVUTIL_OK
                    if not caller.DEBUG_SKIP_PROCESS_IMAGE:
                        result = PixivImageHandler.process_image(caller,
                                                                config,
                                                                None,
                                                                content["illust_id"],
                                                                user_dir=config.rootDirectory,
                                                                title_prefix=title_prefix,
                                                                image_response_count=content["rating_count"],
                                                                notifier=notifier)
                    PixivHelper.wait(result, config)
                except PixivException as pex:
                    PixivHelper.print_and_log("error", f"Failed to process PixivRanking for {content.illust_id} ==> {pex.message}")

            curr_page = curr_page + 1
            if end_page > 0 and curr_page > end_page:
                PixivHelper.print_and_log("info", f"Reach max page {end_page}")
                break
            if not result.next_page:
                PixivHelper.print_and_log("info", "Reaching last page.")
                break

    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        caller.ERROR_CODE = getattr(ex, 'errorCode', -1)
        PixivHelper.print_and_log('error', f'Error at process_ranking(): {sys.exc_info()}')
        print('Failed')
        raise
