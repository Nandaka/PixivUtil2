#!C:/Python37-32/python
# -*- coding: UTF-8 -*-

import unittest
import common.PixivConstant as PixivConstant
from PixivDBManager import PixivDBManager
from model.PixivListItem import PixivListItem

LIST_SIZE = 9
root_directory = '.'
PixivConstant.PIXIVUTIL_LOG_FILE = 'pixivutil.test.log'


class TestPixivDBManager(unittest.TestCase):
    def test_ImportListTxt(self):
        DB = PixivDBManager(root_directory=".", target="test.db.sqlite")
        DB.migrateDatabase()
        members = PixivListItem.parseList("test.list.txt", root_directory)
        result = DB.importList(members)
        # self.assertEqual(result, 0)
        assert result == 0

    def test_SelectMembersByLastDownloadDate(self):
        DB = PixivDBManager(root_directory=".", target="test.db.sqlite")
        DB.migrateDatabase()
        result = DB.selectMembersByLastDownloadDate(7)
        # self.assertEqual(len(result), LIST_SIZE)
        assert len(result) == LIST_SIZE
        for item in result:
            print(item.memberId, item.path)

    def test_SelectAllMember(self):
        DB = PixivDBManager(root_directory=".", target="test.db.sqlite")
        DB.migrateDatabase()
        result = DB.selectAllMember()
        # self.assertEqual(len(result), LIST_SIZE)
        assert len(result) == LIST_SIZE
        for item in result:
            print(item.memberId, item.path)


# if __name__ == '__main__':
#     suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivDBManager)
#     unittest.TextTestRunner(verbosity=5).run(suite)
#     print("================================================================")
