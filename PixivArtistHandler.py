# -*- coding: utf-8 -*-
import gc
import sys
import time
import traceback

from colorama import Fore, Style

import PixivBrowserFactory
import PixivConstant
import PixivDownloadHandler
import PixivHelper
import PixivImageHandler
from PixivException import PixivException
from PixivListHandler import process_blacklist, process_list_with_db


def process_member(caller,
                   config,
                   member_id,
                   page=1,
                   end_page=0,
                   title_prefix="",
                   notifier=None,
                   useImageIDs=False):
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
        end_page= config.numberOfPage

    try:
        no_of_images = 1
        flag = True
        updated_limit_count = 0
        image_id = -1
        if useImageIDs:
            caller.set_console_title(f"{title_prefix}MemberId: {member_id} Images: {page} to {end_page}")
        else:
            caller.set_console_title(f"{title_prefix}MemberId: {member_id} Pages: {page} to {end_page}")
        # Try to get the member page
        while True:
            try:
                (artist, list_page) = PixivBrowserFactory.getExistingBrowser().getMemberPage(member_id, r18mode=config.r18mode)
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
        #PixivHelper.print_and_log(None, f'Processing images from {offset_start + 1} to {print_offset_stop} of {artist.totalImages}')

        if config.downloadAvatar:
            (filename_avatar, filename_bg) = PixivHelper.create_avabg_filename(artist, config.rootDirectory, config)
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

        if config.writeMemberJSON:
            if not caller.DEBUG_SKIP_PROCESS_IMAGE:
                import codecs
                filename = PixivHelper.make_filename(config.filenameMemberJSON, artistInfo=artist, targetDir=config.rootDirectory ,appendExtension=False)+".json"
                try:
                    # Issue #421 ensure subdir exists.
                    PixivHelper.makeSubdirs(filename)
                    outfile = codecs.open(filename, 'w', encoding='utf-8')
                except IOError:
                    outfile = codecs.open(f"Artist {artist.member_id} ({artist.artistName}).json", 'w', encoding='utf-8')
                    PixivHelper.get_logger().exception("Error when saving image info: %s, file is saved to: %s.json", filename, f"Artist {artist.member_id} ({artist.artistName}).json")
                outfile.write(PixivBrowserFactory.getExistingBrowser().getArtistJSON(artist.artistId))
                outfile.close()

        if config.autoAddMember:
            db.insertNewMember(int(member_id))

        db.updateMemberName(member_id, artist.artistName)

        if not artist.haveImages:
            PixivHelper.print_and_log('info', f"No image found for: {member_id}")
            db.updateLastDownloadDate(member_id)
            return

        result = PixivConstant.PIXIVUTIL_NOT_OK
        if useImageIDs:
            artist.imageList=[int(x) for x in artist.imageList if int(x) <= end_page and int(x) >= page]
        else:
            startpage = (page-1)*48
            finalpage = end_page*48
            if startpage > artist.totalImages:
                pass
            artist.imageList=artist.imageList[startpage:finalpage if finalpage else artist.totalImages]

        usingBlacklist = config.preprocess != 0 and config.useBlacklistTags or config.useBlacklistTitles or config.dateDiff
        if config.preprocess == 2:
            artist.imageList = process_list_with_db(caller, config.checkUpdatedLimit, artist.imageList)
            if artist.imageList == []:
                PixivHelper.print_and_log('info', f"No new images found for: {member_id}")
                return
            

        for t in range(0,len(artist.imageList)//100+1 if usingBlacklist else 1):
            flag = False
            images = []
            if usingBlacklist:
                imagedata = PixivBrowserFactory.getExistingBrowser().getMemberImages(member_id,artist.imageList[t*100:(t+1)*100]).values() #API limits us to 100 illusts at a time
                images, flag = process_blacklist(caller, config, imagedata)
            else:
                images = artist.imageList
            for image_id in images:
                PixivHelper.print_and_log(None, f'#{no_of_images}')
                retry_count = 0
                while True:
                    try:
                        #if artist.totalImages > 0:
                        #    PixivHelper.safePrint("Total Images = " + str(artist.totalImages))
                        #    # PixivHelper.safePrint("Total Images Offset = " + str(total_image_page_count))
                        #else:
                        #    total_image_page_count = ((page - 1) * 20) + len(artist.imageList)
                        title_prefix_img = f"{title_prefix}MemberId: {member_id}{' Page: '+str(page) if not useImageIDs else ''} Post {no_of_images}+{updated_limit_count} of {artist.totalImages}"
                        if not caller.DEBUG_SKIP_PROCESS_IMAGE:
                            result = PixivImageHandler.process_image(caller,
                                                                        config,
                                                                        artist,
                                                                        image_id,
                                                                        title_prefix=title_prefix_img,
                                                                        notifier=notifier,
                                                                        useblacklist=not usingBlacklist)
                        break
                    except KeyboardInterrupt:
                        result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                        break
                    except BaseException:
                        if retry_count > config.retry:
                            PixivHelper.dump_id(image_id) #might lead to double adding
                            PixivHelper.print_and_log('error', f"Giving up image_id: {image_id}")
                            return
                        retry_count = retry_count + 1
                        PixivHelper.print_and_log(None, f"Stuff happened, trying again after 2 second ({retry_count})")
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
                        PixivHelper.print_and_log("error", f"Error at process_member(): {sys.exc_info()} Member Id: {member_id}")
                        time.sleep(2)

                if result in (PixivConstant.PIXIVUTIL_SKIP_DUPLICATE,
                                PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER,
                                PixivConstant.PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT):
                    updated_limit_count = updated_limit_count + 1
                    if config.checkUpdatedLimit != 0 and updated_limit_count >= config.checkUpdatedLimit:
                        PixivHelper.safePrint(f"Skipping member: {member_id}")
                        db.updateLastDownloadDate(member_id)
                        PixivBrowserFactory.getBrowser(config=config).clear_history()
                        flag = True
                        break
                    gc.collect()
                    #continue
                if result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                    choice = input("Keyboard Interrupt detected, continue to next image (Y/N)").rstrip("\r")
                    if choice.upper() == 'N':
                        PixivHelper.print_and_log("info", f"Member: {member_id}, processing aborted")
                        flag = True
                        break
                    else:
                        continue
                # return code from process image
                if result == PixivConstant.PIXIVUTIL_SKIP_OLDER:
                    PixivHelper.print_and_log("info", "Reached older images, skippin to next member.")
                    db.updateLastDownloadDate(member_id)
                    flag = True
                    break
                no_of_images = no_of_images + 1
                PixivHelper.wait(result, config)
            if flag:
                break

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
