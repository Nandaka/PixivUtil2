#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-
from PixivModel import PixivArtist, PixivImage, PixivBookmark,PixivNewIllustBookmark, PixivTags
from PixivException import PixivException
from BeautifulSoup import BeautifulSoup
from mechanize import Browser
import os
import unittest

class TestPixivArtist(unittest.TestCase):
    def testPixivArtistProfileDataSrc(self):
      #print '\nTesting member page ProfileDataSrc'
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

    def testPixivArtistNoImage(self):
      #print '\nTesting member page - no image'
      p = open('./test/test-noimage.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException):
          PixivArtist(1233, page)
      page.decompose()
      del page

    def testPixivArtistNoMember(self):
      #print '\nTesting member page - no member'
      p = open('./test/test-nouser.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException):
          PixivArtist(1, page)
      page.decompose()
      del page

    def testPixivArtistNoAvatar(self):
      #print '\nTesting member page without avatar image'
      p = open('./test/test-member-noavatar.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        artist = PixivArtist(26357, page)
        #artist.PrintInfo()
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(artist, None)
      self.assertEqual(artist.artistId, 26357)
      self.assertEqual(artist.artistToken, 'yukimaruko')

    def testPixivArtistSuspended(self):
      #print '\nTesting member page - suspended member'
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
      #print '\nTesting member page'
      p = open('./test/test-member-bookmark.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        artist = PixivArtist(3281699, page)
        #artist.PrintInfo()
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(artist, None)
      self.assertEqual(artist.artistId, 3281699)

class TestPixivImage(unittest.TestCase):
    def testPixivImageParseInfo(self):
      p = open('./test/test-image-info.html', 'r')
      page = BeautifulSoup(p.read())
      image2 = PixivImage(32039274, page)
      page.decompose()
      del page

      self.assertEqual(image2.imageId, 32039274)
      self.assertEqual(image2.imageTitle, u"新しいお姫様")
      self.assertEqual(image2.imageCaption, u'EXIT TUNES様より冬コミ発売予定の「MAYU画集(仮)」に１枚描かせて頂きました。詳しくはこちらをご確認下さい！★ <a href="/jump.php?http%3A%2F%2Fexittunes.com%2Fevent%2Fc83%2Findex.html" target="_blank">http://exittunes.com/event/c83/index.html</a> ★「MAYU」公式サイト<a href="/jump.php?http%3A%2F%2Fmayusan.jp%2F" target="_blank">http://mayusan.jp/</a>')

      self.assertTrue(u'MAYU' in image2.imageTags)
      self.assertTrue(u'VOCALOID' in image2.imageTags)
      self.assertTrue(u'VOCALOID3' in image2.imageTags)
      self.assertTrue(u'うさぎになりたい' in image2.imageTags)
      self.assertTrue(u'なにこれかわいい' in image2.imageTags)
      self.assertTrue(u'やはり存在する斧' in image2.imageTags)
      self.assertTrue(u'ヤンデレ' in image2.imageTags)
      self.assertTrue(u'吸いこまれそうな瞳の色' in image2.imageTags)

      self.assertEqual(image2.imageMode, "big")
      self.assertEqual(image2.worksDate,'12-11-2012 00:23')
      self.assertEqual(image2.worksResolution,'642x900')
      self.assertEqual(image2.worksTools, 'Photoshop SAI')
      #self.assertEqual(image2.jd_rtv, 88190)
      #self.assertEqual(image2.jd_rtc, 6711)
      #self.assertEqual(image2.jd_rtt, 66470)
      self.assertEqual(image2.artist.artistToken, 'nardack')

    def testPixivImageNoAvatar(self):
      #print '\nTesting artist page without avatar image'
      p = open('./test/test-image-noavatar.htm', 'r')
      page = BeautifulSoup(p.read())
      image = PixivImage(20496355, page)
      page.decompose()
      del page
      ##self.assertNotEqual(image, None)
      self.assertEqual(image.artist.artistToken, 'iymt')
      self.assertEqual(image.imageId, 20496355)
      #07/22/2011 03:09｜512×600｜RETAS STUDIO&nbsp;
      #print image.worksDate, image.worksResolution, image.worksTools
      self.assertEqual(image.worksDate,'7-22-2011 03:09')
      self.assertEqual(image.worksResolution,'512x600')
      self.assertEqual(image.worksTools,'RETAS STUDIO')

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
      self.assertEqual(image.worksDate,'6-9-2010 02:33')
      self.assertEqual(image.worksResolution,'1009x683')
      self.assertEqual(image.worksTools,u'SAI')
      ##print image.imageTags
      joinedResult = " ".join(image.imageTags)
      self.assertEqual(joinedResult, u'VOCALOID VOCALOID100users\u5165\u308a \u3075\u3064\u304f\u3057\u3044 \u30ed\u30fc\u30a2\u30f3\u30b0\u30eb \u521d\u97f3\u30df\u30af \u6b4c\u3046 \u717d\u308a_\u4ef0\u8996')

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
      self.assertEqual(image.worksDate,'3-6-2010 03:04')
      self.assertEqual(image.worksResolution,'1155x768')
      self.assertEqual(image.worksTools,u'SAI')
      self.assertEqual(image.imageTags,[])

    def testPixivImageUnicode(self):
      #print '\nTesting image page - big'
      p = open('./test/test-image-unicode.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(2493913, page)
        #image.PrintInfo()
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 2493913)
      self.assertEqual(image.imageMode, 'big')
      self.assertEqual(image.worksDate,'12-23-2008 21:01')
      self.assertEqual(image.worksResolution,'852x1200')
      #print image.worksTools
      self.assertEqual(image.worksTools,u'Photoshop SAI つけペン')

    def testPixivImageRateCount(self):
      p = open('./test/test-image-rate_count.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(28865189, page)
        #image.PrintInfo()
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 28865189)
      self.assertEqual(image.imageMode, 'manga')
      self.assertTrue(image.jd_rtv > 0)
      self.assertTrue(image.jd_rtc > 0)
      self.assertTrue(image.jd_rtt > 0)
      self.assertEqual(image.worksTools, "Photoshop")

    def testPixivImageNoImage(self):
      #print '\nTesting image page - no image'
      p = open('./test/test-image-noimage.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException):
          PixivImage(123, page)
      page.decompose()
      del page

    def testPixivImageNoImageEng(self):
      #print '\nTesting image page - no image'
      p = open('./test/test-image-noimage-eng.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivException):
          PixivImage(123, page)
      page.decompose()
      del page

    def testPixivImageModeManga(self):
      #print '\nTesting image page - manga'
      p = open('./test/test-image-manga.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(28820443, page)
        #image.PrintInfo()
      except PixivException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 28820443)
      self.assertEqual(image.imageMode, 'manga')

    def testPixivImageParseBig(self):
      #print '\nTesting parse Big Image'
      p = open('./test/test-image-parsebig.htm', 'r')
      page = BeautifulSoup(p.read())
      image = PixivImage()
      urls = image.ParseImages(page, mode='big')
      self.assertEqual(len(urls), 1)
      imageId = urls[0].split('/')[-1].split('.')[0]
      #print 'imageId:',imageId
      self.assertEqual(int(imageId), 20644633)

    def testPixivImageParseManga(self):
      #print '\nTesting parse Manga Images'
      p = open('./test/test-image-parsemanga.htm', 'r')
      page = BeautifulSoup(p.read())
      image = PixivImage()
      urls = image.ParseImages(page, mode='manga')
      #print urls
      self.assertEqual(len(urls), 39*2)
      imageId = urls[0].split('/')[-1].split('.')[0]
      #print 'imageId:',imageId
      self.assertEqual(imageId, '20592252_big_p0')

    def testPixivImageNoLogin(self):
      #print '\nTesting not logged in'
      p = open('./test/test-image-nologin.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
          image = PixivImage(9138317, page)
          self.assertRaises(PixivException)
      except PixivException as ex:
          self.assertEqual(ex.errorCode, 100)

class TestPixivBookmark(unittest.TestCase):
    def testPixivBookmarkNewIlust(self):
      #print '\nTesting BookmarkNewIlust'
      p = open('./test/test-bookmarks_new_ilust.htm', 'r')
      page = BeautifulSoup(p.read())
      result = PixivNewIllustBookmark(page)

      self.assertEqual(len(result.imageList), 20)

    def testPixivImageBookmark(self):
      #print '\nTesting PixivImageBookmark'
      p = open('./test/test-image-bookmark.htm', 'r')
      page = BeautifulSoup(p.read())
      result = PixivBookmark.parseImageBookmark(page)

      self.assertEqual(len(result), 19)
      self.assertTrue(35303260 in result)
      self.assertTrue(28629066 in result)
      self.assertTrue(27249307 in result)
      self.assertTrue(30119925 in result)

class TestMyPickPage(unittest.TestCase):
    def testMyPickPage(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-my_pick.html').replace(os.sep,'/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(12467674,page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2002)

    def testMyPickPageEng(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-my_pick-e.html').replace(os.sep,'/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(28688383,page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2002)

    def testGuroPageEng(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-guro-e.html').replace(os.sep,'/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(31111130,page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2005)

    def testEroPageEng(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-ero-e.html').replace(os.sep,'/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(31115956,page)

            self.assertRaises(PixivException)
        except PixivException as ex:
            self.assertEqual(ex.errorCode, 2005)


class TestPixivTags(unittest.TestCase):
    ## tags.php?tag=%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B%21
    def testTagsSearchExact(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-exact.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 20)
        self.assertEqual(image.isLastPage, False)

    def testTagsSearchExactLast(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-exact-last.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        ##self.assertEqual(len(image.itemList), 3)
        self.assertEqual(image.itemList[-1].imageId, 15060554)
        self.assertEqual(image.isLastPage, True)

    ## search.php?s_mode=s_tag&word=%E5%88%9D%E6%98%A5%E9%A3%BE%E5%88%A9
    def testTagsSearchPartial(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-partial.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 20)
        self.assertEqual(image.isLastPage, False)

    def testTagsSearchPartialLast(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-partial-last.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(image.itemList[-1].imageId, 15060554)
        self.assertEqual(image.isLastPage, True)

    def testTagsSearchParseDetails(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-exact-parse_details.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        ##self.assertEqual(len(image.itemList), 20)
        self.assertEqual(image.itemList[-1].imageId, 33815932)
        self.assertEqual(image.itemList[-1].bookmarkCount, 2)
        self.assertEqual(image.itemList[-1].imageResponse, -1)

    def testTagsMemberSearch(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-member-search.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseMemberTags(page)

        self.assertEqual(len(image.itemList), 20)
        self.assertEqual(image.itemList[0].imageId, 25757869)
        self.assertEqual(image.itemList[19].imageId, 14818847)
        self.assertEqual(image.isLastPage, False)

    def testTagsMemberSearchLast(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-member-search-last.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseMemberTags(page)

        ##self.assertEqual(len(image.itemList), 10)
        self.assertEqual(image.itemList[-1].imageId, 1804545)
        self.assertEqual(image.isLastPage, True)

    def testTagsSkipShowcase(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-skip-showcase.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 20)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivArtist)
    unittest.TextTestRunner(verbosity=5).run(suite)
    print "================================================================"
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivImage)
    unittest.TextTestRunner(verbosity=5).run(suite)
    print "================================================================"
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivBookmark)
    unittest.TextTestRunner(verbosity=5).run(suite)
    print "================================================================"
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMyPickPage)
    unittest.TextTestRunner(verbosity=5).run(suite)
    print "================================================================"
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivTags)
    unittest.TextTestRunner(verbosity=5).run(suite)

