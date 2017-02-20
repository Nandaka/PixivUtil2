# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import re
import os
import codecs
from HTMLParser import HTMLParser
import subprocess
import sys
import PixivModel
import PixivConstant
import logging
import logging.handlers
import zipfile
import time
import unicodedata
import json
import urllib2
import imageio
import shutil
import tempfile
from datetime import datetime, date
import traceback
import urllib
from apng import APNG

Logger = None
_config = None


def setConfig(config):
    global _config
    _config = config


def GetLogger(level=logging.DEBUG):
    '''Set up logging'''
    global Logger
    if Logger is None:
        script_path = module_path()
        Logger = logging.getLogger('PixivUtil' + PixivConstant.PIXIVUTIL_VERSION)
        Logger.setLevel(level)
        __logHandler__ = logging.handlers.RotatingFileHandler(script_path + os.sep + PixivConstant.PIXIVUTIL_LOG_FILE,
                                                              maxBytes=PixivConstant.PIXIVUTIL_LOG_SIZE,
                                                              backupCount=PixivConstant.PIXIVUTIL_LOG_COUNT)
        __formatter__ = logging.Formatter(PixivConstant.PIXIVUTIL_LOG_FORMAT)
        __logHandler__.setFormatter(__formatter__)
        Logger.addHandler(__logHandler__)
    return Logger


def setLogLevel(level):
    Logger.info("Setting log level to: " + level)
    GetLogger(level).setLevel(level)


if os.sep == '/':
    __badchars__ = re.compile(r'^\.|\.$|^ | $|^$|\?|:|<|>|\||\*|\"')
else:
    __badchars__ = re.compile(r'^\.|\.$|^ | $|^$|\?|:|<|>|/|\||\*|\"')
__badnames__ = re.compile(r'(aux|com[1-9]|con|lpt[1-9]|prn)(\.|$)')

__h__ = HTMLParser()
__re_manga_index = re.compile(r'_p(\d+)')


def sanitizeFilename(s, rootDir=None):
    '''Replace reserved character/name with underscore (windows), rootDir is not sanitized.'''
    # get the absolute rootdir
    if rootDir is not None:
        rootDir = os.path.abspath(rootDir)

    # Unescape '&amp;', '&lt;', and '&gt;'
    s = __h__.unescape(s)

    # Replace badchars and badnames with _
    name = __badchars__.sub('_', s)
    if __badnames__.match(name.lower()):
        name = '_' + name

    # Replace new line with space
    name = name.replace("\r", '')
    name = name.replace("\n", ' ')

    # Yavos: when foldername ends with "." PixivUtil won't find it
    while name.find('.\\') != -1:
        name = name.replace('.\\', '\\')

    name = name.replace('\\', os.sep)

    # Replace tab character with space
    name = name.replace('\t', ' ')

    # Strip leading/trailing space for each directory
    temp = name.split(os.sep)
    temp2 = list()
    for item in temp:
        temp2.append(item.strip())
    name = os.sep.join(temp2)

    if rootDir is not None:
        name = rootDir + os.sep + name

    # replace double os.sep
    while name.find(os.sep + os.sep) >= 0:
        name = name.replace(os.sep + os.sep, os.sep)

    # cut to 255 char
    if len(name) > 255:
        newLen = 250
        name = name[:newLen]

    # Remove unicode control character
    if isinstance(name, unicode):
        tempName = ""
        for c in name:
            if unicodedata.category(c) == 'Cc':
                tempName = tempName + '_'
            else:
                tempName = tempName + c
    else:
        tempName = name

    GetLogger().debug("Sanitized Filename: " + tempName.strip())

    return tempName.strip()


def makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', tagsLimit=-1, fileUrl='',
                 appendExtension=True, bookmark=False, searchTags=''):
    '''Build the filename from given info to the given format.'''
    if artistInfo is None:
        artistInfo = imageInfo.artist

    # Get the image extension
    fileUrl = os.path.basename(fileUrl)
    splittedUrl = fileUrl.split('.')
    imageExtension = splittedUrl[1]
    imageExtension = imageExtension.split('?')[0]

    # artist related
    nameFormat = nameFormat.replace('%artist%', artistInfo.artistName.replace(os.sep, '_'))
    nameFormat = nameFormat.replace('%member_id%', str(artistInfo.artistId))
    nameFormat = nameFormat.replace('%member_token%', artistInfo.artistToken)

    # image related
    nameFormat = nameFormat.replace('%title%', imageInfo.imageTitle.replace(os.sep, '_'))
    nameFormat = nameFormat.replace('%image_id%', str(imageInfo.imageId))
    nameFormat = nameFormat.replace('%works_date%', imageInfo.worksDate)
    nameFormat = nameFormat.replace('%works_date_only%', imageInfo.worksDate.split(' ')[0])
    # formatted works date/time, ex. %works_date_fmt{%Y-%m-%d}%
    if nameFormat.find("%works_date_fmt") > -1:
        to_replace = re.findall("(%works_date_fmt{.*}%)", nameFormat)
        date_format = re.findall("{(.*)}", to_replace[0])
        nameFormat = nameFormat.replace(to_replace[0], imageInfo.worksDateDateTime.strftime(date_format[0]))

    nameFormat = nameFormat.replace('%works_res%', imageInfo.worksResolution)
    nameFormat = nameFormat.replace('%works_tools%', imageInfo.worksTools)
    nameFormat = nameFormat.replace('%urlFilename%', splittedUrl[0])
    nameFormat = nameFormat.replace('%searchTags%', searchTags)

    # date
    nameFormat = nameFormat.replace('%date%', date.today().strftime('%Y%m%d'))
    # formatted date/time, ex. %date_fmt{%Y-%m-%d}%
    if nameFormat.find("%date_fmt") > -1:
        to_replace2 = re.findall("(%date_fmt{.*}%)", nameFormat)
        date_format2 = re.findall("{(.*)}", to_replace2[0])
        nameFormat = nameFormat.replace(to_replace2[0], date.today().strftime(date_format2[0]))

    # get the page index & big mode if manga
    page_index = ''
    page_number = ''
    page_big = ''
    if imageInfo.imageMode == 'manga':
        idx = __re_manga_index.findall(fileUrl)
        if len(idx) > 0:
            page_index = idx[0]
            page_number = str(int(page_index) + 1)
            padding = len(str(imageInfo.imageCount))
            page_number = str(page_number)
            page_number = page_number.zfill(padding)
        if fileUrl.find('_big') > -1 or not fileUrl.find('_m') > -1:
            page_big = 'big'
    nameFormat = nameFormat.replace('%page_big%', page_big)
    nameFormat = nameFormat.replace('%page_index%', page_index)
    nameFormat = nameFormat.replace('%page_number%', page_number)

    if tagsSeparator == '%space%':
        tagsSeparator = ' '
    if tagsSeparator == '%ideo_space%':
        tagsSeparator = u'\u3000'

    if tagsLimit != -1:
        tagsLimit = tagsLimit if tagsLimit < len(imageInfo.imageTags) else len(imageInfo.imageTags)
        imageInfo.imageTags = imageInfo.imageTags[0:tagsLimit]
    tags = tagsSeparator.join(imageInfo.imageTags)
    r18Dir = ""
    if "R-18G" in imageInfo.imageTags:
        r18Dir = "R-18G"
    elif "R-18" in imageInfo.imageTags:
        r18Dir = "R-18"
    nameFormat = nameFormat.replace('%R-18%', r18Dir)
    nameFormat = nameFormat.replace('%tags%', tags.replace(os.sep, '_'))
    nameFormat = nameFormat.replace('&#039;', '\'')  # Yavos: added html-code for "'" - works only when ' is excluded from __badchars__

    if bookmark:  # from member bookmarks
        nameFormat = nameFormat.replace('%bookmark%', 'Bookmarks')
        nameFormat = nameFormat.replace('%original_member_id%', str(imageInfo.originalArtist.artistId))
        nameFormat = nameFormat.replace('%original_member_token%', imageInfo.originalArtist.artistToken)
        nameFormat = nameFormat.replace('%original_artist%', imageInfo.originalArtist.artistName.replace(os.sep, '_'))
    else:
        nameFormat = nameFormat.replace('%bookmark%', '')
        nameFormat = nameFormat.replace('%original_member_id%', str(artistInfo.artistId))
        nameFormat = nameFormat.replace('%original_member_token%', artistInfo.artistToken)
        nameFormat = nameFormat.replace('%original_artist%', artistInfo.artistName.replace(os.sep, '_'))

    if imageInfo.bookmark_count > 0:
        nameFormat = nameFormat.replace('%bookmark_count%', str(imageInfo.bookmark_count))
    else:
        nameFormat = nameFormat.replace('%bookmark_count%', '')

    if imageInfo.image_response_count > 0:
        nameFormat = nameFormat.replace('%image_response_count%', str(imageInfo.image_response_count))
    else:
        nameFormat = nameFormat.replace('%image_response_count%', '')

    # clean up double space
    while nameFormat.find('  ') > -1:
        nameFormat = nameFormat.replace('  ', ' ')

    if appendExtension:
        nameFormat = nameFormat.strip() + '.' + imageExtension

    return nameFormat.strip()


def safePrint(msg, newline=True):
    """Print empty string if UnicodeError raised."""
    for msgToken in msg.split(' '):
        try:
            print msgToken,
        except UnicodeError:
            print ('?' * len(msgToken)),
    if newline:
        print ""


def setConsoleTitle(title):
    if os.name == 'nt':
        subprocess.call('title' + ' ' + title, shell=True)
    else:
        sys.stdout.write("\x1b]2;" + title + "\x07")


def clearScreen():
    if os.name == 'nt':
        subprocess.call('cls', shell=True)
    else:
        subprocess.call('clear', shell=True)


def startIrfanView(dfilename, irfanViewPath, start_irfan_slide=False, start_irfan_view=False):
    printAndLog('info', 'starting IrfanView...')
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
            Logger.info(ivcommand)
            subprocess.Popen(ivcommand)
        elif start_irfan_view:
            ivcommand = ivpath + ' /filelist=' + dfilename
            Logger.info(ivcommand)
            subprocess.Popen(ivcommand, startupinfo=info)
    else:
        printAndLog('error', u'could not load' + dfilename)


def OpenTextFile(filename, mode='r', encoding='utf-8'):
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


def toUnicode(obj, encoding='utf-8'):
    if isinstance(obj, basestring):
        if not isinstance(obj, unicode):
            obj = unicode(obj, encoding)
    return obj


def uni_input(message=''):
    result = raw_input(message)
    return toUnicode(result, encoding=sys.stdin.encoding)


def createAvatarFilename(artistPage, targetDir):
    filename = ''
    image = PixivModel.PixivImage(parent=artistPage)
    # Download avatar using custom name, refer issue #174
    if len(_config.avatarNameFormat) > 0:
        filenameFormat = _config.avatarNameFormat
        filename = makeFilename(filenameFormat, image,
                                tagsSeparator=_config.tagsSeparator,
                                tagsLimit=_config.tagsLimit,
                                fileUrl=artistPage.artistAvatar,
                                appendExtension=True)
        filename = sanitizeFilename(filename, targetDir)
    else:
        # or as folder.jpg
        filenameFormat = _config.filenameFormat
        if filenameFormat.find(os.sep) == -1:
            filenameFormat = os.sep + filenameFormat
        filenameFormat = os.sep.join(filenameFormat.split(os.sep)[:-1])
        filename = makeFilename(filenameFormat, image,
                                tagsSeparator=_config.tagsSeparator,
                                tagsLimit=_config.tagsLimit,
                                fileUrl=artistPage.artistAvatar,
                                appendExtension=False)
        filename = sanitizeFilename(filename + os.sep + 'folder.jpg', targetDir)
    return filename


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
        return os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))

    return os.path.dirname(unicode(__file__, sys.getfilesystemencoding()))


def speedInStr(totalSize, totalTime):
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


def sizeInStr(totalSize):
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


def dumpHtml(filename, html):
    isDumpEnabled = True
    filename = sanitizeFilename(filename)
    if _config is not None:
        isDumpEnabled = _config.enableDump
        if _config.enableDump:
            if len(_config.skipDumpFilter) > 0:
                matchResult = re.findall(_config.skipDumpFilter, filename)
                if matchResult is not None and len(matchResult) > 0:
                    isDumpEnabled = False

    if html is not None and len(html) == 0:
        printAndLog('info', 'Empty Html')
        return

    if isDumpEnabled:
        try:
            dump = file(filename, 'wb')
            dump.write(str(html))
            dump.close()
            return filename
        except Exception as ex:
            printAndLog('error', ex.message)
    else:
        printAndLog('info', 'No Dump')
    return ""


def printAndLog(level, msg):
    safePrint(msg)
    if level == 'info':
        GetLogger().info(msg)
    elif level == 'error':
        GetLogger().error(msg)
        GetLogger().error(traceback.format_exc())


def HaveStrings(page, strings):
    for string in strings:
        pattern = re.compile(string)
        test_2 = pattern.findall(str(page))
        if len(test_2) > 0:
            if len(test_2[-1]) > 0:
                return True
    return False


def getIdsFromCsv(ids_str, sep=','):
    ids = list()
    ids_str = str(ids_str).split(sep)
    for id_str in ids_str:
        temp = id_str.strip()
        if len(temp) > 0:
            try:
                _id = int(temp)
                ids.append(_id)
            except:
                printAndLog('error', u"ID: {0} is not valid".format(id_str))
    if len(ids) > 1:
        printAndLog('info', u"Found {0} ids".format(len(ids)))
    return ids


def clear_all():
    all_vars = [var for var in globals() if (var[:2], var[-2:]) != ("__", "__") and var != "clear_all"]
    for var in all_vars:
        del globals()[var]


# pylint: disable=W0612
def unescape_charref(data, encoding):
    ''' Replace default mechanize method in _html.py'''
    try:
        name, base = data, 10
        if name.lower().startswith("x"):
            name, base = name[1:], 16
        try:
            result = int(name, base)
        except:
            base = 16
        uc = unichr(int(name, base))
        if encoding is None:
            return uc
        else:
            try:
                repl = uc.encode(encoding)
            except UnicodeError:
                repl = "&#%s;" % data
            return repl
    except:
        return data


def getUgoiraSize(ugoName):
    size = 0
    try:
        with zipfile.ZipFile(ugoName) as z:
            animJson = z.read("animation.json")
            size = json.loads(animJson)['zipSize']
            z.close()
    except:
        printAndLog('error', u'Failed to read ugoira size from json data: {0}, using filesize.'.format(ugoName))
        size = os.path.getsize(ugoName)
    return size


def checkFileExists(overwrite, filename, file_size, old_size, backup_old_file):
    if not overwrite and int(file_size) == old_size:
        printAndLog('info', u"\tFile exist! (Identical Size)")
        return PixivConstant.PIXIVUTIL_SKIP_DUPLICATE
    # elif int(file_size) < old_size:
    #    printAndLog('info', "\tFile exist! (Local is larger)")
    #    return PixivConstant.PIXIVUTIL_SKIP_LOCAL_LARGER
    else:
        if backup_old_file:
            split_name = filename.rsplit(".", 1)
            new_name = filename + "." + str(int(time.time()))
            if len(split_name) == 2:
                new_name = split_name[0] + "." + str(int(time.time())) + "." + split_name[1]
            printAndLog('info', u"\t Found file with different file size, backing up to: " + new_name)
            os.rename(filename, new_name)
        else:
            printAndLog('info',
               u"\tFound file with different file size, removing old file (old: {0} vs new: {1})".format(old_size, file_size))
            os.remove(filename)
        return 1


def printDelay(retryWait):
    repeat = range(1, retryWait)
    for t in repeat:
        print t,
        time.sleep(1)
    print ''


def createCustomRequest(url, config, referer='http://www.pixiv.net', head=False):
    if config.useProxy:
        proxy = urllib2.ProxyHandler(config.proxy)
        opener = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)
    req = urllib2.Request(url)

    req.add_header('Referer', referer)
    printAndLog('info', u"Using Referer: " + str(referer))

    if head:
        req.get_method = lambda: 'HEAD'
    else:
        req.get_method = lambda: 'GET'

    return req


def downloadImage(url, filename, res, file_size, overwrite):
    start_time = datetime.now()

    # try to save to the given filename + .pixiv extension if possible
    try:
        directory = os.path.dirname(filename)
        if not os.path.exists(directory):
            printAndLog('info', u'Creating directory: ' + directory)
            os.makedirs(directory)
        save = file(filename + '.pixiv', 'wb+', 4096)
    except IOError:
        printAndLog('error', u"Error at download_image(): Cannot save {0} to {1}: {2}".format(url, filename, sys.exc_info()))

        # get the actual server filename and use it as the filename for saving to current app dir
        filename = os.path.split(url)[1]
        filename = filename.split("?")[0]
        filename = sanitizeFilename(filename)
        save = file(filename + '.pixiv', 'wb+', 4096)
        printAndLog('info', u'File is saved to ' + filename)

    # download the file
    prev = 0
    curr = 0
    print '{0:22} Bytes'.format(curr),
    try:
        while True:
            save.write(res.read(PixivConstant.BUFFER_SIZE))
            curr = save.tell()
            print '\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b',
            print '{0:9} of {1:9} Bytes'.format(curr, file_size),

            # check if downloaded file is complete
            if file_size > 0 and curr == file_size:
                total_time = (datetime.now() - start_time).total_seconds()
                print u' Completed in {0}s ({1})'.format(total_time, speedInStr(file_size, total_time))
                return curr

            elif curr == prev:  # no file size info
                total_time = (datetime.now() - start_time).total_seconds()
                print u' Completed in {0}s ({1})'.format(total_time, speedInStr(curr, total_time))
                return curr

            prev = curr

    except:
        raise

    finally:
        if save is not None:
            save.close()

        completed = True
        if file_size > 0 and curr < file_size:
            # File size is known and downloaded file is smaller
            printAndLog('error', u'Downloaded file incomplete! {0:9} of {1:9} Bytes'.format(curr, file_size))
            printAndLog('error', u'Filename = ' + unicode(filename))
            printAndLog('error', u'URL      = {0}'.format(url))
            completed = False
        elif curr == 0:
            # No data received.
            printAndLog('error', u'No data received!')
            printAndLog('error', u'Filename = ' + unicode(filename))
            printAndLog('error', u'URL      = {0}'.format(url))
            completed = False

        if completed:
            if overwrite and os.path.exists(filename):
                os.remove(filename)
            os.rename(filename + '.pixiv', filename)
        else:
            os.remove(filename + '.pixiv')

        del save


def generateSearchTagUrl(tags, page, title_caption, wild_card, oldest_first,
                         start_date=None, end_date=None, member_id=None,
                         r18mode=False):
    url = ""
    date_param = ""
    if start_date is not None:
        date_param = date_param + "&scd=" + start_date
    if end_date is not None:
        date_param = date_param + "&ecd=" + end_date

    if member_id is not None:
        url = 'http://www.pixiv.net/member_illust.php?id=' + str(member_id) + '&tag=' + tags + '&p=' + str(page)
    else:
        if title_caption:
            url = 'http://www.pixiv.net/search.php?s_mode=s_tc&p=' + str(page) + '&word=' + tags + date_param
            print u"Using Title Match (s_tc)"
        else:
            if wild_card:
                url = 'http://www.pixiv.net/search.php?s_mode=s_tag&p=' + str(page) + '&word=' + tags + date_param
                print u"Using Partial Match (s_tag)"
            else:
                url = 'http://www.pixiv.net/search.php?s_mode=s_tag_full&word=' + tags + '&p=' + str(page) + date_param
                print u"Using Full Match (s_tag_full)"

    if r18mode:
        url = url + '&r18=1'

    if oldest_first:
        url = url + '&order=date'
    else:
        url = url + '&order=date_d'

    # encode to ascii
    url = unicode(url).encode('iso_8859_1')

    return url


def writeUrlInDescription(image, blacklistRegex, filenamePattern):
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

        info = codecs.open(filename, 'a', encoding='utf-8')
        info.write("#" + str(image.imageId) + "\r\n")
        for link in valid_url:
            info.write(link + "\r\n")
        info.close()


def ugoira2gif(ugoira_file, exportname):
    printAndLog('info', 'processing ugoira to animated gif...')
    temp_folder = tempfile.mkdtemp()
    # imageio cannot handle utf-8 filename
    temp_name = temp_folder + os.sep + "temp.gif"

    z = zipfile.ZipFile(ugoira_file)
    z.extractall(temp_folder)

    filenames = os.listdir(temp_folder)
    filenames.remove('animation.json')
    anim_info = json.load(open(temp_folder + '/animation.json'))

    durations = []
    images = []
    for info in anim_info["frames"]:
        images.append(imageio.imread(temp_folder + os.sep + info["file"]))
        durations.append(float(info["delay"]) / 1000)

    kargs = {'duration': durations}
    imageio.mimsave(temp_name, images, 'GIF', **kargs)
    shutil.move(temp_name, exportname)
    printAndLog('info', 'ugoira exported to: ' + exportname)

    shutil.rmtree(temp_folder)


def ugoira2apng(ugoira_file, exportname):
    printAndLog('info', 'processing ugoira to apng...')
    temp_folder = tempfile.mkdtemp()
    temp_name = temp_folder + os.sep + "temp.png"

    z = zipfile.ZipFile(ugoira_file)
    z.extractall(temp_folder)

    filenames = os.listdir(temp_folder)
    filenames.remove('animation.json')
    anim_info = json.load(open(temp_folder + '/animation.json'))

    files = []
    for info in anim_info["frames"]:
        fImage = temp_folder + os.sep + info["file"]
        delay = info["delay"]
        files.append((fImage, delay))

    im = APNG()
    for fImage, delay in files:
        im.append(fImage, delay=delay)
    im.save(temp_name)
    shutil.move(temp_name, exportname)
    printAndLog('info', 'ugoira exported to: ' + exportname)

    shutil.rmtree(temp_folder)


def ParseDateTime(worksDate, dateFormat):
    if dateFormat is not None and len(dateFormat) > 0 and '%' in dateFormat:
        # use the user defined format
        worksDateDateTime = None
        try:
            worksDateDateTime = datetime.strptime(worksDate, dateFormat)
        except ValueError as ve:
            GetLogger().exception(
                'Error when parsing datetime: {0} using date format {1}'.format(worksDate, str(dateFormat)),
                ve)
            raise
    else:
        worksDate = worksDate.replace(u'/', u'-')
        if worksDate.find('-') > -1:
            try:
                worksDateDateTime = datetime.strptime(worksDate, u'%m-%d-%Y %H:%M')
            except ValueError as ve:
                GetLogger().exception(
                    'Error when parsing datetime: {0}'.format(worksDate), ve)
                worksDateDateTime = datetime.strptime(worksDate.split(" ")[0], u'%Y-%m-%d')
        else:
            tempDate = worksDate.replace(u'年', '-').replace(u'月', '-').replace(u'日', '')
            worksDateDateTime = datetime.strptime(tempDate, '%Y-%m-%d %H:%M')

    return worksDateDateTime


def encode_tags(tags):
    if not tags.startswith("%"):
        try:
            # Encode the tags
            tags = tags.encode('utf-8')
            tags = urllib.quote_plus(tags)
        except UnicodeDecodeError:
            try:
                # from command prompt
                tags = urllib.quote_plus(tags.decode(sys.stdout.encoding).encode("utf8"))
            except UnicodeDecodeError:
                printAndLog('error', 'Cannot decode the tags, you can use URL Encoder (http://meyerweb.com/eric/tools/dencoder/) and paste the encoded tag.')
    return tags


def decode_tags(tags):
    # decode tags.
    try:
        if tags.startswith("%"):
            search_tags = toUnicode(urllib.unquote_plus(tags))
        else:
            search_tags = toUnicode(tags)
    except UnicodeDecodeError:
        # From command prompt
        search_tags = tags.decode(sys.stdout.encoding).encode("utf8")
        search_tags = toUnicode(search_tags)
    return search_tags
