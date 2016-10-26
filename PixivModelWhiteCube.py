# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302
import re
import json
from BeautifulSoup import BeautifulSoup

import PixivModel
from PixivModel import PixivException
import PixivHelper

class PixivArtist(PixivModel.PixivArtist):
    def __init__(self, mid=0, page=None, fromImage=False):
        if page is not None:
            payload = json.loads(page)

            # check error
            if payload["error"] == True:
                raise PixivException('Artist Error: ' + str(payload["error"]), errorCode=PixivException.SERVER_ERROR)

            # detect if image count != 0
            if not fromImage:
                self.ParseImages(payload)

            # parse artist info
            self.ParseInfo(payload, fromImage)


    def ParseInfo(self, page, fromImage=False):
        self.artistId = 0
        self.artistAvatar = "no_profile"
        self.artistToken = "self"
        self.artistName = "self"

        if page is not None:
            if fromImage:
                pass
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

                if page.has_key["profile"]:
                    self.totalImages = int(page["profile"]["total_illusts"])


    def ParseImages(self, page):
        self.imageList = list()
        for image in page["illusts"]:
            self.imageList.append(int(image["id"]))

        if page["next_url"] == None:
            self.isLastPage = True


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
            if self.artist is None:
                self.artist = PixivArtist(page=page, fromImage=True)

            # parse image
            self.ParseInfo(parsed)

    def ParseInfo(self, page):
        images = page.findAll("div", attrs={"class":"illust-zoom-in thumbnail-container"})
        for image in images:
            url = image["data-original-src"]
            self.imageUrls.append(url)

        if len(self.imageUrls) == 1:
            self.imageMode = "big"
            # TODO: handle ugoira
        elif len(self.imageUrls) > 1:
            self.imageMode = "manga"

        # title/caption
        self.imageTitle = page.findAll("div", attrs={"class":"title-container"})[0].text
        descriptions = page.findAll("div", attrs={"class":"description-text ui-expander-target"})
        if len(descriptions) > 0:
            self.imageCaption = descriptions[0].text

        # view count
        self.jd_rtv = int(page.find(attrs={'class': 'react-count'}).text)
        # like count
        # react-count _clickable illust-bookmark-count-59521621 count like-count
        self.jd_rtc = int(page.find(attrs={'class': "react-count _clickable illust-bookmark-count-{0} count like-count".format(self.imageId)}).text)
        # not available
        self.jd_rtt = self.jd_rtc

        # tags
        # _tag-container tags illust-59521621
        tagContainer = page.find("div", attrs={"class":"_tag-container tags illust-{0}".format(self.imageId)})
        tagLinks = tagContainer.findAll("a", attrs={"class": re.compile(r"tag.*")})
        for link in tagLinks:
            self.imageTags.append(link.text)

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

