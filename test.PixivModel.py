# -*- coding: UTF-8 -*-

from PixivModel import PixivArtist, PixivImage, PixivModelException
from BeautifulSoup import BeautifulSoup
import unittest

class TestPixivModel(unittest.TestCase):
    def testPixivArtist(self):
      print '\nTesting member page'
      p = open('./test/test.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        artist = PixivArtist(363073, page)
        artist.PrintInfo()
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(artist, None)
      self.assertEqual(artist.artistId, 363073)

    def testPixivArtistNoImage(self):
      print '\nTesting member page - no image'
      p = open('./test/test-noimage.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivModelException):
          PixivArtist(363073, page)
      page.decompose()
      del page
      
    def testPixivArtistNoMember(self):
      print '\nTesting member page - no member'
      p = open('./test/test-nouser.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivModelException):
          PixivArtist(363073, page)
      page.decompose()
      del page

    def testPixivImage(self):
      print '\nTesting image page - big'
      p = open('./test/test-image.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(20623238, page)
        image.PrintInfo()
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 20623238)
      self.assertEqual(image.imageMode, 'big')

    def testPixivImageNoImage(self):
      print '\nTesting image page - no image'
      p = open('./test/test-noimage2.htm', 'r')
      page = BeautifulSoup(p.read())
      with self.assertRaises(PixivModelException):
          PixivImage(20623238, page)
      page.decompose()
      del page

    def testPixivImage(self):
      print '\nTesting image page - manga'
      p = open('./test/test-image-manga.htm', 'r')
      page = BeautifulSoup(p.read())
      try:
        image = PixivImage(20581412, page)
        image.PrintInfo()
      except PixivModelException as ex:
        print ex
      page.decompose()
      del page
      self.assertNotEqual(image, None)
      self.assertEqual(image.imageId, 20581412)
      self.assertEqual(image.imageMode, 'manga')

    def testPixivImageParseBig(self):
      print '\nTesting parse Big Image'
      p = open('./test/test-bigimage.htm', 'r')
      page = BeautifulSoup(p.read())
      image = PixivImage()
      urls = image.ParseImages(page, mode='big')
      self.assertEqual(len(urls), 1)
      imageId = urls[0].split('/')[-1].split('.')[0]
      print 'imageId:',imageId
      self.assertEqual(int(imageId), 20644633)

    def testPixivImageParseManga(self):
      print '\nTesting parse Manga Images'
      p = open('./test/test-manga.htm', 'r')
      page = BeautifulSoup(p.read())
      image = PixivImage()
      urls = image.ParseImages(page, mode='manga')
      self.assertEqual(len(urls), 39)
      imageId = urls[0].split('/')[-1].split('.')[0]
      print 'imageId:',imageId
      self.assertEqual(imageId, '20592252_big_p0')

if __name__ == '__main__':
    unittest.main()
