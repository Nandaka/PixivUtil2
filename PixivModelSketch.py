# -*- coding: utf-8 -*-
# pylint: disable=C1801, C0330
import demjson3

import datetime_z
from PixivImage import PixivTagData


class SketchArtist(object):
    artistId = 0
    sketchArtistId = 0
    artistName = ""
    artistAvatar = ""
    artistToken = ""
    artistBackground = ""
    posts = []
    dateFormat = None
    _tzInfo = None
    next_page = None

    def __init__(self, artist_id, page, tzInfo=None, dateFormat=None):
        self.posts = list()
        self.dateFormat = dateFormat
        self._tzInfo = tzInfo

        if page is not None:
            post_json = demjson3.decode(page)
            self.parse_artist(post_json["data"])

    def parse_artist(self, page):
        # from https://sketch.pixiv.net/api/users/@camori.json
        root = page
        if "item" in page:
            # from https://sketch.pixiv.net/api/replies/3192562692181961341.json
            root = page["item"]["user"]

        # Issue #812
        if "pixiv_user_id" in root:
            self.artistId = root["pixiv_user_id"]
        else:
            self.artistId = root["id"]

        self.sketchArtistId = root["id"]
        self.artistName = root["name"]
        self.artistToken = root["unique_name"]
        self.artistAvatar = root["icon"]["photo"]["original"]["url"]

    def parse_posts(self, page):
        post_json = demjson3.decode(page)

        links_root = post_json["_links"]
        if "next" in links_root:
            self.next_page = links_root["next"]["href"]
        else:
            self.next_page = None

        for item in post_json["data"]["items"]:
            post_id = item["id"]
            post = SketchPost(post_id, None, None, self._tzInfo, self.dateFormat)
            post.parse_post(item)
            post.artist = self
            self.posts.append(post)

    def __str__(self):
        return f"SketchArtist({self.artistId}, {self.artistName}, {self.artistToken}, {len(self.posts)})"


class SketchPost(object):
    imageId = 0
    imageTitle = ""
    imageCaption = ""
    imageTags = None
    tags = None
    imageUrls = []
    imageResizedUrls = []
    # so far only photo is supported
    imageMode = ""
    worksDate = ""
    worksDateDateTime = None
    worksUpdateDate = ""
    worksUpdateDateTime = None

    artist = None
    dateFormat = None
    _tzInfo = None

    # not supported
    originalArtist = None
    worksResolution = ""
    worksTools = ""
    jd_rtv = 0
    jd_rtc = 0
    imageCount = 0
    fromBookmark = False
    bookmark_count = -1
    image_response_count = -1

    def __init__(self, post_id, artist, page, tzInfo=None, dateFormat=None):
        self.imageUrls = list()
        self.imageResizedUrls = list()
        self.imageId = int(post_id)
        self._tzInfo = tzInfo
        self.dateFormat = dateFormat

        if page is not None:
            post_json = demjson3.decode(page)
            if artist is None:
                artist_id = post_json["data"]["item"]["user"]["id"]
                self.artist = SketchArtist(artist_id, page, tzInfo, dateFormat)
            else:
                self.artist = artist
            self.parse_post(post_json["data"]["item"])

    def parse_post(self, page):
        # post title taken from username
        self.imageTitle = page["user"]["name"]
        self.imageCaption = page["text"]
        self.imageTags = list()
        self.tags = list()
        for tag in page["tags"]:
            self.imageTags.append(tag)
            self.tags.append(PixivTagData(tag, None))

        # add R-18 tag if is_r18 = True
        if "is_r18" in page and page["is_r18"]:
            self.imageTags.append('R-18')
            self.tags.append(PixivTagData('R-18', None))

        for media in page["media"]:
            self.imageMode = media["type"]
            self.imageUrls.append(media["photo"]["original"]["url"])
            self.imageResizedUrls.append(media["photo"]["w540"]["url"])

        self.worksDateDateTime = datetime_z.parse_datetime(str(page["published_at"]))
        if self._tzInfo is not None:
            self.worksDateDateTime = self.worksDateDateTime.astimezone(self._tzInfo)
        self.worksUpdateDateTime = datetime_z.parse_datetime(str(page["updated_at"]))
        if self._tzInfo is not None:
            self.worksUpdateDateTime = self.worksUpdateDateTime.astimezone(self._tzInfo)

        tempDateFormat = self.dateFormat or "%Y-%m-%d"  # 2018-07-22, else configured in config.ini
        self.worksDate = self.worksDateDateTime.strftime(tempDateFormat)
        self.worksUpdateDate = self.worksUpdateDateTime.strftime(tempDateFormat)

    def __str__(self):
        if self.artist is not None:
            return f"SketchPost({self.artist}: {self.imageId}, {self.imageTitle}, {self.imageMode}, {self.imageUrls[0]})"
        else:
            return f"SketchPost({self.imageId}, {self.imageTitle}, {self.imageMode}, {self.imageUrls[0]})"
