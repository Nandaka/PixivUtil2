# -*- coding: utf-8 -*-
# pylint: disable=W0603, C0325


import http.cookiejar
import http.client
import json
import mechanize
import re
import socket
import sys
import time
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import urllib.parse
from bs4 import BeautifulSoup

import demjson
import socks

import PixivHelper
import PixivModel
import PixivModelWhiteCube
from PixivException import PixivException
from PixivModelFanbox import Fanbox, FanboxArtist
from PixivOAuth import PixivOAuth

defaultCookieJar = None
defaultConfig = None
_browser = None


# pylint: disable=E1101
class PixivBrowser(mechanize.Browser):
    _config = None
    _isWhitecube = False
    _whitecubeToken = ""
    _cache = dict()
    _myId = 0
    _isPremium = False

    _username = None
    _password = None
    _oauth_manager = None

    def _put_to_cache(self, key, item, expiration=3600):
        expiry = time.time() + expiration
        self._cache[key] = (item, expiry)

    def _get_from_cache(self, key):
        if key in list(self._cache.keys()):
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
            mechanize.Browser.__init__(self, factory=mechanize.RobustFactory())
        except BaseException:
            PixivHelper.GetLogger().info("Using default factory (mechanize 3.x ?)")
            mechanize.Browser.__init__(self)

        self._configureBrowser(config)
        self._configureCookie(cookie_jar)

    def clear_history(self):
        mechanize.Browser.clear_history(self)
        return

    def back(self):
        mechanize.Browser.back(self)
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
                parseResult = urllib.parse.urlparse(config.proxyAddress)
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
            defaultCookieJar = http.cookiejar.LWPCookieJar()
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
            except urllib.error.HTTPError:
                raise
            except BaseException:
                if retry_count < retry:
                    for t in range(1, self._config.retryWait):
                        print(t, end=' ')
                        time.sleep(1)
                    print('')
                    retry_count = retry_count + 1
                else:
                    PixivHelper.print_and_log('error', 'Error at open_with_retry(): {0}'.format(str(sys.exc_info())))
                    raise PixivException("Failed to get page: {0}, please check your internet connection/firewall/antivirus.".format(url), errorCode=PixivException.SERVER_ERROR)

    def getPixivPage(self, url, referer="https://www.pixiv.net", returnParsed=True):
        ''' get page from pixiv and return as parsed BeautifulSoup object or response object.

            throw PixivException as server error
        '''
        url = self.fixUrl(url)
        retry_count = 0
        while True:
            req = urllib.request.Request(url)
            req.add_header('Referer', referer)
            try:
                page = self.open_with_retry(req)
                if returnParsed:
                    parsedPage = BeautifulSoup(page.read())
                    return parsedPage
                else:
                    return page
            except urllib.error.HTTPError as ex:
                if ex.code in [403, 404, 503]:
                    return BeautifulSoup(ex.read())
            except BaseException:
                if retry_count < self._config.retry:
                    for t in range(1, self._config.retryWait):
                        print(t, end=' ')
                        time.sleep(1)
                    print('')
                    retry_count = retry_count + 1
                else:
                    PixivHelper.print_and_log('error', 'Error at getPixivPage(): {0}'.format(str(sys.exc_info())))
                    raise PixivException("Failed to get page: {0}".format(url), errorCode=PixivException.SERVER_ERROR)

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
        ck = http.cookiejar.Cookie(version=0, name='PHPSESSID', value=cookie_value, port=None,
                              port_specified=False, domain='pixiv.net', domain_specified=False,
                              domain_initial_dot=False, path='/', path_specified=True,
                              secure=False, expires=None, discard=True, comment=None,
                              comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
        self.addCookie(ck)

#        cookies = cookie_value.split(";")
#        for cookie in cookies:
#            temp = cookie.split("=")
#            name = temp[0].strip()
#            value= temp[1] if len(temp) > 1 else ""
#            ck = cookielib.Cookie(version=0, name=name, value=value, port=None,
#                                  port_specified=False, domain='pixiv.net', domain_specified=False,
#                                  domain_initial_dot=False, path='/', path_specified=True,
#                                  secure=False, expires=None, discard=True, comment=None,
#                                  comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
#            self.addCookie(ck)

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
            res = self.open_with_retry('https://www.pixiv.net/mypage.php')
            resData = res.read()

            parsed = BeautifulSoup(resData)

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
            page = self.open_with_retry(url)

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

            request = urllib.request.Request("https://accounts.pixiv.net/api/login?lang=en", urllib.parse.urlencode(data))
            response = self.open_with_retry(request)

            return self.processLoginResult(response, username, password)
        except BaseException:
            PixivHelper.print_and_log('error', 'Error at login(): {0}'.format(sys.exc_info()))
            raise

    def processLoginResult(self, response, username, password):
        PixivHelper.GetLogger().info('Logging in, return url: %s', response.geturl())

        # check the returned json
        js = response.read()
        PixivHelper.GetLogger().info(str(js))
        result = json.loads(js)
        # Fix Issue #181
        if result["body"] is not None and "success" in result["body"]:
            #            cookie.value = self._ua_handlers['_cookies']
            #            PixivHelper.print_and_log('info', 'new cookie value: ' + str(cookie.value))
            #            self._config.cookie = cookie.value
            #            self._config.writeConfig(path=self._config.configFileLocation)
            for cookie in self._ua_handlers['_cookies'].cookiejar:
                if cookie.name == 'PHPSESSID':
                    PixivHelper.print_and_log('info', 'new cookie value: ' + str(cookie.value))
                    self._config.cookie = cookie.value
                    self._config.writeConfig(path=self._config.configFileLocation)
                    break

            # check whitecube
            page = self.open_with_retry(result["body"]["success"]["return_to"])
            parsed = BeautifulSoup(page)
            self.getMyId(parsed)

            # store the username and password in memory for oAuth login
            self._config.username = username
            self._config.password = password

            return True
        else:
            if result["body"] is not None and "validation_errors" in result["body"]:
                PixivHelper.print_and_log('info', "Server reply: " + str(result["body"]["validation_errors"]))
            else:
                PixivHelper.print_and_log('info', 'Unknown login issue, please use cookie login method.')
            return False

    def getMyId(self, parsed):
        ''' Assume from main page '''
        # pixiv.user.id = "189816";
        temp = re.findall(r"pixiv.user.id = \"(\d+)\";", str(parsed))
        if temp is not None:
            self._myId = int(temp[0])
            PixivHelper.print_and_log('info', 'My User Id: {0}.'.format(self._myId))
        else:
            PixivHelper.print_and_log('info', 'Unable to get User Id')

        self._isPremium = False
        temp = re.findall(r"pixiv.user.premium = (\w+);", str(parsed))
        if temp is not None:
            self._isPremium = True if temp[0] == "true" else False
        PixivHelper.print_and_log('info', 'Premium User: {0}.'.format(self._isPremium))

    def parseLoginError(self, res):
        page = BeautifulSoup(res.read())
        r = page.findAll('span', attrs={'class': 'error'})
        return r

    def getImagePage(self, image_id, parent=None, from_bookmark=False,
                     bookmark_count=-1, image_response_count=-1):
        image = None
        response = None
        PixivHelper.GetLogger().debug("Getting image page: %s", image_id)
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
                    meta_response = self.open_with_retry(ugoira_meta_url).read()
                    image.ParseUgoira(meta_response)

                if parent is None:
                    if from_bookmark:
                        image.originalArtist.reference_image_id = image_id
                        self.getMemberInfoWhitecube(image.originalArtist.artistId, image.originalArtist)
                    else:
                        image.artist.reference_image_id = image_id
                        self.getMemberInfoWhitecube(image.artist.artistId, image.artist)
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
                PixivHelper.safePrint("reply: {0}".format(PixivHelper.toUnicode(response)))

    def getMemberInfoWhitecube(self, member_id, artist, bookmark=False):
        ''' get artist information using Ajax and AppAPI '''
        try:
            info = None
            if artist.reference_image_id > 0:
                url = "https://www.pixiv.net/rpc/get_work.php?id={0}".format(artist.reference_image_id)
                PixivHelper.GetLogger().debug("using webrpc: %s", url)
                info = self._get_from_cache(url)
                if info is None:
                    request = urllib.request.Request(url)
                    infoStr = self.open_with_retry(request).read()
                    info = json.loads(infoStr)
                    self._put_to_cache(url, info)
            else:
                PixivHelper.print_and_log('info', 'Using OAuth to retrieve member info for: {0}'.format(member_id))
                if self._username is None or self._username is None or len(self._username) < 0 or len(self._password) < 0:
                    raise PixivException("Empty Username or Password, please remove the cookie value and relogin, or add username/password to config.ini.")

                if self._oauth_manager is None:
                    proxy = None
                    if self._config.useProxy:
                        proxy = self._config.proxy
                    self._oauth_manager = PixivOAuth(self._username, self._password, proxies=proxy, refresh_token=self._config.refresh_token, validate_ssl=self._config.enableSSLVerification)

                url = 'https://app-api.pixiv.net/v1/user/detail?user_id={0}'.format(member_id)
                info = self._get_from_cache(url)
                if info is None:
                    PixivHelper.GetLogger().debug("Getting member information: %s", member_id)
                    login_response = self._oauth_manager.login()
                    if login_response.status_code == 200:
                        info = json.loads(login_response.text)
                        self._config.refresh_token = info["response"]["refresh_token"]
                        self._config.writeConfig(path=self._config.configFileLocation)

                    response = self._oauth_manager.get_user_info(member_id)
                    info = json.loads(response.text)
                    self._put_to_cache(url, info)
                    PixivHelper.GetLogger().debug("reply: %s", response.text)

            artist.ParseInfo(info, False, bookmark=bookmark)

            # will throw HTTPError if user is suspended/not logged in.
            url_ajax = 'https://www.pixiv.net/ajax/user/{0}'.format(member_id)
            info_ajax = self._get_from_cache(url_ajax)
            if info_ajax is None:
                info_ajax_str = self.open_with_retry(url_ajax).read()
                info_ajax = json.loads(info_ajax_str)
                self._put_to_cache(url_ajax, info_ajax)
            # 2nd pass to get the background
            artist.ParseBackground(info_ajax)

            return artist
        except urllib.error.HTTPError as error:
            errorCode = error.getcode()
            errorMessage = error.get_data()
            PixivHelper.GetLogger().error("Error data: \r\n %s", errorMessage)
            payload = demjson.decode(errorMessage)
            # Issue #432
            if "message" in payload:
                msg = payload["message"]
            elif "error" in payload and payload["error"] is not None:
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

    def getMemberPage(self, member_id, page=1, bookmark=False, tags=None):
        artist = None
        response = None
        if tags is not None:
            tags = PixivHelper.encode_tags(tags)
        else:
            tags = ''

        limit = 48
        offset = (page - 1) * limit
        need_to_slice = False
        if bookmark:
            # https://www.pixiv.net/ajax/user/1039353/illusts/bookmarks?tag=&offset=0&limit=24&rest=show
            url = 'https://www.pixiv.net/ajax/user/{0}/illusts/bookmarks?tag={1}&offset={2}&limit={3}&rest=show'.format(member_id, tags, offset, limit)
        else:
            # https://www.pixiv.net/ajax/user/1813972/illusts/tag?tag=Fate%2FGrandOrder?offset=0&limit=24
            # https://www.pixiv.net/ajax/user/1813972/manga/tag?tag=%E3%83%A1%E3%82%A4%E3%82%AD%E3%83%B3%E3%82%B0?offset=0&limit=24
            # https://www.pixiv.net/ajax/user/5238/illustmanga/tag?tag=R-18&offset=0&limit=48
            # https://www.pixiv.net/ajax/user/1813972/profile/all
            url = None
            if len(tags) > 0:
                url = 'https://www.pixiv.net/ajax/user/{0}/illustmanga/tag?tag={1}&offset={2}&limit={3}'.format(member_id, tags, offset, limit)
            elif self._config.r18mode:
                url = 'https://www.pixiv.net/ajax/user/{0}/illustmanga/tag?tag={1}&offset={2}&limit={3}'.format(member_id, 'R-18', offset, limit)
            else:
                url = 'https://www.pixiv.net/ajax/user/{0}/profile/all'.format(member_id)
                need_to_slice = True

            PixivHelper.print_and_log('info', 'Member Url: ' + url)

        if url is not None:
            # cache the response
            response = self._get_from_cache(url)
            if response is None:
                try:
                    response = self.open_with_retry(url).read()
                except urllib.error.HTTPError as ex:
                    if ex.code == 404:
                        response = ex.read()
                self._put_to_cache(url, response)

            PixivHelper.GetLogger().debug(response)
            artist = PixivModelWhiteCube.PixivArtist(member_id, response, False, offset, limit)
            artist.reference_image_id = artist.imageList[0] if len(artist.imageList) > 0 else 0
            self.getMemberInfoWhitecube(member_id, artist, bookmark)

            if artist.haveImages and need_to_slice:
                artist.imageList = artist.imageList[offset:offset + limit]

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
                PixivHelper.safePrint("reply: {0}".format(PixivHelper.toUnicode(response)))

    def fanboxGetSupportedUsers(self):
        ''' get all supported users from the list from https://www.pixiv.net/ajax/fanbox/index'''
        url = 'https://www.pixiv.net/ajax/fanbox/index'
        PixivHelper.print_and_log('info', 'Getting supported artists from ' + url)
        # read the json response
        response = self.open_with_retry(url).read()
        result = Fanbox(response)
        return result

    def fanboxGetPostsFromArtist(self, artist_id, next_url=""):
        ''' get all posts from the supported user from https://www.pixiv.net/ajax/fanbox/creator?userId=15521131 '''
        if next_url is None or next_url == "":
            url = "https://www.pixiv.net/ajax/fanbox/creator?userId={0}".format(artist_id)
        elif next_url.startswith("https://"):
            url = next_url
        else:
            url = "https://www.pixiv.net" + next_url

        # Fix #494
        PixivHelper.print_and_log('info', 'Getting posts from ' + url)
        referer = "https://www.pixiv.net/fanbox/creator/{0}".format(artist_id)
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/json, text/plain, */*')
        req.add_header('Referer', referer)
        req.add_header('Origin', 'https://www.pixiv.net')
        req.add_header('User-Agent', self._config.useragent)

        response = self.open_with_retry(req).read()
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
            defaultCookieJar = http.cookiejar.LWPCookieJar()
        _browser = PixivBrowser(defaultConfig, defaultCookieJar)
    elif config is not None:
        defaultConfig = config
        _browser._configureBrowser(config)

    return _browser


def getExistingBrowser():
    global _browser
    if _browser is None:
        raise PixivException("Browser is not initialized yet!", errorCode=PixivException.NOT_LOGGED_IN)
    return _browser


# pylint: disable=W0612
def get_br():
    from PixivConfig import PixivConfig
    cfg = PixivConfig()
    cfg.loadConfig("./config.ini")
    b = getBrowser(cfg, None)
    if cfg.cookie is not None and len(cfg.cookie) > 0:
        success = b.loginUsingCookie(cfg.cookie)
        b._username = cfg.username
        b._password = cfg.password
    elif not success:
        success = b.login(cfg.username, cfg.password)

    return (b, success)


def test():
    (b, success) = get_br()
    b.get_oauth_token()

    refresh_token = b._oauth_reply['response']['refresh_token']
    auth_token = b._oauth_reply['response']['access_token']
    print("Reply = {0}".format(b._oauth_reply))
    print("Auth Token = " + auth_token)
    print("Refr Token = " + refresh_token)
    b.get_oauth_token(refresh_token, auth_token)

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
