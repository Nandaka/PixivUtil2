#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-


import sys
import os
import unittest

from bs4 import BeautifulSoup
import json

import PixivHelper
from PixivModelWhiteCube import PixivImage, PixivArtist
from PixivException import PixivException


class TestPixivModel_WhiteCube(unittest.TestCase):
    currPath = str(os.path.abspath('.'))
    PixivHelper.GetLogger()

    def testParseLoginForm(self):
        p = open('./test/pixiv-whitecube-main.html', 'r')
        page = BeautifulSoup(p.read(), features='lxml')
        init_config = page.find('input', attrs={'id': 'init-config'})
        js_init_config = json.loads(init_config['value'])
        self.assertIsNotNone(js_init_config)
        self.assertIsNotNone(js_init_config["pixiv.context.token"])

##    @pytest.mark.xfail
##    def testParseImage(self):
##        p = open('./test/work_details_modal_whitecube.json', 'r')
##        image = PixivImage(59521621, p.read())
##        self.assertIsNotNone(image)
##        image.PrintInfo()
##        self.assertEqual(image.imageMode, "big")
##
##    @pytest.mark.xfail
##    def testParseManga(self):
##        p = open('./test/work_details_modal_whitecube-manga.json', 'r')
##        image = PixivImage(59532028, p.read())
##        self.assertIsNotNone(image)
##        image.PrintInfo()
##        self.assertEqual(image.imageMode, "manga")

    def testParseMemberError(self):
        p = open('./test/ajax-error.json', 'r')
        try:
            member = PixivArtist(14095911, p.read())
            self.fail("Exception expected.")
        except Exception as ex:
            self.assertTrue(ex.errorCode == PixivException.OTHER_MEMBER_ERROR)

    def testParseMemberImages(self):
        p = open('./test/all-14095911.json', 'r')
        member = PixivArtist(14095911, p.read(), False, 0, 24)
        self.assertIsNotNone(member)
        p2 = open('./test/userdetail-14095911.json', 'r')
        info = json.loads(p2.read())
        member.ParseInfo(info, False, False)

        member.PrintInfo()
        self.assertEqual(member.artistId, 14095911)
        self.assertTrue(member.haveImages)
        self.assertFalse(member.isLastPage)
        self.assertEqual(member.artistToken, 'p199451')
        self.assertGreater(member.totalImages, 70)
        self.assertEqual(member.artistAvatar, "https://i.pximg.net/user-profile/img/2018/02/01/23/55/46/13768317_dc1474fef3dc982ade71c1b2dbf32d9e.png")

    def testParseMemberImages2(self):
        p = open('./test/all-26357.json', 'r')
        member = PixivArtist(26357, p.read(), False, 0, 24)
        self.assertIsNotNone(member)
        p2 = open('./test/userdetail-26357.json', 'r')
        info = json.loads(p2.read())
        member.ParseInfo(info, False, False)

        member.PrintInfo()
        self.assertEqual(member.artistId, 26357)
        self.assertTrue(member.haveImages)
        self.assertFalse(member.isLastPage)
        self.assertEqual(member.artistToken, 'yukimaruko')
        self.assertGreater(member.totalImages, 7)
        self.assertEqual(member.artistAvatar, "https://s.pximg.net/common/images/no_profile.png")

    # https://www.pixiv.net/ajax/user/14095911/profile/all
    def testParseMemberImagesLastPage(self):
        p = open('./test/all-14095911.json', 'r')
        member = PixivArtist(14095911, p.read(), False, 96, 48)
        self.assertIsNotNone(member)
        p2 = open('./test/userdetail-14095911.json', 'r')
        info = json.loads(p2.read())
        member.ParseInfo(info, False, False)

        member.PrintInfo()
        self.assertEqual(member.artistId, 14095911)
        self.assertEqual(member.totalImages, 143)
        self.assertTrue(member.haveImages)
        self.assertTrue(member.isLastPage)

    # /ajax/user/14095911/illustmanga/tag?tag=R-18&offset=0&limit=48
    def testParseMemberImagesByTags(self):
        p = open('./test/tag-R-18-14095911.json', 'r')
        member = PixivArtist(14095911, p.read(), False, 0, 24)
        self.assertIsNotNone(member)
        p2 = open('./test/userdetail-14095911.json', 'r')
        info = json.loads(p2.read())
        member.ParseInfo(info, False, False)

        member.PrintInfo()
        self.assertEqual(member.artistId, 14095911)
        self.assertTrue(member.haveImages)
        self.assertFalse(member.isLastPage)

    # /ajax/user/14095911/illustmanga/tag?tag=R-18&offset=48&limit=48
    def testParseMemberImagesByTagsLastPage(self):
        p = open('./test/tag-R-18-14095911-lastpage.json', 'r')
        member = PixivArtist(14095911, p.read(), False, 48, 24)
        self.assertIsNotNone(member)
        p2 = open('./test/userdetail-14095911.json', 'r')
        info = json.loads(p2.read())
        member.ParseInfo(info, False, False)

        member.PrintInfo()
        self.assertEqual(member.artistId, 14095911)
        self.assertTrue(member.haveImages)
        self.assertTrue(member.isLastPage)

    def testParseMemberBookmarksByTags(self):
        p = open('./test/bookmarks-1039353.json', 'r')
        member = PixivArtist(1039353, p.read(), False, 0, 24)
        self.assertIsNotNone(member)
        p2 = open('./test/userdetail-1039353.json', 'r')
        info = json.loads(p2.read())
        member.ParseInfo(info, False, True)

        member.PrintInfo()
        self.assertEqual(member.artistId, 1039353)
        self.assertTrue(member.haveImages)
        self.assertFalse(member.isLastPage)

if __name__ == '__main__':
        # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivModel_WhiteCube)
    unittest.TextTestRunner(verbosity=5).run(suite)
