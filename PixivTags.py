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

    def __init__(self, image_id, bookmark_count=0, image_response_count=0):
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

    def parseTags(self, payload, query="", curr_page=1, config=None, caller=None, member=0):
        self.query = query

        # check error
        if payload["error"]:
            raise PixivException('Image Error: ' + payload["message"], errorCode=PixivException.SERVER_ERROR)
        if member:
            self.availableImages = int(payload["body"]["total"])
            payload = payload["body"]["works"]
            self.memberId=member #Is this even used anywhere?
        else:
            self.availableImages = int(payload["body"]["illustManga"]["total"])
            payload = payload["body"]["illustManga"]["data"]

        # parse images information
        self.itemList = list()
        if config and caller:
            if config.useBlacklistTags or config.useBlacklistTitles or config.dateDiff:
                from PixivListHandler import process_blacklist
                for x in process_blacklist(caller, config, payload)[0]:
                    self.itemList.append(PixivTagsItem(int(x)))
        else:
            for item in payload:
                if "isAdContainer" in item and item["isAdContainer"]:
                    continue
                self.itemList.append(PixivTagsItem(int(item["id"])))


        self.haveImage = len(self.itemList) > 0
        # assuming there are only 59 images (and an advertisement) per page
        if self.availableImages/59 > curr_page:
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
