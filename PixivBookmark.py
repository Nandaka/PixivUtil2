# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import codecs
import collections
import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

import PixivException


class PixivBookmark(object):
    '''Class for parsing Bookmarks'''
    # __re_imageULItemsClass = re.compile(r".*\b_image-items\b.*")

    @staticmethod
    def parseBookmark(page, root_directory, db_path, locale='', is_json=False):
        '''Parse favorite artist page'''
        from PixivDBManager import PixivDBManager
        bookmarks = list()
        result2 = list()
        db = PixivDBManager(root_directory=root_directory, target=db_path)

        if is_json:
            parsed = json.loads(page)
            for member in parsed["body"]["users"]:
                if "isAdContainer" in member and member["isAdContainer"]:
                    continue
                result2.append(member["userId"])
        else:
            # old method
            parse_page = BeautifulSoup(page, features="html5lib")
            __re_member = re.compile(locale + r'/users/(\d*)')

            member_list = parse_page.find(attrs={'class': 'members'})
            result = member_list.findAll('a')

            # filter duplicated member_id
            d = collections.OrderedDict()
            for r in result:
                member_id = __re_member.findall(r['href'])
                if len(member_id) > 0:
                    d[member_id[0]] = member_id[0]
            result2 = list(d.keys())

            parse_page.decompose()
            del parse_page

        for r in result2:
            item = db.selectMemberByMemberId2(r)
            bookmarks.append(item)

        return bookmarks

    @staticmethod
    def parseImageBookmark(page, image_tags_filter=None):
        total_images = 0
        imageList = list()

        image_bookmark = json.loads(page)
        total_images = image_bookmark["body"]["total"]  # total bookmarks, won't be the same if image_tags_filter used.
        for work in image_bookmark["body"]["works"]:
            if "isAdContainer" in work and work["isAdContainer"]:
                continue

            # Issue #928
            skip = True
            if image_tags_filter is not None:  # exact tag only
                for tag in work["tags"]:
                    if tag == image_tags_filter:
                        skip = False
                        break
                if skip:
                    continue

            # Issue #822
            if "illustId" in work:
                imageList.append(int(work["illustId"]))
            elif "id" in work:
                imageList.append(int(work["id"]))

        return (imageList, total_images)

    @staticmethod
    def exportList(lst, filename):
        if not filename.endswith('.txt'):
            filename = filename + '.txt'
        writer = codecs.open(filename, 'w', encoding='utf-8')
        writer.write(f'###Export members date: {datetime.today()} ###\n')
        for item in lst:
            data = str(item.memberId)
            if len(item.path) > 0:
                data = data + ' ' + item.path
            writer.write(data)
            writer.write('\r\n')
        writer.write('###END-OF-FILE###')
        writer.close()

    @staticmethod
    def export_image_list(lst, filename):
        if not filename.endswith('.txt'):
            filename = filename + '.txt'
        writer = codecs.open(filename, 'w', encoding='utf-8')
        writer.write(f'###Export images date: {datetime.today()} ###\n')
        for item in lst:
            data = str(item)
            writer.write(data)
            writer.write('\r\n')
        writer.write('###END-OF-FILE###')
        writer.close()


class PixivNewIllustBookmark(object):
    '''Class for parsing New Illust from Bookmarks'''
    imageList = None
    isLastPage = None
    haveImages = None

    def __init__(self, page):
        self.__ParseNewIllustBookmark(page)
        # self.__CheckLastPage(page)
        self.haveImages = bool(len(self.imageList) > 0)

    def __ParseNewIllustBookmark(self, page):
        self.imageList = list()
        page_json = json.loads(page)

        if bool(page_json["error"]):
            raise PixivException(page_json["message"], errorCode=PixivException.OTHER_ERROR)

        # 1028
        for image_id in page_json["body"]["page"]["ids"]:
            self.imageList.append(int(image_id))

        return self.imageList
