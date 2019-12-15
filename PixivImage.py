# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import codecs
import collections
import json
import os
import re
import shutil
import urllib
import zipfile
from collections import OrderedDict
from datetime import datetime

import demjson
from bs4 import BeautifulSoup

import datetime_z
import PixivHelper
from PixivArtist import PixivArtist
from PixivException import PixivException


class PixivImage (object):
    '''Class for parsing image page, including manga page and big image.'''
    artist = None
    originalArtist = None
    imageId = 0
    imageTitle = ""
    imageCaption = ""
    imageTags = []
    imageMode = ""
    imageUrls = []
    worksDate = ""
    worksResolution = ""
    worksTools = ""
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
                parsed = BeautifulSoup(page, features="html5lib")
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
        parsed = BeautifulSoup(self.imageCaption, features="html5lib")
        links = parsed.findAll('a')
        if links is not None and len(links) > 0:
            for link in links:
                link_str = link["href"]
                # "/jump.php?http%3A%2F%2Farsenixc.deviantart.com%2Fart%2FWatchmaker-house-567480110"
                if link_str.startswith("/jump.php?"):
                    link_str = link_str[10:]
                    link_str = urllib.parse.unquote(link_str)
                self.descriptionUrlList.append(link_str)
        parsed.decompose()
        del parsed

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
        return PixivHelper.have_strings(page, errorMessages)

    def IsNeedPermission(self, page):
        errorMessages = ['この作品は.+さんのマイピクにのみ公開されています|この作品は、.+さんのマイピクにのみ公開されています',
                         'This work is viewable only for users who are in .+\'s My pixiv list',
                         'Only .+\'s My pixiv list can view this.',
                         '<section class="restricted-content">']
        return PixivHelper.have_strings(page, errorMessages)

    def IsDeleted(self, page):
        errorMessages = ['該当イラストは削除されたか、存在しないイラストIDです。|該当作品は削除されたか、存在しない作品IDです。',
                         'この作品は削除されました。',
                         'The following work is either deleted, or the ID does not exist.',
                         'This work was deleted.',
                         'Work has been deleted or the ID does not exist.']
        return PixivHelper.have_strings(page, errorMessages)

    def IsGuroDisabled(self, page):
        errorMessages = ['表示されるページには、18歳未満の方には不適切な表現内容が含まれています。',
                         'The page you are trying to access contains content that may be unsuitable for minors']
        return PixivHelper.have_strings(page, errorMessages)

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
                    if 'class' in tag:
                        if tag['class'] == 'portal':
                            pass
                        elif tag['class'] == 'text' and tag.string is not None:
                            self.imageTags.append(tag.string)
                        elif tag['class'].startswith('text js-click-trackable-later'):
                            # Issue#343
                            # no translation for tags
                            if tag.string is not None:
                                self.imageTags.append(tag.string)
                            else:
                                # with translation
                                # print(tag.contents)
                                # print(unicode(tag.contents[0]))
                                self.imageTags.append(tag.contents[0])
                        elif tag['class'] == 'text js-click-trackable':
                            # issue #200 fix
                            # need to split the tag 'incrediblycute <> なにこれかわいい'
                            # and take the 2nd tags
                            temp_tag = tag['data-click-action'].split('<>', 1)[1].strip()
                            self.imageTags.append(temp_tag)

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
            PixivHelper.get_logger().exception("Cannot parse bookmark count for: %d", self.imageId)

    def WriteInfo(self, filename):
        info = None
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)

            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".txt", 'wb', encoding='utf-8')
            PixivHelper.get_logger().exception("Error when saving image info: %s, file is saved to: %d.txt", filename, self.imageId)

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
            PixivHelper.get_logger().exception("Error when saving image info: %s, file is saved to: %s.json", filename, self.imageId)

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
            PixivHelper.get_logger().exception("Error when saving image info: %s, file is saved to: %d.js", filename, self.imageId)
        info.write(str(self.ugoira_data))
        info.close()

    def CreateUgoira(self, filename):
        if len(self.ugoira_data) == 0:
            PixivHelper.get_logger().exception("Missing ugoira animation info for image: %d", self.imageId)

        zipTarget = filename[:-4] + ".ugoira"
        if os.path.exists(zipTarget):
            os.remove(zipTarget)

        shutil.copyfile(filename, zipTarget)
        zipSize = os.stat(filename).st_size
        jsStr = self.ugoira_data[:-1] + r',"zipSize":' + str(zipSize) + r'}'
        with zipfile.ZipFile(zipTarget, mode="a") as z:
            z.writestr("animation.json", jsStr)


def parseJs(page):
    parsed = BeautifulSoup(page, features="html5lib")
    jss = parsed.find('meta', attrs={'id': 'meta-preload-data'})

    # cleanup
    parsed.decompose()
    del parsed

    if jss is None or len(jss["content"]) == 0:
        return None  # Possibly error page

    payload = demjson.decode(jss["content"])
    return payload
