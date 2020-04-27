# -*- coding: utf-8 -*-
import configparser
import itertools
import os
import os.path
import shutil
import sys
import time

import PixivHelper

script_path = PixivHelper.module_path()


class ConfigItem():
    section = None
    option = None
    default = None
    restriction = None
    followup = None

    def __init__(self, section, option, default, *, followup=None, restriction=None):
        self.section = section
        self.option = option
        self.default = default
        self.followup = followup
        self.restriction = restriction

    def process_value(self, value):
        return_value = value
        if self.restriction:
            result = self.restriction(value)
            if not result:
                raise ValueError("Illegal value for", self.option, ":", value)
        if self.followup:
            return_value = self.followup(value)
        return return_value


class PixivConfig():
    '''Configuration class'''
    __logger = PixivHelper.get_logger()
    configFileLocation = "config.ini"

    __items = [
        ConfigItem("Network", "useProxy", False),
        ConfigItem("Network", "proxyAddress", ""),
        ConfigItem("Network", "useragent",
                   "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2062.124 Safari/537.36"),
        ConfigItem("Network", "useRobots", True),
        ConfigItem("Network", "timeout", 60),
        ConfigItem("Network", "retry", 3),
        ConfigItem("Network", "retryWait", 5),
        ConfigItem("Network", "downloadDelay", 2),
        ConfigItem("Network", "checkNewVersion", True),
        ConfigItem("Network", "enableSSLVerification", True),

        ConfigItem("Debug", "logLevel", "DEBUG",
                   followup=lambda x: x.upper(),
                   restriction=lambda x: x.upper() in ['CRITICAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG',
                                                       'NOTSET']),
        ConfigItem("Debug", "enableDump", True),
        ConfigItem("Debug", "skipDumpFilter", ""),
        ConfigItem("Debug", "dumpMediumPage", False),
        ConfigItem("Debug", "dumpTagSearchPage", False),
        ConfigItem("Debug", "debugHttp", False),

        ConfigItem("IrfanView", "IrfanViewPath", r"C:\Program Files\IrfanView", followup=os.path.expanduser),
        ConfigItem("IrfanView", "startIrfanView", False),
        ConfigItem("IrfanView", "startIrfanSlide", False),
        ConfigItem("IrfanView", "createDownloadLists", False),

        ConfigItem("Settings", "downloadListDirectory", ".", followup=os.path.expanduser),
        ConfigItem("Settings", "useList", False),
        ConfigItem("Settings", "processFromDb", True),
        ConfigItem("Settings", "rootDirectory", "."),
        ConfigItem("Settings", "downloadAvatar", False),
        ConfigItem("Settings", "useSuppressTags", False),
        ConfigItem("Settings", "tagsLimit", -1),
        ConfigItem("Settings", "writeImageInfo", False),
        ConfigItem("Settings", "writeImageJSON", False),
        ConfigItem("Settings", "writeHtml", False),
        ConfigItem("Settings", "useAbsolutePathsInHtml", False),
        ConfigItem("Settings", "verifyImage", False),
        ConfigItem("Settings", "writeUrlInDescription", False),
        ConfigItem("Settings", "urlBlacklistRegex", ""),
        ConfigItem("Settings", "dbPath", ""),
        ConfigItem("Settings", "setLastModified", True),
        ConfigItem("Settings", "useLocalTimezone", False),

        ConfigItem("Filename", "filenameFormat",
                   "%artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=lambda x: x is not None and len(x) > 0),
        ConfigItem("Filename", "filenameMangaFormat",
                   "%artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=lambda x:
                   x is not None and len(x) > 0 and
                   (x.find("%urlFilename%") >= 0 or (x.find('%page_index%') >= 0 or x.find('%page_number%') >= 0))),
        ConfigItem("Filename", "filenameInfoFormat",
                   "%artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=lambda x: x is not None and len(x) > 0),
        ConfigItem("Filename", "filenameMangaInfoFormat",
                   "%artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=lambda x: x is not None and len(x) > 0),
        ConfigItem("Filename", "avatarNameFormat", ""),
        ConfigItem("Filename", "tagsSeparator", ", "),
        ConfigItem("Filename", "createMangaDir", False),
        ConfigItem("Filename", "useTagsAsDir", False),
        ConfigItem("Filename", "urlDumpFilename", "url_list_%Y%m%d"),

        ConfigItem("Authentication", "username", ""),
        ConfigItem("Authentication", "password", ""),
        ConfigItem("Authentication", "cookie", ""),
        ConfigItem("Authentication", "refresh_token", ""),

        ConfigItem("Pixiv", "numberOfPage", 0),
        ConfigItem("Pixiv", "r18mode", False),
        ConfigItem("Pixiv", "dateFormat", ""),
        ConfigItem("Pixiv", "autoAddMember", False),

        ConfigItem("FFmpeg", "ffmpeg", "ffmpeg"),
        ConfigItem("FFmpeg", "ffmpegCodec", "libvpx-vp9"),
        ConfigItem("FFmpeg", "ffmpegParam", "-lossless 1 -vsync 2 -r 999 -pix_fmt yuv420p"),
        ConfigItem("FFmpeg", "webpCodec", "libwebp"),
        ConfigItem("FFmpeg", "webpParam", "-lossless 0 -q:v 90 -loop 0 -vsync 2 -r 999"),

        ConfigItem("Ugoira", "writeUgoiraInfo", False),
        ConfigItem("Ugoira", "createUgoira", False),
        ConfigItem("Ugoira", "deleteZipFile", False),
        ConfigItem("Ugoira", "createGif", False),
        ConfigItem("Ugoira", "createApng", False),
        ConfigItem("Ugoira", "deleteUgoira", False),
        ConfigItem("Ugoira", "createWebm", False),
        ConfigItem("Ugoira", "createWebp", False),

        ConfigItem("DownloadControl", "minFileSize", 0),
        ConfigItem("DownloadControl", "maxFileSize", 0),
        ConfigItem("DownloadControl", "overwrite", False),
        ConfigItem("DownloadControl", "backupOldFile", False),
        ConfigItem("DownloadControl", "dayLastUpdated", 7),
        ConfigItem("DownloadControl", "alwaysCheckFileSize", False),
        ConfigItem("DownloadControl", "checkUpdatedLimit", 0),
        ConfigItem("DownloadControl", "useBlacklistTags", False),
        ConfigItem("DownloadControl", "dateDiff", 0),
        ConfigItem("DownloadControl", "enableInfiniteLoop", False),
        ConfigItem("DownloadControl", "useBlacklistMembers", False),
        ConfigItem("DownloadControl", "downloadResized", False),
    ]

    proxy = {"http": "", "https": "", }

    def __init__(self):
        for item in self.__items:
            setattr(self, item.option, item.default)
        self.proxy = {'http': self.proxyAddress, 'https': self.proxyAddress}

    def loadConfig(self, path=None):
        if path is not None:
            self.configFileLocation = path
        else:
            self.configFileLocation = script_path + os.sep + 'config.ini'

        print('Reading', self.configFileLocation, '...')
        config = configparser.RawConfigParser()

        try:
            with PixivHelper.open_text_file(self.configFileLocation) as reader:
                content = reader.read()
        except BaseException as e:
            print('Error at loadConfig() reading file:', self.configFileLocation, "\n", sys.exc_info())
            self.__logger.exception('Error at loadConfig() reading file: ' + self.configFileLocation)
            self.writeConfig(error=True, path=self.configFileLocation)
            return

        haveError = False
        config.read_string(content)

        for item in PixivConfig.__items:
            option_type = type(item.default)

            method = config.get
            if option_type == int:
                method = config.getint
            elif option_type == bool:
                method = config.getboolean

            try:
                value = method(item.section, item.option)
                value = item.process_value(value)
            except:
                print(item.option, "=", item.default)
                value = item.default
                haveError = True

            self.__setattr__(item.option, value)

        self.proxy = {'http': self.proxyAddress, 'https': self.proxyAddress}

        if haveError:
            print('Configurations with invalid value are set to default value.')
            self.writeConfig(error=True, path=self.configFileLocation)

        print('done.')

    # -UI01B------write config
    def writeConfig(self, error=False, path=None):
        '''Backup old config if exist and write updated config.ini'''
        print('Writing config file...', end=' ')
        config = configparser.RawConfigParser()

        groups = itertools.groupby(PixivConfig.__items, lambda x: x.section)

        for k, g in groups:
            config.add_section(k)
            for item in g:
                config.set(item.section, item.option, self.__getattribute__(item.option))

        if path is not None:
            configlocation = path
        else:
            configlocation = 'config.ini'

        try:
            # with codecs.open('config.ini.bak', encoding = 'utf-8', mode = 'wb') as configfile:
            with open(configlocation + '.tmp', 'w', encoding='utf8') as configfile:
                config.write(configfile)
                configfile.close()

            if os.path.exists(configlocation):
                if error:
                    backupName = configlocation + '.error-' + str(int(time.time()))
                    print("Backing up old config (error exist!) to " + backupName)
                    shutil.move(configlocation, backupName)
                else:
                    print("Backing up old config to config.ini.bak")
                    shutil.move(configlocation, configlocation + '.bak')
            self.__logger.debug(f"renaming {configlocation}.tmp to {configlocation}")
            os.rename(configlocation + '.tmp', configlocation)
        except BaseException:
            self.__logger.exception('Error at writeConfig()')
            raise

        print('done.')

    def printConfig(self):
        print('Configuration: ')
        groups = {k: list(g) for k, g in itertools.groupby(PixivConfig.__items, lambda x: x.section)}
        sections = ["Authentication", "Network", "Debug", "IrfanView", "Settings", "Filename", "Pixiv", "FFmpeg",
                    "Ugoira", "DownloadControl"]
        sections.extend([k for k in groups if k not in sections])
        for section in sections:
            g = groups.get(section)
            if g:
                print(f" [{section}]")
                for item in g:
                    print(f" - {item.option:{25}} = {self.__getattribute__(item.option)}")
        print('')
