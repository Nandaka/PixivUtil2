#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-
import PixivHelper
import os
import unittest
import json
from PixivModel import PixivImage, PixivArtist
from BeautifulSoup import BeautifulSoup

class TestPixivModel_WhiteCube(unittest.TestCase):
  currPath = unicode(os.path.abspath('.'))
  PixivHelper.GetLogger()


  def testParseLoginForm(self):
    p = open('./test/pixiv-whitecube-main.html', 'r')
    page = BeautifulSoup(p.read())
    init_config = page.find('input', attrs={'id':'init-config'})
    js_init_config = json.loads(init_config['value'])
    self.assertIsNotNone(js_init_config)
    self.assertIsNotNone(js_init_config["pixiv.context.token"])


if __name__ == '__main__':
    #unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivModel_WhiteCube)
    unittest.TextTestRunner(verbosity=5).run(suite)
