# -*- coding: utf-8 -*-
import gc
import sys
import time
import traceback

import PixivBrowserFactory
import PixivConstant
import PixivDownloadHandler
import PixivException
import PixivHelper
import PixivImageHandler


def process_member(caller,
                   member_id,
                   user_dir='',
                   page=1,
                   end_page=0,
                   bookmark=False,
                   tags=None,
                   title_prefix="",
                   notification_handler=None):
    # caller function/method
    # TODO: ideally to be removed or passed as argument
    db = caller.__dbManager__
    config = caller.__config__
    config.loadConfig(path=caller.configfile)
    np = caller.np
    np_is_valid = caller.np_is_valid

    if notification_handler is None:
        notification_handler = PixivHelper.print_and_log

    list_page = None

    notification_handler('info', 'Processing Member Id: ' + str(member_id))
    if page != 1:
        notification_handler('info', 'Start Page: ' + str(page))
    if end_page != 0:
        notification_handler('info', 'End Page: ' + str(end_page))
        if config.numberOfPage != 0:
            notification_handler('info', 'Number of page setting will be ignored')
    elif np != 0:
        notification_handler('info', 'End Page from command line: ' + str(np))
    elif config.numberOfPage != 0:
        notification_handler('info', 'End Page from config: ' + str(config.numberOfPage))

    # calculate the offset for display properties
    offset = 48  # new offset for AJAX call
    offset_start = (page - 1) * offset
    offset_stop = end_page * offset

    try:
        no_of_images = 1
        is_avatar_downloaded = False
        flag = True
        updated_limit_count = 0
        image_id = -1

        while flag:
            notification_handler(None, 'Page ', page)
            caller.set_console_title(f"{title_prefix}MemberId: {member_id} Page: {page}")
            # Try to get the member page
            while True:
                try:
                    (artist, list_page) = PixivBrowserFactory.getBrowser().getMemberPage(member_id, page, bookmark, tags)
                    break
                except PixivException as ex:
                    caller.ERROR_CODE = ex.errorCode
                    notification_handler('info', f'Member ID ({member_id}): {ex}')
                    if ex.errorCode == PixivException.NO_IMAGES:
                        pass
                    else:
                        if list_page is None:
                            list_page = ex.htmlPage
                        if list_page is not None:
                            PixivHelper.dump_html(f"Dump for {member_id} Error Code {ex.errorCode}.html", list_page)
                        if ex.errorCode == PixivException.USER_ID_NOT_EXISTS or ex.errorCode == PixivException.USER_ID_SUSPENDED:
                            db.setIsDeletedFlagForMemberId(int(member_id))
                            notification_handler('info', f'Set IsDeleted for MemberId: {member_id} not exist.')
                            # db.deleteMemberByMemberId(member_id)
                            # PixivHelper.printAndLog('info', 'Deleting MemberId: ' + str(member_id) + ' not exist.')
                        if ex.errorCode == PixivException.OTHER_MEMBER_ERROR:
                            notification_handler(None, ex.message)
                            caller.__errorList.append(dict(type="Member", id=str(member_id), message=ex.message, exception=ex))
                    return
                except AttributeError:
                    # Possible layout changes, try to dump the file below
                    raise
                except Exception:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exception(exc_type, exc_value, exc_traceback)
                    notification_handler('error', f'Error at processing Artist Info: {sys.exc_info()}')

            notification_handler(None, f'Member Name  : {artist.artistName}')
            notification_handler(None, f'Member Avatar: {artist.artistAvatar}')
            notification_handler(None, f'Member Token : {artist.artistToken}')
            notification_handler(None, f'Member Background : {artist.artistBackground}')
            print_offset_stop = offset_stop if offset_stop < artist.totalImages and offset_stop != 0 else artist.totalImages
            notification_handler(None, f'Processing images from {offset_start + 1} to {print_offset_stop} of {artist.totalImages}')

            if not is_avatar_downloaded and config.downloadAvatar:
                if user_dir == '':
                    target_dir = config.rootDirectory
                else:
                    target_dir = user_dir

                avatar_filename = PixivHelper.create_avatar_filename(artist, target_dir)
                if not caller.DEBUG_SKIP_PROCESS_IMAGE:
                    if artist.artistAvatar.find('no_profile') == -1:
                        PixivDownloadHandler.download_image(caller,
                                                            artist.artistAvatar,
                                                            avatar_filename,
                                                            "https://www.pixiv.net/",
                                                            config.overwrite,
                                                            config.retry,
                                                            config.backupOldFile,
                                                            notification_handler=notification_handler)
                    # Issue #508
                    if artist.artistBackground is not None and artist.artistBackground.startswith("http"):
                        bg_name = PixivHelper.create_bg_filename_from_avatar_filename(avatar_filename)
                        PixivDownloadHandler.download_image(caller,
                                                            artist.artistBackground,
                                                            bg_name,
                                                            "https://www.pixiv.net/",
                                                            config.overwrite,
                                                            config.retry,
                                                            config.backupOldFile,
                                                            notification_handler=notification_handler)
                        is_avatar_downloaded = True

            if config.autoAddMember:
                db.insertNewMember(int(member_id))

            db.updateMemberName(member_id, artist.artistName)

            if not artist.haveImages:
                notification_handler('info', f"No image found for: {member_id}")
                flag = False
                continue

            result = PixivConstant.PIXIVUTIL_NOT_OK
            for image_id in artist.imageList:
                notification_handler(None, f'#{no_of_images}')

                retry_count = 0
                while True:
                    try:
                        if artist.totalImages > 0:
                            # PixivHelper.safePrint("Total Images = " + str(artist.totalImages))
                            total_image_page_count = artist.totalImages
                            if(offset_stop > 0 and offset_stop < total_image_page_count):
                                total_image_page_count = offset_stop
                            total_image_page_count = total_image_page_count - offset_start
                            # PixivHelper.safePrint("Total Images Offset = " + str(total_image_page_count))
                        else:
                            total_image_page_count = ((page - 1) * 20) + len(artist.imageList)
                        title_prefix_img = f"{title_prefix}MemberId: {member_id} Page: {page} Post {no_of_images}+{updated_limit_count} of {total_image_page_count}"
                        if not caller.DEBUG_SKIP_PROCESS_IMAGE:
                            result = PixivImageHandler.process_image(caller,
                                                                     artist,
                                                                     image_id,
                                                                     user_dir,
                                                                     bookmark,
                                                                     title_prefix=title_prefix_img,
                                                                     notification_handler=notification_handler)

                        break
                    except KeyboardInterrupt:
                        result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                        break
                    except BaseException:
                        if retry_count > config.retry:
                            notification_handler('error', f"Giving up image_id: {image_id}")
                            return
                        retry_count = retry_count + 1
                        notification_handler(None, f"Stuff happened, trying again after 2 second ({retry_count})")
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
                        notification_handler("error", f"Error at process_member(): {sys.exc_info()} Member Id: {member_id}")
                        time.sleep(2)

                if result in (PixivConstant.PIXIVUTIL_SKIP_DUPLICATE,
                              PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER,
                              PixivConstant.PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT):
                    updated_limit_count = updated_limit_count + 1
                    if config.checkUpdatedLimit != 0 and updated_limit_count > config.checkUpdatedLimit:
                        PixivHelper.safePrint(f"Skipping tags: {tags}")
                        PixivBrowserFactory.getBrowser(config=config).clear_history()
                        return
                    gc.collect()
                    continue
                if result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                    choice = input("Keyboard Interrupt detected, continue to next image (Y/N)").rstrip("\r")
                    if choice.upper() == 'N':
                        notification_handler("info", f"Member: {member_id}, processing aborted")
                        flag = False
                        break
                    else:
                        continue
                # return code from process image
                if result == PixivConstant.PIXIVUTIL_SKIP_OLDER:
                    notification_handler("info", "Reached older images, skippin to next member.")
                    flag = False
                    break

                no_of_images = no_of_images + 1
                PixivHelper.wait(result, config)

            if artist.isLastPage:
                notification_handler(None, "Last Page")
                flag = False

            page = page + 1

            # page limit checking
            if end_page > 0 and page > end_page:
                notification_handler(None, f"Page limit reached (from endPage limit ={end_page})")
                flag = False
            else:
                if np_is_valid:  # Yavos: overwriting config-data
                    if page > np and np > 0:
                        notification_handler(None, f"Page limit reached (from command line ={np})")
                        flag = False
                elif page > config.numberOfPage and config.numberOfPage > 0:
                    notification_handler(None, f"Page limit reached (from config ={config.numberOfPage})")
                    flag = False

            del artist
            del list_page
            PixivBrowserFactory.getBrowser(config=config).clear_history()
            gc.collect()

        log_message = ""
        if int(image_id) > 0:
            db.updateLastDownloadedImage(member_id, image_id)
            log_message = f'last image_id: {image_id}'
        else:
            log_message = 'no images were found.'

        notification_handler("info", f"Member_id: {member_id} completed: {log_message}")
    except KeyboardInterrupt:
        raise
    except BaseException:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        notification_handler('error', f'Error at process_member(): {sys.exc_info()}')
        try:
            if list_page is not None:
                dump_filename = f'Error page for member {member_id} at page {page}.html'
                PixivHelper.dump_html(dump_filename, list_page)
                notification_handler('error', f"Dumping html to: {dump_filename}")
        except BaseException:
            notification_handler('error', f'Cannot dump page for member_id: {member_id}')
        raise
