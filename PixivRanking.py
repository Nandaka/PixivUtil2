import json


class PixivRanking:
    mode = ""
    curr_page = 0
    next_page = None
    prev_page = None
    curr_date = ""
    next_date = None
    prev_date = None
    rank_total = 0
    contents = list()
    filters = None

    def __init__(self, js_str, filters):
        js_data = json.loads(js_str)
        self.mode = js_data["mode"]
        self.curr_date = js_data["date"]
        self.next_date = js_data["next_date"]
        self.prev_date = js_data["prev_date"]
        self.curr_page = js_data["page"]
        self.next_page = js_data["next"]
        self.prev_page = js_data["prev"]
        self.rank_total = js_data["rank_total"]
        self.contents = js_data["contents"]
        self.filters = filters

        if self.filters is not None:
            self.filter_contents()

    def filter_contents(self):
        for content in self.contents:
            for filter_str in self.filters:
                if content["illust_content_type"][filter_str]:
                    self.contents.remove(content)
                    break
