# -*- coding: utf-8 -*-
# pylint: disable=W0603, C0325

import http.client
import http.cookiejar
import json
import re
import socket
import sys
import time
import traceback
import urllib
from typing import Union, Tuple

import demjson
import mechanize
import socks
from bs4 import BeautifulSoup

import PixivHelper
from PixivArtist import PixivArtist
from PixivException import PixivException
from PixivImage import PixivImage, PixivMangaSeries
from PixivModelFanbox import FanboxArtist, FanboxPost
from PixivModelSketch import SketchArtist, SketchPost
from PixivOAuth import PixivOAuth
from PixivTags import PixivTags
from PixivNovel import NovelSeries, PixivNovel, MAX_LIMIT

defaultCookieJar = None
defaultConfig = None
_browser = None


# pylint: disable=E1101
class PixivBrowser(mechanize.Browser):
    _config = None
    _cache = dict()
    _max_cache = 10000  # keep n-item in memory
    _myId = 0
    _isPremium = False

    _username = None
    _password = None

    _locale = ""

    _is_logged_in_to_FANBOX = False
    _orig_getaddrinfo = None

    __oauth_manager = None

    @property
    def _oauth_manager(self):
        if self.__oauth_manager is None:
            proxy = None
            if self._config.useProxy:
                proxy = self._config.proxy
            if self._config is not None:
                if self._username is None:
                    self._username = self._config.username
                if self._password is None:
                    self._password = self._config.password
            self.__oauth_manager = PixivOAuth(self._username,
                                              self._password,
                                              proxies=proxy,
                                              refresh_token=self._config.refresh_token,
                                              validate_ssl=self._config.enableSSLVerification)
        return self.__oauth_manager

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

    def getaddrinfo(self, *args):
        try:
            return self._orig_getaddrinfo(*args)
        except socket.gaierror:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (args[0], args[1]))]

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

                # https://github.com/Nandaka/PixivUtil2/issues/592#issuecomment-659516296
                if self._orig_getaddrinfo is None:
                    self._orig_getaddrinfo = socket.getaddrinfo
                socket.getaddrinfo = self._orig_getaddrinfo

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
        self.addheaders += [('Accept-Charset', 'utf-8')]

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

                    PixivHelper.print_and_log('error', f'Error at open_with_retry(): {sys.exc_info()}')
                    raise PixivException(f"Failed to get page: {temp}, please check your internet connection/firewall/antivirus.",
                                         errorCode=PixivException.SERVER_ERROR)

    def getPixivPage(self, url, referer="https://www.pixiv.net", returnParsed=True, enable_cache=True) -> Union[str, BeautifulSoup]:
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
                        raise PixivException(f"Failed to get page: {url} => {ex}", errorCode=PixivException.SERVER_ERROR)
                    else:
                        PixivHelper.print_and_log('error', f'Error at getPixivPage(): {sys.exc_info()}')
                        raise PixivException(f"Failed to get page: {url}", errorCode=PixivException.SERVER_ERROR)

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

    def _loadCookie(self, cookie_value, domain):
        """ Load cookie to the Browser instance """
        ck = None

        if "pixiv.net" in domain:
            ck = http.cookiejar.Cookie(version=0, name='PHPSESSID', value=cookie_value, port=None,
                                       port_specified=False, domain='pixiv.net', domain_specified=False,
                                       domain_initial_dot=False, path='/', path_specified=True,
                                       secure=False, expires=None, discard=True, comment=None,
                                       comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
        elif "fanbox.cc" in domain:
            ck = http.cookiejar.Cookie(version=0, name='FANBOXSESSID', value=cookie_value, port=None,
                                       port_specified=False, domain='fanbox.cc', domain_specified=False,
                                       domain_initial_dot=False, path='/', path_specified=True,
                                       secure=False, expires=None, discard=True, comment=None,
                                       comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
        if ck is not None:
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
        result = False

        if login_cookie is None or len(login_cookie) == 0:
            login_cookie = self._config.cookie

        if len(login_cookie) > 0:
            PixivHelper.print_and_log('info', 'Trying to log in with saved cookie')
            self.clearCookie()
            self._loadCookie(login_cookie, "pixiv.net")
            res = self.open_with_retry('https://www.pixiv.net/')
            parsed = BeautifulSoup(res, features="html5lib").decode('utf-8')
            PixivHelper.get_logger().info('Logging in, return url: %s', res.geturl())
            res.close()

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

    def fanboxLoginUsingCookie(self, login_cookie=None):
        """  Log in to Pixiv using saved cookie, return True if success """
        result = False
        parsed = ""
        if login_cookie is None or len(login_cookie) == 0:
            login_cookie = self._config.cookieFanbox

        if len(login_cookie) > 0:
            PixivHelper.print_and_log('info', 'Trying to log in FANBOX with saved cookie')
            # self.clearCookie()
            self._loadCookie(login_cookie, "fanbox.cc")

            req = mechanize.Request("https://www.fanbox.cc")
            req.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
            req.add_header('Origin', 'https://www.fanbox.cc')
            req.add_header('User-Agent', self._config.useragent)
            try:
                res = self.open_with_retry(req)
                parsed = BeautifulSoup(res, features="html5lib").decode('utf-8')
                PixivHelper.get_logger().info('Logging in with cookit to Fanbox, return url: %s', res.geturl())
                res.close()
            except BaseException:
                PixivHelper.get_logger().error('Error at fanboxLoginUsingCookie(): %s', sys.exc_info())
                self.cookiejar.clear("fanbox.cc")

            if '"user":{"isLoggedIn":true' in str(parsed):
                result = True
                self._is_logged_in_to_FANBOX = True
            del parsed

        if result:
            PixivHelper.print_and_log('info', 'FANBOX Login successful.')
        else:
            PixivHelper.print_and_log('info', 'Not logged in to FANBOX, trying to update FANBOX cookie...')
            result = self.updateFanboxCookie()
            self._is_logged_in_to_FANBOX = result

        return result

    def fanbox_is_logged_in(self):
        if not self._is_logged_in_to_FANBOX:
            if not self.fanboxLoginUsingCookie(self._config.cookieFanbox):
                raise Exception("Not logged in to FANBOX")

    def updateFanboxCookie(self):
        p_req = mechanize.Request("https://www.fanbox.cc/auth/start")
        p_req.add_header('Accept', 'application/json, text/plain, */*')
        p_req.add_header('Origin', 'https://www.pixiv.net')
        p_req.add_header('User-Agent', self._config.useragent)

        try:
            p_res = self.open_with_retry(p_req)
            parsed = BeautifulSoup(p_res, features="html5lib").decode('utf-8')
            p_res.close()
        except BaseException:
            PixivHelper.get_logger().error('Error at updateFanboxCookie(): %s', sys.exc_info())
            return False

        result = False
        if '"user":{"isLoggedIn":true' in str(parsed):
            result = True
            self._is_logged_in_to_FANBOX = True
        del parsed

        if result:
            for cookie in self._ua_handlers['_cookies'].cookiejar:
                if cookie.name == 'FANBOXSESSID':
                    PixivHelper.print_and_log(
                        'info', 'New FANBOX cookie value: ' + str(cookie.value))
                    self._config.cookieFanbox = cookie.value
                    self._config.writeConfig(
                        path=self._config.configFileLocation)
                    break
        else:
            PixivHelper.print_and_log('info', 'Could not update FANBOX cookie string.')
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
            PixivHelper.print_and_log('error', f'Error at login(): {sys.exc_info()}')
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
            PixivHelper.print_and_log('error', 'Unable to get User Id, please check your cookie.')
            PixivHelper.print_and_log('error', 'Please follow the instruction in https://github.com/Nandaka/PixivUtil2/issues/814#issuecomment-711182644')
            raise PixivException("Unable to get User Id, please check your cookie.", errorCode=PixivException.NOT_LOGGED_IN, htmlPage=parsed)

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
        PixivHelper.print_and_log('info', f'Premium User: {self._isPremium}.')

    def parseLoginError(self, res):
        page = BeautifulSoup(res, features="html5lib")
        r = page.findAll('span', attrs={'class': 'error'})
        page.decompose()
        del page
        return r

    def getImagePage(self,
                     image_id,
                     parent=None,
                     from_bookmark=False,
                     bookmark_count=-1,
                     image_response_count=-1,
                     manga_series_order=-1,
                     manga_series_parent=None) -> Tuple[PixivImage, str]:
        image = None
        response = None
        PixivHelper.get_logger().debug("Getting image page: %s", image_id)
        # https://www.pixiv.net/en/artworks/76656661
        url = f"https://www.pixiv.net{self._locale}/artworks/{image_id}"
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
                                   tzInfo=_tzInfo,
                                   manga_series_order=manga_series_order,
                                   manga_series_parent=manga_series_parent,
                                   writeRawJSON=self._config.writeRawJSON)

                if image.imageMode == "ugoira_view":
                    ugoira_meta_url = f"https://www.pixiv.net/ajax/illust/{image_id}/ugoira_meta"
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
                dump_filename = f"Medium Page for Image Id {imageId}.html"
                PixivHelper.dump_html(dump_filename, response)
                PixivHelper.print_and_log('info', f'Dumping html to: {dump_filename}')
            if self._config.debugHttp:
                PixivHelper.safePrint(f"reply: {response}")

    def getMemberInfoWhitecube(self, member_id, artist, bookmark=False):
        ''' get artist information using Ajax and AppAPI '''
        try:
            info = None
            if int(artist.reference_image_id) > 0:
                url = f"https://www.pixiv.net/rpc/get_work.php?id={artist.reference_image_id}"
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
                PixivHelper.print_and_log('info', f'Using OAuth to retrieve member info for: {member_id}')
                if self._username is None or self._password is None or len(self._username) < 0 or len(self._password) < 0:
                    raise PixivException("Empty Username or Password, remove cookie value and relogin, or add username/password to config.ini.")

                url = f'https://app-api.pixiv.net/v1/user/detail?user_id={member_id}'
                info = self._get_from_cache(url)
                if info is None:
                    PixivHelper.get_logger().debug("Getting member information: %s", member_id)
                    login_response = self._oauth_manager.login()
                    if login_response.status_code == 200:
                        info = json.loads(login_response.text)
                        if self._config.refresh_token != info["response"]["refresh_token"]:
                            PixivHelper.print_and_log('info', 'OAuth Refresh Token is updated, updating config.ini')
                            self._config.refresh_token = info["response"]["refresh_token"]
                            self._config.writeConfig(path=self._config.configFileLocation)

                    response = self._oauth_manager.get_user_info(member_id)
                    info = json.loads(response.text)
                    self._put_to_cache(url, info)
                    PixivHelper.get_logger().debug("reply: %s", response.text)

            artist.ParseInfo(info, False, bookmark=bookmark)

            # will throw HTTPError if user is suspended/not logged in.
            url_ajax = f'https://www.pixiv.net/ajax/user/{member_id}'
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
            msg = None
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

    def getMemberPage(self, member_id, page=1, bookmark=False, tags=None, r18mode=False) -> Tuple[PixivArtist, str]:
        artist = None
        response = None
        if tags is None:
            tags = ''

        limit = 48
        offset = (page - 1) * limit
        need_to_slice = False
        if bookmark:
            # https://www.pixiv.net/ajax/user/1039353/illusts/bookmarks?tag=&offset=0&limit=24&rest=show
            url = f'https://www.pixiv.net/ajax/user/{member_id}/illusts/bookmarks?tag={tags}&offset={offset}&limit={limit}&rest=show'
        else:
            # https://www.pixiv.net/ajax/user/1813972/illusts/tag?tag=Fate%2FGrandOrder?offset=0&limit=24
            # https://www.pixiv.net/ajax/user/1813972/manga/tag?tag=%E3%83%A1%E3%82%A4%E3%82%AD%E3%83%B3%E3%82%B0?offset=0&limit=24
            # https://www.pixiv.net/ajax/user/5238/illustmanga/tag?tag=R-18&offset=0&limit=48
            # https://www.pixiv.net/ajax/user/1813972/profile/all
            url = None
            if len(tags) > 0:  # called from Download by tags
                url = f'https://www.pixiv.net/ajax/user/{member_id}/illustmanga/tag?tag={tags}&offset={offset}&limit={limit}'
            elif r18mode:
                url = f'https://www.pixiv.net/ajax/user/{member_id}/illustmanga/tag?tag=R-18&offset={offset}&limit={limit}'
            else:
                url = f'https://www.pixiv.net/ajax/user/{member_id}/profile/all'
                need_to_slice = True

            PixivHelper.print_and_log('info', f'Member Url: {url}')

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

            # fix issue with member with 0 images, skip everything.
            if len(artist.imageList) == 0:
                raise PixivException(f"No images for Member Id:{member_id}, from Bookmark: {bookmark}", errorCode=PixivException.NO_IMAGES, htmlPage=response)

            artist.reference_image_id = artist.imageList[0] if len(artist.imageList) > 0 else 0
            self.getMemberInfoWhitecube(member_id, artist, bookmark)

            if artist.haveImages and need_to_slice:
                artist.imageList = artist.imageList[offset:offset + limit]

        return (artist, response)

    def getSearchTagPage(self,
                         tags,
                         current_page,
                         wild_card=True,
                         title_caption=False,
                         start_date=None,
                         end_date=None,
                         member_id=None,
                         sort_order='date_d',
                         start_page=1,
                         use_bookmark_data=False,
                         bookmark_count=0,
                         type_mode="a",
                         r18mode=False) -> Tuple[PixivTags, str]:
        response_page = None
        result = None
        url = ''

        if member_id is not None:
            # from member id search by tags
            (artist, response_page) = self.getMemberPage(member_id, current_page, False, tags, r18mode=r18mode)

            # convert to PixivTags
            result = PixivTags()
            result.parseMemberTags(artist, member_id, tags)
        else:
            # only premium support server-side filtering for bookmark count
            if not self._isPremium:
                bookmark_count = 0

            # search by tags
            url = PixivHelper.generate_search_tag_url(tags,
                                                      current_page,
                                                      title_caption=title_caption,
                                                      wild_card=wild_card,
                                                      sort_order=sort_order,
                                                      start_date=start_date,
                                                      end_date=end_date,
                                                      member_id=member_id,
                                                      r18mode=r18mode,
                                                      blt=bookmark_count,
                                                      type_mode=type_mode)

            PixivHelper.print_and_log('info', f'Looping... for {url}')
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
                    if use_bookmark_data:
                        idx = 0
                        print("Retrieving bookmark information...", end=' ')
                        for image in result.itemList:
                            idx = idx + 1
                            print("\r", end=' ')
                            print(f"Retrieving bookmark information... [{idx}] of [{len(result.itemList)}]", end=' ')

                            img_url = f"https://www.pixiv.net/ajax/illust/{image.imageId}"
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
                    PixivHelper.dump_html(f"Dump for SearchTags {tags}.html", response_page)
                    raise

        return (result, response_page)

    def handleDebugTagSearchPage(self, response, url):
        if self._config.enableDump:
            if self._config.dumpTagSearchPage:
                dump_filename = f"TagSearch Page for {url}.html"
                PixivHelper.dump_html(dump_filename, response)
                PixivHelper.print_and_log('info', f'Dumping html to: {dump_filename}')
            if self._config.debugHttp:
                PixivHelper.safePrint(f"reply: {response}")

    def fanboxGetArtistList(self, via):
        self.fanbox_is_logged_in()
        url = None
        referer = ""
        if via == FanboxArtist.SUPPORTING:
            url = 'https://api.fanbox.cc/plan.listSupporting'
            PixivHelper.print_and_log('info', f'Getting supporting artists from {url}')
            referer = "https://www.fanbox.cc/creators/supporting"
        elif via == FanboxArtist.FOLLOWING:
            url = 'https://api.fanbox.cc/creator.listFollowing'
            PixivHelper.print_and_log('info', f'Getting following artists from {url}')
            referer = "https://www.fanbox.cc/creators/following"

        if url is not None:
            req = mechanize.Request(url)
            req.add_header('Accept', 'application/json, text/plain, */*')
            req.add_header('Referer', referer)
            req.add_header('Origin', 'https://www.fanbox.cc')
            req.add_header('User-Agent', self._config.useragent)

            res = self.open_with_retry(req)
            # read the json response
            response = res.read()
            res.close()

            ids = FanboxArtist.parseArtistIds(page=response)
            return ids
        else:
            raise ValueError(f"Invalid via argument {via}")

    def fanboxGetArtistById(self, artist_id, for_suspended=False):
        self.fanbox_is_logged_in()
        if re.match(r"^\d+$", artist_id):
            id_type = "userId"
        else:
            id_type = "creatorId"

        url = f'https://api.fanbox.cc/creator.get?{id_type}={artist_id}'
        PixivHelper.print_and_log('info', f'Getting artist information from {url}')
        referer = "https://www.fanbox.cc"
        if id_type == "creatorId":
            referer += f"/@{artist_id}"

        req = mechanize.Request(url)
        req.add_header('Accept', 'application/json, text/plain, */*')
        req.add_header('Referer', referer)
        req.add_header('Origin', 'https://www.fanbox.cc')
        req.add_header('User-Agent', self._config.useragent)

        res = self.open_with_retry(req)
        # read the json response
        response = res.read()
        res.close()
        _tzInfo = None
        if self._config.useLocalTimezone:
            _tzInfo = PixivHelper.LocalUTCOffsetTimezone()

        js = demjson.decode(response)
        if "error" in js and js["error"]:
            raise PixivException("Error when requesting Fanbox", 9999, js)

        if "body" in js and js["body"] is not None:
            js_body = js["body"]
            artist = FanboxArtist(js_body["user"]["userId"],
                                  js_body["user"]["name"],
                                  js_body["creatorId"],
                                  tzInfo=_tzInfo)

            if not for_suspended:
                # pixivArtist = PixivArtist(artist.artistId)
                # self.getMemberInfoWhitecube(artist.artistId, pixivArtist)
                # Issue #827, less efficient call, but it can avoid oAuth issue
                (pixivArtist, _) = self.getMemberPage(artist.artistId)

                artist.artistName = pixivArtist.artistName
                artist.artistToken = pixivArtist.artistToken
            return artist
        else:
            raise PixivException("Id does not exist", errorCode=PixivException.USER_ID_NOT_EXISTS)

    def fanboxGetPostsFromArtist(self, artist=None, next_url=""):
        ''' get all posts from the supported user
        from https://fanbox.pixiv.net/api/post.listCreator?userId=1305019&limit=10 '''
        self.fanbox_is_logged_in()

        # Issue #641
        if next_url is None or next_url == "":
            url = f"https://api.fanbox.cc/post.listCreator?userId={artist.artistId}&limit=10"
        elif next_url.startswith("https://"):
            url = next_url
        else:
            url = "https://www.fanbox.cc" + next_url

        # Fix #494
        PixivHelper.print_and_log('info', 'Getting posts from ' + url)
        referer = f"https://www.fanbox.cc/@{artist.creatorId}"
        req = mechanize.Request(url)
        req.add_header('Accept', 'application/json, text/plain, */*')
        req.add_header('Referer', referer)
        req.add_header('Origin', 'https://www.fanbox.cc')
        req.add_header('User-Agent', self._config.useragent)

        res = self.open_with_retry(req)
        response = res.read()
        PixivHelper.get_logger().debug(response.decode('utf8'))
        res.close()
        posts = artist.parsePosts(response)
        return posts

    def fanboxUpdatePost(self, post):
        js = self.fanboxGetPostJsonById(post.imageId, post.parent)
        post.parsePost(js["body"])

    def fanboxGetPostById(self, post_id):
        js = self.fanboxGetPostJsonById(post_id)
        _tzInfo = None
        if self._config.useLocalTimezone:
            _tzInfo = PixivHelper.LocalUTCOffsetTimezone()
        artist = self.fanboxGetArtistById(js["body"]["user"]["userId"])
        post = FanboxPost(post_id, artist, js["body"], _tzInfo)
        return post

    def fanboxGetPostJsonById(self, post_id, artist=None):
        self.fanbox_is_logged_in()
        # https://fanbox.pixiv.net/api/post.info?postId=279561
        # https://www.pixiv.net/fanbox/creator/104409/post/279561
        p_url = f"https://api.fanbox.cc/post.info?postId={post_id}"
        # referer doesn't seeem to be essential
        p_referer = f"https://www.fanbox.cc/@{artist.creatorId if artist else ''}/posts/{post_id}"
        PixivHelper.get_logger().debug('Getting post detail from %s', p_url)
        p_req = mechanize.Request(p_url)
        p_req.add_header('Accept', 'application/json, text/plain, */*')
        p_req.add_header('Referer', p_referer)
        p_req.add_header('Origin', 'https://www.fanbox.cc')
        p_req.add_header('User-Agent', self._config.useragent)

        try:
            p_res = self.open_with_retry(p_req)
        except urllib.error.HTTPError as ex:
            if ex.code in [404]:
                raise PixivException("Fanbox post not found!", PixivException.OTHER_ERROR)
            raise
        p_response = p_res.read()
        PixivHelper.get_logger().debug(p_response.decode('utf8'))
        p_res.close()
        js = demjson.decode(p_response)
        return js

    def sketch_get_post_by_post_id(self, post_id, artist=None):
        # https://sketch.pixiv.net/api/replies/1213195054130835383.json
        url = f"https://sketch.pixiv.net/api/replies/{post_id}.json"
        referer = f"https://sketch.pixiv.net/items/{post_id}"
        x_requested_with = f'https://sketch.pixiv.net/items/{post_id}'

        PixivHelper.get_logger().debug('Getting sketch post detail from %s', url)
        response = self.getPixivSketchPage(url=url, referer=referer, x_requested_with=x_requested_with)
        self.handleDebugMediumPage(response, post_id)
        _tzInfo = None
        if self._config.useLocalTimezone:
            _tzInfo = PixivHelper.LocalUTCOffsetTimezone()
        post = SketchPost(post_id, artist, response, _tzInfo, self._config.dateFormat)
        return post

    def sketch_get_posts_by_artist_id(self, artist_id, max_page=0):
        # get artist info
        # https://sketch.pixiv.net/api/users/@camori.json
        url = f"https://sketch.pixiv.net/api/users/@{artist_id}.json"
        referer = f"https://sketch.pixiv.net/@{artist_id}"
        x_requested_with = f'https://sketch.pixiv.net/@{artist_id}'

        PixivHelper.get_logger().debug('Getting sketch artist detail from %s', url)
        response = self.getPixivSketchPage(url=url, referer=referer, x_requested_with=x_requested_with)
        self.handleDebugMediumPage(response, artist_id)
        _tzInfo = None
        if self._config.useLocalTimezone:
            _tzInfo = PixivHelper.LocalUTCOffsetTimezone()
        artist = SketchArtist(artist_id, response, _tzInfo, self._config.dateFormat)

        # get artists posts
        current_page = 1
        while True:
            # https://sketch.pixiv.net/api/walls/@camori/posts/public.json
            url_posts = f"https://sketch.pixiv.net/api/walls/@{artist_id}/posts/public.json"
            if artist.next_page is not None:
                url_posts = f"https://sketch.pixiv.net{artist.next_page}"
            x_requested_with = f'https://sketch.pixiv.net/@{artist_id}'

            PixivHelper.print_and_log("info", f"Getting page {current_page} from {url_posts}")
            response_post = self.getPixivSketchPage(url=url_posts, referer=referer, x_requested_with=x_requested_with)
            self.handleDebugMediumPage(response_post, artist_id)

            PixivHelper.print_and_log("debug", f"{response_post}")
            artist.parse_posts(response_post)

            current_page = current_page + 1
            if max_page != 0 and current_page > max_page:
                break
            if artist.next_page is None:
                break

        return artist

    def getPixivSketchPage(self, url, referer, x_requested_with) -> str:
        p_req = mechanize.Request(url)
        p_req.add_header('Accept', 'application/vnd.sketch-v4+json')
        p_req.add_header('Referer', referer)
        p_req.add_header('X-Requested-With', x_requested_with)
        p_req.add_header('User-Agent', self._config.useragent)

        p_res = self.open_with_retry(p_req)
        response_post = p_res.read()
        return response_post

    def getMangaSeries(self, manga_series_id: int, current_page: int, returnJSON=False) -> Union[PixivMangaSeries, str]:
        PixivHelper.print_and_log("info", f"Getting Manga Series: {manga_series_id} from page: {current_page}")
        # get the manga information
        # https://www.pixiv.net/ajax/series/6474?p=5&lang=en
        locale = ""
        if self._locale is not None and len(self._locale) > 0:
            locale = f"&lang={self._locale}"
        url = f"https://www.pixiv.net/ajax/series/{manga_series_id}?p={current_page}{locale}"
        response = self.getPixivPage(url, returnParsed=False, enable_cache=True)
        if returnJSON:
            return response
        manga_series = PixivMangaSeries(manga_series_id, current_page, payload=response)

        # get the artist information from given manga list
        PixivHelper.print_and_log("info", f" - Fetching artist details {manga_series.member_id}")
        (artist, _) = self.getMemberPage(manga_series.member_id)
        manga_series.artist = artist

        # # get the image details from work list
        # for (image_id, order) in manga_series.pages_with_order:
        #     PixivHelper.print_and_log("info", f" - Fetching image details {image_id}")
        #     (image, _) = self.getImagePage(image_id, parent=manga_series.artist, manga_series_order=order)
        #     manga_series.images.append(image)

        return manga_series

    def getNovelPage(self, novel_id) -> PixivNovel:
        # https://www.pixiv.net/ajax/novel/14521816?lang=en
        locale = ""
        if self._locale is not None and len(self._locale) > 0:
            locale = f"&lang={self._locale}"
        url = f"https://www.pixiv.net/ajax/novel/{novel_id}?{locale}"
        response = self.getPixivPage(url, returnParsed=False, enable_cache=True)

        _tzInfo = None
        if self._config.useLocalTimezone:
            _tzInfo = PixivHelper.LocalUTCOffsetTimezone()
        novel = PixivNovel(novel_id,
                           response,
                           tzInfo=_tzInfo,
                           dateFormat=self._config.dateFormat)

        (artist, _) = self.getMemberPage(novel.artist_id)
        novel.artist = artist
        return novel

    def getNovelSeries(self, novel_series_id) -> NovelSeries:
        locale = ""
        if self._locale is not None and len(self._locale) > 0:
            locale = f"&lang={self._locale}"

        # https://www.pixiv.net/ajax/novel/series/1328575?lang=en
        url = f"https://www.pixiv.net/ajax/novel/series/{novel_series_id}?{locale}"
        response = self.getPixivPage(url, returnParsed=False, enable_cache=True)
        novel_series = NovelSeries(novel_series_id, series_json=response)
        return novel_series

    def getNovelSeriesContent(self, novel_series, limit=MAX_LIMIT, current_page=1, order_by='asc'):
        locale = ""
        if self._locale is not None and len(self._locale) > 0:
            locale = f"&lang={self._locale}"
        # https://www.pixiv.net/ajax/novel/series_content/1328575?limit=10&last_order=0&order_by=asc&lang=en
        params = list()
        params.append(f"limit={limit}")
        last_order = 10 * (current_page - 1)
        params.append(f"last_order={last_order}")
        params.append(f"order_by={order_by}")
        params_str = "&".join(params)
        novel_series_id = novel_series.series_id
        url = f"https://www.pixiv.net/ajax/novel/series_content/{novel_series_id}?{params_str}{locale}"
        response = self.getPixivPage(url, returnParsed=False, enable_cache=True)
        novel_series.parse_series_content(response, current_page)
        return novel_series


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
        raise PixivException("Browser is not initialized yet!", errorCode=PixivException.NOT_LOGGED_IN)
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
    b._oauth_manager.login()

    refresh_token = b._oauth_manager._refresh_token
    auth_token = b._oauth_manager._access_token
    print("Access Token = " + auth_token)
    print("Refresh Token = " + refresh_token)
    b._oauth_manager.login()

    if success:
        def test_oauth_get_user_info():
            member_id = 2864095
            response = b._oauth_manager.get_user_info(member_id)
            info = json.loads(response.text)
            print(info)
            print()
            member_id = 57188403
            response = b._oauth_manager.get_user_info(member_id)
            info = json.loads(response.text)
            print(info)
            print()

        def testSearchTags():
            print("test search tags")
            tags = "VOCALOID"
            p = 1
            wild_card = True
            title_caption = False
            start_date = "2016-11-06"
            end_date = "2016-11-07"
            member_id = None
            sort_order = 'date'  # oldest first
            start_page = 1
            (resultS, page) = b.getSearchTagPage(tags,
                                                 p,
                                                 wild_card=wild_card,
                                                 title_caption=title_caption,
                                                 start_date=start_date,
                                                 end_date=end_date,
                                                 member_id=member_id,
                                                 sort_order=sort_order,
                                                 start_page=start_page)
            resultS.PrintInfo()
            assert (len(resultS.itemList) > 0)
            print()

        def testImage():
            print("test image mode")
            print(">>")
            (result, page) = b.getImagePage(60040975)
            print(result.PrintInfo())
            assert (len(result.imageTitle) > 0)
            print(result.artist.PrintInfo())
            assert (len(result.artist.artistToken) > 0)
            assert ("R-18" not in result.imageTags)

            print(">>")
            (result2, page2) = b.getImagePage(59628358)
            print(result2.PrintInfo())
            assert (len(result2.imageTitle) > 0)
            print(result2.artist.PrintInfo())
            assert (len(result2.artist.artistToken) > 0)
            assert ("R-18" in result2.imageTags)

            print(">> ugoira")
            (result3, page3) = b.getImagePage(60070169)
            print(result3.PrintInfo())
            assert (len(result3.imageTitle) > 0)
            print(result3.artist.PrintInfo())
            print(result3.ugoira_data)
            assert (len(result3.artist.artistToken) > 0)
            assert (result3.imageMode == 'ugoira_view')
            print()

        def testMember():
            print("Test member mode")
            print(">>")
            (result3, page3) = b.getMemberPage(
                1227869, page=1, bookmark=False, tags=None)
            print(result3.PrintInfo())
            assert (len(result3.artistToken) > 0)
            assert (len(result3.imageList) > 0)
            print(">>")
            (result4, page4) = b.getMemberPage(
                1227869, page=2, bookmark=False, tags=None)
            print(result4.PrintInfo())
            assert (len(result4.artistToken) > 0)
            assert (len(result4.imageList) > 0)
            print(">>")
            (result5, page5) = b.getMemberPage(
                4894, page=1, bookmark=False, tags=None)
            print(result5.PrintInfo())
            assert (len(result5.artistToken) > 0)
            assert (len(result5.imageList) > 0)
            print(">>")
            (result6, page6) = b.getMemberPage(
                4894, page=3, bookmark=False, tags=None)
            print(result6.PrintInfo())
            assert (len(result6.artistToken) > 0)
            assert (len(result6.imageList) > 0)
            print()

        def testMemberBookmark():
            print("Test member bookmarks mode")
            print(">>")
            (result5, page5) = b.getMemberPage(
                1227869, page=1, bookmark=True, tags=None)
            print(result5.PrintInfo())
            assert (len(result5.artistToken) > 0)
            assert (len(result5.imageList) > 0)
            print(">>")
            (result6, page6) = b.getMemberPage(
                1227869, page=2, bookmark=True, tags=None)
            print(result6.PrintInfo())
            assert (len(result6.artistToken) > 0)
            assert (len(result6.imageList) > 0)
            print(">>")
            (result6, page6) = b.getMemberPage(
                1227869, page=10, bookmark=True, tags=None)
            if result6 is not None:
                print(result6.PrintInfo())
            (result6, page6) = b.getMemberPage(
                1227869, page=12, bookmark=True, tags=None)
            if result6 is not None:
                print(result6.PrintInfo())
                assert (len(result6.artistToken) > 0)
                assert (len(result6.imageList) == 0)
            print()

        def testFanbox():
            result = b.fanboxGetArtistList(FanboxArtist.SUPPORTING)
            print(result)
            creatorId = "powzin"
            artist = b.fanboxGetArtistById(creatorId)
            print("artist: ", artist)
            posts = b.fanboxGetPostsFromArtist(artist)
            for post in posts:
                print(post)
            print()

        def testSketch():
            # result = b.sketch_get_post_by_post_id("1213195054130835383")
            # print(result)
            result2 = b.sketch_get_posts_by_artist_id("camori")
            print(result2)
            for post in result2.posts:
                print(post)
            print()

        def testMangaSeries():
            result = b.getMangaSeries(6474, 1)
            result.print_info()
            print()

        test_oauth_get_user_info()
        testFanbox()
        # testSketch()
        # testSearchTags()
        # testImage()
        # testMember()
        # testMemberBookmark()
        # testMangaSeries()

    else:
        print("Invalid username or password")


if __name__ == '__main__':
    test()
    print("done")
