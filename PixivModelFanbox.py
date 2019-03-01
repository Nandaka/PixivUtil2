# -*- coding: utf-8 -*-
# pylint: disable=C1801, C0330
import demjson

import datetime_z
from PixivException import PixivException


class Fanbox(object):
    supportedArtist = None

    def __init__(self, page):
        js = demjson.decode(page)

        if js["error"]:
            raise PixivException("Error when requesting Fanbox", 9999, page)

        if js["body"] is not None:
            self.parseSupportedArtists(js["body"])

    def parseSupportedArtists(self, js_body):
        self.supportedArtist = list()
        for creator in js_body:
            self.supportedArtist.append(int(creator["user"]["userId"]))


class FanboxArtist(object):
    artistId = 0
    posts = None
    nextUrl = None
    hasNextPage = False
    _tzInfo = None

    # require additional API call
    artistName = ""
    artistToken = ""

    def __init__(self, artist_id, page, tzInfo=None):
        self.artistId = int(artist_id)
        self._tzInfo = tzInfo
        js = demjson.decode(page)

        if js["error"]:
            raise PixivException("Error when requesting Fanbox artist: {0}".format(self.artistId), 9999, page)

        if js["body"] is not None:
            self.parsePosts(js["body"])

    def parsePosts(self, js_body):
        self.posts = list()
        if js_body.has_key("post"):
            post_root = js_body["post"]
        else:
            post_root = js_body

        for jsPost in post_root["items"]:
            post_id = int(jsPost["id"])
            post = FanboxPost(post_id, self, jsPost, tzInfo=self._tzInfo)
            self.posts.append(post)

        self.nextUrl = post_root["nextUrl"]
        if self.nextUrl is not None and len(self.nextUrl) > 0:
            self.hasNextPage = True


class FanboxPost(object):
    imageId = 0
    imageTitle = ""
    coverImageUrl = ""
    worksDate = ""
    worksDateDateTime = None
    updatedDatetime = ""
    # image|text|file|article
    type = ""
    body_text = ""
    images = None
    likeCount = 0
    parent = None
    is_restricted = False

    # compatibility
    imageMode = ""
    imageCount = 0
    _tzInfo = None

    # not implemented
    worksResolution = ""
    worksTools = ""
    searchTags = ""
    imageTags = list()
    bookmark_count = 0
    image_response_count = 0

    _supportedType = ["image", "text", "file", "article"]

    def __init__(self, post_id, parent, page, tzInfo=None):
        self.images = list()
        self.imageId = int(post_id)
        self.parent = parent
        self.parsePost(page)
        self._tzInfo = tzInfo

        if not self.is_restricted:
            self.parseBody(page)

            if self.type == 'image':
                self.parseImages(page)
            if self.type == 'file':
                self.parseFiles(page)
        # compatibility for PixivHelper.makeFilename()
        self.imageCount = len(self.images)
        if self.imageCount > 0:
            self.imageMode = "manga"

    def parsePost(self, jsPost):
        self.imageTitle = jsPost["title"]
        self.coverImageUrl = jsPost["coverImageUrl"]
        self.worksDate = jsPost["publishedDatetime"]
        self.worksDateDateTime = datetime_z.parse_datetime(self.worksDate)
        # Issue #420
        if self._tzInfo is not None:
            self.worksDateDateTime = self.worksDateDateTime.astimezone(self._tzInfo)

        self.updatedDatetime = jsPost["updatedDatetime"]
        self.type = jsPost["type"]
        if self.type not in FanboxPost._supportedType:
            raise PixivException("Unsupported post type = {0} for post = {1}".format(self.type, self.imageId), errorCode=9999, htmlPage=jsPost)

        self.likeCount = int(jsPost["likeCount"])
        if jsPost["body"] is None:
            self.is_restricted = True

    def parseBody(self, jsPost):
        ''' Parse general data for text and article'''
        self.body_text = ""
        embedData = list()
        if jsPost["body"].has_key("text"):
            self.body_text = jsPost["body"]["text"]

        # Issue #438
        if jsPost["body"].has_key("imageMap") and jsPost["body"]["imageMap"] is not None:
            for image in jsPost["body"]["imageMap"]:
                self.images.append(jsPost["body"]["imageMap"][image]["originalUrl"])

        if jsPost["body"].has_key("fileMap") and jsPost["body"]["fileMap"] is not None and len(jsPost["body"]["fileMap"]) > 0:
            for filename in jsPost["body"]["fileMap"]:
                self.images.append(jsPost["body"]["fileMap"][filename]["url"])

        if jsPost["body"].has_key("embedMap") and jsPost["body"]["embedMap"] is not None and len(jsPost["body"]["embedMap"]) > 0:

            for embed in jsPost["body"]["embedMap"]:
                embedData.append(jsPost["body"]["embedMap"][embed])

        if jsPost["body"].has_key("blocks") and jsPost["body"]["blocks"] is not None:
            for block in jsPost["body"]["blocks"]:
                if block["type"] == "p":
                    self.body_text = u"{0}<p>{1}</p>".format(self.body_text, block["text"])
                elif block["type"] == "image":
                    imageId = block["imageId"]
                    self.body_text = u"{0}<br /><a href='{1}'><img src='{2}'/></a>".format(
                                     self.body_text,
                                     jsPost["body"]["imageMap"][imageId]["originalUrl"],
                                     jsPost["body"]["imageMap"][imageId]["thumbnailUrl"])
                elif block["type"] == "file":
                    fileId = block["fileId"]
                    self.body_text = u"{0}<br /><a href='{1}'>{2}</a>".format(
                                     self.body_text,
                                     jsPost["body"]["fileMap"][fileId]["url"],
                                     jsPost["body"]["fileMap"][fileId]["name"])
                elif block["type"] == "embed":  # Implement #470
                    embedId = block["embedId"]
                    self.body_text = u"{0}<br />{1}".format(
                                     self.body_text,
                                     self.getEmbedData(jsPost["body"]["embedMap"][embedId]))

    def getEmbedData(self, embedData):
        if embedData["serviceProvider"] == "twitter":
            return "<a href='https://twitter.com/_/status/{0}'>twitter post: {0}</a>".format(embedData["contentId"])
        else:
            raise PixivException("Unsupported embed provider = {0} for post = {1}".format(embedData["serviceProvider"],
                                                                                          self.imageId),
                                 errorCode=9999,
                                 htmlPage=jsPost)

    def parseImages(self, jsPost):
        for image in jsPost["body"]["images"]:
            self.images.append(image["originalUrl"])

    def parseFiles(self, jsPost):
        for image in jsPost["body"]["files"]:
            self.images.append(image["url"])
