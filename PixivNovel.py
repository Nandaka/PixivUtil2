import codecs
import json

import PixivHelper
from PixivException import PixivException

MAX_LIMIT = 10


class PixivNovel:
    novel_id = 0
    novel_json_str = ""
    content = ""
    title = ""

    def __init__(self, novel_id, novel_json) -> None:
        self.novel_id = novel_id
        self.novel_json_str = novel_json
        self.parse()

    def parse(self):
        js = json.loads(self.novel_json_str)
        if js["error"]:
            raise PixivException("Cannot get novel details",
                                 errorCode=PixivException.UNKNOWN_IMAGE_ERROR,
                                 htmlPage=self.novel_json_str)

        self.title = js["body"]["title"]
        self.content = js["body"]["content"]

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
            content_str = template_str.replace("%title%", self.title)
            content_str = content_str.replace("%novel_json_str%", self.novel_json_str)
            fh.write(content_str)
            fh.close()


class NovelSeries:
    series_id = 0
    series_str = ""
    series_list = list()
    series_list_str = dict()
    total = 0

    def __init__(self, series_id, series_json) -> None:
        self.series_id = series_id
        self.series_str = series_json

        self.parse()

    def parse(self):
        js = json.loads(self.series_str)
        if js["error"]:
            raise PixivException("Cannot get novel series content details",
                                 errorCode=PixivException.UNKNOWN_IMAGE_ERROR,
                                 htmlPage=self.series_str)
        self.total = js["body"]["total"]

    def parse_series_content(self, page_info, current_page):
        js = json.loads(page_info)
        if js["error"]:
            raise PixivException("Cannot get novel series content details",
                                 errorCode=PixivException.UNKNOWN_IMAGE_ERROR,
                                 htmlPage=page_info)

        self.series_list.extend(js["body"]["seriesContents"])
        self.series_list_str[current_page] = page_info
