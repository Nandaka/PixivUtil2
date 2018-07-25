# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302
from __future__ import print_function

import ConfigParser
import sys
import os
import PixivHelper
import shutil
import time
import os.path

script_path = PixivHelper.module_path()


class PixivConfig:
    '''Configuration class'''
    __logger = PixivHelper.GetLogger()
    configFileLocation = "config.ini"

    # initialize default value

    # Network related
    proxyAddress = ''
    proxy = {'http': proxyAddress, 'https': proxyAddress, }
    useProxy = False
    useragent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36'
    useRobots = True
    timeout = 60
    retry = 3
    retryWait = 5
    downloadDelay = 2

    # Authentication related
    username = ''
    password = ''
    cookie = ''

    # Pixiv related?
    numberOfPage = 0
    r18mode = False
    dateFormat = ''

    # generic Settings
    filenameFormat = unicode('%artist% (%member_id%)' + os.sep + '%urlFilename% - %title%')
    filenameMangaFormat = unicode('%artist% (%member_id%)' + os.sep + '%urlFilename% - %title%')
    filenameInfoFormat = unicode('%artist% (%member_id%)' + os.sep + '%urlFilename% - %title%')
    rootDirectory = unicode('.')
    overwrite = False
    useList = False
    processFromDb = True
    dayLastUpdated = 7
    tagsSeparator = unicode(', ')
    alwaysCheckFileSize = False
    checkUpdatedLimit = 0
    downloadAvatar = True
    createMangaDir = False
    useTagsAsDir = False
    useBlacklistTags = False
    useSuppressTags = False
    tagsLimit = -1
    writeImageInfo = False
    writeImageJSON = False
    dateDiff = 0
    backupOldFile = False
    writeUgoiraInfo = False
    createUgoira = False
    deleteZipFile = False
    enableInfiniteLoop = False
    verifyImage = False
    writeUrlInDescription = False
    urlBlacklistRegex = ""
    urlDumpFilename = "url_list_%Y%m%d"
    dbPath = ''
    createGif = False
    useBlacklistMembers = False
    avatarNameFormat = ""
    createApng = False
    deleteUgoira = False
    createWebm = False
    setLastModified = True

    # IrfanView
    createDownloadLists = False
    downloadListDirectory = unicode('.')
    startIrfanView = False
    startIrfanSlide = False
    IrfanViewPath = unicode(r'C:\Program Files\IrfanView')

    # FFmpeg
    ffmpeg = "ffmpeg"
    ffmpegCodec = "libvpx-vp9"
    ffmpegParam = "-lossless 1"

    # Debug related
    logLevel = "DEBUG"
    enableDump = True
    skipDumpFilter = ""
    dumpMediumPage = False
    dumpTagSearchPage = False
    debugHttp = False

    def loadConfig(self, path=None):
        ''' new settings must be added on the last'''

        if path is not None:
            self.configFileLocation = path
        else:
            self.configFileLocation = script_path + os.sep + 'config.ini'

        print('Reading', self.configFileLocation, '...')
        haveError = False
        config = ConfigParser.RawConfigParser()
        try:
            config.readfp(PixivHelper.OpenTextFile(self.configFileLocation))

            self.username = config.get('Authentication', 'username')
            self.password = config.get('Authentication', 'password')
            self.cookie = config.get('Authentication', 'cookie')

            self.tagsSeparator = PixivHelper.toUnicode(config.get('Settings', 'tagsseparator'), encoding=sys.stdin.encoding)
            self.rootDirectory = os.path.expanduser(PixivHelper.toUnicode(config.get('Settings', 'rootdirectory'), encoding=sys.stdin.encoding))

            try:
                self.IrfanViewPath = os.path.expanduser(
                    PixivHelper.toUnicode(config.get('IrfanView', 'IrfanViewPath'), encoding=sys.stdin.encoding))
                self.downloadListDirectory = os.path.expanduser(
                    PixivHelper.toUnicode(config.get('Settings', 'downloadListDirectory'), encoding=sys.stdin.encoding))
            except BaseException:
                pass

            try:
                self.processFromDb = config.getboolean('Settings', 'processfromdb')
            except ValueError:
                print("processFromDb = True")
                self.processFromDb = True
                haveError = True

            try:
                self.dayLastUpdated = config.getint('Settings', 'daylastupdated')
            except ValueError:
                print("dayLastUpdated = 7")
                self.dayLastUpdated = 7
                haveError = True

            try:
                self.dateDiff = config.getint('Settings', 'datediff')
            except ValueError:
                print("dateDiff = 0")
                self.dateDiff = 0
                haveError = True

            try:
                self.proxyAddress = config.get('Network', 'proxyaddress')
            except ValueError:
                print("proxyAddress = ''")
                self.proxyAddress = ''
                haveError = True
            self.proxy = {'http': self.proxyAddress, 'https': self.proxyAddress}

            try:
                self.useProxy = config.getboolean('Network', 'useproxy')
            except ValueError:
                print("useProxy = False")
                self.useProxy = False
                haveError = True

            try:
                self.useList = config.getboolean('Settings', 'uselist')
            except ValueError:
                print("useList = False")
                self.useList = False
                haveError = True

            try:
                self.r18mode = config.getboolean('Pixiv', 'r18mode')
            except ValueError:
                print("r18mode = False")
                self.r18mode = False
                haveError = True

            _useragent = config.get('Network', 'useragent')
            if _useragent is not None:
                self.useragent = _useragent

            _filenameFormat = config.get('Settings', 'filenameformat')
            _filenameFormat = PixivHelper.toUnicode(_filenameFormat, encoding=sys.stdin.encoding)
            if _filenameFormat is not None and len(_filenameFormat) > 0:
                self.filenameFormat = _filenameFormat

            _filenameMangaFormat = config.get('Settings', 'filenamemangaformat')
            _filenameMangaFormat = PixivHelper.toUnicode(_filenameMangaFormat, encoding=sys.stdin.encoding)
            if _filenameMangaFormat is not None and len(_filenameMangaFormat) > 0:
                # check if the filename format have page identifier if not using %urlFilename%
                if _filenameMangaFormat.find('%urlFilename%') == -1:
                    if _filenameMangaFormat.find('%page_index%') == -1 and _filenameMangaFormat.find('%page_number%') == -1:
                        print('No page identifier, appending %page_index% to the filename manga format.')
                        _filenameMangaFormat = _filenameMangaFormat + unicode(' %page_index%')
                        print("_filenameMangaFormat =", _filenameMangaFormat)
                        haveError = True
                self.filenameMangaFormat = _filenameMangaFormat

            _filenameInfoFormat = config.get('Settings', 'filenameinfoformat')
            _filenameInfoFormat = PixivHelper.toUnicode(_filenameInfoFormat, encoding=sys.stdin.encoding)
            if _filenameInfoFormat is not None and len(_filenameInfoFormat) > 0:
                self.filenameInfoFormat = _filenameInfoFormat

            try:
                self.debugHttp = config.getboolean('Debug', 'debughttp')
            except ValueError:
                self.debugHttp = False
                print("debugHttp = False")
                haveError = True

            try:
                self.useRobots = config.getboolean('Network', 'userobots')
            except ValueError:
                self.useRobots = False
                print("useRobots = False")
                haveError = True

            try:
                self.overwrite = config.getboolean('Settings', 'overwrite')
            except ValueError:
                print("overwrite = False")
                self.overwrite = False
                haveError = True

            try:
                self.createMangaDir = config.getboolean('Settings', 'createMangaDir')
            except ValueError:
                print("createMangaDir = False")
                self.createMangaDir = False
                haveError = True

            try:
                self.timeout = config.getint('Network', 'timeout')
            except ValueError:
                print("timeout = 60")
                self.timeout = 60
                haveError = True

            try:
                self.retry = config.getint('Network', 'retry')
            except ValueError:
                print("retry = 3")
                self.retry = 3
                haveError = True

            try:
                self.retryWait = config.getint('Network', 'retrywait')
            except ValueError:
                print("retryWait = 5")
                self.retryWait = 5
                haveError = True

            try:
                self.numberOfPage = config.getint('Pixiv', 'numberofpage')
            except ValueError:
                self.numberOfPage = 0
                print("numberOfPage = 0")
                haveError = True

            try:
                self.createDownloadLists = config.getboolean('IrfanView', 'createDownloadLists')
            except ValueError:
                self.createDownloadLists = False
                print("createDownloadLists = False")
                haveError = True

            try:
                self.startIrfanView = config.getboolean('IrfanView', 'startIrfanView')
            except ValueError:
                self.startIrfanView = False
                print("startIrfanView = False")
                haveError = True

            try:
                self.startIrfanSlide = config.getboolean('IrfanView', 'startIrfanSlide')
            except ValueError:
                self.startIrfanSlide = False
                print("startIrfanSlide = False")
                haveError = True

            try:
                self.alwaysCheckFileSize = config.getboolean('Settings', 'alwaysCheckFileSize')
            except ValueError:
                self.alwaysCheckFileSize = False
                print("alwaysCheckFileSize = False")
                haveError = True

            try:
                self.downloadAvatar = config.getboolean('Settings', 'downloadAvatar')
            except ValueError:
                self.downloadAvatar = False
                print("downloadAvatar = False")
                haveError = True

            try:
                self.checkUpdatedLimit = config.getint('Settings', 'checkUpdatedLimit')
            except ValueError:
                self.checkUpdatedLimit = 0
                print("checkUpdatedLimit = 0")
                haveError = True

            try:
                self.useTagsAsDir = config.getboolean('Settings', 'useTagsAsDir')
            except ValueError:
                self.useTagsAsDir = False
                print("useTagsAsDir = False")
                haveError = True

            try:
                self.useBlacklistTags = config.getboolean('Settings', 'useBlacklistTags')
            except ValueError:
                self.useBlacklistTags = False
                print("useBlacklistTags = False")
                haveError = True

            try:
                self.useSuppressTags = config.getboolean('Settings', 'useSuppressTags')
            except ValueError:
                self.useSuppressTags = False
                print("useSuppressTags = False")
                haveError = True

            try:
                self.tagsLimit = config.getint('Settings', 'tagsLimit')
            except ValueError:
                self.tagsLimit = -1
                print("tagsLimit = -1")
                haveError = True

            try:
                self.writeImageInfo = config.getboolean('Settings', 'writeImageInfo')
            except ValueError:
                self.writeImageInfo = False
                print("writeImageInfo = False")
                haveError = True

            try:
                self.backupOldFile = config.getboolean('Settings', 'backupOldFile')
            except ValueError:
                self.backupOldFile = False
                print("backupOldFile = False")
                haveError = True

            try:
                self.logLevel = config.get('Debug', 'logLevel').upper()
                if self.logLevel not in ['CRITICAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']:
                    raise ValueError("Value not in list: " + self.logLevel)
            except ValueError:
                print("logLevel = DEBUG")
                self.logLevel = 'DEBUG'
                haveError = True

            try:
                self.enableDump = config.getboolean('Debug', 'enableDump')
            except ValueError:
                print("enableDump = True")
                self.enableDump = True
                haveError = True

            try:
                self.skipDumpFilter = config.get('Debug', 'skipDumpFilter')
            except ValueError:
                print("skipDumpFilter = ''")
                self.skipDumpFilter = ''
                haveError = True

            try:
                self.dumpMediumPage = config.getboolean('Debug', 'dumpMediumPage')
            except ValueError:
                print("dumpMediumPage = False")
                self.dumpMediumPage = False
                haveError = True

            try:
                self.writeUgoiraInfo = config.getboolean('Settings', 'writeUgoiraInfo')
            except ValueError:
                self.writeUgoiraInfo = False
                print("writeUgoiraInfo = False")
                haveError = True

            try:
                self.createUgoira = config.getboolean('Settings', 'createUgoira')
            except ValueError:
                self.createUgoira = False
                print("createUgoira = False")
                haveError = True

            try:
                self.deleteZipFile = config.getboolean('Settings', 'deleteZipFile')
            except ValueError:
                self.deleteZipFile = False
                print("deleteZipFile = False")
                haveError = True

            try:
                self.enableInfiniteLoop = config.getboolean('Settings', 'enableInfiniteLoop')
            except ValueError:
                self.enableInfiniteLoop = False
                print("enableInfiniteLoop = False")
                haveError = True

            try:
                self.dumpTagSearchPage = config.getboolean('Debug', 'dumpTagSearchPage')
            except ValueError:
                self.dumpTagSearchPage = False
                print("dumpTagSearchPage = False")
                haveError = True

            try:
                self.dateFormat = config.get('Pixiv', 'dateFormat')
            except ValueError:
                print("dateFormat = ''")
                self.dateFormat = ''
                haveError = True

            try:
                self.verifyImage = config.getboolean('Settings', 'verifyImage')
            except ValueError:
                print("verifyImage = False")
                self.verifyImage = False
                haveError = True

            try:
                self.writeUrlInDescription = config.getboolean('Settings', 'writeUrlInDescription')
            except ValueError:
                print("writeUrlInDescription = False")
                self.writeUrlInDescription = False
                haveError = True

            try:
                self.urlBlacklistRegex = config.get('Settings', 'urlBlacklistRegex')
            except ValueError:
                print("urlBlacklistRegex = ")
                self.urlBlacklistRegex = ""
                haveError = True

            try:
                self.urlDumpFilename = config.get('Settings', 'urlDumpFilename')
            except ValueError:
                print("urlDumpFilename = url_list_%Y%m%d")
                self.urlDumpFilename = "url_list_%Y%m%d"
                haveError = True

            try:
                self.dbPath = config.get('Settings', 'dbPath')
            except ValueError:
                print("dbPath = ''")
                self.dbPath = ''
                haveError = True

            try:
                self.createGif = config.getboolean('Settings', 'createGif')
            except ValueError:
                print("createGif = False")
                self.createGif = False
                haveError = True

            try:
                self.useBlacklistMembers = config.getboolean('Settings', 'useBlacklistMembers')
            except ValueError:
                print("useBlacklistMembers = False")
                self.useBlacklistMembers = False
                haveError = True

            try:
                self.avatarNameFormat = config.get('Settings', 'avatarNameFormat')
                self.avatarNameFormat = PixivHelper.toUnicode(self.avatarNameFormat, encoding=sys.stdin.encoding)
            except ValueError:
                print("avatarNameFormat = ")
                self.avatarNameFormat = ""
                haveError = True

            try:
                self.createApng = config.getboolean('Settings', 'createApng')
            except ValueError:
                print("createApng = False")
                self.createApng = False
                haveError = True

            try:
                self.writeImageJSON = config.getboolean('Settings', 'writeImageJSON')
            except ValueError:
                self.writeImageJSON = False
                print("writeImageJSON = False")
                haveError = True

            try:
                self.downloadDelay = config.getint('Network', 'downloadDelay')
            except ValueError:
                self.downloadDelay = 2
                print("downloadDelay = 2")
                haveError = True

            try:
                self.deleteUgoira = config.getboolean('Settings', 'deleteUgoira')
            except ValueError:
                print("deleteUgoira = False")
                self.deleteUgoira = False
                haveError = True

            try:
                self.createWebm = config.getboolean('Settings', 'createWebm')
            except ValueError:
                print("createWebm = False")
                self.createWebm = False
                haveError = True

            try:
                self.ffmpeg = config.get('FFmpeg', 'ffmpeg')
            except ValueError:
                print("ffmpeg = 'ffmpeg'")
                self.ffmpeg = 'ffmpeg'
                haveError = True

            try:
                self.ffmpegCodec = config.get('FFmpeg', 'ffmpegCodec')
            except ValueError:
                print("ffmpegCodec = 'libvpx-vp9'")
                self.ffmpegCodec = 'libvpx-vp9'
                haveError = True

            try:
                self.ffmpegParam = config.get('FFmpeg', 'ffmpegParam')
            except ValueError:
                print("ffmpegParam = '-lossless 1'")
                self.ffmpegParam = '-lossless 1'
                haveError = True

            try:
                self.setLastModified = config.getboolean('Settings', 'setLastModified')
            except ValueError:
                print("setLastModified = True")
                self.setLastModified = True
                haveError = True

        except BaseException:
            print('Error at loadConfig():', sys.exc_info())
            self.__logger.exception('Error at loadConfig()')
            haveError = True

        if haveError:
            print('Some configuration have invalid value, replacing with the default value.')
            self.writeConfig(error=True)

        print('done.')

    # -UI01B------write config
    def writeConfig(self, error=False, path=None):
        '''Backup old config if exist and write updated config.ini'''
        print('Writing config file...', end=' ')
        config = ConfigParser.RawConfigParser()

        config.add_section('Network')
        config.set('Network', 'useProxy', self.useProxy)
        config.set('Network', 'proxyAddress', self.proxyAddress)
        config.set('Network', 'useragent', self.useragent)
        config.set('Network', 'useRobots', self.useRobots)
        config.set('Network', 'timeout', self.timeout)
        config.set('Network', 'retry', self.retry)
        config.set('Network', 'retrywait', self.retryWait)
        config.set('Network', 'downloadDelay', self.downloadDelay)

        config.add_section('Debug')
        config.set('Debug', 'logLevel', self.logLevel)
        config.set('Debug', 'enableDump', self.enableDump)
        config.set('Debug', 'skipDumpFilter', self.skipDumpFilter)
        config.set('Debug', 'dumpMediumPage', self.dumpMediumPage)
        config.set('Debug', 'dumpTagSearchPage', self.dumpTagSearchPage)
        config.set('Debug', 'debugHttp', self.debugHttp)

        config.add_section('IrfanView')
        config.set('IrfanView', 'IrfanViewPath', self.IrfanViewPath)
        config.set('IrfanView', 'startIrfanView', self.startIrfanView)
        config.set('IrfanView', 'startIrfanSlide', self.startIrfanSlide)
        config.set('IrfanView', 'createDownloadLists', self.createDownloadLists)

        config.add_section('Settings')
        config.set('Settings', 'filenameFormat', self.filenameFormat)
        config.set('Settings', 'filenameMangaFormat', self.filenameMangaFormat)
        config.set('Settings', 'filenameInfoFormat', self.filenameInfoFormat)
        config.set('Settings', 'avatarNameFormat', self.avatarNameFormat)
        config.set('Settings', 'downloadListDirectory', self.downloadListDirectory)
        config.set('Settings', 'useList', self.useList)
        config.set('Settings', 'processFromDb', self.processFromDb)
        config.set('Settings', 'overwrite', self.overwrite)
        config.set('Settings', 'tagsseparator', self.tagsSeparator)
        config.set('Settings', 'daylastupdated', self.dayLastUpdated)
        config.set('Settings', 'rootdirectory', self.rootDirectory)
        config.set('Settings', 'alwaysCheckFileSize', self.alwaysCheckFileSize)
        config.set('Settings', 'checkUpdatedLimit', self.checkUpdatedLimit)
        config.set('Settings', 'downloadAvatar', self.downloadAvatar)
        config.set('Settings', 'createMangaDir', self.createMangaDir)
        config.set('Settings', 'useTagsAsDir', self.useTagsAsDir)
        config.set('Settings', 'useBlacklistTags', self.useBlacklistTags)
        config.set('Settings', 'useSuppressTags', self.useSuppressTags)
        config.set('Settings', 'tagsLimit', self.tagsLimit)
        config.set('Settings', 'writeImageInfo', self.writeImageInfo)
        config.set('Settings', 'writeImageJSON', self.writeImageJSON)
        config.set('Settings', 'dateDiff', self.dateDiff)
        config.set('Settings', 'backupOldFile', self.backupOldFile)
        config.set('Settings', 'writeUgoiraInfo', self.writeUgoiraInfo)
        config.set('Settings', 'createUgoira', self.createUgoira)
        config.set('Settings', 'deleteZipFile', self.deleteZipFile)
        config.set('Settings', 'enableInfiniteLoop', self.enableInfiniteLoop)
        config.set('Settings', 'verifyImage', self.verifyImage)
        config.set('Settings', 'writeUrlInDescription', self.writeUrlInDescription)
        config.set('Settings', 'urlBlacklistRegex', self.urlBlacklistRegex)
        config.set('Settings', 'urlDumpFilename', self.urlDumpFilename)
        config.set('Settings', 'dbPath', self.dbPath)
        config.set('Settings', 'createGif', self.createGif)
        config.set('Settings', 'useBlacklistMembers', self.useBlacklistMembers)
        config.set('Settings', 'createApng', self.createApng)
        config.set('Settings', 'deleteUgoira', self.deleteUgoira)
        config.set('Settings', 'createWebm', self.createWebm)
        config.set('Settings', 'setLastModified', self.setLastModified)

        config.add_section('Authentication')
        config.set('Authentication', 'username', self.username)
        config.set('Authentication', 'password', self.password)
        config.set('Authentication', 'cookie', self.cookie)

        config.add_section('Pixiv')
        config.set('Pixiv', 'numberOfPage', self.numberOfPage)
        config.set('Pixiv', 'R18Mode', self.r18mode)
        config.set('Pixiv', 'DateFormat', self.dateFormat)

        config.add_section('FFmpeg')
        config.set('FFmpeg', 'ffmpeg', self.ffmpeg)
        config.set('FFmpeg', 'ffmpegCodec', self.ffmpegCodec)
        config.set('FFmpeg', 'ffmpegParam', self.ffmpegParam)

        if path is not None:
            configlocation = path
        else:
            configlocation = 'config.ini'

        try:
            # with codecs.open('config.ini.bak', encoding = 'utf-8', mode = 'wb') as configfile:
            with open(configlocation + '.tmp', 'w') as configfile:
                config.write(configfile)
            if os.path.exists(configlocation):
                if error:
                    backupName = configlocation + '.error-' + str(int(time.time()))
                    print("Backing up old config (error exist!) to " +
                            backupName)
                    shutil.move(configlocation, backupName)
                else:
                    print("Backing up old config to config.ini.bak")
                    shutil.move(configlocation, configlocation + '.bak')
            os.rename(configlocation + '.tmp', configlocation)
        except BaseException:
            self.__logger.exception('Error at writeConfig()')
            raise

        print('done.')

    def printConfig(self):
        print('Configuration: ')
        print(' [Authentication]')
        print(' - username     =', self.username)
        print(' - password     = ', self.password)
        print(' - cookie       = ', self.cookie)

        print(' [Network]')
        print(' - useproxy         =', self.useProxy)
        print(' - proxyaddress     =', self.proxyAddress)
        print(' - useragent        =', self.useragent)
        print(' - use_robots       =', self.useRobots)
        print(' - timeout          =', self.timeout)
        print(' - retry            =', self.retry)
        print(' - retryWait        =', self.retryWait)
        print(' - downloadDelay      =', self.downloadDelay)

        print(' [Debug]')
        print(' - logLevel         =', self.logLevel)
        print(' - enableDump       =', self.enableDump)
        print(' - skipDumpFilter   =', self.skipDumpFilter)
        print(' - dumpMediumPage   =', self.dumpMediumPage)
        print(' - dumpTagSearchPage=', self.dumpTagSearchPage)
        print(' - debug_http       =', self.debugHttp)

        print(' [IrfanView]')
        print(' - IrfanViewPath    =', self.IrfanViewPath)
        print(' - startIrfanView   =', self.startIrfanView)
        print(' - startIrfanSlide  =', self.startIrfanSlide)
        print(' - createDownloadLists   =', self.createDownloadLists)

        print(' [Settings]')
        print(' - filename_format       =', self.filenameFormat)
        print(' - filename_manga_format =', self.filenameMangaFormat)
        print(' - filename_info_format  =', self.filenameInfoFormat)
        print(' - avatarNameFormat =', self.avatarNameFormat)
        print(' - downloadListDirectory =', self.downloadListDirectory)
        print(' - overwrite        =', self.overwrite)
        print(' - useList          =', self.useList)
        print(' - processFromDb    =', self.processFromDb)
        print(' - tagsSeparator    =', self.tagsSeparator)
        print(' - dayLastUpdated   =', self.dayLastUpdated)
        print(' - rootDirectory    =', self.rootDirectory)
        print(' - alwaysCheckFileSize   =', self.alwaysCheckFileSize)
        print(' - checkUpdatedLimit     =', self.checkUpdatedLimit)
        print(' - downloadAvatar   =', self.downloadAvatar)
        print(' - createMangaDir   =', self.createMangaDir)
        print(' - useTagsAsDir     =', self.useTagsAsDir)
        print(' - useBlacklistTags =', self.useBlacklistTags)
        print(' - useSuppressTags  =', self.useSuppressTags)
        print(' - tagsLimit        =', self.tagsLimit)
        print(' - writeImageInfo   =', self.writeImageInfo)
        print(' - writeImageJSON   =', self.writeImageJSON)
        print(' - dateDiff         =', self.dateDiff)
        print(' - backupOldFile    =', self.backupOldFile)
        print(' - writeUgoiraInfo  =', self.writeUgoiraInfo)
        print(' - createUgoira     =', self.createUgoira)
        print(' - deleteZipFile    =', self.deleteZipFile)
        print(' - enableInfiniteLoop    =', self.enableInfiniteLoop)
        print(' - verifyImage      =', self.verifyImage)
        print(' - writeUrlInDescription =', self.writeUrlInDescription)
        print(' - urlBlacklistRegex =', self.urlBlacklistRegex)
        print(' - urlDumpFilename  =', self.urlDumpFilename)
        print(' - dbPath           =', self.dbPath)
        print(' - createGif        =', self.createGif)
        print(' - useBlacklistMembers  =', self.useBlacklistMembers)
        print(' - createApng       =', self.createApng)
        print(' - deleteUgoira     =', self.deleteUgoira)
        print(' - createWebm       =', self.createWebm)
        print(' - setLastModified  =', self.setLastModified)

        print(' [Pixiv]')
        print(' - numberOfPage =', self.numberOfPage)
        print(' - R18Mode      =', self.r18mode)
        print(' - DateFormat   =', self.dateFormat)

        print(' [FFmpeg]')
        print(' - ffmpeg       =', self.ffmpeg)
        print(' - ffmpegCodec  =', self.ffmpegCodec)
        print(' - ffmpegParam  =', self.ffmpegParam)
        print('')
