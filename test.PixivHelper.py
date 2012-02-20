import PixivHelper
import os
import unittest

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

if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivHelper)
    unittest.TextTestRunner(verbosity=5).run(suite)
