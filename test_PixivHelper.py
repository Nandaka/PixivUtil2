#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-


import os
import unittest
import json

import PixivHelper
from PixivModelWhiteCube import PixivImage
from PixivModel import PixivArtist
import PixivConfig

import bs4


def as_soup(text):
    return bs4.BeautifulSoup(text, features='lxml')

class TestPixivHelper(unittest.TestCase):
    currPath = str(os.path.abspath('.'))
    PixivHelper.GetLogger()

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
        page = as_soup(p.read())
        imageInfo = PixivImage(28820443, page)
        imageInfo.imageCount = 100
        page.decompose()
        del page

        # cross check with json value for artist info
        js_file = open('./test/detail-554800.json', 'r')
        js = json.load(js_file)

        self.assertEqual(imageInfo.artist.artistId, str(js["user"]["id"]))
        self.assertEqual(imageInfo.artist.artistToken, js["user"]["account"])
        self.assertEqual(imageInfo.artist.artistAvatar, js["user"]["profile_image_urls"]["medium"].replace("_170", ""))

        nameFormat = '%member_token% (%member_id%)\\%urlFilename% %page_number% %works_date_only% %works_res% %works_tools% %title%'

        expected = str('maidoll (554800)\\28865189_p0 001 07/22/12 Multiple images: 2P C82おまけ本 「沙耶は俺の嫁」サンプル.jpg')
        result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p0.jpg')
        # print(result)
        self.assertEqual(result, expected)

        expected = str('maidoll (554800)\\28865189_p14 015 07/22/12 Multiple images: 2P C82おまけ本 「沙耶は俺の嫁」サンプル.jpg')
        result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p14.jpg')
        # print(result)
        self.assertEqual(result, expected)

        expected = str('maidoll (554800)\\28865189_p921 922 07/22/12 Multiple images: 2P C82おまけ本 「沙耶は俺の嫁」サンプル.jpg')
        result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img26/img/ffei/28865189_p921.jpg')
        # print(result)
        self.assertEqual(result, expected)

    def testCreateFilenameUnicode(self):
        p = open('./test/test-image-unicode.htm', 'r')
        page = as_soup(p.read())
        imageInfo = PixivImage(2493913, page)
        page.decompose()
        del page

        # cross check with json value for artist info
        js_file = open('./test/detail-267014.json', 'r')
        js = json.load(js_file)

        self.assertEqual(imageInfo.artist.artistId, str(js["user"]["id"]))
        self.assertEqual(imageInfo.artist.artistToken, js["user"]["account"])
        self.assertEqual(imageInfo.artist.artistAvatar, js["user"]["profile_image_urls"]["medium"].replace("_170", ""))

        nameFormat = '%member_token% (%member_id%)\\%urlFilename% %works_date_only% %works_res% %works_tools% %title%'
        expected = str('balzehn (267014)\\2493913 12/23/08 852x1200 アラクネのいる日常２.jpg')
        result = PixivHelper.makeFilename(nameFormat, imageInfo, artistInfo=None, tagsSeparator=' ', fileUrl='http://i2.pixiv.net/img16/img/balzehn/2493913.jpg')
        # print(result)
        self.assertEqual(result, expected)

##    def testcreateAvatarFilenameFormatNoSubfolderNoRootDir(self):
##        p = open('./test/test-helper-avatar-name.htm', 'r')
##        page = as_soup(p.read())
##        artist = PixivArtist(mid=1107124, page=page)
##        targetDir = ''
##        # change the config value
##        _config = PixivConfig.PixivConfig()
##        _config.avatarNameFormat = ''
##        _config.filenameFormat = '%image_id% - %title%'
##        _config.tagsSeparator = ' '
##        _config.tagsLimit = 0
##        PixivHelper.setConfig(_config)
##        filename = PixivHelper.createAvatarFilename(artist, targetDir)
##        self.assertEqual(filename, self.currPath + os.sep + u'folder.jpg')

##    def testcreateAvatarFilenameFormatWithSubfolderNoRootDir(self):
##        p = open('./test/test-helper-avatar-name.htm', 'r')
##        page = as_soup(p.read())
##        artist = PixivArtist(mid=1107124, page=page)
##        targetDir = ''
##        _config = PixivConfig.PixivConfig()
##        _config.avatarNameFormat = ''
##        _config.filenameFormat = '%member_token% (%member_id%)' + os.sep + '%image_id% - %title% - %tags%'
##        _config.tagsSeparator = ' '
##        _config.tagsLimit = 0
##        PixivHelper.setConfig(_config)
##        filename = PixivHelper.createAvatarFilename(artist, targetDir)
##        self.assertEqual(filename, self.currPath + os.sep + u'kirabara29 (1107124)' + os.sep + 'folder.jpg')

##    def testcreateAvatarFilenameFormatNoSubfolderWithRootDir3(self):
##        p = open('./test/test-helper-avatar-name.htm', 'r')
##        page = as_soup(p.read())
##        artist = PixivArtist(mid=1107124, page=page)
##        targetDir = os.path.abspath('.')
##        _config = PixivConfig.PixivConfig()
##        _config.avatarNameFormat = ''
##        _config.filenameFormat = '%image_id% - %title%'
##        _config.tagsSeparator = ' '
##        _config.tagsLimit = 0
##        filename = PixivHelper.createAvatarFilename(artist, targetDir)
##        self.assertEqual(filename, targetDir + os.sep + u'folder.jpg')

##    def testcreateAvatarFilenameFormatWithSubfolderWithRootDir4(self):
##        p = open('./test/test-helper-avatar-name.htm', 'r')
##        page = as_soup(p.read())
##        artist = PixivArtist(mid=1107124, page=page)
##        targetDir = os.path.abspath('.')
##        _config = PixivConfig.PixivConfig()
##        _config.avatarNameFormat = ''
##        _config.filenameFormat = '%member_token% (%member_id%)' + os.sep + '%R-18%' + os.sep + '%image_id% - %title% - %tags%'
##        _config.tagsSeparator = ' '
##        _config.tagsLimit = 0
##        filename = PixivHelper.createAvatarFilename(artist, targetDir)
##        self.assertEqual(filename, targetDir + os.sep + u'kirabara29 (1107124)' + os.sep + 'folder.jpg')

##    def testcreateAvatarFilenameFormatNoSubfolderWithCustomRootDir5(self):
##        p = open('./test/test-helper-avatar-name.htm', 'r')
##        page = as_soup(p.read())
##        artist = PixivArtist(mid=1107124, page=page)
##        targetDir = os.path.abspath(os.sep + 'images')
##        _config = PixivConfig.PixivConfig()
##        _config.avatarNameFormat = ''
##        _config.filenameFormat = '%image_id% - %title%'
##        _config.tagsSeparator = ' '
##        _config.tagsLimit = 0
##        filename = PixivHelper.createAvatarFilename(artist, targetDir)
##        self.assertEqual(filename, targetDir + os.sep + 'folder.jpg')

##    def testcreateAvatarFilenameFormatWithSubfolderWithCustomRootDir6(self):
##        p = open('./test/test-helper-avatar-name.htm', 'r')
##        page = as_soup(p.read())
##        artist = PixivArtist(mid=1107124, page=page)
##        targetDir = os.path.abspath(os.sep + 'images')
##        _config = PixivConfig.PixivConfig()
##        _config.avatarNameFormat = ''
##        _config.filenameFormat = '%member_token% (%member_id%)' + os.sep + '%R-18%' + os.sep + '%image_id% - %title% - %tags%'
##        _config.tagsSeparator = ' '
##        _config.tagsLimit = 0
##        filename = PixivHelper.createAvatarFilename(artist, targetDir)
##        self.assertEqual(filename, targetDir + os.sep + 'kirabara29 (1107124)' + os.sep + 'folder.jpg')

    def testParseLoginError(self):
        p = open('./test/test-login-error.htm', 'r')
        page = as_soup(p.read())
        r = page.findAll('span', attrs={'class': 'error'})
        self.assertTrue(len(r) > 0)
        self.assertEqual('Please ensure your pixiv ID, email address and password is entered correctly.', r[0].string)

    def testParseLoginForm(self):
        p = open('./test/test-login-form.html', 'r')
        page = as_soup(p.read())
        r = page.findAll('form', attrs={'action': '/login.php'})
        # print(r)
        self.assertTrue(len(r) > 0)


if __name__ == '__main__':
        # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivHelper)
    unittest.TextTestRunner(verbosity=5).run(suite)
