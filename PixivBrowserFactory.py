# -*- coding: UTF-8 -*-
from mechanize import Browser
import mechanize
import cookielib
import socket
import socks
import urlparse
import urllib
import urllib2
import httplib

import PixivHelper

defaultCookieJar = None
defaultConfig = None

def getBrowser(config = None, cookieJar = None):
    global defaultCookieJar
    global defaultConfig

    if config != None:
        defaultConfig = config
    if cookieJar != None:
        defaultCookieJar = cookieJar
    if defaultCookieJar == None:
        PixivHelper.GetLogger().info("No default cookie jar available, creating... ")
        defaultCookieJar = cookielib.LWPCookieJar()
    browser = Browser(factory=mechanize.RobustFactory())
    configureBrowser(browser, defaultConfig)
    configureCookie(browser, defaultCookieJar)
    return browser

def configureBrowser(browser, config):
    if config == None:
        PixivHelper.GetLogger().info("No config given")
        return

    global defaultConfig
    if defaultConfig == None:
        defaultConfig = config

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
        browser.set_proxies(config.proxy)
        PixivHelper.GetLogger().info("Using Proxy: " + config.proxyAddress)

    browser.set_handle_equiv(True)
    #browser.set_handle_gzip(True)
    browser.set_handle_redirect(True)
    browser.set_handle_referer(True)
    browser.set_handle_robots(config.useRobots)

    browser.set_debug_http(config.debugHttp)
    if config.debugHttp :
        PixivHelper.GetLogger().info('Debug HTTP enabled.')

    browser.visit_response
    browser.addheaders = [('User-agent', config.useragent)]

    socket.setdefaulttimeout(config.timeout)

def configureCookie(browser, cookieJar):
    if cookieJar != None:
        browser.set_cookiejar(cookieJar)

        global defaultCookieJar
        if defaultCookieJar == None:
            defaultCookieJar = cookieJar

def addCookie(cookie):
    global defaultCookieJar
    if defaultCookieJar == None:
        defaultCookieJar = cookielib.LWPCookieJar()
    defaultCookieJar.set_cookie(cookie)

