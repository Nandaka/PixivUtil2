# -*- coding: UTF-8 -*-
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

import PixivHelper
import PixivException

defaultCookieJar = None
defaultConfig = None
_browser = None

class PixivBrowser(mechanize.Browser):
    _config = None
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

            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, parseResult.hostname, parseResult.port)
            socks.wrapmodule(urllib)
            socks.wrapmodule(urllib2)
            socks.wrapmodule(httplib)

            PixivHelper.GetLogger().info("Using SOCKS Proxy: " + config.proxyAddress)
          else:
            self.set_proxies(config.proxy)
            PixivHelper.GetLogger().info("Using Proxy: " + config.proxyAddress)

        self.set_handle_equiv(True)
        #self.set_handle_gzip(True)
        self.set_handle_redirect(True)
        self.set_handle_referer(True)
        self.set_handle_robots(config.useRobots)

        self.set_debug_http(config.debugHttp)
        if config.debugHttp :
            PixivHelper.GetLogger().info('Debug HTTP enabled.')

        self.visit_response
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


    def getPixivPage(self, url, referer="http://www.pixiv.net", errorPageName=None):
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





