import os
import sys

import PixivArtistHandler
import PixivHelper
import PixivSketchHandler
import PixivTagsHandler
from PixivListItem import PixivListItem
from PixivTags import PixivTags


def process_list(caller, config, list_file_name=None, tags=None, include_sketch=False):
    db = caller.__dbManager__
    br = caller.__br__

    result = None
    try:
        # Getting the list
        if config.processFromDb:
            PixivHelper.print_and_log('info', 'Processing from database.')
            if config.dayLastUpdated == 0:
                result = db.selectAllMember()
            else:
                print(f'Select only last {config.dayLastUpdated} days.')
                result = db.selectMembersByLastDownloadDate(config.dayLastUpdated)
        else:
            PixivHelper.print_and_log('info', f'Processing from list file: {list_file_name}')
            result = PixivListItem.parseList(list_file_name, config.rootDirectory)

        ignore_file_list = "ignore_list.txt"
        if os.path.exists(ignore_file_list):
            PixivHelper.print_and_log('info', f'Processing ignore list for member: {ignore_file_list}')
            ignore_list = PixivListItem.parseList(ignore_file_list, config.rootDirectory)
            for ignore in ignore_list:
                for item in result:
                    if item.memberId == ignore.memberId:
                        result.remove(item)
                        break

        PixivHelper.print_and_log('info', f"Found {len(result)} items.")
        current_member = 1
        for item in result:
            retry_count = 0
            while True:
                try:
                    prefix = f"[{current_member} of {len(result)}] "
                    PixivArtistHandler.process_member(caller,
                                                      config,
                                                      item.memberId,
                                                      user_dir=item.path,
                                                      tags=tags,
                                                      title_prefix=prefix)
                    break
                except KeyboardInterrupt:
                    raise
                except BaseException as ex:
                    if retry_count > config.retry:
                        PixivHelper.print_and_log('error', f'Giving up member_id: {item.memberId} ==> {ex}')
                        break
                    retry_count = retry_count + 1
                    print(f'Something wrong, retrying after 2 second ({retry_count}) ==> {ex}')
                    PixivHelper.print_delay(2)

            retry_count = 0
            while include_sketch:
                try:
                    # Issue 1007
                    # fetching artist token...
                    (artist_model, _) = br.getMemberPage(item.memberId)
                    prefix = f"[{current_member} ({item.memberId} - {artist_model.artistToken}) of {len(result)}] "
                    PixivSketchHandler.process_sketch_artists(caller,
                                                              config,
                                                              artist_model.artistToken,
                                                              title_prefix=prefix)
                    break
                except KeyboardInterrupt:
                    raise
                except BaseException as ex:
                    if retry_count > config.retry:
                        PixivHelper.print_and_log('error', f'Giving up member_id: {item.memberId} when processing PixivSketch ==> {ex}')
                        break
                    retry_count = retry_count + 1
                    print(f'Something wrong, retrying after 2 second ({retry_count}) ==> {ex}')
                    PixivHelper.print_delay(2)

            current_member = current_member + 1
            br.clear_history()
            print(f'done for member id = {item.memberId}.')
            print('')
    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        caller.ERROR_CODE = getattr(ex, 'errorCode', -1)
        PixivHelper.print_and_log('error', f'Error at process_list(): {sys.exc_info()}')
        print('Failed')
        raise


def process_tags_list(caller,
                      config,
                      filename,
                      page=1,
                      end_page=0,
                      wild_card=True,
                      sort_order='date_d',
                      bookmark_count=None,
                      start_date=None,
                      end_date=None):

    try:
        print("Reading:", filename)
        tags = PixivTags.parseTagsList(filename)
        for tag in tags:
            PixivTagsHandler.process_tags(caller,
                                          config,
                                          tag,
                                          page=page,
                                          end_page=end_page,
                                          wild_card=wild_card,
                                          start_date=start_date,
                                          end_date=end_date,
                                          use_tags_as_dir=config.useTagsAsDir,
                                          bookmark_count=bookmark_count,
                                          sort_order=sort_order)
    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        caller.ERROR_CODE = getattr(ex, 'errorCode', -1)
        PixivHelper.print_and_log('error', f'Error at process_tags_list(): {sys.exc_info()}')
        raise


def import_list(caller,
                config,
                list_name='list.txt'):
    list_path = config.downloadListDirectory + os.sep + list_name
    if os.path.exists(list_path):
        list_txt = PixivListItem.parseList(list_path, config.rootDirectory)
        caller.__dbManager__.importList(list_txt)
        print(f"Updated {len(list_txt)} items.")
    else:
        msg = f"List file not found: {list_path}"
        PixivHelper.print_and_log('warn', msg)
