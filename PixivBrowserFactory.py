# -*- coding: utf-8 -*-
# pylint: disable=W0603, C0325

import http.client
import http.cookiejar
import json
import re
import socket
import sys
import time
import urllib
import traceback

import demjson
import mechanize
import socks
from bs4 import BeautifulSoup

import PixivHelper
from PixivArtist import PixivArtist
from PixivException import PixivException
from PixivImage import PixivImage
from PixivModelFanbox import Fanbox, FanboxArtist, FanboxPost
from PixivOAuth import PixivOAuth
from PixivTags import PixivTags

defaultCookieJar = None
defaultConfig = None
_browser = None


# pylint: disable=E1101
class PixivBrowser(mechanize.Browser):
    _config = None
    _isWhitecube = False
    _whitecubeToken = ""
    _cache = dict()
    _max_cache = 10000  # keep 1000 item in memory
    _myId = 0
    _isPremium = False

    _username = None
    _password = None
    _oauth_manager = None
    _locale = ""

    def _put_to_cache(self, key, item, expiration=3600):
        expiry = time.time() + expiration
        self._cache[key] = (item, expiry)

        # check oldest item
        oldest_expiry = expiry
        oldest_item = key
        if len(self._cache) > self._max_cache:
            for key2 in self._cache:
                curr_expiry = self._cache[key2][1]
                if curr_expiry < oldest_expiry:
                    oldest_item = key2
                    oldest_expiry = curr_expiry
            del self._cache[oldest_item]

    def _get_from_cache(self, key, sliding_window=3600):
        if key in self._cache.keys():
            (item, expiry) = self._cache.pop(key)
            if expiry - time.time() > 0:
                self._cache[key] = (item, expiry + sliding_window)
                return item

            # expired data
            del item

        return None

    def __init__(self, config, cookie_jar):
        # fix #218 not applicable after upgrading to mechanize 4.x
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
            PixivHelper.get_logger().info("No config given")
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
                PixivHelper.get_logger().info(f"Using SOCKS5 Proxy= {parseResult.hostname}:{parseResult.port}")
                # https://stackoverflow.com/a/14512227
                socks.setdefaultproxy(socksType, parseResult.hostname, parseResult.port)
                socket.socket = socks.socksocket
            else:
                self.set_proxies(config.proxy)
                PixivHelper.get_logger().info("Using Proxy: %s", config.proxyAddress)

        # self.set_handle_equiv(True)
        # self.set_handle_gzip(True)
        self.set_handle_redirect(True)
        self.set_handle_referer(True)
        self.set_handle_robots(False)

        self.set_debug_http(config.debugHttp)
        if config.debugHttp:
            PixivHelper.get_logger().info('Debug HTTP enabled.')

        # self.visit_response
        self.addheaders = [('User-agent', config.useragent)]

        # force utf-8, fix issue #184
        self.addheaders = [('Accept-Charset', 'utf-8')]

        socket.setdefaulttimeout(config.timeout)

        if not self._config.enableSSLVerification:
            import ssl
            try:
                _create_unverified_https_context = ssl._create_unverified_context
            except AttributeError:
                # Legacy Python that doesn't verify HTTPS certificates by default
                pass
            else:
                # Handle target environment that doesn't support HTTPS verification
                ssl._create_default_https_context = _create_unverified_https_context

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

    def clearCookie(self):
        global defaultCookieJar
        if defaultCookieJar is None:
            defaultCookieJar = http.cookiejar.LWPCookieJar()
        defaultCookieJar.clear()

    def open_with_retry(self, url, data=None, timeout=60, retry=0):
        ''' Return response object with retry.'''
        retry_count = 0
        if retry == 0 and self._config is not None:
            retry = self._config.retry

        while True:
            try:
                return self.open(url, data, timeout)
            except urllib.error.HTTPError:
                raise
            except BaseException:
                exc_value = sys.exc_info()[1]
                if retry_count < retry:
                    print(exc_value, end=' ')
                    for t in range(1, self._config.retryWait):
                        print(t, end=' ')
                        time.sleep(1)
                    print('')
                    retry_count = retry_count + 1
                else:
                    temp = url
                    if isinstance(url, urllib.request.Request):
                        temp = url.full_url

                    PixivHelper.print_and_log('error', 'Error at open_with_retry(): {0}'.format(str(sys.exc_info())))
                    raise PixivException("Failed to get page: {0}, please check your internet connection/firewall/antivirus."
                                         .format(temp), errorCode=PixivException.SERVER_ERROR)

    def getPixivPage(self, url, referer="https://www.pixiv.net", returnParsed=True, enable_cache=True):
        ''' get page from pixiv and return as parsed BeautifulSoup object or response object.

            throw PixivException as server error
        '''
        url = self.fixUrl(url)
        while True:
            req = mechanize.Request(url)
            req.add_header('Referer', referer)

            read_page = self._get_from_cache(url)
            if read_page is None:
                try:
                    temp = self.open_with_retry(req)
                    read_page = temp.read()
                    read_page = read_page.decode('utf8')
                    if enable_cache:
                        self._put_to_cache(url, read_page)
                    temp.close()
                except urllib.error.HTTPError as ex:
                    if ex.code in [403, 404, 503]:
                        read_page = ex.read()
                        raise PixivException("Failed to get page: {0} => {1}".format(
                            url, ex), errorCode=PixivException.SERVER_ERROR)
                    else:
                        PixivHelper.print_and_log(
                            'error', 'Error at getPixivPage(): {0}'.format(str(sys.exc_info())))
                        raise PixivException("Failed to get page: {0}".format(
                            url), errorCode=PixivException.SERVER_ERROR)

            if returnParsed:
                parsedPage = BeautifulSoup(read_page, features="html5lib")
                return parsedPage
            return read_page

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
            self.clearCookie()
            self._loadCookie(login_cookie)
            res = self.open_with_retry('https://www.pixiv.net/')
            parsed = BeautifulSoup(res, features="html5lib").decode('utf-8')
            PixivHelper.get_logger().info('Logging in, return url: %s', res.geturl())
            res.close()

            result = False
            if "logout.php" in str(parsed):
                result = True
            if "pixiv.user.loggedIn = true" in str(parsed):
                result = True
            if "_gaq.push(['_setCustomVar', 1, 'login', 'yes'" in str(parsed):
                result = True
            if "var dataLayer = [{ login: 'yes'," in str(parsed):
                result = True

            if result:
                PixivHelper.print_and_log('info', 'Login successful.')
                PixivHelper.get_logger().info('Logged in using cookie')
                self.getMyId(parsed)
                temp_locale = str(res.geturl()).replace('https://www.pixiv.net/', '').replace('/', '')
                if len(temp_locale) > 0:
                    self._locale = '/' + temp_locale
                PixivHelper.get_logger().info('Locale = %s', self._locale)
            else:
                PixivHelper.get_logger().info('Failed to log in using cookie')
                PixivHelper.print_and_log('info', 'Cookie already expired/invalid.')

        del parsed
        return result

    def login(self, username, password):
        parsed = None
        try:
            PixivHelper.print_and_log('info', 'Logging in...')
            url = "https://accounts.pixiv.net/login"
            # get the post key
            res = self.open_with_retry(url)
            parsed = BeautifulSoup(res, features="html5lib")
            post_key = parsed.find('input', attrs={'name': 'post_key'})
            # js_init_config = self._getInitConfig(parsed)
            res.close()

            data = {}
            data['pixiv_id'] = username
            data['password'] = password
            # data['captcha'] = ''
            # data['g_recaptcha_response'] = ''
            data['return_to'] = 'https://www.pixiv.net'
            data['lang'] = 'en'
            data['post_key'] = post_key['value']
            data['source'] = "accounts"
            data['ref'] = ''

            request = mechanize.Request("https://accounts.pixiv.net/api/login?lang=en", data, method='POST')
            response = self.open_with_retry(request)

            result = self.processLoginResult(response, username, password)
            response.close()
            return result
        except BaseException:
            traceback.print_exc()
            PixivHelper.print_and_log('error', 'Error at login(): {0}'.format(sys.exc_info()))
            PixivHelper.dump_html("login_error.html", str(parsed))
            raise
        finally:
            if parsed is not None:
                parsed.decompose()
                del parsed

    def processLoginResult(self, response, username, password):
        PixivHelper.get_logger().info('Logging in, return url: %s', response.geturl())

        # check the returned json
        js = response.read()
        PixivHelper.get_logger().info(str(js))
        result = json.loads(js)

        # Fix Issue #181
        if result["body"] is not None and "success" in result["body"]:
            for cookie in self._ua_handlers['_cookies'].cookiejar:
                if cookie.name == 'PHPSESSID':
                    PixivHelper.print_and_log(
                        'info', 'new cookie value: ' + str(cookie.value))
                    self._config.cookie = cookie.value
                    self._config.writeConfig(
                        path=self._config.configFileLocation)
                    break

            # check whitecube
            res = self.open_with_retry(result["body"]["success"]["return_to"])
            parsed = BeautifulSoup(res, features="html5lib").decode('utf-8')
            self.getMyId(parsed)
            res.close()

            # store the username and password in memory for oAuth login
            self._config.username = username
            self._config.password = password

            del parsed
            return True
        else:
            if result["body"] is not None and "validation_errors" in result["body"]:
                PixivHelper.print_and_log(
                    'info', "Server reply: " + str(result["body"]["validation_errors"]))
                if str(result["body"]["validation_errors"]).find("reCAPTCHA") > 0:
                    print(
                        "Please follow the method described in https://github.com/Nandaka/PixivUtil2/issues/505")
            else:
                PixivHelper.print_and_log('info', 'Unknown login issue, please use cookie login method.')
            return False

    def getMyId(self, parsed):
        ''' Assume from main page '''
        temp = None
        # pixiv.user.id = "189816";
        temp = re.findall(r"pixiv.user.id = \"(\d+)\";", parsed)
        if temp is not None and len(temp) > 0:
            self._myId = int(temp[0])
            PixivHelper.print_and_log('info', f'My User Id: {self._myId}.')
        else:
            # _gaq.push(['_setCustomVar', 6, 'user_id', "3145410", 1]);
            temp = re.findall(r"_gaq.push\(\['_setCustomVar', 6, 'user_id', \"(\d+)\", 1\]\);", parsed)
            if self._myId == 0 and temp is not None and len(temp) > 0:
                self._myId = int(temp[0])
                PixivHelper.print_and_log('info', f'My User Id: {self._myId}.')
            else:
                # var dataLayer = [{ login: 'yes', gender: "male", user_id: "3145410", lang: "en", illustup_flg: 'not_uploaded', premium: 'no', }];
                temp = re.findall(r"var dataLayer = .*user_id: \"(\d+)\"", parsed)
                if self._myId == 0 and temp is not None and len(temp) > 0:
                    self._myId = int(temp[0])
                    PixivHelper.print_and_log('info', f'My User Id: {self._myId}.')

        if self._myId == 0:
            PixivHelper.print_and_log('info', 'Unable to get User Id')

        self._isPremium = False
        temp = re.findall(r"pixiv.user.premium = (\w+);", parsed)
        if temp is not None and len(temp) > 0:
            self._isPremium = True if temp[0] == "true" else False
        else:
            temp = re.findall(r"_gaq.push\(\['_setCustomVar', 3, 'plan', '(\w+)', 1\]\)", parsed)
            if temp is not None and len(temp) > 0:
                self._isPremium = True if temp[0] == "premium" else False
            else:
                temp = re.findall(r"var dataLayer = .*premium: '(\w+)'", parsed)
                if temp is not None and len(temp) > 0:
                    self._isPremium = True if temp[0] == "yes" else False
        PixivHelper.print_and_log('info', 'Premium User: {0}.'.format(self._isPremium))

    def parseLoginError(self, res):
        page = BeautifulSoup(res, features="html5lib")
        r = page.findAll('span', attrs={'class': 'error'})
        page.decompose()
        del page
        return r

    def getImagePage(self, image_id, parent=None, from_bookmark=False,
                     bookmark_count=-1, image_response_count=-1):
        image = None
        response = None
        PixivHelper.get_logger().debug("Getting image page: %s", image_id)
        # https://www.pixiv.net/en/artworks/76656661
        url = "https://www.pixiv.net{1}/artworks/{0}".format(image_id, self._locale)
        response = self.getPixivPage(url, returnParsed=False, enable_cache=False)
        self.handleDebugMediumPage(response, image_id)

        # Issue #355 new ui handler
        image = None
        try:
            if response.find("meta-preload-data") > 0:
                PixivHelper.print_and_log('debug', 'New UI Mode')

                # Issue #420
                _tzInfo = None
                if self._config.useLocalTimezone:
                    _tzInfo = PixivHelper.LocalUTCOffsetTimezone()

                image = PixivImage(image_id,
                                   response,
                                   parent,
                                   from_bookmark,
                                   bookmark_count,
                                   image_response_count,
                                   dateFormat=self._config.dateFormat,
                                   tzInfo=_tzInfo)

                if image.imageMode == "ugoira_view":
                    ugoira_meta_url = "https://www.pixiv.net/ajax/illust/{0}/ugoira_meta".format(image_id)
                    res = self.open_with_retry(ugoira_meta_url)
                    meta_response = res.read()
                    image.ParseUgoira(meta_response)
                    res.close()

                if parent is None:
                    if from_bookmark:
                        image.originalArtist.reference_image_id = image_id
                        self.getMemberInfoWhitecube(image.originalArtist.artistId, image.originalArtist)
                    else:
                        image.artist.reference_image_id = image_id
                        self.getMemberInfoWhitecube(image.artist.artistId, image.artist)
        except BaseException:
            PixivHelper.get_logger().error("Respose data: \r\n %s", response)
            raise

        return (image, response)

    def handleDebugMediumPage(self, response, imageId):
        if self._config.enableDump:
            if self._config.dumpMediumPage:
                dump_filename = "Medium Page for Image Id {0}.html".format(imageId)
                PixivHelper.dump_html(dump_filename, response)
                PixivHelper.print_and_log('info', 'Dumping html to: {0}'.format(dump_filename))
            if self._config.debugHttp:
                PixivHelper.safePrint(u"reply: {0}".format(response))

    def getMemberInfoWhitecube(self, member_id, artist, bookmark=False):
        ''' get artist information using Ajax and AppAPI '''
        try:
            info = None
            if int(artist.reference_image_id) > 0:
                url = "https://www.pixiv.net/rpc/get_work.php?id={0}".format(artist.reference_image_id)
                PixivHelper.get_logger().debug("using webrpc: %s", url)
                info = self._get_from_cache(url)
                if info is None:
                    request = mechanize.Request(url)
                    res = self.open_with_retry(request)
                    infoStr = res.read()
                    res.close()
                    info = json.loads(infoStr)
                    self._put_to_cache(url, info)
            else:
                PixivHelper.print_and_log('info', 'Using OAuth to retrieve member info for: {0}'.format(member_id))
                if self._username is None or self._password is None or len(self._username) < 0 or len(self._password) < 0:
                    raise PixivException("Empty Username or Password, remove cookie value and relogin, or add username/password to config.ini.")

                if self._oauth_manager is None:
                    proxy = None
                    if self._config.useProxy:
                        proxy = self._config.proxy
                    self._oauth_manager = PixivOAuth(self._username,
                                                     self._password,
                                                     proxies=proxy,
                                                     refresh_token=self._config.refresh_token,
                                                     validate_ssl=self._config.enableSSLVerification)

                url = 'https://app-api.pixiv.net/v1/user/detail?user_id={0}'.format(
                    member_id)
                info = self._get_from_cache(url)
                if info is None:
                    PixivHelper.get_logger().debug("Getting member information: %s", member_id)
                    login_response = self._oauth_manager.login()
                    if login_response.status_code == 200:
                        info = json.loads(login_response.text)
                        self._config.refresh_token = info["response"]["refresh_token"]
                        self._config.writeConfig(
                            path=self._config.configFileLocation)

                    response = self._oauth_manager.get_user_info(member_id)
                    info = json.loads(response.text)
                    self._put_to_cache(url, info)
                    PixivHelper.get_logger().debug("reply: %s", response.text)

            artist.ParseInfo(info, False, bookmark=bookmark)

            # will throw HTTPError if user is suspended/not logged in.
            url_ajax = 'https://www.pixiv.net/ajax/user/{0}'.format(member_id)
            info_ajax = self._get_from_cache(url_ajax)
            if info_ajax is None:
                res = self.open_with_retry(url_ajax)
                info_ajax_str = res.read()
                res.close()
                info_ajax = json.loads(info_ajax_str)
                self._put_to_cache(url_ajax, info_ajax)
            # 2nd pass to get the background
            artist.ParseBackground(info_ajax)

            return artist
        except urllib.error.HTTPError as error:
            errorCode = error.getcode()
            errorMessage = error.get_data()
            PixivHelper.get_logger().error("Error data: \r\n %s", errorMessage)
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
        if tags is None:
            tags = ''

        limit = 48
        offset = (page - 1) * limit
        need_to_slice = False
        if bookmark:
            # https://www.pixiv.net/ajax/user/1039353/illusts/bookmarks?tag=&offset=0&limit=24&rest=show
            url = 'https://www.pixiv.net/ajax/user/{0}/illusts/bookmarks?tag={1}&offset={2}&limit={3}&rest=show'
            url = url.format(member_id, tags, offset, limit)
        else:
            # https://www.pixiv.net/ajax/user/1813972/illusts/tag?tag=Fate%2FGrandOrder?offset=0&limit=24
            # https://www.pixiv.net/ajax/user/1813972/manga/tag?tag=%E3%83%A1%E3%82%A4%E3%82%AD%E3%83%B3%E3%82%B0?offset=0&limit=24
            # https://www.pixiv.net/ajax/user/5238/illustmanga/tag?tag=R-18&offset=0&limit=48
            # https://www.pixiv.net/ajax/user/1813972/profile/all
            url = None
            if len(tags) > 0:
                url = 'https://www.pixiv.net/ajax/user/{0}/illustmanga/tag?tag={1}&offset={2}&limit={3}'
                url = url.format(member_id, tags, offset, limit)
            elif self._config.r18mode:
                url = 'https://www.pixiv.net/ajax/user/{0}/illustmanga/tag?tag={1}&offset={2}&limit={3}'
                url = url.format(member_id, 'R-18', offset, limit)
            else:
                url = 'https://www.pixiv.net/ajax/user/{0}/profile/all'.format(member_id)
                need_to_slice = True

            PixivHelper.print_and_log('info', 'Member Url: ' + url)

        if url is not None:
            # cache the response
            response = self._get_from_cache(url)
            if response is None:
                try:
                    res = self.open_with_retry(url)
                    response = res.read()
                    res.close()
                except urllib.error.HTTPError as ex:
                    if ex.code == 404:
                        response = ex.read()
                self._put_to_cache(url, response)

            PixivHelper.get_logger().debug(response)
            artist = PixivArtist(member_id, response, False, offset, limit)
            artist.reference_image_id = artist.imageList[0] if len(
                artist.imageList) > 0 else 0
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
                         start_page=1,
                         include_bookmark_data=False,
                         bookmark_count=0,
                         type_mode="a"):
        response_page = None
        result = None
        url = ''

        if member_id is not None:
            # from member id search by tags
            (artist, response_page) = self.getMemberPage(member_id, current_page, False, tags)

            # convert to PixivTags
            result = PixivTags()
            result.parseMemberTags(artist, member_id, tags)
        else:
            # only premium support server-side filtering for bookmark count
            if not self._isPremium:
                bookmark_count = 0

            # search by tags
            url = PixivHelper.generate_search_tag_url(tags, current_page,
                                                      title_caption,
                                                      wild_card,
                                                      oldest_first,
                                                      start_date,
                                                      end_date,
                                                      member_id,
                                                      self._config.r18mode,
                                                      bookmark_count,
                                                      type_mode)

            PixivHelper.print_and_log('info', 'Looping... for {0}'.format(url))
            response_page = self.getPixivPage(url, returnParsed=False)
            self.handleDebugTagSearchPage(response_page, url)

            result = None
            if member_id is not None:
                result = PixivTags()
                parse_search_page = BeautifulSoup(response_page, features="html5lib")
                result.parseMemberTags(parse_search_page, member_id, tags)
                parse_search_page.decompose()
                del parse_search_page
            else:
                try:
                    result = PixivTags()
                    result.parseTags(response_page, tags, current_page)

                    # parse additional information
                    if include_bookmark_data:
                        idx = 0
                        print("Retrieving bookmark information...", end=' ')
                        for image in result.itemList:
                            idx = idx + 1
                            print("\r", end=' ')
                            print("Retrieving bookmark information... [{0}] of [{1}]".format(
                                idx, len(result.itemList)), end=' ')

                            img_url = "https://www.pixiv.net/ajax/illust/{0}".format(
                                image.imageId)
                            response_page = self._get_from_cache(img_url)
                            if response_page is None:
                                try:
                                    res = self.open_with_retry(img_url)
                                    response_page = res.read()
                                    res.close()
                                except urllib.error.HTTPError as ex:
                                    if ex.code == 404:
                                        response_page = ex.read()
                                self._put_to_cache(img_url, response_page)

                            image_info_js = json.loads(response_page)
                            image.bookmarkCount = int(
                                image_info_js["body"]["bookmarkCount"])
                            image.imageResponse = int(
                                image_info_js["body"]["responseCount"])
                    print("")
                except BaseException:
                    PixivHelper.dump_html("Dump for SearchTags " + tags + ".html", response_page)
                    raise

        return (result, response_page)

    def handleDebugTagSearchPage(self, response, url):
        if self._config.enableDump:
            if self._config.dumpTagSearchPage:
                dump_filename = "TagSearch Page for {0}.html".format(url)
                PixivHelper.dump_html(dump_filename, response)
                PixivHelper.print_and_log(
                    'info', 'Dumping html to: {0}'.format(dump_filename))
            if self._config.debugHttp:
                PixivHelper.safePrint(u"reply: {0}".format(
                    PixivHelper.toUnicode(response)))

    def fanboxGetSupportedUsers(self):
        url = 'https://api.fanbox.cc/plan.listSupporting'
        PixivHelper.print_and_log('info', f'Getting supported artists from {url}')
        referer = "https://www.fanbox.cc/creators/supporting"
        req = mechanize.Request(url)
        req.add_header('Accept', 'application/json, text/plain, */*')
        req.add_header('Referer', referer)
        req.add_header('Origin', 'https://www.fanbox.cc')
        req.add_header('User-Agent', self._config.useragent)

        res = self.open_with_retry(req)
        # read the json response
        response = res.read()
        res.close()
        result = Fanbox(response)
        return result

    def fanboxGetFollowedUsers(self):
        url = 'https://api.fanbox.cc/creator.listFollowing'
        PixivHelper.print_and_log('info', f'Getting supported artists from {url}')
        referer = "https://www.fanbox.cc/creators/following"
        req = mechanize.Request(url)
        req.add_header('Accept', 'application/json, text/plain, */*')
        req.add_header('Referer', referer)
        req.add_header('Origin', 'https://www.fanbox.cc')
        req.add_header('User-Agent', self._config.useragent)

        res = self.open_with_retry(req)
        # read the json response
        response = res.read()
        res.close()
        result = Fanbox(response)
        return result

    def fanboxGetPostsFromArtist(self, artist_id, next_url=""):
        ''' get all posts from the supported user from https://fanbox.pixiv.net/api/post.listCreator?userId=1305019&limit=10 '''
        # Issue #641
        if next_url is None or next_url == "":
            url = f"https://fanbox.pixiv.net/api/post.listCreator?userId={artist_id}&limit=10"
        elif next_url.startswith("https://"):
            url = next_url
        else:
            url = "https://www.pixiv.net" + next_url

        # Fix #494
        PixivHelper.print_and_log('info', 'Getting posts from ' + url)
        referer = f"https://www.pixiv.net/fanbox/creator/{artist_id}"
        req = mechanize.Request(url)
        req.add_header('Accept', 'application/json, text/plain, */*')
        req.add_header('Referer', referer)
        req.add_header('Origin', 'https://www.pixiv.net')
        req.add_header('User-Agent', self._config.useragent)

        res = self.open_with_retry(req)
        response = res.read()
        PixivHelper.get_logger().debug(response.decode('utf8'))
        res.close()
        # Issue #420
        _tzInfo = None
        if self._config.useLocalTimezone:
            _tzInfo = PixivHelper.LocalUTCOffsetTimezone()
        result = FanboxArtist(artist_id, response, tzInfo=_tzInfo)

        pixivArtist = PixivArtist(artist_id)
        self.getMemberInfoWhitecube(artist_id, pixivArtist)
        result.artistName = pixivArtist.artistName
        result.artistToken = pixivArtist.artistToken

        for post in result.posts:
            js = self.fanboxGetPost(post.imageId, artist_id)
            post.parsePost(js["body"])

        return result

    def fanboxGetPost(self, post_id, member_id=0):
        # https://fanbox.pixiv.net/api/post.info?postId=279561
        # https://www.pixiv.net/fanbox/creator/104409/post/279561
        p_url = f"https://fanbox.pixiv.net/api/post.info?postId={post_id}"
        # referer doesn't seeem to be essential
        p_referer = f"https://www.pixiv.net/fanbox/creator/{member_id}/post/{post_id}"
        PixivHelper.get_logger().debug('Getting post detail from %s', p_url)
        p_req = mechanize.Request(p_url)
        p_req.add_header('Accept', 'application/json, text/plain, */*')
        p_req.add_header('Referer', p_referer)
        p_req.add_header('Origin', 'https://www.pixiv.net')
        p_req.add_header('User-Agent', self._config.useragent)

        p_res = self.open_with_retry(p_req)
        p_response = p_res.read()
        PixivHelper.get_logger().debug(p_response.decode('utf8'))
        p_res.close()
        js = demjson.decode(p_response)
        if member_id:
            return js
        else:
            _tzInfo = None
            if self._config.useLocalTimezone:
                _tzInfo = PixivHelper.LocalUTCOffsetTimezone()
            user = object().__new__(FanboxArtist)
            user.artistId = js["body"]["user"]["userId"]
            user.name = js["body"]["user"]["name"]
            post = FanboxPost(post_id, user, js["body"], _tzInfo)
            return post


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
            PixivHelper.get_logger().info("No default cookie jar available, creating... ")
            defaultCookieJar = http.cookiejar.LWPCookieJar()
        _browser = PixivBrowser(defaultConfig, defaultCookieJar)
    elif config is not None:
        defaultConfig = config
        _browser._configureBrowser(config)

    return _browser


def getExistingBrowser():
    global _browser
    if _browser is None:
        raise PixivException("Browser is not initialized yet!",
                             errorCode=PixivException.NOT_LOGGED_IN)
    return _browser


# pylint: disable=W0612
def get_br():
    from PixivConfig import PixivConfig
    cfg = PixivConfig()
    cfg.loadConfig("./config.ini")
    b = getBrowser(cfg, None)
    success = False
    if cfg.cookie is not None and len(cfg.cookie) > 0:
        success = b.loginUsingCookie(cfg.cookie)
        b._username = cfg.username
        b._password = cfg.password

    if not success:
        success = b.login(cfg.username, cfg.password)

    return (b, success)


def test():
    (b, success) = get_br()
    # b.get_oauth_token()

    # refresh_token = b._oauth_reply['response']['refresh_token']
    # auth_token = b._oauth_reply['response']['access_token']
    # print("Reply = {0}".format(b._oauth_reply))
    # print("Auth Token = " + auth_token)
    # print("Refr Token = " + refresh_token)
    # b.get_oauth_token(refresh_token, auth_token)

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
            assert("R-18" not in result.imageTags)

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
            (result3, page3) = b.getMemberPage(
                1227869, page=1, bookmark=False, tags=None)
            print(result3.PrintInfo())
            assert(len(result3.artistToken) > 0)
            assert(len(result3.imageList) > 0)
            print(">>")
            (result4, page4) = b.getMemberPage(
                1227869, page=2, bookmark=False, tags=None)
            print(result4.PrintInfo())
            assert(len(result4.artistToken) > 0)
            assert(len(result4.imageList) > 0)
            print(">>")
            (result5, page5) = b.getMemberPage(
                4894, page=1, bookmark=False, tags=None)
            print(result5.PrintInfo())
            assert(len(result5.artistToken) > 0)
            assert(len(result5.imageList) > 0)
            print(">>")
            (result6, page6) = b.getMemberPage(
                4894, page=3, bookmark=False, tags=None)
            print(result6.PrintInfo())
            assert(len(result6.artistToken) > 0)
            assert(len(result6.imageList) > 0)

        def testMemberBookmark():
            print("Test member bookmarks mode")
            print(">>")
            (result5, page5) = b.getMemberPage(
                1227869, page=1, bookmark=True, tags=None)
            print(result5.PrintInfo())
            assert(len(result5.artistToken) > 0)
            assert(len(result5.imageList) > 0)
            print(">>")
            (result6, page6) = b.getMemberPage(
                1227869, page=2, bookmark=True, tags=None)
            print(result6.PrintInfo())
            assert(len(result6.artistToken) > 0)
            assert(len(result6.imageList) > 0)
            print(">>")
            (result6, page6) = b.getMemberPage(
                1227869, page=10, bookmark=True, tags=None)
            if result6 is not None:
                print(result6.PrintInfo())
            (result6, page6) = b.getMemberPage(
                1227869, page=12, bookmark=True, tags=None)
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
