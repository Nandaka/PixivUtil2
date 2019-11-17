# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import os
import re
import shutil
import zipfile
import codecs
import collections
import urllib
import datetime_z
import urllib
from collections import OrderedDict
from datetime import datetime
import json

import demjson
from bs4 import BeautifulSoup

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
                    raise PixivException("Missing body content, possible artist id doesn't exists.",
                                         errorCode=PixivException.USER_ID_NOT_EXISTS, htmlPage=page)
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
