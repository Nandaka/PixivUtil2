#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-
from PixivModel import PixivArtist, PixivImage, PixivModelException, PixivBookmark,PixivNewIllustBookmark, PixivTags
from BeautifulSoup import BeautifulSoup
from mechanize import Browser
import os
import unittest

class TestPixivArtist(unittest.TestCase):
    def testPixivArtistPage(self):
      #print '\nTesting member page'
      p = open('./test/test.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        artist = PixivArtist(363073, page)
        #artist.PrintInfo()
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(artist, None)
      self.assertEqual(artist.artistId, 363073)

    def testPixivArtistProfileDataSrc(self):
      #print '\nTesting member page ProfileDataSrc'
      p = open('./test/test-profile-datasrc.html', 'r')
      page = BeautifulSoup(p.read())
      try:
        artist = PixivArtist(1295112, page)
        #artist.PrintInfo()
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(artist, None)
      self.assertEqual(artist.artistId, 1295112)
      self.assertEqual(artist.artistToken, 'naoel')
    
    def testPixivArtistNoImage(self):
      #print '\nTesting member page - no image'
      p = open('./test/test-noimage.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivModelException):
          PixivArtist(363073, page)
      page.decompose()
      del page

    def testPixivArtistNoMember(self):
      #print '\nTesting member page - no member'
      p = open('./test/test-nouser.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivModelException):
          PixivArtist(363073, page)
      page.decompose()
      del page

    def testPixivArtistNoAvatar(self):
      #print '\nTesting member page without avatar image'
      p = open('./test/test-member-noavatar.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        artist = PixivArtist(26357, page)
        #artist.PrintInfo()
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(artist, None)
      self.assertEqual(artist.artistId, 26357)
      self.assertEqual(artist.artistToken, 'yukimaruko')
      
    def testPixivArtistDeleted(self):
      #print '\nTesting member page - deleted member'
      p = open('./test/test-member-deleted.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivModelException):
          PixivArtist(123, page)
      page.decompose()
      del page

    def testPixivArtistSuspended(self):
      #print '\nTesting member page - suspended member'
      p = open('./test/test-member-suspended.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivModelException) as ex:
          PixivArtist(123, page)
      self.assertEqual(ex.exception.errorCode, 1002)
      page.decompose()
      del page

    def testPixivArtistNotLoggedIn(self):
      p = open('./test/test-member-nologin.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivModelException) as ex:
          PixivArtist(143229, page)
      self.assertEqual(ex.exception.errorCode, 100)
      page.decompose()
      del page
      
class TestPixivImage(unittest.TestCase):
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
      self.assertEqual(image.worksDate,'07-22-2011 03:09')
      self.assertEqual(image.worksResolution,'512x600')
      self.assertEqual(image.worksTools,'RETAS STUDIO')

    def testPixivImageParseTags(self):
      p = open('./test/test-image-parse-tags.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(11164869, page)
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 11164869)
      self.assertEqual(image.worksDate,'06-09-2010 02:33')
      self.assertEqual(image.worksResolution,'1009x683')
      self.assertEqual(image.worksTools,u'SAI')
      self.assertEqual(image.imageTags,[u'VOCALOID', u'VOCALOID100users\u5165\u308a', u'\u3075\u3064\u304f\u3057\u3044', u'\u30ed\u30fc\u30a2\u30f3\u30b0\u30eb', u'\u521d\u97f3\u30df\u30af', u'\u6b4c\u3046', u'\u717d\u308a_\u4ef0\u8996'])

    def testPixivImageParseNoTags(self):
      p = open('./test/test-image-no_tags.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(9175987, page)
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 9175987)
      self.assertEqual(image.worksDate,'03-06-2010 03:04')
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
      except PixivModelException as ex:
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
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 28865189)
      self.assertEqual(image.imageMode, 'manga')
      self.assertEqual(image.jd_rtv, 8941)
      self.assertEqual(image.jd_rtc, 294)
      self.assertEqual(image.jd_rtt, 2895)
      self.assertEqual(image.worksTools, "Photoshop")

    def testPixivImageNoImage(self):
      #print '\nTesting image page - no image'
      p = open('./test/test-image-noimage.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivModelException):
          PixivImage(123, page)
      page.decompose()
      del page

    def testPixivImageNoImageEng(self):
      #print '\nTesting image page - no image'
      p = open('./test/test-image-noimage-eng.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivModelException):
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
      except PixivModelException as ex:
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
          self.assertRaises(PixivModelException)
      except PixivModelException as ex:
          self.assertEqual(ex.errorCode, 100)
      
class TestPixivBookmark(unittest.TestCase):
    def testPixivBookmarkNewIlust(self):
      #print '\nTesting BookmarkNewIlust'
      p = open('./test/test-bookmarks_new_ilust.htm', 'r')
      page = BeautifulSoup(p.read())
      result = PixivNewIllustBookmark(page)

      self.assertEqual(len(result.imageList), 20)

class TestMyPickPage(unittest.TestCase):
    def testMyPickPage(self):
        try:
            br = Browser()
            path = 'file:///' + os.path.abspath('./test/test-image-my_pick.html').replace(os.sep,'/')
            p = br.open(path, 'r')
            page = BeautifulSoup(p.read())
            image = PixivImage(12467674,page)
        
            self.assertRaises(PixivModelException)
        except PixivModelException:
            pass

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
        self.assertEqual(image.itemList[0].imageId, 27792358)
        self.assertEqual(image.itemList[0].bookmarkCount, 2)
        self.assertEqual(image.itemList[0].imageResponse, -1)
        self.assertEqual(image.itemList[19].imageId, 27110688)
        self.assertEqual(image.itemList[19].bookmarkCount, -1)
        self.assertEqual(image.itemList[19].imageResponse, -1)
        self.assertEqual(image.isLastPage, False)

    def testTagsSearchExactLast(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-exact-last.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)

        self.assertEqual(len(image.itemList), 4)
        self.assertEqual(image.itemList[0].imageId, 21618970)
        self.assertEqual(image.itemList[0].bookmarkCount, -1)
        self.assertEqual(image.itemList[0].imageResponse, -1)
        self.assertEqual(image.itemList[3].imageId, 15060554)
        self.assertEqual(image.itemList[3].bookmarkCount, 1)
        self.assertEqual(image.itemList[3].imageResponse, -1)        
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
        self.assertEqual(image.itemList[0].imageId, 27792358)
        self.assertEqual(image.itemList[0].bookmarkCount, 2)
        self.assertEqual(image.itemList[0].imageResponse, -1)
        self.assertEqual(image.itemList[19].imageId, 27110688)
        self.assertEqual(image.itemList[19].bookmarkCount, -1)
        self.assertEqual(image.itemList[19].imageResponse, -1)
        self.assertEqual(image.isLastPage, False)

    def testTagsSearchPartialLast(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-partial-last.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)
        
        self.assertEqual(len(image.itemList), 4)
        self.assertEqual(image.itemList[0].imageId, 21618970)
        self.assertEqual(image.itemList[0].bookmarkCount, -1)
        self.assertEqual(image.itemList[0].imageResponse, -1)
        self.assertEqual(image.itemList[3].imageId, 15060554)
        self.assertEqual(image.itemList[3].bookmarkCount, 1)
        self.assertEqual(image.itemList[3].imageResponse, -1)
        self.assertEqual(image.isLastPage, True)

    def testTagsSearchParseDetails(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-search-exact-parse_details.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)
        
        self.assertEqual(len(image.itemList), 20)
        ## http://www.pixiv.net/member_illust.php?mode=medium&illust_id=26563564
        self.assertEqual(image.itemList[0].imageId, 26563564)
        self.assertEqual(image.itemList[0].bookmarkCount, 1)
        ## http://www.pixiv.net/member_illust.php?mode=medium&illust_id=26557089
        self.assertEqual(image.itemList[1].imageId, 26557089)
        self.assertEqual(image.itemList[1].bookmarkCount, 3)
        self.assertEqual(image.itemList[1].imageResponse, 14)
        ## http://www.pixiv.net/member_illust.php?mode=medium&illust_id=26538917
        self.assertEqual(image.itemList[5].imageId, 26538917)
        self.assertEqual(image.itemList[5].bookmarkCount, -1)
        self.assertEqual(image.itemList[5].imageResponse, -1)

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
        
        self.assertEqual(len(image.itemList), 10)
        self.assertEqual(image.itemList[0].imageId, 1894295)
        self.assertEqual(image.itemList[9].imageId, 1804545)
        self.assertEqual(image.isLastPage, True)
      
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

