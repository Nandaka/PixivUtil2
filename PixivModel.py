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
            if self.IsNotLoggedIn(page):
                raise PixivException('Not Logged In!', errorCode=PixivException.NOT_LOGGED_IN)

            if self.IsUserNotExist(page):
                raise PixivException('User ID not exist/deleted!', errorCode=PixivException.USER_ID_NOT_EXISTS)

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


    def ParseInfo(self, page, fromImage=False):
        avatarBox = page.find(attrs={'class':'_unit profile-unit'})
        temp = str(avatarBox.find('a')['href'])
        self.artistId = int(re.search('id=(\d+)', temp).group(1))

        self.artistAvatar = str(page.find('img', attrs={'class':'user-image'})['src'])
        self.artistToken = self.ParseToken(page, fromImage)
        try:
            h1 = page.find('h1', attrs={'class':'user'})
            if h1 is not None  :
                self.artistName = unicode(h1.string.extract())
            else :
                avatar_m = page.findAll(attrs={"class":"avatar_m"})
                if avatar_m is not None and len(avatar_m) > 0 :
                    self.artistName = unicode(avatar_m[0]["title"])
        except:
            self.artistName = self.artistToken ## use the token.

    def ParseToken(self, page, fromImage=False):
        try:
            # get the token from stacc feed
            tabFeeds = page.findAll('a', attrs={'class':'tab-feed'})
            if tabFeeds is not None and len(tabFeeds) > 0:
                for a in tabFeeds:
                    if str(a["href"]).find("stacc/") > 0:
                        self.artistToken = a["href"].split("/")[-1]
                        return self.artistToken
        except:
            raise PixivException('Cannot parse artist token, possibly different image structure.', errorCode = PixivException.PARSE_TOKEN_DIFFERENT_IMAGE_STRUCTURE)

    def ParseImages(self, page):
        del self.imageList[:]
        temp = page.find('ul', attrs={'class':'_image-items'})
        temp = temp.findAll('a')
        if temp == None or len(temp) == 0:
            raise PixivException('No image found!', errorCode=PixivException.NO_IMAGES)
        for item in temp:
            href = re.search('member_illust.php.*illust_id=(\d+)', str(item))
            if href != None:
                href = int(href.group(1))
                # fuck performance :D
                if href not in self.imageList:
                    self.imageList.append(href)

    def IsNotLoggedIn(self, page):
        check = page.findAll('a', attrs={'class':'signup_button'})
        if check != None and len(check) > 0:
            return True
        return False

    def IsUserNotExist(self, page):
        errorMessages = ['該当ユーザーは既に退会したか、存在しないユーザーIDです',
                         'The user has either left pixiv, or the user ID does not exist.',
                         '該当作品は削除されたか、存在しない作品IDです。',
                         'The following work is either deleted, or the ID does not exist.']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsUserSuspended(self, page):
        errorMessages = ['該当ユーザーのアカウントは停止されています。',
                         'This user account has been suspended.']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsErrorExist(self, page):
        check = page.findAll('span', attrs={'class':'error'})
        if len(check) > 0:
            check2 = check[0].findAll('strong')
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
    bookmark_count = -1
    image_response_count = -1
    ugoira_data = ""

    def __init__(self, iid=0, page=None, parent=None, fromBookmark=False, bookmark_count=-1, image_response_count=-1):
        self.artist = parent
        self.fromBookmark = fromBookmark
        self.bookmark_count = bookmark_count
        self.imageId = iid
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

            ## check if there is any other error
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

    def IsNotLoggedIn(self, page):
        check = page.findAll('a', attrs={'class':'signup_button'})
        if check != None and len(check) > 0:
            return True
        return False

    def IsErrorPage(self, page):
        check = page.findAll('span', attrs={'class':'error'})
        if len(check) > 0:
            check2 = check[0].findAll('strong')
            if len(check2) > 0:
                return check2[0].renderContents()
            return check[0].renderContents()
        return None

    def IsNeedAppropriateLevel(self, page):
        errorMessages = ['該当作品の公開レベルにより閲覧できません。']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsNeedPermission(self, page):
        errorMessages = ['この作品は.+さんのマイピクにのみ公開されています|この作品は、.+さんのマイピクにのみ公開されています',
                         'This work is viewable only for users who are in .+\'s My pixiv list',
                         'Only .+\'s My pixiv list can view this.',
                         '<section class="restricted-content">']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsDeleted(self, page):
        errorMessages = ['該当イラストは削除されたか、存在しないイラストIDです。|該当作品は削除されたか、存在しない作品IDです。',
                         'The following work is either deleted, or the ID does not exist.',
                         'This work was deleted.']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsGuroDisabled(self, page):
        errorMessages = ['表示されるページには、18歳未満の方には不適切な表現内容が含まれています。',
                         'The page you are trying to access contains content that may be unsuitable for minors']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsErrorExist(self, page):
        check = page.findAll('span', attrs={'class':'error'})
        if len(check) > 0:
            check2 = check[0].findAll('strong')
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

    def ParseInfo(self, page):
        temp = None
        links = page.find(attrs={'class':'works_display'}).findAll('a')
        for a in links:
            if re.search('illust_id=(\d+)',a['href']) is not None:
                temp = str(a['href'])
                break

        if temp is None:
            # changes on pixiv website to handle big image
            self.imageMode = "bigNew"

        else :
            temp_id = int(re.search('illust_id=(\d+)',temp).group(1))
            assert temp_id == self.imageId, "Invalid Id detected ==> %i != %i" % (temp_id, self.imageId)
            self.imageMode = re.search('mode=(big|manga|ugoira_view)',temp).group(1)

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

        self.jd_rtv = int(page.find(attrs={'class':'view-count'}).string)
        self.jd_rtc = int(page.find(attrs={'class':'rated-count'}).string)
        self.jd_rtt = int(page.find(attrs={'class':'score-count'}).string)

    def ParseWorksData(self, page):
        temp = page.find(attrs={'class':'meta'}).findAll('li')
        #07/22/2011 03:09|512×600|RETAS STUDIO
        #07/26/2011 00:30|Manga 39P|ComicStudio 鉛筆 つけペン
        #1/05/2011 07:09|723×1023|Photoshop SAI  [ R-18 ]
        #2013年3月16日 06:44 | 800×1130 | Photoshop ComicStudio | R-18
        #2013年12月14日 19:00 855×1133 PhotoshopSAI
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

    def ParseImages(self, page, mode=None, _br=None):
        if page == None:
            raise PixivException('No page given', errorCode = PixivException.NO_PAGE_GIVEN)
        if mode == None:
            mode = self.imageMode

        del self.imageUrls[:]
        if mode == 'big' or mode == 'bigNew':
            self.imageUrls.append(self.ParseBigImages(page))
        elif mode == 'manga':
            self.imageUrls = self.CheckMangaType(page, _br)
        elif mode == 'ugoira_view':
            self.imageUrls.append(self.ParseUgoira(page))
        if len(self.imageUrls) == 0:
            raise PixivException('No images found for: '+ str(self.imageId), errorCode = PixivException.NO_IMAGES)
        return self.imageUrls

    def ParseBigImages(self, page):
        self.imageCount = 1

        # new layout for big 20141216
        temp = page.find('img', attrs={'class': 'original-image'})
        if temp is not None:
            return str(temp['data-src'])

        # new layout for big 20141212
        temp = page.find('img', attrs={'class': 'big'})
        if temp is not None:
            return str(temp['data-src'])

        # old layout
        temp = page.find('img')['src']
        return str(temp)

    def ParseUgoira(self, page):
        scripts = page.findAll('script')
        for scr in scripts:
            if scr.text.startswith("pixiv.context.illustId"):
                lines = scr.text.split(";")
                for line in lines:
                    if line.startswith ("pixiv.context.ugokuIllustFullscreenData"):
                        line = line.split("=", 2)[1].strip()
                        import json
                        js = json.loads(line)
                        self.ugoira_data = line
                        self.imageCount = 1
                        return js["src"]

    def CheckMangaType(self, page, _br):
        # _book-viewer
        twopage_format = page.find("html", attrs={'class': re.compile(r".*\b_book-viewer\b.*")})
        if twopage_format is not None and len(twopage_format) > 0:
            # new format
            print "2-page manga viewer mode"
            return self.ParseMangaImagesScript(page)
        else:
            # old  format
            return self.ParseMangaImagesNew(page, _br)

    def ParseMangaImagesScript(self, page):
        urls = []
        scripts = page.findAll('script')
        pattern = re.compile("pixiv.context.originalImages\[\d+\].*(http.*)\"")
        for script in scripts:
            s = str(script)
            if "pixiv.context.originalImages" in s:
                # <script>pixiv.context.images[10] = "http:\/\/i2.pixiv.net\/c\/1200x1200\/img-master\/img\/2014\/10\/03\/14\/13\/59\/46322053_p10_master1200.jpg";pixiv.context.thumbnailImages[10] = "http:\/\/i2.pixiv.net\/c\/128x128\/img-master\/img\/2014\/10\/03\/14\/13\/59\/46322053_p10_square1200.jpg";pixiv.context.originalImages[10] = "http:\/\/i2.pixiv.net\/img-original\/img\/2014\/10\/03\/14\/13\/59\/46322053_p10.jpg";</script>
                m = pattern.findall(s)
                if len(m) > 0:
                    # http:\\/\\/i2.pixiv.net\\/img-original\\/img\\/2014\\/10\\/03\\/14\\/13\\/59\\/46322053_p0.jpg
                    img = m[0].replace('\\/', "/")
                    urls.append(img)

        self.imageCount = len(urls)
        return urls

    def ParseMangaImagesNew(self, page, _br):
        urls = []
        mangaSection = page.find("section", attrs={'class':'manga'})
        links = mangaSection.findAll('a')
        ## /member_illust.php?mode=manga_big&illust_id=46279245&page=0
        if _br is None:
            import PixivBrowserFactory
            _br = PixivBrowserFactory.getExistingBrowser()

        for link in links:
            try:
                href = _br.fixUrl(link["href"])
                print "Fetching big image page:", href
                bigPage = _br.getPixivPage(url=href, referer = "http://www.pixiv.net/member_illust.php?mode=manga&illust_id=" + str(self.imageId))

                bigImg = bigPage.find('img')
                imgUrl = bigImg["src"]
                print "Found: ", imgUrl
                urls.append(imgUrl)
                bigImg.decompose()
                bigPage.decompose()
                del bigImg
                del bigPage
            except Exception as ex:
                print ex

        total = page.find("span", attrs={'class':'total'})
        if total is not None:
            self.imageCount = int(total.string)
            if self.imageCount != len(urls):
                raise PixivException("Different images count: " + str(self.imageCount) + " != " + str(len(urls)))

        return urls

    def ParseBookmarkDetails(self, page):
        if page == None:
            raise PixivException('No page given', errorCode = PixivException.NO_PAGE_GIVEN)
        try:
            countUl = page.findAll('ul', attrs={'class':'count-list'})
            if countUl is not None and len(countUl) > 0:
                countA = countUl[0].findAll('a')
                if countA is not None and len(countA) > 0:
                    for a in countA:
                        if "bookmark-count" in a["class"]:
                            self.bookmark_count = int(a.text)
                        elif "image-response-count" in a["class"]:
                            self.image_response_count = int(a.text)
                    return

            ## no bookmark count
            self.bookmark_count = 0
            self.image_response_count = 0
        except:
            PixivHelper.GetLogger().exception("Cannot parse bookmark count for: " + str(self.imageId))

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
        info.write("BookmarkCount= " + str(self.bookmark_count) + "\r\n")
        info.write("Link       = http://www.pixiv.net/member_illust.php?mode=medium&illust_id=" + str(self.imageId) + "\r\n")
        info.write("Ugoira Data= " + str(self.ugoira_data) + "\r\n")
        info.close()

    def WriteUgoiraData(self, filename):
        info = None
        try:
            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".js", 'wb', encoding='utf-8')
            PixivHelper.GetLogger().exception("Error when saving image info: " + filename + ", file is saved to: " + str(self.imageId) + ".js")
        info.write(str(self.ugoira_data))
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
        lineNo = 1
        try:
            for line in reader:
                originalLine = line
                ##PixivHelper.safePrint("Processing: " + line)
                if line.startswith('#') or len(line) < 1:
                    continue
                if len(line.strip()) == 0:
                    continue
                line = PixivHelper.toUnicode(line)
                line = line.strip()
                items = line.split(" ", 1)

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
                lineNo = lineNo + 1
                originalLine = ""
        except UnicodeDecodeError:
            PixivHelper.GetLogger().exception("PixivListItem.parseList(): Invalid value when parsing list")
            PixivHelper.printAndLog('error', 'Invalid value: {0} at line {1}, try to save the list.txt in UTF-8.'.format(originalLine, lineNo))
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
            result = page.find(attrs={'class':'_image-items autopagerize_page_element'}).findAll('a')
            for r in result:
                href = re.search('member_illust.php?.*illust_id=(\d+)', r['href'])
                if href != None:
                    href = int(href.group(1))
                    # fuck performance :D
                    if href not in self.imageList:
                        self.imageList.append(href)
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
        temp = page.find('ul', attrs={'class':'_image-items'})
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
                if not str(image_id).isdigit() or image_id in ignore:
                    continue

                bookmarkCount = 0
                imageResponse = 0
                countList = item.find('ul', attrs={'class':'count-list'})
                if countList != None:
                    countList = countList.findAll('li')
                    if len(countList) > 0 :
                        for count in countList:
                            temp = count.find('a')
                            if 'bookmark-count' in temp['class']:
                                bookmarkCount = temp.contents[1]
                            elif 'image-response-count' in temp['class'] :
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

