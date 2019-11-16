# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302
from __future__ import print_function

import os
import re
import shutil
import zipfile
import codecs
import collections
import urlparse
import datetime_z
import urllib
from collections import OrderedDict
from datetime import datetime
import json

import demjson
from BeautifulSoup import BeautifulSoup

import PixivHelper
from PixivException import PixivException


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
    offset = None
    limit = None
    reference_image_id = 0

    def __init__(self, mid=0, page=None, fromImage=False, offset=None, limit=None):
        self.offset = offset
        self.limit = limit
        self.artistId = mid

        if page is not None:
            payload = None
            # detect if image count != 0
            if not fromImage:
                payload = demjson.decode(page)
                if payload["error"]:
                    raise PixivException(payload["message"], errorCode=PixivException.OTHER_MEMBER_ERROR, htmlPage=page)
                if payload["body"] is None:
                    raise PixivException("Missing body content, possible artist id doesn't exists.", errorCode=PixivException.USER_ID_NOT_EXISTS, htmlPage=page)
                self.ParseImages(payload["body"])
            else:
                payload = parseJs(page)
                self.isLastPage = True
                self.haveImages = True

            # parse artist info
            self.ParseInfo(payload, fromImage)

    def ParseInfo(self, page, fromImage=False, bookmark=False):
        self.artistId = 0
        self.artistAvatar = "no_profile"
        self.artistToken = "self"
        self.artistName = "self"
        self.artistBackground = "no_background"

        if page is not None:
            if fromImage:
                self.ParseInfoFromImage(page)
            else:
                # used in PixivBrowserFactory.getMemberInfoWhitecube()

                # webrpc method
                if page.has_key("body") and page["body"].has_key("illust") and page["body"]["illust"]:
                    root = page["body"]["illust"]
                    self.artistId = root["illust_user_id"]
                    self.artistToken = root["user_account"]
                    self.artistName = root["user_name"]
                elif page.has_key("body") and page["body"].has_key("novel") and page["body"]["novel"]:
                    root = page["body"]["novel"]
                    self.artistId = root["user_id"]
                    self.artistToken = root["user_account"]
                    self.artistName = root["user_name"]

                # https://app-api.pixiv.net/v1/user/detail?user_id=1039353
                data = None
                if page.has_key("user"):
                    data = page
                elif page.has_key("illusts") and len(page["illusts"]) > 0:
                    data = page["illusts"][0]

                if data is not None:
                    self.artistId = data["user"]["id"]
                    self.artistToken = data["user"]["account"]
                    self.artistName = data["user"]["name"]

                    avatar_data = data["user"]["profile_image_urls"]
                    if avatar_data is not None and avatar_data.has_key("medium"):
                        self.artistAvatar = avatar_data["medium"].replace("_170", "")

                if page.has_key("profile") and self.totalImages == 0:
                    if bookmark:
                        self.totalImages = int(page["profile"]["total_illust_bookmarks_public"])
                    else:
                        self.totalImages = int(page["profile"]["total_illusts"]) + int(page["profile"]["total_manga"])

    def ParseInfoFromImage(self, page):
        key = list(page["user"].keys())[0]
        root = page["user"][key]

        self.artistId = root["userId"]
        self.artistAvatar = root["image"].replace("_50", "").replace("_170", "")
        self.artistName = root["name"]

        if root["background"] is not None:
            self.artistBackground = root["background"]["url"]

        # Issue 388 user token is stored in image
        illusts = page["illust"]
        for il in illusts:
            if illusts[il]["userAccount"]:
                self.artistToken = illusts[il]["userAccount"]
                break

    def ParseBackground(self, payload):
        self.artistBackground = "no_background"

        # https://www.pixiv.net/ajax/user/8021957
        if payload.has_key("body"):
            root = payload["body"]
            self.artistId = root["userId"]
            self.artistName = root["name"]
            if root.has_key("imageBig") and root["imageBig"] is not None:
                self.artistAvatar = payload["body"]["imageBig"].replace("_50", "").replace("_170", "")
            elif root.has_key("image") and root["image"] is not None:
                self.artistAvatar = root["image"].replace("_50", "").replace("_170", "")

            # https://www.pixiv.net/ajax/user/1893126
            if root.has_key("background") and root["background"] is not None:
                self.artistBackground = root["background"]["url"]

    def ParseImages(self, payload):
        self.imageList = list()

        if payload.has_key("works"):  # filter by tags
            for image in payload["works"]:
                self.imageList.append(image["id"])
            self.totalImages = int(payload["total"])

            if len(self.imageList) > 0:
                self.haveImages = True

            if len(self.imageList) + self.offset == self.totalImages:
                self.isLastPage = True
            else:
                self.isLastPage = False

            return
        else:
            if payload.has_key("illusts"):  # all illusts
                for image in payload["illusts"]:
                    self.imageList.append(image)
            if payload.has_key("manga"):  # all manga
                for image in payload["manga"]:
                    self.imageList.append(image)
            self.imageList = sorted(self.imageList, reverse=True, key=int)
            self.totalImages = len(self.imageList)
            # print("{0} {1} {2}".format(self.offset, self.limit, self.totalImages))

            if self.offset + self.limit >= self.totalImages:
                self.isLastPage = True
            else:
                self.isLastPage = False

            if len(self.imageList) > 0:
                self.haveImages = True

    # older function
    # def ParseToken(self, page, fromImage=False):
    #     try:
    #         # get the token from stacc feed
    #         # tab_feeds = page.findAll('a', attrs={'class': 'tab-feed'})
    #         tab_feeds = page.findAll(href=re.compile('/stacc/[^/?]*$'))
    #         if tab_feeds is not None and len(tab_feeds) > 0:
    #             for a in tab_feeds:
    #                 if str(a["href"]).find("stacc/") > 0:
    #                     self.artistToken = a["href"].split("/")[-1]
    #                     return self.artistToken
    #         # no token, possibly self page from manage works.
    #         # https://www.pixiv.net/manage/illusts/
    #         self.artistToken = "self"
    #         return self.artistToken

    #     except BaseException:
    #         raise PixivException('Cannot parse artist token, possibly different image structure.',
    #                              errorCode=PixivException.PARSE_TOKEN_DIFFERENT_IMAGE_STRUCTURE, htmlPage=page)

    # def IsUserNotExist(self, page):
    #     errorMessages = ['該当ユーザーは既に退会したか、存在しないユーザーIDです',
    #                      'The user has either left pixiv, or the user ID does not exist.',
    #                      'User has left pixiv or the user ID does not exist.',
    #                      '該当作品は削除されたか、存在しない作品IDです。',
    #                      'The following work is either deleted, or the ID does not exist.',
    #                      'User has left pixiv or the user ID does not exist.']
    #     return PixivHelper.HaveStrings(page, errorMessages)

    # def IsUserSuspended(self, page):
    #     errorMessages = ['該当ユーザーのアカウントは停止されています。',
    #                      'This user account has been suspended.']
    #     return PixivHelper.HaveStrings(page, errorMessages)

    # def IsErrorExist(self, page):
    #     check = page.findAll('span', attrs={'class': 'error'})
    #     if len(check) > 0:
    #         check2 = check[0].findAll('strong')
    #         if len(check2) > 0:
    #             return check2[0].renderContents()
    #         return check[0].renderContents()
    #     return None

    # def IsServerErrorExist(self, page):
    #     check = page.findAll('div', attrs={'class': 'errorArea'})
    #     if len(check) > 0:
    #         check2 = check[0].findAll('h2')
    #         if len(check2) > 0:
    #             return check2[0].renderContents()
    #         return check[0].renderContents()
    #     return None

    # def CheckLastPage(self, page):
    #     check = page.findAll('a', attrs={'class': '_button', 'rel': 'next'})
    #     if len(check) > 0:
    #         self.isLastPage = False
    #     else:
    #         self.isLastPage = True
    #     return self.isLastPage

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
    worksDate = unicode("")
    worksResolution = unicode("")
    worksTools = unicode("")
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
    _tzInfo = None

    def __init__(self, iid=0, page=None, parent=None, fromBookmark=False,
                 bookmark_count=-1, image_response_count=-1, dateFormat=None, tzInfo=None):
        self.artist = parent
        self.fromBookmark = fromBookmark
        self.bookmark_count = bookmark_count
        self.imageId = iid
        self.imageUrls = []
        self.dateFormat = dateFormat
        self.descriptionUrlList = []
        self._tzInfo = tzInfo

        if page is not None:

            # Issue #556
            payload = parseJs(page)

            # check error
            if payload is None:
                parsed = BeautifulSoup(page.decode("utf8"))
                if self.IsNotLoggedIn(parsed):
                    raise PixivException('Not Logged In!', errorCode=PixivException.NOT_LOGGED_IN, htmlPage=page)
                if self.IsNeedPermission(parsed):
                    raise PixivException('Not in MyPick List, Need Permission!', errorCode=PixivException.NOT_IN_MYPICK, htmlPage=page)
                if self.IsNeedAppropriateLevel(parsed):
                    raise PixivException('Public works can not be viewed by the appropriate level!',
                                         errorCode=PixivException.NO_APPROPRIATE_LEVEL, htmlPage=page)
                if self.IsDeleted(parsed):
                    raise PixivException('Image not found/already deleted!', errorCode=PixivException.IMAGE_DELETED, htmlPage=page)
                if self.IsGuroDisabled(parsed):
                    raise PixivException('Image is disabled for under 18, check your setting page (R-18/R-18G)!',
                                         errorCode=PixivException.R_18_DISABLED, htmlPage=page)
                # detect if there is any other error
                errorMessage = self.IsErrorExist(parsed)
                if errorMessage is not None:
                    raise PixivException('Image Error: ' + str(errorMessage), errorCode=PixivException.UNKNOWN_IMAGE_ERROR, htmlPage=page)
                # detect if there is server error
                errorMessage = self.IsServerErrorExist(parsed)
                if errorMessage is not None:
                    raise PixivException('Image Error: ' + str(errorMessage), errorCode=PixivException.SERVER_ERROR, htmlPage=page)
                parsed.decompose()
                del parsed

            # parse artist information
            if parent is None:
                temp_artist_id = list(payload["user"].keys())[0]
                self.artist = PixivArtist(temp_artist_id, page, fromImage=True)

            if fromBookmark and self.originalArtist is None:
                assert(self.artist is not None)
                self.originalArtist = PixivArtist(page=page, fromImage=True)
                print("From Artist Bookmark: {0}".format(self.artist.artistId))
                print("Original Artist: {0}".format(self.originalArtist.artistId))
            else:
                self.originalArtist = self.artist

            # parse image
            self.ParseInfo(payload)

    def ParseInfo(self, page):
        key = list(page["illust"].keys())[0]
        assert(str(key) == str(self.imageId))
        root = page["illust"][key]

        self.imageUrls = list()

        self.imageCount = int(root["pageCount"])
        temp_url = root["urls"]["original"]
        if self.imageCount == 1:
            if temp_url.find("ugoira") > 0:
                self.imageMode = "ugoira_view"
                # https://i.pximg.net/img-zip-ugoira/img/2018/04/22/00/01/06/68339821_ugoira600x600.zip 1920x1080
                # https://i.pximg.net/img-original/img/2018/04/22/00/01/06/68339821_ugoira0.jpg
                # https://i.pximg.net/img-original/img/2018/04/22/00/01/06/68339821_ugoira0.png
                # Fix Issue #372
                temp_url = temp_url.replace("/img-original/", "/img-zip-ugoira/")
                temp_url = temp_url.split("_ugoira0")[0]
                temp_url = temp_url + "_ugoira1920x1080.zip"
                self.imageUrls.append(temp_url)
                # self.ParseUgoira(page)
            else:
                self.imageMode = "big"
                self.imageUrls.append(temp_url)
        elif self.imageCount > 1:
            self.imageMode = "manga"
            for i in range(0, self.imageCount):
                url = temp_url.replace("_p0", "_p{0}".format(i))
                self.imageUrls.append(url)

        # title/caption
        self.imageTitle = root["illustTitle"]
        self.imageCaption = root["illustComment"]

        # view count
        self.jd_rtv = root["viewCount"]
        # like count
        self.jd_rtc = root["likeCount"]
        # not available anymore
        self.jd_rtt = self.jd_rtc

        # tags
        self.imageTags = list()
        tags = root["tags"]
        if tags is not None:
            tags = root["tags"]["tags"]
            for tag in tags:
                self.imageTags.append(tag["tag"])

        # datetime, in utc
        # "createDate" : "2018-06-08T15:00:04+00:00",
        self.worksDateDateTime = datetime_z.parse_datetime(str(root["createDate"]))
        # Issue #420
        if self._tzInfo is not None:
            self.worksDateDateTime = self.worksDateDateTime.astimezone(self._tzInfo)

        tempDateFormat = self.dateFormat or "%m/%d/%y %H:%M"  # 2/27/2018 12:31
        self.worksDate = self.worksDateDateTime.strftime(tempDateFormat)

        # resolution
        self.worksResolution = "{0}x{1}".format(root["width"], root["height"])
        if self.imageCount > 1:
            self.worksResolution = "Multiple images: {0}P".format(self.imageCount)

        # tools = No more tool information
        self.worksTools = ""

        self.bookmark_count = root["bookmarkCount"]
        self.image_response_count = root["responseCount"]

        # Issue 421
        parsed = BeautifulSoup(self.imageCaption)
        links = parsed.findAll('a')
        if links is not None and len(links) > 0:
            for link in links:
                link_str = link["href"]
                # "/jump.php?http%3A%2F%2Farsenixc.deviantart.com%2Fart%2FWatchmaker-house-567480110"
                if link_str.startswith("/jump.php?"):
                    link_str = link_str[10:]
                    link_str = urllib.unquote(link_str)
                self.descriptionUrlList.append(link_str)

    def ParseImages(self, page, mode=None, _br=None):
        pass

    def ParseUgoira(self, page):
        # preserve the order
        js = json.loads(page, object_pairs_hook=OrderedDict)
        self.imageCount = 1
        js = js["body"]

        # convert to full screen url
        # ugoira600x600.zip ==> ugoira1920x1080.zip
        # js["src_low"] = js["src"]
        js["src"] = js["src"].replace("ugoira600x600.zip", "ugoira1920x1080.zip")

        # need to be minified
        self.ugoira_data = json.dumps(js, separators=(',', ':'))  # ).replace("/", r"\/")

        assert(len(self.ugoira_data) > 0)
        return js["src"]

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

    def ParseTags(self, page):
        del self.imageTags[:]
        temp = page.find(attrs={'class': 'tags'})
        if temp is not None and len(temp) > 0:
            temp2 = temp.findAll('a')
            if temp2 is not None and len(temp2) > 0:
                for tag in temp2:
                    if tag.has_key('class'):
                        if tag['class'] == 'portal':
                            pass
                        elif tag['class'] == 'text' and tag.string is not None:
                            self.imageTags.append(unicode(tag.string))
                        elif tag['class'].startswith('text js-click-trackable-later'):
                            # Issue#343
                            # no translation for tags
                            if tag.string is not None:
                                self.imageTags.append(unicode(tag.string))
                            else:
                                # with translation
                                # print(tag.contents)
                                # print(unicode(tag.contents[0]))
                                self.imageTags.append(unicode(tag.contents[0]))
                        elif tag['class'] == 'text js-click-trackable':
                            # issue #200 fix
                            # need to split the tag 'incrediblycute <> なにこれかわいい'
                            # and take the 2nd tags
                            temp_tag = tag['data-click-action'].split('<>', 1)[1].strip()
                            self.imageTags.append(unicode(temp_tag))

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
            PixivHelper.GetLogger().exception("Cannot parse bookmark count for: %d", self.imageId)

    def WriteInfo(self, filename):
        info = None
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)

            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".txt", 'wb', encoding='utf-8')
            PixivHelper.GetLogger().exception("Error when saving image info: %s, file is saved to: %d.txt", filename, self.imageId)

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
        info.write("Link          = https://www.pixiv.net/en/artworks/{0}\r\n".format(self.imageId))
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
            PixivHelper.GetLogger().exception("Error when saving image info: %s, file is saved to: %s.json", filename, self.imageId)

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
        jsonInfo["Link"] = "https://www.pixiv.net/en/artworks/{0}".format(self.imageId)
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
            PixivHelper.GetLogger().exception("Error when saving image info: %s, file is saved to: %d.js", filename, self.imageId)
        info.write(str(self.ugoira_data))
        info.close()

    def CreateUgoira(self, filename):
        if len(self.ugoira_data) == 0:
            PixivHelper.GetLogger().exception("Missing ugoira animation info for image: %d", self.imageId)

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
                    parsed = urlparse.urlparse(items[0])
                    if parsed.path == "/member.php" or parsed.path == "/member_illust.php":
                        query_str = urlparse.parse_qs(parsed.query)
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
        writer.write(u'###Export date: ' + str(datetime.today()) + '###\n')
        for item in l:
            data = unicode(str(item.memberId))
            if len(item.path) > 0:
                data = data + unicode(' ' + item.path)
            writer.write(data)
            writer.write(u'\r\n')
        writer.write('###END-OF-FILE###')
        writer.close()


class PixivTagsItem:
    imageId = 0
    bookmarkCount = 0
    imageResponse = 0

    def __init__(self, image_id, bookmark_count, image_response_count):
        self.imageId = image_id
        self.bookmarkCount = bookmark_count
        self.imageResponse = image_response_count


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

    def parseMemberTags(self, artist, memberId, query=""):
        '''process artist result and return the image list'''
        self.itemList = list()
        self.memberId = memberId
        self.query = query
        self.haveImage = artist.haveImages
        self.isLastPage = artist.isLastPage
        for image in artist.imageList:
            self.itemList.append(PixivTagsItem(int(image), 0, 0))

    def parseTags(self, page, query="", curr_page=1):
        payload = json.loads(page)
        self.query = query

        # check error
        if payload["error"]:
            raise PixivException('Image Error: ' + payload["message"], errorCode=PixivException.SERVER_ERROR)

        # parse images information
        self.itemList = list()
        ad_container_count = 0
        for item in payload["body"]["illustManga"]["data"]:
            if item["isAdContainer"]:
                ad_container_count = ad_container_count + 1
                continue

            image_id = item["id"]
            # like count not available anymore, need to call separate request...
            bookmarkCount = 0
            imageResponse = 0
            tag_item = PixivTagsItem(int(image_id), int(bookmarkCount), int(imageResponse))
            self.itemList.append(tag_item)

        self.haveImage = False
        if len(self.itemList) > 0:
            self.haveImage = True

        # search page info
        self.availableImages = int(payload["body"]["illustManga"]["total"])
        # assuming there are only 47 image (1 is marked as ad)
        # if self.availableImages > 47 * curr_page:
        # assume it always return 6 images, including the advert
        if len(self.itemList) + ad_container_count == 60:
            self.isLastPage = False
        else:
            self.isLastPage = True
        return self.itemList

    # def checkLastPage(self, page, fromMember=False):
    #     # Check if have image
    #     if len(self.itemList) > 0:
    #         self.haveImage = True
    #     else:
    #         self.haveImage = False

    #     # check if the last page
    #     check = page.findAll('i', attrs={'class': '_icon sprites-next-linked'})
    #     self.isLastPage = not bool(len(check) > 0)

    #     if fromMember:
    #         # check if the last page for member tags
    #         if self.isLastPage:
    #             check = page.findAll(name='a', attrs={'class': 'button', 'rel': 'next'})
    #             if len(check) > 0:
    #                 self.isLastPage = False

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
                image_data.worksResolution = unicode("")
                image_data.worksTools = unicode("")
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
            if temp_count > 0:
                total_images = int(temp_count[0])
        return total_images


def parseJs(page):
    parsed = BeautifulSoup(page.decode("utf8"))
    jss = parsed.find('meta', attrs={'id': 'meta-preload-data'})

    # cleanup
    parsed.decompose()
    del parsed

    if jss is None or len(jss["content"]) == 0:
        return None  # Possibly error page

    payload = demjson.decode(jss["content"])
    return payload
