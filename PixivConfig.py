#!/usr/bin/python
# -*- coding: UTF-8 -*-

import ConfigParser
import sys
import os
import codecs
import traceback
import PixivHelper
import shutil
import time

script_path = PixivHelper.module_path()

class PixivConfig:
    '''Configuration class'''
    __logger = PixivHelper.GetLogger()
    configFileLocation = "config.ini"

    ## default value
    proxyAddress = ''
    proxy = {'http': proxyAddress, 'https': proxyAddress, }
    useProxy = False

    username = ''
    password = ''

    useragent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36'
    debugHttp = False

    numberOfPage = 0
    useRobots = True
    filenameFormat = unicode('%artist% (%member_id%)' + os.sep + '%urlFilename% - %title%')
    filenameMangaFormat = unicode('%artist% (%member_id%)' + os.sep + '%urlFilename% - %title%')
    rootDirectory = unicode('.')
    overwrite = False
    timeout = 60

    useList = False
    processFromDb = True
    dayLastUpdated = 7

    tagsSeparator = unicode(', ')

    retry = 3
    retryWait = 5

    alwaysCheckFileSize = False
    checkUpdatedLimit = 0
    downloadAvatar = True

    cookie = ''
    createMangaDir = False
    useTagsAsDir = False
    useBlacklistTags = False
    useSuppressTags = False
    tagsLimit = -1
    useSSL = False
    writeImageInfo = False
    r18mode = False
    dateDiff = 0
    keepSignedIn = 0

    #Yavos: added next three lines
    createDownloadLists = False
    downloadListDirectory = unicode('.')
    startIrfanView = False
    startIrfanSlide = False
    IrfanViewPath = unicode('C:\Program Files\IrfanView')

    backupOldFile = False

    logLevel = "DEBUG"
    enableDump = True
    skipDumpFilter = ""
    dumpMediumPage = False
    writeUgoiraInfo = False

    def loadConfig(self, path=None):
        if path != None:
            self.configFileLocation = path
        else:
            self.configFileLocation = script_path + os.sep + 'config.ini'

        print 'Reading', self.configFileLocation, '...'
        oldSetting = False
        haveError = False
        config = ConfigParser.RawConfigParser()
        try:
            config.readfp(PixivHelper.OpenTextFile(self.configFileLocation))

            self.username = config.get('Authentication','username')

            self.password = config.get('Authentication','password')

            self.cookie = config.get('Authentication','cookie')

            self.tagsSeparator = PixivHelper.toUnicode(config.get('Settings','tagsseparator'), encoding=sys.stdin.encoding)
            self.rootDirectory = PixivHelper.toUnicode(config.get('Settings','rootdirectory'), encoding=sys.stdin.encoding)

            try:
                self.IrfanViewPath = PixivHelper.toUnicode(config.get('Settings','IrfanViewPath'), encoding=sys.stdin.encoding)
                self.downloadListDirectory = PixivHelper.toUnicode(config.get('Settings','downloadListDirectory'), encoding=sys.stdin.encoding)
            except:
                pass

            try:
                self.processFromDb = config.getboolean('Settings','processfromdb')
            except ValueError:
                print "processFromDb = True"
                self.processFromDb = True
                haveError = True

            try:
                self.dayLastUpdated = config.getint('Settings','daylastupdated')
            except ValueError:
                print "dayLastUpdated = 7"
                self.dayLastUpdated = 7
                haveError = True

            try:
                self.dateDiff = config.getint('Settings','datediff')
            except ValueError:
                print "dateDiff = 0"
                self.dateDiff = 0
                haveError = True

            try:
                self.proxyAddress = config.get('Settings','proxyaddress')
            except ValueError:
                print "proxyAddress = ''"
                self.proxyAddress = ''
                haveError = True
            self.proxy = {'http': self.proxyAddress, 'https': self.proxyAddress}

            try:
                self.useProxy = config.getboolean('Settings','useproxy')
            except ValueError:
                print "useProxy = False"
                self.useProxy = False
                haveError = True

            try:
                self.useList = config.getboolean('Settings','uselist')
            except ValueError:
                print "useList = False"
                self.useList = False
                haveError = True

            try:
                self.r18mode = config.getboolean('Pixiv','r18mode')
            except ValueError:
                print "r18mode = False"
                self.r18mode = False
                haveError = True

            _useragent = config.get('Settings','useragent')
            if _useragent != None:
                self.useragent = _useragent

            _filenameFormat = config.get('Settings','filenameformat')
            _filenameFormat = PixivHelper.toUnicode(_filenameFormat, encoding=sys.stdin.encoding)
            if _filenameFormat != None:
                self.filenameFormat = _filenameFormat

            _filenameMangaFormat = config.get('Settings','filenamemangaformat')
            _filenameMangaFormat = PixivHelper.toUnicode(_filenameMangaFormat, encoding=sys.stdin.encoding)
            if _filenameMangaFormat != None:
                ## check if the filename format have page identifier if not using %urlFilename%
                if _filenameMangaFormat.find('%urlFilename%') == -1:
                    if _filenameMangaFormat.find('%page_index%') == -1 and _filenameMangaFormat.find('%page_number%') == -1:
                        print 'No page identifier, appending %page_index% to the filename manga format.'
                        _filenameMangaFormat = _filenameMangaFormat + unicode(' %page_index%')
                        print "_filenameMangaFormat =", _filenameMangaFormat
                        haveError = True
                self.filenameMangaFormat = _filenameMangaFormat

            try:
                self.debugHttp = config.getboolean('Settings','debughttp')
            except ValueError:
                self.debugHttp = False
                print "debugHttp = False"
                haveError = True

            try:
                self.useRobots = config.getboolean('Settings','userobots')
            except ValueError:
                self.useRobots = False
                print "useRobots = False"
                haveError = True

            try:
                self.overwrite = config.getboolean('Settings','overwrite')
            except ValueError:
                print "overwrite = False"
                self.overwrite = False
                haveError = True

            try:
                self.createMangaDir = config.getboolean('Settings','createMangaDir')
            except ValueError:
                print "createMangaDir = False"
                self.createMangaDir = False
                haveError = True

            try:
                self.timeout = config.getint('Settings','timeout')
            except ValueError:
                print "timeout = 60"
                self.timeout = 60
                haveError = True

            try:
                self.retry = config.getint('Settings','retry')
            except ValueError:
                print "retry = 3"
                self.retry = 3
                haveError = True

            try:
                self.retryWait = config.getint('Settings','retrywait')
            except ValueError:
                print "retryWait = 5"
                self.retryWait = 5
                haveError = True

            try:
                self.numberOfPage = config.getint('Pixiv','numberofpage')
            except ValueError:
                self.numberOfPage = 0
                print "numberOfPage = 0"
                haveError = True

            try:
                self.createDownloadLists = config.getboolean('Settings','createDownloadLists')
            except ValueError:
                self.createDownloadLists = False
                print "createDownloadLists = False"
                haveError = True

            try:
                self.startIrfanView = config.getboolean('Settings','startIrfanView')
            except ValueError:
                self.startIrfanView = False
                print "startIrfanView = False"
                haveError = True

            try:
                self.startIrfanSlide = config.getboolean('Settings','startIrfanSlide')
            except ValueError:
                self.startIrfanSlide = False
                print "startIrfanSlide = False"
                haveError = True

            try:
                self.alwaysCheckFileSize = config.getboolean('Settings','alwaysCheckFileSize')
            except ValueError:
                self.alwaysCheckFileSize = False
                print "alwaysCheckFileSize = False"
                haveError = True

            try:
                self.downloadAvatar = config.getboolean('Settings','downloadAvatar')
            except ValueError:
                self.downloadAvatar = False
                print "downloadAvatar = False"
                haveError = True

            try:
                self.checkUpdatedLimit = config.getint('Settings','checkUpdatedLimit')
            except ValueError:
                self.checkUpdatedLimit = 0
                print "checkUpdatedLimit = 0"
                haveError = True

            try:
                self.useTagsAsDir = config.getboolean('Settings','useTagsAsDir')
            except ValueError:
                self.useTagsAsDir = False
                print "useTagsAsDir = False"
                haveError = True

            try:
                self.useBlacklistTags = config.getboolean('Settings','useBlacklistTags')
            except ValueError:
                self.useBlacklistTags = False
                print "useBlacklistTags = False"
                haveError = True

            try:
                self.useSuppressTags = config.getboolean('Settings','useSuppressTags')
            except ValueError:
                self.useSuppressTags = False
                print "useSuppressTags = False"
                haveError = True

            try:
                self.tagsLimit = config.getint('Settings','tagsLimit')
            except ValueError:
                self.tagsLimit = -1
                print "tagsLimit = -1"
                haveError = True

            try:
                self.useSSL = config.getboolean('Authentication','useSSL')
            except ValueError:
                self.useSSL = False
                print "useSSL = False"
                haveError = True

            try:
                self.writeImageInfo = config.getboolean('Settings','writeImageInfo')
            except ValueError:
                self.writeImageInfo = False
                print "writeImageInfo = False"
                haveError = True

            try:
                self.keepSignedIn = config.getint('Authentication','keepSignedIn')
            except ValueError:
                print "keepSignedIn = 0"
                self.keepSignedIn = 0
                haveError = True

            try:
                self.backupOldFile = config.getboolean('Settings','backupOldFile')
            except ValueError:
                self.backupOldFile = False
                print "backupOldFile = False"
                haveError = True

            try:
                self.logLevel = config.get('Settings','logLevel').upper()
                if not self.logLevel in ['CRITICAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']:
                    raise ValueError("Value not in list: " + self.logLevel)
            except ValueError:
                print "logLevel = DEBUG"
                self.logLevel = 'DEBUG'
                haveError = True


            try:
                self.enableDump = config.getboolean('Settings','enableDump')
            except ValueError:
                print "enableDump = True"
                self.enableDump = True
                haveError = True

            try:
                self.skipDumpFilter = config.get('Settings','skipDumpFilter')
            except ValueError:
                print "skipDumpFilter = ''"
                self.skipDumpFilter = ''
                haveError = True

            try:
                self.dumpMediumPage = config.getboolean('Settings','dumpMediumPage')
            except ValueError:
                print "dumpMediumPage = False"
                self.dumpMediumPage = False
                haveError = True

            try:
                self.writeUgoiraInfo = config.getboolean('Settings','writeUgoiraInfo')
            except ValueError:
                self.writeUgoiraInfo = False
                print "writeUgoiraInfo = False"
                haveError = True

##        except ConfigParser.NoOptionError:
##            print 'Error at loadConfig():',sys.exc_info()
##            print 'Failed to read configuration.'
##            self.writeConfig()
##        except ConfigParser.NoSectionError:
##            print 'Error at loadConfig():',sys.exc_info()
##            print 'Failed to read configuration.'
##            self.writeConfig()
        except:
            print 'Error at loadConfig():',sys.exc_info()
            self.__logger.exception('Error at loadConfig()')
            haveError = True

        if haveError:
            print 'Some configuration have invalid value, replacing with the default value.'
            self.writeConfig(error=True)

        print 'done.'


    #-UI01B------write config
    def writeConfig(self, error=False, path=None):
        '''Backup old config if exist and write updated config.ini'''
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
        config.set('Settings', 'filenameMangaFormat', self.filenameMangaFormat)
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
        config.set('Settings', 'downloadAvatar', self.downloadAvatar)
        config.set('Settings', 'createMangaDir', self.createMangaDir)
        config.set('Settings', 'useTagsAsDir', self.useTagsAsDir)
        config.set('Settings', 'useBlacklistTags', self.useBlacklistTags)
        config.set('Settings', 'useSuppressTags', self.useSuppressTags)
        config.set('Settings', 'tagsLimit', self.tagsLimit)
        config.set('Settings', 'writeImageInfo', self.writeImageInfo)
        config.set('Settings', 'dateDiff', self.dateDiff)
        config.set('Settings', 'backupOldFile', self.backupOldFile)
        config.set('Settings', 'logLevel', self.logLevel)
        config.set('Settings', 'enableDump', self.enableDump)
        config.set('Settings', 'skipDumpFilter', self.skipDumpFilter)
        config.set('Settings', 'dumpMediumPage', self.dumpMediumPage)
        config.set('Settings', 'writeUgoiraInfo', self.writeUgoiraInfo)

        config.set('Authentication', 'username', self.username)
        config.set('Authentication', 'password', self.password)
        config.set('Authentication', 'cookie', self.cookie)
        config.set('Authentication', 'useSSL', self.useSSL)
        config.set('Authentication', 'keepSignedIn', self.keepSignedIn)

        config.set('Pixiv', 'numberOfPage', self.numberOfPage)
        config.set('Pixiv', 'R18Mode', self.r18mode)

        if path != None:
            configlocation = path
        else:
            configlocation = 'config.ini'

        try:
            ##with codecs.open('config.ini.bak', encoding = 'utf-8', mode = 'wb') as configfile:
            with open(configlocation + '.tmp', 'w') as configfile:
                config.write(configfile)
            if os.path.exists(configlocation):
                if error:
                    backupName = configlocation + '.error-' + str(int(time.time()))
                    print "Backing up old config (error exist!) to " + backupName
                    shutil.move(configlocation, backupName)
                else:
                    print "Backing up old config to config.ini.bak"
                    shutil.move(configlocation, configlocation + '.bak')
            os.rename(configlocation + '.tmp', configlocation)
        except:
            self.__logger.exception('Error at writeConfig()')
            raise

        print 'done.'

    def printConfig(self):
        print 'Configuration: '
        print ' [Authentication]'
        print ' - username     =', self.username
        print ' - password     = ', self.password
        print ' - cookie       = ', self.cookie
        print ' - useSSL       = ', self.useSSL
        print ' - keepSignedIn = ', self.keepSignedIn

        print ' [Settings]'
        print ' - filename_format       =', self.filenameFormat
        print ' - filename_manga_format =', self.filenameMangaFormat
        print ' - useproxy         =' , self.useProxy
        print ' - proxyaddress     =', self.proxyAddress
        print ' - debug_http       =', self.debugHttp
        print ' - use_robots       =', self.useRobots
        print ' - useragent        =', self.useragent
        print ' - overwrite        =', self.overwrite
        print ' - timeout          =', self.timeout
        print ' - useList          =', self.useList
        print ' - processFromDb    =', self.processFromDb
        print ' - tagsSeparator    =', self.tagsSeparator
        print ' - dayLastUpdated   =', self.dayLastUpdated
        print ' - rootDirectory    =', self.rootDirectory
        print ' - retry            =', self.retry
        print ' - retryWait        =', self.retryWait
        print ' - createDownloadLists   =', self.createDownloadLists
        print ' - downloadListDirectory =', self.downloadListDirectory
        print ' - IrfanViewPath    =', self.IrfanViewPath
        print ' - startIrfanView   =', self.startIrfanView
        print ' - startIrfanSlide  =', self.startIrfanSlide
        print ' - alwaysCheckFileSize   =', self.alwaysCheckFileSize
        print ' - checkUpdatedLimit     =', self.checkUpdatedLimit
        print ' - downloadAvatar   =', self.downloadAvatar
        print ' - createMangaDir   =', self.createMangaDir
        print ' - useTagsAsDir     =', self.useTagsAsDir
        print ' - useBlacklistTags =', self.useBlacklistTags
        print ' - useSuppressTags  =', self.useSuppressTags
        print ' - tagsLimit        =', self.tagsLimit
        print ' - writeImageInfo   =', self.writeImageInfo
        print ' - dateDiff         =', self.dateDiff
        print ' - backupOldFile    =', self.backupOldFile
        print ' - logLevel         =', self.logLevel
        print ' - enableDump       =', self.enableDump
        print ' - skipDumpFilter   =', self.skipDumpFilter
        print ' - dumpMediumPage   =', self.dumpMediumPage
        print ' - writeUgoiraInfo  =', self.writeUgoiraInfo

        print ' [Pixiv]'
        print ' - numberOfPage =', self.numberOfPage
        print ' - R18Mode      =', self.r18mode
        print ''
