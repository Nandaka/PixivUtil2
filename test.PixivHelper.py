#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-
import PixivHelper
import os
import unittest
from PixivModel import PixivImage, PixivArtist
from BeautifulSoup import BeautifulSoup

class TestPixivHelper(unittest.TestCase):
  currPath = unicode(os.path.abspath('.'))
  
  def testSanitizeFilename(self):
    rootDir = '.'
    filename = '12345.jpg'
    currentDir = os.path.abspath('.')
    expected = currentDir + os.sep + filename        
    
    result = PixivHelper.sanitizeFilename(filename, rootDir)

    self.assertEqual(result, expected)
    self.assertTrue(len(result) < 255)

  def testSanitizeFilename2(self):
    rootDir = '.'
    filename = '12345.jpg'
    currentDir = os.path.abspath('.')
    expected = currentDir + os.sep + filename        
    
    result = PixivHelper.sanitizeFilename(filename, rootDir)

    self.assertEqual(result, expected)
    self.assertTrue(len(result) < 255)

  def testCreateFilename(self):
    p = open('./test/test-image.htm', 'r')
    page = BeautifulSoup(p.read())
    imageInfo = PixivImage(20623238, page)
    page.decompose()
    del page
    expected = u'test-image_files (1108823)\\20623238 07-27-2011 1200x1200 SAI&nbsp; \u3010\u3074\u304f\u30dd\u30d7\u3011\u30b9\u30da\u30fc\u30c9\u306e\u30a8\u30fc\u30b9 - \u3074\u304f\u30dd\u30d7 \u3074\u304f\u30dd\u30d7\u30c8\u30e9\u30f3\u30d7'
    nameFormat = '%member_token% (%member_id%)\%image_id% %works_date_only% %works_res% %works_tools% %title% - %tags%'
    result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ')
    self.assertEqual(result, expected)

  def testCreateFilenameUnicode(self):
    p = open('./test/test-image-unicode.htm', 'r')
    page = BeautifulSoup(p.read())
    imageInfo = PixivImage(9908869, page)
    page.decompose()
    del page
    
    expected = u'eyegasm (450777)\9908869 04-08-2010 594x990 \u304a\u7d75\u63cf\u304d\u30c1\u30e3\u30c3\u30c8&nbsp; VCR - \u30aa\u30ea\u30b8\u30ca\u30eb'
    nameFormat = '%member_token% (%member_id%)\%image_id% %works_date_only% %works_res% %works_tools% %title% - %tags%'
    result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ')
    self.assertEqual(result, expected)

  def testCreateAvatarFilenameFormatNoSubfolderNoRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%image_id% - %title%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = ''    
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    
    self.assertEqual(filename, self.currPath + os.sep + u'folder.jpg')

  def testCreateAvatarFilenameFormatWithSubfolderNoRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%member_token% (%member_id%)\%R-18%\%image_id% - %title% - %tags%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = ''    
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    self.assertEqual(filename, self.currPath + os.sep + u'kirabara29 (1107124)\\folder.jpg')

  def testCreateAvatarFilenameFormatNoSubfolderWithRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%image_id% - %title%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = os.path.abspath('.')
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    
    self.assertEqual(filename, targetDir + os.sep + u'folder.jpg')
                                                         
  def testCreateAvatarFilenameFormatWithSubfolderWithRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%member_token% (%member_id%)\%R-18%\%image_id% - %title% - %tags%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = os.path.abspath('.')
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    
    self.assertEqual(filename, targetDir + os.sep + u'kirabara29 (1107124)\\folder.jpg')

  def testCreateAvatarFilenameFormatNoSubfolderWithCustomRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%image_id% - %title%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = 'C:\\images'    
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    
    self.assertEqual(filename, u'C:\\images\\folder.jpg')
                                                         
  def testCreateAvatarFilenameFormatWithSubfolderWithCustomRootDir(self):
    p = open('./test/test-helper-avatar-name.htm', 'r')
    page = BeautifulSoup(p.read())
    artist = PixivArtist(mid=1107124, page=page)
    filenameFormat = '%member_token% (%member_id%)\%R-18%\%image_id% - %title% - %tags%'
    tagsSeparator = ' '
    tagsLimit = 0
    targetDir = 'C:\\images'    
    filename = PixivHelper.CreateAvatarFilename(filenameFormat, tagsSeparator, tagsLimit, artist, targetDir)
    
    self.assertEqual(filename, u'C:\\images\\kirabara29 (1107124)\\folder.jpg')                                                      

if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivHelper)
    unittest.TextTestRunner(verbosity=5).run(suite)
