# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302


import os
import re
import sys
import shutil
import zipfile
import codecs
import collections
import urllib.request, urllib.parse, urllib.error
import PixivHelper
import urllib.parse
from PixivException import PixivException
from datetime import datetime
import json


class PixivArtist:
    '''Class for parsing member page.'''
    artistId = 0
    artistName = ""
    artistAvatar = ""
    artistToken = ""
    artistBackground = ""
    imageList = []
    isLastPage = None
    haveImages = None
    totalImages = 0
    __re_imageULItemsClass = re.compile(r".*\b_image-items\b.*")

    def __init__(self, mid=0, page=None, fromImage=False):
        if page is not None:
            if self.is_not_logged_in(page):
                raise PixivException('Not Logged In!', errorCode=PixivException.NOT_LOGGED_IN, htmlPage=page)

            if self.IsUserNotExist(page):
                raise PixivException('User ID not exist/deleted!', errorCode=PixivException.USER_ID_NOT_EXISTS, htmlPage=page)

            if self.IsUserSuspended(page):
                raise PixivException('User Account is Suspended!', errorCode=PixivException.USER_ID_SUSPENDED, htmlPage=page)

            # detect if there is any other error
            errorMessage = self.IsErrorExist(page)
            if errorMessage is not None:
                raise PixivException('Member Error: ' + str(errorMessage), errorCode=PixivException.OTHER_MEMBER_ERROR, htmlPage=page)

            # detect if there is server error
            errorMessage = self.IsServerErrorExist(page)
            if errorMessage is not None:
                raise PixivException('Member Error: ' + str(errorMessage), errorCode=PixivException.SERVER_ERROR, htmlPage=page)

            # detect if image count != 0
            if not fromImage:
                self.ParseImages(page)

            # parse artist info
            self.ParseInfo(page, fromImage)

            # check if no images
            self.haveImages = bool(len(self.imageList) > 0)

            # check if the last page
            self.CheckLastPage(page)

    def ParseInfo(self, page, fromImage=False, bookmark=False):
        avatar_box = page.find(attrs={'class': '_unit profile-unit'})
        self.artistToken = self.ParseToken(page, fromImage)

        styles = page.findAll('style')
        for style in styles:
            urls = re.findall('background:.*url\(\'(.*?)\'\)', str(style))
            if len(urls) > 0:
                self.artistBackground = urls[0]
                break

        if avatar_box is not None:
            temp = str(avatar_box.find('a')['href'])
            self.artistId = int(re.search(r'id=(\d+)', temp).group(1))

            self.artistAvatar = str(page.find('img', attrs={'class': 'user-image'})['src'])

            try:
                h1 = page.find('h1', attrs={'class': 'user'})
                if h1 is not None:
                    self.artistName = str(h1.string.extract())
                else:
                    avatar_m = page.findAll(attrs={"class": "avatar_m"})
                    if avatar_m is not None and len(avatar_m) > 0:
                        self.artistName = str(avatar_m[0]["title"])
            except BaseException:
                self.artistName = self.artistToken  # use the token.
            return
        else:
            # Issue #236
            avatar_box = page.find(attrs={'class': '_user-profile-card'})
            if avatar_box is not None:
                temp = avatar_box.find('a')
                self.artistId = int(re.search(r'id=(\d+)', temp['href']).group(1))
                self.artistName = str(temp['title'])
                self.artistAvatar = avatar_box.find('a')['style'].replace("background-image: url('", "").replace("');", "")
                return

        # check if self manage page
        submit_related = page.findAll("ul", attrs={'class': 'related'})
        if len(submit_related) > 0 and str(submit_related[0]).find("upload.php") > 0:
            PixivHelper.print_and_log("info", "Manage Page")
            self.artistAvatar = "no_profile"
            self.artistName = "yourself"
            self.artistToken = "yourself"
            temp = page.find("h1", attrs={'class': 'column-title'}).find("a")
            self.artistId = int(re.findall(r'pixiv.user.id = "(\d+)";', str(page))[0])
            return

        # Issue #236
        # cannot parse information
        self.artistAvatar = "no_profile"
        self.artistName = "self"
        title = page.find("title").text
        filename = "Dump for {0} UnknownProfile for {1}.html".format(title, self.artistToken)
        PixivHelper.print_and_log("error", "Cannot parse artist info, dumping to {0}".format(filename))
        # PixivHelper.printAndLog("error", u"{0}".format(page))
        PixivHelper.dumpHtml(filename, page)

    def ParseToken(self, page, fromImage=False):
        try:
            # get the token from stacc feed
            # tab_feeds = page.findAll('a', attrs={'class': 'tab-feed'})
            tab_feeds = page.findAll(href=re.compile('/stacc/[^/?]*$'))
            if tab_feeds is not None and len(tab_feeds) > 0:
                for a in tab_feeds:
                    if str(a["href"]).find("stacc/") > 0:
                        self.artistToken = a["href"].split("/")[-1]
                        return self.artistToken
            # no token, possibly self page from manage works.
            # https://www.pixiv.net/manage/illusts/
            self.artistToken = "self"
            return self.artistToken
##            if fromImage:
##                uls = page.findAll('ul', attrs={'class': 'tabs'})
##                for ul in uls:
##                    links = ul.findAll('a')
##                    for a in links:
##                        if str(a["href"]).find("stacc/") > 0:
##                            self.artistToken = a["href"].split("/")[-1]
##                            return self.artistToken

        except BaseException:
            raise PixivException('Cannot parse artist token, possibly different image structure.',
                                 errorCode=PixivException.PARSE_TOKEN_DIFFERENT_IMAGE_STRUCTURE, htmlPage=page)

    def ParseImages(self, page):
        del self.imageList[:]
        temp = page.find('ul', attrs={'class': PixivArtist.__re_imageULItemsClass})
        if temp is not None and len(temp) > 0:
            temp = temp.findAll('a')
            for item in temp:
                href = re.search(r'member_illust.php.*illust_id=(\d+)', str(item))
                if href is not None:
                    href = int(href.group(1))
                    # fuck performance :D
                    if href not in self.imageList:
                        self.imageList.append(href)
        self.totalImages = SharedParser.parseCountBadge(page)

        if len(self.imageList) == 0:
            raise PixivException('No image found!', errorCode=PixivException.NO_IMAGES, htmlPage=page)

    def is_not_logged_in(self, page):
        check = page.findAll('div', attrs={'id': 'register-introduction-modal'})
        if check is not None and len(check) > 0:
            return True
        return False

    def IsUserNotExist(self, page):
        errorMessages = ['該当ユーザーは既に退会したか、存在しないユーザーIDです',
                         'The user has either left pixiv, or the user ID does not exist.',
                         'User has left pixiv or the user ID does not exist.',
                         '該当作品は削除されたか、存在しない作品IDです。',
                         'The following work is either deleted, or the ID does not exist.',
                         'User has left pixiv or the user ID does not exist.']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsUserSuspended(self, page):
        errorMessages = ['該当ユーザーのアカウントは停止されています。',
                         'This user account has been suspended.']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsErrorExist(self, page):
        check = page.findAll('span', attrs={'class': 'error'})
        if len(check) > 0:
            check2 = check[0].findAll('strong')
            if len(check2) > 0:
                return check2[0].renderContents()
            return check[0].renderContents()
        return None

    def IsServerErrorExist(self, page):
        check = page.findAll('div', attrs={'class': 'errorArea'})
        if len(check) > 0:
            check2 = check[0].findAll('h2')
            if len(check2) > 0:
                return check2[0].renderContents()
            return check[0].renderContents()
        return None

    def CheckLastPage(self, page):
        check = page.findAll('a', attrs={'class': '_button', 'rel': 'next'})
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
        PixivHelper.safePrint('urls  : {0}'.format(len(self.imageList)))
        for item in self.imageList:
            PixivHelper.safePrint('\t' + str(item))
        PixivHelper.safePrint('total : {0}'.format(self.totalImages))
        PixivHelper.safePrint('last? : {0}'.format(self.isLastPage))


class PixivImage:
    '''Class for parsing image page, including manga page and big image.'''
    artist = None
    originalArtist = None
    imageId = 0
    imageTitle = ""
    imageCaption = ""
    imageTags = []
    imageMode = ""
    imageUrls = []
    worksDate = str("")
    worksResolution = str("")
    worksTools = str("")
    jd_rtv = 0
    jd_rtc = 0
    # jd_rtt = 0
    imageCount = 0
    fromBookmark = False
    worksDateDateTime = datetime.fromordinal(1)
    bookmark_count = -1
    image_response_count = -1
    ugoira_data = ""
    dateFormat = None
    descriptionUrlList = []
    __re_caption = re.compile("caption")

    def __init__(self, iid=0, page=None, parent=None, fromBookmark=False, bookmark_count=-1, image_response_count=-1,
                 dateFormat=None):
        self.artist = parent
        self.fromBookmark = fromBookmark
        self.bookmark_count = bookmark_count
        self.imageId = iid
        self.imageUrls = []
        self.dateFormat = dateFormat
        self.descriptionUrlList = []

        if page is not None:
            # check is error page
            if self.IsNotLoggedIn(page):
                raise PixivException('Not Logged In!', errorCode=PixivException.NOT_LOGGED_IN, htmlPage=page)
            if self.IsNeedPermission(page):
                raise PixivException('Not in MyPick List, Need Permission!', errorCode=PixivException.NOT_IN_MYPICK, htmlPage=page)
            if self.IsNeedAppropriateLevel(page):
                raise PixivException('Public works can not be viewed by the appropriate level!',
                                     errorCode=PixivException.NO_APPROPRIATE_LEVEL, htmlPage=page)
            if self.IsDeleted(page):
                raise PixivException('Image not found/already deleted!', errorCode=PixivException.IMAGE_DELETED, htmlPage=page)
            if self.IsGuroDisabled(page):
                raise PixivException('Image is disabled for under 18, check your setting page (R-18/R-18G)!',
                                     errorCode=PixivException.R_18_DISABLED, htmlPage=page)

            # detect if there is any other error
            errorMessage = self.IsErrorExist(page)
            if errorMessage is not None:
                raise PixivException('Image Error: ' + errorMessage, errorCode=PixivException.UNKNOWN_IMAGE_ERROR, htmlPage=page)

            # detect if there is server error
            errorMessage = self.IsServerErrorExist(page)
            if errorMessage is not None:
                raise PixivException('Image Error: ' + errorMessage, errorCode=PixivException.SERVER_ERROR, htmlPage=page)

            # parse artist information
            if self.artist is None:
                self.artist = PixivArtist(page=page, fromImage=True)

            if fromBookmark and self.originalArtist is None:
                self.originalArtist = PixivArtist(page=page, fromImage=True)
            else:
                self.originalArtist = self.artist

            # parse image information
            self.ParseInfo(page)
            self.ParseTags(page)
            self.ParseWorksData(page)

    def IsNotLoggedIn(self, page):
        check = page.findAll('a', attrs={'class': 'signup_button'})
        if check is not None and len(check) > 0:
            return True
        check = page.findAll('a', attrs={'class': 'ui-button _signup'})
        if check is not None and len(check) > 0:
            return True
        return False

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
                         'この作品は削除されました。',
                         'The following work is either deleted, or the ID does not exist.',
                         'This work was deleted.',
                         'Work has been deleted or the ID does not exist.']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsGuroDisabled(self, page):
        errorMessages = ['表示されるページには、18歳未満の方には不適切な表現内容が含まれています。',
                         'The page you are trying to access contains content that may be unsuitable for minors']
        return PixivHelper.HaveStrings(page, errorMessages)

    def IsErrorExist(self, page):
        check = page.findAll('span', attrs={'class': 'error'})
        if len(check) > 0:
            check2 = check[0].findAll('strong')
            if len(check2) > 0:
                return check2[0].renderContents()

        check = page.findAll('div', attrs={'class': '_unit error-unit'})
        if len(check) > 0:
            check2 = check[0].findAll('p', attrs={'class': 'error-message'})
            if len(check2) > 0:
                return check2[0].renderContents()
        return None

    def IsServerErrorExist(self, page):
        check = page.findAll('div', attrs={'class': 'errorArea'})
        if len(check) > 0:
            check2 = check[0].findAll('h2')
            if len(check2) > 0:
                return check2[0].renderContents()
        return None

    def ParseInfo(self, page):
        temp = None
        links = page.find(attrs={'class': 'works_display'})
        if links is not None:
            links2 = links.findAll('a')
            for a in links2:
                if re.search(r'illust_id=(\d+)', a['href']) is not None:
                    temp = str(a['href'])
                    break

        if temp is None:
            # changes on pixiv website to handle big image
            self.imageMode = "bigNew"

        else:
            temp_id = int(re.search(r'illust_id=(\d+)', temp).group(1))
            assert temp_id == self.imageId, "Invalid Id detected ==> %i != %i" % (temp_id, self.imageId)
            self.imageMode = re.search('mode=(big|manga|ugoira_view)', temp).group(1)

        # remove premium-introduction-modal so we can get caption from work-info
        # somehow selecting section doesn't works
        premium_introduction_modal = page.findAll('div', attrs={'id': 'premium-introduction-modal'})
        premium_introduction_modal.extend(page.findAll('div', attrs={'id': 'popular-search-trial-end-introduction-modal'}))
        for modal in premium_introduction_modal:
            if modal is not None:
                modal.extract()

        # meta_data = page.findAll('meta')
        # for meta in meta_data:
        #     if meta.has_key("property"):
        #         if "og:title" == meta["property"]:
        #             self.imageTitle = meta["content"].split("|")[0].strip()
        #         if "og:description" in meta["property"]:
        #             self.imageCaption = meta["content"]

        # new layout on 20160319
        temp_titles = page.findAll('h1', attrs={'class': 'title'})
        for tempTitle in temp_titles:
            if tempTitle is None or tempTitle.string is None:
                continue
            elif len(tempTitle.string) == 0:
                continue
            else:
                self.imageTitle = tempTitle.string
                break

        description_para = page.findAll("p", attrs={'class': PixivImage.__re_caption})
        for tempCaption in description_para:
            if tempCaption is None or tempCaption.text is None:
                continue
            elif len(tempCaption.text.strip()) == 0:
                continue
            else:
                self.imageCaption = ''
                for line in tempCaption.contents:
                    if str(line) == '<br />':
                        self.imageCaption += (os.linesep)
                    else:
                        self.imageCaption += (str(line))

        # stats
        view_count = page.find(attrs={'class': 'view-count'})
        if view_count is not None:
            self.jd_rtv = int(view_count.string)
        # Issue#182 fix
        rated_count = page.find(attrs={'class': 'rated-count'})
        if rated_count is not None:
            self.jd_rtc = int(rated_count.string)
        # deprecated since 11-April-2017
        # score_count = page.find(attrs={'class': 'score-count'})
        # if score_count is not None:
        #    self.jd_rtt = int(score_count.string)

        if description_para is not None and len(description_para) > 0:
            for para in description_para:
                links = para.findAll("a")
                if links is not None and len(links) > 0:
                    for link in links:
                        link_str = link["href"]
                        # "/jump.php?http%3A%2F%2Farsenixc.deviantart.com%2Fart%2FWatchmaker-house-567480110"
                        if link_str.startswith("/jump.php?"):
                            link_str = link_str[10:]
                            link_str = urllib.parse.unquote(link_str)
                        self.descriptionUrlList.append(link_str)

    def ParseWorksData(self, page):
        temp = page.find(attrs={'class': 'meta'}).findAll('li')
        # 07/22/2011 03:09|512×600|RETAS STUDIO
        # 07/26/2011 00:30|Manga 39P|ComicStudio 鉛筆 つけペン
        # 1/05/2011 07:09|723×1023|Photoshop SAI  [ R-18 ]
        # 2013年3月16日 06:44 | 800×1130 | Photoshop ComicStudio | R-18
        # 2013年12月14日 19:00 855×1133 PhotoshopSAI

        self.worksDate = PixivHelper.toUnicode(temp[0].string, encoding=sys.stdin.encoding)
        self.worksDateDateTime = PixivHelper.ParseDateTime(self.worksDate, self.dateFormat)

        self.worksResolution = str(temp[1].string).replace('×', 'x')
        toolsTemp = page.find(attrs={'class': 'meta'}).find(attrs={'class': 'tools'})
        if toolsTemp is not None and len(toolsTemp) > 0:
            tools = toolsTemp.findAll('li')
            for tool in tools:
                self.worksTools = self.worksTools + ' ' + str(tool.string)
            self.worksTools = self.worksTools.strip()

    def ParseTags(self, page):
        del self.imageTags[:]
        temp = page.find(attrs={'class': 'tags'})
        if temp is not None and len(temp) > 0:
            temp2 = temp.findAll('a')
            if temp2 is not None and len(temp2) > 0:
                for tag in temp2:
                    if 'class' in tag:
                        if tag['class'] == 'portal':
                            pass
                        elif tag['class'] == 'text' and tag.string is not None:
                            self.imageTags.append(str(tag.string))
                        elif tag['class'].startswith('text js-click-trackable-later'):
                            # Issue#343
                            # no translation for tags
                            if tag.string is not None:
                                self.imageTags.append(str(tag.string))
                            else:
                                # with translation
                                # print(tag.contents)
                                # print(unicode(tag.contents[0]))
                                self.imageTags.append(str(tag.contents[0]))
                        elif tag['class'] == 'text js-click-trackable':
                            # issue #200 fix
                            # need to split the tag 'incrediblycute <> なにこれかわいい'
                            # and take the 2nd tags
                            temp_tag = tag['data-click-action'].split('<>', 1)[1].strip()
                            self.imageTags.append(str(temp_tag))

    def PrintInfo(self):
        PixivHelper.safePrint('Image Info')
        PixivHelper.safePrint('img id: ' + str(self.imageId))
        PixivHelper.safePrint('title : ' + self.imageTitle)
        PixivHelper.safePrint('caption : ' + self.imageCaption)
        PixivHelper.safePrint('mode  : ' + self.imageMode)
        PixivHelper.safePrint('tags  :', newline=False)
        PixivHelper.safePrint(', '.join(self.imageTags))
        PixivHelper.safePrint('views : ' + str(self.jd_rtv))
        PixivHelper.safePrint('rating: ' + str(self.jd_rtc))
        # PixivHelper.safePrint('total : ' + str(self.jd_rtt))
        PixivHelper.safePrint('Date : ' + self.worksDate)
        PixivHelper.safePrint('Resolution : ' + self.worksResolution)
        PixivHelper.safePrint('Tools : ' + self.worksTools)
        return ""

    def ParseImages(self, page, mode=None, _br=None):
        if page is None:
            raise PixivException('No page given', errorCode=PixivException.NO_PAGE_GIVEN)
        if mode is None:
            mode = self.imageMode

        del self.imageUrls[:]
        if mode == 'big' or mode == 'bigNew':
            self.imageUrls.append(self.ParseBigImages(page, _br))
        elif mode == 'manga':
            self.imageUrls = self.CheckMangaType(page, _br)
        elif mode == 'ugoira_view':
            self.imageUrls.append(self.ParseUgoira(page))
        if len(self.imageUrls) == 0:
            raise PixivException('No images found for: ' + str(self.imageId), errorCode=PixivException.NO_IMAGES, htmlPage=page)
        return self.imageUrls

    def ParseBigImages(self, page, _br):
        self.imageCount = 1

        # Issue #224
        # work manga
        temp = page.find('a', attrs={'class': ' _work manga '})
        if temp is not None:
            if _br is None:
                import PixivBrowserFactory
                _br = PixivBrowserFactory.getExistingBrowser()

            expected_url = '/member_illust.php?mode=big&illust_id=' + str(self.imageId)
            try:
                href = _br.fixUrl(expected_url)
                print("Fetching big image page:", href)
                bigPage = _br.getPixivPage(url=href,
                                           referer="https://www.pixiv.net/member_illust.php?mode=medium&illust_id=" + str(self.imageId))
                bigImg = bigPage.find('img')
                imgUrl = bigImg["src"]
                # http://i2.pixiv.net/img-original/img/2013/12/27/01/51/37/40538869_p7.jpg
                print("Found: ", imgUrl)
                bigImg.decompose()
                bigPage.decompose()
                del bigImg
                del bigPage
                return imgUrl
            except Exception as ex:
                print(ex)

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
                    if line.startswith("pixiv.context.ugokuIllustFullscreenData"):
                        line = line.split("=", 2)[1].strip()
                        js = json.loads(line)
                        self.ugoira_data = line
                        self.imageCount = 1
                        return js["src"]

    def CheckMangaType(self, page, _br):
        # _book-viewer
        twopage_format = page.find("html", attrs={'class': re.compile(r".*\b_book-viewer\b.*")})
        if twopage_format is not None and len(twopage_format) > 0:
            # new format
            # print("2-page manga viewer mode")
            return self.ParseMangaImagesScript(page)
        else:
            # standard format
            return self.ParseMangaImagesNew(page, _br)

    def ParseMangaImagesScript(self, page):
        urls = []
        scripts = page.findAll('script')
        pattern = re.compile(r"pixiv.context.originalImages\[\d+\].*(http.*)\"")
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
        # mangaSection = page.find("section", attrs={'class': 'manga'})
        # links = mangaSection.findAll('a')
        # pattern /member_illust.php?mode=manga_big&illust_id=46279245&page=0
        if _br is None:
            import PixivBrowserFactory
            _br = PixivBrowserFactory.getExistingBrowser()

        total = page.find("span", attrs={'class': 'total'})
        if total is not None:
            self.imageCount = int(total.string)

        for currPage in range(0, self.imageCount):
            expected_url = '/member_illust.php?mode=manga_big&illust_id=' + str(self.imageId) + '&page=' + str(currPage)
            try:
                href = _br.fixUrl(expected_url)
                msg = "\rFetching big image page: {0}".format(href)
                print("{0:79}".format(msg), end=' ')
                bigPage = _br.getPixivPage(url=href,
                                           referer="https://www.pixiv.net/member_illust.php?mode=manga&illust_id=" + str(
                                               self.imageId))

                bigImg = bigPage.find('img')
                imgUrl = bigImg["src"]
                # http://i2.pixiv.net/img-original/img/2013/12/27/01/51/37/40538869_p7.jpg
                msg = "\rFound: {0}".format(imgUrl)
                print("{0:79}".format(msg), end=' ')
                urls.append(imgUrl)
                bigImg.decompose()
                bigPage.decompose()
                del bigImg
                del bigPage
            except Exception as ex:
                print(ex)
        print("\r{0:120}".format("Manga pages parsed."))

        return urls

    def ParseBookmarkDetails(self, page):
        if page is None:
            raise PixivException('No page given', errorCode=PixivException.NO_PAGE_GIVEN)
        try:
            countUl = page.findAll('ul', attrs={'class': 'count-list'})
            if countUl is not None and len(countUl) > 0:
                countA = countUl[0].findAll('a')
                if countA is not None and len(countA) > 0:
                    for a in countA:
                        if "bookmark-count" in a["class"]:
                            self.bookmark_count = int(a.text)
                        elif "image-response-count" in a["class"]:
                            self.image_response_count = int(a.text)
                    return

            # no bookmark count
            self.bookmark_count = 0
            self.image_response_count = 0
        except BaseException:
            PixivHelper.GetLogger().exception("Cannot parse bookmark count for: " + str(self.imageId))

    def WriteInfo(self, filename):
        info = None
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)

            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".txt", 'wb', encoding='utf-8')
            PixivHelper.GetLogger().exception(
                "Error when saving image info: " + filename + ", file is saved to: " + str(self.imageId) + ".txt")

        info.write("ArtistID      = " + str(self.artist.artistId) + "\r\n")
        info.write("ArtistName    = " + self.artist.artistName + "\r\n")
        info.write("ImageID       = " + str(self.imageId) + "\r\n")
        info.write("Title         = " + self.imageTitle + "\r\n")
        info.write("Caption       = " + self.imageCaption + "\r\n")
        info.write("Tags          = " + ", ".join(self.imageTags) + "\r\n")
        info.write("Image Mode    = " + self.imageMode + "\r\n")
        info.write("Pages         = " + str(self.imageCount) + "\r\n")
        info.write("Date          = " + self.worksDate + "\r\n")
        info.write("Resolution    = " + self.worksResolution + "\r\n")
        info.write("Tools         = " + self.worksTools + "\r\n")
        info.write("BookmarkCount = " + str(self.bookmark_count) + "\r\n")
        info.write(
            "Link          = https://www.pixiv.net/member_illust.php?mode=medium&illust_id=" + str(self.imageId) + "\r\n")
        info.write("Ugoira Data   = " + str(self.ugoira_data) + "\r\n")
        if len(self.descriptionUrlList) > 0:
            info.write("Urls          =\r\n")
            for link in self.descriptionUrlList:
                info.write(" - " + link + "\r\n")
        info.close()

    def WriteJSON(self, filename):
        info = None
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)
            info = codecs.open(filename, 'w', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".json", 'w', encoding='utf-8')
            PixivHelper.GetLogger().exception("Error when saving image info: " + filename + ", file is saved to: " + str(self.imageId) + ".json")

        # Fix Issue #481
        jsonInfo = collections.OrderedDict()
        jsonInfo["Artist ID"] = self.artist.artistId
        jsonInfo["Artist Name"] = self.artist.artistName
        jsonInfo["Image ID"] = self.imageId
        jsonInfo["Title"] = self.imageTitle
        jsonInfo["Caption"] = self.imageCaption
        jsonInfo["Tags"] = self.imageTags
        jsonInfo["Image Mode"] = self.imageMode
        jsonInfo["Pages"] = self.imageCount
        jsonInfo["Date"] = self.worksDate
        jsonInfo["Resolution"] = self.worksResolution
        jsonInfo["Tools"] = self.worksTools
        jsonInfo["BookmarkCount"] = self.bookmark_count
        jsonInfo["Link"] = "https://www.pixiv.net/member_illust.php?mode=medium&illust_id=" + str(self.imageId)
        jsonInfo["Ugoira Data"] = self.ugoira_data
        if len(self.descriptionUrlList) > 0:
            jsonInfo["Urls"] = self.descriptionUrlList

        info.write(json.dumps(jsonInfo, ensure_ascii=False, indent=4))
        info.close()

    def WriteUgoiraData(self, filename):
        info = None
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)
            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".js", 'wb', encoding='utf-8')
            PixivHelper.GetLogger().exception(
                "Error when saving image info: " + filename + ", file is saved to: " + str(self.imageId) + ".js")
        info.write(str(self.ugoira_data))
        info.close()

    def CreateUgoira(self, filename):
        if len(self.ugoira_data) == 0:
            PixivHelper.GetLogger().exception("Missing ugoira animation info for image: " + str(self.imageId))

        zipTarget = filename[:-4] + ".ugoira"
        if os.path.exists(zipTarget):
            os.remove(zipTarget)

        shutil.copyfile(filename, zipTarget)
        zipSize = os.stat(filename).st_size
        jsStr = self.ugoira_data[:-1] + r',"zipSize":' + str(zipSize) + r'}'
        with zipfile.ZipFile(zipTarget, mode="a") as z:
            z.writestr("animation.json", jsStr)


class PixivListItem:
    '''Class for item in list.txt'''
    memberId = ""
    path = ""

    def __init__(self, memberId, path):
        self.memberId = int(memberId)
        self.path = path.strip()
        if self.path == r"N\A":
            self.path = ""

    def __repr__(self):
        return "(id:{0}, path:'{1}')".format(self.memberId, self.path)

    @staticmethod
    def parseList(filename, rootDir=None):
        '''read list.txt and return the list of PixivListItem'''
        l = list()

        if not os.path.exists(filename):
            raise PixivException("File doesn't exists or no permission to read: " + filename,
                                 errorCode=PixivException.FILE_NOT_EXISTS_OR_NO_WRITE_PERMISSION)

        reader = PixivHelper.OpenTextFile(filename)
        line_no = 1
        try:
            for line in reader:
                original_line = line
                # PixivHelper.safePrint("Processing: " + line)
                if line.startswith('#') or len(line) < 1:
                    continue
                if len(line.strip()) == 0:
                    continue
                line = PixivHelper.toUnicode(line)
                line = line.strip()
                items = line.split(None, 1)

                if items[0].startswith("http"):
                    # handle urls:
                    # http://www.pixiv.net/member_illust.php?id=<member_id>
                    # http://www.pixiv.net/member.php?id=<member_id>
                    parsed = urllib.parse.urlparse(items[0])
                    if parsed.path == "/member.php" or parsed.path == "/member_illust.php":
                        query_str = urllib.parse.parse_qs(parsed.query)
                        if 'id' in query_str:
                            member_id = int(query_str["id"][0])
                        else:
                            PixivHelper.print_and_log('error', "Cannot detect member id from url: " + items[0])
                            continue
                    else:
                        PixivHelper.print_and_log('error', "Unsupported url detected: " + items[0])
                        continue

                else:
                    # handle member id directly
                    member_id = int(items[0])

                path = ""
                if len(items) > 1:
                    path = items[1].strip()

                    path = path.replace('\"', '')
                    if rootDir is not None:
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

                list_item = PixivListItem(member_id, path)
                # PixivHelper.safePrint(u"- {0} ==> {1} ".format(member_id, path))
                l.append(list_item)
                line_no = line_no + 1
                original_line = ""
        except UnicodeDecodeError:
            PixivHelper.GetLogger().exception("PixivListItem.parseList(): Invalid value when parsing list")
            PixivHelper.print_and_log('error',
                                    'Invalid value: {0} at line {1}, try to save the list.txt in UTF-8.'.format(
                                        original_line, line_no))
        except BaseException:
            PixivHelper.GetLogger().exception("PixivListItem.parseList(): Invalid value when parsing list")
            PixivHelper.print_and_log('error', 'Invalid value: {0} at line {1}'.format(original_line, line_no))

        reader.close()
        return l


class PixivNewIllustBookmark:
    '''Class for parsing New Illust from Bookmarks'''
    imageList = None
    isLastPage = None
    haveImages = None

    def __init__(self, page):
        self.__ParseNewIllustBookmark(page)
        self.__CheckLastPage(page)
        self.haveImages = bool(len(self.imageList) > 0)

    def __ParseNewIllustBookmark(self, page):
        self.imageList = list()

        # Fix Issue#290
        jsBookmarkItem = page.find(id='js-mount-point-latest-following')
        if jsBookmarkItem is not None:
            js = jsBookmarkItem["data-items"]
            items = json.loads(js)
            for item in items:
                image_id = item["illustId"]
                # bookmarkCount = item["bookmarkCount"]
                # imageResponse = item["responseCount"]
                self.imageList.append(int(image_id))
        else:
            try:
                result = page.find(attrs={'class': '_image-items autopagerize_page_element'}).findAll('a')
                for r in result:
                    href = re.search(r'member_illust.php?.*illust_id=(\d+)', r['href'])
                    if href is not None:
                        href = int(href.group(1))
                        # fuck performance :D
                        if href not in self.imageList:
                            self.imageList.append(href)
            except BaseException:
                pass

        return self.imageList

    def __CheckLastPage(self, page):
        check = page.findAll('a', attrs={'class': '_button', 'rel': 'next'})
        if len(check) > 0:
            self.isLastPage = False
        else:
            self.isLastPage = True
        return self.isLastPage


class PixivBookmark:
    '''Class for parsing Bookmarks'''
    __re_imageULItemsClass = re.compile(r".*\b_image-items\b.*")

    @staticmethod
    def parseBookmark(page):
        '''Parse favorite artist page'''
        import PixivDBManager
        l = list()
        db = PixivDBManager.PixivDBManager()
        __re_member = re.compile(r'member\.php\?id=(\d*)')
        try:
            result = page.find(attrs={'class': 'members'}).findAll('a')

            # filter duplicated member_id
            d = collections.OrderedDict()
            for r in result:
                member_id = __re_member.findall(r['href'])
                if len(member_id) > 0:
                    d[member_id[0]] = member_id[0]
            result2 = list(d.keys())

            for r in result2:
                item = db.selectMemberByMemberId2(r)
                l.append(item)
        except BaseException:
            pass
        return l

    @staticmethod
    def parseImageBookmark(page):
        imageList = list()

        temp = page.find('ul', attrs={'class': PixivBookmark.__re_imageULItemsClass})
        temp = temp.findAll('a')
        if temp is None or len(temp) == 0:
            return imageList
        for item in temp:
            href = re.search(r'member_illust.php?.*illust_id=(\d+)', str(item))
            if href is not None:
                href = href.group(1)
                if not int(href) in imageList:
                    imageList.append(int(href))

        return imageList

    @staticmethod
    def exportList(l, filename):
        if not filename.endswith('.txt'):
            filename = filename + '.txt'
        writer = codecs.open(filename, 'wb', encoding='utf-8')
        writer.write('###Export date: ' + str(datetime.today()) + '###\n')
        for item in l:
            data = str(str(item.memberId))
            if len(item.path) > 0:
                data = data + str(' ' + item.path)
            writer.write(data)
            writer.write('\r\n')
        writer.write('###END-OF-FILE###')
        writer.close()


PixivTagsItem = collections.namedtuple('PixivTagsItem', ['imageId', 'bookmarkCount', 'imageResponse'])


class PixivTags:
    '''Class for parsing tags search page'''
    itemList = None
    haveImage = None
    isLastPage = None
    availableImages = 0
    __re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
    __re_imageItemClass = re.compile(r".*\bimage-item\b.*")
    query = ""
    memberId = 0

    def parseIgnoreSection(self, page, sectionName):
        ignore = list()
        showcases = page.findAll('section', attrs={'class': sectionName})
        for showcase in showcases:
            lis = showcase.findAll('li', attrs={'class': self.__re_imageItemClass})
            for li in lis:
                if str(li).find('member_illust.php?') > -1:
                    image_id = self.__re_illust.findall(li.find('a')['href'])[0]
                    ignore.append(image_id)
        return ignore

    def parseTags(self, page, query=""):
        '''parse tags search page and return the image list with bookmarkCount and imageResponse'''
        self.itemList = list()
        self.query = query

        ignore = list()
        # ignore showcase and popular-introduction
        # ignore.extend(self.parseIgnoreSection(page, 'showcase'))
        # ignore.extend(self.parseIgnoreSection(page, 'popular-introduction'))

        # new format for tag list, fix issue #252
        # fix issue #270, changed to search based on id only
        js_tags_item = page.find(id="js-mount-point-search-result-list")
        if js_tags_item is not None:
            js = js_tags_item["data-items"]
            items = json.loads(js)
            for item in items:
                image_id = item["illustId"]
                if image_id is not None:  # Fix #472 skip if no illustId
                    bookmarkCount = item["bookmarkCount"]
                    imageResponse = item["responseCount"]
                    self.itemList.append(PixivTagsItem(int(image_id), int(bookmarkCount), int(imageResponse)))

        else:
            search_result = page.find('section', attrs={'class': 'column-search-result'})
            # new parse for bookmark items
            items = search_result.findAll('li', attrs={'class': self.__re_imageItemClass})

            # possible bug related to #143
            if len(items) == 0:
                # showcase must be removed first
                showcase = page.find("section", attrs={'class': 'showcase'})
                if showcase is not None:
                    showcase.extract()
                search_result = page.find("ul", attrs={'class': '_image-items autopagerize_page_element'})
                if search_result is None or len(search_result) == 0:
                    return self.itemList
                items = search_result.findAll('li', attrs={'class': self.__re_imageItemClass})

            for item in items:
                if str(item).find('member_illust.php?') > -1:
                    image_id = self.__re_illust.findall(item.find('a')['href'])[0]
                    if not str(image_id).isdigit() or image_id in ignore:
                        continue

                    bookmarkCount = 0
                    imageResponse = 0
                    countList = item.find('ul', attrs={'class': 'count-list'})
                    if countList is not None:
                        countList = countList.findAll('li')
                        if len(countList) > 0:
                            for count in countList:
                                temp = count.find('a')
                                if 'bookmark-count' in temp['class']:
                                    bookmarkCount = temp.contents[1]
                                elif 'image-response-count' in temp['class']:
                                    imageResponse = temp.contents[1]
                    self.itemList.append(PixivTagsItem(int(image_id), int(bookmarkCount), int(imageResponse)))

        self.checkLastPage(page)
        self.availableImages = SharedParser.parseCountBadge(page)
        return self.itemList

    def parseMemberTags(self, page, memberId, query=""):
        '''parse member tags search page and return the image list'''
        self.itemList = list()
        self.memberId = memberId
        self.query = query

        linkList = page.findAll('a')
        for link in linkList:
            if 'href' in link:
                result = self.__re_illust.findall(link['href'])
                if len(result) > 0:
                    image_id = int(result[0])
                    self.itemList.append(PixivTagsItem(int(image_id), 0, 0))
        self.checkLastPage(page, fromMember=True)
        self.availableImages = SharedParser.parseCountBadge(page)
        return self.itemList

    def checkLastPage(self, page, fromMember=False):
        # Check if have image
        if len(self.itemList) > 0:
            self.haveImage = True
        else:
            self.haveImage = False

        # check if the last page
        check = page.findAll('i', attrs={'class': '_icon sprites-next-linked'})
        self.isLastPage = not bool(len(check) > 0)

        if fromMember:
            # check if the last page for member tags
            if self.isLastPage:
                check = page.findAll(name='a', attrs={'class': 'button', 'rel': 'next'})
                if len(check) > 0:
                    self.isLastPage = False

    def PrintInfo(self):
        PixivHelper.safePrint('Search Result')
        if self.memberId > 0:
            PixivHelper.safePrint('Member Id: {0}'.format(self.memberId))
        PixivHelper.safePrint('Query: {0}'.format(self.query))
        PixivHelper.safePrint('haveImage  : {0}'.format(self.haveImage))
        PixivHelper.safePrint('urls  : {0}'.format(len(self.itemList)))
        for item in self.itemList:
            print("\tImage Id: {0}\tFav Count:{1}".format(item.imageId, item.bookmarkCount))
        PixivHelper.safePrint('total : {0}'.format(self.availableImages))
        PixivHelper.safePrint('last? : {0}'.format(self.isLastPage))

    @staticmethod
    def parseTagsList(filename):
        '''read tags.txt and return the tags list'''
        l = list()

        if not os.path.exists(filename):
            raise PixivException("File doesn't exists or no permission to read: " + filename,
                                 PixivException.FILE_NOT_EXISTS_OR_NO_READ_PERMISSION)

        reader = PixivHelper.OpenTextFile(filename)
        for line in reader:
            if line.startswith('#') or len(line) < 1:
                continue
            line = line.strip()
            if len(line) > 0:
                l.append(PixivHelper.toUnicode(line))
        reader.close()
        return l


class PixivGroup:
    short_pattern = re.compile(r"https?://www.pixiv.net/member_illust.php\?mode=(.*)&illust_id=(\d+)")
    imageList = None
    externalImageList = None
    maxId = 0

    def __init__(self, jsonResponse):
        data = json.loads(jsonResponse.read())
        self.maxId = data["max_id"]
        self.imageList = list()
        self.externalImageList = list()

        for imageData in data["imageArticles"]:
            if "id" in imageData["detail"]:
                # hosted in pixiv
                imageId = imageData["detail"]["id"]
                self.imageList.append(imageId)
            elif "fullscale_url" in imageData["detail"]:
                # external images?
                fullscale_url = imageData["detail"]["fullscale_url"]
                member_id = PixivArtist()
                member_id.artistId = imageData["user_id"]
                if "user_name" in imageData:
                    member_id.artistName = imageData["user_name"]
                    member_id.artistAvatar = self.parseAvatar(imageData["img"])
                    member_id.artistToken = self.parseToken(imageData["img"])
                else:
                    # probably user is gone.
                    member_id.artistName = imageData["user_id"]
                    member_id.artistAvatar = ""
                    member_id.artistToken = ""

                image_data = PixivImage()
                image_data.artist = member_id
                image_data.originalArtist = member_id
                image_data.imageId = 0
                image_data.imageTitle = self.shortenPixivUrlInBody(imageData["body"])
                image_data.imageCaption = self.shortenPixivUrlInBody(imageData["body"])
                image_data.imageTags = []
                image_data.imageMode = ""
                image_data.imageUrls = [fullscale_url]
                image_data.worksDate = imageData["create_time"]
                image_data.worksResolution = str("")
                image_data.worksTools = str("")
                image_data.jd_rtv = 0
                image_data.jd_rtc = 0
                # image_data.jd_rtt = 0
                image_data.imageCount = 0
                image_data.fromBookmark = False
                image_data.worksDateDateTime = datetime.strptime(image_data.worksDate, '%Y-%m-%d %H:%M:%S')

                self.externalImageList.append(image_data)

    @staticmethod
    def parseAvatar(url):
        return url.replace("_s", "")

    @staticmethod
    def parseToken(url):
        token = url.split('/')[-2]
        if token != "Common":
            return token
        return None

    def shortenPixivUrlInBody(self, string):
        shortened = ""
        result = self.short_pattern.findall(string)
        if result is not None and len(result) > 0:
            if result[0][0] == 'medium':
                shortened = "Illust={0}".format(result[0][1])
            else:
                shortened = "Manga={0}".format(result[0][1])
        string = self.short_pattern.sub("", string).strip()
        string = string + " " + shortened
        return string


class SharedParser:
    @staticmethod
    def parseCountBadge(page):
        # parse image count from count-badge
        total_images = 0
        count_badge_span = page.find('span', attrs={'class': 'count-badge'})
        if count_badge_span is not None:
            temp_count = re.findall(r'\d+', count_badge_span.string)
            if temp_count:
                total_images = int(temp_count[0])
        return total_images
