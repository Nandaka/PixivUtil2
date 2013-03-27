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

  def testCreateMangaFilename(self):
    p = open('./test/test-image-manga.htm', 'r')
    page = BeautifulSoup(p.read())
    imageInfo = PixivImage(28820443, page)
    imageInfo.imageCount = 100
    page.decompose()
    del page
    print imageInfo.PrintInfo()
    nameFormat = '%member_token% (%member_id%)\%urlFilename% %page_number% %works_date_only% %works_res% %works_tools% %title% - %tags%'

    expected = unicode(u'ffei (554800)\\28865189_p0 001 07-23-2012 Manga 2P Photoshop C82\u304a\u307e\u3051\u672c \u300c\u6c99\u8036\u306f\u4ffa\u306e\u5ac1\u300d\u30b5\u30f3\u30d7\u30eb - C82 R-18 \u304a\u3063\u3071\u3044 \u3076\u3063\u304b\u3051 \u5b66\u5712\u9ed9\u793a\u9332 \u6f2b\u753b \u773c\u93e1 \u9ad8\u57ce\u6c99\u8036.jpg')
    result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p0.jpg')
    self.assertEqual(result, expected)

    expected = unicode(u'ffei (554800)\\28865189_p14 015 07-23-2012 Manga 2P Photoshop C82\u304a\u307e\u3051\u672c \u300c\u6c99\u8036\u306f\u4ffa\u306e\u5ac1\u300d\u30b5\u30f3\u30d7\u30eb - C82 R-18 \u304a\u3063\u3071\u3044 \u3076\u3063\u304b\u3051 \u5b66\u5712\u9ed9\u793a\u9332 \u6f2b\u753b \u773c\u93e1 \u9ad8\u57ce\u6c99\u8036.jpg')
    result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p14.jpg')
    self.assertEqual(result, expected)
    
    expected = unicode(u'ffei (554800)\\28865189_p921 922 07-23-2012 Manga 2P Photoshop C82\u304a\u307e\u3051\u672c \u300c\u6c99\u8036\u306f\u4ffa\u306e\u5ac1\u300d\u30b5\u30f3\u30d7\u30eb - C82 R-18 \u304a\u3063\u3071\u3044 \u3076\u3063\u304b\u3051 \u5b66\u5712\u9ed9\u793a\u9332 \u6f2b\u753b \u773c\u93e1 \u9ad8\u57ce\u6c99\u8036.jpg')
    result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p921.jpg')
    self.assertEqual(result, expected)

  def testCreateFilenameUnicode(self):
    p = open('./test/test-image-unicode.htm', 'r')
    page = BeautifulSoup(p.read())
    imageInfo = PixivImage(2493913, page)
    page.decompose()
    del page
    print imageInfo.PrintInfo()
    nameFormat = '%member_token% (%member_id%)\%urlFilename% %works_date_only% %works_res% %works_tools% %title% - %tags%'
    
    expected = unicode(u'balzehn (267014)\\2493913 12-23-2008 852x1200 Photoshop SAI つけペン アラクネのいる日常２ - R-18 これは萌える ぱるぱるぱるぱる アラクネ ツンデレ ピロートークの上手さに定評のある兄弟 モンスター娘 モン娘のいる日常シリーズ 人外 魔物娘.jpg')
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

  def testParseLoginError(self):
    p = open('./test/test-login-error.htm', 'r')
    page = BeautifulSoup(p.read())
    r = page.findAll('span', attrs={'class':'error'})
    self.assertTrue(len(r)>0)
    self.assertEqual(u'Please ensure your pixiv ID, email address and password is entered correctly.', r[0].string)
    
if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivHelper)
    unittest.TextTestRunner(verbosity=5).run(suite)
