# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

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

import PixivHelper
from PixivException import PixivException
import PixivConstant
import PixivModelWhiteCube

defaultCookieJar = None
defaultConfig = None
_browser = None

class PixivBrowser(mechanize.Browser):
    _config = None
    _isWhitecube = False
    _whitecubeToken = ""

    def __init__(self, config, cookieJar):
        mechanize.Browser.__init__(self, factory=mechanize.RobustFactory())
        self._configureBrowser(config)
        self._configureCookie(cookieJar)


    def _configureBrowser(self, config):
        if config == None:
            PixivHelper.GetLogger().info("No config given")
            return

        global defaultConfig
        if defaultConfig == None:
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

                PixivHelper.GetLogger().info("Using SOCKS Proxy: " + config.proxyAddress)
            else:
                self.set_proxies(config.proxy)
                PixivHelper.GetLogger().info("Using Proxy: " + config.proxyAddress)

        #self.set_handle_equiv(True)
        #self.set_handle_gzip(True)
        self.set_handle_redirect(True)
        self.set_handle_referer(True)
        self.set_handle_robots(False)

        self.set_debug_http(config.debugHttp)
        if config.debugHttp :
            PixivHelper.GetLogger().info('Debug HTTP enabled.')

        # self.visit_response
        self.addheaders = [('User-agent', config.useragent)]

        socket.setdefaulttimeout(config.timeout)


    def _configureCookie(self, cookieJar):
        if cookieJar != None:
            self.set_cookiejar(cookieJar)

            global defaultCookieJar
            if defaultCookieJar == None:
                defaultCookieJar = cookieJar


    def addCookie(self, cookie):
        global defaultCookieJar
        if defaultCookieJar == None:
            defaultCookieJar = cookielib.LWPCookieJar()
        defaultCookieJar.set_cookie(cookie)


    def getPixivPage(self, url, referer="http://www.pixiv.net"):
        ''' get page from pixiv and return as parsed BeautifulSoup object

            throw PixivException as server error
        '''
        url = self.fixUrl(url)
        retry_count = 0
        while True:
            req = urllib2.Request(url)
            req.add_header('Referer', referer)
            try:
                page = self.open(req)
                parsedPage = BeautifulSoup(page.read())
                return parsedPage
            except Exception as ex:
                if isinstance(ex, urllib2.HTTPError):
                    if ex.code in [403, 404, 503]:
                        return BeautifulSoup(ex.read())

                if retry_count < self._config.retry:
                    for t in range(1, self._config.retryWait):
                        print t,
                        time.sleep(1)
                    print ''
                    retry_count = retry_count + 1
                else:
                    raise PixivException("Failed to get page: " + ex.message, errorCode = PixivException.SERVER_ERROR)


    def fixUrl(self, url, useHttps=False):
        ## url = str(url)
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
        init_config = page.find('input', attrs={'id':'init-config'})
        js_init_config = json.loads(init_config['value'])
        return js_init_config


##    def _makeRequest(self, url):
##        if self._config.useProxy:
##            proxy = urllib2.ProxyHandler(self._config.proxy)
##            opener = urllib2.build_opener(proxy)
##            urllib2.install_opener(opener)
##        req = urllib2.Request(url)
##        return req


    def loginUsingCookie(self, loginCookie=None):
        """  Log in to Pixiv using saved cookie, return True if success """

        if loginCookie is None or len(loginCookie) == 0:
            loginCookie = self._config.cookie

        if len(loginCookie) > 0:
            PixivHelper.printAndLog('info', 'Trying to log with saved cookie')
            self._loadCookie(loginCookie)
            res = self.open('http://www.pixiv.net/mypage.php')
            resData = res.read()

            parsed = BeautifulSoup(resData)
            self.detectWhiteCube(parsed, res.geturl())

            if "logout.php" in resData:
                PixivHelper.printAndLog('info', 'Login successfull.')
                PixivHelper.GetLogger().info('Logged in using cookie')
                return True
            else:
                PixivHelper.GetLogger().info('Failed to login using cookie')
                PixivHelper.printAndLog('info', 'Cookie already expired/invalid.')
        return False


    def login(self, username, password):
        try:
            PixivHelper.printAndLog('info', 'Logging in...')
            url = "https://accounts.pixiv.net/login"
            page = self.open(url)

            # get the post key
            parsed = BeautifulSoup(page)
            js_init_config = self._getInitConfig(parsed)

            data = {}
            data['pixiv_id'] = username
            data['password'] = password
            #data['captcha'] = ''
            #data['g_recaptcha_response'] = ''
            data['return_to'] = 'http://www.pixiv.net'
            data['lang'] = 'en'
            data['post_key'] = js_init_config["pixivAccount.postKey"]
            data['source'] = "pc"

            request = urllib2.Request("https://accounts.pixiv.net/api/login?lang=en", urllib.urlencode(data))
            response = self.open(request)

            return self.processLoginResult(response)
        except:
            PixivHelper.printAndLog('error', 'Error at login(): ' + str(sys.exc_info()))
            raise

    def processLoginResult(self, response):
        PixivHelper.GetLogger().info('Logging in, return url: ' + response.geturl())

        # check the returned json
        js = response.read()
        PixivHelper.GetLogger().info(str(js))
        result = json.loads(js)
        if result["body"] is not None and result["body"].has_key("successed"):
            for cookie in self._ua_handlers['_cookies'].cookiejar:
                if cookie.name == 'PHPSESSID':
                    PixivHelper.printAndLog('info', 'new cookie value: ' + str(cookie.value))
                    self._config.cookie = cookie.value
                    self._config.writeConfig(path=self._config.configFileLocation)
                    break

            # check whitecube
            page = self.open(result["body"]["successed"]["return_to"])
            parsed = BeautifulSoup(page)
            self.detectWhiteCube(parsed, page.geturl())

            return True
        else :
            if result["body"] is not None and result["body"].has_key("validation_errors"):
                PixivHelper.printAndLog('info', "Server reply: " + str(result["body"]["validation_errors"]))
            else:
                PixivHelper.printAndLog('info', 'Unknown login issue, please use cookie login method.')
            return False

    def detectWhiteCube(self, page, url):
        if url.find("pixiv.net/whitecube") > 0:
            print "*******************************************"
            print "* Pixiv whitecube UI mode.                *"
            print "* Some feature might not working properly *"
            print "*******************************************"
            js_init = self._getInitConfig(page)
            self._whitecubeToken = js_init["pixiv.context.token"]
            print "whitecube token:", self._whitecubeToken
            self._isWhitecube = True

    def parseLoginError(self, res):
        page = BeautifulSoup(res.read())
        r = page.findAll('span', attrs={'class': 'error'})
        return r

    def getImagePage(self, imageId, parent=None, fromBookmark=False,
                     bookmark_count=-1, image_response_count=-1):
        image = None
        PixivHelper.GetLogger().debug("Getting image page: {0}".format(imageId))
        if self._isWhitecube:
            url = "https://www.pixiv.net/rpc/whitecube/index.php?mode=work_details_modal_whitecube&id={0}&tt={1}".format(imageId, self._whitecubeToken)
            response = self.open(url).read()
            image = PixivModelWhiteCube.PixivImage(imageId,
                                                   response,
                                                   parent,
                                                   fromBookmark,
                                                   bookmark_count,
                                                   image_response_count,
                                                   dateFormat=self._config.dateFormat)
        else:
            url = "http://www.pixiv.net/member_illust.php?mode=medium&illust_id={0}".format(image_id)
            parsed = BeautifulSoup(response)
            image = PixivModel.PixivImage(imageId,
                                          parsed,
                                          parent,
                                          fromBookmark,
                                          bookmark_count,
                                          image_response_count,
                                          dateFormat=self._config.dateFormat)
            if image.imageMode == "ugoira_view" or image.imageMode == "bigNew":
                image.ParseImages(page=response)
            parsed.decompose()

        return (image, response)


def getBrowser(config = None, cookieJar = None):
    global defaultCookieJar
    global defaultConfig
    global _browser

    if _browser is None:
        if config != None:
            defaultConfig = config
        if cookieJar != None:
            defaultCookieJar = cookieJar
        if defaultCookieJar == None:
            PixivHelper.GetLogger().info("No default cookie jar available, creating... ")
            defaultCookieJar = cookielib.LWPCookieJar()
        _browser = PixivBrowser(defaultConfig, defaultCookieJar)

    return _browser


def getExistingBrowser():
    global _browser
    if _browser is None:
        raise PixivException("Browser is not initialized yet!", errorCode = PixivException.NOT_LOGGED_IN)
    return _browser


def test():
    from PixivConfig import PixivConfig
    cfg = PixivConfig()
    cfg.loadConfig("./config.ini")
    b = getBrowser(cfg, None)
    success = b.login(cfg.username, cfg.password)
    if success:
        (result, parsed) = b.getImagePage(59513189)
        print result.PrintInfo()

        (result, parsed) = b.getImagePage(59532028)
        print result.PrintInfo()

if __name__ == '__main__':
    test()