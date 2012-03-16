# -*- coding: UTF-8 -*-
import re
import os
import codecs
#import xml.sax.saxutils as saxutils
from HTMLParser import HTMLParser
import subprocess
import sys

if os.sep == '/':
    __badchars__ = re.compile(r'^\.|\.$|^ | $|^$|\?|:|<|>|\||\*|\"')
else :
    __badchars__ = re.compile(r'^\.|\.$|^ | $|^$|\?|:|<|>|/|\||\*|\"')
__badnames__ = re.compile(r'(aux|com[1-9]|con|lpt[1-9]|prn)(\.|$)')

__h__ = HTMLParser()

def sanitizeFilename(s, rootDir=None):
    '''Replace reserved character/name with underscore (windows), rootDir is not sanitized.'''
    ## get the absolute rootdir
    if rootDir != None:
        rootDir = os.path.abspath(rootDir)
    
    ## Unescape '&amp;', '&lt;', and '&gt;'
    s = __h__.unescape(s)

    ## Replace badchars with _
    name= __badchars__.sub('_', s)
    if __badnames__.match(name):
        name= '_'+name

    #Yavos: when foldername ends with "." PixivUtil won't find it
    while name.find('.\\') != -1:
        name = name.replace('.\\','\\')

    name = name.replace('\\', os.sep)

    #Replace tab character with space
    name = name.replace('\t',' ')

    ## cut to 255 char
    pathLen = 0
    if rootDir != None:
        name = unicode(rootDir, "utf-8") + os.sep + name
        
    if len(name) > 255:
        newLen = 254
        name = name[:newLen]
        
    return name.strip()

def makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' '):
    '''Build the filename from given info to the given format.'''
    if artistInfo == None:
        artistInfo = imageInfo.artist
    #nameFormat = unicode(nameFormat)
    nameFormat = nameFormat.replace('%artist%',artistInfo.artistName.replace(os.sep,'_'))
    nameFormat = nameFormat.replace('%title%',imageInfo.imageTitle.replace(os.sep,'_'))
    nameFormat = nameFormat.replace('%image_id%',str(imageInfo.imageId))
    nameFormat = nameFormat.replace('%member_id%',str(artistInfo.artistId))
    nameFormat = nameFormat.replace('%member_token%',artistInfo.artistToken)
    nameFormat = nameFormat.replace('%works_date%',imageInfo.worksDate)
    nameFormat = nameFormat.replace('%works_date_only%',imageInfo.worksDate.split(' ')[0])
    nameFormat = nameFormat.replace('%works_res%',imageInfo.worksResolution)
    nameFormat = nameFormat.replace('%works_tools%',imageInfo.worksTools)
    if tagsSeparator == '%space%':
        tagsSeparator = ' '
    tags = tagsSeparator.join(imageInfo.imageTags)
    nameFormat = nameFormat.replace('%tags%',tags.replace(os.sep,'_'))
    nameFormat = nameFormat.replace('&#039;','\'') #Yavos: added html-code for "'" - works only when ' is excluded from __badchars__
    return nameFormat

def safePrint(msg):
    '''Print empty string if UnicodeError raised.'''
    try:
        print msg,
    except UnicodeError:
        print '',
    return ' '

def setConsoleTitle(title):
    if os.name == 'nt':
        subprocess.call('title' + ' ' + title, shell=True)
    else:
        sys.stdout.write("\x1b]2;" + title + "\x07")

def startIrfanView(dfilename, irfanViewPath):
    print 'starting IrfanView...'
    if os.path.exists(dfilename):
        ivpath = irfanViewPath + os.sep + 'i_view32.exe' #get first part from config.ini
        ivpath = ivpath.replace('\\\\', '\\')
        ivpath = ivpath.replace('\\', os.sep)
        info = None
        if IrfanSlide == True:
            info = subprocess.STARTUPINFO()
            info.dwFlags = 1
            info.wShowWindow = 6 #start minimized in background (6)
            ivcommand = ivpath + ' /slideshow=' + dfilename
            subprocess.Popen(ivcommand)
        if IrfanView == True:
            ivcommand = ivpath + ' /filelist=' + dfilename
            subprocess.Popen(ivcommand, startupinfo=info)
    else:
        print 'could not load', dfilename

''' taken from: '''
''' http://www.velocityreviews.com/forums/t328920-remove-bom-from-string-read-from-utf-8-file.html'''
def OpenTextFile(filename, mode='r', encoding = 'utf-8'):
    hasBOM = False
    if os.path.isfile(filename):
        f = open(filename,'rb')
        header = f.read(4)
        f.close()
        
        # Don't change this to a map, because it is ordered
        encodings = [ ( codecs.BOM_UTF32, 'utf-32' ),
            ( codecs.BOM_UTF16, 'utf-16' ),
            ( codecs.BOM_UTF8, 'utf-8' ) ]
        
        for h, e in encodings:
            if header.startswith(h):
                encoding = e
                hasBOM = True
                break
        
    f = codecs.open(filename,mode,encoding)
    # Eat the byte order mark
    if hasBOM:
        f.read(1)
    return f
