from PixivException import PixivException
import PixivHelper
import demjson
import datetime_z
import os


class Fanbox:
    supportedArtist = None

    def __init__(self, page):
        js = demjson.decode(page)

        if js["error"]:
            raise PixivException("Error when requesting Fanbox", 9999, page)

        if js["body"] is not None:
            self.parseSupportedArtists(js["body"])

    def parseSupportedArtists(self, js_body):
        self.supportedArtist = list()
        for creator in js_body:
            self.supportedArtist.append(int(creator["user"]["userId"]))


class FanboxArtist:
    artistId = 0
    posts = None
    nextUrl = None
    hasNextPage = False

    # require additional API call
    artistName = ""
    artistToken = ""

    def __init__(self, artist_id, page):
        self.artistId = int(artist_id)
        js = demjson.decode(page)

        if js["error"]:
            raise PixivException("Error when requesting Fanbox artist: {0}".format(artistId), 9999, page)

        if js["body"] is not None:
            self.parsePosts(js["body"])

    def parsePosts(self, js_body):
        self.posts = list()
        if js_body.has_key("post"):
            post_root = js_body["post"]
        else:
            post_root = js_body

        for jsPost in post_root["items"]:
            post_id = int(jsPost["id"])
            post = FanboxPost(post_id, self, jsPost)
            self.posts.append(post)

        self.nextUrl = post_root["nextUrl"]
        if self.nextUrl is not None and len(self.nextUrl) > 0:
            self.hasNextPage = True


class FanboxPost:
    imageId = 0
    imageTitle = ""
    coverImageUrl = ""
    worksDate = ""
    worksDateDateTime = None
    updatedDatetime = ""
    # image|text|file
    type = ""
    body_text = ""
    images = None
    likeCount = 0
    parent = None
    is_restricted = False

    # not implemented
    worksResolution = ""
    worksTools = ""
    searchTags = ""
    imageMode = ""
    imageTags = list()
    bookmark_count = 0
    image_response_count = 0

    def __init__(self, post_id, parent, page):
        self.images = list()
        self.imageId = int(post_id)
        self.parent = parent
        self.parsePost(page)

        if not self.is_restricted:
            self.parseBody(page)
            if self.type == 'image':
                self.parseImages(page)

    def parsePost(self, jsPost):
        self.imageTitle = jsPost["title"]
        self.coverImageUrl = jsPost["coverImageUrl"]
        self.worksDate = jsPost["publishedDatetime"]
        self.worksDateDateTime = datetime_z.parse_datetime(self.worksDate)
        self.updatedDatetime = jsPost["updatedDatetime"]
        self.type = jsPost["type"]
        if self.type not in ["image", "text"]:
            raise PixivException("Unsupported post type = {0} for post = ".format(self.type, self.imageId), errorCode=9999, htmlPage=jsPost)

        self.likeCount = int(jsPost["likeCount"])
        if jsPost["body"] is None:
            self.is_restricted = True

    def parseBody(self, jsPost):
        self.body_text = jsPost["body"]["text"]

    def parseImages(self, jsPost):
        for image in jsPost["body"]["images"]:
            self.images.append(image["originalUrl"])
