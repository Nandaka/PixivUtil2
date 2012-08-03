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
    imageInfo = PixivImage(28865189, page)
    page.decompose()
    del page
    expected = unicode(u'ffei (554800)\\28865189_p0 07/25/2012 Manga 2P Photoshop 「SUN PLAY! 毒島先輩温感ポスター」サンプル - C82 R-18 おっぱい ローション 学園黙示録 極上のおっぱい 毒島冴子 水着 漫画 足.jpg')
    nameFormat = '%member_token% (%member_id%)\%urlFilename% %works_date_only% %works_res% %works_tools% %title% - %tags%'
    result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p0.jpg')
    print result
    self.assertEqual(result, expected)

  def testCreateFilenameUnicode(self):
    p = open('./test/test-image-unicode.htm', 'r')
    page = BeautifulSoup(p.read())
    imageInfo = PixivImage(2493913, page)
    page.decompose()
    del page
    
    expected = unicode(u'balzehn (267014)\\2493913 12/23/2008 852x1200 Photoshop SAI つけペン アラクネのいる日常２ - R-18 これは萌える ぱるぱるぱるぱる アラクネ ツンデレ ピロートークの上手さに定評のある兄弟 モンスター娘 モン娘のいる日常シリーズ 人外 魔物娘.jpg')
    nameFormat = '%member_token% (%member_id%)\%urlFilename% %works_date_only% %works_res% %works_tools% %title% - %tags%'
    result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img16/img/balzehn/2493913.jpg')
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
