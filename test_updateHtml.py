# -*- coding: UTF-8 -*-


import PixivUtil2
import PixivBrowserFactory
import PixivConfig
import getpass
import mechanize

__config__ = PixivConfig.PixivConfig()
PixivUtil2.__config__ = __config__
__config__.loadConfig()
__br__ = PixivUtil2.__br__ = PixivBrowserFactory.getBrowser(config=__config__)


def prepare():
    # Log in
    username = __config__.username
    if username == '':
        username = input('Username ? ')
    password = __config__.password
    if password == '':
        password = getpass.getpass('Password ? ')

    result = False
    if len(__config__.cookie) > 0:
        result = __br__.loginUsingCookie(__config__.cookie)

    if not result:
        result = __br__.login(username, password)

    return result


def downloadPage(url, filename):
    print("Dumping " + url + " to " + filename)
    try:
        html = __br__.open(url).read()
    except mechanize.HTTPError as e:
        if e.code in [400, 403, 404]:
            html = e.read()
        else:
            raise
    try:
        dump = file(filename, 'wb')
        dump.write(html)
        dump.close()
    except BaseException:
        pass


def main():
    downloadPage('https://www.pixiv.net/member_illust.php?id=143229', './test/test-member-nologin.htm')
    downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=67089412', './test/test-image-nologin.htm')

    result = prepare()
    if result:
        # ./test/test-image-manga.htm
        # https://www.pixiv.net/member_illust.php?mode=medium&illust_id=28820443
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=28820443', './test/test-image-manga.htm')

        # ./test/test-image-unicode.htm
        # https://www.pixiv.net/member_illust.php?mode=medium&illust_id=2493913
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=2493913', './test/test-image-unicode.htm')

        # ./test/test-helper-avatar-name.htm
        # https://www.pixiv.net/member_illust.php?id=1107124
        # downloadPage('https://www.pixiv.net/member_illust.php?id=1107124', './test/test-helper-avatar-name.htm')

        downloadPage('https://www.pixiv.net/member_illust.php?id=1', './test/test-nouser.htm')
        # downloadPage('https://www.pixiv.net/member_illust.php?id=26357', './test/test-member-noavatar.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?id=1233', './test/test-noimage.htm')
        # downloadPage('https://www.pixiv.net/bookmark.php?id=490219', './test/test-member-bookmark.htm')
        downloadPage('https://www.pixiv.net/manage/illusts/', './test/test-member-self.htm')

        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=32039274', './test/test-image-info.html')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=67729319', './test/test-image-info2.html')
        downloadPage('https://www.pixiv.net/bookmark_new_illust.php', './test/test-bookmarks_new_ilust.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=12467674', './test/test-image-my_pick.html')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=20496355', './test/test-image-noavatar.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=11164869', './test/test-image-parse-tags.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=9175987', './test/test-image-no_tags.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=28865189', './test/test-image-rate_count.htm')
        ## downloadPage('https://www.pixiv.net/member_illust.php?mode=big&illust_id=20644633', './test/test-image-parsebig.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=manga&illust_id=46279245', './test/test-image-parsemanga.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=46281014', './test/test-image-ugoira.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=manga&illust_id=46322053', './test/test-image-manga-2page.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=28688383', './test/test-image-deleted.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=62670665', './test/test-image-big-manga.html')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=67487303', './test/test-image-big-manga-mixed.html')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=65079382', './test/test-image-selfimage.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=12467674', './test/test-image-my_pick.html')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=37882549x', './test/test-image-generic-error.html')
        downloadPage('https://www.pixiv.net/member_illust.php?mode=medium&illust_id=123', './test/test-image-deleted.htm')

        downloadPage('https://www.pixiv.net/bookmark.php', './test/test-image-bookmark.htm')
        downloadPage('https://www.pixiv.net/bookmark.php?id=283027', './test/test-image-bookmark-member.htm')

        downloadPage('https://www.pixiv.net/member_illust.php?id=313631&p=7', './test/test-tags-member-search-last.htm')
        downloadPage('https://www.pixiv.net/search.php?s_mode=s_tag_full&word=%E5%88%9D%E6%98%A5%E9%A3%BE%E5%88%A9', './test/test-tags-search-exact.htm')
        downloadPage('https://www.pixiv.net/search.php?word=%E5%88%9D%E6%98%A5%E9%A3%BE%E5%88%A9&s_mode=s_tag_full&order=date_d&p=70', './test/test-tags-search-exact-last.htm')
        downloadPage('https://www.pixiv.net/search.php?word=%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B!&s_mode=s_tag_full&order=date_d&p=12', './test/test-tags-search-partial.htm')
        downloadPage('https://www.pixiv.net/search.php?s_mode=s_tag_full&word=XXXXXX', './test/test-tags-search-exact-parse_details.htm')
        downloadPage('https://www.pixiv.net/search.php?s_mode=s_tag&word=%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B!', './test/test-tags-search-partial.htm')
        downloadPage('https://www.pixiv.net/search.php?word=%E3%81%93%E3%81%AE%E4%B8%AD%E3%81%AB1%E4%BA%BA%E3%80%81%E5%A6%B9%E3%81%8C%E3%81%84%E3%82%8B!&order=date_d&p=6', './test/test-tags-search-partial-last.htm')

        downloadPage('https://www.pixiv.net/search.php?s_mode=s_tag&word=R-18%20K-On!', './test/test-tags-search-skip-showcase.htm')

        downloadPage('https://www.pixiv.net/search.php?word=%E3%82%AF%E3%83%89%E3%83%AA%E3%83%A3%E3%83%95%E3%82%AB&s_mode=s_tag_full', './test/test-tags-search-exact2.htm')

        downloadPage('https://www.pixiv.net/member_illust.php?id=313631&tag=R-18', './test/test-tags-member-search.htm')
        downloadPage('https://www.pixiv.net/member_illust.php?id=313631&tag=R-18', './test/test-tags-member-search.htm')

        downloadPage('https://www.pixiv.net/group/images.php?format=json&max_id=946801&id=881', './test/group.json')
        downloadPage('https://app-api.pixiv.net/v1/user/detail?user_id=554800', './test/detail-554800.json')
        downloadPage('https://app-api.pixiv.net/v1/user/detail?user_id=267014', './test/detail-267014.json')

        # AJAX calls
        downloadPage('https://www.pixiv.net/ajax/user/14095911/profile/all', './test/all-14095911.json')
        downloadPage('https://app-api.pixiv.net/v1/user/detail?user_id=14095911', './test/userdetail-14095911.json')
        downloadPage('https://www.pixiv.net/ajax/user/26357/profile/all', './test/all-26357.json')
        downloadPage('https://app-api.pixiv.net/v1/user/detail?user_id=26357', './test/userdetail-26357.json')
        downloadPage('https://www.pixiv.net/ajax/user/14095911/illustmanga/tag?tag=R-18&offset=0&limit=48', './test/tag-R-18-14095911.json')
        downloadPage('https://www.pixiv.net/ajax/user/14095911/illustmanga/tag?tag=R-18&offset=48&limit=48', './test/tag-R-18-14095911-lastpage.json')
        downloadPage('https://www.pixiv.net/ajax/user/1039353/illusts/bookmarks?tag=&offset=0&limit=24&rest=show', './test/bookmarks-1039353.json')
        downloadPage('https://app-api.pixiv.net/v1/user/detail?user_id=1039353', './test/userdetail-1039353.json')

        # Not updated:
        # ./test/test-login-error.htm
        # ./test/test-member-suspended.htm
        # ./test/test-member-nologin.htm

        print("Completed")


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        print(ex)
    input("anykey")
