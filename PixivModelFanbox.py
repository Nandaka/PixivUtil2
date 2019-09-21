# -*- coding: utf-8 -*-
# pylint: disable=C1801, C0330
import codecs
import os

import demjson
import datetime_z

from PixivException import PixivException
import PixivHelper


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
        # Fix #495
        if "supportingPlans" in js_body:
            js_body = js_body["supportingPlans"]
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

        if "error" in js and js["error"]:
            raise PixivException("Error when requesting Fanbox artist: {0}".format(self.artistId), 9999, page)

        if js["body"] is not None:
            self.parsePosts(js["body"])

    def parsePosts(self, js_body):
        self.posts = list()

        if "creator" in js_body:
            self.artistName = js_body["creator"]["user"]["name"]

        if "post" in js_body:
            post_root = js_body["post"]
        else:
            # https://www.pixiv.net/ajax/fanbox/post?postId={0}
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
    # image|text|file|article|video
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

    _supportedType = ["image", "text", "file", "article", "video"]
    embeddedFiles = None
    provider = None

    def __init__(self, post_id, parent, page, tzInfo=None):
        self.images = list()
        self.embeddedFiles = list()
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
        if self.coverImageUrl is not None:
            self.embeddedFiles.append(jsPost["coverImageUrl"])
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
        if "text" in jsPost["body"]:
            self.body_text = jsPost["body"]["text"]

        # Issue #438
        if "imageMap" in jsPost["body"] and jsPost["body"]["imageMap"] is not None:
            for image in jsPost["body"]["imageMap"]:
                self.images.append(jsPost["body"]["imageMap"][image]["originalUrl"])
                self.embeddedFiles.append(jsPost["body"]["imageMap"][image]["originalUrl"])

        if "fileMap" in jsPost["body"] and jsPost["body"]["fileMap"] is not None and len(jsPost["body"]["fileMap"]) > 0:
            for filename in jsPost["body"]["fileMap"]:
                self.images.append(jsPost["body"]["fileMap"][filename]["url"])
                self.embeddedFiles.append(jsPost["body"]["fileMap"][filename]["url"])

        if "embedMap" in jsPost["body"] and jsPost["body"]["embedMap"] is not None and len(jsPost["body"]["embedMap"]) > 0:
            for embed in jsPost["body"]["embedMap"]:
                embedData.append(jsPost["body"]["embedMap"][embed])
                self.embeddedFiles.append(jsPost["body"]["embedMap"][embed])

        if "blocks" in jsPost["body"] and jsPost["body"]["blocks"] is not None:
            for block in jsPost["body"]["blocks"]:
                if block["type"] == "p":
                    self.body_text = "{0}<p>{1}</p>".format(self.body_text, block["text"])
                elif block["type"] == "image":
                    imageId = block["imageId"]
                    self.body_text = "{0}<br /><a href='{1}'><img src='{2}'/></a>".format(
                                     self.body_text,
                                     jsPost["body"]["imageMap"][imageId]["originalUrl"],
                                     jsPost["body"]["imageMap"][imageId]["thumbnailUrl"])
                elif block["type"] == "file":
                    fileId = block["fileId"]
                    self.body_text = "{0}<br /><a href='{1}'>{2}</a>".format(
                                     self.body_text,
                                     jsPost["body"]["fileMap"][fileId]["url"],
                                     jsPost["body"]["fileMap"][fileId]["name"])
                elif block["type"] == "embed":  # Implement #470
                    embedId = block["embedId"]
                    self.body_text = "{0}<br />{1}".format(
                                     self.body_text,
                                     self.getEmbedData(jsPost["body"]["embedMap"][embedId], jsPost))

        # Issue #476
        if "video" in jsPost["body"]:
            self.body_text = "{0}<br />{1}".format(
                             self.body_text,
                             self.getEmbedData(jsPost["body"]["video"], jsPost))

    def getEmbedData(self, embedData, jsPost):
        if not os.path.exists("content_provider.json"):
            raise PixivException("Missing content_provider.json, please redownload application!",
                                  errorCode=PixivException.MISSING_CONFIG,
                                  htmlPage=None)

        cfg = demjson.decode_file("content_provider.json")
        embed_cfg = cfg["embedConfig"]
        current_provider = embedData["serviceProvider"]

        if current_provider in embed_cfg:
            if embed_cfg[current_provider]["ignore"]:
                return ""

            content_id = None
            for key in embed_cfg[current_provider]["keys"]:
                if key in embedData:
                    content_id = embedData[key]
                    break

            if content_id is not None and len(content_id) > 0:
                content_format = embed_cfg[current_provider]["format"]
                return content_format.format(content_id)
            else:
                raise PixivException("Empty content_id for embed provider = {0} for post = {1}, please update content_provider.json.".format(embedData["serviceProvider"], self.imageId),
                                      errorCode=9999,
                                      htmlPage=jsPost)
        else:
            raise PixivException("Unsupported embed provider = {0} for post = {1}, please update content_provider.json.".format(embedData["serviceProvider"], self.imageId),
                                 errorCode=9999,
                                 htmlPage=jsPost)

    def parseImages(self, jsPost):
        for image in jsPost["body"]["images"]:
            self.images.append(image["originalUrl"])
            if image["originalUrl"] not in self.embeddedFiles:
                self.embeddedFiles.append(image["originalUrl"])

    def parseFiles(self, jsPost):
        for image in jsPost["body"]["files"]:
            self.images.append(image["url"])
            if image["url"] not in self.embeddedFiles:
                self.embeddedFiles.append(image["url"])

    def WriteInfo(self, filename):
        info = None
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)

            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".txt", 'wb', encoding='utf-8')
            PixivHelper.GetLogger().exception("Error when saving image info: {0}, file is saved to: {1}.txt".format(filename, self.imageId))

        info.write("ArtistID      = {0}\r\n".format(self.parent.artistId))
        info.write("ArtistName    = {0}\r\n".format(self.parent.artistName))

        info.write("ImageID       = {0}\r\n".format(self.imageId))
        info.write("Title         = {0}\r\n".format(self.imageTitle))
        info.write("Caption       = {0}\r\n".format(self.body_text))
        # info.write(u"Tags          = " + ", ".join(self.imageTags) + "\r\n")
        if self.is_restricted:
            info.write("Image Mode    = {0}, Restricted\r\n".format(self.type))
        else:
            info.write("Image Mode    = {0}\r\n".format(self.type))
        info.write("Pages         = {0}\r\n".format(self.imageCount))
        info.write("Date          = {0}\r\n".format(self.worksDate))
        # info.write(u"Resolution    = " + self.worksResolution + "\r\n")
        # info.write(u"Tools         = " + self.worksTools + "\r\n")
        info.write("Like Count    = {0}\r\n".format(self.likeCount))
        info.write("Link          = https://www.pixiv.net/fanbox/creator/{0}/post/{1}\r\n".format(self.parent.artistId, self.imageId))
        # info.write("Ugoira Data   = " + str(self.ugoira_data) + "\r\n")
        if len(self.embeddedFiles) > 0:
            info.write("Urls          =\r\n")
            for link in self.embeddedFiles:
                info.write(" - {0}\r\n".format(link))
        info.close()
