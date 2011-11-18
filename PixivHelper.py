# -*- coding: UTF-8 -*-
import re
import os
import xml.sax.saxutils as saxutils

__badchars__ = re.compile(r'^\.|\.$|^ | $|^$|\?|:|<|>|/|\||\*|\"')
__badnames__ = re.compile(r'(aux|com[1-9]|con|lpt[1-9]|prn)(\.|$)')
def sanitizeFilename(s, rootDir=''):
    '''Replace reserved character/name with underscore (windows).'''
    ## Unescape '&amp;', '&lt;', and '&gt;'
    s = saxutils.unescape(s)
    name= __badchars__.sub('_', s)
    if __badnames__.match(name):
        name= '_'+name

    #Yavos: when foldername ends with "." PixivUtil won't find it
    while name.find('.\\') != -1:
        name = name.replace('.\\','\\')

    ## cut to 255 char
    pathLen = len(rootDir) + 1
    if len(name) + pathLen > 255:
        newLen = 250 - pathLen
        name = name[:newLen]
    return name.strip()

def makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' '):
    '''Build the filename from given info to the given format.'''
    if artistInfo == None:
        artistInfo = imageInfo.artist
    nameFormat = nameFormat.replace('%artist%',artistInfo.artistName.replace('\\','_'))
    nameFormat = nameFormat.replace('%title%',imageInfo.imageTitle.replace('\\','_'))
    nameFormat = nameFormat.replace('%image_id%',str(imageInfo.imageId))
    nameFormat = nameFormat.replace('%member_id%',str(artistInfo.artistId))
    nameFormat = nameFormat.replace('%member_token%',artistInfo.artistToken)
    if tagsSeparator == '%space%':
        tagsSeparator = ' '
    tags = tagsSeparator.join(imageInfo.imageTags)
    nameFormat = nameFormat.replace('%tags%',tags.replace('\\','_'))
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
        os.system('title ' + title)
    else:
        sys.stdout.write("\x1b]2;" + title + "\x07")

