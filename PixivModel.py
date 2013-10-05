# -*- coding: UTF-8 -*-
from BeautifulSoup import BeautifulSoup, Tag
import os
import re
import sys
import codecs
import collections
import PixivHelper
from PixivException import PixivException
import datetime
import json

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
      ## check if logged in
      if self.IsNotLoggedIn(page):
        raise PixivException('Not Logged In!', errorCode=PixivException.NOT_LOGGED_IN)

      ## detect if artist exist
      if self.IsUserNotExist(page):
        raise PixivException('User ID not exist/deleted!', errorCode=PixivException.USER_ID_NOT_EXISTS)

      ## detect if artist account is suspended.
      if self.IsUserSuspended(page):
        raise PixivException('User Account is Suspended!', errorCode=PixivException.USER_ID_SUSPENDED)

      ## detect if there is any other error
      errorMessage = self.IsErrorExist(page)
      if errorMessage != None:
        raise PixivException('Member Error: ' + errorMessage, errorCode=PixivException.OTHER_MEMBER_ERROR)

      ## detect if there is server error
      errorMessage = self.IsServerErrorExist(page)
      if errorMessage != None:
        raise PixivException('Member Error: ' + errorMessage, errorCode=PixivException.SERVER_ERROR)

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
    avatarBox = page.find(attrs={'class':'_unit profile-unit'})
    temp = str(avatarBox.find('a')['href'])
    self.artistId = int(re.search('id=(\d+)', temp).group(1))

    try:
      ##self.artistName = unicode(page.h2.span.a.string.extract())
      self.artistName = unicode(page.find('h1', attrs={'class':'user'}).string.extract())
    except:
      self.artistName = unicode(page.findAll(attrs={"class":"avatar_m"})[0]["title"])
    self.artistAvatar = str(page.find('img', attrs={'class':'user-image'})['src'])
    self.artistToken = self.ParseToken(page, fromImage)


  def ParseToken(self, page, fromImage=False):
    if self.artistAvatar == 'http://source.pixiv.net/source/images/no_profile.png':
      if fromImage:
        token = str(page.find(attrs={'class':'works_display'}).find('img')['src'])
        #print token
        return token.split('/')[-2]
      else :
        artistToken = None
        try:
          temp = page.find(attrs={'class':'display_works linkStyleWorks'}).ul
          if temp != None:
            tokens = temp.findAll('img', attrs={'class':'_thumbnail'})
            for token in tokens:
              try:
                tempImage = token['data-src']
              except:
                tempImage = token['src']
              folders = tempImage.split('/')
              ## skip http://i2.pixiv.net/img-inf/img/2013/04/07/03/08/21/34846113_s.jpg
              if folders[3] == 'img-inf':
                continue
              artistToken = folders[-2]
              if artistToken != 'common':
                return artistToken

            ## all thumb images are using img-inf
            ## take the first image and check the medium page
            if artistToken == None or artistToken != 'common':
              PixivHelper.GetLogger().info("Unable to parse Artist Token from image list, try to parse from the first image")
              import PixivBrowserFactory, PixivConstant
              firstImageLink = temp.find('a', attrs={'class':'work'})['href']
              if firstImageLink.find("http") != 0:
                firstImageLink = PixivConstant.PIXIV_URL + firstImageLink
              PixivHelper.GetLogger().info("Using: " + firstImageLink + " for parsing artist token")
              imagePage = PixivBrowserFactory.getBrowser().open(firstImageLink)
              imageResult = BeautifulSoup(imagePage.read())
              token = str(imageResult.find(attrs={'class':'works_display'}).find('img')['src'])
              return token.split('/')[-2]

            raise PixivException('Cannot parse artist token, possibly different image structure.', errorCode = PixivException.PARSE_TOKEN_DIFFERENT_IMAGE_STRUCTURE)
        except TypeError:
          raise PixivException('Cannot parse artist token, possibly no images.', errorCode = PixivException.PARSE_TOKEN_NO_IMAGES)
    else :
      temp = self.artistAvatar.split('/')
      return temp[-2]

  def ParseImages(self, page):
    del self.imageList[:]
    temp = page.find(attrs={'class':'display_works linkStyleWorks'}).ul
    temp = temp.findAll('a')
    if temp == None or len(temp) == 0:
      raise PixivException('No image found!', errorCode=PixivException.NO_IMAGES)
    for item in temp:
      #print item
      href = re.search('member_illust.php.*illust_id=(\d+)', str(item))
      if href != None:
        #print href.group(0)
        href = href.group(1)
        self.imageList.append(int(href))
    ## Remove duplicates
    ##self.imageList = list(set(self.imageList))
##    for item in self.imageList:
##      print item
##    raw_input()

  def HaveString(self, page, string):
    pattern = re.compile(string)
    test_2 = pattern.findall(str(page))
    if len(test_2) > 0 :
        if len(test_2[-1]) > 0 :
            return True
    else :
      return False

  def IsNotLoggedIn(self, page):
    check = page.findAll('a', attrs={'class':'signup_button'})
    if check != None and len(check) > 0:
      return True
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

  def IsServerErrorExist(self, page):
    check = page.findAll('div', attrs={'class':'errorArea'})
    if len(check) > 0:
      check2 = check[0].findAll('h2')
      if len(check2) > 0:
        return check2[0].renderContents()
      return check[0].renderContents()
    return None

  def CheckLastPage(self, page):
    check = page.findAll('a', attrs={'class':'_button', 'rel':'next'})
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
      PixivHelper.safePrint('\t' + str(item))

class PixivImage:
  '''Class for parsing image page, including manga page and big image.'''
  artist     = None
  originalArtist  = None
  imageId    = 0
  imageTitle = ""
  imageCaption = ""
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
  fromBookmark = False
  worksDateDateTime = datetime.datetime.fromordinal(1)

  def __init__(self, iid=0, page=None, parent=None, fromBookmark=False):
    self.artist = parent
    self.fromBookmark = fromBookmark
    self.imageUrls = []

    if page != None:
      ## check is error page
      if self.IsNotLoggedIn(page):
        raise PixivException('Not Logged In!', errorCode=PixivException.NOT_LOGGED_IN)
      if self.IsNeedPermission(page):
        raise PixivException('Not in MyPick List, Need Permission!', errorCode=PixivException.NOT_IN_MYPICK)
      if self.IsNeedAppropriateLevel(page):
        raise PixivException('Public works can not be viewed by the appropriate level!', errorCode=PixivException.NO_APPROPRIATE_LEVEL)
      if self.IsDeleted(page):
        raise PixivException('Image not found/already deleted!', errorCode=PixivException.IMAGE_DELETED)
      if self.IsGuroDisabled(page):
        raise PixivException('Image is disabled for under 18, check your setting page (R-18/R-18G)!', errorCode=PixivException.R_18_DISABLED)

      # check if there is any other error
      if self.IsErrorPage(page):
        raise PixivException('An error occurred!', errorCode=PixivException.OTHER_IMAGE_ERROR)

      ## detect if there is any other error
      errorMessage = self.IsErrorExist(page)
      if errorMessage != None:
        raise PixivException('Image Error: ' + errorMessage, errorCode=PixivException.UNKNOWN_IMAGE_ERROR)

      ## detect if there is server error
      errorMessage = self.IsServerErrorExist(page)
      if errorMessage != None:
        raise PixivException('Image Error: ' + errorMessage, errorCode=PixivException.SERVER_ERROR)

      ## parse artist information
      if self.artist == None:
        self.artist = PixivArtist(page=page, fromImage=True)

      if fromBookmark and self.originalArtist == None:
        self.originalArtist = PixivArtist(page=page, fromImage=True)

      ## parse image information
      self.ParseInfo(page)
      self.ParseTags(page)
      self.ParseWorksData(page)

      ## check id
      #if iid == self.imageId:
      #  print 'image_id OK'

  def IsNotLoggedIn(self, page):
    check = page.findAll('a', attrs={'class':'signup_button'})
    if check != None and len(check) > 0:
      return True
    return False

  def IsErrorPage(self, page):
    ##errorMessage = 'エラーが発生しました'
    ##return self.HaveString(page, errorMessage)
    check = page.findAll('span', attrs={'class':'error'})
    if len(check) > 0:
      check2 = page.findAll('strong')
      if len(check2) > 0:
        return check2[0].renderContents()
      return check[0].renderContents()
    return None

  def IsNeedAppropriateLevel(self, page):
    errorMessage = '該当作品の公開レベルにより閲覧できません。'
    return self.HaveString(page, errorMessage)

  def IsNeedPermission(self, page):
    errorMessage = 'この作品は.+さんのマイピクにのみ公開されています|この作品は、.+さんのマイピクにのみ公開されています'
    errorMessage2 = 'This work is viewable only for users who are in .+\'s My pixiv list'
    return self.HaveString(page, errorMessage) or self.HaveString(page, errorMessage2)

  def IsDeleted(self, page):
    errorMessage = '該当イラストは削除されたか、存在しないイラストIDです。|該当作品は削除されたか、存在しない作品IDです。'
    errorMessage2 = 'The following work is either deleted, or the ID does not exist.'
    return self.HaveString(page, errorMessage) or self.HaveString(page, errorMessage2)

  def IsGuroDisabled(self, page):
    errorMessage = '表示されるページには、18歳未満の方には不適切な表現内容が含まれています。'
    errorMessage2 = 'The page you are trying to access contains content that may be unsuitable for minors'
    return self.HaveString(page, errorMessage) or self.HaveString(page, errorMessage2)

  def IsErrorExist(self, page):
    check = page.findAll('span', attrs={'class':'error'})
    if len(check) > 0:
      check2 = page.findAll('strong')
      if len(check2) > 0:
        return check2[0].renderContents()
      return check[0].renderContents()
    return None

  def IsServerErrorExist(self, page):
    check = page.findAll('div', attrs={'class':'errorArea'})
    if len(check) > 0:
      check2 = check[0].findAll('h2')
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

    # remove premium-introduction-modal so we can get caption from work-info
    # somehow selecting section doesn't works
    premium_introduction_modal = page.findAll('div', attrs={'id':'premium-introduction-modal'})
    for modal in premium_introduction_modal:
        modal.extract()

    meta_data = page.findAll('meta')
    for meta in meta_data:
        if meta.has_key("property"):
            if "og:title" == meta["property"]:
                self.imageTitle = meta["content"].split("|")[0].strip()
            if "og:description" in meta["property"]:
                self.imageCaption = meta["content"]

##    work_details_unit = page.findAll('div', {'class':'_unit work-detail-unit'})
##    if work_details_unit is not None and len(work_details_unit) > 0:
##        titles = work_details_unit[0].findAll('h1', attrs={'class':'title'})
##        for title in titles:
##          if title.string != None and title.string != "pixiv":
##            self.imageTitle = unicode(title.string)
##            break
##
##        captions = work_details_unit[0].findAll('p', attrs={'class':'caption'})
##        if captions != None and len(captions) > 0:
##            self.imageCaption = unicode("".join(unicode(item) for item in captions[0].contents))

    self.jd_rtv = int(page.find(attrs={'class':'view-count'}).string)
    self.jd_rtc = int(page.find(attrs={'class':'rated-count'}).string)
    self.jd_rtt = int(page.find(attrs={'class':'score-count'}).string)

  def ParseWorksData(self, page):
    temp = page.find(attrs={'class':'meta'}).findAll('li')
    #07/22/2011 03:09｜512×600｜RETAS STUDIO
    #07/26/2011 00:30｜Manga 39P｜ComicStudio 鉛筆 つけペン
    #1/05/2011 07:09｜723×1023｜Photoshop SAI 　[ R-18 ]
    #2013年3月16日 06:44 | 800×1130 | Photoshop ComicStudio | R-18
    self.worksDate = PixivHelper.toUnicode(temp[0].string, encoding=sys.stdin.encoding).replace(u'/', u'-')
    if self.worksDate.find('-') > -1:
      try:
         self.worksDateDateTime = datetime.datetime.strptime(self.worksDate, u'%m-%d-%Y %H:%M')
      except ValueError as ve:
         PixivHelper.GetLogger().exception('Error when parsing datetime: {0} for imageId {1}'.format(self.worksDate, self.imageId))
         self.worksDateDateTime = datetime.datetime.strptime(self.worksDate.split(" ")[0], u'%Y-%m-%d')
    else:
      tempDate = self.worksDate.replace(u'年', '-').replace(u'月','-').replace(u'日', '')
      self.worksDateDateTime = datetime.datetime.strptime(tempDate, '%Y-%m-%d %H:%M')

    self.worksResolution = unicode(temp[1].string).replace(u'×',u'x')
    toolsTemp = page.find(attrs={'class':'meta'}).find(attrs={'class':'tools'})
    if toolsTemp!= None and len(toolsTemp) > 0:
      tools = toolsTemp.findAll('li')
      for tool in tools:
        self.worksTools = self.worksTools + ' ' + unicode(tool.string)
      self.worksTools = self.worksTools.strip()

  def ParseTags(self, page):
    del self.imageTags[:]
    temp = page.find(attrs={'class':'tags'})
    if temp != None and len(temp) > 0:
      temp2 = temp.findAll('a')
      if temp2 != None and len(temp2) > 0:
        for tag in temp2:
          if not tag.string == None and tag['class'] == 'text':
            self.imageTags.append(unicode(tag.string))

  def PrintInfo(self):
    PixivHelper.safePrint( 'Image Info')
    PixivHelper.safePrint( 'img id: ' + str(self.imageId))
    PixivHelper.safePrint( 'title : ' + self.imageTitle)
    PixivHelper.safePrint( 'caption : ' + self.imageCaption)
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
      raise PixivException('No page given', errorCode = PixivException.NO_PAGE_GIVEN)
    if mode == None:
      mode = self.imageMode

    del self.imageUrls[:]
    if mode == 'big':
      self.imageUrls.append(self.ParseBigImages(page))
    elif mode == 'manga':
      self.imageUrls = self.ParseMangaImages(page)
    if len(self.imageUrls) == 0:
      raise PixivException('No images found for: '+ str(self.imageId), errorCode = PixivException.NO_IMAGES)
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
    pattern = re.compile('http.*?(?<!mobile)\d+[_0-9a-z_]*_p\d+\..{3}')
    pattern2 = re.compile('http.*?(?<!mobile)(\d+[_0-9a-z_]*_p\d+)\..{3}')
    m = pattern.findall(string)

    # filter mobile thumb: http://i1.pixiv.net/img01/img/sokusekimaou/mobile/20592252_128x128_p8.jpg
    m2 = []
    for img in m:
        if img.find('/mobile/') == -1:
            m2.append(img)
    m = m2

    self.imageCount = len(m)
    for img in m:
      temp = str(img)
      m2 = pattern2.findall(temp)         ## 1234_p0
      temp = temp.replace(m2[0], m2[0].replace('_p', '_big_p'))
      urls.append(temp)
      temp = str(img)
      urls.append(temp)
    return urls

  def WriteInfo(self, filename):
    info = None
    try:
      info = codecs.open(filename, 'wb', encoding='utf-8')
    except IOError:
      info = codecs.open(str(self.imageId) + ".txt", 'wb', encoding='utf-8')
      PixivHelper.GetLogger().exception("Error when saving image info: " + filename + ", file is saved to: " + str(self.imageId) + ".txt")

    info.write("ArtistID   = " + str(self.artist.artistId) + "\r\n")
    info.write("ArtistName = " + self.artist.artistName + "\r\n")
    info.write("ImageID    = " + str(self.imageId) + "\r\n")
    info.write("Title      = " + self.imageTitle + "\r\n")
    info.write("Caption    = " + self.imageCaption + "\r\n")
    info.write("Tags       = " + ", ".join(self.imageTags) + "\r\n")
    info.write("Image Mode = " + self.imageMode + "\r\n")
    info.write("Pages      = " + str(self.imageCount) + "\r\n")
    info.write("Date       = " + self.worksDate + "\r\n")
    info.write("Resolution = " + self.worksResolution + "\r\n")
    info.write("Tools      = " + self.worksTools + "\r\n")
    info.write("Link       = http://www.pixiv.net/member_illust.php?mode=medium&illust_id=" + str(self.imageId) + "\r\n")
    info.close()

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
      raise PixivException("File doesn't exists or no permission to read: " + filename, errorCode=PixivException.FILE_NOT_EXISTS_OR_NO_WRITE_PERMISSION)

    reader = PixivHelper.OpenTextFile(filename)
    lineNo = 0
    for line in reader:
        lineNo = lineNo + 1
        originalLine = line
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
          PixivHelper.GetLogger().exception("PixivListItem.parseList(): Invalid value when parsing list")
          PixivHelper.printAndLog('error', 'Invalid value: {0} at line {1}'.format(originalLine, lineNo))

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
      result = page.find(attrs={'class':'image-items autopagerize_page_element'}).findAll('a')
      for r in result:
        href = re.search('member_illust.php?.*illust_id=(\d+)', r['href'])
        if href != None:
          href = href.group(1)
          self.imageList.append(int(href))
    except:
      pass
    return self.imageList

  def __CheckLastPage(self, page):
    check = page.findAll('a', attrs={'class':'_button', 'rel':'next'})
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
        if not int(href) in imageList:
          imageList.append(int(href))
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

    ## get showcase
    ignore = list()
    showcases = page.findAll('section', attrs={'class': 'showcase'})
    for showcase in showcases:
      lis = showcase.findAll('li', attrs={'class':'image'})
      for li in lis:
        if str(li).find('member_illust.php?') > -1:
          image_id = __re_illust.findall(li.find('a')['href'])[0]
          ignore.append(image_id)

    ## new parse for bookmark items
    items = page.findAll('li', attrs={'class':'image-item'})
    for item in items:
      if str(item).find('member_illust.php?') > -1:
        image_id = __re_illust.findall(item.find('a')['href'])[0]
        if image_id in ignore:
          continue
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
    self.checkLastPage(page)
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
    self.checkLastPage(page, fromMember=True)
    return self.itemList

  def checkLastPage(self, page, fromMember=False):
    # Check if have image
    if len(self.itemList) > 0:
      self.haveImage = True
    else:
      self.haveImage = False

    # check if the last page
    check = page.findAll('i', attrs={'class':'_icon sprites-next-linked'})
    if len(check) > 0:
      self.isLastPage = False
    else:
      self.isLastPage = True

    if fromMember:
        # check if the last page for member tags
        if self.isLastPage:
          check = page.findAll(name='a', attrs={'class':'button', 'rel':'next'})
          if len(check) > 0:
            self.isLastPage = False

  @staticmethod
  def parseTagsList(filename):
    '''read tags.txt and return the tags list'''
    l = list()

    if not os.path.exists(filename) :
      raise PixivException("File doesn't exists or no permission to read: " + filename, FILE_NOT_EXISTS_OR_NO_READ_PERMISSION)

    reader = PixivHelper.OpenTextFile(filename)
    for line in reader:
        if line.startswith('#') or len(line) < 1:
          continue
        line = line.strip()
        if len(line) > 0 :
          l.append(PixivHelper.toUnicode(line))
    reader.close()
    return l

class PixivGroup:
   short_pattern = re.compile("https?://www.pixiv.net/member_illust.php\?mode=(.*)&illust_id=(\d+)")
   imageList = None
   externalImageList = None
   maxId = 0

   def __init__(self, jsonResponse):
      data = json.loads(jsonResponse.read())
      self.maxId = data["max_id"]
      self.imageList = list()
      self.externalImageList = list()
      for imageData in data["imageArticles"]:
         if imageData["detail"].has_key("id"):
            imageId = imageData["detail"]["id"]
            self.imageList.append(imageId)
         elif imageData["detail"].has_key("fullscale_url"):
            fullscale_url = imageData["detail"]["fullscale_url"]
            member_id = PixivArtist()
            member_id.artistId     = imageData["user_id"]
            member_id.artistName   = imageData["user_name"]
            member_id.artistAvatar = self.parseAvatar(imageData["img"])
            member_id.artistToken  = self.parseToken(imageData["img"])
            image_data = PixivImage()
            image_data.artist = member_id
            image_data.originalArtist  = member_id
            image_data.imageId    = 0
            image_data.imageTitle = self.shortenPixivUrlInBody(imageData["body"])
            image_data.imageCaption = self.shortenPixivUrlInBody(imageData["body"])
            image_data.imageTags  = []
            image_data.imageMode  = ""
            image_data.imageUrls  = [fullscale_url]
            image_data.worksDate  = imageData["create_time"]
            image_data.worksResolution = unicode("")
            image_data.worksTools = unicode("")
            image_data.jd_rtv = 0
            image_data.jd_rtc = 0
            image_data.jd_rtt = 0
            image_data.imageCount = 0
            image_data.fromBookmark = False
            image_data.worksDateDateTime = datetime.datetime.strptime(image_data.worksDate, '%Y-%m-%d %H:%M:%S')

            self.externalImageList.append(image_data)

   def parseAvatar(self, url):
      return url.replace("_s", "")

   def parseToken(self, url):
      token = url.split('/')[-2]
      if token != "Common":
         return token
      return None

   def shortenPixivUrlInBody(self, string):
      shortened = ""
      result = self.short_pattern.findall(string)
      if result != None and len(result) > 0:
         if result[0][0] == 'medium':
            shortened = "Illust={0}".format(result[0][1])
         else:
            shortened = "Manga={0}".format(result[0][1])
      string = self.short_pattern.sub("", string).strip()
      string = string + " " + shortened
      return string


