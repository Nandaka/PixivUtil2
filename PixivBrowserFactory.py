# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302, W0603
from __future__ import print_function

from mechanize import Browser
import mechanize
from BeautifulSoup import BeautifulSoup
import cookielib
import socket
import socks
import urlparse
import urllib
import urllib2
import httplib
import time
import sys
import json
import demjson
import re

import PixivHelper
from PixivException import PixivException
import PixivModelWhiteCube
import PixivModel
from PixivModelFanbox import Fanbox, FanboxArtist

defaultCookieJar = None
defaultConfig = None
_browser = None


# pylint: disable=E1101
class PixivBrowser(Browser):
    _config = None
    _isWhitecube = False
    _whitecubeToken = ""
    _cache = dict()
    _myId = 0

    def put_to_cache(self, key, item, expiration=3600):
        expiry = time.time() + expiration
        self._cache[key] = (item, expiry)

    def get_from_cache(self, key):
        if key in self._cache.keys():
            (item, expiry) = self._cache[key]
            if expiry - time.time() > 0:
                return item
            else:
                del item
                self._cache.pop(key)
        return None

    def __init__(self, config, cookie_jar):
        # fix #218
        try:
            Browser.__init__(self, factory=mechanize.RobustFactory())
        except BaseException:
            PixivHelper.GetLogger().info("Using default factory (mechanize 3.x ?)")
            Browser.__init__(self)

        self._configureBrowser(config)
        self._configureCookie(cookie_jar)

    def clear_history(self):
        super(PixivBrowser, self).clear_history()
        return

    def back(self):
        super(PixivBrowser, self).back()
        return

    def _configureBrowser(self, config):
        if config is None:
            PixivHelper.GetLogger().info("No config given")
            return

        global defaultConfig
        if defaultConfig is None:
            defaultConfig = config

        self._config = config
        if config.useProxy:
            if config.proxyAddress.startswith('socks'):
                parseResult = urlparse.urlparse(config.proxyAddress)
                assert parseResult.scheme and parseResult.hostname and parseResult.port
                socksType = socks.PROXY_TYPE_SOCKS5 if parseResult.scheme == 'socks5' else socks.PROXY_TYPE_SOCKS4

                socks.setdefaultproxy(socksType, parseResult.hostname, parseResult.port)
                socks.wrapmodule(urllib)
                socks.wrapmodule(urllib2)
                socks.wrapmodule(httplib)

                PixivHelper.GetLogger().info("Using SOCKS Proxy: %s", config.proxyAddress)
            else:
                self.set_proxies(config.proxy)
                PixivHelper.GetLogger().info("Using Proxy: %s", config.proxyAddress)

        # self.set_handle_equiv(True)
        # self.set_handle_gzip(True)
        self.set_handle_redirect(True)
        self.set_handle_referer(True)
        self.set_handle_robots(False)

        self.set_debug_http(config.debugHttp)
        if config.debugHttp:
            PixivHelper.GetLogger().info('Debug HTTP enabled.')

        # self.visit_response
        self.addheaders = [('User-agent', config.useragent)]

        # force utf-8, fix issue #184
        self.addheaders = [('Accept-Charset', 'utf-8')]

        socket.setdefaulttimeout(config.timeout)

    def _configureCookie(self, cookie_jar):
        if cookie_jar is not None:
            self.set_cookiejar(cookie_jar)

            global defaultCookieJar
            if defaultCookieJar is None:
                defaultCookieJar = cookie_jar

    def addCookie(self, cookie):
        global defaultCookieJar
        if defaultCookieJar is None:
            defaultCookieJar = cookielib.LWPCookieJar()
        defaultCookieJar.set_cookie(cookie)

    def open_with_retry(self, url, data=None,
                        timeout=mechanize._sockettimeout._GLOBAL_DEFAULT_TIMEOUT,
                        retry=0):
        retry_count = 0
        if retry == 0 and self._config is not None:
            retry = self._config.retry

        while True:
            try:
                return self.open(url, data, timeout)
            except Exception as ex:
                if isinstance(ex, urllib2.HTTPError):
                    raise

                if retry_count < retry:
                    for t in range(1, self._config.retryWait):
                        print(t, end=' ')
                        time.sleep(1)
                    print('')
                    retry_count = retry_count + 1
                else:
                    raise PixivException("Failed to get page: " + ex.message, errorCode=PixivException.SERVER_ERROR)

    def getPixivPage(self, url, referer="https://www.pixiv.net", returnParsed=True):
        ''' get page from pixiv and return as parsed BeautifulSoup object or response object.

            throw PixivException as server error
        '''
        url = self.fixUrl(url)
        retry_count = 0
        while True:
            req = urllib2.Request(url)
            req.add_header('Referer', referer)
            try:
                page = self.open(req)
                if returnParsed:
                    parsedPage = BeautifulSoup(page.read())
                    return parsedPage
                else:
                    return page
            except Exception as ex:
                if isinstance(ex, urllib2.HTTPError):
                    if ex.code in [403, 404, 503]:
                        return BeautifulSoup(ex.read())

                if retry_count < self._config.retry:
                    for t in range(1, self._config.retryWait):
                        print(t, end=' ')
                        time.sleep(1)
                    print('')
                    retry_count = retry_count + 1
                else:
                    raise PixivException("Failed to get page: " + ex.message, errorCode=PixivException.SERVER_ERROR)

    def fixUrl(self, url, useHttps=True):
        # url = str(url)
        if not url.startswith("http"):
            if not url.startswith("/"):
                url = "/" + url
            if useHttps:
                return "https://www.pixiv.net" + url
            else:
                return "http://www.pixiv.net" + url
        return url

    def _loadCookie(self, cookie_value):
        """ Load cookie to the Browser instance """
        ck = cookielib.Cookie(version=0, name='PHPSESSID', value=cookie_value, port=None,
                             port_specified=False, domain='pixiv.net', domain_specified=False,
                             domain_initial_dot=False, path='/', path_specified=True,
                             secure=False, expires=None, discard=True, comment=None,
                             comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
        self.addCookie(ck)

    def _getInitConfig(self, page):
        init_config = page.find('input', attrs={'id': 'init-config'})
        js_init_config = json.loads(init_config['value'])
        return js_init_config

    def loginUsingCookie(self, login_cookie=None):
        """  Log in to Pixiv using saved cookie, return True if success """

        if login_cookie is None or len(login_cookie) == 0:
            login_cookie = self._config.cookie

        if len(login_cookie) > 0:
            PixivHelper.print_and_log('info', 'Trying to log in with saved cookie')
            self._loadCookie(login_cookie)
            res = self.open('https://www.pixiv.net/mypage.php')
            resData = res.read()

            parsed = BeautifulSoup(resData)
            self.detectWhiteCube(parsed, res.geturl())

            if "logout.php" in resData:
                PixivHelper.print_and_log('info', 'Login successful.')
                PixivHelper.GetLogger().info('Logged in using cookie')
                self.getMyId(parsed)
                return True
            else:
                PixivHelper.GetLogger().info('Failed to log in using cookie')
                PixivHelper.print_and_log('info', 'Cookie already expired/invalid.')
        return False

    def login(self, username, password):
        try:
            PixivHelper.print_and_log('info', 'Logging in...')
            url = "https://accounts.pixiv.net/login"
            page = self.open(url)

            # get the post key
            parsed = BeautifulSoup(page)
            js_init_config = self._getInitConfig(parsed)

            data = {}
            data['pixiv_id'] = username
            data['password'] = password
            data['captcha'] = ''
            data['g_recaptcha_response'] = ''
            data['return_to'] = 'https://www.pixiv.net'
            data['lang'] = 'en'
            data['post_key'] = js_init_config["pixivAccount.postKey"]
            data['source'] = "accounts"
            data['ref'] = ''

            request = urllib2.Request("https://accounts.pixiv.net/api/login?lang=en", urllib.urlencode(data))
            response = self.open(request)

            return self.processLoginResult(response)
        except BaseException:
            PixivHelper.print_and_log('error', 'Error at login(): {0}'.format(sys.exc_info()))
            raise

    def processLoginResult(self, response):
        PixivHelper.GetLogger().info('Logging in, return url: %s', response.geturl())

        # check the returned json
        js = response.read()
        PixivHelper.GetLogger().info(str(js))
        result = json.loads(js)
        # Fix Issue #181
        if result["body"] is not None and result["body"].has_key("success"):
            for cookie in self._ua_handlers['_cookies'].cookiejar:
                if cookie.name == 'PHPSESSID':
                    PixivHelper.print_and_log('info', 'new cookie value: ' + str(cookie.value))
                    self._config.cookie = cookie.value
                    self._config.writeConfig(path=self._config.configFileLocation)
                    break

            # check whitecube
            page = self.open(result["body"]["success"]["return_to"])
            parsed = BeautifulSoup(page)
            self.detectWhiteCube(parsed, page.geturl())

            self.getMyId(parsed)

            return True
        else:
            if result["body"] is not None and result["body"].has_key("validation_errors"):
                PixivHelper.print_and_log('info', "Server reply: " + str(result["body"]["validation_errors"]))
            else:
                PixivHelper.print_and_log('info', 'Unknown login issue, please use cookie login method.')
            return False

    def getMyId(self, parsed):
        ''' Assume from main page '''
        # pixiv.user.id = "189816";
        temp = re.findall(r"pixiv.user.id = \"(\d+)\";", unicode(parsed))
        if temp is not None:
            self._myId = int(temp[0])
            PixivHelper.print_and_log('info', 'My User Id: {0}.'.format(self._myId))
        else:
            PixivHelper.print_and_log('info', 'Unable to get User Id')

    def detectWhiteCube(self, page, url):
        if page.find("capybara-status-check") == -1:
            print("*******************************************")
            print("* Pixiv AJAX UI mode.                     *")
            print("* Some feature might not working properly *")
            print("*******************************************")

            self._isWhitecube = True

    def parseLoginError(self, res):
        page = BeautifulSoup(res.read())
        r = page.findAll('span', attrs={'class': 'error'})
        return r

    def getImagePage(self, image_id, parent=None, from_bookmark=False,
                     bookmark_count=-1, image_response_count=-1):
        image = None
        response = None
        PixivHelper.GetLogger().debug("Getting image page: %s", image_id)
        if self._isWhitecube:
            pass
##            url = "https://www.pixiv.net/rpc/whitecube/index.php?mode=work_details_modal_whitecube&id={0}&tt={1}".format(image_id, self._whitecubeToken)
##            response = self.open(url).read()
##            self.handleDebugMediumPage(response, image_id)
##            # PixivHelper.GetLogger().debug(response)
##
##            image = PixivModelWhiteCube.PixivImage(image_id,
##                                                   response,
##                                                   parent,
##                                                   from_bookmark,
##                                                   bookmark_count,
##                                                   image_response_count,
##                                                   dateFormat=self._config.dateFormat)
##            # overwrite artist info
##            if from_bookmark:
##                self.getMemberInfoWhitecube(image.originalArtist.artistId, image.originalArtist)
##            else:
##                self.getMemberInfoWhitecube(image.artist.artistId, image.artist)

        else:
            url = "https://www.pixiv.net/member_illust.php?mode=medium&illust_id={0}".format(image_id)
            # response = self.open(url).read()
            response = self.getPixivPage(url, returnParsed=False).read()
            self.handleDebugMediumPage(response, image_id)

            # Issue #355 new ui handler
            image = None
            try:
                if response.find("globalInitData") > 0:
                    PixivHelper.print_and_log('debug', 'New UI Mode')

                    # Issue #420
                    _tzInfo = None
                    if self._config.useLocalTimezone:
                        _tzInfo = PixivHelper.LocalUTCOffsetTimezone()

                    image = PixivModelWhiteCube.PixivImage(image_id,
                                                           response,
                                                           parent,
                                                           from_bookmark,
                                                           bookmark_count,
                                                           image_response_count,
                                                           dateFormat=self._config.dateFormat,
                                                           tzInfo=_tzInfo)

                    if image.imageMode == "ugoira_view":
                        ugoira_meta_url = "https://www.pixiv.net/ajax/illust/{0}/ugoira_meta".format(image_id)
                        meta_response = self.open(ugoira_meta_url).read()
                        image.ParseUgoira(meta_response)
    ##                    PixivHelper.GetLogger().debug("animation.js")
    ##                    PixivHelper.GetLogger().debug(image.ugoira_data)

                    if parent is None:
                        if from_bookmark:
                            self.getMemberInfoWhitecube(image.originalArtist.artistId, image.originalArtist)
                        else:
                            self.getMemberInfoWhitecube(image.artist.artistId, image.artist)

                else:
                    parsed = BeautifulSoup(response)
                    image = PixivModel.PixivImage(image_id,
                                                  parsed,
                                                  parent,
                                                  from_bookmark,
                                                  bookmark_count,
                                                  image_response_count,
                                                  dateFormat=self._config.dateFormat)
                    if image.imageMode == "ugoira_view" or image.imageMode == "bigNew":
                        image.ParseImages(parsed)
                    parsed.decompose()
            except:
                PixivHelper.GetLogger().error("Respose data: \r\n %s", response)
                raise

        return (image, response)

    def handleDebugMediumPage(self, response, imageId):
        if self._config.enableDump:
            if self._config.dumpMediumPage:
                dump_filename = "Medium Page for Image Id {0}.html".format(imageId)
                PixivHelper.dumpHtml(dump_filename, response)
                PixivHelper.print_and_log('info', 'Dumping html to: {0}'.format(dump_filename))
            if self._config.debugHttp:
                PixivHelper.safePrint(u"reply: {0}".format(PixivHelper.toUnicode(response)))

    def getMemberInfoWhitecube(self, member_id, artist, bookmark=False):
        ''' get artist information using Ajax and AppAPI '''
        try:
            url = 'https://app-api.pixiv.net/v1/user/detail?user_id={0}'.format(member_id)
            info = self.get_from_cache(url)
            if info is None:
                PixivHelper.GetLogger().debug("Getting member information: %s", member_id)
                infoStr = self.open(url).read()
                info = json.loads(infoStr)
                self.put_to_cache(url, info)

            artist.ParseInfo(info, False, bookmark=bookmark)

            # will throw HTTPError if user is suspended/not logged in.
            url_ajax = 'https://www.pixiv.net/ajax/user/{0}'.format(member_id)
            info_ajax = self.get_from_cache(url_ajax)
            if info_ajax is None:
                info_ajax_str = self.open(url_ajax).read()
                info_ajax = json.loads(info_ajax_str)
                self.put_to_cache(url_ajax, info_ajax)
            # 2nd pass to get the background
            artist.ParseBackground(info_ajax)

            return artist
        except urllib2.HTTPError, error:
            errorCode = error.getcode()
            errorMessage = error.get_data()
            PixivHelper.GetLogger().error("Error data: \r\n %s", errorMessage)
            payload = demjson.decode(errorMessage)
            # Issue #432
            if payload.has_key("message"):
                msg = payload["message"]
            elif payload.has_key("error") and payload["error"] is not None:
                msgs = list()
                msgs.append(payload["error"]["user_message"])
                msgs.append(payload["error"]["message"])
                msgs.append(payload["error"]["reason"])
                msg = ",".join(msgs)
            if errorCode == 401:
                raise PixivException(msg, errorCode=PixivException.NOT_LOGGED_IN, htmlPage=errorMessage)
            elif errorCode == 403:
                raise PixivException(msg, errorCode=PixivException.USER_ID_SUSPENDED, htmlPage=errorMessage)
            else:
                raise PixivException(msg, errorCode=PixivException.OTHER_MEMBER_ERROR, htmlPage=errorMessage)


##    def getMemberBookmarkWhiteCube(self, member_id, page, limit, tag):
##        response = None
##        PixivHelper.print_and_log('info', 'Getting Bookmark Url for page {0}...'.format(page))
##        # iterate to get next page url
##        start = 1
##        last_member_bookmark_next_url = None
##        while start <= page:
##            if start == 1:
##                url = 'https://www.pixiv.net/rpc/whitecube/index.php?mode=user_collection_unified&id={0}&bookmark_restrict={1}&limit={2}&is_profile_page={3}&is_first_request={4}&max_illust_bookmark_id={5}&max_novel_bookmark_id={6}&tt={7}&tag={8}'
##                url = url.format(member_id, 0, limit, 1, 1, 0, 0, self._whitecubeToken, tag)
##            else:
##                url = last_member_bookmark_next_url
##
##            # PixivHelper.printAndLog('info', 'Member Bookmark Page {0} Url: {1}'.format(start, url))
##            if self._cache.has_key(url):
##                response = self._cache[url]
##            else:
##                response = self.open(url).read()
##                self._cache[url] = response
##
##            payload = json.loads(response)
##            last_member_bookmark_next_url = payload["body"]["next_url"]
##            if last_member_bookmark_next_url is None and start < page:
##                PixivHelper.print_and_log('info', 'No more images for {0} bookmarks'.format(member_id))
##                url = None
##                break
##
##            start = start + 1
##        PixivHelper.print_and_log('info', 'Member Bookmark Page {0} Url: {1}'.format(page, url))
##        return (url, response)

    def getMemberPage(self, member_id, page=1, bookmark=False, tags=None):
        artist = None
        response = None
        if tags is not None:
            tags = PixivHelper.encode_tags(tags)
        else:
            tags = ''

        ## if True:
        limit = 24
        offset = (page - 1) * limit
        need_to_slice = False
        if bookmark:
            # (url, response) = self.getMemberBookmarkWhiteCube(member_id, page, limit, tags)
            # https://www.pixiv.net/ajax/user/1039353/illusts/bookmarks?tag=&offset=0&limit=24&rest=show
            url = 'https://www.pixiv.net/ajax/user/{0}/illusts/bookmarks?tag={1}&offset={2}&limit={3}&rest=show'.format(member_id, tags, offset, limit)
        else:
            # https://www.pixiv.net/ajax/user/1813972/illusts/tag/Fate%2FGrandOrder?offset=0&limit=24
            # https://www.pixiv.net/ajax/user/1813972/manga/tag/%E3%83%A1%E3%82%A4%E3%82%AD%E3%83%B3%E3%82%B0?offset=0&limit=24
            # https://www.pixiv.net/ajax/user/1113943/illustmanga/tag/%E6%A5%B5%E4%B8%8A%E3%81%AE%E4%B9%B3?offset=0&limit=24
            # https://www.pixiv.net/ajax/user/1813972/profile/all
            url = None
            if len(tags) > 0:
                url = 'https://www.pixiv.net/ajax/user/{0}/illustmanga/tag/{1}?offset={2}&limit={3}'.format(member_id, tags, offset, limit)
            elif self._config.r18mode:
                url = 'https://www.pixiv.net/ajax/user/{0}/illustmanga/tag/{1}?offset={2}&limit={3}'.format(member_id, 'R-18', offset, limit)
            else:
                url = 'https://www.pixiv.net/ajax/user/{0}/profile/all'.format(member_id)
                need_to_slice = True

            PixivHelper.print_and_log('info', 'Member Url: ' + url)

        if url is not None:
            # cache the response
            response = self.get_from_cache(url)
            if response is None:
                response = self.open(url).read()
                self.put_to_cache(url, response)

            PixivHelper.GetLogger().debug(response)
            artist = PixivModelWhiteCube.PixivArtist(member_id, response, False, offset, limit)
            self.getMemberInfoWhitecube(member_id, artist, bookmark)

            if artist.haveImages and need_to_slice:
                artist.imageList = artist.imageList[offset:offset + limit]
            ##        else:
            ##            if bookmark:
            ##                member_url = 'https://www.pixiv.net/bookmark.php?id=' + str(member_id) + '&p=' + str(page)
            ##            else:
            ##                member_url = 'https://www.pixiv.net/member_illust.php?id=' + str(member_id) + '&p=' + str(page)
            ##
            ##            if len(tags) > 0:
            ##                member_url = member_url + "&tag=" + tags
            ##            elif self._config.r18mode and not bookmark:
            ##                member_url = member_url + '&tag=R-18'
            ##                PixivHelper.print_and_log('info', 'R-18 Mode only.')
            ##            PixivHelper.print_and_log('info', 'Member Url: ' + member_url)
            ##            response = self.getPixivPage(member_url)
            ##            artist = PixivModel.PixivArtist(mid=member_id, page=response)

        return (artist, response)

    def getSearchTagPage(self, tags,
                         current_page,
                         wild_card=True,
                         title_caption=False,
                         start_date=None,
                         end_date=None,
                         member_id=None,
                         oldest_first=False,
                         start_page=1):
        response = None
        result = None
        url = ''

        if member_id is not None:
            ##            if member_id is None:
            ##                # from search page:
            ##                # https://www.pixiv.net/rpc/whitecube/index.php?order=date&adult_mode=include&q=vocaloid&p=0&type=&mode=whitecube_search&s_mode=s_tag&scd=&size=&ratio=&like=&tools=&tt=4e2cdee233f1156231ee99da1e51a83c
            ##                url = "https://www.pixiv.net/rpc/whitecube/index.php?q={0}".format(tags)
            ##                url = url + "&adult_mode={0}".format("include")
            ##                url = url + "&mode={0}".format("whitecube_search")
            ##
            ##                # date ordering
            ##                order = "date_d"
            ##                if oldest_first:
            ##                    order = "date"
            ##                url = url + "&order={0}".format(order)
            ##
            ##                # search mode
            ##                s_mode = "s_tag_full"
            ##                if wild_card:
            ##                    s_mode = "s_tag"
            ##                elif title_caption:
            ##                    s_mode = "s_tc"
            ##                url = url + "&s_mode={0}".format(s_mode)
            ##
            ##                # start/end date
            ##                if start_date is not None:
            ##                    url = url + "&scd={0}".format(start_date)
            ##                if end_date is not None:
            ##                    url = url + "&ecd={0}".format(end_date)
            ##
            ##                url = url + "&p={0}".format(i)
            ##                url = url + "&start_page={0}".format(start_page)
            ##                url = url + "&tt={0}".format(self._whitecubeToken)
            ##
            ##                PixivHelper.print_and_log('info', 'Looping for {0} ...'.format(url))
            ##                response = self.open(url).read()
            ##                self.handleDebugTagSearchPage(response, url)
            ##
            ##                PixivHelper.GetLogger().debug(response)
            ##                result = PixivModelWhiteCube.PixivTags()
            ##                result.parseTags(response, tags)
            ##            else:
            # from member id search by tags
            (artist, response) = self.getMemberPage(member_id, current_page, False, tags)

            # convert to PixivTags
            result = PixivModelWhiteCube.PixivTags()
            result.parseMemberTags(artist, member_id, tags)
        else:
            # search by tags
            url = PixivHelper.generateSearchTagUrl(tags, current_page,
                                                   title_caption,
                                                   wild_card,
                                                   oldest_first,
                                                   start_date,
                                                   end_date,
                                                   member_id,
                                                   self._config.r18mode)

            PixivHelper.print_and_log('info', 'Looping... for ' + url)
            # response = self.open(url).read()
            response = self.getPixivPage(url, returnParsed=False).read()
            self.handleDebugTagSearchPage(response, url)

            parse_search_page = BeautifulSoup(response)

            result = PixivModel.PixivTags()
            if member_id is not None:
                result.parseMemberTags(parse_search_page, member_id, tags)
            else:
                try:
                    result.parseTags(parse_search_page, tags)
                except BaseException:
                    PixivHelper.dumpHtml("Dump for SearchTags " + tags + ".html", response)
                    raise

            parse_search_page.decompose()
            del parse_search_page

        return (result, response)

    def handleDebugTagSearchPage(self, response, url):
        if self._config.enableDump:
            if self._config.dumpTagSearchPage:
                dump_filename = "TagSearch Page for {0}.html".format(url)
                PixivHelper.dumpHtml(dump_filename, response)
                PixivHelper.print_and_log('info', 'Dumping html to: {0}'.format(dump_filename))
            if self._config.debugHttp:
                PixivHelper.safePrint(u"reply: {0}".format(PixivHelper.toUnicode(response)))

    def fanboxGetSupportedUsers(self):
        ''' get all supported users from the list from https://www.pixiv.net/ajax/fanbox/support'''
        url = 'https://www.pixiv.net/ajax/fanbox/support'
        PixivHelper.print_and_log('info', 'Getting supported artists from ' + url)
        # read the json response
        response = self.open(url).read()
        result = Fanbox(response)
        return result

    def fanboxGetPostsFromArtist(self, artist_id, next_url=""):
        ''' get all posts from the supported user from https://www.pixiv.net/ajax/fanbox/creator?userId=15521131 '''
        if next_url is None or next_url == "":
            url = "https://www.pixiv.net/ajax/fanbox/creator?userId={0}".format(artist_id)
        else:
            url = "https://www.pixiv.net" + next_url

        PixivHelper.print_and_log('info', 'Getting posts from ' + url)
        response = self.open(url).read()
        # Issue #420
        _tzInfo = None
        if self._config.useLocalTimezone:
            _tzInfo = PixivHelper.LocalUTCOffsetTimezone()
        result = FanboxArtist(artist_id, response, tzInfo=_tzInfo)

        pixivArtist = PixivModelWhiteCube.PixivArtist(artist_id)
        self.getMemberInfoWhitecube(artist_id, pixivArtist)
        result.artistName = pixivArtist.artistName
        result.artistToken = pixivArtist.artistToken

        return result


def getBrowser(config=None, cookieJar=None):
    global defaultCookieJar
    global defaultConfig
    global _browser

    if _browser is None:
        if config is not None:
            defaultConfig = config
        if cookieJar is not None:
            defaultCookieJar = cookieJar
        if defaultCookieJar is None:
            PixivHelper.GetLogger().info("No default cookie jar available, creating... ")
            defaultCookieJar = cookielib.LWPCookieJar()
        _browser = PixivBrowser(defaultConfig, defaultCookieJar)

    return _browser


def getExistingBrowser():
    global _browser
    if _browser is None:
        raise PixivException("Browser is not initialized yet!", errorCode=PixivException.NOT_LOGGED_IN)
    return _browser


# pylint: disable=W0612
def test():
    from PixivConfig import PixivConfig
    cfg = PixivConfig()
    cfg.loadConfig("./config.ini")
    b = getBrowser(cfg, None)
    success = False
    if cfg.cookie is not None and len(cfg.cookie) > 0:
        success = b.loginUsingCookie(cfg.cookie)
    elif not success:
        success = b.login(cfg.username, cfg.password)

    if success:
        def testSearchTags():
            print("test search tags")
            tags = "VOCALOID"
            p = 1
            wild_card = True
            title_caption = False
            start_date = "2016-11-06"
            end_date = "2016-11-07"
            member_id = None
            oldest_first = True
            start_page = 1
            (resultS, page) = b.getSearchTagPage(tags, p,
                                                wild_card,
                                                title_caption,
                                                start_date,
                                                end_date,
                                                member_id,
                                                oldest_first,
                                                start_page)
            resultS.PrintInfo()
            assert(len(resultS.itemList) > 0)

        def testImage():
            print("test image mode")
            print(">>")
            (result, page) = b.getImagePage(60040975)
            print(result.PrintInfo())
            assert(len(result.imageTitle) > 0)
            print(result.artist.PrintInfo())
            assert(len(result.artist.artistToken) > 0)
            assert(not("R-18" in result.imageTags))

            print(">>")
            (result2, page2) = b.getImagePage(59628358)
            print(result2.PrintInfo())
            assert(len(result2.imageTitle) > 0)
            print(result2.artist.PrintInfo())
            assert(len(result2.artist.artistToken) > 0)
            assert("R-18" in result2.imageTags)

            print(">> ugoira")
            (result3, page3) = b.getImagePage(60070169)
            print(result3.PrintInfo())
            assert(len(result3.imageTitle) > 0)
            print(result3.artist.PrintInfo())
            print(result3.ugoira_data)
            assert(len(result3.artist.artistToken) > 0)
            assert(result3.imageMode == 'ugoira_view')

        def testMember():
            print("Test member mode")
            print(">>")
            (result3, page3) = b.getMemberPage(1227869, page=1, bookmark=False, tags=None)
            print(result3.PrintInfo())
            assert(len(result3.artistToken) > 0)
            assert(len(result3.imageList) > 0)
            print(">>")
            (result4, page4) = b.getMemberPage(1227869, page=2, bookmark=False, tags=None)
            print(result4.PrintInfo())
            assert(len(result4.artistToken) > 0)
            assert(len(result4.imageList) > 0)
            print(">>")
            (result5, page5) = b.getMemberPage(4894, page=1, bookmark=False, tags=None)
            print(result5.PrintInfo())
            assert(len(result5.artistToken) > 0)
            assert(len(result5.imageList) > 0)
            print(">>")
            (result6, page6) = b.getMemberPage(4894, page=3, bookmark=False, tags=None)
            print(result6.PrintInfo())
            assert(len(result6.artistToken) > 0)
            assert(len(result6.imageList) > 0)

        def testMemberBookmark():
            print("Test member bookmarks mode")
            print(">>")
            (result5, page5) = b.getMemberPage(1227869, page=1, bookmark=True, tags=None)
            print(result5.PrintInfo())
            assert(len(result5.artistToken) > 0)
            assert(len(result5.imageList) > 0)
            print(">>")
            (result6, page6) = b.getMemberPage(1227869, page=2, bookmark=True, tags=None)
            print(result6.PrintInfo())
            assert(len(result6.artistToken) > 0)
            assert(len(result6.imageList) > 0)
            print(">>")
            (result6, page6) = b.getMemberPage(1227869, page=10, bookmark=True, tags=None)
            if result6 is not None:
                print(result6.PrintInfo())
            (result6, page6) = b.getMemberPage(1227869, page=12, bookmark=True, tags=None)
            if result6 is not None:
                print(result6.PrintInfo())
                assert(len(result6.artistToken) > 0)
                assert(len(result6.imageList) == 0)

        # testSearchTags()
        testImage()
        # testMember()
        # testMemberBookmark()

    else:
        print("Invalid username or password")


if __name__ == '__main__':
    test()
    print("done")
