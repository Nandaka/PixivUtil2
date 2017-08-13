#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-
from PixivModel import PixivArtist, PixivImage, PixivBookmark, PixivNewIllustBookmark, PixivTags, PixivGroup
from PixivBrowserFactory import PixivBrowser
from PixivException import PixivException
from BeautifulSoup import BeautifulSoup
from mechanize import Browser
import os
import unittest


class MockPixivBrowser(PixivBrowser):
    mode = None

    def __init__(self, mode):
        self.mode = mode
        pass

    def getPixivPage(self, url, referer="http://www.pixiv.net", errorPageName=None):
        if self.mode == 1:
            p = open('./test/test-image-big-single.html', 'r')
            page = BeautifulSoup(p.read())
            return page
        else:
            ''' fake the manga page '''
            pageNo = url.split("=")[-1]
            p = open('./test/test-image-parsemanga-big-' + pageNo + '.htm', 'r')
            page = BeautifulSoup(p.read())
            return page


class TestPixivArtist(unittest.TestCase):
    def testPixivArtistProfileDataSrc(self):
        # print '\nTesting member page ProfileDataSrc'
        p = open('./test/test-helper-avatar-name.htm', 'r')
        page = BeautifulSoup(p.read())
        try:
            artist = PixivArtist(1107124, page)
        except PixivException as ex:
            print ex
        page.decompose()
        del page
        self.assertNotEqual(artist, None)
        self.assertEqual(artist.artistId, 1107124)
        self.assertEqual(artist.artistToken, 'kirabara29')
        self.assertGreater(artist.totalImages, 71)

    def testPixivArtistNoImage(self):
        # print '\nTesting member page - no image'
        p = open('./test/test-noimage.htm', 'r')
        page = BeautifulSoup(p.read())
        with self.assertRaises(PixivException):
            member = PixivArtist(1233, page)
            print member.imageList
        page.decompose()
        del page

    def testPixivArtistNoMember(self):
        # print '\nTesting member page - no member'
        p = open('./test/test-nouser.htm', 'r')
        page = BeautifulSoup(p.read())
        with self.assertRaises(PixivException):
            PixivArtist(1, page)
        page.decompose()
        del page

    def testPixivArtistNoAvatar(self):
        # print '\nTesting member page without avatar image'
        p = open('./test/test-member-noavatar.htm', 'r')
        page = BeautifulSoup(p.read())
        try:
            artist = PixivArtist(26357, page)
            # artist.PrintInfo()
        except PixivException as ex:
            print ex
        page.decompose()
        del page
        self.assertNotEqual(artist, None)
        self.assertEqual(artist.artistId, 26357)
        self.assertEqual(artist.artistToken, 'yukimaruko')

    def testPixivArtistSuspended(self):
        # print '\nTesting member page - suspended member'
        p = open('./test/test-member-suspended.htm', 'r')
        page = BeautifulSoup(p.read())
        with self.assertRaises(PixivException) as ex:
            PixivArtist(123, page)
        self.assertEqual(ex.exception.errorCode, 1002)
        page.decompose()
        del page

    def testPixivArtistNotLoggedIn(self):
        p = open('./test/test-member-nologin.htm', 'r')
        page = BeautifulSoup(p.read())
        with self.assertRaises(PixivException) as ex:
            PixivArtist(143229, page)
        self.assertEqual(ex.exception.errorCode, 100)
        page.decompose()
        del page

    def testPixivArtistBookmark(self):
        # print '\nTesting member page'
        p = open('./test/test-member-bookmark.htm', 'r')
        page = BeautifulSoup(p.read())
        try:
            artist = PixivArtist(490219, page)
            # artist.PrintInfo()
        except PixivException as ex:
            print ex
            self.assertTrue(ex is None)

        page.decompose()
        del page

        self.assertNotEqual(artist, None)
        self.assertEqual(artist.artistId, 490219)

    def testPixivArtistServerError(self):
        # print '\nTesting member page'
        p = open('./test/test-server-error.html', 'r')
        page = BeautifulSoup(p.read())
        with self.assertRaises(PixivException) as ex:
            artist = PixivArtist(234753, page)
        self.assertEqual(ex.exception.errorCode, PixivException.SERVER_ERROR)
        page.decompose()
        del page


class TestPixivImage(unittest.TestCase):
    def testPixivImageParseInfo(self):
        p = open('./test/test-image-info.html', 'r')
        page = BeautifulSoup(p.read())
        image2 = PixivImage(32039274, page)
        page.decompose()
        del page

        self.assertEqual(image2.imageId, 32039274)
        self.assertEqual(image2.imageTitle, u"新しいお姫様")
        self.assertTrue(len(image2.imageCaption) > 0)
        print u"\r\nCaption = {0}".format(image2.imageCaption)

        self.assertTrue(u'MAYU' in image2.imageTags)
        self.assertTrue(u'VOCALOID' in image2.imageTags)
        self.assertTrue(u'VOCALOID3' in image2.imageTags)
        self.assertTrue(u'うさぎになりたい' in image2.imageTags)
        self.assertTrue(u'なにこれかわいい' in image2.imageTags)
        self.assertTrue(u'やはり存在する斧' in image2.imageTags)

        self.assertEqual(image2.imageMode, "bigNew")
        self.assertEqual(image2.worksDate, '12/11/2012 00:23')
        self.assertEqual(image2.worksResolution, '642x900')
        self.assertEqual(image2.worksTools, 'Photoshop SAI')
        # self.assertEqual(image2.jd_rtv, 88190)
        # self.assertEqual(image2.jd_rtc, 6711)
        # self.assertEqual(image2.jd_rtt, 66470)
        self.assertEqual(image2.artist.artistToken, 'nardack')

    def testPixivImageParseInfoJa(self):
        p = open('./test/test-image-parse-image-40273739-ja.html', 'r')
        page = BeautifulSoup(p.read())
        image2 = PixivImage(40273739, page)
        page.decompose()
        del page

        self.assertEqual(image2.imageId, 40273739)
        self.assertEqual(image2.imageTitle, u"Cos-Nurse")

        self.assertTrue(u'東方' in image2.imageTags)
        self.assertTrue(u'幽々子' in image2.imageTags)
        self.assertTrue(u'むちむち' in image2.imageTags)
        self.assertTrue(u'おっぱい' in image2.imageTags)
        self.assertTrue(u'尻' in image2.imageTags)
        self.assertTrue(u'東方グラマラス' in image2.imageTags)
        self.assertTrue(u'誰だお前' in image2.imageTags)

        self.assertEqual(image2.imageMode, "big")
        self.assertEqual(image2.worksDate, u"2013年12月14日 19:00")
        self.assertEqual(image2.worksResolution, '855x1133')
        self.assertEqual(image2.worksTools, 'Photoshop SAI')
        self.assertEqual(image2.artist.artistToken, 'k2321656')

    def testPixivImageParseInfoPixivPremiumOffer(self):
        p = open('./test/test-image-parse-image-38826533-pixiv-premium.html', 'r')
        page = BeautifulSoup(p.read())
        image2 = PixivImage(38826533, page)
        page.decompose()
        del page

        self.assertEqual(image2.imageId, 38826533)
        self.assertEqual(image2.imageTitle, u"てやり")
        self.assertEqual(image2.imageCaption, u'一応シーダ様です。')

        self.assertTrue(u'R-18' in image2.imageTags)
        self.assertTrue(u'FE' in image2.imageTags)
        self.assertTrue(u'ファイアーエムブレム' in image2.imageTags)
        self.assertTrue(u'シーダ' in image2.imageTags)

        self.assertEqual(image2.imageMode, "big")
        self.assertEqual(image2.worksDate, '9/30/2013 01:43')
        self.assertEqual(image2.worksResolution, '1000x2317')
        self.assertEqual(image2.worksTools, 'CLIP STUDIO PAINT')
        # self.assertEqual(image2.jd_rtv, 88190)
        # self.assertEqual(image2.jd_rtc, 6711)
        # self.assertEqual(image2.jd_rtt, 66470)
        self.assertEqual(image2.artist.artistToken, 'hvcv')

    def testPixivImageNoAvatar(self):
        # print '\nTesting artist page without avatar image'
        p = open('./test/test-image-noavatar.htm', 'r')
        page = BeautifulSoup(p.read())
        image = PixivImage(20496355, page)
        page.decompose()
        del page
        # self.assertNotEqual(image, None)
        self.assertEqual(image.artist.artistToken, 'iymt')
        self.assertEqual(image.imageId, 20496355)
        # 07/22/2011 03:09｜512×600｜RETAS STUDIO&nbsp;
        # print image.worksDate, image.worksResolution, image.worksTools
        self.assertEqual(image.worksDate, '7/22/2011 03:09')
        self.assertEqual(image.worksResolution, '512x600')
        self.assertEqual(image.worksTools, 'RETAS STUDIO')

    def testPixivImageParseTags(self):
        p = open('./test/test-image-parse-tags.htm', 'r')
        page = BeautifulSoup(p.read())
        try:
            image = PixivImage(11164869, page)
        except PixivException as ex:
            print ex
        page.decompose()
        del page
        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 11164869)
        self.assertEqual(image.worksDate, '6/9/2010 02:33')
        self.assertEqual(image.worksResolution, '1009x683')
        self.assertEqual(image.worksTools, u'SAI')
        # print image.imageTags
        joinedResult = " ".join(image.imageTags)
        self.assertEqual(joinedResult.find("VOCALOID") > -1, True)

    def testPixivImageParseNoTags(self):
        p = open('./test/test-image-no_tags.htm', 'r')
        page = BeautifulSoup(p.read())
        try:
            image = PixivImage(9175987, page)
        except PixivException as ex:
            print ex
        page.decompose()
        del page
        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 9175987)
        self.assertEqual(image.worksDate, '3/6/2010 03:04')
        self.assertEqual(image.worksResolution, '1155x768')
        self.assertEqual(image.worksTools, u'SAI')
        self.assertEqual(image.imageTags, [])

    def testPixivImageUnicode(self):
        # print '\nTesting image page - big'
        p = open('./test/test-image-unicode.htm', 'r')
        page = BeautifulSoup(p.read())
        try:
            image = PixivImage(2493913, page)
            # image.PrintInfo()
        except PixivException as ex:
            print ex
        page.decompose()
        del page
        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 2493913)
        self.assertEqual(image.imageMode, 'bigNew')
        self.assertEqual(image.worksDate, '12/23/2008 21:01')
        self.assertEqual(image.worksResolution, '852x1200')
        # print image.worksTools
        self.assertEqual(image.worksTools, u'Photoshop SAI つけペン')

    def testPixivImageRateCount(self):
        p = open('./test/test-image-rate_count.htm', 'r')
        page = BeautifulSoup(p.read())
        try:
            image = PixivImage(28865189, page)
            # image.PrintInfo()
        except PixivException as ex:
            print ex
        page.decompose()
        del page
        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 28865189)
        self.assertEqual(image.imageMode, 'manga')
        self.assertTrue(image.jd_rtv > 0)
        self.assertTrue(image.jd_rtc > 0)
        # deprecated since 11-April-2017
        # self.assertTrue(image.jd_rtt > 0)
        self.assertEqual(image.worksTools, "Photoshop")

    def testPixivImageNoImage(self):
        # print '\nTesting image page - no image'
        p = open('./test/test-image-noimage.htm', 'r')
        page = BeautifulSoup(p.read())
        with self.assertRaises(PixivException):
            PixivImage(123, page)
        page.decompose()
        del page

    def testPixivImageDeleted(self):
        # print '\nTesting image page - deleted image'
        p = open('./test/test-image-deleted.htm', 'r')
        page = BeautifulSoup(p.read())
        with self.assertRaises(PixivException):
            PixivImage(123, page)
        page.decompose()
        del page

    def testPixivImageNoImageEng(self):
        # print '\nTesting image page - no image'
        p = open('./test/test-image-noimage-eng.htm', 'r')
        page = BeautifulSoup(p.read())
        with self.assertRaises(PixivException):
            PixivImage(123, page)
        page.decompose()
        del page

    def testPixivImageModeManga(self):
        # print '\nTesting image page - manga'
        p = open('./test/test-image-manga.htm', 'r')
        page = BeautifulSoup(p.read())
        try:
            image = PixivImage(28820443, page)
            # image.PrintInfo()
        except PixivException as ex:
            print ex
        page.decompose()
        del page
        self.assertNotEqual(image, None)
        self.assertEqual(image.imageId, 28820443)
        self.assertEqual(image.imageMode, 'manga')

    def testPixivImageParseMangaTwoPage(self):
        # print '\nTesting parse Manga Images'
        p = open('./test/test-image-manga-2page.htm', 'r')
        page = BeautifulSoup(p.read())
        image = PixivImage()
        urls = image.ParseImages(page, mode='manga')
        # print urls
        self.assertEqual(len(urls), 11)
        self.assertEqual(len(urls), image.imageCount)
        imageId = urls[0].split('/')[-1].split('.')[0]
        # print 'imageId:',imageId
        self.assertEqual(imageId, '46322053_p0')

    def testPixivImageParseBig(self):
        # print '\nTesting parse Big Image'
        p = open('./test/test-image-unicode.htm', 'r')
        page = BeautifulSoup(p.read())
        image = PixivImage()
        urls = image.ParseImages(page, mode='big')
        self.assertEqual(len(urls), 1)
        print urls[0]
        imageId = urls[0].split('/')[-1].split('_')[0]
        # print 'imageId:',imageId
        self.assertEqual(int(imageId), 2493913)

    def testPixivImageParseManga(self):
        # print '\nTesting parse Manga Images'
        p = open('./test/test-image-parsemanga.htm', 'r')
        page = BeautifulSoup(p.read())
        image = PixivImage()
        urls = image.ParseImages(page, mode='manga', _br=MockPixivBrowser(None))
        # print urls
        self.assertEqual(len(urls), 3)
        self.assertEqual(len(urls), image.imageCount)
        imageId = urls[0].split('/')[-1].split('.')[0]
        # print 'imageId:',imageId
        self.assertEqual(imageId, '46279245_p0')

    def testPixivImageParseMangaBig(self):
        # print '\nTesting parse Manga Images'
        # Issue #224
        p = open('./test/test-image-big-manga.html', 'r')
        page = BeautifulSoup(p.read())
        image = PixivImage(iid=62670665)
        image.ParseInfo(page)
        urls = image.ParseImages(page, mode=image.imageMode, _br=MockPixivBrowser(1))
        self.assertEqual(len(urls), 1)
        print urls[0]
        imageId = urls[0].split('/')[-1].split('_')[0]
        # print 'imageId:',imageId
        self.assertEqual(int(imageId), 62670665)

    def testPixivImageNoLogin(self):
        # print '\nTesting not logged in'
        p = open('./test/test-image-nologin.htm', 'r')
        page = BeautifulSoup(p.read())
        try:
            image = PixivImage(9138317, page)
            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, PixivException.NOT_LOGGED_IN)

    def testPixivImageServerError(self):
        # print '\nTesting image page'
        p = open('./test/test-server-error.html', 'r')
        page = BeautifulSoup(p.read())
        with self.assertRaises(PixivException) as ex:
            image = PixivImage(9138317, page)
        self.assertEqual(ex.exception.errorCode, PixivException.SERVER_ERROR)
        page.decompose()
        del page

    def testPixivImageServerError2(self):
        # print '\nTesting image page'
        p = open('./test/test-image-generic-error.html', 'r')
        page = BeautifulSoup(p.read())
        with self.assertRaises(PixivException) as ex:
            image = PixivImage(37882549, page)
        self.assertEqual(ex.exception.errorCode, PixivException.SERVER_ERROR)
        page.decompose()
        del page

    def testPixivImageUgoira(self):
        # print '\nTesting image page'
        p = open('./test/test-image-ugoira.htm', 'r')
        page = BeautifulSoup(p.read())
        image = PixivImage(46281014, page)
        urls = image.ParseImages(page)
        print image.imageUrls
        self.assertTrue(image.imageUrls[0].find(".zip") > -1)
        page.decompose()
        del page


class TestPixivBookmark(unittest.TestCase):
    def testPixivBookmarkNewIlust(self):
        # print '\nTesting BookmarkNewIlust'
        p = open('./test/test-bookmarks_new_ilust.htm', 'r')
        page = BeautifulSoup(p.read())
        result = PixivNewIllustBookmark(page)

        self.assertEqual(len(result.imageList), 20)

    def testPixivImageBookmark(self):
        # print '\nTesting PixivImageBookmark'
        p = open('./test/test-image-bookmark.htm', 'r')
        page = BeautifulSoup(p.read())
        result = PixivBookmark.parseImageBookmark(page)

        self.assertEqual(len(result), 20)
        self.assertTrue(35303260 in result)
        self.assertTrue(28629066 in result)
        self.assertTrue(27249307 in result)
        self.assertTrue(30119925 in result)

    def testPixivImageBookmarkMember(self):
        # print '\nTesting PixivImageBookmark'
        p = open('./test/test-image-bookmark-member.htm', 'r')
        page = BeautifulSoup(p.read())
        result = PixivBookmark.parseImageBookmark(page)

        self.assertEqual(len(result), 20)
        # self.assertTrue(51823321 in result)
        # self.assertTrue(42934821 in result)
        # self.assertTrue(44328684 in result)


class TestMyPickPage(unittest.TestCase):
    def testMyPickPage(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-my_pick.html').replace(os.sep, '/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(12467674, page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2002)

    def testMyPickPageEng(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-my_pick-e.html').replace(os.sep, '/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(28688383, page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2002)

    def testGuroPageEng(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-guro-e.html').replace(os.sep, '/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(31111130, page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2005)

    def testEroPageEng(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-ero-e.html').replace(os.sep, '/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(31115956, page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2005)


class TestPixivTags(unittest.TestCase):
    def testTagsSearchExact1(self):
        br = Browser()
        path = 'file:///' + os.path.abspath(u'./test/test-tags-search-exact2.htm').replace(os.sep, '/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 40)
        self.assertEqual(image.isLastPage, False)
        self.assertEqual(image.availableImages, 2270)

    # tags.php?tag=%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B%21
    def testTagsSearchExact(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-exact.htm').replace(os.sep, '/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)
        for img in image.itemList:
            print img.imageId
        self.assertEqual(len(image.itemList), 40)
        self.assertEqual(image.isLastPage, False)

    def testTagsSearchExactLast(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-exact-last.htm').replace(os.sep, '/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        # self.assertEqual(len(image.itemList), 3)
        self.assertEqual(image.itemList[-1].imageId, 15060554)
        self.assertEqual(image.isLastPage, True)

    # search.php?s_mode=s_tag&word=%E5%88%9D%E6%98%A5%E9%A3%BE%E5%88%A9
    def testTagsSearchPartial(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-partial.htm').replace(os.sep, '/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 40)
        self.assertEqual(image.isLastPage, False)

    def testTagsSearchPartialLast(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-partial-last.htm').replace(os.sep, '/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(image.itemList[-1].imageId, 15060554)
        self.assertEqual(image.isLastPage, True)

    def testTagsSearchParseDetails(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-exact-parse_details.htm').replace(os.sep, '/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        # self.assertEqual(len(image.itemList), 20)
        self.assertEqual(image.itemList[-1].imageId, 33815932)
        self.assertGreater(image.itemList[-1].bookmarkCount, 4)
        self.assertEqual(image.itemList[-1].imageResponse, 0)

    def testTagsMemberSearch(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-member-search.htm').replace(os.sep, '/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseMemberTags(page, 313631)

        self.assertEqual(len(image.itemList), 40)
        # self.assertEqual(image.itemList[0].imageId, 53977340)
        # self.assertEqual(image.itemList[19].imageId, 45511597)
        self.assertEqual(image.isLastPage, False)
        self.assertEqual(image.availableImages, 67)

    def testTagsMemberSearchLast(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-member-search-last.htm').replace(os.sep, '/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseMemberTags(page, 313631)

        # self.assertEqual(len(image.itemList), 10)
        self.assertEqual(image.itemList[-1].imageId, 1804545)
        self.assertEqual(image.isLastPage, True)

    def testTagsSkipShowcase(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-skip-showcase.htm').replace(os.sep, '/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 40)


class TestPixivGroup(unittest.TestCase):
    def testParseJson(self):
        path = os.path.abspath('./test/group.json').replace(os.sep, '/')
        p = open(path)
        result = PixivGroup(p)

        self.assertEqual(len(result.imageList), 34)
        self.assertEqual(len(result.externalImageList), 2)
        self.assertEqual(result.maxId, 626288)

if __name__ == '__main__':
    test_classes_to_run = [TestPixivArtist, TestPixivImage, TestPixivBookmark, TestMyPickPage, TestPixivTags, TestPixivGroup]
    # test_classes_to_run = [TestPixivImage]
    # test_classes_to_run = [TestPixivTags]

    loader = unittest.TestLoader()

    suites_list = []
    for test_class in test_classes_to_run:
        suite = loader.loadTestsFromTestCase(test_class)
        suites_list.append(suite)

    big_suite = unittest.TestSuite(suites_list)

    runner = unittest.TextTestRunner(verbosity=5)
    results = runner.run(big_suite)
