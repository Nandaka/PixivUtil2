# -*- coding: utf-8 -*-
# pylint: disable=C1801, C0330
import codecs
import os

import demjson
from bs4 import BeautifulSoup

import PixivHelper
import datetime_z
from PixivException import PixivException


class FanboxArtist(object):
    artistId = 0
    creatorId = ""
    nextUrl = None
    hasNextPage = False
    _tzInfo = None
    # require additional API call
    artistName = ""
    artistToken = ""

    SUPPORTING = 0
    FOLLOWING = 1

    @classmethod
    def parseArtistIds(cls, page):
        ids = list()
        js = demjson.decode(page)

        if "error" in js and js["error"]:
            raise PixivException("Error when requesting Fanbox", 9999, page)

        if "body" in js and js["body"] is not None:
            js_body = js["body"]
            if "supportingPlans" in js["body"]:
                js_body = js_body["supportingPlans"]
            for creator in js_body:
                ids.append(creator["user"]["userId"])
        return ids

    def __init__(self, artist_id, artist_name, creator_id, tzInfo=None):
        self.artistId = int(artist_id)
        self.artistName = artist_name
        self.creatorId = creator_id
        self._tzInfo = tzInfo

    def __str__(self):
        return f"FanboxArtist({self.artistId}, {self.creatorId}, {self.artistName})"

    def parsePosts(self, page):
        js = demjson.decode(page)

        if "error" in js and js["error"]:
            raise PixivException(
                "Error when requesting Fanbox artist: {0}".format(self.artistId), 9999, page)

        if js["body"] is not None:
            js_body = js["body"]

            posts = list()

            if "creator" in js_body:
                self.artistName = js_body["creator"]["user"]["name"]

            if "post" in js_body:
                # new api
                post_root = js_body["post"]
            else:
                # https://www.pixiv.net/ajax/fanbox/post?postId={0}
                # or old api
                post_root = js_body

            for jsPost in post_root["items"]:
                post_id = int(jsPost["id"])
                post = FanboxPost(post_id, self, jsPost, tzInfo=self._tzInfo)
                posts.append(post)
                # sanity check
                assert (self.artistId == int(jsPost["user"]["userId"])), "Different user id from constructor!"

            self.nextUrl = post_root["nextUrl"]
            if self.nextUrl is not None and len(self.nextUrl) > 0:
                self.hasNextPage = True

            return posts


class FanboxPost(object):
    imageId = 0
    imageTitle = ""
    coverImageUrl = ""
    worksDate = ""
    worksDateDateTime = None
    updatedDate = ""
    updatedDateDatetime = None
    # image|text|file|article|video|entry
    _supportedType = ["image", "text", "file", "article", "video", "entry"]
    type = ""
    body_text = ""
    images = None
    likeCount = 0
    parent = None
    is_restricted = False
    feeRequired = 0
    # compatibility
    imageMode = ""
    imageCount = 0
    _tzInfo = None

    linkToFile = None

    # not implemented
    worksResolution = ""
    worksTools = ""
    searchTags = ""
    imageTags = list()
    bookmark_count = 0
    image_response_count = 0

    embeddedFiles = None
    provider = None

    def __init__(self, post_id, parent, page, tzInfo=None):
        self.images = list()
        self.embeddedFiles = list()
        self.imageId = int(post_id)
        self.parent = parent
        self._tzInfo = tzInfo

        self.linkToFile = dict()

        self.parsePost(page)

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

    def __str__(self):
        if self.parent is not None:
            return f"FanboxPost({self.parent}: {self.imageId}, {self.imageTitle}, {self.type}, {self.feeRequired})"
        else:
            return f"FanboxPost({self.imageId}, {self.imageTitle}, {self.type}, {self.feeRequired})"

    def parsePost(self, jsPost):
        self.imageTitle = jsPost["title"]

        self.coverImageUrl = jsPost["coverImageUrl"]
        if self.coverImageUrl is not None and self.coverImageUrl not in self.embeddedFiles:
            self.embeddedFiles.append(jsPost["coverImageUrl"])

        self.worksDate = jsPost["publishedDatetime"]
        self.worksDateDateTime = datetime_z.parse_datetime(self.worksDate)
        self.updatedDate = jsPost["updatedDatetime"]
        self.updatedDateDatetime = datetime_z.parse_datetime(self.updatedDate)

        if "feeRequired" in jsPost:
            self.feeRequired = jsPost["feeRequired"]

        # Issue #420
        if self._tzInfo is not None:
            self.worksDateDateTime = self.worksDateDateTime.astimezone(
                self._tzInfo)

        self.type = jsPost["type"]
        if self.type not in FanboxPost._supportedType:
            raise PixivException("Unsupported post type = {0} for post = {1}".format(
                self.type, self.imageId), errorCode=9999, htmlPage=jsPost)

        self.likeCount = int(jsPost["likeCount"])
        if jsPost["body"] is None:
            self.is_restricted = True

    def parseBody(self, jsPost):
        ''' Parse general data for text and article'''
        self.body_text = ""
        embedData = list()
        if "text" in jsPost["body"]:
            self.body_text = jsPost["body"]["text"]
        # Issue #544
        elif "html" in jsPost["body"]:
            self.body_text = jsPost["body"]["html"]
            # Issue #611: try to parse all images in the html body for compatibility
            parsed = BeautifulSoup(self.body_text, features="html5lib")
            links = parsed.findAll('a')
            for link in links:
                if link["href"].find("//fanbox.pixiv.net/images/entry/") > 0:
                    self.try_add(link["href"], self.embeddedFiles)
                    self.try_add(link["href"], self.images)
            images = parsed.findAll('img')
            for image in images:
                if "data-src-original" in image.attrs:
                    self.try_add(image["data-src-original"], self.embeddedFiles)
                    self.try_add(image["data-src-original"], self.images)
            parsed.decompose()
            del parsed

        if "thumbnailUrl" in jsPost["body"] and jsPost["body"]["thumbnailUrl"] is not None:
            # set the thumbnail as the cover image is not exists.
            if self.coverImageUrl is None:
                PixivHelper.get_logger().debug("Missing coverImageUrl, using thumbnailUrl instead as cover.")
                self.coverImageUrl = jsPost["body"]["thumbnailUrl"]
            self.embeddedFiles.append(jsPost["body"]["thumbnailUrl"])

        if "embedMap" in jsPost["body"] and jsPost["body"]["embedMap"] is not None and len(jsPost["body"]["embedMap"]) > 0:
            for embed in jsPost["body"]["embedMap"]:
                embedData.append(jsPost["body"]["embedMap"][embed])
                self.embeddedFiles.append(jsPost["body"]["embedMap"][embed])

        if "blocks" in jsPost["body"] and jsPost["body"]["blocks"] is not None:
            for block in jsPost["body"]["blocks"]:
                if block["type"] == "p":
                    if "links" in block:
                        pointer = 0
                        block_text = ""
                        for i in range(0, len(block["links"])):
                            link = block["links"][i]
                            link_offset = link["offset"]
                            block_text += block["text"][pointer:link_offset]
                            pointer = link_offset + link["length"]
                            block_text += "<a href='{0}'>{1}</a>".format(
                                link["url"],
                                block["text"][link_offset:pointer])
                        block_text += block["text"][pointer:]
                    else:
                        block_text = block["text"]
                    self.body_text = u"{0}<p>{1}</p>".format(
                        self.body_text, block_text)
                elif block["type"] == "image":
                    imageId = block["imageId"]
                    if imageId not in jsPost["body"]["imageMap"]:
                        continue
                    self.body_text = u"{0}<br /><a href='{1}'><img src='{2}'/></a>".format(
                        self.body_text,
                        jsPost["body"]["imageMap"][imageId]["originalUrl"],
                        jsPost["body"]["imageMap"][imageId]["thumbnailUrl"])
                    self.try_add(jsPost["body"]["imageMap"][imageId]["originalUrl"], self.images)
                    self.try_add(jsPost["body"]["imageMap"][imageId]["originalUrl"], self.embeddedFiles)
                elif block["type"] == "file":
                    fileId = block["fileId"]
                    if fileId not in jsPost["body"]["fileMap"]:
                        continue
                    self.body_text = u"{0}<br /><a href='{1}'>{2}</a>".format(
                        self.body_text,
                        jsPost["body"]["fileMap"][fileId]["url"],
                        jsPost["body"]["fileMap"][fileId]["name"])
                    self.try_add(jsPost["body"]["fileMap"][fileId]["url"], self.images)
                    self.try_add(jsPost["body"]["fileMap"][fileId]["url"], self.embeddedFiles)
                elif block["type"] == "embed":  # Implement #470
                    embedId = block["embedId"]
                    self.body_text = u"{0}<br />{1}".format(
                        self.body_text,
                        self.getEmbedData(jsPost["body"]["embedMap"][embedId], jsPost))

        # Issue #476
        if "video" in jsPost["body"]:
            self.body_text = u"{0}<br />{1}".format(
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
                msg = "Empty content_id for embed provider = {0} for post = {1}, please update content_provider.json."
                raise PixivException(msg.format(embedData["serviceProvider"], self.imageId),
                                     errorCode=9999,
                                     htmlPage=jsPost)
        else:
            msg = "Unsupported embed provider = {0} for post = {1}, please update content_provider.json."
            raise PixivException(msg.format(embedData["serviceProvider"], self.imageId),
                                 errorCode=9999,
                                 htmlPage=jsPost)

    def parseImages(self, jsPost):
        for image in jsPost["body"]["images"]:
            self.try_add(image["originalUrl"], self.images)
            self.try_add(image["originalUrl"], self.embeddedFiles)

    def parseFiles(self, jsPost):
        for image in jsPost["body"]["files"]:
            self.try_add(image["url"], self.images)
            self.try_add(image["url"], self.embeddedFiles)

    def try_add(self, item, list_data):
        if self.coverImageUrl == item:
            return
        if item not in list_data:
            list_data.append(item)

    def printPost(self):
        print("Post  = {0}".format(self.imageId))
        print("Title = {0}".format(self.imageTitle))
        print("Type  = {0}".format(self.type))
        print("Created Date  = {0}".format(self.worksDate))
        print("Is Restricted = {0}".format(self.is_restricted))

    def WriteInfo(self, filename):
        info = None
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)

            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".txt",
                               'wb', encoding='utf-8')
            PixivHelper.get_logger().exception("Error when saving image info: %s, file is saved to: %s.txt", filename, self.imageId)

        info.write(u"ArtistID      = {0}\r\n".format(self.parent.artistId))
        info.write(u"ArtistName    = {0}\r\n".format(self.parent.artistName))

        info.write(u"ImageID       = {0}\r\n".format(self.imageId))
        info.write(u"Title         = {0}\r\n".format(self.imageTitle))
        info.write(u"Caption       = {0}\r\n".format(self.body_text))
        # info.write(u"Tags          = " + ", ".join(self.imageTags) + "\r\n")
        if self.is_restricted:
            info.write(
                u"Image Mode    = {0}, Restricted\r\n".format(self.type))
        else:
            info.write(u"Image Mode    = {0}\r\n".format(self.type))
        info.write(u"Pages         = {0}\r\n".format(self.imageCount))
        info.write(u"Date          = {0}\r\n".format(self.worksDate))
        # info.write(u"Resolution    = " + self.worksResolution + "\r\n")
        # info.write(u"Tools         = " + self.worksTools + "\r\n")
        info.write(u"Like Count    = {0}\r\n".format(self.likeCount))
        info.write(u"Link          = https://www.pixiv.net/fanbox/creator/{0}/post/{1}\r\n".format(
            self.parent.artistId, self.imageId))
        # info.write("Ugoira Data   = " + str(self.ugoira_data) + "\r\n")
        if len(self.embeddedFiles) > 0:
            info.write("Urls          =\r\n")
            for link in self.embeddedFiles:
                info.write(" - {0}\r\n".format(link))
        info.close()

    def WriteHtml(self, html_template, useAbsolutePaths, filename):
        info = None
        try:
            PixivHelper.makeSubdirs(filename)
            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".html",
                               'wb', encoding='utf-8')
            PixivHelper.get_logger().exception("Error when saving article html: %s, file is saved to: %s.html",
                                               filename, self.imageId)

        cover_image = ""
        if self.coverImageUrl:
            cover_image = f'<div class="cover"><img src="{self.coverImageUrl}"/></div>'
        page = html_template.replace("%coverImage%", cover_image)
        page = page.replace("%coverImageUrl%", self.coverImageUrl or "")
        page = page.replace("%artistName%", self.parent.artistName)
        page = page.replace("%imageTitle%", self.imageTitle)
        page = page.replace("%worksDate%", self.worksDate)

        token_body_text = ""
        token_images = ""
        token_text = ""
        if self.type == "article":
            token_body_text = f'<div class="article">{self.body_text}</div>'
        else:
            token_images = '<div class="non-article images">{0}</div>'.format(
                "".join(['<a href="{0}">{1}</a>'.format(x,
                f'<img scr="{0}"/>' if x[x.rindex(".") + 1:].lower() in ["jpg", "jpeg", "png", "bmp"] else x)for x in self.images]))
            token_text = '<div class="non-article text">{0}</div>'.format(
                "".join(['<p>{0}</p>'.format(x.rstrip()) for x in self.body_text.split("\n")]))

        page = page.replace("%body_text(article)%", token_body_text)
        page = page.replace("%images(non-article)%", token_images)
        page = page.replace("%text(non-article)%", token_text)

        page = BeautifulSoup(page, features="html5lib")
        imageATags = page.find_all("a", attrs={"href": True})
        for imageATag in imageATags:
            tag = imageATag.img
            if tag:
                tag["src"] = imageATag["href"]
        root = page.find("div", attrs={"class": "root"})
        if root:
            root["class"].append("non-article" if self.type != "article" else "article")
        page = page.prettify()
        html_dir = os.path.dirname(filename)
        for k, v in self.linkToFile.items():
            if not useAbsolutePaths:
                try:
                    v = os.path.relpath(v, html_dir)
                except ValueError:
                    PixivHelper.get_logger() \
                        .exception("Error when converting local paths to relative ones, absolute paths are used",
                                   filename, self.imageId)
                    v = "file://" + v
            else:
                v = "file://" + v
            page = page.replace(k, v)
        info.write(page)
        info.close()
