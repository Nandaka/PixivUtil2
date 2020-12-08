import os
import sys
import time

import PixivArtistHandler
import PixivHelper
import PixivTagsHandler
from PixivListItem import PixivListItem
from PixivTags import PixivTags


def process_list(caller, config, list_file_name=None, tags=None):
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
                print('Select only last', config.dayLastUpdated, 'days.')
                result = db.selectMembersByLastDownloadDate(config.dayLastUpdated)
        else:
            PixivHelper.print_and_log('info', 'Processing from list file: {0}'.format(list_file_name))
            result = PixivListItem.parseList(list_file_name, config.rootDirectory)

        if os.path.exists("ignore_list.txt"):
            PixivHelper.print_and_log('info', 'Processing ignore list for member: {0}'.format("ignore_list.txt"))
            ignore_list = PixivListItem.parseList("ignore_list.txt", config.rootDirectory)
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
                    prefix = "[{0} of {1}] ".format(current_member, len(result))
                    if tags:
                        PixivTagsHandler.process_tags(caller, tags, member_id=item.memberId)
                        db.updateLastDownloadDate(item.memberId)
                    else:
                        PixivArtistHandler.process_member(caller,
                                                        config,
                                                        item.memberId,
                                                        user_dir=item.path,
                                                        title_prefix=prefix)
                    current_member = current_member + 1
                    break
                except KeyboardInterrupt:
                    raise
                except BaseException:
                    if retry_count > config.retry:
                        PixivHelper.print_and_log('error', 'Giving up member_id: ' + str(item.memberId))
                        break
                    retry_count = retry_count + 1
                    print('Something wrong, retrying after 2 second (', retry_count, ')')
                    time.sleep(2)

            br.clear_history()
            print('done.')
    except Exception as ex:
        if isinstance(ex, KeyboardInterrupt):
            raise
        caller.ERROR_CODE = getattr(ex, 'errorCode', -1)
        PixivHelper.print_and_log('error', 'Error at process_list(): {0}'.format(sys.exc_info()))
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
        PixivHelper.print_and_log('error', 'Error at process_tags_list(): {0}'.format(sys.exc_info()))
        raise


def import_list(caller,
                config,
                list_name='list.txt'):
    list_path = config.downloadListDirectory + os.sep + list_name
    if os.path.exists(list_path):
        list_txt = PixivListItem.parseList(list_path, config.rootDirectory)
        caller.__dbManager__.importList(list_txt)
        print("Updated " + str(len(list_txt)) + " items.")
    else:
        msg = "List file not found: {0}".format(list_path)
        PixivHelper.print_and_log('warn', msg)


def process_blacklist(caller, config, imagedata, tags=[]):
    import re
    flag = False
    toDownload = []
    if config.r18mode:
        tags.append['R-18']
    for image in imagedata:
        if "isAdContainer" in image and image["isAdContainer"]:
            continue
        notRemoved = True                   

        if config.dateDiff:
            if image["createDate"]:
                flag = True
                break
        
        if tags:
            for x in tags:
                if x not in image["tags"]:
                    notRemoved = False
                    break


        if config.useBlacklistTags and notRemoved:
            for item in caller.__blacklistTags:
                if item in image["tags"]:
                    PixivHelper.print_and_log('warn', f'Skipping image_id: {image["id"]} – blacklisted tag: {item}')
                    notRemoved = False
                    break

        if config.useBlacklistTitles and notRemoved:
            if config.useBlacklistTitlesRegex:
                for item in caller.__blacklistTitles:
                    if re.search(rf"{item}", image["title"]):
                        PixivHelper.print_and_log('warn', f'Skipping image_id: {image["id"]} – Title matched: {item}')
                        notRemoved = False
                        break
            else:
                for item in caller.__blacklistTitles:
                    if item in image["title"]:
                        PixivHelper.print_and_log('warn', f'Skipping image_id: {image["id"]} – Title contained: {item}')
                        notRemoved = False
                        break

        if notRemoved:
           toDownload.append(image["id"])
    return toDownload, flag


def process_list_with_db(caller, limit, images):
    count = 0
    newimages = []
    db = caller.__dbManager__
    for image in images:
            if db.selectImageByImageId(image):
                count += 1
            else:
                count = 0
                newimages.append(image)
            if count == limit:
                return newimages, True
    return newimages, False
