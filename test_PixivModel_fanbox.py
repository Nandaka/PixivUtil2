#!/c/Python27/python.exe
# -*- coding: UTF-8 -*-


import sys
import os
import unittest
import re

from PixivModelFanbox import Fanbox, FanboxArtist, FanboxPost
import PixivHelper

temp = PixivHelper.__re_manga_index


class TestPixivModel_Fanbox(unittest.TestCase):
    currPath = str(os.path.abspath('.'))
    PixivHelper.GetLogger()

    def testFanboxSupportedArtist(self):
        p = open('./test/Fanbox_supported_artist.json', 'r').read()
        result = Fanbox(p)
        self.assertIsNotNone(result)

        self.assertEqual(len(result.supportedArtist), 19)
        self.assertTrue(7968 in result.supportedArtist)
        self.assertTrue(3931854 in result.supportedArtist)
        self.assertTrue(30716447 in result.supportedArtist)

    def testFanboxArtistPosts(self):
        p = open('./test/Fanbox_artist_posts.json', 'r').read()
        result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 15521131)
        self.assertTrue(result.hasNextPage)
        self.assertTrue(len(result.nextUrl) > 0)
        self.assertTrue(len(result.posts) > 0)

        for post in result.posts:
            self.assertFalse(post.is_restricted)

        # post-136761 image
        self.assertEqual(result.posts[0].imageId, 136761)
        self.assertTrue(len(result.posts[0].imageTitle) > 0)
        self.assertTrue(len(result.posts[0].coverImageUrl) > 0)
        self.assertEqual(result.posts[0].type, "image")
        self.assertEqual(len(result.posts[0].images), 5)

        # post-132919 text
        self.assertEqual(result.posts[2].imageId, 132919)
        self.assertTrue(len(result.posts[2].imageTitle) > 0)
        self.assertIsNone(result.posts[2].coverImageUrl)
        self.assertEqual(result.posts[2].type, "text")
        self.assertEqual(len(result.posts[2].images), 0)

        # post-79695 image
        self.assertEqual(result.posts[3].imageId, 79695)
        self.assertTrue(len(result.posts[3].imageTitle) > 0)
        self.assertIsNone(result.posts[3].coverImageUrl)
        self.assertEqual(result.posts[3].type, "image")
        self.assertEqual(len(result.posts[3].images), 4)

    def testFanboxArtistArticle(self):
        p = open('./test/Fanbox_artist_posts_article.json', 'r').read()
        result = FanboxArtist(190026, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 190026)
        self.assertTrue(result.hasNextPage)
        self.assertTrue(len(result.nextUrl) > 0)
        self.assertTrue(len(result.posts) > 0)

        # post-201946 article
        self.assertEqual(result.posts[0].imageId, 201946)
        self.assertTrue(len(result.posts[0].imageTitle) > 0)
        self.assertIsNone(result.posts[0].coverImageUrl)
        self.assertEqual(result.posts[0].type, "article")
        self.assertEqual(len(result.posts[0].images), 5)
        self.assertEqual(len(result.posts[0].body_text), 1292)
        # result.posts[0].WriteInfo("./201946.txt")

    def testFanboxArtistArticleFileMap(self):
        p = open('./test/creator_with_filemap.json', 'r').read()
        result = FanboxArtist(190026, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 190026)
        self.assertTrue(result.hasNextPage)
        self.assertTrue(len(result.nextUrl) > 0)
        self.assertTrue(len(result.posts) > 0)

        # post-201946 article
        self.assertEqual(result.posts[0].imageId, 210980)
        self.assertTrue(len(result.posts[0].imageTitle) > 0)
        self.assertIsNone(result.posts[0].coverImageUrl)
        self.assertEqual(result.posts[0].type, "article")
        self.assertEqual(len(result.posts[0].images), 15)
        self.assertEqual(len(result.posts[0].body_text), 3006)

        # result.posts[0].WriteInfo("./210980.txt")

    def testFanboxArtistVideo(self):
        p = open('./test/creator_posts_with_video.json', 'r').read()
        result = FanboxArtist(711048, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 711048)
        self.assertTrue(result.hasNextPage)
        self.assertTrue(len(result.nextUrl) > 0)
        self.assertTrue(len(result.posts) > 0)

        # post-201946 article
        self.assertEqual(result.posts[4].imageId, 330905)
        self.assertTrue(len(result.posts[4].imageTitle) > 0)
        self.assertEqual(result.posts[4].coverImageUrl, 'https://pixiv.pximg.net/c/1200x630_90_a2_g5/fanbox/public/images/post/330905/cover/3A2zPUg4s6iz17MM0Z45eWBj.jpeg')
        self.assertEqual(result.posts[4].type, "video")
        self.assertEqual(len(result.posts[4].images), 0)
        self.assertEqual(len(result.posts[4].body_text), 99)

        # result.posts[0].WriteInfo("./210980.txt")

    def testFanboxArtistArticleEmbedTwitter(self):
        p = open('./test/creator_embedMap.json', 'r').read()
        result = FanboxArtist(68813, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 68813)
        self.assertFalse(result.hasNextPage)
        self.assertTrue(len(result.posts) > 0)

        # post-201946 article
        self.assertEqual(result.posts[0].imageId, 285502)
        self.assertTrue(len(result.posts[0].imageTitle) > 0)
        self.assertEqual(result.posts[0].coverImageUrl, 'https://pixiv.pximg.net/c/1200x630_90_a2_g5/fanbox/public/images/post/285502/cover/orx9TCsiPFi5sgDdbvg4zwkX.jpeg')
        self.assertEqual(result.posts[0].type, "article")
        self.assertEqual(len(result.posts[0].images), 7)
        self.assertEqual(len(result.posts[0].body_text), 3095)

        # result.posts[0].WriteInfo("./285502.txt")

    def testFanboxArtistPostsNextPage(self):
        p2 = open('./test/Fanbox_artist_posts_nextpage.json', 'r').read()
        result = FanboxArtist(15521131, p2)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 15521131)
        self.assertFalse(result.hasNextPage)
        self.assertTrue(result.nextUrl is None)
        self.assertEqual(len(result.posts), 1)

    def testFanboxArtistPostsRestricted(self):
        p = open('./test/Fanbox_artist_posts_restricted.json', 'r').read()
        result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 15521131)
        self.assertTrue(result.hasNextPage)
        self.assertTrue(len(result.nextUrl) > 0)
        self.assertEqual(len(result.posts), 10)

        for post in result.posts:
            self.assertTrue(post.is_restricted)

    def testFanboxArtistPostsRestrictedNextPage(self):
        p = open('./test/Fanbox_artist_posts_next_page_restricted.json', 'r').read()
        result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 15521131)
        self.assertFalse(result.hasNextPage)
        self.assertTrue(result.nextUrl is None)
        self.assertEqual(len(result.posts), 6)

        self.assertTrue(result.posts[0].is_restricted)
        self.assertFalse(result.posts[1].is_restricted)

    def testFanboxFilename(self):
        p = open('./test/Fanbox_artist_posts.json', 'r').read()
        result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)
        root_dir = os.path.abspath(os.path.curdir)
        post = result.posts[0]
        image_url = post.images[0]
        current_page = 0
        fake_image_url = image_url.replace("{0}/".format(post.imageId), "{0}_p{1}_".format(post.imageId, current_page))

        re_page = temp.findall(fake_image_url)
        self.assertIsNotNone(re_page)
        self.assertEqual(re_page[0], "0")

        def simple_from_images():
            filename_format = '%title%_%urlFilename%'

            filename = PixivHelper.makeFilename(filename_format,
                                                post,
                                                artistInfo=result,
                                                tagsSeparator=" ",
                                                tagsLimit=0,
                                                fileUrl=fake_image_url,
                                                bookmark=None,
                                                searchTags='')
            filename = PixivHelper.sanitizeFilename(filename, root_dir)

            self.assertEqual(filename, root_dir + os.sep + "アスナさん０２_136761_p0_hcXl48iORoJykmrR3zPZEoUu.jpeg")
        simple_from_images()

        def more_format():
            # from images
            filename_format = '%member_id%' + os.sep + '%image_id%_p%page_index%_%title%_%urlFilename%_%works_date%'

            filename = PixivHelper.makeFilename(filename_format,
                                                post,
                                                artistInfo=result,
                                                tagsSeparator=" ",
                                                tagsLimit=0,
                                                fileUrl=fake_image_url,
                                                bookmark=None,
                                                searchTags='')
            filename = PixivHelper.sanitizeFilename(filename, root_dir)

            self.assertEqual(filename, root_dir + os.sep + "15521131" + os.sep + "136761_p0_アスナさん０２_136761_p0_hcXl48iORoJykmrR3zPZEoUu_2018-08-26 20_28_16.jpeg")
        more_format()

        def cover_more_format():
            # https://pixiv.pximg.net/c/1200x630_90_a2_g5/fanbox/public/images/post/96862/cover/6SRpcQwIUuJdeZbhn5q85l9x.jpeg
            fake_image_url = post.coverImageUrl.replace("{0}/cover/".format(post.imageId), "{0}_".format(post.imageId))
            print(fake_image_url)
            filename_format = '%member_id%' + os.sep + '%image_id%_%title%_%urlFilename%_%works_date%'

            filename = PixivHelper.makeFilename(filename_format,
                                                post,
                                                artistInfo=result,
                                                tagsSeparator=" ",
                                                tagsLimit=0,
                                                fileUrl=fake_image_url,
                                                bookmark=None,
                                                searchTags='')
            filename = PixivHelper.sanitizeFilename(filename, root_dir)

            self.assertEqual(filename, root_dir + os.sep + "15521131" + os.sep + "136761_アスナさん０２_136761_OqhhcslOfbzZpHyTfJNtnIWm_2018-08-26 20_28_16.jpeg")
        cover_more_format()


if __name__ == '__main__':
        # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivModel_Fanbox)
    unittest.TextTestRunner(verbosity=5).run(suite)
