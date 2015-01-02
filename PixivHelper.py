# -*- coding: utf-8 -*-
import re
import os
import codecs
from HTMLParser import HTMLParser
import subprocess
import sys
import PixivModel, PixivConstant
import logging, logging.handlers
import datetime

import unicodedata

Logger = None
_config = None


def setConfig(config):
    global _config
    _config = config


def GetLogger(level=logging.DEBUG):
    '''Set up logging'''
    global Logger
    if Logger == None:
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
__re_manga_index = re.compile('_p(\d+)')


def sanitizeFilename(s, rootDir=None):
    '''Replace reserved character/name with underscore (windows), rootDir is not sanitized.'''
    ## get the absolute rootdir
    if rootDir != None:
        rootDir = os.path.abspath(rootDir)

    ## Unescape '&amp;', '&lt;', and '&gt;'
    s = __h__.unescape(s)

    ## Replace badchars with _
    name = __badchars__.sub('_', s)
    if __badnames__.match(name):
        name = '_' + name

    ## Replace new line with space
    name = name.replace("\r", '')
    name = name.replace("\n", ' ')

    #Yavos: when foldername ends with "." PixivUtil won't find it
    while name.find('.\\') != -1:
        name = name.replace('.\\', '\\')

    name = name.replace('\\', os.sep)

    #Replace tab character with space
    name = name.replace('\t', ' ')

    #Strip leading/trailing space for each directory
    temp = name.split(os.sep)
    temp2 = list()
    for item in temp:
        temp2.append(item.strip())
    name = os.sep.join(temp2)

    if rootDir != None:
        name = rootDir + os.sep + name

    #replace double os.sep
    while name.find(os.sep + os.sep) >= 0:
        name = name.replace(os.sep + os.sep, os.sep)

    ## cut to 255 char
    if len(name) > 255:
        newLen = 250
        name = name[:newLen]

    ## Remove unicode control character
    tempName = ""
    for c in name:
        if unicodedata.category(c) == 'Cc':
            tempName = tempName + '_'
        else:
            tempName = tempName + c
    Logger.debug("Sanitized Filename: " + tempName.strip())

    return tempName.strip()


def makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', tagsLimit=-1, fileUrl='',
                 appendExtension=True, bookmark=False, searchTags=''):
    '''Build the filename from given info to the given format.'''
    if artistInfo == None:
        artistInfo = imageInfo.artist

    ## Get the image extension
    fileUrl = os.path.basename(fileUrl)
    splittedUrl = fileUrl.split('.')
    imageExtension = splittedUrl[1]
    imageExtension = imageExtension.split('?')[0]

    nameFormat = nameFormat.replace('%artist%', artistInfo.artistName.replace(os.sep, '_'))
    nameFormat = nameFormat.replace('%title%', imageInfo.imageTitle.replace(os.sep, '_'))
    nameFormat = nameFormat.replace('%image_id%', str(imageInfo.imageId))
    nameFormat = nameFormat.replace('%member_id%', str(artistInfo.artistId))
    nameFormat = nameFormat.replace('%member_token%', artistInfo.artistToken)
    nameFormat = nameFormat.replace('%works_date%', imageInfo.worksDate)
    nameFormat = nameFormat.replace('%works_date_only%', imageInfo.worksDate.split(' ')[0])
    nameFormat = nameFormat.replace('%works_res%', imageInfo.worksResolution)
    nameFormat = nameFormat.replace('%works_tools%', imageInfo.worksTools)
    nameFormat = nameFormat.replace('%urlFilename%', splittedUrl[0])
    nameFormat = nameFormat.replace('%searchTags%', searchTags)

    ## date
    nameFormat = nameFormat.replace('%date%', datetime.date.today().strftime('%Y%m%d'))

    ## get the page index & big mode if manga
    page_index = ''
    page_number = ''
    page_big = ''
    if imageInfo.imageMode == 'manga':
        idx = __re_manga_index.findall(fileUrl)
        if len(idx) > 0:
            page_index = idx[0]#[0]
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
    nameFormat = nameFormat.replace('&#039;', '\'') #Yavos: added html-code for "'" - works only when ' is excluded from __badchars__

    if bookmark: # from member bookmarks
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

    ## clean up double space
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
        print ''


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
    print 'starting IrfanView...'
    if os.path.exists(dfilename):
        ivpath = irfanViewPath + os.sep + 'i_view32.exe' #get first part from config.ini
        ivpath = ivpath.replace('\\\\', '\\')
        ivpath = ivpath.replace('\\', os.sep)
        info = None
        if start_irfan_slide:
            info = subprocess.STARTUPINFO()
            info.dwFlags = 1
            info.wShowWindow = 6 #start minimized in background (6)
            ivcommand = ivpath + ' /slideshow=' + dfilename
            Logger.info(ivcommand)
            subprocess.Popen(ivcommand)
        elif start_irfan_view:
            ivcommand = ivpath + ' /filelist=' + dfilename
            Logger.info(ivcommand)
            subprocess.Popen(ivcommand, startupinfo=info)
    else:
        print 'could not load', dfilename


def OpenTextFile(filename, mode='r', encoding='utf-8'):
    ''' taken from: http://www.velocityreviews.com/forums/t328920-remove-bom-from-string-read-from-utf-8-file.html'''
    hasBOM = False
    if os.path.isfile(filename):
        f = open(filename, 'rb')
        header = f.read(4)
        f.close()

        # Don't change this to a map, because it is ordered
        encodings = [( codecs.BOM_UTF32, 'utf-32' ),
                     ( codecs.BOM_UTF16, 'utf-16' ),
                     ( codecs.BOM_UTF8, 'utf-8' )]

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


def CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artistPage, targetDir):
    filename = ''
    if filenameFormat.find(os.sep) == -1:
        filenameFormat = os.sep + filenameFormat
    filenameFormat = filenameFormat.split(os.sep)[0]
    image = PixivModel.PixivImage(parent=artistPage)
    filename = makeFilename(filenameFormat, image, tagsSeparator=tagsSeparator, tagsLimit=tagsLimit,
                            fileUrl=artistPage.artistAvatar, appendExtension=False)
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


def dumpHtml(filename, html):
    isDumpEnabled = True
    if _config != None:
        isDumpEnabled = _config.enableDump
        if _config.enableDump:
            if len(_config.skipDumpFilter) > 0:
                matchResult = re.findall(_config.skipDumpFilter, filename)
                if matchResult != None and len(matchResult) > 0:
                    isDumpEnabled = False

    if len(html) == 0:
        print 'Empty Html'
        return

    if isDumpEnabled:
        try:
            dump = file(filename, 'wb')
            dump.write(str(html))
            dump.close()
        except Exception as ex:
            print ex
            pass
    else:
        print "No Dump"


def printAndLog(level, msg):
    safePrint(msg)
    if level == 'info':
        GetLogger().info(msg)
    elif level == 'error':
        GetLogger().error(msg)


def HaveStrings(page, strings):
    for string in strings:
       pattern = re.compile(string)
       test_2 = pattern.findall(str(page))
       if len(test_2) > 0 :
           if len(test_2[-1]) > 0 :
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
                printAndLog('error', "ID: {0} is not valid".format(id_str))
    if len(ids) > 1:
        printAndLog('info', "Found {0} ids".format(len(ids)))
    return ids


def clear_all():
    all_vars = [var for var in globals() if (var[:2], var[-2:]) != ("__", "__") and var != "clear_all"]
    for var in all_vars:
        del globals()[var]

''' Replace default mechanize method in _html.py'''
def unescape_charref(data, encoding):
    try:
      name, base = data, 10
      if name.lower().startswith("x"):
          name, base= name[1:], 16
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