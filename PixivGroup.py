# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import json
import re
from datetime import datetime

from PixivArtist import PixivArtist
from PixivImage import PixivImage


class PixivGroup(object):
    short_pattern = re.compile(r"https?://www.pixiv.net/member_illust.php\?mode=(.*)&illust_id=(\d+)")
    imageList = None
    externalImageList = None
    maxId = 0

    def __init__(self, jsonResponse):
        data = json.loads(jsonResponse)
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
                image_data.worksResolution = ""
                image_data.worksTools = ""
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
