import PixivHelper
import os
import unittest
from PixivModel import PixivImage
from BeautifulSoup import BeautifulSoup

class TestPixivHelper(unittest.TestCase):
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

if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivHelper)
    unittest.TextTestRunner(verbosity=5).run(suite)
