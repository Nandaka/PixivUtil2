# -*- coding: utf-8 -*-
# pylint: disable=C1801, C0330
import codecs
import os
import re
import sys
from typing import List

import demjson3
from bs4 import BeautifulSoup

import datetime_z
import PixivHelper
from PixivException import PixivException

_re_fanbox_cover = re.compile(r"c\/.*\/fanbox")
_url_pattern = re.compile("(https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]")


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
    # 949
    descriptionUrlList = None

    def __init__(self, post_id, parent, page, tzInfo=None):
        self.images = list()
        self.embeddedFiles = list()
        self.imageId = int(post_id)
        self.parent = parent
        self._tzInfo = tzInfo
        # 949
        self.descriptionUrlList = list()
        self.linkToFile = dict()

        self.parsePost(page)
        self.parse_post_details(page)

    def parse_post_details(self, page):
        # Issue #1094
        if not self.is_restricted and "body" in page:
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

        coverUrl = jsPost["coverImageUrl"]
        # Issue #930
        if not self.coverImageUrl and coverUrl:
            self.coverImageUrl = _re_fanbox_cover.sub("fanbox", coverUrl)
            self.try_add(coverUrl, self.embeddedFiles)

        self.worksDate = jsPost["publishedDatetime"]
        self.worksDateDateTime = datetime_z.parse_datetime(self.worksDate)
        self.updatedDate = jsPost["updatedDatetime"]
        self.updatedDateDatetime = datetime_z.parse_datetime(self.updatedDate)

        if "feeRequired" in jsPost:
            self.feeRequired = jsPost["feeRequired"]

        # Issue #420
        if self._tzInfo is not None:
            self.worksDateDateTime = self.worksDateDateTime.astimezone(self._tzInfo)

        # Issue #1094
        if "type" in jsPost:
            self.type = jsPost["type"]
            if self.type not in FanboxPost._supportedType:
                raise PixivException(f"Unsupported post type = {self.type} for post = {self.imageId}", errorCode=9999, htmlPage=jsPost)
        else:
            # assume it is image post
            self.type = "image"

        self.likeCount = int(jsPost["likeCount"])

        # Issue #1094
        if "body" not in jsPost or jsPost["body"] is None:
            self.is_restricted = True
        if "isRestricted" in jsPost:
            self.is_restricted = jsPost["isRestricted"]

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
                # Issue #929
                if link["href"].find("//fanbox.pixiv.net/images/entry/") > 0 or link["href"].find("//downloads.fanbox.cc/") > 0:
                    self.try_add(link["href"], self.embeddedFiles)
                    self.try_add(link["href"], self.images)
                # 949
                else:
                    self.try_add(link["href"], self.descriptionUrlList)
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
                    block_text_raw = block["text"]

                    if block_text_raw == "":
                        block_text = "<br/>"
                    else:
                        in_hyper = False
                        in_style = False
                        style_clause = ""
                        sections = []
                        links = sorted(block.get("links", []), key=lambda x: x["offset"])
                        styles = sorted(block.get("styles", []), key=lambda x: x["offset"])

                        # 949
                        for link in links:
                            self.try_add(link["url"], self.descriptionUrlList)
                        for match in _url_pattern.finditer(block_text_raw):
                            self.try_add(match.group(), self.descriptionUrlList)

                        for i in range(0, len(block_text_raw)):
                            for link in links:
                                link_offset = link["offset"]
                                link_length = link["length"]
                                if i > link_offset + link_length:
                                    continue
                                elif i < link_offset:
                                    break
                                # prioritized this situation for efficiency, nothing to do here indeed
                                # not sure if this is how python works
                                elif link_offset < i < link_offset + link_length:
                                    pass
                                elif link_offset == i:
                                    in_hyper = True
                                    if in_style:
                                        sections.append("</span>")
                                    sections.append("<a href='{0}'>".format(link["url"]))
                                    if in_style:
                                        sections.append(f"<span style='{style_clause}'>")
                                elif link_offset + link_length == i:
                                    in_hyper = False
                                    if in_style:
                                        sections.append("</span>")
                                    sections.append("</a>")
                                    if in_style:
                                        sections.append(f"<span style='{style_clause}'>")
                            for style in styles:
                                style_offset = style["offset"]
                                style_length = style["length"]
                                style_clause = style["type"]
                                if style_clause == "bold":
                                    style_clause = "font-weight: bold;"
                                    if i > style_offset + style_length:
                                        continue
                                    elif i < style_offset:
                                        break
                                    # prioritized this situation for efficiency, nothing to do here indeed
                                    # not sure if this is how python works
                                    elif style_offset < i < style_offset + style_length:
                                        pass
                                    elif style_offset == i:
                                        in_style = True
                                        sections.append(f"<span style='{style_clause}'>")
                                    elif style_offset + style_length == i:
                                        in_style = False
                                        sections.append("</span>")
                                else:
                                    raise PixivException(f"Unknown style: {style_clause}", errorCode=PixivException.OTHER_ERROR)
                            sections.append(block_text_raw[i])
                        if in_style:
                            sections.append("</span>")
                        if in_hyper:
                            sections.append("</a>")
                        block_text = "".join(sections)
                    self.body_text += f"<p>{block_text}</p>"
                elif block["type"] == "header":
                    block_text = block["text"]
                    self.body_text += f"<h2>{block_text}</h2>"
                elif block["type"] == "image":
                    imageId = block["imageId"]
                    if imageId not in jsPost["body"]["imageMap"]:
                        continue
                    originalUrl = jsPost["body"]["imageMap"][imageId]["originalUrl"]
                    thumbnailUrl = jsPost["body"]["imageMap"][imageId]["thumbnailUrl"]
                    self.body_text += f"<a href='{originalUrl}'><img src='{thumbnailUrl}'/></a>"
                    self.try_add(originalUrl, self.images)
                    self.try_add(originalUrl, self.embeddedFiles)
                elif block["type"] == "file":
                    fileId = block["fileId"]
                    if fileId not in jsPost["body"]["fileMap"]:
                        continue
                    fileUrl = jsPost["body"]["fileMap"][fileId]["url"]
                    fileName = jsPost["body"]["fileMap"][fileId]["name"]
                    self.body_text += f"<p><a href='{fileUrl}'>{fileName}</a></p>"
                    self.try_add(fileUrl, self.images)
                    self.try_add(fileUrl, self.embeddedFiles)
                elif block["type"] == "embed":  # Implement #470
                    embedId = block["embedId"]
                    if embedId in jsPost["body"]["embedMap"]:
                        embedStr = self.getEmbedData(jsPost["body"]["embedMap"][embedId], jsPost)
                        self.body_text += f"<p>{embedStr}</p>"
                        # 949
                        # links = re.finditer("<a.*?href=(?P<mark>'|\")(.+?)(?P=mark)", embedStr)
                        # for link in links:
                        #     self.try_add(link.group(2), self.descriptionUrlList)
                        links = _url_pattern.finditer(embedStr)
                        for link in links:
                            self.try_add(link.group(), self.descriptionUrlList)
                    else:
                        PixivHelper.print_and_log("warn", f"Found missing embedId: {embedId} for {self.imageId}")
                elif block["type"] == "url_embed":  # Issue #1087
                    urlEmbedId = block["urlEmbedId"]
                    if urlEmbedId in jsPost["body"]["urlEmbedMap"]:
                        result = self.get_embed_url_data(jsPost["body"]["urlEmbedMap"][urlEmbedId], jsPost)
                        self.body_text += "\n" + result
                        # embedType = jsPost["body"]["urlEmbedMap"][urlEmbedId]["type"]
                        # if embedType == "html.card":
                        #     embedStr = jsPost["body"]["urlEmbedMap"][urlEmbedId]["html"]
                        #     self.body_text += f"<p>{embedStr}</p>"
                        #     links = _url_pattern.finditer(embedStr)
                        #     for link in links:
                        #         self.try_add(link.group(), self.descriptionUrlList)
                        # else:
                        #     PixivHelper.print_and_log("warn", f"Unknown urlEmbedId's type: {urlEmbedId} for {self.imageId} => {embedType}")
                    else:
                        PixivHelper.print_and_log("warn", f"Found missing urlEmbedId: {urlEmbedId} for {self.imageId}")

        # Issue #476
        if "video" in jsPost["body"]:
            self.body_text += u"{0}<br />{1}".format(
                self.body_text,
                self.getEmbedData(jsPost["body"]["video"], jsPost))

    def get_embed_url_data(self, embedData, jsPost) -> str:
        # Issue #1133
        content_provider_path = os.path.abspath(os.path.dirname(sys.executable) + os.sep + "content_provider.json")
        if not os.path.exists(content_provider_path):
            content_provider_path = os.path.abspath("./content_provider.json")
        if not os.path.exists(content_provider_path):
            raise PixivException(f"Missing content_provider.json, please get it from https://github.com/Nandaka/PixivUtil2/blob/master/content_provider.json! Expected location => {content_provider_path}",
                                 errorCode=PixivException.MISSING_CONFIG,
                                 htmlPage=None)

        cfg = demjson3.decode_file(content_provider_path)
        embed_cfg = cfg["urlEmbedConfig"]
        current_provider = embedData["type"]

        if current_provider in embed_cfg:
            if embed_cfg[current_provider]["ignore"]:
                return ""

            # get urls from given keys
            for key in embed_cfg[current_provider]["get_link_keys"]:
                js_keys = key.split(".")
                root = embedData
                for js_key in js_keys:
                    root = root[js_key]
                links = _url_pattern.finditer(root)
                for link in links:
                    self.try_add(link.group(), self.descriptionUrlList)

            # get all the keys to list
            keys = list()
            for key in embed_cfg[current_provider]["keys"]:
                js_keys = key.split(".")
                root = embedData
                for js_key in js_keys:
                    root = root[js_key]
                keys.append(root)
            template = embed_cfg[current_provider]["format"]

            result = template.format(*keys)
            return result

        else:
            msg = "Unsupported url embed provider = {0} for post = {1}, please update content_provider.json."
            raise PixivException(msg.format(embedData["serviceProvider"], self.imageId),
                                 errorCode=9999,
                                 htmlPage=jsPost)

    def getEmbedData(self, embedData, jsPost) -> str:
        # Issue #881
        content_provider_path = os.path.abspath(os.path.dirname(sys.executable) + os.sep + "content_provider.json")
        if not os.path.exists(content_provider_path):
            content_provider_path = os.path.abspath("./content_provider.json")
        if not os.path.exists(content_provider_path):
            raise PixivException(f"Missing content_provider.json, please get it from https://github.com/Nandaka/PixivUtil2/blob/master/content_provider.json! Expected location => {content_provider_path}",
                                 errorCode=PixivException.MISSING_CONFIG,
                                 htmlPage=None)

        cfg = demjson3.decode_file(content_provider_path)
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
        print(f"Post  = {self.imageId}")
        print(f"Title = {self.imageTitle}")
        print(f"Type  = {self.type}")
        print(f"Created Date  = {self.worksDate}")
        print(f"Is Restricted = {self.is_restricted}")

    def WriteInfo(self, filename):
        info = None
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)

            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".txt", 'wb', encoding='utf-8')
            PixivHelper.get_logger().exception("Error when saving image info: %s, file is saved to: %s.txt", filename, self.imageId)

        info.write(f"ArtistID      = {self.parent.artistId}\r\n")
        info.write(f"ArtistName    = {self.parent.artistName}\r\n")

        info.write(f"ImageID       = {self.imageId}\r\n")
        info.write(f"Title         = {self.imageTitle}\r\n")
        info.write(f"Caption       = {self.body_text}\r\n")
        if self.is_restricted:
            info.write(f"Image Mode    = {self.type}, Restricted\r\n")
        else:
            info.write(f"Image Mode    = {self.type}\r\n")
        info.write(f"Pages         = {self.imageCount}\r\n")
        info.write(f"Date          = {self.worksDate}\r\n")
        info.write(f"Like Count    = {self.likeCount}\r\n")
        # https://www.fanbox.cc/@nekoworks/posts/928
        info.write(f"Link          = https://www.fanbox.cc/@{self.parent.creatorId}/posts/{self.imageId}\r\n")
        if len(self.embeddedFiles) > 0:
            info.write("Urls          =\r\n")
            for link in self.embeddedFiles:
                info.write(" - {0}\r\n".format(link))
        if len(self.embeddedFiles) > 0:
            info.write("descriptionUrlList =\r\n")
            for link in self.descriptionUrlList:
                info.write(" - {0}\r\n".format(link))
        info.close()

    def WriteHtml(self, html_template, useAbsolutePaths, filename):
        info = None
        try:
            PixivHelper.makeSubdirs(filename)
            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".html", 'wb', encoding='utf-8')
            PixivHelper.get_logger().exception("Error when saving article html: %s, file is saved to: %s.html", filename, self.imageId)

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
            token_body_text = f'<div class="article caption">{self.body_text}</div>'
        else:
            token_images = '<div class="non-article images">{0}</div>'.format(
                "".join(['<a href="{0}">{1}</a>'.format(x,
                f'<img scr="{0}"/>' if x[x.rindex(".") + 1:].lower() in ["jpg", "jpeg", "png", "bmp", "gif"] else x) for x in self.images]))
            token_text = '<div class="non-article caption">{0}</div>'.format(
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
        root = page.find("div", attrs={"class": "main"})
        if root:
            root["class"].append("non-article" if self.type != "article" else "article")
        page = page.decode()
        html_dir = os.path.dirname(filename)
        for k, v in self.linkToFile.items():
            if not useAbsolutePaths:
                try:
                    v = os.path.relpath(v, html_dir)
                except ValueError:
                    PixivHelper.get_logger().exception("Error when converting local paths to relative ones, absolute paths are used", filename, self.imageId)
                    v = "file://" + v
            else:
                v = "file://" + v
            page = page.replace(k, v)
        info.write(page)
        info.close()


class FanboxArtist(object):
    artistId = 0
    creatorId = ""
    nextUrl = None
    hasNextPage = False
    _tzInfo = None
    # require additional API call
    artistName = ""
    artistToken = ""
    fanbox_name = ""

    SUPPORTING = 0
    FOLLOWING = 1
    CUSTOM = 2

    @classmethod
    def parseArtistIds(cls, page):
        ids = list()
        js = demjson3.decode(page)

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
        # Issue #1117 Fanbox name might be different with Pixiv name
        self.fanbox_name = artist_name

    def __str__(self):
        return f"FanboxArtist({self.artistId}, {self.creatorId}, {self.artistName})"

    def parsePosts(self, page) -> List[FanboxPost]:
        js = demjson3.decode(page)

        if "error" in js and js["error"]:
            raise PixivException(f"Error when requesting Fanbox artist: {self.artistId}", 9999, page)

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
