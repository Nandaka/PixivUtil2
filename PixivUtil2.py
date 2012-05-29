#!/usr/bin/python # -*- coding: UTF-8 -*-
import sys
import os
import re
import traceback
import logging
import logging.handlers
import gc
import time
import xml.sax.saxutils as saxutils

from mechanize import Browser
import mechanize
from BeautifulSoup import BeautifulSoup, Tag
import urllib2
import urllib

import getpass
import socket
import httplib
import cookielib

import PixivConstant
import PixivConfig
import PixivDBManager
import PixivHelper
from PixivModel import PixivArtist, PixivModelException, PixivImage, PixivListItem, PixivBookmark, PixivTags, PixivNewIllustBookmark

Yavos = True
npisvalid = False
np = 0
opisvalid = False
op = ''

from optparse import OptionParser
import datetime
import codecs
import subprocess

__cj__ = cookielib.LWPCookieJar()
__br__ = Browser(factory=mechanize.RobustFactory())
__br__.set_cookiejar(__cj__)

gc.enable()
##gc.set_debug(gc.DEBUG_LEAK)

__dbManager__ = PixivDBManager.PixivDBManager()
__config__    = PixivConfig.PixivConfig()
__blacklistTags = list()
__suppressTags = list()

### Set up logging###
__log__ = logging.getLogger('PixivUtil'+PixivConstant.PIXIVUTIL_VERSION)
__log__.setLevel(logging.DEBUG)

__logHandler__ = logging.handlers.RotatingFileHandler(PixivConstant.PIXIVUTIL_LOG_FILE, maxBytes=1024000, backupCount=5)
__formatter__  = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
__logHandler__.setFormatter(__formatter__)
__log__.addHandler(__logHandler__)

## http://www.pixiv.net/member_illust.php?mode=medium&illust_id=18830248
__re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
__re_manga_page = re.compile('(\d+(_big)?_p\d+)')

### Utilities function ###
def clearall():
    all = [var for var in globals() if (var[:2], var[-2:]) != ("__", "__") and var != "clearall"]
    for var in all:
        del globals()[var]

def dumpHtml(filename, html):
    try:
        dump = file(filename, 'wb')
        dump.write(html)
        dump.close()
    except :
        pass

def printAndLog(level, msg):
    PixivHelper.safePrint(msg)
    if level == 'info':
        __log__.info(msg)
    elif level == 'error':
        __log__.error(msg)

def customRequest(url):
    if __config__.useProxy:
        proxy = urllib2.ProxyHandler(__config__.proxy)
        opener = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)
##        urllib2.Request.set_proxy(__config__.proxy, None)
##    else:
##        req._tunnel_host = None
    req = urllib2.Request(url)
    return req

#-T04------For download file
def downloadImage(url, filename, referer, overwrite, retry):
    try:
        
        try:
            req = customRequest(url)

            if referer != None:
                req.add_header('Referer', referer)
            else :
                req.add_header('Referer', 'http://www.pixiv.net')

            br2 = Browser()
            br2.set_cookiejar(__cj__)
            if __config__.useProxy:
                br2.set_proxies(__config__.proxy)

            br2.set_handle_robots(__config__.useRobots)
            filesize = -1
            
##            for item in req.headers:
##                print str(item), "=", req.headers[str(item)]
                
            #res = __br__.open(req)
            res = br2.open(req)
            try:
                filesize = int(res.info()['Content-Length'])
##                for item in res.info():
##                    print str(item), "=", res.info()[str(item)]
            except KeyError:
                filesize = -1
            except:
                raise

            if not overwrite and os.path.exists(filename) and os.path.isfile(filename) :
                if int(filesize) == os.path.getsize(filename) :
                    print "\tFile exist! (Identical Size)"
                    return 0 #Yavos: added 0 -> updateImage() will be executed
                else :
                    print "\t Found file with different filesize, removing..."
                    os.remove(filename)

            directory = os.path.dirname(filename)
            if not os.path.exists(directory):
                __log__.info('Creating directory: '+directory)
                os.makedirs(directory)

            try:
                save = file(filename + '.pixiv', 'wb+', 4096)
            except IOError:
                msg = 'Error at downloadImage(): Cannot save ' + url +' to ' + filename + ' ' + str(sys.exc_info())
                PixivHelper.safePrint(msg)
                __log__.error(unicode(msg))
                save = file(os.path.split(url)[1], 'wb+', 4096)

            prev = 0
            curr = 0
            print 'Start downloading...',
            print '{0:22} Bytes'.format(prev),
            try:
                while 1:
                    save.write(res.read(4096))
                    curr = save.tell()
                    print '\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b',
                    print '{0:9} of {1:9} Bytes'.format(curr, filesize),

                    ## check if downloaded file is complete
                    if filesize > 0 and curr == filesize:
                        print ' Complete.'
                        break
                    elif curr == prev:  ## no filesize info
                        print ''
                        break
                    prev = curr
                if iv == True or __config__.createDownloadLists == True:
                    dfile = codecs.open(dfilename, 'a+', encoding='utf-8')
                    dfile.write(filename + "\n")
                    dfile.close()
            except:
                if filesize > 0 and curr < filesize:
                    printAndLog('error', 'Downloaded file incomplete! {0:9} of {1:9} Bytes'.format(curr, filesize))
                    printAndLog('error', 'Filename = ' + unicode(filename))
                    printAndLog('error', 'URL      = {0}'.format(url))
                raise 
            finally:
                save.close()                
                if overwrite and os.path.exists(filename):
                    os.remove(filename)
                os.rename(filename + '.pixiv', filename)
                del save
                del req
                del res
        except urllib2.HTTPError as httpError:
            print httpError
            print str(httpError.code)
            __log__.error('HTTPError: '+ str(httpError) + '(' + url + ')')
            if httpError.code == 404:
                return -1
            raise
        except urllib2.URLError as urlError:
            print urlError
            __log__.error('URLError: '+ str(urlError) + '(' + url + ')')
            raise
        except KeyboardInterrupt:
            printAndLog('info', 'Aborted by user request => Ctrl-C')
            raise
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            __log__.error('Error at downloadImage(): ' + str(sys.exc_info()))
            raise
    except KeyboardInterrupt:
        raise
    except:
        if retry > 0:
            repeat = range(1,__config__.retryWait)
            for t in repeat:
                print t,
                time.sleep(1)
            print ''
            return downloadImage(url, filename, referer, overwrite, retry - 1)
        else :
            raise
    print ' done.'
    return 0
        
def configBrowser():
    if __config__.useProxy:
        __br__.set_proxies(__config__.proxy)
        msg = 'Using proxy: ' + __config__.proxyAddress
        print msg
        __log__.info(msg)
        
    __br__.set_handle_equiv(True)
    #__br__.set_handle_gzip(True)
    __br__.set_handle_redirect(True)
    __br__.set_handle_referer(True)
    __br__.set_handle_robots(__config__.useRobots)
    
    __br__.set_debug_http(__config__.debugHttp)
    if __config__.debugHttp :
        msg = 'Debug HTTP enabled.'
        print msg
        __log__.info(msg)
        
    __br__.visit_response
    __br__.addheaders = [('User-agent', __config__.useragent)]

    socket.setdefaulttimeout(__config__.timeout)

def loadCookie(cookieValue):
    '''Load cookie to the Browser instance'''
    ck = cookielib.Cookie(version=0, name='PHPSESSID', value=cookieValue, port=None, port_specified=False, domain='pixiv.net', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
    __cj__.set_cookie(ck)
    
### Pixiv related function ###
def pixivLoginCookie():
    '''Log in to Pixiv using saved cookie, return True if success'''
    
    printAndLog('info','logging in with saved cookie')
    cookieValue = __config__.cookie
    if len(cookieValue) > 0:
        printAndLog('info','Trying to log with saved cookie')
        loadCookie(cookieValue);
        req = customRequest('http://www.pixiv.net/mypage.php')
        __br__.open(req)
        if __br__.response().geturl() == 'http://www.pixiv.net/mypage.php' :
            print 'done.'
            __log__.info('Logged in using cookie')
            return True
        else :
            printAndLog('info','Cookie already expired/invalid.')
    return False
            
def pixivLogin(username, password):
    '''Log in to Pixiv, return 0 if success'''
    
    try:
        printAndLog('info','Log in using form.')
        req = customRequest(PixivConstant.PIXIV_URL+PixivConstant.PIXIV_LOGIN_URL)
        __br__.open(req)
        
        form = __br__.select_form(nr=PixivConstant.PIXIV_FORM_NUMBER)
        __br__['pixiv_id'] = username
        __br__['pass'] = password

        response = __br__.submit()
        if response.geturl() == 'http://www.pixiv.net/mypage.php':
            print 'done.'
            __log__.info('Logged in')
            ## write back the new cookie value
            for cookie in  __br__._ua_handlers['_cookies'].cookiejar:
                if cookie.name == 'PHPSESSID':
                    print 'new cookie value:', cookie.value
                    __config__.cookie = cookie.value
                    __config__.writeConfig()
                    break                
            return True
        else :
            printAndLog('info','Wrong username or password.')
            return False
    except:
        print 'Error at pixivLogin():',sys.exc_info()
        print 'failed'
        __log__.error('Error at pixivLogin(): ' + str(sys.exc_info()))
        raise

def pixivLoginSSL(username, password):
    try:
        printAndLog('info','Log in using secure form.')
        req = customRequest(PixivConstant.PIXIV_URL_SSL)
        __br__.open(req)
        
        form = __br__.select_form(nr=PixivConstant.PIXIV_FORM_NUMBER_SSL)
        __br__['pixiv_id'] = username
        __br__['pass'] = password

        response = __br__.submit()
        if response.geturl() == 'http://www.pixiv.net/mypage.php':
            print 'done.'
            __log__.info('Logged in')
            ## write back the new cookie value
            for cookie in  __br__._ua_handlers['_cookies'].cookiejar:
                if cookie.name == 'PHPSESSID':
                    print 'new cookie value:', cookie.value
                    __config__.cookie = cookie.value
                    __config__.writeConfig()
                    break                
            return True
        else :
            printAndLog('info','Wrong username or password.')
            return False
    except:
        print 'Error at pixivLoginSSL():',sys.exc_info()
        __log__.error('Error at pixivLoginSSL(): ' + str(sys.exc_info()))
        raise    

def processList(mode):
    global args
    result = None
    try:
        ## Getting the list
        if __config__.processFromDb :
            printAndLog('info','Processing from database.')
            if __config__.dayLastUpdated == 0:
                result = __dbManager__.selectAllMember()
            else :
                print 'Select only last',__config__.dayLastUpdated, 'days.'
                result = __dbManager__.selectMembersByLastDownloadDate(__config__.dayLastUpdated)
        else :
            printAndLog('info','Processing from list file.')
            listFilename = __config__.downloadListDirectory + os.sep + 'list.txt'
            if op == '4' and len(args) > 0:
                testListFilename = __config__.downloadListDirectory + os.sep + args[0]
                if os.path.exists(testListFilename) :
                    listFilename = testListFilename
            result = PixivListItem.parseList(listFilename, __config__.rootDirectory)
            printAndLog('info','List file used: ' + listFilename)

        print "Found "+str(len(result))+" items."

        ## iterating the list
        for item in result:
            retryCount = 0
            while True:
                try:
                    processMember(mode, item.memberId, item.path)
                    break
                except KeyboardInterrupt:
                    raise
                except:
                    if retryCount > __config__.retry:
                        printAndLog('error','Giving up member_id: '+str(row[0]))
                        break
                    retryCount = retryCount + 1
                    print 'Something wrong, retrying after 2 second (', retryCount, ')'
                    time.sleep(2)
            
            __br__.clear_history()
            print 'done.'
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at processList():',sys.exc_info()
        print 'Failed'
        __log__.error('Error at processList(): ' + str(sys.exc_info()))
        raise

def processMember(mode, member_id, userDir='', page=1, endPage=0): #Yavos added dir-argument which will be initialized as '' when not given
    printAndLog('info','Processing Member Id: ' + str(member_id))
    if page != 1:
        printAndLog('info', 'Start Page: ' + str(page))
    if endPage != 0:
        printAndLog('info', 'End Page: ' + str(endPage))
        if __config__.numberOfPage != 0:
            printAndLog('info', 'Number of page setting will be ignored')
        
    __config__.loadConfig()
    try:
        noOfImages = 1
        avatarDownloaded = False
        flag = True

        while flag:
            print 'Page ',page
            setTitle("MemberId: " + str(member_id) + " Page: " + str(page))
            ## Try to get the member page
            while True:
                try:
                    listPage = __br__.open('http://www.pixiv.net/member_illust.php?id='+str(member_id)+'&p='+str(page))
                    artist = PixivArtist(mid=member_id, page=BeautifulSoup(listPage.read()))
                    break
                except PixivModelException as ex:
                    printAndLog('info', 'Member ID (' + str(member_id) + '): ' + str(ex))
                    if ex.errorCode == 1001 or ex.errorCode == 1002:
                        __dbManager__.setIsDeletedFlagForMemberId(int(member_id))
                        printAndLog('info', 'Set IsDeleted for MemberId: ' + str(member_id) + ' not exist.')
                        #__dbManager__.deleteMemberByMemberId(member_id)
                        #printAndLog('info', 'Deleting MemberId: ' + str(member_id) + ' not exist.')
                    return
                except Exception as ue:
                    print ue
                    repeat = range(1,__config__.retryWait)
                    for t in repeat:
                        print t,
                        time.sleep(1)
                    print ''
            PixivHelper.safePrint('Member Name  : ' + artist.artistName)
            print 'Member Avatar:', artist.artistAvatar
            print 'Member Token :', artist.artistToken

            if artist.artistAvatar.find('no_profile') == -1 and avatarDownloaded == False and __config__.downloadAvatar :
                ## Download avatar as folder.jpg
                filenameFormat = __config__.filenameFormat
                if userDir == '':
                    targetDir = __config__.rootDirectory
                else:
                    targetDir = userDir
                #printAndLog('info','targetDir: ' + targetDir)
                filenameFormat = filenameFormat.split(os.sep)[0]
                #printAndLog('info','filenameFormat: ' + filenameFormat)
                image = PixivImage(parent=artist)
                filename = PixivHelper.makeFilename(filenameFormat, image, tagsSeparator=__config__.tagsSeparator, tagsLimit=__config__.tagsLimit)
                #printAndLog('info','makeFilename: ' + filename)
                filename = PixivHelper.sanitizeFilename(filename + os.sep + 'folder.jpg', targetDir)
                #printAndLog('info','sanitizeFilename: ' + filename)
                
                result = downloadImage(artist.artistAvatar, filename, listPage.geturl(), __config__.overwrite, __config__.retry)
                avatarDownloaded = True
            
            __dbManager__.updateMemberName(member_id, artist.artistName)

            updatedLimitCount = 0
            for image_id in artist.imageList:
                print '#'+ str(noOfImages)
                if mode == PixivConstant.PIXIVUTIL_MODE_UPDATE_ONLY:
                    r = __dbManager__.selectImageByMemberIdAndImageId(member_id, image_id)
                    if r != None and not(__config__.alwaysCheckFileSize):
                        print 'Already downloaded:', image_id
                        updatedLimitCount = updatedLimitCount + 1
                        if updatedLimitCount > __config__.checkUpdatedLimit and __config__.checkUpdatedLimit != 0 :
                            print 'Skipping member:', member_id
                            __dbManager__.updateLastDownloadedImage(member_id, image_id)

                            del listPage
                            __br__.clear_history()
                            return
                        gc.collect()
                        continue

                retryCount = 0
                while True :
                    try:
                        processImage(mode, artist, image_id, userDir) #Yavos added dir-argument to pass
                        __dbManager__.insertImage(member_id, image_id)
                        break
                    except KeyboardInterrupt:
                        raise
                    except Exception as ex:
                        if retryCount > __config__.retry:
                            printAndLog('error', "Giving up image_id: "+str(image_id)) 
                            return
                        retryCount = retryCount + 1
                        print "Stuff happened, trying again after 2 second (", retryCount,")"
                        print ex
                        time.sleep(2)

                noOfImages = noOfImages + 1
            
            if endPage != 0 and page >= endPage:
                print "Page limit reached"
                flag = False
            else:
                if npisvalid == True: #Yavos: overwriting config-data
                    if page > np and np != 0:
                        flag = False
                elif page > __config__.numberOfPage and __config__.numberOfPage != 0 :
                    flag = False

            if artist.isLastPage:
                print "Last Page"
                flag = False
                            
            page = page + 1
            
            del artist
            del listPage
            __br__.clear_history()
            gc.collect()
            
        __dbManager__.updateLastDownloadedImage(member_id, image_id)
        print 'Done.\n'
        __log__.info('Member_id: ' + str(member_id) + ' complete, last image_id: ' + str(image_id))
    except KeyboardInterrupt:
        raise
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        printAndLog('error', 'Error at processMember(): ' + str(sys.exc_info()))
        try: 
            if listPage != None :
                dumpFilename = 'Error page for member ' + str(member_id) + '.html'
                dumpHtml(dumpFilename, listPage.get_data())
                printAndLog('error', "Dumping html to: " + dumpFilename)
        except:
            printAndLog('error', 'Cannot dump page for member_id:'+str(member_id))
        raise

def processImage(mode, artist=None, image_id=None, userDir=''): #Yavos added dir-argument which will be initialized as '' when not given
    try:
        mediumPage = None
        viewPage = None
        image = None
            
        filename = 'N/A'
        print 'Processing Image Id:', image_id
        ## check if already downloaded. images won't be downloaded twice - needed in processImage to catch any download
        r = __dbManager__.selectImageByImageId(image_id)
        if r != None and not __config__.alwaysCheckFileSize:
            if mode == PixivConstant.PIXIVUTIL_MODE_UPDATE_ONLY:
                print 'Already downloaded:', image_id
                gc.collect()
                return

        retryCount = 0
        while 1:
            mediumPage = None
            try :
                mediumPage = __br__.open('http://www.pixiv.net/member_illust.php?mode=medium&illust_id='+str(image_id))
                parseMediumPage = BeautifulSoup(mediumPage.read())
                image = PixivImage(iid=image_id, page=parseMediumPage, parent=artist)
                setTitle('MemberId: ' + str(image.artist.artistId) + ' ImageId: ' + str(image.imageId))
                parseMediumPage.decompose()
                del parseMediumPage
                break
            except PixivModelException as ex:
                printAndLog('info', 'Image ID (' + str(image_id) +'): ' + str(ex))
                return
            except urllib2.URLError as ue:
                print ue
                repeat = range(1,__config__.retryWait)
                for t in repeat:
                    print t,
                    time.sleep(1)
                print ''
                ++retryCount
                if retryCount > __config__.retry:
                    printAndLog('error', 'Giving up image_id (medium): ' + str(image_id))
                    if mediumPage != None:
                        dumpFilename = 'Error medium page for image ' + str(image_id) + '.html'
                        dumpHtml(dumpFilename , mediumPage.get_data())
                        printAndLog('error', 'Dumping html to: ' + dumpFilename);
                    return
        
        downloadImageFlag = True
        if __config__.useBlacklistTags:
            for item in __blacklistTags:
                if item in image.imageTags:
                    printAndLog('info', 'Skipping image_id: ' + str(image_id) + ' because contains blacklisted tags: ' + item);
                    downloadImageFlag = False
                    result = 0
                    break
                
        if downloadImageFlag:

            PixivHelper.safePrint("Title: " + image.imageTitle)
            PixivHelper.safePrint("Tags : " + ', '.join(image.imageTags))
            print "Mode :", image.imageMode
            
            if __config__.useSuppressTags:
                for item in __suppressTags:
                    if item in image.imageTags:
                        image.imageTags.remove(item)
            
            errorCount = 0
            while True:
                try :
                    bigUrl = 'http://www.pixiv.net/member_illust.php?mode='+image.imageMode+'&illust_id='+str(image_id)
                    viewPage = __br__.follow_link(url_regex='mode='+image.imageMode+'&illust_id='+str(image_id))
                    parseBigImage = BeautifulSoup(viewPage.read())
                    image.ParseImages(page=parseBigImage)
                    parseBigImage.decompose()
                    del parseBigImage
                    break
                except PixivModelException as ex:
                    printAndLog('info', 'Image ID (' + str(image_id) +'): ' + str(ex))
                    return
                except urllib2.URLError as ue:
                    if errorCount > __config__.retry:
                        printAndLog('error', 'Giving up image_id: '+str(image_id))
                        return
                    errorCount = errorCount + 1
                    print ue
                    repeat = range(1,__config__.retryWait)
                    for t in repeat:
                        print t,
                        time.sleep(1)
                    print ''

            result = 0
            skipOne = False
            for img in image.imageUrls:
                if skipOne:
                    skipOne = False
                    continue
                print 'Image URL :', img
                url = os.path.basename(img)
                splittedUrl = url.split('.')
                if splittedUrl[0].startswith(str(image_id)):
                    imageExtension = splittedUrl[1]
                    imageExtension = imageExtension.split('?')[0]

                    #Yavos: filename will be added here if given in list
                    filenameFormat = __config__.filenameFormat
                    if userDir == '': #Yavos: use config-options
                        targetDir = __config__.rootDirectory
                    else: #Yavos: use filename from list
                        targetDir = userDir

                    filename = PixivHelper.makeFilename(filenameFormat, image, tagsSeparator=__config__.tagsSeparator, tagsLimit=__config__.tagsLimit)
                    if image.imageMode == 'manga':
                        filename = filename.replace(str(image_id), str(splittedUrl[0]))
                    filename = filename + '.' + imageExtension
                    filename = PixivHelper.sanitizeFilename(filename, targetDir)
                    
                    if image.imageMode == 'manga' and __config__.createMangaDir :
                        mangaPage = __re_manga_page.findall(filename)
                        splittedFilename = filename.split(mangaPage[0][0],1)
                        splittedMangaPage = mangaPage[0][0].split("_p",1)
                        filename = splittedFilename[0] + splittedMangaPage[0] + os.sep + "_p" + splittedMangaPage[1] + splittedFilename[1]

                    PixivHelper.safePrint('Filename  : ' + filename)
                    result = -1
       
                    if mode == PixivConstant.PIXIVUTIL_MODE_OVERWRITE:
                        result = downloadImage(img, filename, viewPage.geturl(), True, __config__.retry)
                    else:
                        result = downloadImage(img, filename, viewPage.geturl(), False, __config__.retry)
                    print ''
                    
                if result == -1 and image.imageMode == 'manga' and img.find('_big') > -1:
                    print 'No big manga image available, try the small one'
                elif result == 0 and image.imageMode == 'manga' and img.find('_big') > -1:
                    skipOne = True
                elif result == -1:
                    printAndLog('error', 'Image url not found: '+str(image.imageId))
                      
        ## Only save to db if all images is downloaded completely
        if result == 0 :
            try:
                __dbManager__.insertImage(image.artist.artistId, image.imageId)
            except:
                pass
            __dbManager__.updateImage(image.imageId, image.imageTitle, filename)

        if mediumPage != None:
            del mediumPage
        if viewPage != None:
            del viewPage
        if image != None:
            del image
        gc.collect()
        ##clearall()
        print '\n'
    except KeyboardInterrupt:
        raise
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        printAndLog('error', 'Error at processImage(): ' + str(sys.exc_info()))
        try:
            if mediumPage != None:
                dumpFilename = 'Error Medium Page for image ' + str(image_id) + '.html'
                dumpHtml(dumpFilename , mediumPage.get_data())
                printAndLog('error', 'Dumping html to: ' + dumpFilename);
            if parseBigImage != None:
                dumpFilename = 'Error Big Page for image ' + str(image_id) + '.html'
                dumpHtml(dumpFilename , parseBigImage.get_data())
                printAndLog('error', 'Dumping html to: ' + dumpFilename);
        except:
            printAndLog('error', 'Cannot dump page for image_id: '+str(image_id))
        raise            

def processTags(mode, tags, page=1, endPage=0, wildCard=True, titleCaption=False, startDate=None, endDate=None, useTagsAsDir=False, member_id=None, bookmarkCount=None):
    try:
        decodedTags = tags
        if useTagsAsDir:
            print "Save to each directory using query tags."
            if tags.startswith("%"):
                tags = tags.encode(sys.stdout.encoding)
                decodedTags = urllib.unquote(tags).decode('utf8')
                PixivHelper.safePrint( tags + '==>' + decodedTags)
            __config__.rootDirectory += os.sep + PixivHelper.sanitizeFilename(decodedTags)
                
        if not tags.startswith("%") :
            try:
                ## Encode the tags
                tags = tags.encode('utf-8')
                tags = urllib.quote_plus(tags)#.decode(sys.stdout.encoding).encode("utf8"))
            except UnicodeDecodeError as ex:
                print "Cannot decode the tags, you can use URL Encoder (http://meyerweb.com/eric/tools/dencoder/) and paste the encoded tag."
        i = page
        images = 1

        dateParam = ""
        if startDate != None:
            dateParam = dateParam + "&scd=" + startDate
        if endDate != None:
            dateParam = dateParam + "&ecd=" + endDate

        printAndLog('info', 'Searching for: ('+ decodedTags + ") " + tags + dateParam)
        
        while True:
            if not member_id == None:
                url = 'http://www.pixiv.net/member_illust.php?id=' + str(member_id) + '&tag=' + tags + '&p='+str(i)
            else :
                if titleCaption:
                    url = 'http://www.pixiv.net/search.php?s_mode=s_tc&p='+str(i)+'&word='+tags + dateParam
                else:
                    if wildCard:
                        url = 'http://www.pixiv.net/search.php?s_mode=s_tag&p='+str(i)+'&word='+tags + dateParam
                        print "Using Wildcard (search.php)"
                    else:
                        url = 'http://www.pixiv.net/tags.php?tag='+tags+'&p='+str(i) + dateParam
                    
            printAndLog('info', 'Looping... for '+ url)
            searchPage = __br__.open(url)

            parseSearchPage = BeautifulSoup(searchPage.read())
            t = PixivTags()
            l = list()
            if not member_id == None:
                l = t.parseMemberTags(parseSearchPage)
            else :
                l = t.parseTags(parseSearchPage)

            if len(l) == 0 :
                print 'No more images'
                break
            else:
                #for image_id in l:
                for item in t.itemList:
                    print 'Image #' + str(images)
                    print 'Image Id:', str(item.imageId)
                    print 'Bookmark Count:', str(item.bookmarkCount)
                    if bookmarkCount != None and bookmarkCount > item.bookmarkCount:
                        printAndLog('info', 'Skipping imageId='+str(item.imageId)+' because less than bookmark count limit ('+ str(bookmarkCount) + ' > ' + str(item.bookmarkCount) + ')')
                        continue
                    while True:
                        try:
                            processImage(mode, None, item.imageId)
                            break;
                        except httplib.BadStatusLine:
                            print "Stuff happened, trying again after 2 second..."
                            time.sleep(2)
                        
                    images = images + 1

            __br__.clear_history()

            i = i + 1

            parseSearchPage.decompose()
            del parseSearchPage
            del searchPage

            if endPage != 0 and endPage < i:
                print 'End Page reached.'
                break
            if t.isLastPage:
                print 'Last page'
                break
        print 'done'
        __config__.loadConfig()
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at processTags():',sys.exc_info()
        __log__.error('Error at processTags(): ' + str(sys.exc_info()))
        raise

def processTagsList(mode, filename, page=1, endPage=0):
    try:
        print "Reading:",filename
        l = PixivTags.parseTagsList(filename)
        for tag in l:
            processTags(mode, tag, page=page, endPage=endPage, useTagsAsDir=__config__.useTagsAsDir)
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at processTagsList():',sys.exc_info()
        __log__.error('Error at processTagsList(): ' + str(sys.exc_info()))
        raise

def processImageBookmark(mode, hide='n', member_id=0):
    try:
        print "Importing image bookmarks..."
        #totalList = list()
        i = 1
        while True:
            print "Importing page", str(i)
            url = 'http://www.pixiv.net/bookmark.php?p='+str(i)
            if member_id > 0:
                url = url + "&id=" + str(member_id)
            if member_id == 0 and hide == 'y':
                url = url + "&rest=hide"
            page = __br__.open(url)
            parsePage = BeautifulSoup(page.read())
            l = PixivBookmark.parseImageBookmark(parsePage)
            if len(l) == 0:
                break

            for item in l:
                processImage(mode, artist=None, image_id=item)
        
            i = i + 1

            parsePage.decompose()
            del parsePage

            if npisvalid == True: #Yavos: overwrite config-data
                if i > np and np != 0:
                    break
            elif i > __config__.numberOfPage and __config__.numberOfPage != 0 :
                break

        print "Done.\n"
    except KeyboardInterrupt:
        raise
    except :
        print 'Error at processImageBookmark():',sys.exc_info()
        __log__.error('Error at processImageBookmark(): ' + str(sys.exc_info()))
        raise
    
def getBookmarks(hide):
    totalList = list()
    i = 1
    while True:
        print 'Exporting page', str(i)
        url = 'http://www.pixiv.net/bookmark.php?type=user&p='+str(i)
        if hide:
            url = url + "&rest=hide"
        page = __br__.open(url)
        parsePage = BeautifulSoup(page.read())
        l = PixivBookmark.parseBookmark(parsePage)
        if len(l) == 0:
            break
        totalList.extend(l)
        i = i + 1
    return totalList

def processBookmark(mode, hide='n'):
    try:
        totalList = list()
        if hide != 'o':
            print "Importing Bookmarks..."
            totalList.extend(getBookmarks(False))
        if hide != 'n':
            print "Importing Private Bookmarks..."
            totalList.extend(getBookmarks(True))
        print "Result: ", str(len(totalList)), "items."        
        for item in totalList:
            processMember(mode, item.memberId, item.path)
    except KeyboardInterrupt:
        raise
    except :
        print 'Error at processBookmark():',sys.exc_info()
        __log__.error('Error at processBookmark(): ' + str(sys.exc_info()))
        raise

def exportBookmark(filename, hide='n'):
    try:
        totalList = list()
        if hide != 'o':
            print "Importing Bookmarks..."
            totalList.extend(getBookmarks(False))
        if hide != 'n':
            print "Importing Private Bookmarks..."
            totalList.extend(getBookmarks(True))
        print "Result: ", str(len(totalList)), "items."
        PixivBookmark.exportList(totalList, filename)
    except KeyboardInterrupt:
        raise
    except :
        print 'Error at exportBookmark():',sys.exc_info()
        __log__.error('Error at exportBookmark(): ' + str(sys.exc_info()))
        raise

def processNewIllustFromBookmark(mode, pageNum=1, endPageNum=0):
    try:
        print "Processing New Illust from bookmark"
        i = pageNum
        imageCount = 1
        while True:
            print "Page #"+str(i)
            url = 'http://www.pixiv.net/bookmark_new_illust.php?p='+str(i)
            page = __br__.open(url)
            parsedPage = BeautifulSoup(page.read())
            pb = PixivNewIllustBookmark(parsedPage)
            if not pb.haveImages:
                print "No images!"
                break

            for image_id in pb.imageList:
                print "Image #"+str(imageCount)
                processImage(mode, artist=None, image_id=int(image_id))
                imageCount = imageCount + 1
            i = i + 1

            parsedPage.decompose()
            del parsedPage

            if ( endPageNum != 0 and i > endPageNum ) or i >= 100 or pb.isLastPage:
                print "Limit or last page reached."
                break
            
        print "Done."
    except KeyboardInterrupt:
        raise
    except:
        print 'Error at processNewIllustFromBookmark():',sys.exc_info()
        __log__.error('Error at processNewIllustFromBookmark(): ' + str(sys.exc_info()))
        raise
        
def header():
    print 'PixivDownloader2 version', PixivConstant.PIXIVUTIL_VERSION
    print PixivConstant.PIXIVUTIL_LINK

def getStartAndEndNumber(startOnly=False):
    pageNum = raw_input('Start Page (default=1): ') or 1
    try:
        pageNum = int(pageNum)
    except:
        print "Invalid page number:", pageNum
        raise

    endPageNum = 0
    if npisvalid:
        endPageNum = np
    else:
        endPageNum = __config__.numberOfPage
    if not startOnly:
        endPageNum = raw_input('End Page (default='+ str(endPageNum) +', 0 for no limit): ') or endPageNum
        try:
            endPageNum = int(endPageNum)
            if pageNum > endPageNum and endPageNum != 0:
                print "pageNum is bigger than endPageNum, assuming as page count."
                endPageNum = pageNum + endPageNum
        except:
            print "Invalid end page number:", endPageNum
            raise

    return (pageNum, endPageNum)

def getStartAndEndNumberFromArgs(args, offset=0, startOnly=False):
    pageNum = 1
    if len(args) > 0+offset:
        try:
            pageNum = int(args[0+offset])
            print "Start Page =", str(pageNum)
        except:
            print "Invalid page number:", args[0+offset]
            raise
        
    endPageNum = 0
    if npisvalid:
        endPageNum = np
    else:
        endPageNum = __config__.numberOfPage
    if not startOnly:
        if len(args) > 1+offset:
            try:
                endPageNum = int(args[1+offset])
                if pageNum > endPageNum and endPageNum != 0:
                    print "pageNum is bigger than endPageNum, assuming as page count."
                    endPageNum = pageNum + endPageNum
                print "End Page =", str(endPageNum)
            except:
                print "Invalid end page number:", args[1+offset]
                raise
    return (pageNum, endPageNum)

def checkDateTime(inputDate):
    split = inputDate.split("-")
    return datetime.date(int(split[0]),int(split[1]),int(split[2])).isoformat()
    
def getStartAndEndDate():
    while(True):
        try:
            startDate = raw_input('Start Date [YYYY-MM-DD]: ') or None
            if startDate != None:
                startDate = checkDateTime(startDate)
            break
        except Exception as e:
            print str(e)
            
    while(True):
        try:
            endDate = raw_input('End Date [YYYY-MM-DD]: ') or None
            if endDate != None:
                endDate = checkDateTime(endDate)
            break
        except Exception as e:
                print str(e)
    
    return (startDate, endDate)

def menu():
    setTitle()
    header()
    print '1. Download by member_id'
    print '2. Download by image_id'
    print '3. Download by tags'
    print '4. Download from list'
    print '5. Download from online user bookmark'
    print '6. Download from online image bookmark'
    print '7. Download from tags list'
    print '8. Download new illust from bookmark'
    print '9. Download by Title/Caption'
    print '10. Download by Tag and Member Id'
    print '------------------------'
    print 'd. Manage database'
    print 'e. Export online bookmark'
    print 'x. Exit'
    
    return raw_input('Input: ').strip()

def menuDownloadByMemberId(mode, opisvalid, args):
    __log__.info('Member id mode.')
    page = 1
    endPage = 0
    if opisvalid and len(args) > 0:
        for member_id in args:
            try:
                testID = int(member_id)
            except:
                print "ID", member_id, "is not valid"
                continue
            processMember(mode, int(member_id))
    else:
        member_id = raw_input('Member id: ')
        (page, endPage) = getStartAndEndNumber()
        processMember(mode, member_id.strip(), page=page, endPage=endPage)

def menuDownloadByImageId(mode, opisvalid, args):
    __log__.info('Image id mode.')
    if opisvalid and len(args) > 0:
        for image_id in args:
            try:
                testID = int(image_id)
            except:
                print "ID", image_id, "is not valid"
                continue
            processImage(mode, None, int(image_id))
    else:
        image_id = raw_input('Image id: ')
        processImage(mode, None, int(image_id))

def menuDownloadByTags(mode, opisvalid, args):
    __log__.info('tags mode.')
    page = 1
    endPage = 0
    startDate = None
    endDate = None
    bookmarkCount = None
    if opisvalid and len(args) > 0:
        wildcard = args[0]
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        tags = " ".join(args[1:])
    else:
        tags = PixivHelper.uni_input('Tags: ')
        bookmarkCount = raw_input('Bookmark Count: ') or None
        wildcard = raw_input('Use Wildcard[y/n]: ') or 'n'
        if wildcard.lower() == 'y':
            wildcard = True
        else:
            wildcard = False
        (page, endPage) = getStartAndEndNumber()
        (startDate, endDate) = getStartAndEndDate()
    if bookmarkCount != None:
        bookmarkCount = int(bookmarkCount)
    processTags(mode, tags.strip(), page, endPage, wildcard, startDate=startDate, endDate=endDate, useTagsAsDir=__config__.useTagsAsDir,bookmarkCount=bookmarkCount)

def menuDownloadByTitleCaption(mode, opisvalid, args):
    __log__.info('Title/Caption mode.')
    page = 1
    endPage = 0
    startDate = None
    endDate = None
    if opisvalid and len(args) > 0:
        tags = " ".join(args)
    else:
        tags = PixivHelper.uni_input('Title/Caption: ')
        (page, endPage) = getStartAndEndNumber()
        (startDate, endDate) = getStartAndEndDate()
        
    processTags(mode, tags.strip(), page, endPage, wildCard=False, titleCaption=True, startDate=startDate, endDate=endDate, useTagsAsDir=__config__.useTagsAsDir)

def menuDownloadByTagAndMemberId(mode, opisvalid, args):
    __log__.info('Tag and MemberId mode.')

    member_id = raw_input('Member Id: ')
    tags      = PixivHelper.uni_input('Tag      : ')
    
    processTags(mode, tags.strip(), member_id=int(member_id), useTagsAsDir=__config__.useTagsAsDir)

    
def menuDownloadFromList(mode, opisvalid, args):
    __log__.info('Batch mode.')
    processList(mode)

def menuDownloadFromOnlineUserBookmark(mode, opisvalid, args):
    __log__.info('User Bookmark mode.')
    hide = 'n'
    if opisvalid :
        if len(args) > 0:
            arg = args[0].lower()
            if arg == 'y' or arg =='n' or arg == 'o':
                hide = arg
            else:
                print "Invalid args: ", args
    else :
        arg = raw_input("Include Private bookmarks [y/n/o]: ") or 'n'
        arg = arg.lower()
        if arg == 'y' or arg =='n' or arg == 'o':
            hide = arg
        else:
            print "Invalid args: ", arg
    processBookmark(mode, hide)

def menuDownloadFromOnlineImageBookmark(mode, opisvalid, args):
    __log__.info('Image Bookmark mode.')
    if opisvalid and len(args) > 0 :
        arg = args.pop(0)
        arg = arg.lower()
        arg = args[0].lower()
        if arg == 'y' or arg =='n':
            hide = arg
        else:
            print "Invalid args: ", args
        if len(args) == 0:
            args.append(0)
        for arg in args:
            try:
                memberId = int(arg)
            except:
                print "Invalid Member Id:", arg
    else:
        memberIdStr = raw_input("Member Id (0 for your bookmark): ") or 0
        memberId = int(memberIdStr)
        hide = False
        if memberId == 0 :
            arg = raw_input("Only Private bookmarks [y/n]: ") or 'n'
            arg = arg.lower()
            if arg == 'y' or arg =='n':
                hide = arg
            else:
                print "Invalid args: ", arg
                
    processImageBookmark(mode, hide, memberId)

def menuDownloadFromTagsList(mode, opisvalid, args):
    __log__.info('Taglist mode.')
    page = 1
    endPage = 0
    if opisvalid and len(args) > 0 :
        filename = args[0]
        (page, endPage) = getStartAndEndNumberFromArgs(args, offset=1)
    else:
        filename = raw_input("Tags list filename [tags.txt]: ") or './tags.txt'
        (page, endPage) = getStartAndEndNumber()

    processTagsList(mode, filename, page, endPage)

def menuDownloadNewIllustFromBookmark(mode, opisvalid, args):
    __log__.info('New Illust from Bookmark mode.')

    if opisvalid:
        (pageNum, endPageNum) = getStartAndEndNumberFromArgs(args, offset=0)
    else:
        (pageNum, endPageNum) = getStartAndEndNumber()
    
    processNewIllustFromBookmark(mode, pageNum, endPageNum)

def menuExportOnlineBookmark(mode, opisvalid, args):
    __log__.info('Export Bookmark mode.')
    filename = raw_input("Filename: ")
    arg = raw_input("Include Private bookmarks [y/n/o]: ") or 'n'
    arg = arg.lower()
    if arg == 'y' or arg =='n' or arg == 'o':
        hide = arg
    else:
        print "Invalid args: ", arg
    exportBookmark(filename, hide)
    
def setTitle(title=''):
    setTitle = 'PixivDownloader ' + str(PixivConstant.PIXIVUTIL_VERSION) + ' ' + title
    PixivHelper.setConsoleTitle(setTitle)
    
### Main thread ###
def main():
    setTitle()
    header()
    
    ## Option Parser
    global npisvalid
    global opisvalid
    global np
    global iv
    global op
    global args
    
    parser = OptionParser()
    parser.add_option('-s', '--startaction', dest='startaction',
                      help='Action you want to load your program with:              ' + 
                           '1 - Download by member_id                               ' +
                           '2 - Download by image_id                                ' +
                           '3 - Download by tags                                    ' +
                           '4 - Download from list                                  ' +
                           '5 - Download from user bookmark                          ' +
                           '6 - Download from image bookmark                         ' +
                           '7 - Download from tags list                              ' +
                           '8 - Download new illust from bookmark                    ' +
                           '9 - Download by Title/Caption                            ' +
                           '10 - Download by Tag and Member Id                       ' +
                           'e - Export online bookmark                               ' +
                           'd - Manage database' )
    parser.add_option('-x', '--exitwhendone', dest='exitwhendone',
                      help='Exit programm when done. (only useful when not using DB-Manager)', action='store_true', default=False)
    parser.add_option('-i', '--irfanview', dest='iv',
                      help='start IrfanView after downloading images using downloaded_on_%date%.txt', action='store_true', default=False)
    parser.add_option('-n', '--numberofpages', dest='numberofpages',
                      help='temporarily overwrites numberOfPage set in config.ini')

    (options, args) = parser.parse_args()

    op = options.startaction
    if op in ('1', '2', '3', '4', '5', '6', '7', '8', '9', 'd', 'e'):
        opisvalid = True
    elif op == None:
        opisvalid = False
    else:
        opisvalid = False
        parser.error('%s is not valid operation' % op) #Yavos: use print option instead when program should be running even with this error

    ewd = options.exitwhendone
    try:
        if options.numberofpages != None:
            np = int(options.numberofpages)
            npisvalid = True
        else:
            npisvalid = False
    except:
        npisvalid = False
        parser.error('Value %s used for numberOfPage is not an integer.' % options.numberofpages) #Yavos: use print option instead when program should be running even with this error
    ### end new lines by Yavos ###
    
    __log__.info('Starting...')
    try:
        __config__.loadConfig()
    except:
        print 'Failed to read configuration.'
        __log__.error('Failed to read configuration.')

    configBrowser()
    selection = None
    global dfilename
    
    #Yavos: adding File for downloadlist
    now = datetime.date.today()
    dfilename = __config__.downloadListDirectory + os.sep + 'Downloaded_on_' + now.strftime('%Y-%m-%d') + '.txt'
    if not re.match(r'[a-zA-Z]:', dfilename):
        dfilename = sys.path[0] + os.sep + dfilename
        #dfilename = sys.path[0].rsplit('\\',1)[0] + '\\' + dfilename #Yavos: only useful for myself ;P
    dfilename = dfilename.replace('\\\\', '\\')
    dfilename = dfilename.replace('\\', os.sep)
    directory = os.path.dirname(dfilename)
    if not os.path.exists(directory):
        os.makedirs(directory)
        __log__.info('Creating directory: '+directory)
        
    #Yavos: adding IrfanView-Handling
    if __config__.startIrfanSlide == True or __config__.startIrfanView == True:
        iv = True
        IrfanSlide = __config__.startIrfanSlide
        IrfanView = __config__.startIrfanView
    elif options.iv != None:
        iv = options.iv
        IrfanView = True
        IrfanSlide = False

    try:
        __dbManager__.createDatabase()

        if __config__.useList :
            listTxt = PixivListItem.parseList(__config__.downloadListDirectory+ os.sep + 'list.txt')
            __dbManager__.importList(listTxt)
            print "Updated " + str(len(listTxt)) + " items."

        if __config__.overwrite :
            msg = 'Overwrite enabled.'
            print msg
            __log__.info(msg)

        if __config__.dayLastUpdated != 0  and __config__.processFromDb:
            msg = 'Only process member where day last updated >= ' + str(__config__.dayLastUpdated)
            print msg
            __log__.info(msg)

        if __config__.useBlacklistTags:
            global __blacklistTags
            __blacklistTags = PixivTags.parseTagsList("blacklist_tags.txt")
            printAndLog('info', 'Using Blacklist Tags: ' + str(len(__blacklistTags)) + " items.")

        if __config__.useSuppressTags:
            global __suppressTags
            __suppressTags = PixivTags.parseTagsList("suppress_tags.txt")
            printAndLog('info', 'Using Suppress Tags: ' + str(len(__suppressTags)) + " items.")

        username = __config__.username
        if username == '':
            username = raw_input('Username ? ')
        else :
            msg = 'Using Username: ' + username
            print msg
            __log__.info(msg)

        password = __config__.password
        if password == '':
            password = getpass.getpass('Password ? ')

        if npisvalid == True and np != 0: #Yavos: overwrite config-data
            msg = 'Limit up to: ' +  str(np) + ' page(s). (set via commandline)'
            print msg
            __log__.info(msg)
        elif __config__.numberOfPage != 0:
            msg = 'Limit up to: ' +  str(__config__.numberOfPage) + ' page(s).'
            print msg
            __log__.info(msg)

        ## Log in
        result = False
        if len(__config__.cookie) > 0:
            result = pixivLoginCookie()

        if not result:
            if __config__.useSSL:
                result = pixivLoginSSL(username,password)
            else:
                result = pixivLogin(username,password)                  

        if result:            
            if __config__.overwrite :
                mode = PixivConstant.PIXIVUTIL_MODE_OVERWRITE
            else :
                mode = PixivConstant.PIXIVUTIL_MODE_UPDATE_ONLY

            while True:
                try:
                    if opisvalid: #Yavos (next 3 lines): if commandline then use it ;P
                        selection = op
                    else:
                        selection = menu()
                        
                    if selection == '1':
                        menuDownloadByMemberId(mode, opisvalid, args)
                    elif selection == '2':
                        menuDownloadByImageId(mode, opisvalid, args)
                    elif selection == '3':
                        menuDownloadByTags(mode, opisvalid, args)
                    elif selection == '4':
                        menuDownloadFromList(mode, opisvalid, args)

                    elif selection == '5':
                        menuDownloadFromOnlineUserBookmark(mode, opisvalid, args)
                    elif selection == '6':
                        menuDownloadFromOnlineImageBookmark(mode, opisvalid, args)
                    elif selection == '7':
                        menuDownloadFromTagsList(mode, opisvalid, args)
                    elif selection == '8':
                        menuDownloadNewIllustFromBookmark(mode, opisvalid, args)
                    elif selection == '9':
                        menuDownloadByTitleCaption(mode, opisvalid, args)
                    elif selection == '10':
                        menuDownloadByTagAndMemberId(mode, opisvalid, args)
                    elif selection == 'e':
                        menuExportOnlineBookmark(mode, opisvalid, args)
                    elif selection == 'd':
                        __dbManager__.main()
                    elif selection == '-all':
                        if npisvalid == False:
                            npisvalid = True
                            np = 0
                            print 'download all mode activated'
                        else:
                            npisvalid = False
                            print 'download mode reset to', __config__.numberOfPage, 'pages'
                    elif selection == 'x':
                        break
                    
                    if ewd == True: #Yavos: added lines for "exit when done"
                        break
                    opisvalid = False #Yavos: needed to prevent endless loop
                except KeyboardInterrupt:
                    PixivHelper.clearScreen()
                    print "Restarting..."
            if iv == True: #Yavos: adding IrfanView-handling
                PixivHelper.startIrfanView(dfilename, __config__.IrfanViewPath)
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        __log__.error('Unknown Error: '+ str(exc_value))
    finally:
        __dbManager__.close()
        if ewd == False: ### Yavos: prevent input on exitwhendone
            if selection == None or selection != 'x' :
                raw_input('press enter to exit.')
        __log__.info('EXIT')
        __log__.info('#####################################################')

if __name__ == '__main__':
    main()

    
