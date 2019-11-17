#!C:/Python37-32/python
# -*- coding: UTF-8 -*-

import json
import os
import unittest

from bs4 import BeautifulSoup

import PixivHelper
from PixivImage import PixivImage


class TestPixivHelper(unittest.TestCase):
    currPath = os.path.abspath('.')
    PixivHelper.GetLogger()

    def testSanitizeFilename(self):
        rootDir = '.'
        filename = u'12345.jpg'
        currentDir = os.path.abspath('.')
        expected = currentDir + os.sep + filename

        result = PixivHelper.sanitizeFilename(filename, rootDir)

        self.assertEqual(result, expected)
        self.assertTrue(len(result) < 255)

    def testSanitizeFilename2(self):
        rootDir = '.'
        filename = u'12345.jpg'
        currentDir = os.path.abspath('.')
        expected = currentDir + os.sep + filename

        result = PixivHelper.sanitizeFilename(filename, rootDir)

        self.assertEqual(result, expected)
        self.assertTrue(len(result) < 255)

    def testCreateMangaFilename(self):
        p = open(r'./test/test-image-manga.htm', 'r', encoding='utf-8')
        page = p.read()
        imageInfo = PixivImage(28820443, page)
        imageInfo.imageCount = 100

        # cross check with json value for artist info
        js_file = open('./test/detail-554800.json', 'r')
        js = json.load(js_file)

        self.assertEqual(imageInfo.artist.artistId, str(js["user"]["id"]))
        self.assertEqual(imageInfo.artist.artistToken, js["user"]["account"])
        self.assertEqual(imageInfo.artist.artistAvatar, js["user"]["profile_image_urls"]["medium"].replace("_170", ""))

        nameFormat = '%member_token% (%member_id%)\\%urlFilename% %page_number% %works_date_only% %works_res% %works_tools% %title%'

        expected = u'maidoll (554800)\\28865189_p0 001 07/22/12 Multiple images: 2P C82おまけ本 「沙耶は俺の嫁」サンプル.jpg'
        result = PixivHelper.makeFilename(nameFormat,
                                          imageInfo,
                                          artistInfo=None,
                                          tagsSeparator=' ',
                                          fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p0.jpg')
        # print(result)
        self.assertEqual(result, expected)

        expected = u'maidoll (554800)\\28865189_p14 015 07/22/12 Multiple images: 2P C82おまけ本 「沙耶は俺の嫁」サンプル.jpg'
        result = PixivHelper.makeFilename(nameFormat,
                                          imageInfo,
                                          artistInfo=None,
                                          tagsSeparator=' ',
                                          fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p14.jpg')
        # print(result)
        self.assertEqual(result, expected)

        expected = u'maidoll (554800)\\28865189_p921 922 07/22/12 Multiple images: 2P C82おまけ本 「沙耶は俺の嫁」サンプル.jpg'
        result = PixivHelper.makeFilename(nameFormat,
                                          imageInfo,
                                          artistInfo=None,
                                          tagsSeparator=' ',
                                          fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p921.jpg')
        # print(result)
        self.assertEqual(result, expected)

    def testCreateFilenameUnicode(self):
        p = open('./test/test-image-unicode.htm', 'r', encoding='utf-8')
        page = p.read()
        imageInfo = PixivImage(2493913, page)

        # cross check with json value for artist info
        js_file = open('./test/detail-267014.json', 'r', encoding='utf-8')
        js = json.load(js_file)

        self.assertEqual(imageInfo.artist.artistId, str(js["user"]["id"]))
        self.assertEqual(imageInfo.artist.artistToken, js["user"]["account"])
        self.assertEqual(imageInfo.artist.artistAvatar, js["user"]["profile_image_urls"]["medium"].replace("_170", ""))

        nameFormat = '%member_token% (%member_id%)\\%urlFilename% %works_date_only% %works_res% %works_tools% %title%'
        expected = u'balzehn (267014)\\2493913 12/23/08 852x1200 アラクネのいる日常２.jpg'
        result = PixivHelper.makeFilename(nameFormat,
                                          imageInfo,
                                          artistInfo=None,
                                          tagsSeparator=' ',
                                          fileUrl='http://i2.pixiv.net/img16/img/balzehn/2493913.jpg')
        # print(result)
        self.assertEqual(result, expected)

#    def testcreateAvatarFilenameFormatNoSubfolderNoRootDir(self):
#        p = open('./test/test-helper-avatar-name.htm', 'r')
#        page = BeautifulSoup(p.read())
#        artist = PixivArtist(mid=1107124, page=page)
#        targetDir = ''
#        # change the config value
#        _config = PixivConfig.PixivConfig()
#        _config.avatarNameFormat = ''
#        _config.filenameFormat = '%image_id% - %title%'
#        _config.tagsSeparator = ' '
#        _config.tagsLimit = 0
#        PixivHelper.setConfig(_config)
#        filename = PixivHelper.createAvatarFilename(artist, targetDir)
#        self.assertEqual(filename, self.currPath + os.sep + u'folder.jpg')

#    def testcreateAvatarFilenameFormatWithSubfolderNoRootDir(self):
#        p = open('./test/test-helper-avatar-name.htm', 'r')
#        page = BeautifulSoup(p.read())
#        artist = PixivArtist(mid=1107124, page=page)
#        targetDir = ''
#        _config = PixivConfig.PixivConfig()
#        _config.avatarNameFormat = ''
#        _config.filenameFormat = '%member_token% (%member_id%)' + os.sep + '%image_id% - %title% - %tags%'
#        _config.tagsSeparator = ' '
#        _config.tagsLimit = 0
#        PixivHelper.setConfig(_config)
#        filename = PixivHelper.createAvatarFilename(artist, targetDir)
#        self.assertEqual(filename, self.currPath + os.sep + u'kirabara29 (1107124)' + os.sep + 'folder.jpg')

#    def testcreateAvatarFilenameFormatNoSubfolderWithRootDir3(self):
#        p = open('./test/test-helper-avatar-name.htm', 'r')
#        page = BeautifulSoup(p.read())
#        artist = PixivArtist(mid=1107124, page=page)
#        targetDir = os.path.abspath('.')
#        _config = PixivConfig.PixivConfig()
#        _config.avatarNameFormat = ''
#        _config.filenameFormat = '%image_id% - %title%'
#        _config.tagsSeparator = ' '
#        _config.tagsLimit = 0
#        filename = PixivHelper.createAvatarFilename(artist, targetDir)
#        self.assertEqual(filename, targetDir + os.sep + u'folder.jpg')

#    def testcreateAvatarFilenameFormatWithSubfolderWithRootDir4(self):
#        p = open('./test/test-helper-avatar-name.htm', 'r')
#        page = BeautifulSoup(p.read())
#        artist = PixivArtist(mid=1107124, page=page)
#        targetDir = os.path.abspath('.')
#        _config = PixivConfig.PixivConfig()
#        _config.avatarNameFormat = ''
#        _config.filenameFormat = '%member_token% (%member_id%)' + os.sep + '%R-18%' + os.sep + '%image_id% - %title% - %tags%'
#        _config.tagsSeparator = ' '
#        _config.tagsLimit = 0
#        filename = PixivHelper.createAvatarFilename(artist, targetDir)
#        self.assertEqual(filename, targetDir + os.sep + u'kirabara29 (1107124)' + os.sep + 'folder.jpg')

#    def testcreateAvatarFilenameFormatNoSubfolderWithCustomRootDir5(self):
#        p = open('./test/test-helper-avatar-name.htm', 'r')
#        page = BeautifulSoup(p.read())
#        artist = PixivArtist(mid=1107124, page=page)
#        targetDir = os.path.abspath(os.sep + 'images')
#        _config = PixivConfig.PixivConfig()
#        _config.avatarNameFormat = ''
#        _config.filenameFormat = '%image_id% - %title%'
#        _config.tagsSeparator = ' '
#        _config.tagsLimit = 0
#        filename = PixivHelper.createAvatarFilename(artist, targetDir)
#        self.assertEqual(filename, targetDir + os.sep + 'folder.jpg')

#    def testcreateAvatarFilenameFormatWithSubfolderWithCustomRootDir6(self):
#        p = open('./test/test-helper-avatar-name.htm', 'r')
#        page = BeautifulSoup(p.read())
#        artist = PixivArtist(mid=1107124, page=page)
#        targetDir = os.path.abspath(os.sep + 'images')
#        _config = PixivConfig.PixivConfig()
#        _config.avatarNameFormat = ''
#        _config.filenameFormat = '%member_token% (%member_id%)' + os.sep + '%R-18%' + os.sep + '%image_id% - %title% - %tags%'
#        _config.tagsSeparator = ' '
#        _config.tagsLimit = 0
#        filename = PixivHelper.createAvatarFilename(artist, targetDir)
#        self.assertEqual(filename, targetDir + os.sep + 'kirabara29 (1107124)' + os.sep + 'folder.jpg')

    def testParseLoginError(self):
        p = open('./test/test-login-error.htm', 'r', encoding='utf-8')
        page = BeautifulSoup(p.read())
        r = page.findAll('span', attrs={'class': 'error'})
        self.assertTrue(len(r) > 0)
        self.assertEqual(u'Please ensure your pixiv ID, email address and password is entered correctly.', r[0].string)

    def testParseLoginForm(self):
        p = open('./test/test-login-form.html', 'r', encoding='utf-8')
        page = BeautifulSoup(p.read())
        r = page.findAll('form', attrs={'action': '/login.php'})
        # print(r)
        self.assertTrue(len(r) > 0)


if __name__ == '__main__':
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivHelper)
    unittest.TextTestRunner(verbosity=5).run(suite)
