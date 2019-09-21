#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-


from PixivModel import PixivArtist, PixivBookmark, PixivNewIllustBookmark, PixivTags, PixivGroup
from PixivModelWhiteCube import PixivImage
from PixivBrowserFactory import PixivBrowser
from PixivException import PixivException
import bs4
from mechanize import Browser
import os
import unittest

def as_soup(text):
    return bs4.BeautifulSoup(text, features='lxml')


class MockPixivBrowser(PixivBrowser):
    mode = None

    def __init__(self, mode):
        self.mode = mode
        pass

    def getPixivPage(self, url, referer="http://www.pixiv.net", errorPageName=None):
        if self.mode == 1:
            p = open('./test/test-image-big-single.html', 'r')
            page = as_soup(p.read())
            return page
        else:
            ''' fake the manga page '''
            pageNo = url.split("=")[-1]
            p = open('./test/test-image-parsemanga-big-' + pageNo + '.htm', 'r')
            page = as_soup(p.read())
            return page


class TestPixivArtist(unittest.TestCase):
    def testPixivArtistNoImage(self):
        # print('\nTesting member page - no image')
        p = open('./test/test-noimage.htm', 'r')
        page = as_soup(p.read())
        with self.assertRaises(PixivException):
            member = PixivArtist(1233, page)
            # print(member.imageList)
        page.decompose()
        del page

    def testPixivArtistNoMember(self):
        # print('\nTesting member page - no member')
        p = open('./test/test-nouser.htm', 'r')
        page = as_soup(p.read())
        with self.assertRaises(PixivException):
            PixivArtist(1, page)
        page.decompose()
        del page

    def testPixivArtistSuspended(self):
        # print('\nTesting member page - suspended member')
        p = open('./test/test-member-suspended.htm', 'r')
        page = as_soup(p.read())
        with self.assertRaises(PixivException) as ex:
            PixivArtist(123, page)
        self.assertEqual(ex.exception.errorCode, 1002)
        page.decompose()
        del page

##    def testPixivArtistNotLoggedIn(self):
##        p = open('./test/test-member-nologin.htm', 'r')
##        page = as_soup(p.read())
##        with self.assertRaises(PixivException) as ex:
##            PixivArtist(143229, page)
##        self.assertEqual(ex.exception.errorCode, 100)
##        page.decompose()
##        del page

    def testPixivArtistServerError(self):
        # print('\nTesting member page')
        p = open('./test/test-server-error.html', 'r')
        page = as_soup(p.read())
        with self.assertRaises(PixivException) as ex:
            artist = PixivArtist(234753, page)
        self.assertEqual(ex.exception.errorCode, PixivException.SERVER_ERROR)
        page.decompose()
        del page

    def testPixivArtistManageSelf(self):
        # print('\nTesting own page ')
        p = open('./test/test-member-self.htm', 'r')
        page = as_soup(p.read())
        artist = PixivArtist(189816, page)

        page.decompose()
        del page

        # no artist information for manage self page.
        self.assertNotEqual(artist, None)
        self.assertEqual(artist.artistId, 189816)
        # self.assertEqual(artist.artistToken, 'nandaka')
        self.assertGreaterEqual(artist.totalImages, 1)
        self.assertIn(65079382, artist.imageList)


class TestPixivImage(unittest.TestCase):
    def testPixivImageParseInfo(self):
        p = open('./test/test-image-info.html', 'r')
        page = as_soup(p.read())
        image2 = PixivImage(32039274, page)
        page.decompose()
        del page

        self.assertEqual(image2.imageId, 32039274)
        self.assertEqual(image2.imageTitle, "新しいお姫様")
        self.assertTrue(len(image2.imageCaption) > 0)
        # print(u"\r\nCaption = {0}".format(image2.imageCaption))

        self.assertTrue('MAYU' in image2.imageTags)
        self.assertTrue('VOCALOID' in image2.imageTags)
        self.assertTrue('VOCALOID3' in image2.imageTags)
        self.assertTrue('なにこれかわいい' in image2.imageTags)
        self.assertTrue('やはり存在する斧' in image2.imageTags)

        self.assertEqual(image2.imageMode, "big")
        self.assertEqual(image2.worksDate, '12/10/12 15:23')
        self.assertEqual(image2.worksResolution, '642x900')
        # self.assertEqual(image2.worksTools, 'Photoshop SAI')
        # self.assertEqual(image2.jd_rtv, 88190)
        # self.assertEqual(image2.jd_rtc, 6711)
        # self.assertEqual(image2.jd_rtt, 66470)
        self.assertEqual(image2.artist.artistToken, 'nardack')

    def testPixivImageParseInfo2(self):
        p = open('./test/test-image-manga-69287623.htm', 'r')
        page = as_soup(p.read())
        image2 = PixivImage(69287623, page)
        page.decompose()
        del page

        self.assertEqual(image2.imageId, 69287623)
        self.assertEqual(image2.imageTitle, "「ふふっ」漫画　その９")

        self.assertTrue('漫画' in image2.imageTags)

        self.assertEqual(image2.imageMode, "manga")
        self.assertEqual(image2.worksDate, '06/17/18 23:16')
        self.assertEqual(image2.worksResolution, 'Multiple images: 2P')
        self.assertEqual(image2.artist.artistToken, 'komesama')

##    def testPixivImageParseInfoJa(self):
##        p = open('./test/test-image-parse-image-40273739-ja.html', 'r')
##        page = as_soup(p.read())
##        image2 = PixivImage(40273739, page)
##        page.decompose()
##        del page
##
##        self.assertEqual(image2.imageId, 40273739)
##        self.assertEqual(image2.imageTitle, u"Cos-Nurse")
##
##        self.assertTrue(u'東方' in image2.imageTags)
##        self.assertTrue(u'幽々子' in image2.imageTags)
##        self.assertTrue(u'むちむち' in image2.imageTags)
##        self.assertTrue(u'おっぱい' in image2.imageTags)
##        self.assertTrue(u'尻' in image2.imageTags)
##        self.assertTrue(u'東方グラマラス' in image2.imageTags)
##        self.assertTrue(u'誰だお前' in image2.imageTags)
##
##        self.assertEqual(image2.imageMode, "big")
##        self.assertEqual(image2.worksDate, u"2013年12月14日 19:00")
##        self.assertEqual(image2.worksResolution, '855x1133')
##        self.assertEqual(image2.worksTools, 'Photoshop SAI')
##        self.assertEqual(image2.artist.artistToken, 'k2321656')

    def testPixivImageParseInfoMixed(self):
        p = open('./test/test-image-info2.html', 'r')
        page = as_soup(p.read())
        image2 = PixivImage(67729319, page)
        page.decompose()
        del page

        # image2.PrintInfo()

        self.assertEqual(image2.imageId, 67729319)
        self.assertEqual(image2.imageTitle, "独り言")
        self.assertTrue(len(image2.imageCaption) > 0)
        # print(u"\r\nCaption = {0}".format(image2.imageCaption))

        self.assertTrue('FGO' in image2.imageTags)
        self.assertTrue('ネロ・クラウディウス' in image2.imageTags)
        self.assertTrue('セイバー・ブライド' in image2.imageTags)

        self.assertEqual(image2.imageMode, "big")
        self.assertEqual(image2.worksDate, '03/14/18 09:00')
        self.assertEqual(image2.worksResolution, '721x1200')
        self.assertEqual(image2.artist.artistToken, 'kawanocyan')

##    def testPixivImageParseInfoPixivPremiumOffer(self):
##        p = open('./test/test-image-parse-image-38826533-pixiv-premium.html', 'r')
##        page = as_soup(p.read())
##        image2 = PixivImage(38826533, page)
##        page.decompose()
##        del page
##
##        self.assertEqual(image2.imageId, 38826533)
##        self.assertEqual(image2.imageTitle, u"てやり")
##        self.assertEqual(image2.imageCaption, u'一応シーダ様です。')
##
##        self.assertTrue(u'R-18' in image2.imageTags)
##        self.assertTrue(u'FE' in image2.imageTags)
##        self.assertTrue(u'ファイアーエムブレム' in image2.imageTags)
##        self.assertTrue(u'シーダ' in image2.imageTags)
##
##        self.assertEqual(image2.imageMode, "big")
##        self.assertEqual(image2.worksDate, '03/14/18 09:00')
##        self.assertEqual(image2.worksResolution, '1000x2317')
##        # self.assertEqual(image2.worksTools, 'CLIP STUDIO PAINT')
##        # self.assertEqual(image2.jd_rtv, 88190)
##        # self.assertEqual(image2.jd_rtc, 6711)
##        # self.assertEqual(image2.jd_rtt, 66470)
##        self.assertEqual(image2.artist.artistToken, 'hvcv')

    def testPixivImageNoAvatar(self):
        # print('\nTesting artist page without avatar image')
        p = open('./test/test-image-noavatar.htm', 'r')
        page = as_soup(p.read())
        image = PixivImage(20496355, page)
        page.decompose()
        del page
        # self.assertNotEqual(image, None)
        self.assertEqual(image.artist.artistToken, 'iymt')
        self.assertEqual(image.imageId, 20496355)
        # 07/22/2011 03:09｜512×600｜RETAS STUDIO&nbsp;
        # print(image.worksDate, image.worksResolution, image.worksTools)
        self.assertEqual(image.worksDate, '07/21/11 18:09')
        self.assertEqual(image.worksResolution, '512x600')
        # self.assertEqual(image.worksTools, 'RETAS STUDIO')

    def testPixivImageParseTags(self):
        p = open('./test/test-image-parse-tags.htm', 'r')
        page = as_soup(p.read())
        image = PixivImage(11164869, page)
        page.decompose()
        del page

        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 11164869)
        self.assertEqual(image.worksDate, '06/08/10 17:33')
        self.assertEqual(image.worksResolution, '1009x683')
        # self.assertEqual(image.worksTools, u'SAI')
        # print(image.imageTags)
        joinedResult = " ".join(image.imageTags)
        self.assertEqual(joinedResult.find("VOCALOID") > -1, True)

    def testPixivImageParseNoTags(self):
        p = open('./test/test-image-no_tags.htm', 'r')
        page = as_soup(p.read())
        image = PixivImage(9175987, page)
        page.decompose()
        del page

        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 9175987)
        self.assertEqual(image.worksDate, '03/05/10 18:04')
        self.assertEqual(image.worksResolution, '1155x768')
        # self.assertEqual(image.worksTools, u'SAI')
        self.assertEqual(image.imageTags, [])

    def testPixivImageUnicode(self):
        # print('\nTesting image page - big')
        p = open('./test/test-image-unicode.htm', 'r')
        page = as_soup(p.read())
        image = PixivImage(2493913, page)
        page.decompose()
        del page

        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 2493913)
        self.assertEqual(image.imageMode, 'big')
        self.assertEqual(image.worksDate, '12/23/08 12:01')
        self.assertEqual(image.worksResolution, '852x1200')
        # print(image.worksTools)
        # self.assertEqual(image.worksTools, u'Photoshop SAI つけペン')

    def testPixivImageRateCount(self):
        p = open('./test/test-image-rate_count.htm', 'r')
        page = as_soup(p.read())
        image = PixivImage(28865189, page)
        page.decompose()
        del page

        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 28865189)
        self.assertEqual(image.imageMode, 'manga')
        self.assertTrue(image.jd_rtv > 0)
        self.assertTrue(image.jd_rtc > 0)
        # deprecated since 11-April-2017
        # self.assertTrue(image.jd_rtt > 0)
        # self.assertEqual(image.worksTools, "Photoshop")

    def testPixivImageNoImage(self):
        # print('\nTesting image page - no image')
        p = open('./test/test-image-noimage.htm', 'r')
        page = as_soup(p.read())
        with self.assertRaises(PixivException):
            PixivImage(123, page)
        page.decompose()
        del page

    def testPixivImageDeleted(self):
        # print('\nTesting image page - deleted image')
        p = open('./test/test-image-deleted.htm', 'r')
        page = as_soup(p.read())
        with self.assertRaises(PixivException):
            PixivImage(123, page)
        page.decompose()
        del page

    def testPixivImageNoImageEng(self):
        # print('\nTesting image page - no image')
        p = open('./test/test-image-noimage-eng.htm', 'r')
        page = as_soup(p.read())
        with self.assertRaises(PixivException):
            PixivImage(123, page)
        page.decompose()
        del page

    def testPixivImageModeManga(self):
        # print('\nTesting image page - manga')
        p = open('./test/test-image-manga.htm', 'r')
        page = as_soup(p.read())
        image = PixivImage(28820443, page)
        page.decompose()
        del page

        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 28820443)
        self.assertEqual(image.imageMode, 'manga')

    def testPixivImageParseMangaInfoMixed(self):
        # print('\nTesting parse Manga Images')
        # Issue #224
        p = open('./test/test-image-big-manga-mixed.html', 'r')
        page = as_soup(p.read())
        image = PixivImage(iid=67487303, page=page)
        # image.PrintInfo()

        self.assertTrue('R-18' in image.imageTags)
        self.assertTrue('Fate/EXTRA' in image.imageTags)
        self.assertTrue('ネロ・クラウディウス' in image.imageTags)
        self.assertTrue('腋' in image.imageTags)
        self.assertTrue('クリチラ' in image.imageTags)
        self.assertTrue('おっぱい' in image.imageTags)
        self.assertTrue('Fate/EXTRA_Last_Encore' in image.imageTags)

        self.assertEqual(image.imageMode, "manga")
        self.assertEqual(image.worksDate, '02/27/18 03:31')
        self.assertEqual(image.worksResolution, 'Multiple images: 2P')
        # self.assertEqual(image.worksTools, 'SAI')
        self.assertEqual(image.artist.artistToken, 's33127')

##    def testPixivImageParseMangaTwoPage(self):
##        # print('\nTesting parse Manga Images')
##        p = open('./test/test-image-manga-2page.htm', 'r')
##        page = as_soup(p.read())
##        image = PixivImage()
##        urls = image.ParseImages(page, mode='manga')
##        # print(urls)
##        self.assertEqual(len(urls), 11)
##        self.assertEqual(len(urls), image.imageCount)
##        imageId = urls[0].split('/')[-1].split('.')[0]
##        # print('imageId:',imageId)
##        self.assertEqual(imageId, '46322053_p0')

##    def testPixivImageParseBig(self):
##        # print('\nTesting parse Big Image')
##        p = open('./test/test-image-unicode.htm', 'r')
##        page = as_soup(p.read())
##        image = PixivImage(iid=2493913, page=page)
##        urls = image.imageUrls
##        self.assertEqual(len(urls), 1)
##        # print(urls[0])
##        imageId = urls[0].split('/')[-1].split('_')[0]
##        # print('imageId:',imageId)
##        self.assertEqual(int(imageId), 2493913)

##    def testPixivImageParseManga(self):
##        # print('\nTesting parse Manga Images')
##        p = open('./test/test-image-parsemanga.htm', 'r')
##        page = as_soup(p.read())
##        image = PixivImage()
##        urls = image.ParseImages(page, mode='manga', _br=MockPixivBrowser(None))
##        # print(urls)
##        self.assertEqual(len(urls), 3)
##        self.assertEqual(len(urls), image.imageCount)
##        imageId = urls[0].split('/')[-1].split('.')[0]
##        # print('imageId:',imageId)
##        self.assertEqual(imageId, '46279245_p0')

##    def testPixivImageParseMangaBig(self):
##        # print('\nTesting parse Manga Images')
##        # Issue #224
##        p = open('./test/test-image-big-manga.html', 'r')
##        page = as_soup(p.read())
##        image = PixivImage(iid=62670665)
##        image.ParseInfo(page)
##        urls = image.ParseImages(page, mode=image.imageMode, _br=MockPixivBrowser(1))
##        self.assertEqual(len(urls), 1)
##        # print(urls[0])
##        self.assertGreater(len(urls[0]), 0)
##        imageId = urls[0].split('/')[-1].split('_')[0]
##        # print('imageId:',imageId)
##        self.assertEqual(int(imageId), 62670665)

    def testPixivImageNoLogin(self):
        # print('\nTesting not logged in')
        p = open('./test/test-image-nologin.htm', 'r')
        page = as_soup(p.read())
        try:
            image = PixivImage(9138317, page)
            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, PixivException.NOT_LOGGED_IN)

    def testPixivImageServerError(self):
        # print('\nTesting image page')
        p = open('./test/test-server-error.html', 'r')
        page = as_soup(p.read())
        with self.assertRaises(PixivException) as ex:
            image = PixivImage(9138317, page)
        self.assertEqual(ex.exception.errorCode, PixivException.SERVER_ERROR)
        page.decompose()
        del page

    def testPixivImageServerError2(self):
        # print('\nTesting image page')
        p = open('./test/test-image-generic-error.html', 'r')
        page = as_soup(p.read())
        with self.assertRaises(PixivException) as ex:
            image = PixivImage(37882549, page)
        self.assertEqual(ex.exception.errorCode, PixivException.UNKNOWN_IMAGE_ERROR)
        page.decompose()
        del page

    def testPixivImageUgoira(self):
        # print('\nTesting image page')
        p = open('./test/test-image-ugoira.htm', 'r')
        page = as_soup(p.read())
        image = PixivImage(46281014, page)
        urls = image.ParseImages(page)
        # print(image.imageUrls)
        self.assertTrue(image.imageUrls[0].find(".zip") > -1)
        page.decompose()
        del page

    def testPixivImageParseInfoSelf(self):
        # assuming being accessed via manage page for your own artwork.
        p = open('./test/test-image-selfimage.htm', 'r')
        page = as_soup(p.read())
        image2 = PixivImage(65079382, page)
        page.decompose()
        del page

        self.assertEqual(image2.imageId, 65079382)
        self.assertEqual(image2.imageTitle, "Test")
        self.assertTrue(len(image2.imageCaption) > 0)
        # print(u"\r\nCaption = {0}".format(image2.imageCaption))

        self.assertTrue('None' in image2.imageTags)

        self.assertEqual(image2.imageMode, "big")
        self.assertEqual(image2.worksDate, '09/22/17 02:29')
        self.assertEqual(image2.worksResolution, '946x305')


class TestPixivBookmark(unittest.TestCase):
    def testPixivBookmarkNewIlust(self):
        # print('\nTesting BookmarkNewIlust')
        p = open('./test/test-bookmarks_new_ilust.htm', 'r')
        page = as_soup(p.read())
        result = PixivNewIllustBookmark(page)

        self.assertEqual(len(result.imageList), 20)

    def testPixivImageBookmark(self):
        # print('\nTesting PixivImageBookmark')
        p = open('./test/test-image-bookmark.htm', 'r')
        page = as_soup(p.read())
        result = PixivBookmark.parseImageBookmark(page)

        self.assertEqual(len(result), 20)
        self.assertTrue(35303260 in result)
        self.assertTrue(28629066 in result)
        self.assertTrue(27249307 in result)
        self.assertTrue(30119925 in result)

##    def testPixivImageBookmarkMember(self):
##        # print('\nTesting PixivImageBookmark')
##        p = open('./test/test-image-bookmark-member.htm', 'r')
##        page = as_soup(p.read())
##        result = PixivBookmark.parseImageBookmark(page)
##
##        self.assertEqual(len(result), 20)
##        # self.assertTrue(51823321 in result)
##        # self.assertTrue(42934821 in result)
##        # self.assertTrue(44328684 in result)


class TestMyPickPage(unittest.TestCase):
    def testMyPickPage(self):
        try:
            path = './test/test-image-my_pick.html'
            p = open(path, 'r')
            page = as_soup(p.read())
            image = PixivImage(12467674, page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2004)

    def testGuroPageEng(self):
        try:
            path = './test/test-image-guro-e.html'
            p = open(path, 'r')
            page = as_soup(p.read())
            image = PixivImage(31111130, page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2005)

    def testEroPageEng(self):
        try:
            path = './test/test-image-ero-e.html'
            p = open(path, 'r')
            page = as_soup(p.read())
            image = PixivImage(31115956, page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2005)


class TestPixivTags(unittest.TestCase):
    def testTagsSearchExact1(self):
        path = './test/test-tags-search-exact2.htm'
        p = open(path, 'r')
        page = as_soup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 40)
        self.assertEqual(image.isLastPage, False)
        self.assertEqual(image.availableImages, 2283)

    # tags.php?tag=%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B%21
    def testTagsSearchExact(self):
        path = './test/test-tags-search-exact.htm'
        p = open(path, 'r')
        page = as_soup(p.read())
        image = PixivTags()
        image.parseTags(page)
##        for img in image.itemList:
##            print(img.imageId)
        self.assertEqual(len(image.itemList), 40)
        self.assertEqual(image.isLastPage, False)

    # search.php?word=%E5%88%9D%E6%98%A5%E9%A3%BE%E5%88%A9&s_mode=s_tag_full&order=date_d&p=70
    def testTagsSearchExactLast(self):
        path = './test/test-tags-search-exact-last.htm'
        p = open(path, 'r')
        page = as_soup(p.read())
        image = PixivTags()
        image.parseTags(page)

        print(image.itemList[-1])
        self.assertEqual(image.itemList[-1].imageId, 544700)
        self.assertEqual(image.isLastPage, True)

    # search.php?s_mode=s_tag&word=%E5%88%9D%E6%98%A5%E9%A3%BE%E5%88%A9
    def testTagsSearchPartial(self):
        path = './test/test-tags-search-partial.htm'
        p = open(path, 'r')
        page = as_soup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 40)
        self.assertEqual(image.isLastPage, False)

    def testTagsSearchPartialLast(self):
        path = './test/test-tags-search-partial-last.htm'
        p = open(path, 'r')
        page = as_soup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(image.itemList[-1].imageId, 15060554)
        self.assertEqual(image.isLastPage, True)

    def testTagsSearchParseDetails(self):
        path = './test/test-tags-search-exact-parse_details.htm'
        p = open(path, 'r')
        page = as_soup(p.read())
        image = PixivTags()
        image.parseTags(page)

        # self.assertEqual(len(image.itemList), 20)
        self.assertEqual(image.itemList[-1].imageId, 33815932)
        self.assertGreater(image.itemList[-1].bookmarkCount, 4)
        self.assertEqual(image.itemList[-1].imageResponse, 0)

##    def testTagsMemberSearch(self):
##        path = './test/test-tags-member-search.htm'
##        p = open(path, 'r')
##        page = as_soup(p.read())
##        image = PixivTags()
##        image.parseMemberTags(page, 313631)
##
##        self.assertEqual(len(image.itemList), 40)
##        # self.assertEqual(image.itemList[0].imageId, 53977340)
##        # self.assertEqual(image.itemList[19].imageId, 45511597)
##        self.assertEqual(image.isLastPage, False)
##        self.assertEqual(image.availableImages, 73)

##    def testTagsMemberSearchLast(self):
##        path = './test/test-tags-member-search-last.htm'
##        p = open(path, 'r')
##        page = as_soup(p.read())
##        image = PixivTags()
##        image.parseMemberTags(page, 313631)
##
##        # self.assertEqual(len(image.itemList), 10)
##        self.assertEqual(image.itemList[-1].imageId, 1804545)
##        self.assertEqual(image.isLastPage, True)

    def testTagsSkipShowcase(self):
        path = './test/test-tags-search-skip-showcase.htm'
        p = open(path, 'r')
        page = as_soup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 40)


class TestPixivGroup(unittest.TestCase):
    def testParseJson(self):
        path = './test/group.json'
        p = open(path)
        result = PixivGroup(p)

        self.assertEqual(len(result.imageList), 35)
        self.assertEqual(len(result.externalImageList), 1)
        self.assertEqual(result.maxId, 920234)


def main():
    test_classes_to_run = [TestPixivArtist, TestPixivImage, TestPixivBookmark, TestMyPickPage, TestPixivTags, TestPixivGroup]
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


if __name__ == '__main__':
    main()
