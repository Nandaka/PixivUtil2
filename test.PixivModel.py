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
      p = open('./test/test-membernoimage.htm', 'r')
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

class TestPixivImage(unittest.TestCase):
    def testPixivImageNoAvatar(self):
      #print '\nTesting artist page without avatar image'
      p = open('./test/test-membernoimage2.htm', 'r')
      page = BeautifulSoup(p.read())
      image = PixivImage(20496355, page)
      #image.PrintInfo()
      #image.artist.PrintInfo()
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.artist.artistToken, 'iymt')
      self.assertEqual(image.imageId, 20496355)
      #07/22/2011 03:09｜512×600｜RETAS STUDIO&nbsp;
      #print image.worksDate, image.worksResolution, image.worksTools
      self.assertEqual(image.worksDate,'07-22-2011 03.09')
      self.assertEqual(image.worksResolution,'512x600')
      self.assertEqual(image.worksTools,'RETAS STUDIO&nbsp;')

    def testPixivImageUnicode(self):
      #print '\nTesting image page - big'
      p = open('./test/test-image-unicode.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(9908869, page)
        #image.PrintInfo()
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 9908869)
      self.assertEqual(image.imageMode, 'big')
      
    def testPixivImage(self):
      #print '\nTesting image page - big'
      p = open('./test/test-image.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(20623238, page)
        #image.PrintInfo()
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 20623238)
      self.assertEqual(image.imageMode, 'big')
      self.assertEqual(image.jd_rtv, 1)
      self.assertEqual(image.jd_rtc, 2)
      self.assertEqual(image.jd_rtt, 3)

    def testPixivImageNoImage(self):
      #print '\nTesting image page - no image'
      p = open('./test/test-noimage2.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivModelException):
          PixivImage(20623238, page)
      page.decompose()
      del page

    def testPixivImageModeManga(self):
      #print '\nTesting image page - manga'
      p = open('./test/test-image-manga.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(20581412, page)
        #image.PrintInfo()
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 20581412)
      self.assertEqual(image.imageMode, 'manga')

    def testPixivImageParseBig(self):
      #print '\nTesting parse Big Image'
      p = open('./test/test-bigimage.htm', 'r')
      page = BeautifulSoup(p.read())
      image = PixivImage()
      urls = image.ParseImages(page, mode='big')
      self.assertEqual(len(urls), 1)
      imageId = urls[0].split('/')[-1].split('.')[0]
      #print 'imageId:',imageId
      self.assertEqual(int(imageId), 20644633)

    def testPixivImageParseManga(self):
      #print '\nTesting parse Manga Images'
      p = open('./test/test-manga.htm', 'r')
      page = BeautifulSoup(p.read())
      image = PixivImage()
      urls = image.ParseImages(page, mode='manga')
      #print urls
      self.assertEqual(len(urls), 39*2)
      imageId = urls[0].split('/')[-1].split('.')[0]
      #print 'imageId:',imageId
      self.assertEqual(imageId, '20592252_big_p0')
      
class TestPixivBookmark(unittest.TestCase):
    def testPixivBookmarkNewIlust(self):
      #print '\nTesting BookmarkNewIlust'
      p = open('./test/test-bookmarks_new_ilust.htm', 'r')
      page = BeautifulSoup(p.read())
      result = PixivNewIllustBookmark(page)

      self.assertEqual(len(result.imageList), 20)

class TestMyPickPage(unittest.TestCase):
    def testMyPickPage(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test.image_12467674.html').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivImage(12467674,page)
        self.assertEqual(image.imageId, 12467674)
        print image.PrintInfo()
        #viewPage = br.follow_link(url_regex='mode='+image.imageMode+'&illust_id='+str(image.imageId))

class TestPixivTags(unittest.TestCase):
    def testMemberTagCheckPage(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-memberlist-checkpage.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)
        
        self.assertEqual(image.isLastPage, False)

    def testTagsListParsing(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-list.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseTags(page)
        
        self.assertEqual(len(image.itemList), 20)
        self.assertEqual(image.itemList[0].imageId, 26180887)
        self.assertEqual(image.itemList[0].bookmarkCount, 60)
        self.assertEqual(image.itemList[4].imageId, 25930505)
        self.assertEqual(image.itemList[4].bookmarkCount, 45)
        self.assertEqual(image.itemList[4].imageResponse, 1)

    def testTagsListParseMemberSearch(self):
        br = Browser()
        path = 'file:///' + os.path.abspath('./test/test-tags-memberlist.htm').replace(os.sep,'/')
        p = br.open(path, 'r')
        page = BeautifulSoup(p.read())
        image = PixivTags()
        image.parseMemberTags(page)

        self.assertEqual(len(image.itemList), 12)
      
if __name__ == '__main__':
##    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivArtist)
##    unittest.TextTestRunner(verbosity=5).run(suite)
##    print "================================================================"
##    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivImage)
##    unittest.TextTestRunner(verbosity=5).run(suite)
##    print "================================================================"
##    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivBookmark)
##    unittest.TextTestRunner(verbosity=5).run(suite)
##    print "================================================================"
##    suite = unittest.TestLoader().loadTestsFromTestCase(TestMyPickPage)
##    unittest.TextTestRunner(verbosity=5).run(suite)
##    print "================================================================"
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivTags)
    unittest.TextTestRunner(verbosity=5).run(suite)
