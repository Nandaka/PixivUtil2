# -*- coding: utf-8 -*-
# pylint: disable=W0603

import codecs
import html
import json
import logging
import logging.handlers
import os
import platform
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import unicodedata
import urllib
import urllib.parse
import webbrowser
import zipfile
from datetime import date, datetime, timedelta, tzinfo
from hashlib import md5, sha1, sha256
from mmap import ACCESS_READ, mmap
from pathlib import Path
from typing import Union

import mechanize
from colorama import Fore, Style

import PixivConstant
from PixivException import PixivException
import PixivArtist
from PixivImage import PixivImage
from PixivModelFanbox import FanboxArtist, FanboxPost

logger = None
_config = None
__re_manga_index = re.compile(r'_p(\d+)')
__badchars__ = None
if platform.system() == 'Windows':
    __badchars__ = re.compile(r'''
    ^$
    |\?
    |:
    |<
    |>
    |\|
    |\*
    |\"
    ''', re.VERBOSE)
else:
    __badchars__ = re.compile(r'''
    ^$
    ''', re.VERBOSE)

__custom_sanitizer_dic__ = {}


def set_config(config):
    global _config
    _config = config


def get_logger(level=logging.DEBUG):
    '''Set up logging'''
    global logger
    if logger is None:
        script_path = module_path()
        logger = logging.getLogger('PixivUtil' + PixivConstant.PIXIVUTIL_VERSION)
        logger.setLevel(level)
        __logHandler__ = logging.handlers.RotatingFileHandler(script_path + os.sep + PixivConstant.PIXIVUTIL_LOG_FILE,
                                                              maxBytes=PixivConstant.PIXIVUTIL_LOG_SIZE,
                                                              backupCount=PixivConstant.PIXIVUTIL_LOG_COUNT,
                                                              encoding="utf-8")
        __formatter__ = logging.Formatter(PixivConstant.PIXIVUTIL_LOG_FORMAT)
        __logHandler__.setFormatter(__formatter__)
        logger.addHandler(__logHandler__)
    return logger


def set_log_level(level):
    logger.info("Setting log level to: %s", level)
    get_logger(level).setLevel(level)


def sanitize_filename(name, rootDir=None):
    '''Replace reserved character/name with underscore (windows), rootDir is not sanitized.'''
    # get the absolute rootdir
    if rootDir is not None:
        rootDir = os.path.abspath(rootDir)

    # Unescape '&amp;', '&lt;', and '&gt;'
    name = html.unescape(name)

    name = __badchars__.sub("_", name)

    for key, value in __custom_sanitizer_dic__.items():
        name = value["regex"].sub(value["replace"], name)

    # Remove unicode control characters
    name = "".join(c for c in name if unicodedata.category(c) != "Cc")

    # Strip leading/trailing space for each directory
    # Issue #627: remove trailing '.'
    # Ensure Windows reserved filenames are prefixed with _
    stripped_name = list()
    for item in name.split(os.sep):
        if Path(item).is_reserved():
            item = '_' + item
        stripped_name.append(item.strip(" .\t\r\n"))
    name = os.sep.join(stripped_name)

    if platform.system() == 'Windows':
        # cut whole path to 255 char
        # TODO: check for Windows long path extensions being enabled
        if rootDir is not None:
            # need to remove \\ from name prefix
            tname = name[1:] if name[0] == os.sep else name
            full_name = os.path.abspath(os.path.join(rootDir, tname))
        else:
            full_name = os.path.abspath(name)

        if len(full_name) > 255:
            filename, extname = os.path.splitext(name)  # NOT full_name, to avoid clobbering paths
            # don't trim the extension
            name = filename[:255 - len(extname)] + extname
            if name == extname:  # we have no file name left
                raise OSError(None, "Path name too long", full_name, 0x000000A1)  # 0xA1 is "invalid path"
    else:
        # Unix: cut filename to <= 249 bytes
        # TODO: allow macOS higher limits, HFS+ allows 255 UTF-16 chars, and APFS 255 UTF-8 chars
        while len(name.encode('utf-8')) > 249:
            filename, extname = os.path.splitext(name)
            name = filename[:len(filename) - 1] + extname
        name = name.replace('\\', '/')

    if rootDir is not None:
        name = name[1:] if name[0] == os.sep else name
        name = os.path.abspath(os.path.join(rootDir, name))

    get_logger().debug("Sanitized Filename: %s", name)

    return name


# Issue #277: always replace '/' and '\' with '_' for %artist%, %title%, %searchTags%, %tags%, and %original_artist%.
def replace_path_separator(s, replacement='_'):
    return s.replace('/', replacement).replace('\\', replacement)


def make_filename(nameFormat: str,
                  imageInfo: Union[PixivImage, FanboxPost],
                  artistInfo: Union[PixivArtist.PixivArtist, FanboxArtist] = None,
                  tagsSeparator=' ',
                  tagsLimit=-1,
                  fileUrl='',
                  appendExtension=True,
                  bookmark=False,
                  searchTags='',
                  useTranslatedTag=False,
                  tagTranslationLocale="en") -> str:
    '''Build the filename from given info to the given format.'''
    global _config
    if artistInfo is None:
        artistInfo = imageInfo.artist

    # Get the image extension
    fileUrl = os.path.basename(fileUrl)
    imageExtension = ""
    imageFile = fileUrl
    if fileUrl.find(".") > 0:
        splittedUrl = fileUrl.split('.')
        imageFile = splittedUrl[0]
        imageExtension = splittedUrl[1]
        imageExtension = imageExtension.split('?')[0]

    # Issue #940
    if nameFormat.find('%force_extension') > -1:
        to_replace_ext = re.findall("(%force_extension{.*}%)", nameFormat)
        forced_ext = re.findall("{(.*)}", to_replace_ext[0])
        nameFormat = nameFormat.replace(to_replace_ext[0], "")
        imageExtension = forced_ext[0]

    # artist related
    nameFormat = nameFormat.replace('%artist%', replace_path_separator(artistInfo.artistName))
    nameFormat = nameFormat.replace('%member_id%', str(artistInfo.artistId))
    nameFormat = nameFormat.replace('%member_token%', artistInfo.artistToken)

    # sketch related
    if hasattr(artistInfo, "sketchArtistId"):
        nameFormat = nameFormat.replace('%sketch_member_id%', str(artistInfo.sketchArtistId))

    # image related
    nameFormat = nameFormat.replace('%title%', replace_path_separator(imageInfo.imageTitle))
    nameFormat = nameFormat.replace('%image_id%', str(imageInfo.imageId))
    nameFormat = nameFormat.replace('%works_date%', imageInfo.worksDate)
    nameFormat = nameFormat.replace('%works_date_only%', imageInfo.worksDate.split(' ')[0])

    # Issue #1064
    if hasattr(imageInfo, "translated_work_title") and len(imageInfo.translated_work_title) > 0:
        nameFormat = nameFormat.replace('%translated_title%', replace_path_separator(imageInfo.translated_work_title))
    else:
        nameFormat = nameFormat.replace('%translated_title%', replace_path_separator(imageInfo.imageTitle))

    # formatted works date/time, ex. %works_date_fmt{%Y-%m-%d}%
    if nameFormat.find("%works_date_fmt") > -1:
        to_replace = re.findall("(%works_date_fmt{.*}%)", nameFormat)
        date_format = re.findall("{(.*)}", to_replace[0])
        nameFormat = nameFormat.replace(to_replace[0], imageInfo.worksDateDateTime.strftime(date_format[0]))

    nameFormat = nameFormat.replace('%works_res%', imageInfo.worksResolution)
    nameFormat = nameFormat.replace('%urlFilename%', imageFile)
    nameFormat = nameFormat.replace('%searchTags%', replace_path_separator(searchTags))

    # date
    nameFormat = nameFormat.replace('%date%', date.today().strftime('%Y%m%d'))

    # formatted date/time, ex. %date_fmt{%Y-%m-%d}%
    if nameFormat.find("%date_fmt") > -1:
        to_replace2 = re.findall("(%date_fmt{.*}%)", nameFormat)
        date_format2 = re.findall("{(.*)}", to_replace2[0])
        nameFormat = nameFormat.replace(to_replace2[0], datetime.today().strftime(date_format2[0]))

    # get the page index & big mode if manga
    page_index = ''
    page_number = ''
    page_big = ''
    if imageInfo.imageMode == 'manga':
        # not working for fanbox due to url filename doesn't have _p0
        idx = __re_manga_index.findall(fileUrl)
        if len(idx) > 0:
            page_index = idx[0]
            page_number = str(int(page_index) + 1)
            padding = len(str(imageInfo.imageCount)) or 1
            page_number = str(page_number)
            page_number = page_number.zfill(padding)
        if fileUrl.find('_big') > -1 or fileUrl.find('_m') <= -1:
            page_big = 'big'
    nameFormat = nameFormat.replace('%page_big%', page_big)
    nameFormat = nameFormat.replace('%page_index%', page_index)
    nameFormat = nameFormat.replace('%page_number%', page_number)

    # Manga Series related
    if hasattr(imageInfo, "seriesNavData") and imageInfo.seriesNavData:
        nameFormat = nameFormat.replace('%manga_series_order%', str(imageInfo.seriesNavData['order']))
        nameFormat = nameFormat.replace('%manga_series_id%', str(imageInfo.seriesNavData['seriesId']))
        nameFormat = nameFormat.replace('%manga_series_title%', imageInfo.seriesNavData['title'])
    else:
        nameFormat = nameFormat.replace('%manga_series_order%', '')
        nameFormat = nameFormat.replace('%manga_series_id%', '')
        nameFormat = nameFormat.replace('%manga_series_title%', '')

    if tagsSeparator == '%space%':
        tagsSeparator = ' '
    if tagsSeparator == '%ideo_space%':
        tagsSeparator = u'\u3000'

    image_tags = imageInfo.imageTags
    if tagsLimit != -1:
        tagsLimit = tagsLimit if tagsLimit < len(imageInfo.imageTags) else len(imageInfo.imageTags)
        image_tags = image_tags[0:tagsLimit]

    # 701
    if useTranslatedTag:
        for idx, tag in enumerate(image_tags):
            for translated_tags in imageInfo.tags:
                if translated_tags.tag == tag:
                    image_tags[idx] = translated_tags.get_translation(tagTranslationLocale)
                    break

    tags = tagsSeparator.join(image_tags)

    r18Dir = ""
    if "R-18G" in imageInfo.imageTags:
        r18Dir = "R-18G"
    elif "R-18" in imageInfo.imageTags:
        r18Dir = "R-18"
    nameFormat = nameFormat.replace('%R-18%', r18Dir)
    nameFormat = nameFormat.replace('%tags%', replace_path_separator(tags))
    nameFormat = nameFormat.replace('&#039;', '\'')  # Yavos: added html-code for "'" - works only when ' is excluded from __badchars__

    if bookmark:  # from member bookmarks
        nameFormat = nameFormat.replace('%bookmark%', 'Bookmarks')
        nameFormat = nameFormat.replace('%original_member_id%', str(imageInfo.originalArtist.artistId))
        nameFormat = nameFormat.replace('%original_member_token%', imageInfo.originalArtist.artistToken)
        nameFormat = nameFormat.replace('%original_artist%', replace_path_separator(imageInfo.originalArtist.artistName))
    else:
        nameFormat = nameFormat.replace('%bookmark%', '')
        nameFormat = nameFormat.replace('%original_member_id%', str(artistInfo.artistId))
        nameFormat = nameFormat.replace('%original_member_token%', artistInfo.artistToken)
        nameFormat = nameFormat.replace('%original_artist%', replace_path_separator(artistInfo.artistName))

    if imageInfo.bookmark_count > 0:
        nameFormat = nameFormat.replace('%bookmark_count%', str(imageInfo.bookmark_count))
        if '%bookmarks_group%' in nameFormat:
            nameFormat = nameFormat.replace('%bookmarks_group%', calculate_group(imageInfo.bookmark_count))
    else:
        nameFormat = nameFormat.replace('%bookmark_count%', '')
        nameFormat = nameFormat.replace('%bookmarks_group%', '')

    if imageInfo.image_response_count > 0:
        nameFormat = nameFormat.replace('%image_response_count%', str(imageInfo.image_response_count))
    else:
        nameFormat = nameFormat.replace('%image_response_count%', '')

    # clean up double space
    while nameFormat.find('  ') > -1:
        nameFormat = nameFormat.replace('  ', ' ')

    # clean up double slash
    while nameFormat.find('//') > -1 or nameFormat.find('\\\\') > -1:
        nameFormat = nameFormat.replace('//', '/').replace('\\\\', '\\')

    if appendExtension:
        nameFormat = nameFormat.strip() + '.' + imageExtension

    if _config and len(_config.customCleanUpRe) > 0:
        nameFormat = re.sub(_config.customCleanUpRe, '', nameFormat)

    return nameFormat.strip()


# Issue #956
def get_hash(path: str, method="md5") -> str:
    hash_str = ""
    hash_method = None
    if method == "md5":
        hash_method = md5
    elif method == "sha1":
        hash_method = sha1
    elif method == "sha256":
        hash_method = sha256
    else:
        raise PixivException(msg=f"Invalid hash function {method}")

    with open(path) as file, mmap(file.fileno(), 0, access=ACCESS_READ) as file:
        hash_str = hash_method(file).hexdigest()
    return hash_str


def calculate_group(count):
    # follow rules from https://dic.pixiv.net/a/users%E5%85%A5%E3%82%8A
    if count >= 100 and count < 250:
        return '100'
    elif count >= 250 and count < 500:
        return '250'
    elif count >= 500 and count < 1000:
        return '500'
    elif count >= 1000 and count < 5000:
        return '1000'
    elif count >= 5000 and count < 10000:
        return '5000'
    elif count >= 10000:
        return '10000'
    else:
        return ''


def safePrint(msg, newline=True, end=None):
    """Print empty string if UnicodeError raised."""
    if not isinstance(msg, str):
        print(f"{msg}", end=' ')
    for msgToken in msg.split(' '):
        try:
            print(msgToken, end=' ')
        except UnicodeError:
            print(('?' * len(msgToken)), end=' ')

    if end is not None:
        print("", end=end)
    elif newline:
        print("")


def set_console_title(title):
    try:
        if platform.system() == "Windows":
            subprocess.call('title' + ' ' + title, shell=True)
        else:
            sys.stdout.write(f'\33]0;{title}\a')
            sys.stdout.flush()
    except FileNotFoundError:
        print_and_log("error", f"Cannot set console title to {title}")
    except AttributeError:
        # Issue #1065
        pass


def clearScreen():
    if platform.system() == "Windows":
        subprocess.call('cls', shell=True)
    else:
        subprocess.call('clear', shell=True)


def start_irfanview(dfilename, irfanViewPath, start_irfan_slide=False, start_irfan_view=False):
    print_and_log('info', 'starting IrfanView...')
    if os.path.exists(dfilename):
        ivpath = irfanViewPath + os.sep + 'i_view32.exe'  # get first part from config.ini
        ivpath = ivpath.replace('\\\\', '\\')
        ivpath = ivpath.replace('\\', os.sep)
        info = None
        if start_irfan_slide:
            info = subprocess.STARTUPINFO()
            info.dwFlags = 1
            info.wShowWindow = 6  # start minimized in background (6)
            ivcommand = ivpath + ' /slideshow=' + dfilename
            logger.info(ivcommand)
            subprocess.Popen(ivcommand)
        elif start_irfan_view:
            ivcommand = ivpath + ' /filelist=' + dfilename
            logger.info(ivcommand)
            subprocess.Popen(ivcommand, startupinfo=info)
    else:
        print_and_log('error', u'could not load' + dfilename)


def open_text_file(filename, mode='r', encoding='utf-8'):
    ''' taken from: http://www.velocityreviews.com/forums/t328920-remove-bom-from-string-read-from-utf-8-file.html'''
    hasBOM = False
    if os.path.isfile(filename):
        f = open(filename, 'rb')
        header = f.read(4)
        f.close()

        # Don't change this to a map, because it is ordered
        encodings = [(codecs.BOM_UTF32, 'utf-32'),
                     (codecs.BOM_UTF16, 'utf-16'),
                     (codecs.BOM_UTF8, 'utf-8')]

        for h, e in encodings:
            if header.startswith(h):
                encoding = e
                hasBOM = True
                break

    f = codecs.open(filename, mode, encoding)
    # Eat the byte order mark
    if hasBOM:
        f.read(1)
    return f


def create_avabg_filename(artistModel, targetDir, format_src):
    filename_avatar = ""
    filename_bg = ""

    image = PixivImage(parent=artistModel)

    # Issue #795
    if artistModel.artistAvatar.find('no_profile') == -1:
        # Download avatar using custom name, refer issue #174
        if format_src.avatarNameFormat != "":
            tmpfilename = make_filename(format_src.avatarNameFormat,
                                        image,
                                        tagsSeparator=_config.tagsSeparator,
                                        tagsLimit=_config.tagsLimit,
                                        fileUrl=artistModel.artistAvatar,
                                        appendExtension=True)
            filename_avatar = sanitize_filename(tmpfilename, targetDir)
        else:
            filenameFormat = format_src.filenameFormat
            if filenameFormat.find(os.sep) == -1:
                filenameFormat = os.sep + filenameFormat
            filenameFormat = os.sep.join(filenameFormat.split(os.sep)[:-1])
            tmpfilename = make_filename(filenameFormat,
                                        image,
                                        tagsSeparator=_config.tagsSeparator,
                                        tagsLimit=_config.tagsLimit,
                                        fileUrl=artistModel.artistAvatar,
                                        appendExtension=False)
            filename_avatar = sanitize_filename(tmpfilename + os.sep + 'folder.' + artistModel.artistAvatar.rsplit(".", 1)[1], targetDir)

    if artistModel.artistBackground is not None and artistModel.artistBackground.startswith("http"):
        if format_src.backgroundNameFormat != "" and format_src.avatarNameFormat != format_src.backgroundNameFormat:
            tmpfilename = make_filename(format_src.backgroundNameFormat,
                                        image,
                                        tagsSeparator=_config.tagsSeparator,
                                        tagsLimit=_config.tagsLimit,
                                        fileUrl=artistModel.artistBackground,
                                        appendExtension=True)
            filename_bg = sanitize_filename(tmpfilename, targetDir)
        else:
            if format_src.avatarNameFormat != "":
                tmpfilename = make_filename(format_src.avatarNameFormat,
                                            image,
                                            tagsSeparator=_config.tagsSeparator,
                                            tagsLimit=_config.tagsLimit,
                                            fileUrl=artistModel.artistBackground,
                                            appendExtension=True)
                tmpfilename = tmpfilename.split(os.sep)
                tmpfilename[-1] = "bg_" + tmpfilename[-1]
                filename_bg = sanitize_filename(os.sep.join(tmpfilename), targetDir)
            else:
                filenameFormat = format_src.filenameFormat
                if filenameFormat.find(os.sep) == -1:
                    filenameFormat = os.sep + filenameFormat
                filenameFormat = os.sep.join(filenameFormat.split(os.sep)[:-1])
                tmpfilename = make_filename(filenameFormat,
                                            image,
                                            tagsSeparator=_config.tagsSeparator,
                                            tagsLimit=_config.tagsLimit,
                                            fileUrl=artistModel.artistBackground,
                                            appendExtension=False)
                filename_bg = sanitize_filename(tmpfilename + os.sep + 'bg_folder.' + artistModel.artistBackground.rsplit(".", 1)[1], targetDir)

    return (filename_avatar, filename_bg)


def we_are_frozen():
    """Returns whether we are frozen via py2exe.
        This will affect how we find out where we are located.
        Get actual script directory
        http://www.py2exe.org/index.cgi/WhereAmI"""

    return hasattr(sys, "frozen")


def module_path():
    """ This will get us the program's directory,
  even if we are frozen using py2exe"""

    if we_are_frozen():
        return os.path.dirname(sys.executable)

    return os.path.dirname(__file__)


def speed_in_str(totalSize, totalTime):
    if totalTime > 0:
        speed = totalSize / totalTime
        if speed < 1024:
            return "{0:.0f} B/s".format(speed)
        speed = speed / 1024
        if speed < 1024:
            return "{0:.2f} KiB/s".format(speed)
        speed = speed / 1024
        if speed < 1024:
            return "{0:.2f} MiB/s".format(speed)
        speed = speed / 1024
        return "{0:.2f} GiB/s".format(speed)
    else:
        return " infinity B/s"


def size_in_str(totalSize):
    totalSize = float(totalSize)
    if totalSize < 1024:
        return "{0:.0f} B".format(totalSize)
    totalSize = totalSize / 1024
    if totalSize < 1024:
        return "{0:.2f} KiB".format(totalSize)
    totalSize = totalSize / 1024
    if totalSize < 1024:
        return "{0:.2f} MiB".format(totalSize)
    totalSize = totalSize / 1024
    return "{0:.2f} GiB".format(totalSize)


def dump_html(filename, html_text):
    isDumpEnabled = True
    filename = sanitize_filename(filename)
    if _config is not None:
        isDumpEnabled = _config.enableDump
        if _config.enableDump:
            if len(_config.skipDumpFilter) > 0:
                matchResult = re.findall(_config.skipDumpFilter, filename)
                if matchResult is not None and len(matchResult) > 0:
                    isDumpEnabled = False

    if html_text is not None and len(html_text) == 0:
        print_and_log('info', 'Empty Html.')
        return ""

    if isDumpEnabled:
        if not isinstance(html_text, str):
            html_text = str(html_text)
        if isinstance(html_text, str):
            html_text = html_text.encode()
        try:
            dump = open(filename, 'wb')
            dump.write(html_text)
            dump.close()
            return filename
        except IOError as ex:
            print_and_log('error', str(ex))
        print_and_log("info", "Dump File created: {0}".format(filename))
    else:
        print_and_log('info', 'Dump not enabled.')
    return ""


def print_and_log(level, msg, exception=None, newline=True, end=None):
    if level == 'debug':
        get_logger().debug(msg)
    else:
        if level == 'info':
            safePrint(msg, newline, end)
            get_logger().info(msg)
        elif level == 'warn':
            safePrint(Fore.YELLOW + f"{msg}" + Style.RESET_ALL, newline, end)
            get_logger().warning(msg)
        elif level == 'error':
            safePrint(Fore.RED + f"{msg}" + Style.RESET_ALL, newline, end)
            if exception is None:
                get_logger().error(msg)
            else:
                get_logger().error(msg, exception)
            get_logger().error(traceback.format_exc())
        elif level is None:
            safePrint(msg, newline, end)


def have_strings(page, strings):
    for string in strings:
        pattern = re.compile(string)
        test_2 = pattern.findall(str(page))
        if len(test_2) > 0:
            if len(test_2[-1]) > 0:
                return True
    return False


def get_ids_from_csv(ids_str, is_string=False):
    ids = []
    if is_string:
        ids = re.findall(r"(?:@|^|https:\/\/(?!www|sketch\.)|\s|,)(?!https:)(\d+|\S[\S]*\S)", ids_str)
        if not ids:
            print_and_log('error', u"Input: {0} is not valid".format(ids_str))
    else:
        ids = re.findall(r"(?:series|users|\s|,|^|artworks|posts)\/?(\d+)", ids_str)
        if not ids:
            print_and_log('error', u"Input: {0} is not valid".format(ids_str))
    if len(ids) > 1:
        print_and_log('info', u"Found {0} ids".format(len(ids)))
    return ids


def clear_all():
    all_vars = [var for var in globals() if (var[:2], var[-2:]) != ("__", "__") and var != "clear_all"]
    for var in all_vars:
        del globals()[var]


# # pylint: disable=W0612
# def unescape_charref(data, encoding):
#     ''' Replace default mechanize method in _html.py'''
#     try:
#         name, base = data, 10
#         if name.lower().startswith("x"):
#             name, base = name[1:], 16
#         try:
#             int(name, base)
#         except ValueError:
#             base = 16
#         uc = chr(int(name, base))
#         if encoding is None:
#             return uc

#         try:
#             repl = uc.encode(encoding)
#         except UnicodeError:
#             repl = "&#%s;" % data
#         return repl
#     except BaseException:
#         return data


def get_ugoira_size(ugoName):
    size = 0
    try:
        with zipfile.ZipFile(ugoName) as z:
            animJson = z.read("animation.json")
            size = json.loads(animJson)['zipSize']
            z.close()
    except zipfile.BadZipFile:
        print_and_log('error', u'Failed to read ugoira size from json data: {0}, using filesize.'.format(ugoName))
        size = os.path.getsize(ugoName)
    return size


def check_file_exists(overwrite, filename, file_size, old_size, backup_old_file):
    if not overwrite and int(file_size) == old_size:
        print_and_log('warn', f"\tFile exist! (Identical Size) ==> {filename}.")
        return PixivConstant.PIXIVUTIL_SKIP_DUPLICATE
    else:
        if backup_old_file:
            split_name = filename.rsplit(".", 1)
            new_name = filename + "." + str(int(time.time()))
            if len(split_name) == 2:
                new_name = split_name[0] + "." + str(int(time.time())) + "." + split_name[1]
            print_and_log('warn', f"\t Found file with different file size ==> {filename}, backing up to: {new_name}.")
            os.rename(filename, new_name)
        else:
            print_and_log('warn', f"\tFound file with different file size ==> {filename}, removing old file (old: {old_size} vs new: {file_size})")
            os.remove(filename)
        return PixivConstant.PIXIVUTIL_OK


def print_delay(retryWait):
    repeat = range(1, retryWait)
    for t in repeat:
        print_and_log(None, f"{t}", newline=False)
        time.sleep(1)
    print_and_log(None, "")


def create_custom_request(url, config, referer='https://www.pixiv.net', head=False):
    if config.useProxy:
        proxy = urllib.request.ProxyHandler(config.proxy)
        opener = urllib.request.build_opener(proxy)
        urllib.request.install_opener(opener)
    req = mechanize.Request(url)
    req.add_header('Referer', referer)
    # print_and_log('info', u"Using Referer: " + str(referer))
    get_logger().info(f"Using Referer: {referer}")

    if head:
        req.get_method = lambda: 'HEAD'
    else:
        req.get_method = lambda: 'GET'

    return req


def makeSubdirs(filename):
    directory = os.path.dirname(filename)
    if not os.path.exists(directory) and len(directory) > 0:
        print_and_log('info', u'Creating directory: ' + directory)
        os.makedirs(directory)


def download_image(url, filename, res, file_size, overwrite):
    ''' Actual download, return the downloaded filesize and saved filename.'''
    start_time = datetime.now()

    # try to save to the given filename + .pixiv extension if possible
    try:
        makeSubdirs(filename)
        save = open(filename + '.pixiv', 'wb+', 4096)
    except IOError:
        print_and_log('error', u"Error at download_image(): Cannot save {0} to {1}: {2}".format(url, filename, sys.exc_info()))

        # get the actual server filename and use it as the filename for saving to current app dir
        filename = os.path.split(url)[1]
        filename = filename.split("?")[0]
        filename = sanitize_filename(filename)
        save = open(filename + '.pixiv', 'wb+', 4096)
        print_and_log('info', u'File is saved to ' + filename)

    # download the file
    prev = 0
    curr = 0
    msg_len = 0
    try:
        while True:
            save.write(res.read(PixivConstant.BUFFER_SIZE))
            curr = save.tell()
            msg_len = print_progress(curr, file_size, msg_len)

            # check if downloaded file is complete
            if file_size > 0 and curr == file_size:
                total_time = (datetime.now() - start_time).total_seconds()
                print_and_log(None, f' Completed in {total_time}s ({speed_in_str(file_size, total_time)})')
                break

            elif curr == prev:  # no file size info
                total_time = (datetime.now() - start_time).total_seconds()
                print_and_log(None, f' Completed in {total_time}s ({speed_in_str(curr, total_time)})')
                break

            prev = curr

    finally:
        if save is not None:
            save.close()

        completed = True
        if file_size > 0 and curr < file_size:
            # File size is known and downloaded file is smaller
            print_and_log('error', u'Downloaded file incomplete! {0:9} of {1:9} Bytes'.format(curr, file_size))
            print_and_log('error', u'Filename = ' + filename)
            print_and_log('error', u'URL      = {0}'.format(url))
            completed = False
        elif curr == 0:
            # No data received.
            print_and_log('error', u'No data received!')
            print_and_log('error', u'Filename = ' + filename)
            print_and_log('error', u'URL      = {0}'.format(url))
            completed = False

        if completed:
            if overwrite and os.path.exists(filename):
                os.remove(filename)
            os.rename(filename + '.pixiv', filename)
        else:
            os.remove(filename + '.pixiv')

        del save

    return (curr, filename)


def print_progress(curr, total, max_msg_length=80):
    # [12345678901234567890]
    # [████████------------]
    animBarLen = 20

    if total > 0:
        complete = int((curr * animBarLen) / total)
        remainder = (((curr * animBarLen) % total) / total)
        use_half_block = (remainder <= 0.5) and remainder > 0.1
        if use_half_block:
            with_half_block = f"{'█' * (complete - 1)}▌"
            msg = f"\r[{with_half_block:{animBarLen}}] {size_in_str(curr)} of {size_in_str(total)}"
        else:
            msg = f"\r[{'█' * complete:{animBarLen}}] {size_in_str(curr)} of {size_in_str(total)}"

    else:
        # indeterminite
        pos = curr % (animBarLen + 3)  # 3 corresponds to the length of the '███' below
        anim = '.' * animBarLen + '███' + '.' * animBarLen
        # Use nested replacement field to specify the precision value. This limits the maximum print
        # length of the progress bar. As pos changes, the starting print position of the anim string
        # also changes, thus producing the scrolling effect.
        msg = f'\r[{anim[animBarLen + 3 - pos:]:.{animBarLen}}] {size_in_str(curr)}'

    curr_msg_length = len(msg)
    print_and_log(None, msg.ljust(max_msg_length, " "), newline=False)

    return curr_msg_length if curr_msg_length > max_msg_length else max_msg_length


def generate_search_tag_url(tags,
                            page,
                            title_caption=False,
                            wild_card=False,
                            sort_order='date_d',
                            start_date=None,
                            end_date=None,
                            member_id=None,
                            r18mode=False,
                            blt=0,
                            type_mode="a"):
    url = ""
    date_param = ""
    page_param = ""

    if start_date is not None:
        date_param = f"{date_param}&scd={start_date}"
    if end_date is not None:
        date_param = f"{date_param}&ecd={end_date}"
    if page is not None and int(page) > 1:
        page_param = f"&p={page}"

    if member_id is not None:
        url = f'https://www.pixiv.net/member_illust.php?id={member_id}&tag={tags}&p={page}'
    else:
        root_url = 'https://www.pixiv.net/ajax/search/artworks'
        search_mode = ""
        if title_caption:
            search_mode = '&s_mode=s_tc'
            print_and_log(None, "Using Title Match (s_tc)")
        elif wild_card:
            # partial match
            search_mode = '&s_mode=s_tag'
            print_and_log(None, "Using Partial Match (s_tag)")
        else:
            search_mode = '&s_mode=s_tag_full'
            print_and_log(None, "Using Full Match (s_tag_full)")

        bookmark_limit_premium = ""
        if blt is not None and blt > 0:
            bookmark_limit_premium = f'&blt={blt}'

        if type_mode == "i":
            type_mode = "illust_and_ugoira"
        elif type_mode == "m":
            type_mode = "manga"
        else:
            type_mode = "all"
        type_mode = f"&type={type_mode}"

        # https://www.pixiv.net/ajax/search/artworks/k-on?word=k-on&order=date_d&mode=all&p=1&s_mode=s_tag_full&type=all&lang=en
        url = f"{root_url}/{tags}?word={tags}{date_param}{page_param}{search_mode}{bookmark_limit_premium}{type_mode}"

    if r18mode:
        url = f'{url}&mode=r18'

    if sort_order in ('date', 'date_d', 'popular_d', 'popular_male_d', 'popular_female_d'):
        url = f'{url}&order={sort_order}'

    # encode to ascii
    # url = url.encode('iso_8859_1')

    return url


def write_url_in_description(image: Union[PixivImage, FanboxPost], blacklistRegex, filenamePattern):
    valid_url = list()
    if len(image.descriptionUrlList) > 0:
        # filter first
        if len(blacklistRegex) > 0:
            for link in image.descriptionUrlList:
                res = re.findall(blacklistRegex, link)
                if len(res) == 0:
                    valid_url.append(link)
        else:
            valid_url = image.descriptionUrlList

    # then write
    if len(valid_url) > 0:
        if len(filenamePattern) == 0:
            filenamePattern = "url_list_%Y%m%d"
        filename = date.today().strftime(filenamePattern) + ".txt"
        makeSubdirs(filename)
        info = codecs.open(filename, 'a', encoding='utf-8')

        # implement #1002
        if isinstance(image, FanboxPost):
            info.write(f"# Fanbox Author ID: {image.parent.artistId} Post ID: {image.imageId}\r\n")
        else:
            info.write(f"# Pixiv Author ID: {image.artist.artistId} Image ID: {image.imageId}\r\n")

        for link in valid_url:
            info.write(link + "\r\n")
        info.close()


def ugoira2gif(ugoira_file, exportname, fmt='gif', image=None):
    print_and_log('info', 'Processing ugoira to animated gif...')
    # Issue #802 use ffmpeg to convert to gif
    if len(_config.gifParam) == 0:
        _config.gifParam = "-filter_complex \"[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle\""
    convert_ugoira(ugoira_file,
                   exportname,
                   ffmpeg=_config.ffmpeg,
                   codec=None,
                   param=_config.gifParam,
                   extension="gif",
                   image=image)


def ugoira2apng(ugoira_file, exportname, image=None):
    print_and_log('info', 'Processing ugoira to apng...')
    # fix #796 convert apng using ffmpeg
    if len(_config.apngParam) == 0:
        _config.apngParam = "-vf \"setpts=PTS-STARTPTS,hqdn3d=1.5:1.5:6:6\" -plays 0"
    convert_ugoira(ugoira_file,
                   exportname,
                   ffmpeg=_config.ffmpeg,
                   codec="apng",
                   param=_config.apngParam,
                   extension="apng",
                   image=image)


def ugoira2webp(ugoira_file, exportname, image=None):
    print_and_log('info', 'Processing ugoira to webp...')
    if len(_config.webpParam) == 0:
        _config.webpParam = "-lossless 0 -q:v 90 -loop 0 -vsync 2 -r 999"
    convert_ugoira(ugoira_file,
                   exportname,
                   ffmpeg=_config.ffmpeg,
                   codec=_config.webpCodec,
                   param=_config.webpParam,
                   extension="webp",
                   image=image)


def ugoira2webm(ugoira_file, exportname, codec="libvpx-vp9", extension="webm", image=None):
    print_and_log('info', 'Processing ugoira to webm...')
    if len(_config.ffmpegParam) == 0:
        _config.ffmpegParam = "-vsync 2 -r 999 -pix_fmt yuv420p"
    convert_ugoira(ugoira_file,
                   exportname,
                   ffmpeg=_config.ffmpeg,
                   codec=codec,
                   param=_config.ffmpegParam,
                   extension=extension,
                   image=image)


def convert_ugoira(ugoira_file, exportname, ffmpeg, codec, param, extension, image=None):
    ''' modified based on https://github.com/tsudoko/ugoira-tools/blob/master/ugoira2webm/ugoira2webm.py '''
    # if not os.path.exists(os.path.abspath(ffmpeg)):
    #     raise PixivException(f"Cannot find ffmpeg executables => {ffmpeg}", errorCode=PixivException.MISSING_CONFIG)

    d = tempfile.mkdtemp(prefix="convert_ugoira")
    d = d.replace(os.sep, '/')

    # Issue #1035
    if not os.path.exists(d):
        new_temp = os.path.abspath(f"ugoira_{int(datetime.now().timestamp())}")
        new_temp = new_temp.replace(os.sep, '/')
        os.makedirs(new_temp)
        print_and_log("warn", f"Cannot create temp folder at {d}, using current folder as the temp location => {new_temp}")
        d = new_temp
        # check again if still fail
        if not os.path.exists(d):
            raise PixivException(f"Cannot create temp folder => {d}", errorCode=PixivException.OTHER_ERROR)

    if exportname is None or len(exportname) == 0:
        name = '.'.join(ugoira_file.split('.')[:-1])
        exportname = f"{os.path.basename(name)}.{extension}"

    tempname = d + "/temp." + extension

    cmd = f"{ffmpeg} -y -safe 0 -i \"{d}/i.ffconcat\" -c:v {codec} {param} \"{tempname}\""
    if codec is None:
        cmd = f"{ffmpeg} -y -safe 0 -i \"{d}/i.ffconcat\" {param} \"{tempname}\""

    try:
        frames = {}
        ffconcat = "ffconcat version 1.0\n"

        with zipfile.ZipFile(ugoira_file) as f:
            f.extractall(d)

        with open(d + "/animation.json") as f:
            frames = json.load(f)['frames']

        for i in frames:
            ffconcat += "file " + i['file'] + '\n'
            ffconcat += "duration " + str(float(i['delay']) / 1000) + '\n'
        # Fix ffmpeg concat demuxer as described in issue #381
        # this will increase the frame count, but will fix the last frame timestamp issue.
        ffconcat += "file " + frames[-1]['file'] + '\n'

        with open(d + "/i.ffconcat", "w") as f:
            f.write(ffconcat)

        ffmpeg_args = shlex.split(cmd)
        get_logger().info(f"[convert_ugoira()] running with cmd: {cmd}")
        p = subprocess.Popen(ffmpeg_args, stderr=subprocess.PIPE)

        # progress report
        chatter = ""
        print_and_log('info', f"Start encoding {exportname}")
        while p.stderr:
            buff = p.stderr.readline().decode('utf-8').rstrip('\n')
            chatter += buff
            if buff.endswith("\r"):
                if _config.verboseOutput:
                    print(chatter.strip())
                elif chatter.find("frame=") > 0 \
                     or chatter.lower().find("stream") > 0:
                    print(chatter.strip())
                elif chatter.lower().find("error") > 0 \
                     or chatter.lower().find("could not") > 0 \
                     or chatter.lower().find("unknown") > 0 \
                     or chatter.lower().find("invalid") > 0 \
                     or chatter.lower().find("trailing options") > 0 \
                     or chatter.lower().find("cannot") > 0 \
                     or chatter.lower().find("can't") > 0:
                    print_and_log("error", chatter.strip())
                chatter = ""
            if len(buff) == 0:
                break

        ret = p.wait()

        if(p.returncode != 0):
            print_and_log("error", f"Failed when converting image using {cmd} ==> ffmpeg return exit code={p.returncode}, expected to return 0.")
        else:
            print_and_log("info", f"- Done with status = {ret}")
            shutil.move(tempname, exportname)

        # set last-modified and last-accessed timestamp
        if image is not None and _config.setLastModified and exportname is not None and os.path.isfile(exportname):
            ts = time.mktime(image.worksDateDateTime.timetuple())
            os.utime(exportname, (ts, ts))
    except FileNotFoundError:
        print_and_log("error", f"Failed when converting, ffmpeg command used: {cmd}")
        raise

    finally:
        if os.path.exists(d):
            shutil.rmtree(d)
        print()


def parse_date_time(worksDate, dateFormat):
    if dateFormat is not None and len(dateFormat) > 0 and '%' in dateFormat:
        # use the user defined format
        worksDateDateTime = None
        try:
            worksDateDateTime = datetime.strptime(worksDate, dateFormat)
        except ValueError:
            get_logger().exception('Error when parsing datetime: %s using date format %s', worksDate, dateFormat)
            raise
    else:
        worksDate = worksDate.replace(u'/', u'-')
        if worksDate.find('-') > -1:
            try:
                worksDateDateTime = datetime.strptime(worksDate, u'%m-%d-%Y %H:%M')
            except ValueError:
                get_logger().exception('Error when parsing datetime: %s', worksDate)
                worksDateDateTime = datetime.strptime(worksDate.split(" ")[0], u'%Y-%m-%d')
        else:
            tempDate = worksDate.replace(u'年', '-').replace(u'月', '-').replace(u'日', '')
            worksDateDateTime = datetime.strptime(tempDate, '%Y-%m-%d %H:%M')

    return worksDateDateTime


def encode_tags(tags):
    if not tags.startswith("%"):
        try:
            # Encode the tags
            tags = tags.replace(' ', '%%space%%')
            tags = urllib.parse.quote_plus(tags).replace('%25%25space%25%25', '%20')
        except UnicodeDecodeError:
            try:
                # from command prompt
                tags = urllib.request.quote(tags.decode(sys.stdout.encoding).encode("utf8"))
            except UnicodeDecodeError:
                print_and_log('error', 'Cannot decode tags, use URL Encoder (http://meyerweb.com/eric/tools/dencoder/) and paste result.')
    return tags


def check_version(br, config=None):
    if br is None:
        import PixivBrowserFactory
        br = PixivBrowserFactory.getBrowser(config=config)
    result = br.open_with_retry("https://raw.githubusercontent.com/Nandaka/PixivUtil2/master/PixivConstant.py", retry=3)
    page = result.read().decode('utf-8')
    result.close()
    latest_version_full = re.findall(r"PIXIVUTIL_VERSION = '(\d+)(.*)'", page)

    latest_version_int = int(latest_version_full[0][0])
    curr_version_int = int(re.findall(r"(\d+)", PixivConstant.PIXIVUTIL_VERSION)[0])
    is_beta = True if latest_version_full[0][1].find("beta") >= 0 else False
    if is_beta and not config.notifyBetaVersion:
        return
    url = "https://github.com/Nandaka/PixivUtil2/releases"
    if latest_version_int > curr_version_int:
        if is_beta:
            print_and_log("info", "New beta version available: {0}".format(latest_version_full[0]))
        else:
            print_and_log("info", "New version available: {0}".format(latest_version_full[0]))
        if config.openNewVersion:
            webbrowser.open_new(url)


def decode_tags(tags):
    # decode tags.
    try:
        if tags.startswith("%"):
            search_tags = urllib.parse.unquote_plus(tags)
        else:
            search_tags = tags
    except UnicodeDecodeError:
        # From command prompt
        search_tags = tags.decode(sys.stdout.encoding).encode("utf8")
    return search_tags


def check_date_time(input_date):
    split = input_date.split("-")
    return date(int(split[0]), int(split[1]), int(split[2])).isoformat()


def get_start_and_end_date():
    start_date = None
    end_date = None
    while True:
        try:
            start_date = input('Start Date [YYYY-MM-DD]: ').rstrip("\r") or None
            if start_date is not None and len(start_date) == 10:
                start_date = check_date_time(start_date)
            break
        except Exception as e:
            print_and_log(None, str(e))

    while True:
        try:
            end_date = input('End Date [YYYY-MM-DD]: ').rstrip("\r") or None
            if end_date is not None and len(end_date) == 10:
                end_date = check_date_time(end_date)
            break
        except Exception as e:
            print_and_log(None, str(e))

    return start_date, end_date


def get_start_and_end_number(start_only=False, total_number_of_page=None):
    page_num = input('Start Page (default=1): ').rstrip("\r") or 1
    try:
        page_num = int(page_num)
    except BaseException:
        print_and_log(None, f"Invalid page number: {page_num}")
        raise

    end_page_num = 0
    if total_number_of_page is not None:
        end_page_num = int(total_number_of_page)
    else:
        if _config.numberOfPage > 0:
            print_and_log(None, f"Using numberOfPage from config = {_config.numberOfPage} as default.")
        end_page_num = _config.numberOfPage

    if not start_only:
        end_page_num = input(f'End Page (default= {end_page_num}, 0 for no limit): ').rstrip("\r") or end_page_num
        if end_page_num is not None:
            try:
                end_page_num = int(end_page_num)
                if page_num > end_page_num and end_page_num != 0:
                    print_and_log(None, "page_num is bigger than end_page_num, assuming as page count.")
                    end_page_num = page_num + end_page_num
            except BaseException:
                print_and_log(None, f"Invalid end page number: {end_page_num}")
                raise

    return page_num, end_page_num


def wait(result=None, config=None):
    if result == PixivConstant.PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT:
        return
    # Issue#276: add random delay for each post.
    if config is not None and config.downloadDelay > 0:
        delay = random.random() * config.downloadDelay
        message = "Wait for {0:.3}s".format(delay)
        print_and_log(None, message)
        time.sleep(delay)


def dummy_notifier(type=None, message=None, **kwargs):
    pass


def get_extension_from_url(url):
    o = urllib.parse.urlparse(url, scheme='', allow_fragments=True)
    ext = os.path.splitext(o.path)
    return ext[1]


# Issue 420
class LocalUTCOffsetTimezone(tzinfo):
    def __init__(self, offset=0, name=None):
        super(LocalUTCOffsetTimezone, self).__init__()
        self.offset = time.timezone * -1
        is_dst = time.localtime().tm_isdst
        self.name = time.tzname[0] if not is_dst and len(time.tzname) > 1 else time.tzname[1]

    def __str__(self):
        offset1 = abs(int(self.offset / 60 / 60))
        offset2 = abs(int(self.offset / 60 % 60))
        return "{0}{1:02d}:{2:02d}".format("-" if self.offset < 0 else "+", offset1, offset2)

    def __repr__(self):
        return self.__str__()

    def utcoffset(self, dt):
        return timedelta(seconds=self.offset)

    def tzname(self, dt):
        return self.name

    def dst(self, dt):
        return timedelta(0) if (time.localtime().tm_isdst == 0) else timedelta(seconds=time.timezone - time.altzone)

    def getTimeZoneOffset(self):
        offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
        return offset / 60 / 60 * -1


def parse_custom_clean_up_re(custom_clean_up_re_string):
    # need to use eval so can retain whitespace
    if custom_clean_up_re_string is not None and len(custom_clean_up_re_string) > 0:
        return eval(custom_clean_up_re_string)
    else:
        return ""


def parse_custom_sanitizer(bad_char_string):
    __custom_sanitizer_dic__.clear()
    default_replacement = "_"
    clean_string = ""

    temp_string = bad_char_string
    group_dic = {}

    match = re.search(r"%replace<default>\((.+?)\)%", temp_string)
    if match:
        temp_string = temp_string.replace(match.group(), "")
        default_replacement = match.group(1)
        clean_string += f"%replace<default>({default_replacement})%"

    for match in re.finditer(r"%(pattern|replace)<(.+?)>\((.*?)\)%", temp_string):
        temp_string = temp_string.replace(match.group(), "")
        kind = match.group(1)
        group_name = match.group(2)
        content = match.group(3)
        if group_name == "default":
            continue
        if group_name not in group_dic:
            group_dic[group_name] = {"pattern": None}
        group_dic[group_name][kind] = content

    if temp_string:
        temp_string = "".join(sorted(set(temp_string)))
        clean_string = temp_string + clean_string
        temp_string = "|".join([c if c not in r"$()*+.[]?^\{}|" else rf"\{c}" for c in temp_string])
        __custom_sanitizer_dic__["default"] = {"regex": re.compile(temp_string), "replace": default_replacement}

    for key, value in group_dic.items():
        if not value["pattern"]:
            continue
        __custom_sanitizer_dic__[key] = {
            "regex": re.compile(value["pattern"]),
            "replace": value.get("replace", default_replacement)
        }
        for k, v in value.items():
            clean_string += f"%{k}<{key}>({v})%"

    return clean_string
