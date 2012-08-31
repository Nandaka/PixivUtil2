# -*- coding: UTF-8 -*-
from BeautifulSoup import BeautifulSoup, Tag
import os
import re
import sys
import codecs
import collections
import PixivHelper

class PixivArtist:
  '''Class for parsing member page.'''
  artistId     = 0
  artistName   = ""
  artistAvatar = ""
  artistToken  = ""
  imageList    = []
  isLastPage = None
  haveImages = None

  def __init__(self, mid=0, page=None, fromImage=False):
    if page != None:
      ## detect if artist exist
      if self.IsUserNotExist(page):
        raise PixivModelException('User ID not exist/deleted!', errorCode=1001)

      ## detect if artist account is suspended.
      if self.IsUserSuspended(page):
        raise PixivModelException('User Account is Suspended!', errorCode=1002)

      ## detect if there is any other error
      errorMessage = self.IsErrorExist(page)
      if errorMessage != None:
        raise PixivModelException('Member Error: ' + errorMessage, errorCode=1003)
        
      ## detect if image count != 0
      if not fromImage:
        self.ParseImages(page)
      
      ## parse artist info
      self.ParseInfo(page, fromImage)

      ## check if no images
      if len(self.imageList) > 0:
        self.haveImages = True
      else:
        self.haveImages = False

      ## check if the last page
      self.CheckLastPage(page)
      
      ## check id
      #if mid == self.artistId:
      #  print 'member_id OK'

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
        #print token
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

  def HaveString(self, page, string):
    pattern = re.compile(string)
    test_2 = pattern.findall(str(page))
    if len(test_2) > 0 :
        if len(test_2[-1]) > 0 :
            return True
    else :
      return False
  
  def IsUserNotExist(self, page):
    errorMessage = '該当ユーザーは既に退会したか、存在しないユーザーIDです'
    errorMessage2 = 'The user has either left pixiv, or the user ID does not exist.'
    return self.HaveString(page, errorMessage) or self.HaveString(page, errorMessage2)
    
  def IsUserSuspended(self, page):
    errorMessage = '該当ユーザーのアカウントは停止されています。'
    errorMessage2 = 'This user account has been suspended.'
    return self.HaveString(page, errorMessage) or self.HaveString(page, errorMessage2)

  def IsErrorExist(self, page):
    check = page.findAll('span', attrs={'class':'error'})
    if len(check) > 0:
      check2 = page.findAll('strong')
      if len(check2) > 0:
        return check2[0].renderContents()
      return check[0].renderContents()
    return None
  
  def CheckLastPage(self, page):
    check = page.findAll('a', attrs={'class':'button', 'rel':'next'})
    if len(check) > 0:
      self.isLastPage = False
    else:
      self.isLastPage = True
    return self.isLastPage
    
  def PrintInfo(self):
    PixivHelper.safePrint('Artist Info')
    PixivHelper.safePrint('id    : ' + str(self.artistId))
    PixivHelper.safePrint('name  : ' + self.artistName)
    PixivHelper.safePrint('avatar: ' + self.artistAvatar)
    PixivHelper.safePrint('token : ' + self.artistToken)
    PixivHelper.safePrint('urls  : ')
    for item in self.imageList:
      PixivHelper.safePrint('\t' + item)
    
class PixivImage:
  '''Class for parsing image page, including manga page and big image.'''
  artist     = None
  imageId    = 0
  imageTitle = ""
  imageTags  = []
  imageMode  = ""
  imageUrls  = []
  worksDate  = unicode("")
  worksResolution = unicode("")
  worksTools = unicode("")
  jd_rtv = 0
  jd_rtc = 0
  jd_rtt = 0
  imageCount = 0

  def __init__(self, iid=0, page=None, parent=None):
    self.artist = parent
    if page != None:
      ## check is error page
      if self.IsErrorPage(page):
        raise PixivModelException('An error occurred!', errorCode=2001)
      if self.IsNeedPermission(page):
        raise PixivModelException('Not in MyPick List, Need Permission!', errorCode=2002)
      if self.IsNeedAppropriateLevel(page):
        raise PixivModelException('Public works can not be viewed by the appropriate level!', errorCode=2003)
      if self.IsDeleted(page):
        raise PixivModelException('Image not found/already deleted!', errorCode=2004)
      if self.IsGuroDisabled(page):
        raise PixivModelException('Image is disabled for under 18, check your setting page (R-18/R-18G)!', errorCode=2005)

      ## detect if there is any other error
      errorMessage = self.IsErrorExist(page)
      if errorMessage != None:
        raise PixivModelException('Image Error: ' + errorMessage, errorCode=2006)
        
      ## parse artist information
      if self.artist == None:
        self.artist = PixivArtist(page=page, fromImage=True)

      ## parse image information
      self.ParseInfo(page)
      self.ParseTags(page)
      self.ParseWorksData(page)

      ## check id
      #if iid == self.imageId:
      #  print 'image_id OK'

  def IsErrorPage(self, page):
    errorMessage = 'エラーが発生しました'
    return self.HaveString(page, errorMessage)

  def IsNeedAppropriateLevel(self, page):
    errorMessage = '該当作品の公開レベルにより閲覧できません。'
    return self.HaveString(page, errorMessage)
  
  def IsNeedPermission(self, page):
    errorMessage = 'この作品は、.+さんのマイピクにのみ公開されています|この作品は、.+さんのマイピクにのみ公開されています'
    return self.HaveString(page, errorMessage)

  def IsDeleted(self, page):
    errorMessage = '該当イラストは削除されたか、存在しないイラストIDです。|該当作品は削除されたか、存在しない作品IDです。'
    errorMessage2 = 'The following work is either deleted, or the ID does not exist.'
    return self.HaveString(page, errorMessage) or self.HaveString(page, errorMessage2)

  def IsGuroDisabled(self, page):
    errorMessage = '表示されるページには、18歳未満の方には不適切な表現内容が含まれています。'
    return self.HaveString(page, errorMessage)

  def IsErrorExist(self, page):
    check = page.findAll('span', attrs={'class':'error'})
    if len(check) > 0:
      check2 = page.findAll('strong')
      if len(check2) > 0:
        return check2[0].renderContents()
      return check[0].renderContents()
    return None
  
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
    self.imageTitle = unicode(page.find(attrs={'class':'title'}).string)
    self.jd_rtv = int(page.find(attrs={'class':'view-count'}).string)
    self.jd_rtc = int(page.find(attrs={'class':'rated-count'}).string)
    self.jd_rtt = int(page.find(attrs={'class':'score-count'}).string)

  def ParseWorksData(self, page):
    temp = page.find(attrs={'class':'meta'}).findAll('li')
    #07/22/2011 03:09｜512×600｜RETAS STUDIO
    #07/26/2011 00:30｜Manga 39P｜ComicStudio 鉛筆 つけペン
    #1/05/2011 07:09｜723×1023｜Photoshop SAI 　[ R-18 ]
    self.worksDate = unicode(temp[0].string)
    self.worksResolution = unicode(temp[1].string).replace(u'×',u'x')
    toolsTemp = page.find(attrs={'class':'meta'}).find(attrs={'class':'tools'})
    if toolsTemp!= None and len(toolsTemp) > 0:
      tools = toolsTemp.findAll('li')
      for tool in tools:
        self.worksTools = self.worksTools + ' ' + unicode(tool.string)
      self.worksTools = self.worksTools.strip()

  def ParseTags(self, page):
    del self.imageTags[:]
    temp = page.find(id='tags').findAll('a')
    for tag in temp:
      if not tag.string == None:
        self.imageTags.append(unicode(tag.string))

  def PrintInfo(self):
    PixivHelper.safePrint( 'Image Info')
    PixivHelper.safePrint( 'img id: ' + str(self.imageId))
    PixivHelper.safePrint( 'title : ' + self.imageTitle)
    PixivHelper.safePrint( 'mode  : ' + self.imageMode)
    PixivHelper.safePrint( 'tags  :')
    PixivHelper.safePrint( ', '.join(self.imageTags))
    PixivHelper.safePrint( 'views : ' + str(self.jd_rtv))
    PixivHelper.safePrint( 'rating: ' + str(self.jd_rtc))
    PixivHelper.safePrint( 'total : ' + str(self.jd_rtt))
    PixivHelper.safePrint( 'Date : ' + self.worksDate)
    PixivHelper.safePrint( 'Resolution : ' + self.worksResolution)
    PixivHelper.safePrint( 'Tools : ' + self.worksTools)
    return ""

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
      raise PixivModelException('No images found for: '+ str(self.imageId))
    return self.imageUrls

  def ParseBigImages(self, page):
    temp = page.find('img')['src']
    imageCount = 1
    return str(temp)

  def ParseMangaImages(self, page):
    urls = []
    scripts = page.findAll('script')
    string = ''
    for script in scripts:
      string += str(script)
    # normal: http://img04.pixiv.net/img/xxxx/12345_p0.jpg
    # mypick: http://img04.pixiv.net/img/xxxx/12344_5baa86aaad_p0.jpg
    pattern = re.compile('http.*?\d+[_0-9a-z_]*_p\d+\..{3}')
    pattern2 = re.compile('http.*?(\d+[_0-9a-z_]*_p\d+)\..{3}')
    m = pattern.findall(string)
    self.imageCount = len(m)
    for img in m:
      temp = str(img)
      m2 = pattern2.findall(temp)         ## 1234_p0
      temp = temp.replace(m2[0], m2[0].replace('_p', '_big_p')) 
      urls.append(temp)
      temp = str(img)
      urls.append(temp)
    return urls    

class PixivModelException(Exception):
  errorCode = 0
  
  def __init__(self, value, errorCode = 0):
    self.value = value
    self.errorCode = errorCode
    
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
  def parseList(filename, rootDir=None):
    '''read list.txt and return the list of PixivListItem'''
    l = list()

    if not os.path.exists(filename) :
      raise PixivModelException("File doesn't exists or no permission to read: " + filename)

    reader = PixivHelper.OpenTextFile(filename)
    for line in reader:
        if line.startswith('#') or len(line) < 1:
          continue
        line = PixivHelper.toUnicode(line)
        line = line.strip()        
        items = line.split(" ", 1)
        try:
          member_id = int(items[0])
          path = ""
          if len(items) > 1:
            path = items[1].strip()

            path = path.replace('\"', '')
            if rootDir != None:
              path = path.replace('%root%', rootDir)
            else:
              path = path.replace('%root%', '')
              
            path = os.path.abspath(path)
            # have drive letter
            if re.match(r'[a-zA-Z]:', path):
                dirpath = path.split(os.sep, 1)
                dirpath[1] = PixivHelper.sanitizeFilename(dirpath[1], None)
                path = os.sep.join(dirpath)
            else:
                path = PixivHelper.sanitizeFilename(path, rootDir)
            
            path = path.replace('\\\\', '\\')
            path = path.replace('\\', os.sep)

          listItem = PixivListItem(member_id, path)
          l.append(listItem)
        except:
          PixivHelper.safePrint('Invalid line: '+line)
          (exType, value, traceback) = sys.exc_info()
          print 'Error at PixivListItem.parseList():', exType, value

    reader.close()
    return l

class PixivNewIllustBookmark:
  '''Class for parsing New Illust from Bookmarks'''
  imageList  = None
  isLastPage = None
  haveImages = None

  def __init__(self, page):
    self.__ParseNewIllustBookmark(page)
    self.__CheckLastPage(page)
    if len(self.imageList) > 0:
      self.haveImages = True
    else:
      self.haveImages = False
    
  def __ParseNewIllustBookmark(self,page):
    self.imageList = list()
    try:
      result = page.find(attrs={'class':'images autopagerize_page_element'}).findAll('a')
      for r in result:
        href = re.search('member_illust.php?.*illust_id=(\d+)', r['href'])
        if href != None:
          href = href.group(1)
          self.imageList.append(int(href))
    except:
      pass
    return self.imageList

  def __CheckLastPage(self, page):
    check = page.findAll('a', attrs={'class':'button', 'rel':'next'})
    if len(check) > 0:
      self.isLastPage = False
    else:
      self.isLastPage = True
    return self.isLastPage

class PixivBookmark:
  '''Class for parsing Bookmarks'''

  @staticmethod
  def parseBookmark(page):
    '''Parse favorite artist page'''
    import PixivDBManager
    l = list()
    db = PixivDBManager.PixivDBManager()
    __re_member = re.compile(r'member\.php\?id=(\d*)')
    try:
      result = page.find(attrs={'class':'members'}).findAll('a')

      ##filter duplicated member_id
      d = collections.OrderedDict()
      for r in result:
        member_id = __re_member.findall(r['href'])
        if len(member_id) > 0:
          d[member_id[0]] = member_id[0]
      result2 = list(d.keys())
      
      for r in result2:
        item = db.selectMemberByMemberId2(r)
        l.append(item)
    except:
      pass
    return l

  @staticmethod
  def parseImageBookmark(page):
    imageList = list()
    temp = page.find(attrs={'class':'display_works linkStyleWorks'}).ul
    temp = temp.findAll('a')
    if temp == None or len(temp) == 0:
      return imageList
    for item in temp:
      href = re.search('member_illust.php?.*illust_id=(\d+)', str(item))
      if href != None:
        href = href.group(1)
        imageList.append(int(href))
        
    #remove duplicate
    imageList = list(set(imageList))
    
    return imageList

  @staticmethod
  def exportList(l, filename):
    from datetime import datetime
    if not filename.endswith('.txt'):
      filename = filename + '.txt'
    writer = codecs.open(filename, 'wb', encoding='utf-8')
    writer.write(u'###Export date: ' + str(datetime.today()) +'###\n')
    for item in l:
      data = unicode(str(item.memberId))
      if len(item.path) > 0:        
        data = data + unicode(' ' + item.path)
      writer.write(data)
      writer.write(u'\r\n')
    writer.write('###END-OF-FILE###')
    writer.close()

import collections
PixivTagsItem = collections.namedtuple('PixivTagsItem', ['imageId', 'bookmarkCount', 'imageResponse'])

class PixivTags:
  '''Class for parsing tags search page'''
  #imageList = None
  itemList = None
  haveImage = None
  isLastPage = None
  
  def parseTags(self, page):
    '''parse tags search page and return the image list with bookmarkCound and imageResponse'''
    self.itemList = list()

    __re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
    ## new parse for bookmark items
    items = page.findAll('li', attrs={'class':'image'})
    for item in items:
      if str(item).find('member_illust.php?') > -1:
        image_id = __re_illust.findall(item.find('a')['href'])[0]
        bookmarkCount = -1
        imageResponse = -1
        countList = item.find('ul', attrs={'class':'count-list'})
        if countList != None:
          countList = countList.findAll('li')
          if len(countList) > 0 :
            for count in countList:
              temp = count.find('a')
              if temp['class'] == 'bookmark-count ui-tooltip' :
                bookmarkCount = temp.contents[1]
              elif temp['class'] == 'image-response-count ui-tooltip' :
                imageResponse = temp.contents[1]
        self.itemList.append(PixivTagsItem(int(image_id), int(bookmarkCount), int(imageResponse)))
    self.checkPage(page)
    return self.itemList

  def parseMemberTags(self, page):
    '''parse member tags search page and return the image list'''
    self.itemList = list()

    __re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
    linkList = page.findAll('a')
    for link in linkList:
      if link.has_key('href') :
        result = __re_illust.findall(link['href'])
        if len(result) > 0 :
          image_id = int(result[0])
          self.itemList.append(PixivTagsItem(int(image_id), 0, 0))
    self.checkPage(page)
    return self.itemList

  def checkPage(self, page):
    # Check if have image
    if len(self.itemList) > 0:
      self.haveImage = True
    else:
      self.haveImage = False

    # check if the last page
    check = page.findAll('li', attrs={'class':'next'})
    if len(check) > 0:
      self.isLastPage = False
    else:
      self.isLastPage = True

    # check if the last page for member tags
    if self.isLastPage:
      check = page.findAll(name='a', attrs={ 'class':'button', 'rel':'next'})
      if len(check) > 0:
        self.isLastPage = False
      else:
        self.isLastPage = True
     
  @staticmethod
  def parseTagsList(filename):
    '''read tags.txt and return the tags list'''
    l = list()

    if not os.path.exists(filename) :
      raise PixivModelException("File doesn't exists or no permission to read: " + filename)

    reader = PixivHelper.OpenTextFile(filename)
    for line in reader:
        if line.startswith('#') or len(line) < 1:
          continue
        line = line.strip()
        if len(line) > 0 :
          l.append(PixivHelper.toUnicode(line))
    reader.close()
    return l
  
