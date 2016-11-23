# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302
import re
import json
from collections import OrderedDict
from BeautifulSoup import BeautifulSoup

import PixivModel
from PixivModel import PixivException
import PixivHelper

class PixivArtist(PixivModel.PixivArtist):
    def __init__(self, mid=0, page=None, fromImage=False):
        if page is not None:
            self.artistId=mid
            payload = json.loads(page)
            # check error
            if payload["error"] == True:
                raise PixivException('Artist Error: ' + str(payload["error"]), errorCode=PixivException.SERVER_ERROR)

            # detect if image count != 0
            if not fromImage:
                self.ParseImages(payload)
            else:
                self.isLastPage = True
                self.haveImages = True

            # parse artist info
            self.ParseInfo(payload, fromImage)


    def ParseInfo(self, page, fromImage=False, bookmark=False):
        self.artistId = 0
        self.artistAvatar = "no_profile"
        self.artistToken = "self"
        self.artistName = "self"

        if page is not None:
            if fromImage:
                # will be updated using AppAPI call from browser
                parsed = BeautifulSoup(page["body"]["html"])
                artist_container = parsed.find('div', attrs={'class':'header-author-container'})
                artist_link = artist_container.find('a', attrs={'class':'user-view-popup'})
                self.artistId = int(artist_link['data-user_id'])

                artist_icon = artist_container.find(attrs={'class': re.compile(r"_user-icon.*")})
                self.artistAvatar = re.findall(r"background-image:url\((.*)\)", artist_icon["style"])[0]

                self.artistName = artist_container.find("div", attrs={'class':'user-name'}).text
                self.artistToken = self.artistName

            else:
                data = None
                if page.has_key("user"):
                    data = page
                elif page.has_key("illusts") and len(page["illusts"]) > 0:
                    data = page["illusts"][0]

                if data is not None:
                    self.artistId = data["user"]["id"]
                    self.artistToken = data["user"]["account"]
                    self.artistName = data["user"]["name"]

                    avatar_data = data["user"]["profile_image_urls"]
                    if avatar_data is not None and avatar_data.has_key("medium"):
                        self.artistAvatar = avatar_data["medium"]

                if page.has_key("profile"):
                    if bookmark:
                        self.totalImages = int(page["profile"]["total_illust_bookmarks_public"])
                    else:
                        self.totalImages = int(page["profile"]["total_illusts"]) + int(page["profile"]["total_manga"])


    def ParseImages(self, page):
        self.imageList = list()
        parsed = BeautifulSoup(page["body"]["html"])
        item_containers = parsed.findAll("div", attrs={"class": re.compile("item-container _work-item-container.*")})
        for item in item_containers:
            # data-entry-id="illust:59640232"
            image_id_illust = item["data-entry-id"]
            image_id = int(image_id_illust.replace("illust:", ""))
            self.imageList.append(image_id)

        self.isLastPage = True
        if page["body"]["next_url"] is not None:
            self.isLastPage = False

        self.haveImages = False
        if len(self.imageList) > 0:
            self.haveImages = True


class PixivImage(PixivModel.PixivImage):
    def __init__(self, iid=0, page=None, parent=None, fromBookmark=False,
                 bookmark_count=-1, image_response_count=-1, dateFormat=None):
        self.artist = parent
        self.fromBookmark = fromBookmark
        self.bookmark_count = bookmark_count
        self.imageId = iid
        self.imageUrls = []
        self.dateFormat = dateFormat
        self.descriptionUrlList = []

        if page is not None:
            payload = json.loads(page)

            # check error
            if payload["error"] == True:
                raise PixivException('Image Error: ' + payload["message"], errorCode=PixivException.SERVER_ERROR)
            # parse image information
            parsed = BeautifulSoup(payload["body"]["html"])

            # parse artist information
            if parent is None:
                parsed = BeautifulSoup(payload["body"]["html"])
                artist_container = parsed.find('div', attrs={'class':'header-author-container'})
                artist_link = artist_container.find('a', attrs={'class':'user-view-popup'})
                artistId = int(artist_link['data-user_id'])
                self.artist = PixivArtist(artistId, page, fromImage=True)

            if fromBookmark and self.originalArtist is None:
                self.originalArtist = PixivArtist(page=page, fromImage=True)
            else:
                self.originalArtist = self.artist

            # parse image
            self.ParseInfo(parsed)

    def ParseInfo(self, page):
        self.imageUrls = list()
        images = page.findAll("div", attrs={"class":"illust-zoom-in thumbnail-container"})

        if len(images) > 0:
            for image in images:
                url = image["data-original-src"]
                self.imageUrls.append(url)

            self.imageCount = len(self.imageUrls)
            if self.imageCount == 1:
                self.imageMode = "big"
            elif self.imageCount > 1:
                self.imageMode = "manga"
        else:
            # ugoira
            canvas = page.find("div", attrs={"class":"ugoira player-container"})
            self.imageMode = "ugoira_view"
            url = self.ParseUgoira(canvas["data-ugoira-meta"])
            self.imageUrls.append(url)

        # title/caption
        self.imageTitle = page.findAll("div", attrs={"class":"title-container"})[0].text
        descriptions = page.findAll("div", attrs={"class":"description-text ui-expander-target"})
        if len(descriptions) > 0:
            self.imageCaption = descriptions[0].text

        # view count
        self.jd_rtv = int(page.find(attrs={'class': 'react-count'}).text)
        # like count
        # react-count _clickable illust-bookmark-count-59521621 count like-count
        self.jd_rtc = int(page.find(attrs={'class': re.compile(r"react-count _clickable illust-bookmark-count-{0} count like-count.*".format(self.imageId))}).text)
        # not available
        self.jd_rtt = self.jd_rtc

        # tags
        self.imageTags = list()
        # _tag-container tags illust-59521621
        tagContainer = page.find("div", attrs={"class":"_tag-container tags illust-{0}".format(self.imageId)})
        # special node for R-18
        r18Tag = page.findAll(attrs={'class': 'tag r-18'})
        if r18Tag is not None and len(r18Tag) > 0:
            self.imageTags.append("R-18")
        tagLinks = tagContainer.findAll("a", attrs={"class": re.compile(r"tag.*")})
        for link in tagLinks:
            self.imageTags.append(link["data-activity-tag_name"])

        # date
        self.worksDate = page.find("li", attrs={"class":"datetime"}).text
        self.worksDateDateTime = PixivHelper.ParseDateTime(self.worksDate, self.dateFormat)

        # resolution

        # tools
        tools = page.findAll("li", attrs={"class" : "tool"})
        t = list()
        for tool in tools:
            t.append(tool.text)
        if len(t) > 0:
            self.worksTools = ", ".join(t)

    def ParseImages(self, page, mode=None, _br=None):
        pass

    def ParseUgoira(self, page):
        # preserve the order
        js = json.loads(page, object_pairs_hook=OrderedDict)
        self.imageCount = 1

        # modify the structure to old version
        temp = js["frames"]
        js["frames"] = list()
        for key, value in temp.items():
            js["frames"].append(value)

        # convert to full screen url
        # ugoira600x600.zip ==> ugoira1920x1080.zip
        # js["src_low"] = js["src"]
        js["src"] = js["src"].replace("ugoira600x600.zip", "ugoira1920x1080.zip")

        # need to be minified
        self.ugoira_data = json.dumps(js, separators=(',',':'))#).replace("/", r"\/")

        return js["src"]


class PixivTags(PixivModel.PixivTags):
    __re_imageItemClass = re.compile(r"item-container _work-item-container.*")

    def parseMemberTags(self, artist, memberId, query=""):
        '''process artist result and return the image list'''
        self.itemList = list()
        self.memberId = memberId
        self.query = query
        self.haveImage = artist.haveImages
        self.isLastPage = artist.isLastPage
        for image in artist.imageList:
            self.itemList.append(PixivModel.PixivTagsItem(int(image), 0, 0))


    def parseTags(self, page, query=""):
        payload = json.loads(page)
        self.query = query

        # check error
        if payload["error"] == True:
            raise PixivException('Image Error: ' + payload["message"], errorCode=PixivException.SERVER_ERROR)

        # parse image information
        parsed = BeautifulSoup(payload["body"]["html"])
        self.itemList = list()
        images = parsed.findAll("div", attrs={"class": self.__re_imageItemClass})
        for item in images:
            thumbnail_container = item.find("div", attrs={"class":"thumbnail-container"})
            image_details = thumbnail_container.find("a", attrs={"class":"_work-modal-target user-activity"})
            image_id = image_details["data-work-id"]

            # like count
            status_container = thumbnail_container.find("div", attrs={"class":"status-container"})
            bookmarkCount = status_container.text

            imageResponse = 0
            self.itemList.append(PixivModel.PixivTagsItem(int(image_id), int(bookmarkCount), int(imageResponse)))

        if len(self.itemList) > 0:
            self.haveImage = True
        else:
            self.haveImage = False

        # search page info
        self.availableImages = int(payload["body"]["total"])
        if len(payload["body"]["next_url"]) > 0:
            self.isLastPage = False
        else:
            self.isLastPage = True

        return self.itemList
