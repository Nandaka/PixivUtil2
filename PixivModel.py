# -*- coding: UTF-8 -*-
from BeautifulSoup import BeautifulSoup, Tag
import os
import re

import PixivHelper

class PixivArtist:
  artistId     = 0
  artistName   = ""
  artistAvatar = ""
  artistToken  = ""
  imageList    = []

  def __init__(self, mid=0, page=None, fromImage=False):
    if page != None:
      ## detect if artist exist
      if not self.IsUserExist(page):
        raise PixivModelException('User ID not exist/deleted!')
      
      ## detect if image count != 0
      if not fromImage:
        self.ParseImages(page)
      
      ## parse artist info
      self.ParseInfo(page, fromImage)

      ## check id
      if mid == self.artistId:
        print 'member_id OK'

  def ParseInfo(self, page, fromImage=False):
    temp = str(page.find(attrs={'class':'f18b'}).find('a')['href'])
    self.artistId = int(re.search('id=(\d+)', temp).group(1))
    try:
      self.artistName = unicode(page.h2.span.a.string.extract())
    except:
      self.artistName = unicode(page.findAll(attrs={"class":"avatar_m"})[0]["title"])
    self.artistAvatar = str(page.find(attrs={'class':'avatar_m'}).find('img')['src'])
    self.artistToken = self.ParseToken(page, fromImage)
      

  def ParseToken(self, page, fromImage=False):
    if self.artistAvatar == 'http://source.pixiv.net/source/images/no_profile.png':
      if fromImage:
        token = str(page.find(attrs={'class':'works_display'}).find('img')['src'])
        print token
        return token.split('/')[-2]
      else :
        try:
          temp = page.find(attrs={'class':'display_works linkStyleWorks'})
          if temp != None:
            tokens = temp.ul.findAll('li')
            for token in tokens:
              try:
                artistToken = token.find('img')['data-src']
              except:
                artistToken = token.find('img')['src']
              artistToken = artistToken.split('/')[-2]
              if artistToken != 'common':
                return artistToken
          raw_input('cannot parse artist token')
        except TypeError:
          raise PixivModelException('Cannot parse artist token, possibly no images.')
    else :
      temp = self.artistAvatar.split('/')
      return temp[-2]
    
  def ParseImages(self, page):
    del self.imageList[:]
    temp = page.find(attrs={'class':'display_works linkStyleWorks'}).ul
    temp = temp.findAll('a')
    if temp == None or len(temp) == 0:
      raise PixivModelException('No image found!')
    for item in temp:
      href = re.search('illust_id=(\d+)', str(item)).group(1)
      self.imageList.append(int(href))
    
  def IsUserExist(self, page):
    if page == None:
      raise PixivModelException('Empty page')
    errorMessage = '該当ユーザーは既に退会したか、存在しないユーザーIDです'
    pattern = re.compile(errorMessage)
    test_2 = pattern.findall(str(page))
    if len(test_2) > 0 :
        if len(test_2[-1]) > 0 :
            return False
    else :
      return True

  def PrintInfo(self):
    print 'id    :',self.artistId
    print 'name  :',self.artistName
    print 'avatar:',self.artistAvatar
    print 'token :',self.artistToken
    for item in self.imageList:
      print item
    
class PixivImage:
  artist     = None
  imageId    = 0
  imageTitle = ""
  imageTags  = []
  imageMode  = ""
  imageUrls  = []

  def __init__(self, iid=0, page=None, parent=None):
    self.artist = parent
    if page != None:
      ## check is error page
      if self.IsErrorPage(page):
        raise PixivModelException('An error occurred!')
      if self.IsNeedPermission(page):
        raise PixivModelException('Not in MyPick List, Need Permission!')
      if self.IsNeedAppropriateLevel(page):
        raise PixivModelException('Public works can not be viewed by the appropriate level!')
      if self.IsDeleted(page):
        raise PixivModelException('Image not found/already deleted!')
      unknownError = self.CheckUnknownError(page)
      if not unknownError == None:
        raise PixivModelException('Unknown Error: '+unknownError)
      ## parse artist information
      if self.artist == None:
        self.artist = PixivArtist(page=page, fromImage=True)

      ## parse image information
      self.ParseInfo(page)
      self.ParseTags(page)

      ## check id
      if iid == self.imageId:
        print 'image_id OK'

  def IsErrorPage(self, page):
    errorMessage = 'エラーが発生しました'
    return self.HaveString(page, errorMessage)

  def CheckUnknownError(self, page):
    test = page.findAll('span', {'class':'error'})
    if not test == None and len(test) > 0:
      return test[0].contents[0].renderContents()
    else :
      return None

  def IsNeedAppropriateLevel(self, page):
    errorMessage = '該当作品の公開レベルにより閲覧できません。'
    return self.HaveString(page, errorMessage)
  
  def IsNeedPermission(self, page):
    errorMessage = 'この作品は、.+さんのマイピクにのみ公開されています'
    return self.HaveString(page, errorMessage)

  def IsDeleted(self, page):
    errorMessage = '該当イラストは削除されたか、存在しないイラストIDです。|該当作品は削除されたか、存在しない作品IDです。'
    return self.HaveString(page, errorMessage)
  
  def HaveString(self, page, string):
    pattern = re.compile(string)
    test_2 = pattern.findall(str(page))
    if len(test_2) > 0 :
        if len(test_2[-1]) > 0 :
            return True
    else :
      return False
  
  def ParseInfo(self, page):
    temp = str(page.find(attrs={'class':'works_display'}).find('a')['href'])
    self.imageId = int(re.search('illust_id=(\d+)',temp).group(1))
    self.imageMode = re.search('mode=(big|manga)',temp).group(1)
    self.imageTitle = unicode(page.h3.string)

  def ParseTags(self, page):
    del self.imageTags[:]
    temp = page.find(id='tags').findAll('a')
    for tag in temp:
      if not tag.string == None:
        self.imageTags.append(unicode(tag.string))

  def PrintInfo(self):
    #self.artist.PrintInfo()
    print 'img id:',self.imageId
    print 'title :',self.imageTitle
    print 'mode  :',self.imageMode
    for item in self.imageTags:
      print item

  def ParseImages(self, page, mode=None):
    if page == None:
      raise PixivModelException('No page given')
    if mode == None:
      mode = self.imageMode

    del self.imageUrls[:]
    if mode == 'big':
      self.imageUrls.append(self.ParseBigImages(page))
    elif mode == 'manga':
      self.imageUrls = self.ParseMangaImages(page)
    if len(self.imageUrls) == 0:
      raise PixivModelException('No images found for: '+self.imageId)
    return self.imageUrls

  def ParseBigImages(self, page):
    temp = page.find('img')['src']
    return str(temp)

  def ParseMangaImages(self, page):
    urls = []
    scripts = page.findAll('script')
    string = ''
    for script in scripts:
      string += str(script)
    pattern = re.compile('http.*?\d+_p\d+\..{3}')
    m = pattern.findall(string)
    for img in m:
      temp = str(img)
      temp = temp.replace('_p', '_big_p')
      urls.append(temp)
      temp = str(img)
      urls.append(temp)
    return urls    

class PixivModelException(Exception):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

class PixivListItem:
  '''Class for item in list.txt'''
  memberId = ""
  path = ""

  def __init__(self, memberId, path):
    self.memberId = int(memberId)
    self.path = path.strip()
    if self.path == "N\A":
      self.path = ""

  @staticmethod
  def parseList(filename, rootDir=""):
    '''read list.txt and return the list of PixivListItem'''
    l = list()

    if not os.path.exists(filename) :
      raise PixivModelException("File doesn't exists or no permission to read: " + filename)

    reader = open(filename, "r")
    for line in reader:
        if line.startswith('#') or len(line) < 1:
          continue
        items = line.split(" ", 1)
        member_id = int(items[0])
        path = ""
        if len(items) > 1:
          path = items[1].strip()
          path = path.replace('\"', '')
          if re.match(r'[a-zA-Z]:', path):
              dirpath = path.split('\\', 1)
              dirpath[1] = PixivHelper.sanitizeFilename(dirpath[1], rootDir)
              path = '\\'.join(dirpath)
          else:
              path = PixivHelper.sanitizeFilename(path, rootDir)
          path = path.replace('%root%', rootDir)
          path = path.replace('\\\\', '\\')

        listItem = PixivListItem(member_id, path)
        l.append(listItem)

    reader.close()        
    return l

class PixivBookmark:

  @staticmethod
  def parseBookmark(page):
    import PixivDBManager
    l = list()
    db = PixivDBManager.PixivDBManager()
    result = page.find(attrs={'class':'list_box'}).findAll('input')
    for r in result:
      item = db.selectMemberByMemberId2(r['value'])
      l.append(item)

    return l

  @staticmethod
  def exportList(l, filename):
    from datetime import datetime
    writer = open(filename, 'w')
    writer.write('###Export date: ' + str(datetime.today()) +'###\n')
    for item in l:
        writer.write(str(item.memberId) + " " + str(item.path))
        writer.write('\n')
    writer.write('###END-OF-FILE###')
    writer.close()

class PixivTags:
  imageList = list()
  
  def parseTags(self, page):
    __re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
    linkList = page.findAll('a')
    for link in linkList:
      link.extract()
      if link.has_key('href') :
        result = __re_illust.findall(link['href'])
        if len(result) > 0 :
          image_id = int(result[0])
          self.imageList.append(image_id)
          
    return self.imageList
 
  @staticmethod
  def parseTagsList(filename):
    '''read tags.txt and return the tags list'''
    l = list()

    if not os.path.exists(filename) :
      raise PixivModelException("File doesn't exists or no permission to read: " + filename)

    reader = open(filename, "r")
    for line in reader:
        if line.startswith('#') or len(line) < 1:
          continue
        l.append(line.strip())

    reader.close()        
    return l
