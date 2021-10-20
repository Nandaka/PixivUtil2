# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import re

import demjson3
from bs4 import BeautifulSoup

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
    manga_series = []
    novel_series = []

    def __init__(self, mid: int = 0, page: str = None, fromImage=False, offset: int = None, limit: int = None):
        self.offset = offset
        self.limit = limit
        self.artistId = mid

        if page is not None:
            payload = None
            # detect if image count != 0
            if not fromImage:
                payload = demjson3.decode(page)
                if payload["error"]:
                    raise PixivException(payload["message"], errorCode=PixivException.OTHER_MEMBER_ERROR, htmlPage=page)
                if payload["body"] is None:
                    raise PixivException("Missing body content, possible artist id doesn't exists.",
                                         errorCode=PixivException.USER_ID_NOT_EXISTS, htmlPage=page)
                self.ParseImages(payload["body"])
                self.ParseMangaList(payload["body"])
                self.ParseNovelList(payload["body"])
            else:
                payload = self.parseJs(page)
                self.isLastPage = True
                self.haveImages = True

            # parse artist info
            self.ParseInfo(payload, fromImage)

    def ParseMangaList(self, payload):
        if payload is not None and "mangaSeries" in payload:
            for manga_series_id in payload["mangaSeries"]:
                self.manga_series.append(int(manga_series_id["id"]))

    def ParseNovelList(self, payload):
        if payload is not None and "novelSeries" in payload:
            for novel_series_id in payload["novelSeries"]:
                self.novel_series.append(int(novel_series_id["id"]))

    def ParseInfo(self, page, fromImage=False, bookmark=False):
        ''' parse artistId, artistAvatar, artistToken, artistName, and artistBackground '''
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
                else:
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

                if "profile" in page:
                    if self.totalImages == 0:
                        if bookmark:
                            self.totalImages = int(page["profile"]["total_illust_bookmarks_public"])
                        else:
                            self.totalImages = int(page["profile"]["total_illusts"]) + int(page["profile"]["total_manga"])
                    if "background_image_url" in page["profile"] and page["profile"]["background_image_url"] is not None and page["profile"]["background_image_url"].startswith("http"):
                        self.artistBackground = page["profile"]["background_image_url"]

    def ParseInfoFromImage(self, page):
        key = list(page["user"].keys())[0]
        root = page["user"][key]

        self.artistId = root["userId"]
        self.artistAvatar = root["image"].replace("_50.", ".").replace("_170.", ".")
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
        # self.artistBackground = "no_background"

        # https://www.pixiv.net/ajax/user/8021957
        if "body" in payload:
            root = payload["body"]
            self.artistId = root["userId"]
            self.artistName = root["name"]
            if "imageBig" in root and root["imageBig"] is not None:
                self.artistAvatar = payload["body"]["imageBig"].replace("_50.", ".").replace("_170.", ".")
            elif "image" in root and root["image"] is not None:
                self.artistAvatar = root["image"].replace("_50.", ".").replace("_170.", ".")

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

    def PrintInfo(self):
        print('Artist Info')
        print(f'id    : {self.artistId}')
        print(f'name  : {self.artistName}')
        print(f'avatar: {self.artistAvatar}')
        print(f'token : {self.artistToken}')
        print(f'urls  : {len(self.imageList)}')
        for item in self.imageList:
            print(f'\t{item}')
        print(f'total : {self.totalImages}')
        print(f'last? : {self.isLastPage}')

    def parseJs(self, page):
        ''' get the <meta> tag for attribute meta-preload-data and return json object'''
        parsed = BeautifulSoup(page, features="html5lib")
        jss = parsed.find('meta', attrs={'id': 'meta-preload-data'})

        # cleanup
        parsed.decompose()
        del parsed

        if jss is None or len(jss["content"]) == 0:
            return None  # Possibly error page

        payload = demjson3.decode(jss["content"])
        return payload
