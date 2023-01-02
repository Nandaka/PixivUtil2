#!C:/Python37-32/python
# -*- coding: UTF-8 -*-

import unittest

from bs4 import BeautifulSoup

import PixivConstant
# import PixivHelper
from PixivArtist import PixivArtist
from PixivBookmark import PixivBookmark, PixivNewIllustBookmark
from PixivBrowserFactory import PixivBrowser
from PixivException import PixivException
from PixivGroup import PixivGroup
from PixivImage import PixivImage
from PixivTags import PixivTags

PixivConstant.PIXIVUTIL_LOG_FILE = 'pixivutil.test.log'
last_page = 52


# class MockPixivBrowser(PixivBrowser):
#     mode = None

#     def __init__(self, mode):
#         self.mode = mode

#     def getPixivPage(self, url, referer="https://www.pixiv.net", returnParsed=True):
#         if self.mode == 1:
#             p = open('./test/test-image-big-single.html', 'r', encoding="utf-8")
#             page = BeautifulSoup(p.read(), features="html5lib")
#             return page
#         else:
#             # fake the manga page
#             pageNo = url.split("=")[-1]
#             p = open('./test/test-image-parsemanga-big-' + pageNo + '.htm', 'r', encoding="utf-8")
#             page = BeautifulSoup(p.read(), features="html5lib")
#             return page


class TestPixivArtist(unittest.TestCase):
    # def testPixivArtistNoImage(self):
    #     # print('\nTesting member page - no image')
    #     p = open('./test/test-noimage.htm', 'r', encoding="utf-8")
    #     page = p.read()
    #     with self.assertRaises(PixivException):
    #         member = PixivArtist(1233, page, 0, 48, 0)
    #         # print(member.imageList)

    def testPixivArtistNoMember(self):
        # print('\nTesting member page - no member')
        p = open('./test/test-nouser.htm', 'r', encoding="utf-8")
        page = p.read()
        with self.assertRaises(PixivException):
            PixivArtist(1, page)

    # def testPixivArtistSuspended(self):
    #     # print('\nTesting member page - suspended member')
    #     p = open('./test/test-member-suspended.htm', 'r', encoding="utf-8")
    #     page = BeautifulSoup(p.read())
    #     with self.assertRaises(PixivException) as ex:
    #         PixivArtist(123, page)
    #     self.assertEqual(ex.exception.errorCode, 1002)
    #     page.decompose()
    #     del page

    #    def testPixivArtistNotLoggedIn(self):
    #        p = open('./test/test-member-nologin.htm', 'r', encoding="utf-8")
    #        page = BeautifulSoup(p.read())
    #        with self.assertRaises(PixivException) as ex:
    #            PixivArtist(143229, page)
    #        self.assertEqual(ex.exception.errorCode, 100)
    #        page.decompose()
    #        del page

    # def testPixivArtistServerError(self):
    #     # print('\nTesting member page')
    #     p = open('./test/test-server-error.html', 'r', encoding="utf-8")
    #     page = BeautifulSoup(p.read())
    #     with self.assertRaises(PixivException) as ex:
    #         artist = PixivArtist(234753, page)
    #     self.assertEqual(ex.exception.errorCode, PixivException.SERVER_ERROR)
    #     page.decompose()
    #     del page

    # def testPixivArtistManageSelf(self):
    #     # print('\nTesting own page ')
    #     p = open('./test/test-member-self.htm', 'r', encoding="utf-8")
    #     page = BeautifulSoup(p.read())
    #     artist = PixivArtist(189816, page)

    #     page.decompose()
    #     del page

    #     # no artist information for manage self page.
    #     self.assertNotEqual(artist, None)
    #     self.assertEqual(artist.artistId, 189816)
    #     # self.assertEqual(artist.artistToken, 'nandaka')
    #     self.assertGreaterEqual(artist.totalImages, 1)
    #     self.assertIn(65079382, artist.imageList)


class TestPixivImage(unittest.TestCase):
    def testPixivImageParseInfo(self):
        p = open('./test/test-image-info.html', 'r', encoding="utf-8")
        page = p.read()
        image2 = PixivImage(32039274, page, dateFormat='%Y-%m-%d %H:%M')

        self.assertEqual(image2.imageId, 32039274)
        self.assertEqual(image2.imageTitle, u"新しいお姫様")
        self.assertTrue(len(image2.imageCaption) > 0)
        # print(u"\r\nCaption = {0}".format(image2.imageCaption))

        self.assertTrue(u'MAYU' in image2.imageTags)
        self.assertTrue(u'VOCALOID' in image2.imageTags)
        self.assertTrue(u'VOCALOID3' in image2.imageTags)
        self.assertTrue(u'なにこれかわいい' in image2.imageTags)
        self.assertTrue(u'やはり存在する斧' in image2.imageTags)

        self.assertTrue(len(image2.tags) > 0)
        self.assertEqual(image2.tags[0].tag, "MAYU")
        self.assertEqual(image2.tags[0].romaji, "mayu")
        self.assertEqual(image2.tags[0].get_translation(locale="en"), "MAYU")
        self.assertEqual(image2.tags[3].tag, "なにこれかわいい")
        self.assertEqual(image2.tags[3].romaji, "nanikorekawaii")
        self.assertEqual(image2.tags[3].get_translation(locale="en"), "incredibly cute")

        self.assertEqual(image2.imageMode, "big")
        self.assertEqual(image2.worksDate, '2012-12-10 15:23')
        self.assertEqual(image2.worksResolution, '642x900')
        self.assertEqual(len(image2.imageUrls), 1)
        self.assertEqual(len(image2.imageResizedUrls), 1)

        self.assertEqual(image2.artist.artistToken, 'nardack')

    # def testPixivImageParseInfo2(self):
    #     p = open('./test/test-image-manga-69287623.htm', 'r', encoding="utf-8")
    #     page = p.read()
    #     image2 = PixivImage(69287623, page)

    #     self.assertEqual(image2.imageId, 69287623)
    #     self.assertEqual(image2.imageTitle, u"「ふふっ」漫画　その９")

    #     self.assertTrue(u'漫画' in image2.imageTags)

    #     self.assertEqual(image2.imageMode, "manga")
    #     self.assertEqual(image2.worksDate, '06/17/18 23:16')
    #     self.assertEqual(image2.worksResolution, 'Multiple images: 2P')
    #     self.assertEqual(image2.artist.artistToken, 'komesama')

#    def testPixivImageParseInfoJa(self):
#        p = open('./test/test-image-parse-image-40273739-ja.html', 'r', encoding="utf-8")
#        page = BeautifulSoup(p.read())
#        image2 = PixivImage(40273739, page)
#        page.decompose()
#        del page
#
#        self.assertEqual(image2.imageId, 40273739)
#        self.assertEqual(image2.imageTitle, u"Cos-Nurse")
#
#        self.assertTrue(u'東方' in image2.imageTags)
#        self.assertTrue(u'幽々子' in image2.imageTags)
#        self.assertTrue(u'むちむち' in image2.imageTags)
#        self.assertTrue(u'おっぱい' in image2.imageTags)
#        self.assertTrue(u'尻' in image2.imageTags)
#        self.assertTrue(u'東方グラマラス' in image2.imageTags)
#        self.assertTrue(u'誰だお前' in image2.imageTags)
#
#        self.assertEqual(image2.imageMode, "big")
#        self.assertEqual(image2.worksDate, u"2013年12月14日 19:00")
#        self.assertEqual(image2.worksResolution, '855x1133')
#        self.assertEqual(image2.worksTools, 'Photoshop SAI')
#        self.assertEqual(image2.artist.artistToken, 'k2321656')

    def testPixivImageParseInfoMixed(self):
        p = open('./test/test-image-info2.html', 'r', encoding="utf-8")
        page = p.read()
        image2 = PixivImage(67729319, page)

        # image2.PrintInfo()

        self.assertEqual(image2.imageId, 67729319)
        self.assertEqual(image2.imageTitle, u"独り言")
        self.assertTrue(len(image2.imageCaption) > 0)
        # print(u"\r\nCaption = {0}".format(image2.imageCaption))

        self.assertTrue(u'FGO' in image2.imageTags)
        self.assertTrue(u'ネロ・クラウディウス' in image2.imageTags)
        self.assertTrue(u'セイバー・ブライド' in image2.imageTags)

        self.assertEqual(image2.imageMode, "big")
        self.assertEqual(image2.worksDate, '2018-03-14')
        self.assertEqual(image2.worksResolution, '721x1200')
        self.assertEqual(image2.artist.artistToken, 'kawanocyan')

#    def testPixivImageParseInfoPixivPremiumOffer(self):
#        p = open('./test/test-image-parse-image-38826533-pixiv-premium.html', 'r', encoding="utf-8")
#        page = BeautifulSoup(p.read())
#        image2 = PixivImage(38826533, page)
#        page.decompose()
#        del page
#
#        self.assertEqual(image2.imageId, 38826533)
#        self.assertEqual(image2.imageTitle, u"てやり")
#        self.assertEqual(image2.imageCaption, u'一応シーダ様です。')
#
#        self.assertTrue(u'R-18' in image2.imageTags)
#        self.assertTrue(u'FE' in image2.imageTags)
#        self.assertTrue(u'ファイアーエムブレム' in image2.imageTags)
#        self.assertTrue(u'シーダ' in image2.imageTags)
#
#        self.assertEqual(image2.imageMode, "big")
#        self.assertEqual(image2.worksDate, '03/14/18 09:00')
#        self.assertEqual(image2.worksResolution, '1000x2317')
#        # self.assertEqual(image2.worksTools, 'CLIP STUDIO PAINT')
#        # self.assertEqual(image2.jd_rtv, 88190)
#        # self.assertEqual(image2.jd_rtc, 6711)
#        # self.assertEqual(image2.jd_rtt, 66470)
#        self.assertEqual(image2.artist.artistToken, 'hvcv')

    def testPixivImageNoAvatar(self):
        # print('\nTesting artist page without avatar image')
        p = open('./test/test-image-noavatar.htm', 'r', encoding="utf-8")
        page = p.read()
        image = PixivImage(20496355, page)

        # self.assertNotEqual(image, None)
        self.assertEqual(image.artist.artistToken, 'iymt')
        self.assertEqual(image.imageId, 20496355)
        # 07/22/2011 03:09｜512×600｜RETAS STUDIO&nbsp;
        # print(image.worksDate, image.worksResolution, image.worksTools)
        self.assertEqual(image.worksDate, '2011-07-21')
        self.assertEqual(image.worksResolution, '512x600')
        # self.assertEqual(image.worksTools, 'RETAS STUDIO')

    def testPixivImageParseTags(self):
        p = open('./test/test-image-parse-tags.htm', 'r', encoding="utf-8")
        page = p.read()
        image = PixivImage(11164869, page)

        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 11164869)
        self.assertEqual(image.worksDate, '2010-06-08')
        self.assertEqual(image.worksResolution, '1009x683')
        # self.assertEqual(image.worksTools, u'SAI')
        # print(image.imageTags)
        joinedResult = " ".join(image.imageTags)
        self.assertEqual(joinedResult.find("VOCALOID") > -1, True)

    def testPixivImageParseNoTags(self):
        p = open('./test/test-image-no_tags.htm', 'r', encoding="utf-8")
        page = p.read()
        image = PixivImage(9175987, page)

        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 9175987)
        self.assertEqual(image.worksDate, '2010-03-05')
        self.assertEqual(image.worksResolution, '1155x768')
        # self.assertEqual(image.worksTools, u'SAI')
        self.assertEqual(image.imageTags, [])

    def testPixivImageUnicode(self):
        # print('\nTesting image page - big')
        p = open('./test/test-image-unicode.htm', 'r', encoding="utf-8")
        page = p.read()
        image = PixivImage(2493913, page, dateFormat="%m/%d/%y %H:%M")

        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 2493913)
        self.assertEqual(image.imageMode, 'big')
        self.assertEqual(image.worksDate, '12/23/08 12:01')
        self.assertEqual(image.worksResolution, '852x1200')
        # print(image.worksTools)
        # self.assertEqual(image.worksTools, u'Photoshop SAI つけペン')

    def testPixivImageRateCount(self):
        p = open('./test/test-image-rate_count.htm', 'r', encoding="utf-8")
        page = p.read()
        image = PixivImage(28865189, page)

        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 28865189)
        self.assertEqual(image.imageMode, 'manga')
        self.assertTrue(image.jd_rtv > 0)
        self.assertTrue(image.jd_rtc > 0)
        # deprecated since 11-April-2017
        # self.assertTrue(image.jd_rtt > 0)
        # self.assertEqual(image.worksTools, "Photoshop")

    # def testPixivImageNoImage(self):
    #     # print('\nTesting image page - no image')
    #     p = open('./test/test-image-noimage.htm', 'r', encoding="utf-8")
    #     page = p.read()
    #     with self.assertRaises(PixivException):
    #         PixivImage(123, page)

    def testPixivImageDeleted(self):
        # print('\nTesting image page - deleted image')
        p = open('./test/test-image-deleted.htm', 'r', encoding="utf-8")
        page = p.read()
        with self.assertRaises(PixivException):
            PixivImage(123, page)

    def testPixivImageNoImageEng(self):
        # print('\nTesting image page - no image')
        p = open('./test/test-image-noimage-eng.htm', 'r', encoding="utf-8")
        page = p.read()
        with self.assertRaises(PixivException):
            PixivImage(123, page)

    def testPixivImageModeManga(self):
        # print('\nTesting image page - manga')
        p = open('./test/test-image-manga.htm', 'r', encoding="utf-8")
        page = p.read()
        image = PixivImage(28820443, page)

        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 28820443)
        self.assertEqual(image.imageMode, 'manga')

        self.assertEqual(len(image.imageUrls), 2)
        self.assertEqual(len(image.imageResizedUrls), 2)

    def testPixivImageParseMangaInfoMixed(self):
        # print('\nTesting parse Manga Images')
        # Issue #224
        p = open('./test/test-image-big-manga-mixed.html', 'r', encoding="utf-8")
        page = p.read()
        image = PixivImage(iid=67487303, page=page, dateFormat="%m/%d/%y %H:%M")
        # image.PrintInfo()

        self.assertTrue(u'R-18' in image.imageTags)
        self.assertTrue(u'Fate/EXTRA' in image.imageTags)
        self.assertTrue(u'ネロ・クラウディウス' in image.imageTags)
        self.assertTrue(u'腋' in image.imageTags)
        self.assertTrue(u'クリチラ' in image.imageTags)
        self.assertTrue(u'おっぱい' in image.imageTags)
        self.assertTrue(u'Fate/EXTRA_Last_Encore' in image.imageTags)

        self.assertEqual(image.imageMode, "manga")
        self.assertEqual(image.worksDate, '02/27/18 03:31')
        self.assertEqual(image.worksResolution, 'Multiple images: 2P')
        # self.assertEqual(image.worksTools, 'SAI')
        self.assertEqual(image.artist.artistToken, 's33127')

#    def testPixivImageParseMangaTwoPage(self):
#        # print('\nTesting parse Manga Images')
#        p = open('./test/test-image-manga-2page.htm', 'r', encoding="utf-8")
#        page = BeautifulSoup(p.read())
#        image = PixivImage()
#        urls = image.ParseImages(page, mode='manga')
#        # print(urls)
#        self.assertEqual(len(urls), 11)
#        self.assertEqual(len(urls), image.imageCount)
#        imageId = urls[0].split('/')[-1].split('.')[0]
#        # print('imageId:',imageId)
#        self.assertEqual(imageId, '46322053_p0')

#    def testPixivImageParseBig(self):
#        # print('\nTesting parse Big Image')
#        p = open('./test/test-image-unicode.htm', 'r', encoding="utf-8")
#        page = BeautifulSoup(p.read())
#        image = PixivImage(iid=2493913, page=page)
#        urls = image.imageUrls
#        self.assertEqual(len(urls), 1)
#        # print(urls[0])
#        imageId = urls[0].split('/')[-1].split('_')[0]
#        # print('imageId:',imageId)
#        self.assertEqual(int(imageId), 2493913)

#    def testPixivImageParseManga(self):
#        # print('\nTesting parse Manga Images')
#        p = open('./test/test-image-parsemanga.htm', 'r', encoding="utf-8")
#        page = BeautifulSoup(p.read())
#        image = PixivImage()
#        urls = image.ParseImages(page, mode='manga', _br=MockPixivBrowser(None))
#        # print(urls)
#        self.assertEqual(len(urls), 3)
#        self.assertEqual(len(urls), image.imageCount)
#        imageId = urls[0].split('/')[-1].split('.')[0]
#        # print('imageId:',imageId)
#        self.assertEqual(imageId, '46279245_p0')

#    def testPixivImageParseMangaBig(self):
#        # print('\nTesting parse Manga Images')
#        # Issue #224
#        p = open('./test/test-image-big-manga.html', 'r', encoding="utf-8")
#        page = BeautifulSoup(p.read())
#        image = PixivImage(iid=62670665)
#        image.ParseInfo(page)
#        urls = image.ParseImages(page, mode=image.imageMode, _br=MockPixivBrowser(1))
#        self.assertEqual(len(urls), 1)
#        # print(urls[0])
#        self.assertGreater(len(urls[0]), 0)
#        imageId = urls[0].split('/')[-1].split('_')[0]
#        # print('imageId:',imageId)
#        self.assertEqual(int(imageId), 62670665)

    def testPixivImageNoLogin(self):
        # print('\nTesting not logged in')
        p = open('./test/test-image-nologin.htm', 'r', encoding="utf-8")
        page = p.read()
        try:
            PixivImage(67089412, page)
            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, PixivException.NOT_LOGGED_IN)

    def testPixivImageServerError(self):
        # print('\nTesting image page')
        p = open('./test/test-server-error.html', 'r', encoding="utf-8")
        page = p.read()
        with self.assertRaises(PixivException) as ex:
            PixivImage(9138317, page)
        self.assertEqual(ex.exception.errorCode, PixivException.SERVER_ERROR)

    def testPixivImageServerError2(self):
        # print('\nTesting image page')
        p = open('./test/test-image-generic-error.html', 'r', encoding="utf-8")
        page = p.read()
        with self.assertRaises(PixivException) as ex:
            PixivImage(37882549, page)
        self.assertEqual(ex.exception.errorCode, PixivException.UNKNOWN_IMAGE_ERROR)

    def testPixivImageUgoira(self):
        # print('\nTesting image page')
        p = open('./test/test-image-ugoira.htm', 'r', encoding="utf-8")
        page = p.read()
        image = PixivImage(46281014, page)
        # print(image.imageUrls)
        self.assertTrue(image.imageUrls[0].find(".zip") > -1)
        self.assertTrue(image.imageResizedUrls[0].find(".zip") > -1)

    def testPixivImageParseInfoSelf(self):
        # assuming being accessed via manage page for your own artwork.
        p = open('./test/test-image-selfimage.htm', 'r', encoding="utf-8")
        page = p.read()
        image2 = PixivImage(65079382, page, dateFormat="%m/%d/%y %H:%M")

        self.assertEqual(image2.imageId, 65079382)
        self.assertEqual(image2.imageTitle, u"Test")
        self.assertTrue(len(image2.imageCaption) > 0)
        # print(u"\r\nCaption = {0}".format(image2.imageCaption))

        self.assertTrue(u'None' in image2.imageTags)

        self.assertEqual(image2.imageMode, "big")
        self.assertEqual(image2.worksDate, '09/22/17 02:29')
        self.assertEqual(image2.worksResolution, '946x305')


class TestPixivBookmark(unittest.TestCase):
    def testPixivBookmarkNewIlust(self):
        # print('\nTesting BookmarkNewIlust')
        p = open('./test/test-bookmarks_new_ilust.json', 'r', encoding="utf-8")
        # page = BeautifulSoup(p.read(), features="html5lib")
        page = p.read()
        result = PixivNewIllustBookmark(page)

        self.assertEqual(len(result.imageList), 60)

    def testPixivImageBookmark(self):
        # print('\nTesting PixivImageBookmark')
        p = open('./test/bookmarks.json', 'r', encoding="utf-8")
        page = p.read()
        (result, total) = PixivBookmark.parseImageBookmark(page)

        self.assertEqual(len(result), 19)
        self.assertTrue(35303260 in result)
        self.assertTrue(28629066 in result)
        self.assertTrue(27249307 in result)
        self.assertTrue(30119925 in result)

#    def testPixivImageBookmarkMember(self):
#        # print('\nTesting PixivImageBookmark')
#        p = open('./test/test-image-bookmark-member.htm', 'r', encoding="utf-8")
#        page = BeautifulSoup(p.read())
#        result = PixivBookmark.parseImageBookmark(page)
#
#        self.assertEqual(len(result), 20)
#        # self.assertTrue(51823321 in result)
#        # self.assertTrue(42934821 in result)
#        # self.assertTrue(44328684 in result)

# image already deleted
# class TestMyPickPage(unittest.TestCase):
#     def testMyPickPage(self):
#         try:
#             path = './test/test-image-my_pick.html'
#             p = open(path, 'r', encoding="utf-8")
#             page = p.read()
#             image = PixivImage(12467674, page)

#             self.assertRaises(PixivException)
#         except PixivException as ex:
#             self.assertEqual(ex.errorCode, 2004)

    # def testGuroPageEng(self):
    #     try:
    #         path = './test/test-image-guro-e.html'
    #         p = open(path, 'r', encoding="utf-8")
    #         page = BeautifulSoup(p.read())
    #         image = PixivImage(31111130, page)

    #         self.assertRaises(PixivException)
    #     except PixivException as ex:
    #         self.assertEqual(ex.errorCode, 2005)

    # def testEroPageEng(self):
    #     try:
    #         path = './test/test-image-ero-e.html'
    #         p = open(path, 'r', encoding="utf-8")
    #         page = BeautifulSoup(p.read())
    #         image = PixivImage(31115956, page)

    #         self.assertRaises(PixivException)
    #     except PixivException as ex:
    #         self.assertEqual(ex.errorCode, 2005)


class TestPixivTags(unittest.TestCase):
    def testTagsSearchExact1(self):
        path = './test/test-tags-search-exact2.htm'
        p = open(path, 'r', encoding="utf-8")
        response = p.read()
        tags = ''
        current_page = 1

        image = PixivTags()
        image.parseTags(response, tags, current_page)

        self.assertEqual(len(image.itemList), 60)
        self.assertEqual(image.isLastPage, False)
        self.assertEqual(image.availableImages, 2302)

    # tags.php?tag=%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B%21
    def testTagsSearchExact(self):
        path = './test/test-tags-search-exact.htm'
        p = open(path, 'r', encoding="utf-8")
        response = p.read()
        tags = ''
        current_page = 1

        image = PixivTags()
        image.parseTags(response, tags, current_page)

        self.assertEqual(len(image.itemList), 60)
        self.assertEqual(image.isLastPage, False)

    # search.php?word=%E5%88%9D%E6%98%A5%E9%A3%BE%E5%88%A9&s_mode=s_tag_full&order=date_d&p=70
    def testTagsSearchExactLast(self):
        path = './test/test-tags-search-exact-last.json'
        p = open(path, 'r', encoding="utf-8")
        response = p.read()
        tags = ''

        image = PixivTags()
        image.parseTags(response, tags, last_page)

        print(image.itemList[-1])
        self.assertEqual(image.isLastPage, True)
        self.assertEqual(image.itemList[-1].imageId, 740933)

    # /ajax/search/artworks/GuP or ガルパン or ガールズ%26パンツァー or garupan?word=GuP or ガルパン or ガールズ%26パンツァー or garupan&p=119&s_mode=s_tag&type=all&order=date_d
    def testTagsSearchPartialNotLast(self):
        path = './test/tag-not-last-page.json'
        p = open(path, 'r', encoding="utf-8")
        response = p.read()
        tags = ''

        image = PixivTags()
        image.parseTags(response, tags, last_page)

        print(image.itemList[-1])
        self.assertEqual(image.isLastPage, False)
        self.assertEqual(image.itemList[-1].imageId, 91248467)

    # search.php?s_mode=s_tag&word=%E5%88%9D%E6%98%A5%E9%A3%BE%E5%88%A9
    def testTagsSearchPartial(self):
        path = './test/test-tags-search-partial.htm'
        p = open(path, 'r', encoding="utf-8")
        response = p.read()
        tags = '%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B!'
        current_page = 1

        image = PixivTags()
        image.parseTags(response, tags, current_page)

        self.assertEqual(len(image.itemList), 60)
        self.assertEqual(image.isLastPage, False)

    def testTagsSearchPartialLast(self):
        path = './test/test-tags-search-partial-last.htm'
        p = open(path, 'r', encoding="utf-8")
        response = p.read()
        tags = '%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B!'
        current_page = 4

        image = PixivTags()
        image.parseTags(response, tags, current_page)

        self.assertEqual(image.itemList[-1].imageId, 15060554)
        self.assertEqual(image.isLastPage, True)

    def testTagsSearchParseDetails(self):
        path = './test/test-tags-search-exact-parse_details.htm'
        p = open(path, 'r', encoding="utf-8")
        response = p.read()
        tags = ''
        current_page = 1

        image = PixivTags()
        image.parseTags(response, tags, current_page)

        self.assertEqual(image.itemList[-1].imageId, 33815932)

#    def testTagsMemberSearch(self):
#        path = './test/test-tags-member-search.htm'
#        p = open(path, 'r', encoding="utf-8")
#        page = BeautifulSoup(p.read())
#        image = PixivTags()
#        image.parseMemberTags(page, 313631)
#
#        self.assertEqual(len(image.itemList), 40)
#        # self.assertEqual(image.itemList[0].imageId, 53977340)
#        # self.assertEqual(image.itemList[19].imageId, 45511597)
#        self.assertEqual(image.isLastPage, False)
#        self.assertEqual(image.availableImages, 73)

#    def testTagsMemberSearchLast(self):
#        path = './test/test-tags-member-search-last.htm'
#        p = open(path, 'r', encoding="utf-8")
#        page = BeautifulSoup(p.read())
#        image = PixivTags()
#        image.parseMemberTags(page, 313631)
#
#        # self.assertEqual(len(image.itemList), 10)
#        self.assertEqual(image.itemList[-1].imageId, 1804545)
#        self.assertEqual(image.isLastPage, True)

    def testTagsSkipShowcase(self):
        path = './test/test-tags-search-skip-showcase.htm'
        p = open(path, 'r', encoding="utf-8")
        response = p.read()
        tags = 'K-On!'
        current_page = 1

        image = PixivTags()
        image.parseTags(response, tags, current_page)

        self.assertEqual(len(image.itemList), 60)


class TestPixivGroup(unittest.TestCase):
    def testParseJson(self):
        path = './test/group.json'
        p = open(path)
        result = PixivGroup(p.read())

        self.assertEqual(len(result.imageList), 35)
        self.assertEqual(len(result.externalImageList), 1)
        self.assertEqual(result.maxId, 920234)


def main():
    test_classes_to_run = [TestPixivArtist, TestPixivImage, TestPixivBookmark, TestPixivTags, TestPixivGroup]
    # test_classes_to_run = [TestPixivImage]
    # test_classes_to_run = [TestPixivTags]
    # test_classes_to_run = [TestPixivArtist]
    # test_classes_to_run = [TestPixivBookmark]

    loader = unittest.TestLoader()

    suites_list = []
    for test_class in test_classes_to_run:
        suite = loader.loadTestsFromTestCase(test_class)
        suites_list.append(suite)

    big_suite = unittest.TestSuite(suites_list)

    runner = unittest.TextTestRunner(verbosity=5)
    results = runner.run(big_suite)
    return results


if __name__ == '__main__':
    main()
