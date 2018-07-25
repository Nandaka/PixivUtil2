#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-
from __future__ import print_function

import sys
import os
import unittest

from BeautifulSoup import BeautifulSoup
import json
import pytest

import PixivHelper
from PixivModelWhiteCube import PixivImage, PixivArtist


class TestPixivModel_WhiteCube(unittest.TestCase):
    currPath = unicode(os.path.abspath('.'))
    PixivHelper.GetLogger()

    def testParseLoginForm(self):
        p = open('./test/pixiv-whitecube-main.html', 'r')
        page = BeautifulSoup(p.read())
        init_config = page.find('input', attrs={'id': 'init-config'})
        js_init_config = json.loads(init_config['value'])
        self.assertIsNotNone(js_init_config)
        self.assertIsNotNone(js_init_config["pixiv.context.token"])

    @pytest.mark.xfail
    def testParseImage(self):
        p = open('./test/work_details_modal_whitecube.json', 'r')
        image = PixivImage(59521621, p.read())
        self.assertIsNotNone(image)
        image.PrintInfo()
        self.assertEqual(image.imageMode, "big")

    @pytest.mark.xfail
    def testParseManga(self):
        p = open('./test/work_details_modal_whitecube-manga.json', 'r')
        image = PixivImage(59532028, p.read())
        self.assertIsNotNone(image)
        image.PrintInfo()
        self.assertEqual(image.imageMode, "manga")


if __name__ == '__main__':
        # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivModel_WhiteCube)
    unittest.TextTestRunner(verbosity=5).run(suite)
