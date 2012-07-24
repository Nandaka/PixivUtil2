# -*- coding: UTF-8 -*-
import re
import os
import codecs
from HTMLParser import HTMLParser
import subprocess
import sys
import PixivModel

if os.sep == '/':
  __badchars__ = re.compile(r'^\.|\.$|^ | $|^$|\?|:|<|>|\||\*|\"')
else :
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
  name= __badchars__.sub('_', s)
  if __badnames__.match(name):
    name= '_'+name

  #Yavos: when foldername ends with "." PixivUtil won't find it
  while name.find('.\\') != -1:
    name = name.replace('.\\','\\')

  name = name.replace('\\', os.sep)

  #Replace tab character with space
  name = name.replace('\t',' ')

  #Strip leading/trailing space for each directory
  temp = name.split(os.sep)
  temp2 = list()
  for item in temp:
    temp2.append(item.strip())
  name = os.sep.join(temp2)

  if rootDir != None:
    name = rootDir + os.sep + name

  #replace double os.sep
  while name.find(os.sep+os.sep) >= 0:
    name = name.replace(os.sep+os.sep, os.sep)

  ## cut to 255 char
  if len(name) > 255:
    newLen = 250
    name = name[:newLen]

  return name.strip()

def makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', tagsLimit=-1, fileUrl=''):
  '''Build the filename from given info to the given format.'''
  if artistInfo == None:
    artistInfo = imageInfo.artist

  ## Get the image extension
  splittedUrl = fileUrl.split('.')
  imageExtension = splittedUrl[1]
  imageExtension = imageExtension.split('?')[0]
  
  nameFormat = nameFormat.replace('%artist%',artistInfo.artistName.replace(os.sep,'_'))
  nameFormat = nameFormat.replace('%title%',imageInfo.imageTitle.replace(os.sep,'_'))
  nameFormat = nameFormat.replace('%image_id%',str(imageInfo.imageId))
  nameFormat = nameFormat.replace('%member_id%',str(artistInfo.artistId))
  nameFormat = nameFormat.replace('%member_token%',artistInfo.artistToken)
  nameFormat = nameFormat.replace('%works_date%',imageInfo.worksDate)
  nameFormat = nameFormat.replace('%works_date_only%',imageInfo.worksDate.split(' ')[0])
  nameFormat = nameFormat.replace('%works_res%',imageInfo.worksResolution)
  nameFormat = nameFormat.replace('%works_tools%',imageInfo.worksTools)
  nameFormat = nameFormat.replace('%urlFilename%',splittedUrl[0])
  
  ## get the page index & big mode if manga
  page_index = ''
  page_number = ''
  page_big = ''
  if imageInfo.imageMode == 'manga':
    idx = __re_manga_index.findall(fileUrl)
    if len(idx) > 0:
      page_index = idx[0][0]
      page_number = str(int(page_index) + 1)
    if fileUrl.find('_big') > -1 or not fileUrl.find('_m') > -1:
      page_big = 'big'
  nameFormat = nameFormat.replace('%page_big%',page_big)
  nameFormat = nameFormat.replace('%page_index%',page_index)
  nameFormat = nameFormat.replace('%page_number%',page_number)
  
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
  nameFormat = nameFormat.replace('%R-18%',r18Dir)
  nameFormat = nameFormat.replace('%tags%',tags.replace(os.sep,'_'))
  nameFormat = nameFormat.replace('&#039;','\'') #Yavos: added html-code for "'" - works only when ' is excluded from __badchars__

  ## clean up double space
  while nameFormat.find('  ') > -1:
    nameFormat = nameFormat.replace('  ', ' ')
  
  nameFormat = nameFormat + '.' + imageExtension  
  
  return nameFormat

def safePrint(msg, newline=True):
  '''Print empty string if UnicodeError raised.'''
  for msgToken in msg.split(' '):
    try:
      print msgToken,
    except UnicodeError:
      print ('?' * len (msgToken)),
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
  filename = makeFilename(filenameFormat, image, tagsSeparator=tagsSeparator, tagsLimit=tagsLimit)  
  filename = sanitizeFilename(filename + os.sep + 'folder.jpg', targetDir)

  return filename
  
