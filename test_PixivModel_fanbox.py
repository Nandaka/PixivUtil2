#!C:/Python37-32/python
# -*- coding: UTF-8 -*-

import json
import os
import platform
import unittest

import PixivConstant
import PixivHelper
from PixivModelFanbox import FanboxArtist, FanboxPost

temp = PixivHelper.__re_manga_index
PixivConstant.PIXIVUTIL_LOG_FILE = 'pixivutil.test.log'


class TestPixivModel_Fanbox(unittest.TestCase):
    currPath = os.path.abspath('.')
    PixivHelper.get_logger()

    def testFanboxSupportedArtist(self):
        # https://fanbox.pixiv.net/api/plan.listSupporting
        reader = open('./test/Fanbox_supported_artist.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()
        result = FanboxArtist.parseArtistIds(p)
        self.assertIsNotNone(result)

        self.assertEqual(len(result), 52)
        self.assertTrue('4820' in result)
        self.assertTrue('11443' in result)
        self.assertTrue('226267' in result)

    def testFanboxArtistPosts(self):
        reader = open('./test/Fanbox_artist_posts.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()

        artist = FanboxArtist(15521131, "", "", None)
        result = artist.parsePosts(p)
        # result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)

        self.assertEqual(artist.artistId, 15521131)
        self.assertTrue(artist.hasNextPage)
        self.assertTrue(len(artist.nextUrl) > 0)
        self.assertTrue(len(result) > 0)

        for post in result:
            self.assertFalse(post.is_restricted)

        # post-136761 image
        self.assertEqual(result[0].imageId, 136761)
        self.assertTrue(len(result[0].imageTitle) > 0)
        self.assertTrue(len(result[0].coverImageUrl) > 0)
        self.assertEqual(result[0].type, "image")
        self.assertEqual(len(result[0].images), 5)

        # post-132919 text
        self.assertEqual(result[2].imageId, 132919)
        self.assertTrue(len(result[2].imageTitle) > 0)
        self.assertIsNotNone(result[2].coverImageUrl)
        self.assertEqual(result[2].type, "text")
        self.assertEqual(len(result[2].images), 0)

        # post-79695 image
        self.assertEqual(result[3].imageId, 79695)
        self.assertTrue(len(result[3].imageTitle) > 0)
        self.assertIsNotNone(result[3].coverImageUrl)
        self.assertEqual(result[3].type, "image")
        self.assertEqual(len(result[3].images), 4)

    def testFanboxArtistArticle(self):
        reader = open('./test/Fanbox_artist_posts_article.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()

        artist = FanboxArtist(190026, "", "", None)
        result = artist.parsePosts(p)
        # result = FanboxArtist(190026, p)
        self.assertIsNotNone(result)

        self.assertEqual(artist.artistId, 190026)
        self.assertTrue(artist.hasNextPage)
        self.assertTrue(len(artist.nextUrl) > 0)
        self.assertTrue(len(result) > 0)

        # post-201946 article
        self.assertEqual(result[0].imageId, 201946)
        self.assertTrue(len(result[0].imageTitle) > 0)
        self.assertIsNotNone(result[0].coverImageUrl)
        self.assertEqual(result[0].type, "article")
        self.assertEqual(len(result[0].images), 5)
        self.assertEqual(len(result[0].body_text), 1312)
        # result.posts[0].WriteInfo("./201946.txt")

    def testFanboxArtistArticleFileMap(self):
        reader = open('./test/creator_with_filemap.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()
        artist = FanboxArtist(190026, "", "", None)
        result = artist.parsePosts(p)
        # result = FanboxArtist(190026, p)
        self.assertIsNotNone(result)

        self.assertEqual(artist.artistId, 190026)
        self.assertTrue(artist.hasNextPage)
        self.assertTrue(len(artist.nextUrl) > 0)
        self.assertTrue(len(result) > 0)

        # post-201946 article
        self.assertEqual(result[0].imageId, 210980)
        self.assertTrue(len(result[0].imageTitle) > 0)
        self.assertIsNotNone(result[0].coverImageUrl)
        self.assertEqual(result[0].type, "article")
        self.assertEqual(len(result[0].images), 15)
        self.assertEqual(len(result[0].body_text), 3038)

        # result.posts[0].WriteInfo("./210980.txt")

    def testFanboxArtistVideo(self):
        reader = open('./test/creator_posts_with_video.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()

        artist = FanboxArtist(711048, "", "", None)
        result = artist.parsePosts(p)
        # result = FanboxArtist(711048, p)
        self.assertIsNotNone(result)

        self.assertEqual(artist.artistId, 711048)
        self.assertTrue(artist.hasNextPage)
        self.assertTrue(len(artist.nextUrl) > 0)
        self.assertTrue(len(result) > 0)

        # post-201946 article
        self.assertEqual(result[4].imageId, 330905)
        self.assertTrue(len(result[4].imageTitle) > 0)
        self.assertEqual(result[4].coverImageUrl, u'https://pixiv.pximg.net/fanbox/public/images/post/330905/cover/3A2zPUg4s6iz17MM0Z45eWBj.jpeg')
        self.assertEqual(result[4].type, "video")
        self.assertEqual(len(result[4].images), 0)
        self.assertEqual(len(result[4].body_text), 109)
        print(result[4].body_text)

        # result.posts[0].WriteInfo("./210980.txt")

    def testFanboxArtistArticleEmbedTwitter(self):
        reader = open('./test/creator_embedMap.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()

        artist = FanboxArtist(68813, "", "", None)
        result = artist.parsePosts(p)
        # result = FanboxArtist(68813, p)
        self.assertIsNotNone(result)

        self.assertEqual(artist.artistId, 68813)
        self.assertFalse(artist.hasNextPage)
        self.assertTrue(len(result) > 0)

        # post-201946 article
        self.assertEqual(result[0].imageId, 285502)
        self.assertTrue(len(result[0].imageTitle) > 0)
        self.assertEqual(result[0].coverImageUrl, u'https://pixiv.pximg.net/fanbox/public/images/post/285502/cover/orx9TCsiPFi5sgDdbvg4zwkX.jpeg')
        self.assertEqual(result[0].type, "article")
        self.assertEqual(len(result[0].images), 7)
        self.assertEqual(len(result[0].body_text), 3414)

        # result.posts[0].WriteInfo("./285502.txt")

    def testFanboxArtistPostsNextPage(self):
        # https://fanbox.pixiv.net/api/post.listCreator?userId=91029&maxPublishedDatetime=2019-07-25%2004%3A27%3A54&maxId=481268&limit=10
        reader = open('./test/Fanbox_artist_posts_nextpage.json', 'r', encoding="utf-8")
        p2 = reader.read()
        reader.close()

        artist = FanboxArtist(91029, "", "", None)
        result = artist.parsePosts(p2)
        # result = FanboxArtist(91029, p2)
        self.assertIsNotNone(result)

        self.assertEqual(artist.artistId, 91029)
        self.assertTrue(artist.hasNextPage)
        self.assertTrue(artist.nextUrl is not None)
        self.assertEqual(len(result), 10)

    def testFanboxArtistPostsRestricted(self):
        reader = open('./test/Fanbox_artist_posts_restricted.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()

        artist = FanboxArtist(15521131, "", "", None)
        result = artist.parsePosts(p)
        # result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)

        self.assertEqual(artist.artistId, 15521131)
        self.assertTrue(artist.hasNextPage)
        self.assertTrue(len(artist.nextUrl) > 0)
        self.assertEqual(len(result), 10)

        for post in result:
            self.assertTrue(post.is_restricted)

    def testFanboxArtistPostsRestrictedNextPage(self):
        reader = open('./test/Fanbox_artist_posts_next_page_restricted.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()
        artist = FanboxArtist(15521131, "", "", None)
        result = artist.parsePosts(p)
        # result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)

        self.assertEqual(artist.artistId, 15521131)
        self.assertFalse(artist.hasNextPage)
        self.assertTrue(artist.nextUrl is None)
        self.assertEqual(len(result), 6)

        self.assertTrue(result[0].is_restricted)
        self.assertFalse(result[1].is_restricted)

    def testFanboxOldApi(self):
        reader = open('./test/fanbox-posts-old-api.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()
        artist = FanboxArtist(104409, "", "", None)
        result = artist.parsePosts(p)
        # result = FanboxArtist(104409, p)
        self.assertIsNotNone(result)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].imageId, 916)
        self.assertEqual(len(result[0].images), 8)
        print(result[0].images)
        self.assertEqual(result[1].imageId, 915)
        self.assertEqual(len(result[1].images), 1)
        print(result[1].images)

    def testFanboxNewApi(self):
        reader = open('./test/fanbox-posts-new-api.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()
        artist = FanboxArtist(104409, "", "", None)
        result = artist.parsePosts(p)
        # result = FanboxArtist(104409, p)
        self.assertIsNotNone(result)

        self.assertEqual(len(result), 10)
        self.assertEqual(result[0].imageId, 577968)
        self.assertEqual(len(result[0].images), 2)
        self.assertEqual(result[1].imageId, 535518)
        self.assertEqual(len(result[1].images), 2)

    def testFanboxNewApi2_MultiImages(self):
        reader = open('./test/Fanbox_post_with_multi_images.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()
        js = json.loads(p)
        result = FanboxPost(855025, None, js["body"])
        self.assertIsNotNone(result)

        self.assertEqual(result.imageId, 855025)
        self.assertEqual(len(result.images), 2)
        self.assertEqual(len(result.embeddedFiles), 3)
        self.assertIsNotNone(result.coverImageUrl)
        self.assertFalse(result.coverImageUrl in result.images)

    def testFanboxNewApi2_Files(self):
        reader = open('./test/Fanbox_post_with_files.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()
        js = json.loads(p)
        result = FanboxPost(685832, None, js["body"])
        self.assertIsNotNone(result)

        self.assertEqual(result.imageId, 685832)
        self.assertEqual(len(result.images), 1)
        self.assertEqual(len(result.embeddedFiles), 2)
        self.assertIsNotNone(result.coverImageUrl)
        self.assertFalse(result.coverImageUrl in result.images)

    def testFanboxFilename(self):
        reader = open('./test/Fanbox_artist_posts.json', 'r', encoding="utf-8")
        p = reader.read()
        reader.close()
        artist = FanboxArtist(15521131, "", "", None)
        result = artist.parsePosts(p)
        # result = FanboxArtist(15521131, p)
        self.assertIsNotNone(result)
        root_dir = os.path.abspath(os.path.curdir)
        post = result[0]

        # # 'https://pixiv.pximg.net/fanbox/public/images/post/136761/cover/OqhhcslOfbzZpHyTfJNtnIWm.jpeg'
        # big_cover_url = post.images[0]
        # 'https://fanbox.pixiv.net/images/post/136761/hcXl48iORoJykmrR3zPZEoUu.jpeg'
        image_url = post.images[0]
        # current_page = 0
        # fake_image_url = image_url.replace("{0}/".format(post.imageId), "{0}_p{1}_".format(post.imageId, current_page))

        # # re_page = temp.findall(fake_image_url)
        # re_page = temp.findall(image_url)
        # self.assertIsNotNone(re_page)
        # self.assertEqual(re_page[0], u"0")
        # re_page = temp.findall(big_cover_url)
        # self.assertIsNotNone(re_page)
        # self.assertEqual(re_page[0], u"0")

        def simple_from_images():
            filename_format = '%title%_%urlFilename%'

            filename = PixivHelper.make_filename(filename_format,
                                                 post,
                                                 artistInfo=artist,
                                                 tagsSeparator=" ",
                                                 tagsLimit=0,
                                                 fileUrl=image_url,
                                                 bookmark=None,
                                                 searchTags='')
            filename = PixivHelper.sanitize_filename(filename, root_dir)

            self.assertEqual(filename, root_dir + os.sep + "アスナさん０２_hcXl48iORoJykmrR3zPZEoUu.jpeg")
        simple_from_images()

        def more_format():
            # from images
            filename_format = '%member_id%' + os.sep + '%image_id%_p%page_index%_%title%_%urlFilename%_%works_date%'

            filename = PixivHelper.make_filename(filename_format,
                                                 post,
                                                 artistInfo=artist,
                                                 tagsSeparator=" ",
                                                 tagsLimit=0,
                                                 fileUrl=image_url,
                                                 bookmark=None,
                                                 searchTags='')
            filename = PixivHelper.sanitize_filename(filename, root_dir)

            expected_name = root_dir + os.sep + u"15521131" + os.sep + u"136761_p_アスナさん０２_hcXl48iORoJykmrR3zPZEoUu_2018-08-26 20:28:16.jpeg"
            if platform.system() == 'Windows':
                expected_name = root_dir + os.sep + u"15521131" + os.sep + u"136761_p_アスナさん０２_hcXl48iORoJykmrR3zPZEoUu_2018-08-26 20_28_16.jpeg"

            self.assertEqual(filename, expected_name)
        more_format()

        def cover_more_format():
            # https://pixiv.pximg.net/c/1200x630_90_a2_g5/fanbox/public/images/post/96862/cover/6SRpcQwIUuJdeZbhn5q85l9x.jpeg
            fake_image_url = post.coverImageUrl.replace("{0}/cover/".format(post.imageId), "{0}_".format(post.imageId))
            print(fake_image_url)
            filename_format = '%member_id%' + os.sep + '%image_id%_%title%_%urlFilename%_%works_date%'

            filename = PixivHelper.make_filename(filename_format,
                                                 post,
                                                 artistInfo=artist,
                                                 tagsSeparator=" ",
                                                 tagsLimit=0,
                                                 fileUrl=fake_image_url,
                                                 bookmark=None,
                                                 searchTags='')
            filename = PixivHelper.sanitize_filename(filename, root_dir)

            expected_name = root_dir + os.sep + u"15521131" + os.sep + u"136761_アスナさん０２_136761_OqhhcslOfbzZpHyTfJNtnIWm_2018-08-26 20:28:16.jpeg"
            if platform.system() == 'Windows':
                expected_name = root_dir + os.sep + u"15521131" + os.sep + u"136761_アスナさん０２_136761_OqhhcslOfbzZpHyTfJNtnIWm_2018-08-26 20_28_16.jpeg"

            self.assertEqual(filename, expected_name)
        cover_more_format()

    def test_links_in_p_tags(self):
        with open('./test/test_for_links_in_p_tags.json', 'r', encoding="utf-8") as reader:
            p = reader.read()
        js = json.loads(p)
        result = FanboxPost(6544246, None, js["body"])
        self.assertIsNotNone(result)

        test_string1 = "<a href='https://www.pixiv.net/fanbox/creator/6544246/post/407551'>{0}</a>".format(
            u"Bleach: S\u014dsuke\u0027s Revenge Ch.2 "[0:29])
        self.assertTrue(test_string1 in result.body_text)

        temp_string = "H x H: The Plan to Wipe Out the Strongests "
        test_string2 = "{0}<a href='{1}'>{2}</a>{3}<a href='{4}'>{5}</a>{6}".format(
            temp_string[:5],
            "https://www.pixiv.net/fanbox/creator/6544246/post/407881",
            temp_string[5:15],
            temp_string[15:20],
            "#modified_for_test",
            temp_string[20:30],
            temp_string[30:])
        self.assertTrue(test_string2 in result.body_text)


if __name__ == '__main__':
    # unittest.main()
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPixivModel_Fanbox)
    unittest.TextTestRunner(verbosity=5).run(suite)
