# -*- coding: utf-8 -*-
import configparser
import itertools
import os
import os.path
import shutil
import sys
import time
import re

from colorama import Fore, Style

import PixivHelper

script_path = PixivHelper.module_path()


def stringNotEmpty(value):
    return value is not None and len(value) > 0


class ConfigItem():
    section = None
    option = None
    default = None
    restriction = None
    followup = None
    error_message = None

    def __init__(self, section, option, default, *, followup=None, restriction=None, error_message=None):
        self.section = section
        self.option = option
        self.default = default
        self.followup = followup
        self.restriction = restriction
        self.error_message = error_message

    def process_value(self, value):
        return_value = value
        if self.restriction:
            result = self.restriction(value)
            if not result:
                if self.error_message is not None:
                    raise ValueError(f"{self.error_message} {self.option}: [{value}]")
                else:
                    raise ValueError(f"Illegal value for {self.option}: [{value}]")
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
        ConfigItem("Network", "notifyBetaVersion", True),
        ConfigItem("Network", "openNewVersion", True),
        ConfigItem("Network", "enableSSLVerification", True),

        ConfigItem("Debug", "logLevel", "DEBUG",
                   followup=str.upper,
                   restriction=lambda x: x.upper() in ['CRITICAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']),
        ConfigItem("Debug", "enableDump", True),
        ConfigItem("Debug", "skipDumpFilter", ""),
        ConfigItem("Debug", "dumpMediumPage", False),
        ConfigItem("Debug", "dumpTagSearchPage", False),
        ConfigItem("Debug", "debugHttp", False),
        ConfigItem("Debug", "disableLog", False),

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
        ConfigItem("Settings", "writeRawJSON", False),
        ConfigItem("Settings", "RawJSONFilter",
                   "id,title,description,alt,userIllusts,storableTags,zoneConfig,extraData,comicPromotion,fanboxPromotion"),
        ConfigItem("Settings", "includeSeriesJSON", False),
        ConfigItem("Settings", "writeImageXMP", False),
        ConfigItem("Settings", "writeImageXMPPerImage", False),
        ConfigItem("Settings", "verifyImage", False),
        ConfigItem("Settings", "writeUrlInDescription", False),
        ConfigItem("Settings", "stripHTMLTagsFromCaption", False),
        ConfigItem("Settings", "urlBlacklistRegex", ""),
        ConfigItem("Settings", "dbPath", ""),
        ConfigItem("Settings", "setLastModified", True),
        ConfigItem("Settings", "useLocalTimezone", False),
        ConfigItem("Settings", "defaultSketchOption", ""),

        ConfigItem("Filename",
                   "filenameFormat",
                   "%artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=stringNotEmpty),
        ConfigItem("Filename",
                   "filenameMangaFormat",
                   "%artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=lambda x: stringNotEmpty(x) and (x.find("%urlFilename%") >= 0 or (x.find('%page_index%') >= 0 or x.find('%page_number%') >= 0)),
                   error_message="At least %urlFilename%, %page_index%, or %page_number% is required in"),
        ConfigItem("Filename", "filenameInfoFormat",
                   "%artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=stringNotEmpty),
        ConfigItem("Filename", "filenameMangaInfoFormat",
                   "%artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=stringNotEmpty),
        ConfigItem("Filename", "filenameSeriesJSON",
                   "%artist% (%member_id%)" + os.sep + "%manga_series_id% - %manga_series_title%",
                   restriction=stringNotEmpty),
        ConfigItem("Filename", "filenameFormatSketch", "%artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=stringNotEmpty),
        ConfigItem("Filename", "filenameFormatNovel",
                   "%artist% (%member_id%)" + os.sep + "%manga_series_id% %manga_series_order% %urlFilename% - %title%",
                   restriction=stringNotEmpty),
        ConfigItem("Filename", "avatarNameFormat", ""),
        ConfigItem("Filename", "backgroundNameFormat", ""),
        ConfigItem("Filename", "tagsSeparator", ", "),
        ConfigItem("Filename", "createMangaDir", False),
        ConfigItem("Filename", "useTagsAsDir", False),
        ConfigItem("Filename", "urlDumpFilename", "url_list_%Y%m%d"),
        ConfigItem("Filename", "useTranslatedTag", False),
        ConfigItem("Filename", "tagTranslationLocale", "en"),
        ConfigItem("Filename", "customBadChars", "", followup=PixivHelper.parse_custom_sanitizer),
        ConfigItem("Filename", "customCleanUpRe", "", followup=PixivHelper.parse_custom_clean_up_re),

        ConfigItem("Authentication", "username", ""),
        ConfigItem("Authentication", "password", ""),
        ConfigItem("Authentication", "cookie", ""),
        ConfigItem("Authentication", "cookieFanbox", ""),
        ConfigItem("Authentication", "refresh_token", ""),

        ConfigItem("Pixiv", "numberOfPage", 0),
        ConfigItem("Pixiv", "r18mode", False),
        ConfigItem("Pixiv", "dateFormat", ""),
        ConfigItem("Pixiv", "autoAddMember", False),

        ConfigItem("FANBOX", "filenameFormatFanboxCover",
                   "FANBOX %artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=stringNotEmpty),
        ConfigItem("FANBOX", "filenameFormatFanboxContent",
                   "FANBOX %artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=lambda x: stringNotEmpty(x) and (x.find("%urlFilename%") >= 0 or (x.find('%page_index%') >= 0 or x.find('%page_number%') >= 0)),
                   error_message="At least %urlFilename%, %page_index%, or %page_number% is required in"),
        ConfigItem("FANBOX", "filenameFormatFanboxInfo",
                   "FANBOX %artist% (%member_id%)" + os.sep + "%urlFilename% - %title%",
                   restriction=stringNotEmpty),
        ConfigItem("FANBOX", "writeHtml", False),
        ConfigItem("FANBOX", "minTextLengthForNonArticle", 45),
        ConfigItem("FANBOX", "minImageCountForNonArticle", 3),
        ConfigItem("FANBOX", "useAbsolutePathsInHtml", False),
        ConfigItem("FANBOX", "downloadCoverWhenRestricted", False),
        ConfigItem("FANBOX", "downloadCover", True),
        ConfigItem("FANBOX", "checkDBProcessHistory", False),
        ConfigItem("FANBOX", "listPathFanbox", "listfanbox.txt"),

        ConfigItem("FFmpeg", "ffmpeg", "ffmpeg.exe"),
        ConfigItem("FFmpeg", "ffmpegCodec", "libvpx-vp9"),
        ConfigItem("FFmpeg", "ffmpegExt", "webm"),
        ConfigItem("FFmpeg", "ffmpegParam", "-row-mt 1 -deadline good -crf 20 -vsync 2 -r 999 -pix_fmt yuv420p"),
        ConfigItem("FFmpeg", "webpCodec", "libwebp"),
        ConfigItem("FFmpeg", "webpParam", "-row-mt 1 -lossless 0 -q:v 90 -loop 0 -vsync 2 -r 999"),
        ConfigItem("FFmpeg", "gifParam",
                   "-filter_complex \"[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle\""),
        ConfigItem("FFmpeg", "apngParam", "-vf \"setpts=PTS-STARTPTS,hqdn3d=1.5:1.5:6:6\" -plays 0"),
        ConfigItem("FFmpeg", "verboseOutput", False),

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
        ConfigItem("DownloadControl", "useBlacklistTitles", False),
        ConfigItem("DownloadControl", "useBlacklistTitlesRegex", False),
        ConfigItem("DownloadControl", "dateDiff", 0),
        ConfigItem("DownloadControl", "enableInfiniteLoop", False),
        ConfigItem("DownloadControl", "useBlacklistMembers", False),
        ConfigItem("DownloadControl", "downloadResized", False),
        ConfigItem("DownloadControl", "checkLastModified", True),
        ConfigItem("DownloadControl", "skipUnknownSize", False),
        ConfigItem("DownloadControl", "enablePostProcessing", False),
        ConfigItem("DownloadControl", "postProcessingCmd", ""),
    ]

    def __init__(self):
        for item in self.__items:
            setattr(self, item.option, item.process_value(item.default))

    @property
    def proxy(self):
        value = getattr(self, "proxyAddress", None)
        if not value:
            return None
        match = re.match(r"^(?:(https?|socks[45])://)?([\w.-]+)(:\d+)?$", value)
        if not match:
            return None
        scheme, netloc, port = match.groups()
        scheme = scheme or "http"
        value = f"{scheme}://{netloc}{port}"
        return {"http": value, "https": value}

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
        except BaseException:
            print('Error at loadConfig() reading file:', self.configFileLocation, "\n", sys.exc_info())
            self.__logger.exception('Error at loadConfig() reading file: %s', self.configFileLocation)
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

            value = None
            try:
                try:
                    value = method(item.section, item.option)
                except (configparser.NoSectionError, configparser.NoOptionError):
                    haveError = True
                    for section in config.sections():
                        try:
                            value = method(section, item.option)
                            break
                        except (configparser.NoSectionError, configparser.NoOptionError):
                            continue
                    if value is None:
                        raise
            except BaseException:
                print(item.option, "=", item.default)
                value = item.default
                haveError = True

            # Issue #743
            try:
                value = item.process_value(value)
            except ValueError:
                print(Fore.RED + Style.BRIGHT + f"{sys.exc_info()}" + Style.RESET_ALL)
                self.__logger.exception('Error at process_value() of : %s', item.option)
                print(Fore.YELLOW + Style.BRIGHT + f"{item.option} = {item.default}" + Style.RESET_ALL)
                value = item.default
                haveError = True

            # assign the value to the actual configuration attribute
            self.__setattr__(item.option, value)

        if haveError:
            print(Fore.RED + Style.BRIGHT + 'Configurations with invalid value are set to default value.' + Style.RESET_ALL)
            self.writeConfig(error=True, path=self.configFileLocation)

        print('Configuration loaded.')

    # -UI01B------write config
    def writeConfig(self, error=False, path=None):
        '''Backup old config if exist and write updated config.ini'''
        print('Writing config file...', end=' ')
        config = configparser.RawConfigParser()
        config.optionxform = lambda option: option

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

        print('Configuration saved.')

    def printConfig(self):
        print('Configuration: ')
        groups = {k: list(g) for k, g in itertools.groupby(PixivConfig.__items, lambda x: x.section)}
        sections = ["Authentication", "Network", "Debug", "IrfanView", "Settings", "Filename", "Pixiv", "FANBOX",
                    "FFmpeg", "Ugoira", "DownloadControl"]
        sections.extend([k for k in groups if k not in sections])
        for section in sections:
            g = groups.get(section)
            if g:
                print(f" [{section}]")
                for item in g:
                    print(f" - {item.option:{25}} = {self.__getattribute__(item.option)}")
        print('')


if __name__ == '__main__':
    cfg = PixivConfig()
    cfg.loadConfig("./config.ini")
    test_filename = "C:\\haha\\hehe\\ ()\\filename.jpg"
    print(f"[{cfg.customCleanUpRe}]")
    print(f"{test_filename} ==> {re.sub(cfg.customCleanUpRe, '', test_filename)}")
