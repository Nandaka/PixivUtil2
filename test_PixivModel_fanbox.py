#!C:/Python37-32/python
# -*- coding: UTF-8 -*-

import os
import unittest

import demjson

import PixivHelper
from PixivModelFanbox import Fanbox, FanboxArtist, FanboxPost

temp = PixivHelper.__re_manga_index


class TestPixivModel_Fanbox(unittest.TestCase):
    currPath = os.path.abspath('.')
    PixivHelper.get_logger()

    def testFanboxSupportedArtist(self):
        # https://fanbox.pixiv.net/api/plan.listSupporting
        p = open('./test/Fanbox_supported_artist.json', 'r', encoding="utf-8").read()
        result = Fanbox(p)
        self.assertIsNotNone(result)

        self.assertEqual(len(result.supportedArtist), 52)
        self.assertTrue(4820 in result.supportedArtist)
        self.assertTrue(11443 in result.supportedArtist)
        self.assertTrue(226267 in result.supportedArtist)

    def testFanboxArtistPosts(self):
        p = open('./test/Fanbox_artist_posts.json', 'r', encoding="utf-8").read()
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
        p = open('./test/Fanbox_artist_posts_article.json', 'r', encoding="utf-8").read()
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
        p = open('./test/creator_with_filemap.json', 'r', encoding="utf-8").read()
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
        p = open('./test/creator_posts_with_video.json', 'r', encoding="utf-8").read()
        result = FanboxArtist(711048, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 711048)
        self.assertTrue(result.hasNextPage)
        self.assertTrue(len(result.nextUrl) > 0)
        self.assertTrue(len(result.posts) > 0)

        # post-201946 article
        self.assertEqual(result.posts[4].imageId, 330905)
        self.assertTrue(len(result.posts[4].imageTitle) > 0)
        self.assertEqual(result.posts[4].coverImageUrl, u'https://pixiv.pximg.net/c/1200x630_90_a2_g5/fanbox/public/images/post/330905/cover/3A2zPUg4s6iz17MM0Z45eWBj.jpeg')
        self.assertEqual(result.posts[4].type, "video")
        self.assertEqual(len(result.posts[4].images), 0)
        self.assertEqual(len(result.posts[4].body_text), 99)

        # result.posts[0].WriteInfo("./210980.txt")

    def testFanboxArtistArticleEmbedTwitter(self):
        p = open('./test/creator_embedMap.json', 'r', encoding="utf-8").read()
        result = FanboxArtist(68813, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 68813)
        self.assertFalse(result.hasNextPage)
        self.assertTrue(len(result.posts) > 0)

        # post-201946 article
        self.assertEqual(result.posts[0].imageId, 285502)
        self.assertTrue(len(result.posts[0].imageTitle) > 0)
        self.assertEqual(result.posts[0].coverImageUrl, u'https://pixiv.pximg.net/c/1200x630_90_a2_g5/fanbox/public/images/post/285502/cover/orx9TCsiPFi5sgDdbvg4zwkX.jpeg')
        self.assertEqual(result.posts[0].type, "article")
        self.assertEqual(len(result.posts[0].images), 7)
        self.assertEqual(len(result.posts[0].body_text), 3095)

        # result.posts[0].WriteInfo("./285502.txt")

    def testFanboxArtistPostsNextPage(self):
        # https://fanbox.pixiv.net/api/post.listCreator?userId=91029&maxPublishedDatetime=2019-07-25%2004%3A27%3A54&maxId=481268&limit=10
        p2 = open('./test/Fanbox_artist_posts_nextpage.json', 'r', encoding="utf-8").read()
        result = FanboxArtist(91029, p2)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 91029)
        self.assertTrue(result.hasNextPage)
        self.assertTrue(result.nextUrl is not None)
        self.assertEqual(len(result.posts), 10)

    def testFanboxArtistPostsRestricted(self):
        p = open('./test/Fanbox_artist_posts_restricted.json', 'r', encoding="utf-8").read()
        result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 15521131)
        self.assertTrue(result.hasNextPage)
        self.assertTrue(len(result.nextUrl) > 0)
        self.assertEqual(len(result.posts), 10)

        for post in result.posts:
            self.assertTrue(post.is_restricted)

    def testFanboxArtistPostsRestrictedNextPage(self):
        p = open('./test/Fanbox_artist_posts_next_page_restricted.json', 'r', encoding="utf-8").read()
        result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)

        self.assertEqual(result.artistId, 15521131)
        self.assertFalse(result.hasNextPage)
        self.assertTrue(result.nextUrl is None)
        self.assertEqual(len(result.posts), 6)

        self.assertTrue(result.posts[0].is_restricted)
        self.assertFalse(result.posts[1].is_restricted)

    def testFanboxOldApi(self):
        p = open('./test/fanbox-posts-old-api.json', 'r', encoding="utf-8").read()
        result = FanboxArtist(104409, p)
        self.assertIsNotNone(result)

        self.assertEqual(len(result.posts), 2)
        self.assertEqual(result.posts[0].imageId, 916)
        self.assertEqual(len(result.posts[0].images), 8)
        print(result.posts[0].images)
        self.assertEqual(result.posts[1].imageId, 915)
        self.assertEqual(len(result.posts[1].images), 1)
        print(result.posts[1].images)

    def testFanboxNewApi(self):
        p = open('./test/fanbox-posts-new-api.json', 'r', encoding="utf-8").read()
        result = FanboxArtist(104409, p)
        self.assertIsNotNone(result)

        self.assertEqual(len(result.posts), 10)
        self.assertEqual(result.posts[0].imageId, 577968)
        self.assertEqual(len(result.posts[0].images), 2)
        self.assertEqual(result.posts[1].imageId, 535518)
        self.assertEqual(len(result.posts[1].images), 2)

    def testFanboxNewApi2_MultiImages(self):
        p = open('./test/Fanbox_post_with_multi_images.json', 'r', encoding="utf-8").read()
        js = demjson.decode(p)
        result = FanboxPost(855025, None, js["body"])
        self.assertIsNotNone(result)

        self.assertEqual(result.imageId, 855025)
        self.assertEqual(len(result.images), 2)
        self.assertEqual(len(result.embeddedFiles), 3)
        self.assertIsNotNone(result.coverImageUrl)
        self.assertFalse(result.coverImageUrl in result.images)

    def testFanboxNewApi2_Files(self):
        p = open('./test/Fanbox_post_with_files.json', 'r', encoding="utf-8").read()
        js = demjson.decode(p)
        result = FanboxPost(685832, None, js["body"])
        self.assertIsNotNone(result)

        self.assertEqual(result.imageId, 685832)
        self.assertEqual(len(result.images), 1)
        self.assertEqual(len(result.embeddedFiles), 2)
        self.assertIsNotNone(result.coverImageUrl)
        self.assertFalse(result.coverImageUrl in result.images)

    def testFanboxFilename(self):
        p = open('./test/Fanbox_artist_posts.json', 'r', encoding="utf-8").read()
        result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)
        root_dir = os.path.abspath(os.path.curdir)
        post = result.posts[0]
        image_url = post.images[0]
        current_page = 0
        fake_image_url = image_url.replace("{0}/".format(post.imageId), "{0}_p{1}_".format(post.imageId, current_page))

        re_page = temp.findall(fake_image_url)
        self.assertIsNotNone(re_page)
        self.assertEqual(re_page[0], u"0")

        def simple_from_images():
            filename_format = '%title%_%urlFilename%'

            filename = PixivHelper.make_filename(filename_format,
                                                 post,
                                                 artistInfo=result,
                                                 tagsSeparator=" ",
                                                 tagsLimit=0,
                                                 fileUrl=fake_image_url,
                                                 bookmark=None,
                                                 searchTags='')
            filename = PixivHelper.sanitize_filename(filename, root_dir)

            self.assertEqual(filename, root_dir + os.sep + u"アスナさん０２_136761_p0_hcXl48iORoJykmrR3zPZEoUu.jpeg")
        simple_from_images()

        def more_format():
            # from images
            filename_format = '%member_id%' + os.sep + '%image_id%_p%page_index%_%title%_%urlFilename%_%works_date%'

            filename = PixivHelper.make_filename(filename_format,
                                                 post,
                                                 artistInfo=result,
                                                 tagsSeparator=" ",
                                                 tagsLimit=0,
                                                 fileUrl=fake_image_url,
                                                 bookmark=None,
                                                 searchTags='')
            filename = PixivHelper.sanitize_filename(filename, root_dir)

            self.assertEqual(filename, root_dir + os.sep + u"15521131" + os.sep + u"136761_p0_アスナさん０２_136761_p0_hcXl48iORoJykmrR3zPZEoUu_2018-08-26 20_28_16.jpeg")
        more_format()

        def cover_more_format():
            # https://pixiv.pximg.net/c/1200x630_90_a2_g5/fanbox/public/images/post/96862/cover/6SRpcQwIUuJdeZbhn5q85l9x.jpeg
            fake_image_url = post.coverImageUrl.replace("{0}/cover/".format(post.imageId), "{0}_".format(post.imageId))
            print(fake_image_url)
            filename_format = '%member_id%' + os.sep + '%image_id%_%title%_%urlFilename%_%works_date%'

            filename = PixivHelper.make_filename(filename_format,
                                                 post,
                                                 artistInfo=result,
                                                 tagsSeparator=" ",
                                                 tagsLimit=0,
                                                 fileUrl=fake_image_url,
                                                 bookmark=None,
                                                 searchTags='')
            filename = PixivHelper.sanitize_filename(filename, root_dir)

            self.assertEqual(filename, root_dir + os.sep + u"15521131" + os.sep + u"136761_アスナさん０２_136761_OqhhcslOfbzZpHyTfJNtnIWm_2018-08-26 20_28_16.jpeg")
        cover_more_format()


if __name__ == '__main__':
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivModel_Fanbox)
    unittest.TextTestRunner(verbosity=5).run(suite)
