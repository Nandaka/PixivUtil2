# -*- coding: utf-8 -*-
import codecs
import collections
import json
import os
import re
import shutil
import urllib
import zipfile
from collections import OrderedDict
from datetime import datetime
from typing import List, Tuple

import demjson3
from bs4 import BeautifulSoup

import datetime_z
import PixivHelper
from PixivArtist import PixivArtist
from PixivException import PixivException


class PixivTagData(object):
    tag = ""
    romaji = None
    translation_data = None

    def __init__(self, tag, tag_node):
        super().__init__()
        self.tag = tag
        if tag_node is not None:
            if "romaji" in tag_node:
                self.romaji = tag_node["romaji"]
            else:
                self.romaji = tag.lower()
            if "translation" in tag_node:
                self.translation_data = tag_node["translation"]
        else:
            self.romaji = tag.lower()

    def get_translation(self, locale="en"):
        if self.translation_data is not None:
            if locale in self.translation_data:
                return self.translation_data[locale]
        return self.tag


class PixivImage (object):
    '''Class for parsing image page, including manga page and big image.'''
    artist = None
    originalArtist = None
    imageId = 0
    imageTitle = ""
    imageCaption = ""
    imageTags = []
    imageMode = ""
    imageUrls = []
    imageResizedUrls = []
    worksDate = ""
    worksResolution = ""
    seriesNavData = ""
    rawJSON = {}
    jd_rtv = 0
    jd_rtc = 0
    # jd_rtt = 0
    imageCount = 0
    fromBookmark = False
    worksDateDateTime = datetime.fromordinal(1)
    js_createDate = None
    bookmark_count = -1
    image_response_count = -1
    ugoira_data = ""
    dateFormat = None
    descriptionUrlList = []
    __re_caption = re.compile("caption")
    _tzInfo = None
    tags = list()

    # only applicable for manga series
    manga_series_order: int = -1
    manga_series_parent = None

    # Issue #1064 titleCaptionTranslation
    translated_work_title = ""
    translated_work_caption = ""

    def __init__(self,
                 iid=0,
                 page=None,
                 parent=None,
                 fromBookmark=False,
                 bookmark_count=-1,
                 image_response_count=-1,
                 dateFormat=None,
                 tzInfo=None,
                 manga_series_order=-1,
                 manga_series_parent=None,
                 writeRawJSON=False,
                 stripHTMLTagsFromCaption=False):
        self.artist = parent
        self.fromBookmark = fromBookmark
        self.bookmark_count = bookmark_count
        self.imageId = iid
        self.imageUrls = []
        self.imageResizedUrls = []
        self.dateFormat = dateFormat
        self.descriptionUrlList = []
        self._tzInfo = tzInfo
        self.tags = list()
        self.stripHTMLTagsFromCaption = stripHTMLTagsFromCaption
        # only for manga series
        self.manga_series_order = manga_series_order
        self.manga_series_parent = manga_series_parent

        self.translated_work_title = ""
        self.translated_work_caption = ""

        if page is not None:

            # Issue #556
            payload = self.parseJs(page)

            # check error
            if payload is None:
                parsed = BeautifulSoup(page, features="html5lib")
                if self.IsNotLoggedIn(parsed):
                    raise PixivException('Not Logged In!', errorCode=PixivException.NOT_LOGGED_IN, htmlPage=page)
                if self.IsNeedPermission(parsed):
                    raise PixivException('Not in MyPick List, Need Permission!', errorCode=PixivException.NOT_IN_MYPICK, htmlPage=page)
                if self.IsNeedAppropriateLevel(parsed):
                    raise PixivException('Public works can not be viewed by the appropriate level!',
                                         errorCode=PixivException.NO_APPROPRIATE_LEVEL, htmlPage=page)
                if self.IsDeleted(parsed):
                    raise PixivException('Image not found/already deleted!', errorCode=PixivException.IMAGE_DELETED, htmlPage=page)
                if self.IsGuroDisabled(parsed):
                    raise PixivException('Image is disabled for under 18, check your setting page (R-18/R-18G)!',
                                         errorCode=PixivException.R_18_DISABLED, htmlPage=page)
                # detect if there is any other error
                errorMessage = self.IsErrorExist(parsed)
                if errorMessage is not None:
                    raise PixivException('Image Error: ' + str(errorMessage), errorCode=PixivException.UNKNOWN_IMAGE_ERROR, htmlPage=page)
                # detect if there is server error
                errorMessage = self.IsServerErrorExist(parsed)
                if errorMessage is not None:
                    raise PixivException('Image Error: ' + str(errorMessage), errorCode=PixivException.SERVER_ERROR, htmlPage=page)
                parsed.decompose()
                del parsed

            # parse artist information
            if parent is None:
                temp_artist_id = list(payload["user"].keys())[0]
                self.artist = PixivArtist(temp_artist_id, page, fromImage=True)

            if fromBookmark and self.originalArtist is None:
                assert(self.artist is not None)
                self.originalArtist = PixivArtist(page=page, fromImage=True)
                print("From Artist Bookmark: {0}".format(self.artist.artistId))
                print("Original Artist: {0}".format(self.originalArtist.artistId))
            else:
                self.originalArtist = self.artist

            # parse image
            self.ParseInfo(payload, writeRawJSON)

    def ParseInfo(self, page, writeRawJSON):
        key = list(page["illust"].keys())[0]
        assert(str(key) == str(self.imageId))
        root = page["illust"][key]
        # save the JSON if writeRawJSON is enabled
        if writeRawJSON:
            self.rawJSON = root

        self.imageUrls = list()
        self.imageResizedUrls = list()

        self.imageCount = int(root["pageCount"])
        temp_url = root["urls"]["original"]
        temp_resized_url = root["urls"]["regular"]
        if self.imageCount == 1:
            if temp_url.find("ugoira") > 0:
                # ugoira mode
                self.imageMode = "ugoira_view"
                # https://i.pximg.net/img-zip-ugoira/img/2018/04/22/00/01/06/68339821_ugoira600x600.zip 1920x1080
                # https://i.pximg.net/img-original/img/2018/04/22/00/01/06/68339821_ugoira0.jpg
                # https://i.pximg.net/img-original/img/2018/04/22/00/01/06/68339821_ugoira0.png
                # Fix Issue #372
                temp_url_ori = temp_url.replace("/img-original/", "/img-zip-ugoira/")
                temp_url_ori = temp_url_ori.split("_ugoira0")[0]
                temp_url_ori = temp_url_ori + "_ugoira1920x1080.zip"
                self.imageUrls.append(temp_url_ori)

                temp_resized_url = temp_url.replace("/img-original/", "/img-zip-ugoira/")
                temp_resized_url = temp_resized_url.split("_ugoira0")[0]
                temp_resized_url = temp_resized_url + "_ugoira600x600.zip"
                self.imageResizedUrls.append(temp_resized_url)
            else:
                # single page image
                self.imageMode = "big"
                self.imageUrls.append(temp_url)
                self.imageResizedUrls.append(temp_resized_url)
        elif self.imageCount > 1:
            # multi-page images
            self.imageMode = "manga"
            for i in range(0, self.imageCount):
                url = temp_url.replace("_p0", "_p{0}".format(i))
                self.imageUrls.append(url)
                resized_url = temp_resized_url.replace("_p0", "_p{0}".format(i))
                self.imageResizedUrls.append(resized_url)

        # title/caption
        self.imageTitle = root["illustTitle"]
        self.imageCaption = root["illustComment"]
        # Series
        self.seriesNavData = root["seriesNavData"]
        # view count
        self.jd_rtv = root["viewCount"]
        # like count
        self.jd_rtc = root["likeCount"]
        # not available anymore
        self.jd_rtt = self.jd_rtc

        # tags
        self.imageTags = list()
        tags = root["tags"]
        if tags is not None:
            tags = root["tags"]["tags"]
            for tag in tags:
                self.imageTags.append(tag["tag"])

                # 701
                self.tags.append(PixivTagData(tag["tag"], tag))

        # datetime, in utc
        # "createDate" : "2018-06-08T15:00:04+00:00",
        self.worksDateDateTime = datetime_z.parse_datetime(root["createDate"])
        self.js_createDate = root["createDate"]  # store for json file
        # Issue #420
        if self._tzInfo is not None:
            self.worksDateDateTime = self.worksDateDateTime.astimezone(self._tzInfo)

        tempDateFormat = self.dateFormat or "%Y-%m-%d"     # 2018-07-22, else configured in config.ini
        self.worksDate = self.worksDateDateTime.strftime(tempDateFormat)

        # resolution
        self.worksResolution = "{0}x{1}".format(root["width"], root["height"])
        if self.imageCount > 1:
            self.worksResolution = "Multiple images: {0}P".format(self.imageCount)

        self.bookmark_count = root["bookmarkCount"]
        self.image_response_count = root["responseCount"]

        # Issue 421
        self.parse_url_from_caption(self.imageCaption)

        # Strip HTML tags from caption once they have been collected by the above statement.
        if self.stripHTMLTagsFromCaption:
            self.imageCaption = BeautifulSoup(self.imageCaption, "lxml").text

        # Issue #1064
        if "titleCaptionTranslation" in root:
            if "workTitle" in root["titleCaptionTranslation"] and \
               root["titleCaptionTranslation"]["workTitle"] is not None and \
               len(root["titleCaptionTranslation"]["workTitle"]) > 0:
                self.translated_work_title = root["titleCaptionTranslation"]["workTitle"]
            if "workCaption" in root["titleCaptionTranslation"] and \
               root["titleCaptionTranslation"]["workCaption"] is not None and \
               len(root["titleCaptionTranslation"]["workCaption"]) > 0:
                self.translated_work_caption = root["titleCaptionTranslation"]["workCaption"]
                self.parse_url_from_caption(self.translated_work_caption)
                if self.stripHTMLTagsFromCaption:
                    self.translated_work_caption = BeautifulSoup(self.translated_work_caption, "lxml").text

    def parse_url_from_caption(self, caption_to_parse):
        parsed = BeautifulSoup(caption_to_parse, features="html5lib")
        links = parsed.findAll('a')
        if links is not None and len(links) > 0:
            for link in links:
                link_str = link["href"]
                # "/jump.php?http%3A%2F%2Farsenixc.deviantart.com%2Fart%2FWatchmaker-house-567480110"
                if link_str.startswith("/jump.php?"):
                    link_str = link_str[10:]
                    link_str = urllib.parse.unquote(link_str)

                if link_str not in self.descriptionUrlList:
                    self.descriptionUrlList.append(link_str)
        parsed.decompose()
        del parsed

    def ParseUgoira(self, page):
        # preserve the order
        js = json.loads(page, object_pairs_hook=OrderedDict)
        self.imageCount = 1
        js = js["body"]

        # convert to full screen url
        # ugoira600x600.zip ==> ugoira1920x1080.zip
        # js["src_low"] = js["src"]
        js["src"] = js["src"].replace("ugoira600x600.zip", "ugoira1920x1080.zip")

        # need to be minified
        self.ugoira_data = json.dumps(js, separators=(',', ':'))  # ).replace("/", r"\/")

        assert(len(self.ugoira_data) > 0)
        return js["src"]

    def IsNotLoggedIn(self, page):
        check = page.findAll('a', attrs={'class': 'signup_button'})
        if check is not None and len(check) > 0:
            return True
        check = page.findAll('a', attrs={'class': 'ui-button _signup'})
        if check is not None and len(check) > 0:
            return True
        return False

    def IsNeedAppropriateLevel(self, page):
        errorMessages = ['該当作品の公開レベルにより閲覧できません。']
        return PixivHelper.have_strings(page, errorMessages)

    def IsNeedPermission(self, page):
        errorMessages = ['この作品は.+さんのマイピクにのみ公開されています|この作品は、.+さんのマイピクにのみ公開されています',
                         'This work is viewable only for users who are in .+\'s My pixiv list',
                         'Only .+\'s My pixiv list can view this.',
                         '<section class="restricted-content">']
        return PixivHelper.have_strings(page, errorMessages)

    def IsDeleted(self, page):
        errorMessages = ['該当イラストは削除されたか、存在しないイラストIDです。|該当作品は削除されたか、存在しない作品IDです。',
                         'この作品は削除されました。',
                         'The following work is either deleted, or the ID does not exist.',
                         'This work was deleted.',
                         'Work has been deleted or the ID does not exist.']
        return PixivHelper.have_strings(page, errorMessages)

    def IsGuroDisabled(self, page):
        errorMessages = ['表示されるページには、18歳未満の方には不適切な表現内容が含まれています。',
                         'The page you are trying to access contains content that may be unsuitable for minors']
        return PixivHelper.have_strings(page, errorMessages)

    def IsErrorExist(self, page):
        check = page.findAll('span', attrs={'class': 'error'})
        if len(check) > 0:
            check2 = check[0].findAll('strong')
            if len(check2) > 0:
                return check2[0].renderContents()
        check = page.findAll('div', attrs={'class': '_unit error-unit'})
        if len(check) > 0:
            check2 = check[0].findAll('p', attrs={'class': 'error-message'})
            if len(check2) > 0:
                return check2[0].renderContents()
        return None

    def IsServerErrorExist(self, page):
        check = page.findAll('div', attrs={'class': 'errorArea'})
        if len(check) > 0:
            check2 = check[0].findAll('h2')
            if len(check2) > 0:
                return check2[0].renderContents()
        return None

    def PrintInfo(self):
        PixivHelper.safePrint('Image Info')
        PixivHelper.safePrint('img id: ' + str(self.imageId))
        PixivHelper.safePrint('title : ' + self.imageTitle)
        PixivHelper.safePrint('caption : ' + self.imageCaption)
        PixivHelper.safePrint('mode  : ' + self.imageMode)
        PixivHelper.safePrint('tags  :', newline=False)
        PixivHelper.safePrint(', '.join(self.imageTags))
        PixivHelper.safePrint('views : ' + str(self.jd_rtv))
        PixivHelper.safePrint('rating: ' + str(self.jd_rtc))
        # PixivHelper.safePrint('total : ' + str(self.jd_rtt))
        PixivHelper.safePrint('Date : ' + self.worksDate)
        PixivHelper.safePrint('Resolution : ' + self.worksResolution)
        return ""

    def ParseBookmarkDetails(self, page):
        if page is None:
            raise PixivException('No page given', errorCode=PixivException.NO_PAGE_GIVEN)
        try:
            countUl = page.findAll('ul', attrs={'class': 'count-list'})
            if countUl is not None and len(countUl) > 0:
                countA = countUl[0].findAll('a')
                if countA is not None and len(countA) > 0:
                    for a in countA:
                        if "bookmark-count" in a["class"]:
                            self.bookmark_count = int(a.text)
                        elif "image-response-count" in a["class"]:
                            self.image_response_count = int(a.text)
                    return
            # no bookmark count
            self.bookmark_count = 0
            self.image_response_count = 0
        except BaseException:
            PixivHelper.get_logger().exception("Cannot parse bookmark count for: %d", self.imageId)

    def WriteInfo(self, filename):
        info = None
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)

            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".txt", 'wb', encoding='utf-8')
            PixivHelper.get_logger().exception("Error when saving image info: %s, file is saved to: %s.txt", filename, str(self.imageId))

        info.write(f"ArtistID      = {self.artist.artistId}\r\n")
        info.write(f"ArtistName    = {self.artist.artistName}\r\n")
        info.write(f"ImageID       = {self.imageId}\r\n")
        info.write(f"Title         = {self.imageTitle}\r\n")
        if self.seriesNavData:
            info.write(f"SeriesTitle   = {self.seriesNavData['title']}\r\n")
            info.write(f"SeriesOrder   = {self.seriesNavData['order']}\r\n")
            info.write(f"SeriesId      = {self.seriesNavData['seriesId']}\r\n")
        info.write(f"Caption       = {self.imageCaption}\r\n")
        info.write(f"Tags          = {', '.join(self.imageTags)}\r\n")
        info.write(f"Image Mode    = {self.imageMode}\r\n")
        info.write(f"Pages         = {self.imageCount}\r\n")
        info.write(f"Date          = {self.worksDateDateTime}\r\n")
        info.write(f"Resolution    = {self.worksResolution}\r\n")
        info.write(f"BookmarkCount = {self.bookmark_count}\r\n")
        info.write(f"Link          = http://www.pixiv.net/en/artworks/{self.imageId}\r\n")
        if self.ugoira_data:
            info.write(f"Ugoira Data   = {self.ugoira_data}\r\n")
        if len(self.descriptionUrlList) > 0:
            info.write("Urls          =\r\n")
            for link in self.descriptionUrlList:
                info.write(f" - {link}\r\n")
        # Issue #1064
        if len(self.translated_work_title) > 0:
            info.write(f"Translated Title   = {self.translated_work_title}\r\n")
        if len(self.translated_work_caption) > 0:
            info.write(f"Translated Caption = {self.translated_work_caption}\r\n")

        info.close()

    def WriteJSON(self, filename, JSONfilter):
        info = None
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)
            info = codecs.open(filename, 'w', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".json", 'w', encoding='utf-8')
            PixivHelper.get_logger().exception("Error when saving image info: %s, file is saved to: %s.json", filename, self.imageId)
        if self.rawJSON:
            jsonInfo = self.rawJSON
            if JSONfilter:
                for x in JSONfilter.split(","):
                    del jsonInfo[x.strip()]
            if self.ugoira_data:
                jsonInfo["Ugoira Data"] = self.ugoira_data
            info.write(json.dumps(jsonInfo, ensure_ascii=False, indent=4))
            info.close()
        else:
            # Fix Issue #481
            jsonInfo = collections.OrderedDict()
            jsonInfo["Artist ID"] = self.artist.artistId
            jsonInfo["Artist Name"] = self.artist.artistName
            jsonInfo["Image ID"] = self.imageId
            if self.seriesNavData:
                jsonInfo["Series Data"] = self.seriesNavData
            jsonInfo["Title"] = self.imageTitle
            jsonInfo["Caption"] = self.imageCaption
            jsonInfo["Tags"] = self.imageTags
            jsonInfo["Image Mode"] = self.imageMode
            jsonInfo["Pages"] = self.imageCount
            jsonInfo["Date"] = self.js_createDate
            jsonInfo["Resolution"] = self.worksResolution
            jsonInfo["BookmarkCount"] = self.bookmark_count
            jsonInfo["Link"] = f"https://www.pixiv.net/en/artworks/{self.imageId}"
            if self.ugoira_data:
                jsonInfo["Ugoira Data"] = self.ugoira_data
            if len(self.descriptionUrlList) > 0:
                jsonInfo["Urls"] = self.descriptionUrlList
            # Issue #1064
            jsonInfo["titleCaptionTranslation"] = {"workTitle": self.translated_work_title, "workCaption": self.translated_work_caption}
            info.write(json.dumps(jsonInfo, ensure_ascii=False, indent=4))
            info.close()

    def WriteXMP(self, filename):
        import pyexiv2
        import tempfile

        # need to use temp file due to bad unicode support for pyexiv2 in windows
        d = tempfile.mkdtemp(prefix="xmp")
        d = d.replace(os.sep, '/')
        tempname = f"{d}/{self.imageId}.xmp"

        info = codecs.open(tempname, 'wb', encoding='utf-8')

        # Create the XMP file template.
        info.write('<?xpacket begin="" id=""?>\n<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 4.4.0-Exiv2">\n</x:xmpmeta>\n<?xpacket end="w"?>\n')
        info.close()

        # Reopen file using pyexiv2
        # newer version e.g. pyexiv2-2.7.0
        info = pyexiv2.Image(tempname)
        info_dict = info.read_xmp()
        info_dict['Xmp.dc.creator'] = [self.artist.artistName]
        # Check array isn't empty.
        if self.imageTitle:
            info_dict['Xmp.dc.title'] = self.imageTitle
        # Check array isn't empty.
        if self.imageCaption:
            info_dict['Xmp.dc.description'] = self.imageCaption
        # Check array isn't empty.
        if self.imageTags:
            info_dict['Xmp.dc.subject'] = self.imageTags
        info_dict['Xmp.dc.date'] = [self.worksDateDateTime]
        info_dict['Xmp.dc.source'] = f"http://www.pixiv.net/en/artworks/{self.imageId}"
        info_dict['Xmp.dc.identifier'] = self.imageId

        # Custom 'pixiv' namespace for non-standard details.
        pyexiv2.registerNs('http://pixiv.com/', 'pixiv')

        info_dict['Xmp.pixiv.artist_id'] = self.artist.artistId
        info_dict['Xmp.pixiv.image_mode'] = self.imageMode
        info_dict['Xmp.pixiv.pages'] = self.imageCount
        info_dict['Xmp.pixiv.resolution'] = self.worksResolution
        info_dict['Xmp.pixiv.bookmark_count'] = self.bookmark_count

        if self.seriesNavData:
            info_dict['Xmp.pixiv.series_title'] = self.seriesNavData['title']
            info_dict['Xmp.pixiv.series_order'] = self.seriesNavData['order']
            info_dict['Xmp.pixiv.series_id'] = self.seriesNavData['seriesId']
        if self.ugoira_data:
            info_dict['Xmp.pixiv.ugoira_data'] = self.ugoira_data
        if len(self.descriptionUrlList) > 0:
            info_dict['Xmp.pixiv.urls'] = ", ".join(self.descriptionUrlList)
        # Issue #1064
        if len(self.translated_work_title) > 0:
            info_dict['Xmp.pixiv.translated_work_title'] = self.translated_work_title
        if len(self.translated_work_caption) > 0:
            info_dict['Xmp.pixiv.translated_work_caption'] = self.translated_work_caption
        info.modify_xmp(info_dict)
        info.close()

        # rename to actual file
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)
            shutil.move(tempname, filename)
        except IOError:
            shutil.move(tempname, f"{self.imageId}.xmp")
            PixivHelper.get_logger().exception("Error when saving image info: %s, file is saved to: %s.xmp", filename, str(self.imageId))

    def WriteSeriesData(self, seriesId, seriesDownloaded, filename):
        from PixivBrowserFactory import getBrowser
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)
            outfile = codecs.open(filename, 'w', encoding='utf-8')
        except IOError:
            outfile = codecs.open("Series " + str(seriesId) + ".json", 'w', encoding='utf-8')
            PixivHelper.get_logger().exception("Error when saving image info: %s, file is saved to: %s.json", filename, "Series " + str(seriesId) + ".json")
        receivedJSON = json.loads(getBrowser().getMangaSeries(seriesId, 1, returnJSON=True))
        jsondata = receivedJSON["body"]["illustSeries"][0]
        jsondata.update(receivedJSON["body"]["page"])
        pages = jsondata["total"] // 12 + 2
        for x in range(2, pages):
            receivedJSON = json.loads(getBrowser().getMangaSeries(seriesId, x, returnJSON=True))
            jsondata["series"].extend(receivedJSON["body"]["page"]["series"])
        for x in ["recentUpdatedWorkIds", "otherSeriesId", "seriesId", "isSetCover", "firstIllustId", "coverImageSl", "url"]:
            del jsondata[x]
        outfile.write(json.dumps(jsondata, ensure_ascii=False))
        outfile.close()
        seriesDownloaded.append(seriesId)

    def WriteUgoiraData(self, filename):
        info = None
        try:
            # Issue #421 ensure subdir exists.
            PixivHelper.makeSubdirs(filename)
            info = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            info = codecs.open(str(self.imageId) + ".js", 'wb', encoding='utf-8')
            PixivHelper.get_logger().exception("Error when saving image info: %s, file is saved to: %d.js", filename, self.imageId)
        info.write(str(self.ugoira_data))
        info.close()

    def create_ugoira(self, filename) -> bool:
        if len(self.ugoira_data) == 0:
            PixivHelper.get_logger().exception("Missing ugoira animation info for image: %d", self.imageId)

        zipTarget = filename[:-4] + ".ugoira"
        if os.path.exists(zipTarget):
            os.remove(zipTarget)

        shutil.copyfile(filename, zipTarget)
        zipSize = os.stat(filename).st_size
        jsStr = self.ugoira_data[:-1] + r',"zipSize":' + str(zipSize) + r'}'
        with zipfile.ZipFile(zipTarget, mode="a") as z:
            z.writestr("animation.json", jsStr)
        return True

    def parseJs(self, page):
        parsed = BeautifulSoup(page, features="html5lib")
        jss = parsed.find('meta', attrs={'id': 'meta-preload-data'})

        # cleanup
        parsed.decompose()
        del parsed

        if jss is None or len(jss["content"]) == 0:
            return None  # Possibly error page

        payload = demjson3.decode(jss["content"])
        return payload


class PixivMangaSeries:
    manga_series_id: int = 0
    member_id: int = 0
    pages_with_order: List[Tuple[int, int]] = []
    current_page: int = 0
    total_works: int = 0
    title: str = ""
    description: str = ""
    is_last_page = False

    # object data
    artist: PixivArtist = None
    images: List[PixivImage] = []

    def __init__(self, manga_series_id: int, current_page: int, payload: str):
        self.manga_series_id = manga_series_id
        self.current_page = current_page

        if payload is not None:
            js = json.loads(payload)

            if js["error"]:
                raise PixivException(message=js["message"], errorCode=PixivException.OTHER_ERROR, htmlPage=payload)
            self.parse_info(js["body"])

    def parse_info(self, payload):
        self.title = payload["extraData"]["meta"]["title"]
        self.description = payload["extraData"]["meta"]["description"]
        self.total_works = payload["page"]["total"]

        # possible to get multiple artists, not supported yet
        # for now just take the first artist.
        if len(payload["users"]) > 1:
            raise PixivException(f"Multiple artist detected in manga series: {self.manga_series_id}", errorCode=PixivException.OTHER_ERROR, htmlPage=payload)
        self.member_id = payload["users"][0]["userId"]

        for work_id in payload["page"]["series"]:
            self.pages_with_order.append((work_id["workId"], work_id["order"]))
            if int(work_id["order"]) == 1:
                self.is_last_page = True

    def print_info(self):
        works_per_page = 12
        PixivHelper.safePrint('Manga Series Info')
        PixivHelper.safePrint(f'Manga Series ID: {self.manga_series_id}')
        PixivHelper.safePrint(f'Artist ID      : {self.member_id}')
        if self.artist is not None:
            PixivHelper.safePrint(f'Artist Name    : {self.artist.artistName}')
        PixivHelper.safePrint(f'Title          : {self.title}')
        PixivHelper.safePrint(f'Description    : {self.description}')
        PixivHelper.safePrint(f'Pages          : {self.current_page} of {int(self.total_works/works_per_page)}')
        PixivHelper.safePrint('Works          :')
        for (work_id, order) in self.pages_with_order:
            PixivHelper.safePrint(f' - [{order}] {work_id}')
