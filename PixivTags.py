# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import json
import os
import re

import PixivHelper
from PixivException import PixivException


class PixivTagsItem:
    imageId = 0
    bookmarkCount = 0
    imageResponse = 0

    def __init__(self, image_id, bookmark_count, image_response_count):
        self.imageId = image_id
        self.bookmarkCount = bookmark_count
        self.imageResponse = image_response_count


class PixivTags:
    '''Class for parsing tags search page'''
    itemList = None
    haveImage = None
    isLastPage = None
    availableImages = 0
    __re_illust = re.compile(r'member_illust.*illust_id=(\d*)')
    __re_imageItemClass = re.compile(r".*\bimage-item\b.*")
    query = ""
    memberId = 0

    def parseMemberTags(self, artist, memberId, query=""):
        '''process artist result and return the image list'''
        self.itemList = list()
        self.memberId = memberId
        self.query = query
        self.haveImage = artist.haveImages
        self.isLastPage = artist.isLastPage
        for image in artist.imageList:
            self.itemList.append(PixivTagsItem(int(image), 0, 0))

    def parseTags(self, page, query="", curr_page=1):
        payload = json.loads(page)
        self.query = query

        # check error
        if payload["error"]:
            raise PixivException('Image Error: ' + payload["message"], errorCode=PixivException.SERVER_ERROR)

        # parse images information
        self.itemList = list()
        ad_container_count = 0
        for item in payload["body"]["illustManga"]["data"]:
            if "isAdContainer" in item and item["isAdContainer"]:
                ad_container_count = ad_container_count + 1
                continue

            image_id = item["id"]
            # like count not available anymore, need to call separate request...
            bookmarkCount = 0
            imageResponse = 0
            tag_item = PixivTagsItem(int(image_id), int(bookmarkCount), int(imageResponse))
            self.itemList.append(tag_item)

        self.haveImage = False
        if len(self.itemList) > 0:
            self.haveImage = True

        # search page info
        self.availableImages = int(payload["body"]["illustManga"]["total"])
        # assuming there are only 47 image (1 is marked as ad)
        # if self.availableImages > 47 * curr_page:
        # assume it always return 6 images, including the advert
        if len(self.itemList) + ad_container_count == 60:
            self.isLastPage = False
        else:
            self.isLastPage = True
        return self.itemList

    def PrintInfo(self):
        PixivHelper.safePrint('Search Result')
        if self.memberId > 0:
            PixivHelper.safePrint('Member Id: {0}'.format(self.memberId))
        PixivHelper.safePrint('Query: {0}'.format(self.query))
        PixivHelper.safePrint('haveImage  : {0}'.format(self.haveImage))
        PixivHelper.safePrint('urls  : {0}'.format(len(self.itemList)))
        for item in self.itemList:
            print("\tImage Id: {0}\tFav Count:{1}".format(item.imageId, item.bookmarkCount))
        PixivHelper.safePrint('total : {0}'.format(self.availableImages))
        PixivHelper.safePrint('last? : {0}'.format(self.isLastPage))

    @staticmethod
    def parseTagsList(filename):
        '''read tags.txt and return the tags list'''
        tags = list()

        if not os.path.exists(filename):
            raise PixivException("File doesn't exists or no permission to read: " + filename,
                                 PixivException.FILE_NOT_EXISTS_OR_NO_READ_PERMISSION)

        reader = PixivHelper.open_text_file(filename)
        for line in reader:
            if line.startswith('#') or len(line) < 1:
                continue
            line = line.strip()
            if len(line) > 0:
                tags.append(line)
        reader.close()
        return tags
