# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import codecs
import collections
import json
import re
from datetime import datetime


class PixivBookmark(object):
    '''Class for parsing Bookmarks'''
    __re_imageULItemsClass = re.compile(r".*\b_image-items\b.*")

    @staticmethod
    def parseBookmark(page, root_directory, db_path):
        '''Parse favorite artist page'''
        from PixivDBManager import PixivDBManager
        bookmarks = list()
        db = PixivDBManager(root_directory=root_directory, target=db_path)
        __re_member = re.compile(r'member\.php\?id=(\d*)')
        result = page.find(attrs={'class': 'members'}).findAll('a')

        # filter duplicated member_id
        d = collections.OrderedDict()
        for r in result:
            member_id = __re_member.findall(r['href'])
            if len(member_id) > 0:
                d[member_id[0]] = member_id[0]
        result2 = list(d.keys())

        for r in result2:
            item = db.selectMemberByMemberId2(r)
            bookmarks.append(item)

        return bookmarks

    @staticmethod
    def parseImageBookmark(page):
        imageList = list()

        temp = page.find('ul', attrs={'class': PixivBookmark.__re_imageULItemsClass})
        temp = temp.findAll('a')
        if temp is None or len(temp) == 0:
            return imageList
        for item in temp:
            href = re.search(r'/artworks/(\d+)', str(item))
            if href is not None:
                href = href.group(1)
                if not int(href) in imageList:
                    imageList.append(int(href))

        return imageList

    @staticmethod
    def exportList(l, filename):
        if not filename.endswith('.txt'):
            filename = filename + '.txt'
        writer = codecs.open(filename, 'w', encoding='utf-8')
        writer.write(u'###Export date: ' + str(datetime.today()) + '###\n')
        for item in l:
            data = str(item.memberId)
            if len(item.path) > 0:
                data = data + ' ' + item.path
            writer.write(data)
            writer.write(u'\r\n')
        writer.write('###END-OF-FILE###')
        writer.close()


class PixivNewIllustBookmark(object):
    '''Class for parsing New Illust from Bookmarks'''
    imageList = None
    isLastPage = None
    haveImages = None

    def __init__(self, page):
        self.__ParseNewIllustBookmark(page)
        self.__CheckLastPage(page)
        self.haveImages = bool(len(self.imageList) > 0)

    def __ParseNewIllustBookmark(self, page):
        self.imageList = list()

        # Fix Issue#290
        jsBookmarkItem = page.find(id='js-mount-point-latest-following')
        if jsBookmarkItem is not None:
            js = jsBookmarkItem["data-items"]
            items = json.loads(js)
            for item in items:
                image_id = item["illustId"]
                # bookmarkCount = item["bookmarkCount"]
                # imageResponse = item["responseCount"]
                self.imageList.append(int(image_id))
        else:
            result = page.find(attrs={'class': '_image-items autopagerize_page_element'}).findAll('a')
            for r in result:
                href = re.search(r'/artworks/(\d+)', r['href'])
                if href is not None:
                    href = int(href.group(1))
                    if href not in self.imageList:
                        self.imageList.append(href)

        return self.imageList

    def __CheckLastPage(self, page):
        check = page.findAll('a', attrs={'class': '_button', 'rel': 'next'})
        if len(check) > 0:
            self.isLastPage = False
        else:
            self.isLastPage = True
        return self.isLastPage
