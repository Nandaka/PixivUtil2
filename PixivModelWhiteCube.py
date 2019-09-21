# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302


import json
import re
import urllib.request, urllib.parse, urllib.error
from collections import OrderedDict

import demjson
from bs4 import BeautifulSoup

import datetime_z
import PixivModel
from PixivException import PixivException

re_payload = re.compile(r"(\{token.*\})\);")


class PixivArtist(PixivModel.PixivArtist):
    offset = None
    limit = None
    reference_image_id = 0

    def __init__(self, mid=0, page=None, fromImage=False, offset=None, limit=None):
        self.offset = offset
        self.limit = limit
        self.artistId = mid

        if page is not None:
            payload = parseJs(page)

            # detect if image count != 0
            if not fromImage:
                payload = demjson.decode(page)
                if payload["error"]:
                    raise PixivException(payload["message"], errorCode=PixivException.OTHER_MEMBER_ERROR, htmlPage=page)
                if payload["body"] is None:
                    raise PixivException("Missing body content, possible artist id doesn't exists.", errorCode=PixivException.USER_ID_NOT_EXISTS, htmlPage=page)
                self.ParseImages(payload["body"])
            else:
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
                if "body" in page and "illust" in page["body"] and page["body"]["illust"]:
                    root = page["body"]["illust"]
                    self.artistId = root["illust_user_id"]
                    self.artistToken = root["user_account"]
                    self.artistName = root["user_name"]
                elif "body" in page and "novel" in page["body"] and page["body"]["novel"]:
                    root = page["body"]["novel"]
                    self.artistId = root["user_id"]
                    self.artistToken = root["user_account"]
                    self.artistName = root["user_name"]

                # https://app-api.pixiv.net/v1/user/detail?user_id=1039353
                data = None
                if "user" in page:
                    data = page
                elif "illusts" in page and len(page["illusts"]) > 0:
                    data = page["illusts"][0]

                if data is not None:
                    self.artistId = data["user"]["id"]
                    self.artistToken = data["user"]["account"]
                    self.artistName = data["user"]["name"]

                    avatar_data = data["user"]["profile_image_urls"]
                    if avatar_data is not None and "medium" in avatar_data:
                        self.artistAvatar = avatar_data["medium"].replace("_170", "")

                if "profile" in page and self.totalImages == 0:
                    if bookmark:
                        self.totalImages = int(page["profile"]["total_illust_bookmarks_public"])
                    else:
                        self.totalImages = int(page["profile"]["total_illusts"]) + int(page["profile"]["total_manga"])

    def ParseInfoFromImage(self, page):
        key = list(page["preload"]["user"].keys())[0]
        root = page["preload"]["user"][key]

        self.artistId = root["userId"]
        self.artistAvatar = root["image"].replace("_50", "").replace("_170", "")
        self.artistName = root["name"]

        if root["background"] is not None:
            self.artistBackground = root["background"]["url"]

        # Issue 388 user token is stored in image
        illusts = page["preload"]["illust"]
        for il in illusts:
            if illusts[il]["userAccount"]:
                self.artistToken = illusts[il]["userAccount"]
                break

    def ParseBackground(self, payload):
        self.artistBackground = "no_background"

        # https://www.pixiv.net/ajax/user/8021957
        if "body" in payload:
            root = payload["body"]
            self.artistId = root["userId"]
            self.artistName = root["name"]
            if "imageBig" in root and root["imageBig"] is not None:
                self.artistAvatar = payload["body"]["imageBig"].replace("_50", "").replace("_170", "")
            elif "image" in root and root["image"] is not None:
                self.artistAvatar = root["image"].replace("_50", "").replace("_170", "")

            # https://www.pixiv.net/ajax/user/1893126
            if "background" in root and root["background"] is not None:
                self.artistBackground = root["background"]["url"]

    def ParseImages(self, payload):
        self.imageList = list()

        if "works" in payload:  # filter by tags
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
            if "illusts" in payload:  # all illusts
                for image in payload["illusts"]:
                    self.imageList.append(image)
            if "manga" in payload:  # all manga
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


class PixivImage(PixivModel.PixivImage):
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
            payload = parseJs(page)

            # check error
            if payload is None:
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
                    raise PixivException('Image Error: ' + str(errorMessage), errorCode=PixivException.UNKNOWN_IMAGE_ERROR, htmlPage=page)
                # detect if there is server error
                errorMessage = self.IsServerErrorExist(page)
                if errorMessage is not None:
                    raise PixivException('Image Error: ' + str(errorMessage), errorCode=PixivException.SERVER_ERROR, htmlPage=page)

            # parse artist information
            if parent is None:
                temp_artist_id = list(payload["preload"]["user"].keys())[0]
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
        key = list(page["preload"]["illust"].keys())[0]
        assert(str(key) == str(self.imageId))
        root = page["preload"]["illust"][key]

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
        parsed = BeautifulSoup(self.imageCaption, features='lxml')
        links = parsed.findAll('a')
        if links is not None and len(links) > 0:
            for link in links:
                link_str = link["href"]
                # "/jump.php?http%3A%2F%2Farsenixc.deviantart.com%2Fart%2FWatchmaker-house-567480110"
                if link_str.startswith("/jump.php?"):
                    link_str = link_str[10:]
                    link_str = urllib.parse.unquote(link_str)
                self.descriptionUrlList.append(link_str)

    def ParseImages(self, page, mode=None, _br=None):
        pass

    def ParseUgoira(self, page):
        # preserve the order
        js = json.loads(page, object_pairs_hook=OrderedDict)
        self.imageCount = 1
        js = js["body"]

##        # modify the structure to old version
##        temp = js["frames"]
##        js["frames"] = list()
##        for key, value in temp.items():
##            js["frames"].append(value)

        # convert to full screen url
        # ugoira600x600.zip ==> ugoira1920x1080.zip
        # js["src_low"] = js["src"]
        js["src"] = js["src"].replace("ugoira600x600.zip", "ugoira1920x1080.zip")

        # need to be minified
        self.ugoira_data = json.dumps(js, separators=(',', ':'))  # ).replace("/", r"\/")

        assert(len(self.ugoira_data) > 0)
        return js["src"]


class PixivTags(PixivModel.PixivTags):
    __re_imageItemClass = re.compile(r"item-container _work-item-container.*")

    def parseMemberTags(self, artist, memberId, query=""):
        '''process artist result and return the image list'''
        self.itemList = list()
        self.memberId = memberId
        self.query = query
        self.haveImage = artist.haveImages
        self.isLastPage = artist.isLastPage
        for image in artist.imageList:
            self.itemList.append(PixivModel.PixivTagsItem(int(image), 0, 0))

    def parseTags(self, page, query=""):
        payload = json.loads(page)
        self.query = query

        # check error
        if payload["error"]:
            raise PixivException('Image Error: ' + payload["message"], errorCode=PixivException.SERVER_ERROR)

        # parse image information
        parsed = BeautifulSoup(payload["body"]["html"])
        self.itemList = list()
        images = parsed.findAll("div", attrs={"class": self.__re_imageItemClass})
        for item in images:
            thumbnail_container = item.find("div", attrs={"class": "thumbnail-container"})
            image_details = thumbnail_container.find("a", attrs={"class": "_work-modal-target user-activity"})
            image_id = image_details["data-work-id"]

            # like count
            status_container = thumbnail_container.find("div", attrs={"class": "status-container"})
            bookmarkCount = status_container.text

            imageResponse = 0
            self.itemList.append(PixivModel.PixivTagsItem(int(image_id), int(bookmarkCount), int(imageResponse)))

        if len(self.itemList) > 0:
            self.haveImage = True
        else:
            self.haveImage = False

        # search page info
        self.availableImages = int(payload["body"]["total"])
        if len(payload["body"]["next_url"]) > 0:
            self.isLastPage = False
        else:
            self.isLastPage = True

        return self.itemList


def parseJs(page):
    jss = re_payload.findall(str(page))

    if len(jss) == 0:
        return None  # Possibly error page

    # Fix issue #364, switch to demjson
    return demjson.decode(jss[0])
##
##
##    js = jss[0]
##    js1_split = js.split('{')
##    upd_js1_split = list()
##    for js1_token in js1_split:
##        js2_split = js1_token.split(',')
##        upd_js2_split = list()
##
##        for token in js2_split:
##            token_split = token.split(':', 1)
##            if len(token_split[0]) > 0 and not token_split[0].startswith("\"") and not token_split[0].startswith("{") and not token_split[0].startswith("}"):
##                token_split[0] = "\"" + token_split[0].strip() + "\""
##            else:
##                token_split[0] = token_split[0].strip()
##            if len(token_split) > 1:
##                token_split[1] = token_split[1].strip()
##            token_join = ":".join(token_split)
##            upd_js2_split.append(token_join)
##        js1_join = ",".join(upd_js2_split)
##        upd_js1_split.append(js1_join)
##
##    result = "{".join(upd_js1_split)
##    result = result.replace(",}", "}")
##
##    # PixivHelper.GetLogger().debug("ConvertedJson")
##    # PixivHelper.GetLogger().debug(result)
##    try:
##        return json.loads(result)
##    except:
##        PixivHelper.print_and_log("error", "failed to parse json:")
##        PixivHelper.print_and_log("error", result)
##        raise
