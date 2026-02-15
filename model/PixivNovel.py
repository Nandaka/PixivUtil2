import codecs
import json
from datetime import datetime
import common.datetime_z as datetime_z

import common.PixivHelper as PixivHelper
from common.PixivException import PixivException
from model.PixivImage import PixivTagData

MAX_LIMIT = 10


class PixivNovel:

    def __init__(self, novel_id, novel_json, tzInfo=None, dateFormat=None) -> None:
        self.novel_id = self.imageId = novel_id
        self.novel_json_str = novel_json
        self.content = ""

        # compatibility
        self.artist = None
        self.artist_id = 0
        self.imageTitle = ""
        self.worksDate = ""
        self.worksDateDateTime = datetime.fromordinal(1)
        self.imageTags = None
        self.tags = None
        self.bookmark_count = 0
        self.image_response_count = 0

        # series info
        self.seriesNavData = None
        self.seriesId = 0
        self.seriesOrder = 0

        # novel specific
        self.isOriginal = False
        self.isBungei = False
        self.language = ""
        self.xRestrict = False
        self.uploadDate = datetime.fromordinal(1)

        # doesn't apply
        self.worksResolution = ""
        self.imageMode = "Novel"

        self._tzInfo = tzInfo
        self.dateFormat = dateFormat
        self.parse()

    def parse(self):
        js = json.loads(self.novel_json_str)
        if js["error"]:
            raise PixivException("Cannot get novel details",
                                 errorCode=PixivException.UNKNOWN_IMAGE_ERROR,
                                 htmlPage=self.novel_json_str)

        root = js["body"]

        self.imageTitle = root["title"]
        self.content = root["content"]
        self.artist_id = root["userId"]
        self.bookmark_count = root["bookmarkCount"]
        self.image_response_count = root["imageResponseCount"]
        self.seriesNavData = root["seriesNavData"]
        if root["seriesNavData"] is not None:
            self.seriesId = root["seriesNavData"]["seriesId"]
            self.seriesOrder = root["seriesNavData"]["order"]
        self.isOriginal = root["isOriginal"]
        self.isBungei = root["isBungei"]
        self.language = root["language"]
        self.xRestrict = root["xRestrict"]

        # datetime
        self.worksDateDateTime = datetime_z.parse_datetime(root["createDate"])
        self.uploadDate = datetime_z.parse_datetime(root["uploadDate"])
        self.js_createDate = root["createDate"]  # store for json file
        if self._tzInfo is not None:
            self.worksDateDateTime = self.worksDateDateTime.astimezone(self._tzInfo)
            self.uploadDate = self.uploadDate.astimezone(self._tzInfo)

        tempDateFormat = self.dateFormat or "%Y-%m-%d"     # 2018-07-22, else configured in config.ini
        self.worksDate = self.worksDateDateTime.strftime(tempDateFormat)

        # tags
        self.imageTags = list()
        self.tags = list()
        tags = root["tags"]
        if tags is not None:
            tags = root["tags"]["tags"]
            for tag in tags:
                self.imageTags.append(tag["tag"])
                self.tags.append(PixivTagData(tag["tag"], tag))

        # append original tag
        if root["isOriginal"]:
            self.imageTags.append("オリジナル")
            tag = {"tag": "オリジナル",
                        "locked": True,
                        "deletable": False,
                        "userId": "",
                        "romaji": "original",
                        "translation": {
                            "en": "original"
                        }
                   }
            self.tags.append(PixivTagData(tag["tag"], tag))

    def write_content(self, filename):
        ft = open("novel_template.html")
        template_str = ft.read()
        ft.close()

        fh = None
        try:
            PixivHelper.makeSubdirs(filename)
            fh = codecs.open(filename, 'wb', encoding='utf-8')
        except IOError:
            fh = codecs.open(str(self.novel_id) + ".html", 'wb', encoding='utf-8')
            PixivHelper.get_logger().exception("Error when saving novel: %s, file is saved to: %s.html", filename, str(self.novel_id))

        if fh is not None:
            content_str = template_str.replace("%title%", self.imageTitle)
            content_str = content_str.replace("%novel_json_str%", self.novel_json_str)
            fh.write(content_str)
            fh.close()


class NovelSeries:

    def __init__(self, series_id, series_json) -> None:
        self.series_id = series_id
        self.series_str = series_json
        self.series_list = list()
        self.series_list_str = dict()
        self.total = 0
        self.series_name = ""

        self.parse()

    def parse(self):
        js = json.loads(self.series_str)
        if js["error"]:
            raise PixivException("Cannot get novel series content details",
                                 errorCode=PixivException.UNKNOWN_IMAGE_ERROR,
                                 htmlPage=self.series_str)
        # from publishedContentCount or total or displaySeriesContentCount ????
        self.total = js["body"]["total"]
        self.series_name = js["body"]["title"]

    def parse_series_content(self, page_info, current_page):
        js = json.loads(page_info)
        if js["error"]:
            raise PixivException("Cannot get novel series content details",
                                 errorCode=PixivException.UNKNOWN_IMAGE_ERROR,
                                 htmlPage=page_info)

        self.series_list.extend(js["body"]["page"]["seriesContents"])
        self.series_list_str[current_page] = page_info
