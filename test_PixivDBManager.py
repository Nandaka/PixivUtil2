#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-
from __future__ import print_function

from PixivDBManager import PixivDBManager
from PixivModel import PixivListItem
from PixivConfig import PixivConfig

LIST_SIZE = 9
config = PixivConfig()
config.loadConfig()


class TestPixivDBManager(object):
    def test_ImportListTxt(self):
        DB = PixivDBManager(target="test.db.sqlite")
        DB.createDatabase()
        l = PixivListItem.parseList("test.list.txt", config.rootDirectory)
        result = DB.importList(l)
        # self.assertEqual(result, 0)
        assert result == 0

    def test_SelectMembersByLastDownloadDate(self):
        DB = PixivDBManager(target="test.db.sqlite")
        DB.createDatabase()
        l = PixivListItem.parseList("test.list.txt", config.rootDirectory)
        result = DB.selectMembersByLastDownloadDate(7)
        # self.assertEqual(len(result), LIST_SIZE)
        assert len(result) == LIST_SIZE
        for item in result:
            print(item.memberId, item.path)

    def test_SelectAllMember(self):
        DB = PixivDBManager(target="test.db.sqlite")
        DB.createDatabase()
        l = PixivListItem.parseList("test.list.txt", config.rootDirectory)
        result = DB.selectAllMember()
        # self.assertEqual(len(result), LIST_SIZE)
        assert len(result) == LIST_SIZE
        for item in result:
            print(item.memberId, item.path)


# if __name__ == '__main__':
#     suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivDBManager)
#     unittest.TextTestRunner(verbosity=5).run(suite)
#     print("================================================================")
