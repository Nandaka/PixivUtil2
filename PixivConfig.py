#!/usr/bin/python
# -*- coding: UTF-8 -*-

import ConfigParser
import sys
import os
import traceback

class PixivConfig:
    '''Configuration class'''

    #default value
    proxyAddress = ''
    proxy = {'http': proxyAddress}
    useProxy = False

    username = ''
    password = ''

    useragent = 'Mozilla/5.0 (X11; U; Unix i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1'
    debugHttp = False

    numberOfPage = 0
    useRobots = True
    filenameFormat = '%artist% (%member_id%)\\%image_id% - %title%'
    rootDirectory = ''
    overwrite = False
    timeout = 60

    useList = False
    processFromDb = True
    dayLastUpdated = 7

    tagsSeparator = ', '

    retry = 3
    retryWait = 5

    alwaysCheckFileSize = True
    checkUpdatedLimit = 0

    cookie = ''
    
    #Yavos: added next three lines
    createDownloadLists = False
    downloadListDirectory = '..'
    startIrfanView = False
    startIrfanSlide = False
    IrfanViewPath = 'C:\Program Files\IrfanView'
    
    def loadConfig(self):
        print 'Reading config file...',
        oldSetting = False
        
        config = ConfigParser.RawConfigParser()
        try:
            config.read('config.ini')

            self.username = config.get('Authentication','username')
        
            self.password = config.get('Authentication','password')

            self.cookie = config.get('Authentication','cookie')

            self.tagsSeparator = config.get('Settings','tagsseparator')
            self.rootDirectory = config.get('Settings','rootdirectory')
            
            try:
                self.IrfanViewPath = config.get('Settings','IrfanViewPath')
                self.downloadListDirectory = config.get('Settings','downloadListDirectory')
            except:
                self.rootDirectory = ''

            try:
                self.processFromDb = config.getboolean('Settings','processfromdb')
            except ValueError:
                self.processFromDb = True

            try:
                self.dayLastUpdated = config.getint('Settings','daylastupdated')
            except ValueError:
                self.dayLastUpdated = 7

            try:
                self.proxyAddress = config.get('Settings','proxyaddress')
            except ValueError:
                self.proxyAddress = ''
            self.proxy = {'http': self.proxyAddress}
            
            try:
                self.useProxy = config.getboolean('Settings','useproxy')
            except ValueError:
                self.useProxy = False
                
            try:
                self.useList = config.getboolean('Settings','uselist')
            except ValueError:
                self.useList = False
                
            _useragent = config.get('Settings','useragent')
            if _useragent != None:
                self.useragent = _useragent

            _filenameFormat = config.get('Settings','filenameformat')
            if _filenameFormat != None:
                self.filenameFormat = _filenameFormat
            
            try:
                self.debugHttp = config.getboolean('Settings','debughttp')
            except ValueError:
                self.debugHttp = False
                
            try:
                self.useRobots = config.getboolean('Settings','userobots')
            except ValueError:
                self.useRobots = False

            try:
                self.overwrite = config.getboolean('Settings','overwrite')
            except ValueError:
                self.overwrite = False

            try:
                self.timeout = config.getint('Settings','timeout')
            except ValueError:
                self.timeout = 60
                
            try:
                self.retry = config.getint('Settings','retry')
            except ValueError:
                self.retry = 3

            try:
                self.retryWait = config.getint('Settings','retrywait')
            except ValueError:
                self.retryWait = 5
                
            try:
                self.numberOfPage = config.getint('Pixiv','numberofpage')
            except ValueError:
                self.numberOfPage = 0
                
            try:
                self.createDownloadLists = config.getboolean('Settings','createDownloadLists')
            except ValueError:
                self.createDownloadLists = False
                
            try:
                self.startIrfanView = config.getboolean('Settings','startIrfanView')
            except ValueError:
                self.startIrfanView = False
                
            try:
                self.startIrfanSlide = config.getboolean('Settings','startIrfanSlide')
            except ValueError:
                self.startIrfanSlide = False

            try:
                self.alwaysCheckFileSize = config.getboolean('Settings','alwaysCheckFileSize')
            except ValueError:
                self.alwaysCheckFileSize = False
                
            try:
                self.checkUpdatedLimit = config.getint('Settings','checkUpdatedLimit')
            except ValueError:
                self.checkUpdatedLimit = 0
            
        except ConfigParser.NoOptionError:
            print 'Error at loadConfig():',sys.exc_info()
            print 'Failed to read configuration.'
            self.writeConfig()
        except ConfigParser.NoSectionError:
            print 'Error at loadConfig():',sys.exc_info()
            print 'Failed to read configuration.'
            self.writeConfig()
            
        print 'done.'


    #-UI01B------write config
    def writeConfig(self):
        print 'Writing config file...',
        config = ConfigParser.RawConfigParser()
        config.add_section('Settings')
        config.add_section('Pixiv')
        config.add_section('Authentication')

        config.set('Settings', 'proxyAddress',self.proxyAddress)
        config.set('Settings', 'useProxy', self.useProxy)
        config.set('Settings', 'useragent', self.useragent)
        config.set('Settings', 'debugHttp', self.debugHttp)
        config.set('Settings', 'useRobots', self.useRobots)
        config.set('Settings', 'filenameFormat', self.filenameFormat)
        config.set('Settings', 'timeout', self.timeout)
        config.set('Settings', 'useList', self.useList)
        config.set('Settings', 'processFromDb', self.processFromDb)
        config.set('Settings', 'overwrite', self.overwrite)
        config.set('Settings', 'tagsseparator', self.tagsSeparator)
        config.set('Settings', 'daylastupdated',self.dayLastUpdated)
        config.set('Settings', 'rootdirectory', self.rootDirectory)
        config.set('Settings', 'retry', self.retry)
        config.set('Settings', 'retrywait', self.retryWait)
        config.set('Settings', 'createDownloadLists', self.createDownloadLists)
        config.set('Settings', 'downloadListDirectory', self.downloadListDirectory)
        config.set('Settings', 'IrfanViewPath', self.IrfanViewPath)
        config.set('Settings', 'startIrfanView', self.startIrfanView)
        config.set('Settings', 'startIrfanSlide', self.startIrfanSlide)
        config.set('Settings', 'alwaysCheckFileSize', self.alwaysCheckFileSize)
        config.set('Settings', 'checkUpdatedLimit', self.checkUpdatedLimit)
        
        config.set('Authentication', 'username', self.username)
        config.set('Authentication', 'password', self.password)
        config.set('Authentication', 'cookie', self.cookie)
        
        config.set('Pixiv', 'numberOfPage', self.numberOfPage)
        
        with open('config.ini', 'wb') as configfile:
            config.write(configfile)
            
        print 'done.'

    def printConfig(self):
        print 'Configuration: '
        print ' [Authentication]'
        print ' - username    =', self.username
        print ' - password    = ', self.password
        print ' - cookie      = ', self.cookie
        
        print ' [Settings]'
        print ' - filename_format =', self.filenameFormat
        print ' - useproxy  =' , self.useProxy
        print ' - proxyaddress =', self.proxyAddress
        print ' - debug_http =', self.debugHttp
        print ' - use_robots =', self.useRobots
        print ' - useragent  =', self.useragent
        print ' - overwrite =', self.overwrite
        print ' - timeout   =', self.timeout
        print ' - useList   =', self.useList
        print ' - processFromDb  =', self.processFromDb
        print ' - tagsSeparator  =', self.tagsSeparator
        print ' - dayLastUpdated =', self.dayLastUpdated
        print ' - rootDirectory  =', self.rootDirectory
        print ' - retry  =', self.retry
        print ' - retryWait =', self.retryWait
        print ' - createDownloadLists =', self.createDownloadLists
        print ' - downloadListDirectory =', self.downloadListDirectory
        print ' - IrfanViewPath =', self.IrfanViewPath
        print ' - startIrfanView =', self.startIrfanView
        print ' - startIrfanSlide =', self.startIrfanSlide
        print ' - alwaysCheckFileSize =', self.alwaysCheckFileSize
        print ' - checkUpdatedLimit =', self.checkUpdatedLimit
        
        print ' [Pixiv]'
        print ' - number_of_page =', self.numberOfPage
        
