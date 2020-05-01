# -*- coding: utf-8 -*-


def process_member(member_id, user_dir='', page=1, end_page=0, bookmark=False, tags=None, title_prefix=""):
    global __errorList
    global ERROR_CODE
    list_page = None

    PixivHelper.print_and_log('info', 'Processing Member Id: ' + str(member_id))
    if page != 1:
        PixivHelper.print_and_log('info', 'Start Page: ' + str(page))
    if end_page != 0:
        PixivHelper.print_and_log('info', 'End Page: ' + str(end_page))
        if __config__.numberOfPage != 0:
            PixivHelper.print_and_log('info', 'Number of page setting will be ignored')
    elif np != 0:
        PixivHelper.print_and_log('info', 'End Page from command line: ' + str(np))
    elif __config__.numberOfPage != 0:
        PixivHelper.print_and_log('info', 'End Page from config: ' + str(__config__.numberOfPage))

    __config__.loadConfig(path=configfile)

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
            print('Page ', page)
            set_console_title("{0}MemberId: {1} Page: {2}".format(title_prefix, member_id, page))
            # Try to get the member page
            while True:
                try:
                    (artist, list_page) = PixivBrowserFactory.getBrowser().getMemberPage(member_id, page, bookmark, tags)
                    break
                except PixivException as ex:
                    ERROR_CODE = ex.errorCode
                    PixivHelper.print_and_log('info', 'Member ID (' + str(member_id) + '): ' + str(ex))
                    if ex.errorCode == PixivException.NO_IMAGES:
                        pass
                    else:
                        if list_page is None:
                            list_page = ex.htmlPage
                        if list_page is not None:
                            PixivHelper.dump_html("Dump for " + str(member_id) + " Error Code " + str(ex.errorCode) + ".html", list_page)
                        if ex.errorCode == PixivException.USER_ID_NOT_EXISTS or ex.errorCode == PixivException.USER_ID_SUSPENDED:
                            __dbManager__.setIsDeletedFlagForMemberId(int(member_id))
                            PixivHelper.print_and_log('info', 'Set IsDeleted for MemberId: ' + str(member_id) + ' not exist.')
                            # __dbManager__.deleteMemberByMemberId(member_id)
                            # PixivHelper.printAndLog('info', 'Deleting MemberId: ' + str(member_id) + ' not exist.')
                        if ex.errorCode == PixivException.OTHER_MEMBER_ERROR:
                            PixivHelper.safePrint(ex.message)
                            __errorList.append(dict(type="Member", id=str(member_id), message=ex.message, exception=ex))
                    return
                except AttributeError:
                    # Possible layout changes, try to dump the file below
                    raise
                except Exception:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    traceback.print_exception(exc_type, exc_value, exc_traceback)
                    PixivHelper.print_and_log('error', 'Error at processing Artist Info: {0}'.format(sys.exc_info()))

            PixivHelper.safePrint('Member Name  : ' + artist.artistName)
            print('Member Avatar:', artist.artistAvatar)
            print('Member Token :', artist.artistToken)
            print('Member Background :', artist.artistBackground)
            print_offset_stop = offset_stop if offset_stop < artist.totalImages and offset_stop != 0 else artist.totalImages
            print('Processing images from {0} to {1} of {2}'.format(offset_start + 1, print_offset_stop, artist.totalImages))

            if not is_avatar_downloaded and __config__.downloadAvatar:
                if user_dir == '':
                    target_dir = __config__.rootDirectory
                else:
                    target_dir = user_dir

                avatar_filename = PixivHelper.create_avatar_filename(artist, target_dir)
                if not DEBUG_SKIP_PROCESS_IMAGE:
                    if artist.artistAvatar.find('no_profile') == -1:
                        download_image(artist.artistAvatar,
                                       avatar_filename,
                                       "https://www.pixiv.net/",
                                       __config__.overwrite,
                                       __config__.retry,
                                       __config__.backupOldFile)
                    # Issue #508
                    if artist.artistBackground is not None and artist.artistBackground.startswith("http"):
                        bg_name = PixivHelper.create_bg_filename_from_avatar_filename(avatar_filename)
                        download_image(artist.artistBackground,
                                       bg_name, "https://www.pixiv.net/",
                                       __config__.overwrite,
                                       __config__.retry,
                                       __config__.backupOldFile)
                is_avatar_downloaded = True

            if __config__.autoAddMember:
                __dbManager__.insertNewMember(int(member_id))

            __dbManager__.updateMemberName(member_id, artist.artistName)

            if not artist.haveImages:
                PixivHelper.print_and_log('info', "No image found for: " + str(member_id))
                flag = False
                continue

            result = PixivConstant.PIXIVUTIL_NOT_OK
            for image_id in artist.imageList:
                print('#' + str(no_of_images))

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
                        title_prefix_img = "{0}MemberId: {1} Page: {2} Post {3}+{4} of {5}".format(title_prefix,
                                                                                                   member_id,
                                                                                                   page,
                                                                                                   no_of_images,
                                                                                                   updated_limit_count,
                                                                                                   total_image_page_count)
                        if not DEBUG_SKIP_PROCESS_IMAGE:
                            result = process_image(artist, image_id, user_dir, bookmark, title_prefix=title_prefix_img)

                        break
                    except KeyboardInterrupt:
                        result = PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT
                        break
                    except BaseException:
                        if retry_count > __config__.retry:
                            PixivHelper.print_and_log('error', "Giving up image_id: {0}".format(image_id))
                            return
                        retry_count = retry_count + 1
                        print("Stuff happened, trying again after 2 second (", retry_count, ")")
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        traceback.print_exception(exc_type, exc_value, exc_traceback)
                        __log__.exception('Error at process_member(): %s Member Id: %d', str(sys.exc_info()), member_id)
                        time.sleep(2)

                if result in (PixivConstant.PIXIVUTIL_SKIP_DUPLICATE,
                              PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER,
                              PixivConstant.PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT):
                    updated_limit_count = updated_limit_count + 1
                    if __config__.checkUpdatedLimit != 0 and updated_limit_count > __config__.checkUpdatedLimit:
                        PixivHelper.safePrint("Skipping tags: {0}".format(tags))
                        __br__.clear_history()
                        return
                    gc.collect()
                    continue
                if result == PixivConstant.PIXIVUTIL_KEYBOARD_INTERRUPT:
                    choice = input("Keyboard Interrupt detected, continue to next image (Y/N)").rstrip("\r")
                    if choice.upper() == 'N':
                        PixivHelper.print_and_log("info", "Member: " + str(member_id) + ", processing aborted")
                        flag = False
                        break
                    else:
                        continue
                # return code from process image
                if result == PixivConstant.PIXIVUTIL_SKIP_OLDER:
                    PixivHelper.print_and_log("info", "Reached older images, skippin to next member.")
                    flag = False
                    break

                no_of_images = no_of_images + 1
                wait(result)

            if artist.isLastPage:
                print("Last Page")
                flag = False

            page = page + 1

            # page limit checking
            if end_page > 0 and page > end_page:
                print("Page limit reached (from endPage limit =" + str(end_page) + ")")
                flag = False
            else:
                if np_is_valid:  # Yavos: overwriting config-data
                    if page > np and np > 0:
                        print("Page limit reached (from command line =" + str(np) + ")")
                        flag = False
                elif page > __config__.numberOfPage and __config__.numberOfPage > 0:
                    print("Page limit reached (from config =" + str(__config__.numberOfPage) + ")")
                    flag = False

            del artist
            del list_page
            __br__.clear_history()
            gc.collect()

        if int(image_id) > 0:
            __dbManager__.updateLastDownloadedImage(member_id, image_id)
            log_message = 'last image_id: ' + str(image_id)
        else:
            log_message = 'no images were found'

        print('Done.\n')
        __log__.info('Member_id: %d complete, %s', member_id, log_message)
    except KeyboardInterrupt:
        raise
    except BaseException:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        PixivHelper.print_and_log('error', 'Error at process_member(): {0}'.format(sys.exc_info()))
        try:
            if list_page is not None:
                dump_filename = 'Error page for member {0} at page {1}.html'.format(member_id, page)
                PixivHelper.dump_html(dump_filename, list_page)
                PixivHelper.print_and_log('error', "Dumping html to: {0}".format(dump_filename))
        except BaseException:
            PixivHelper.print_and_log('error', 'Cannot dump page for member_id: {0}'.format(member_id))
        raise
