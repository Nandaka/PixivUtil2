# -*- coding: utf-8 -*-
# pylint: disable=C1801, C0330
import demjson

import datetime_z


class SketchArtist(object):
    artistId = 0
    artistName = ""
    artistAvatar = ""
    artistToken = ""
    artistBackground = ""
    posts = []
    dateFormat = None
    _tzInfo = None
    next_page = None

    def __init__(self, artist_id, page, tzInfo=None, dateFormat=None):
        self.artistId = artist_id
        self.posts = list()
        self.dateFormat = dateFormat
        self._tzInfo = tzInfo

        if page is not None:
            post_json = demjson.decode(page)
            self.parse_artist(post_json["data"])

    def parse_artist(self, page):
        # from https://sketch.pixiv.net/api/users/@camori.json
        root = page
        if "item" in page:
            # from https://sketch.pixiv.net/api/replies/3192562692181961341.json
            root = page["item"]["user"]

        self.artistName = root["name"]
        self.artistToken = root["unique_name"]
        self.artistAvatar = root["icon"]["photo"]["original"]["url"]

    def parse_posts(self, page):
        post_json = demjson.decode(page)

        links_root = post_json["_links"]
        if "next" in links_root:
            self.next_page = links_root["next"]["href"]
        else:
            self.next_page = None

        for item in post_json["data"]["items"]:
            post_id = item["id"]
            post = SketchPost(post_id, self, None, self._tzInfo, self.dateFormat)
            post.parse_post(item)
            self.posts.append(post)

    def __str__(self):
        return f"SketchArtist({self.artistId}, {self.artistName}, {self.artistToken}, {len(self.posts)})"


class SketchPost(object):
    imageId = 0
    imageTitle = ""
    imageCaption = ""
    imageUrls = []
    imageResizedUrls = []
    imageMode = ""
    worksDate = ""
    worksDateDateTime = None

    parent = None
    dateFormat = None
    _tzInfo = None

    def __init__(self, post_id, parent, page, tzInfo=None, dateFormat=None):
        self.imageUrls = list()
        self.imageResizedUrls = list()
        self.imageId = int(post_id)
        self._tzInfo = tzInfo
        self.dateFormat = dateFormat

        if page is not None:
            post_json = demjson.decode(page)
            if parent is None:
                artist_id = post_json["data"]["item"]["user"]["id"]
                self.parent = SketchArtist(artist_id, page, tzInfo, dateFormat)
            else:
                self.parent = parent
            self.parse_post(post_json["data"]["item"])

    def parse_post(self, page):
        # post title taken from username
        self.imageTitle = page["user"]["name"]
        self.imageCaption = page["text"]
        self.imageTags = list()
        for tag in page["tags"]:
            self.imageTags.append(tag)

        for media in page["media"]:
            self.imageMode = media["type"]
            self.imageUrls.append(media["photo"]["original"]["url"])
            self.imageResizedUrls.append(media["photo"]["w540"]["url"])

        self.worksDateDateTime = datetime_z.parse_datetime(str(page["updated_at"]))
        if self._tzInfo is not None:
            self.worksDateDateTime = self.worksDateDateTime.astimezone(self._tzInfo)

        tempDateFormat = self.dateFormat or "%m/%d/%y %H:%M"  # 2/27/2018 12:31
        self.worksDate = self.worksDateDateTime.strftime(tempDateFormat)

    def __str__(self):
        if self.parent is not None:
            return f"SketchPost({self.parent}: {self.imageId}, {self.imageTitle}, {self.imageMode}, {self.imageUrls[0]})"
        else:
            return f"SketchPost({self.imageId}, {self.imageTitle}, {self.imageMode}, {self.imageUrls[0]})"
