# -*- coding: utf-8 -*-
import gc
import sys
import traceback

from colorama import Fore, Style

import PixivBrowserFactory
import PixivConstant
import PixivDownloadHandler
import PixivHelper
import PixivImageHandler
from PixivException import PixivException


def process_member(caller,
                   config,
                   member_id,
                   user_dir='',
                   page=1,
                   end_page=0,
                   bookmark=False,
                   tags=None,
                   title_prefix="",
                   bookmark_count=None,
                   notifier=None):
    # caller function/method
    # TODO: ideally to be removed or passed as argument
    db = caller.__dbManager__
    # np = caller.np
    # np_is_valid = caller.np_is_valid

    if notifier is None:
        notifier = PixivHelper.dummy_notifier

    list_page = None

    msg = Fore.YELLOW + Style.BRIGHT + f'Processing Member Id: {member_id}' + Style.RESET_ALL
    PixivHelper.print_and_log('info', msg)
    notifier(type="MEMBER", message=msg)
    if page != 1:
        PixivHelper.print_and_log('info', 'Start Page: ' + str(page))
    if end_page != 0:
        PixivHelper.print_and_log('info', 'End Page: ' + str(end_page))
        if config.numberOfPage != 0:
            PixivHelper.print_and_log('info', 'Number of page setting will be ignored')
    elif config.numberOfPage != 0:
        PixivHelper.print_and_log('info', f'End Page from config: {config.numberOfPage}')

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
            PixivHelper.print_and_log(None, 'Page ', page)
            caller.set_console_title(f"{title_prefix}MemberId: {member_id} Page: {page}")
            # Try to get the member page
            while True:
                try:
                    (artist, list_page) = PixivBrowserFactory.getBrowser().getMemberPage(member_id, page, bookmark, tags, r18mode=config.r18mode, throw_empty_error=True)
                    break
                except PixivException as ex:
                    caller.ERROR_CODE = ex.errorCode
                    PixivHelper.print_and_log('info', f'Member ID ({member_id}): {ex}')
                    if ex.errorCode == PixivException.NO_IMAGES:
                        pass
                    else:
                        if list_page is None:
                            list_page = ex.htmlPage
                        if list_page is not None:
                            PixivHelper.dump_html(f"Dump for {member_id} Error Code {ex.errorCode}.html", list_page)
                        if ex.errorCode == PixivException.USER_ID_NOT_EXISTS or ex.errorCode == PixivException.USER_ID_SUSPENDED:
                            db.setIsDeletedFlagForMemberId(int(member_id))
                            PixivHelper.print_and_log('info', f'Set IsDeleted for MemberId: {member_id} not exist.')
                            # db.deleteMemberByMemberId(member_id)
                            # PixivHelper.printAndLog('info', 'Deleting MemberId: ' + str(member_id) + ' not exist.')
                        if ex.errorCode == PixivException.OTHER_MEMBER_ERROR:
                            PixivHelper.print_and_log(None, ex.message)
                            caller.__errorList.append(dict(type="Member", id=str(member_id), message=ex.message, exception=ex))
                    return
                except AttributeError:
                    # Possible layout changes, try to dump the file below
                    raise
                except BaseException:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exception(exc_type, exc_value, exc_traceback)
                    PixivHelper.print_and_log('error', f'Error at processing Artist Info: {sys.exc_info()}')

            PixivHelper.print_and_log(None, f'Member Name  : {artist.artistName}')
            PixivHelper.print_and_log(None, f'Member Avatar: {artist.artistAvatar}')
            PixivHelper.print_and_log(None, f'Member Token : {artist.artistToken}')
            PixivHelper.print_and_log(None, f'Member Background : {artist.artistBackground}')
            print_offset_stop = offset_stop if offset_stop < artist.totalImages and offset_stop != 0 else artist.totalImages
            PixivHelper.print_and_log(None, f'Processing images from {offset_start + 1} to {print_offset_stop} of {artist.totalImages}')

            if not is_avatar_downloaded and config.downloadAvatar:
                if user_dir == '':
                    target_dir = config.rootDirectory
                else:
                    target_dir = user_dir

                (filename_avatar, filename_bg) = PixivHelper.create_avabg_filename(artist, target_dir, config)
                if not caller.DEBUG_SKIP_PROCESS_IMAGE:
                    if artist.artistAvatar.find('no_profile') == -1:
                        PixivDownloadHandler.download_image(caller,
                                                            artist.artistAvatar,
                                                            filename_avatar,
                                                            "https://www.pixiv.net/",
                                                            config.overwrite,
                                                            config.retry,
                                                            config.backupOldFile,
                                                            notifier=notifier)
                    # Issue #508
                    if artist.artistBackground is not None and artist.artistBackground.startswith("http"):
                        PixivDownloadHandler.download_image(caller,
                                                            artist.artistBackground,
                                                            filename_bg,
                                                            "https://www.pixiv.net/",
                                                            config.overwrite,
                                                            config.retry,
                                                            config.backupOldFile,
                                                            notifier=notifier)
                    is_avatar_downloaded = True

            if config.autoAddMember:
                db.insertNewMember(int(member_id), member_token=artist.artistToken)

            db.updateMemberName(member_id, artist.artistName, artist.artistToken)

            if not artist.haveImages:
                PixivHelper.print_and_log('info', f"No image found for: {member_id}")
                db.updateLastDownloadDate(member_id)
                flag = False
                continue

            result = PixivConstant.PIXIVUTIL_NOT_OK
            for image_id in artist.imageList:
                PixivHelper.print_and_log(None, f'#{no_of_images}')
                retry_count = 0
                while True:
                    try:
                        if artist.totalImages > 0:
                            # PixivHelper.safePrint("Total Images = " + str(artist.totalImages))
                            total_image_page_count = artist.totalImages
                            if (offset_stop > 0 and offset_stop < total_image_page_count):
                                total_image_page_count = offset_stop
                            total_image_page_count = total_image_page_count - offset_start
                            # PixivHelper.safePrint("Total Images Offset = " + str(total_image_page_count))
                        else:
                            total_image_page_count = ((page - 1) * 20) + len(artist.imageList)
                        title_prefix_img = f"{title_prefix}MemberId: {member_id} Page: {page} Post {no_of_images}+{updated_limit_count} of {total_image_page_count}"
                        if not caller.DEBUG_SKIP_PROCESS_IMAGE:
                            result = PixivImageHandler.process_image(caller,
                                                                     config,
                                                                     artist,
                                                                     image_id,
                                                                     user_dir,
                                                                     bookmark,
                                                                     title_prefix=title_prefix_img,
                                                                     bookmark_count=bookmark_count,
                                                                     notifier=notifier)

                        break
                    except KeyboardInterrupt:
                        result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                        break
                    except BaseException:
                        if retry_count > config.retry:
                            PixivHelper.print_and_log('error', f"Giving up image_id: {image_id}")
                            return
                        retry_count = retry_count + 1
                        PixivHelper.print_and_log(None, f"Stuff happened, trying again after 2 second ({retry_count})")
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
                        PixivHelper.print_and_log("error", f"Error at process_member(): {sys.exc_info()} Member Id: {member_id}")
                        PixivHelper.print_delay(2)

                if result in (PixivConstant.PIXIVUTIL_SKIP_DUPLICATE,
                              PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER,
                              PixivConstant.PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT):
                    updated_limit_count = updated_limit_count + 1
                    if config.checkUpdatedLimit != 0 and updated_limit_count >= config.checkUpdatedLimit:
                        PixivHelper.safePrint(f"Skipping member: {member_id}")
                        db.updateLastDownloadDate(member_id)
                        PixivBrowserFactory.getBrowser(config=config).clear_history()
                        return
                    gc.collect()
                    continue
                if result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                    choice = input("Keyboard Interrupt detected, continue to next image (Y/N)").rstrip("\r")
                    if choice.upper() == 'N':
                        PixivHelper.print_and_log("info", f"Member: {member_id}, processing aborted")
                        flag = False
                        break
                    else:
                        continue
                # return code from process image
                if result == PixivConstant.PIXIVUTIL_SKIP_OLDER:
                    PixivHelper.print_and_log("info", "Reached older images, skippin to next member.")
                    db.updateLastDownloadDate(member_id)
                    flag = False
                    break

                no_of_images = no_of_images + 1
                PixivHelper.wait(result, config)

            if artist.isLastPage:
                db.updateLastDownloadDate(member_id)
                PixivHelper.print_and_log(None, "Last Page")
                flag = False

            page = page + 1

            # page limit checking
            if end_page > 0 and page > end_page:
                PixivHelper.print_and_log(None, f"Page limit reached (from endPage limit ={end_page})")
                db.updateLastDownloadDate(member_id)
                flag = False
            elif config.numberOfPage > 0 and page > config.numberOfPage:
                PixivHelper.print_and_log(None, f"Page limit reached (from config ={config.numberOfPage})")
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

        PixivHelper.print_and_log("info", f"Member_id: {member_id} completed: {log_message}")
    except KeyboardInterrupt:
        raise
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        PixivHelper.print_and_log('error', f'Error at process_member(): {sys.exc_info()}')
        try:
            if list_page is not None:
                dump_filename = f'Error page for member {member_id} at page {page}.html'
                PixivHelper.dump_html(dump_filename, list_page)
                PixivHelper.print_and_log('error', f"Dumping html to: {dump_filename}")
        except BaseException:
            PixivHelper.print_and_log('error', f'Cannot dump page for member_id: {member_id}')
        raise
