# -*- coding: utf-8 -*-
import gc
import http.client
import os
import sys
import time

import PixivBrowserFactory
import PixivConstant
import PixivHelper
import PixivImageHandler


def process_tags(caller,
                 tags,
                 page=1,
                 end_page=0,
                 wild_card=True,
                 title_caption=False,
                 start_date=None,
                 end_date=None,
                 use_tags_as_dir=False,
                 member_id=None,
                 bookmark_count=None,
                 oldest_first=False,
                 type_mode=None,
                 notification_handler=None,
                 job_option=None):
    # caller function/method
    # TODO: ideally to be removed or passed as argument
    config = caller.__config__
    config.loadConfig(path=caller.configfile)

    if notification_handler is None:
        notification_handler = PixivHelper.print_and_log

    # override the config source if job_option is give for filename formats
    format_src = config
    if job_option is not None:
        format_src = job_option

    search_page = None
    _last_search_result = None
    i = page
    updated_limit_count = 0

    try:
        search_tags = PixivHelper.decode_tags(tags)

        if use_tags_as_dir:
            notification_handler(None, "Save to each directory using query tags.")
            format_src.rootDirectory += os.sep + PixivHelper.sanitize_filename(search_tags)

        tags = PixivHelper.encode_tags(tags)

        images = 1
        last_image_id = -1
        skipped_count = 0
        use_bookmark_data = False
        if bookmark_count is not None and bookmark_count > 0:
            use_bookmark_data = True

        offset = 60
        start_offset = (page - 1) * offset
        stop_offset = end_page * offset

        notification_handler('info', f'Searching for: ({search_tags}) {tags}')
        flag = True
        while flag:
            (t, search_page) = PixivBrowserFactory.getBrowser().getSearchTagPage(tags,
                                                                                i,
                                                                                wild_card,
                                                                                title_caption,
                                                                                start_date,
                                                                                end_date,
                                                                                member_id,
                                                                                oldest_first,
                                                                                page,
                                                                                use_bookmark_data,
                                                                                bookmark_count,
                                                                                type_mode)
            if len(t.itemList) == 0:
                notification_handler(None, 'No more images')
                flag = False
            elif _last_search_result is not None:
                set1 = set((x.imageId) for x in _last_search_result.itemList)
                difference = [x for x in t.itemList if (x.imageId) not in set1]
                if len(difference) == 0:
                    notification_handler(None, 'Getting duplicated result set, no more new images.')
                    flag = False

            if flag:
                for item in t.itemList:
                    last_image_id = item.imageId
                    notification_handler(None, f'Image #{images}')
                    notification_handler(None, f'Image Id: {item.imageId}')

                    if bookmark_count is not None and bookmark_count > item.bookmarkCount:
                        notification_handler(None, f'Bookmark Count: {item.bookmarkCount}')
                        notification_handler('info', f'Skipping imageId= {item.imageId} because less than bookmark count limit ({bookmark_count} > {item.bookmarkCount}).')
                        skipped_count = skipped_count + 1
                        continue

                    result = 0
                    while True:
                        try:
                            if t.availableImages > 0:
                                # notification_handler(None, "Total Images: " + str(t.availableImages))
                                total_image = t.availableImages
                                if(stop_offset > 0 and stop_offset < total_image):
                                    total_image = stop_offset
                                total_image = total_image - start_offset
                                # notification_handler(None, "Total Images Offset: " + str(total_image))
                            else:
                                total_image = ((i - 1) * 20) + len(t.itemList)
                            title_prefix = "Tags:{0} Page:{1} Image {2}+{3} of {4}".format(tags, i, images, skipped_count, total_image)
                            if member_id is not None:
                                title_prefix = "MemberId: {0} Tags:{1} Page:{2} Image {3}+{4} of {5}".format(member_id,
                                                                                                             tags,
                                                                                                             i,
                                                                                                             images,
                                                                                                             skipped_count,
                                                                                                             total_image)
                            result = PixivConstant.PIXIVUTIL_OK
                            if not caller.DEBUG_SKIP_PROCESS_IMAGE:
                                result = PixivImageHandler.process_image(caller,
                                                                         None,
                                                                         item.imageId,
                                                                         search_tags=search_tags,
                                                                         title_prefix=title_prefix,
                                                                         bookmark_count=item.bookmarkCount,
                                                                         image_response_count=item.imageResponse,
                                                                         notification_handler=notification_handler,
                                                                         job_option=job_option)
                                PixivHelper.wait(result, config)
                            break
                        except KeyboardInterrupt:
                            result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                            break
                        except http.client.BadStatusLine:
                            notification_handler(None, "Stuff happened, trying again after 2 second...")
                            time.sleep(2)

                    images = images + 1
                    if result in (PixivConstant.PIXIVUTIL_SKIP_DUPLICATE,
                                  PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER,
                                  PixivConstant.PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT):
                        updated_limit_count = updated_limit_count + 1
                        if config.checkUpdatedLimit != 0 and updated_limit_count > config.checkUpdatedLimit:
                            notification_handler(None, f"Skipping tags: {tags}")
                            PixivBrowserFactory.getBrowser().clear_history()
                            return
                        gc.collect()
                        continue
                    elif result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                        choice = input("Keyboard Interrupt detected, continue to next image (Y/N)").rstrip("\r")
                        if choice.upper() == 'N':
                            notification_handler("info", f"Tags: {tags}, processing aborted.")
                            flag = False
                            break
                        else:
                            continue

            PixivBrowserFactory.getBrowser().clear_history()

            i = i + 1
            _last_search_result = t

            if end_page != 0 and end_page < i:
                notification_handler('info', f"End Page reached: {end_page}")
                flag = False
            if t.isLastPage:
                notification_handler('info', f"Last page: {i - 1}")
                flag = False
            if config.enableInfiniteLoop and i == 1001 and not oldest_first:
                if last_image_id > 0:
                    # get the last date
                    notification_handler('info', f"Hit page 1000, trying to get workdate for last image id: {last_image_id}.")
                    # referer = 'https://www.pixiv.net/en/artworks/{0}'.format(last_image_id)
                    result = PixivBrowserFactory.getBrowser().getImagePage(last_image_id)
                    _last_date = result[0].worksDateDateTime
                    # _start_date = image.worksDateDateTime + datetime.timedelta(365)
                    # hit the last page
                    i = 1
                    end_date = _last_date.strftime("%Y-%m-%d")
                    notification_handler('info', f"Hit page 1000, looping back to page 1 with ecd: {end_date}.")
                    flag = True
                    last_image_id = -1
                else:
                    notification_handler('info', "No more image in the list.")
                    flag = False

        notification_handler(None, 'done')
        if search_page is not None:
            del search_page
    except KeyboardInterrupt:
        raise
    except BaseException:
        notification_handler('error', f'Error at process_tags() at page {i}: {sys.exc_info()}')
        try:
            if search_page is not None:
                dump_filename = f'Error page for search tags {tags} at page {i}.html'
                PixivHelper.dump_html(dump_filename, search_page)
                notification_handler('error', f"Dumping html to: {dump_filename}")
        except BaseException:
            notification_handler('error', f'Cannot dump page for search tags: {search_tags}')
        raise
