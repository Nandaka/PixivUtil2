# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import json
import os
import re
from typing import Optional

import common.PixivHelper as PixivHelper
from common.PixivException import PixivException


class PixivTagsItem:
    imageId: int = 0
    bookmarkCount: int = 0
    imageResponse: int = 0
    ai_type: int = -1

    def __init__(self, image_id, bookmark_count, image_response_count, ai_type=-1):
        self.imageId = image_id
        self.bookmarkCount = bookmark_count
        self.imageResponse = image_response_count
        self.ai_type = ai_type


class PixivTags:
    '''Class for parsing tags search page'''
    itemList = None
    haveImage = None
    isLastPage = None
    availableImages = 0
    # __re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
    # __re_imageItemClass = re.compile(r".*\bimage-item\b.*")
    query = ""
    memberId = 0

    POSTS_PER_PAGE = 60
    page = -1

    def parseMemberTags(self, artist, memberId, query=""):
        '''process artist result and return the image list, https://www.pixiv.net/ajax/user/25661139/illustmanga/tag/<search_tags>'''
        self.itemList = list()
        self.memberId = memberId
        self.query = query
        self.haveImage = artist.haveImages
        self.isLastPage = artist.isLastPage
        for image in artist.imageList:
            self.itemList.append(PixivTagsItem(int(image), 0, 0))

    def parseTags(self, page, query="", curr_page=1):
        '''From search by tags page, https://www.pixiv.net/ajax/search/artworks/<search_tags>'''
        payload = json.loads(page)
        self.query = query
        self.page = curr_page

        # check error
        if payload["error"]:
            raise PixivException(f'Image Error: {payload["message"]}', errorCode=PixivException.SERVER_ERROR)

        # parse images information
        self.itemList = list()
        ad_container_count = 0
        for item in payload["body"]["illustManga"]["data"]:
            if "isAdContainer" in item and item["isAdContainer"]:
                ad_container_count = ad_container_count + 1
                continue

            image_id = int(item["id"])
            # like count not available anymore, need to call separate request...
            bookmarkCount = 0
            imageResponse = 0
            ai_type = -1
            if "aiType" in item:
                ai_type = int(item["aiType"])
            tag_item = PixivTagsItem(image_id, bookmarkCount, imageResponse, ai_type)
            self.itemList.append(tag_item)

        self.haveImage = False
        if len(self.itemList) > 0:
            self.haveImage = True

        # search page info
        self.availableImages = int(payload["body"]["illustManga"]["total"])
        # assume it always return 60 images, including the advert
        if len(self.itemList) + ad_container_count == PixivTags.POSTS_PER_PAGE:
            self.isLastPage = False
        else:
            self.isLastPage = True
        return self.itemList

    def PrintInfo(self):
        PixivHelper.safePrint('Search Result')
        if self.memberId > 0:
            PixivHelper.safePrint(f'Member Id: {self.memberId}')
        PixivHelper.safePrint(f'Query: {self.query}')
        PixivHelper.safePrint(f'haveImage  : {self.haveImage}')
        PixivHelper.safePrint(f'urls  : {len(self.itemList)}')
        for item in self.itemList:
            print(f"\tImage Id: {item.imageId}\tFav Count:{item.bookmarkCount}")
        PixivHelper.safePrint(f'total : {self.availableImages}')
        PixivHelper.safePrint(f'last? : {self.isLastPage}')

    @staticmethod
    def parseTagsList(filename):
        '''read tags.txt and return the tags list'''
        tags = list()

        if not os.path.exists(filename):
            raise PixivException(f"File doesn't exists or no permission to read: {filename}", PixivException.FILE_NOT_EXISTS_OR_NO_PERMISSION)

        reader = PixivHelper.open_text_file(filename)
        for line in reader:
            if line.startswith('#') or len(line) < 1:
                continue
            line = line.strip()
            if len(line) > 0:
                tags.append(line)
        reader.close()
        return tags

class PixivTag:
    """
    AJAX response of https://www.pixiv.net/ajax/search/tags/{tag_id}
    """

    class PixPediaInfo:
        abstract: str
        image: str
        id: str
        tag: str

        def __init__(self, payload):
            self.abstract = payload.get("abstract", "")
            self.image = payload.get("image", "")
            self.id = payload.get("id", "")
            self.tag = payload.get("tag", "")

    tag: str
    word: str
    pixpedia: Optional[PixPediaInfo]
    myFavoriteTags: list[str]
    tagTranslation: dict[str, dict[str, dict]]  # tag_id -> { lang -> translation }

    def __init__(self, payload):
        if payload is None:
            raise PixivException("Tag payload is empty", errorCode=PixivException.OTHER_ERROR)
        if payload.get("error"):
            raise PixivException(payload.get("message", "Tag info error"),
                                 errorCode=PixivException.OTHER_ERROR,
                                 htmlPage=payload)

        body = payload.get("body", {})
        self.tag = body.get("tag", "")
        self.word = body.get("word", "")
        pixpedia_payload = body.get("pixpedia")
        self.pixpedia = self.PixPediaInfo(pixpedia_payload) if pixpedia_payload else None
        self.myFavoriteTags = body.get("myFavoriteTags", [])
        self.tagTranslation = body.get("tagTranslation", {})
