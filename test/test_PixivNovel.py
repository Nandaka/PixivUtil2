# -*- coding: UTF-8 -*-

import json
import os
import tempfile
import unittest

import common.PixivConstant as PixivConstant
from model.PixivNovel import PixivNovel, cover_urls

PixivConstant.PIXIVUTIL_LOG_FILE = 'pixivutil.test.log'


def novel_json(content="text", x_restrict=0, tags=("tag",), embedded=None,
               cover="https://i.pximg.net/c/600x600/novel-cover-master/img/2026/01/02/03/04/05/ci123_abc_master1200.jpg"):
    return json.dumps({
        "error": False,
        "message": "",
        "body": {
            "id": "123",
            "title": "Title",
            "content": content,
            "userId": "456",
            "bookmarkCount": 0,
            "imageResponseCount": 0,
            "seriesNavData": None,
            "isOriginal": False,
            "isBungei": False,
            "language": "ja",
            "xRestrict": x_restrict,
            "createDate": "2026-01-02T03:04:05+09:00",
            "uploadDate": "2026-01-02T03:04:05+09:00",
            "tags": {"tags": [{"tag": t} for t in tags]},
            "coverUrl": cover,
            "textEmbeddedImages": embedded or {},
        },
    })


class TestPixivNovel(unittest.TestCase):

    def testRestrictionFromXRestrict(self):
        # pixiv does not always tag an R-18 novel R-18; %R-18% reads the tags
        self.assertIn("R-18", PixivNovel(123, novel_json(x_restrict=1)).imageTags)
        self.assertIn("R-18G", PixivNovel(123, novel_json(x_restrict=2)).imageTags)
        self.assertNotIn("R-18", PixivNovel(123, novel_json(x_restrict=0)).imageTags)
        tagged = PixivNovel(123, novel_json(x_restrict=1, tags=("R-18",)))
        self.assertEqual(tagged.imageTags.count("R-18"), 1)

    def testImagesInText(self):
        embedded = {"25974400": {"novelImageId": "25974400", "sl": "2",
                                 "urls": {"original": "https://i.pximg.net/novel-cover-original/img/x/tei1_a.jpg",
                                          "480mw": "https://i.pximg.net/c/480x960/x.jpg"}}}
        novel = PixivNovel(123, novel_json(
            content="a\n[uploadedimage:25974400]\n[pixivimage:111]\n[pixivimage:222-3]\n[pixivimage:111]",
            embedded=embedded))
        self.assertEqual(novel.embeddedImages,
                         {"25974400": "https://i.pximg.net/novel-cover-original/img/x/tei1_a.jpg"})
        self.assertEqual(novel.pixivImages, [("111", 1), ("222", 3)])
        self.assertTrue(novel.coverUrl.endswith("ci123_abc_master1200.jpg"))

    def testCoverUrls(self):
        given = "https://i.pximg.net/c/600x600/novel-cover-master/img/2026/01/02/03/04/05/ci123_abc_master1200.jpg"
        self.assertEqual(cover_urls(given), [
            "https://i.pximg.net/novel-cover-original/img/2026/01/02/03/04/05/ci123_abc.jpg",
            "https://i.pximg.net/novel-cover-original/img/2026/01/02/03/04/05/ci123_abc.png",
            "https://i.pximg.net/novel-cover-master/img/2026/01/02/03/04/05/ci123_abc_master1200.jpg",
            given])
        self.assertEqual(cover_urls(""), [])
        self.assertEqual(cover_urls("https://example.com/a.jpg"), ["https://example.com/a.jpg"])

    def testWriteContentEmbedsImages(self):
        novel = PixivNovel(123, novel_json(content="end of </script> here"))
        novel.images = {"cover": "data:image/jpeg;base64,AAAA"}
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "novel.html")
            novel.write_content(target)
            with open(target, encoding="utf-8") as f:
                page = f.read()
        self.assertIn('images = {"cover": "data:image/jpeg;base64,AAAA"};', page)
        self.assertNotIn("%novel_images_json%", page)
        # the text cannot close the script the data sits in
        self.assertNotIn("end of </script>", page)
        self.assertIn("end of <\\/script>", page)
        self.assertIn('<html data-theme="light">', page)

    def testWriteContentDarkTheme(self):
        novel = PixivNovel(123, novel_json())
        novel.theme = "dark"
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "novel.html")
            novel.write_content(target)
            with open(target, encoding="utf-8") as f:
                page = f.read()
        self.assertIn('<html data-theme="dark">', page)
        self.assertNotIn("%novel_theme%", page)


if __name__ == '__main__':
    unittest.main()
