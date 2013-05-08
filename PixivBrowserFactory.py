# -*- coding: UTF-8 -*-
from mechanize import Browser
import mechanize
import cookielib
import socket
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

