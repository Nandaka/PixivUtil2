#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-
from __future__ import print_function

import sys
import os
import unittest

from PixivModelFanbox import Fanbox, FanboxArtist, FanboxPost
import PixivHelper


class TestPixivModel_Fanbox(unittest.TestCase):
    currPath = unicode(os.path.abspath('.'))
    PixivHelper.GetLogger()

    def testFanboxSupportedArtist(self):
        p = open('./test/Fanbox_supported_artist.json', 'r').read()
        result = Fanbox(p)
        self.assertIsNotNone(result)

        self.assertEqual(len(result.supportedArtist), 3)
        self.assertTrue(190026 in result.supportedArtist)
        self.assertTrue(685000 in result.supportedArtist)
        self.assertTrue(15521131 in result.supportedArtist)

    def testFanboxArtistPosts(self):
        p = open('./test/Fanbox_artist_posts.json', 'r').read()
        result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artist_id, 15521131)
        self.assertTrue(result.hasNextPage)
        self.assertTrue(len(result.nextUrl) > 0)
        self.assertTrue(len(result.posts) > 0)

        for post in result.posts:
            self.assertFalse(post.is_restricted)

        # post-136761
        self.assertEqual(result.posts[0].post_id, 136761)
        self.assertTrue(len(result.posts[0].title) > 0)
        self.assertTrue(len(result.posts[0].coverImageUrl) > 0)
        self.assertEqual(result.posts[0].type, "image")
        self.assertEqual(len(result.posts[0].images), 5)

        # post-132919
        self.assertEqual(result.posts[2].post_id, 132919)
        self.assertTrue(len(result.posts[2].title) > 0)
        self.assertIsNone(result.posts[2].coverImageUrl)
        self.assertEqual(result.posts[2].type, "text")
        self.assertEqual(len(result.posts[2].images), 0)

        # post-79695
        self.assertEqual(result.posts[3].post_id, 79695)
        self.assertTrue(len(result.posts[3].title) > 0)
        self.assertIsNone(result.posts[3].coverImageUrl)
        self.assertEqual(result.posts[3].type, "image")
        self.assertEqual(len(result.posts[3].images), 4)

    def testFanboxArtistPostsRestricted(self):
        p = open('./test/Fanbox_artist_posts_restricted.json', 'r').read()
        result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artist_id, 15521131)
        self.assertTrue(result.hasNextPage)
        self.assertTrue(len(result.nextUrl) > 0)
        self.assertTrue(len(result.posts) > 0)

        for post in result.posts:
            self.assertTrue(post.is_restricted)

if __name__ == '__main__':
        # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivModel_Fanbox)
    unittest.TextTestRunner(verbosity=5).run(suite)
