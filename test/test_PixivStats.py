#!C:/Python37-32/python
# -*- coding: UTF-8 -*-

import json
import unittest

import common.PixivConstant as PixivConstant
from common.PixivConfig import PixivConfig
from model.PixivImage import PixivImage
from PixivDBManager import PixivDBManager

PixivConstant.PIXIVUTIL_LOG_FILE = 'pixivutil.test.log'


class TestPixivStatsParsing(unittest.TestCase):
    def testParseStatsFromPayload(self):
        with open('./test_data/test-image-info-32039274.json', 'r', encoding="utf-8") as p:
            body = json.load(p)["body"]

        image = PixivImage()
        image.imageId = 32039274
        image.ParseInfo(body, False)

        # jd_rtv == viewCount, jd_rtc == likeCount
        self.assertEqual(image.jd_rtv, 378894)
        self.assertEqual(image.jd_rtc, 23694)
        self.assertEqual(image.bookmark_count, 23229)
        self.assertEqual(image.comment_count, 74)
        self.assertEqual(image.image_response_count, 0)


class TestPixivStatsConfig(unittest.TestCase):
    def testAutoAddStatsDefaultsToFalse(self):
        config = PixivConfig()
        self.assertFalse(config.autoAddStats)


class TestPixivStatsPersistence(unittest.TestCase):
    def setUp(self):
        self.db = PixivDBManager(root_directory=".", target=":memory:")
        self.db.createDatabase()

    def tearDown(self):
        self.db.close()

    def testInsertAndSelectRoundtrip(self):
        self.db.insertStats(32039274, 378894, 23694, 23229, 74, 0)
        result = self.db.selectStatsByImageId(32039274)
        self.assertEqual(result, (378894, 23694, 23229, 74, 0))

    def testSelectMissingReturnsNone(self):
        self.assertIsNone(self.db.selectStatsByImageId(999999999))

    def testReinsertUpdatesSnapshot(self):
        self.db.insertStats(32039274, 100, 10, 5, 1, 0)
        self.db.insertStats(32039274, 378894, 23694, 23229, 74, 0)
        result = self.db.selectStatsByImageId(32039274)
        self.assertEqual(result, (378894, 23694, 23229, 74, 0))


if __name__ == '__main__':
    unittest.main()
