import PixivException
import demjson


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
    artist_id = 0
    posts = None
    nextUrl = None
    hasNextPage = False

    def __init__(self, artist_id, page):
        self.artist_id = int(artist_id)
        js = demjson.decode(page)

        if js["error"]:
            raise PixivException("Error when requesting Fanbox artist: {0}".format(artist_id), 9999, page)

        if js["body"] is not None:
            self.parsePosts(js["body"])

    def parsePosts(self, js_body):
        self.posts = list()
        for jsPost in js_body["post"]["items"]:
            post_id = int(jsPost["id"])
            post = FanboxPost(post_id, self, jsPost)
            self.posts.append(post)

        self.nextUrl = js_body["post"]["nextUrl"]
        if self.nextUrl is not None and len(self.nextUrl) > 0:
            self.hasNextPage = True


class FanboxPost:
    post_id = 0
    title = ""
    coverImageUrl = ""
    publishedDatetime = ""
    updatedDatetime = ""
    # image|text
    type = ""
    body_text = ""
    images = None
    likeCount = 0
    parent = None
    is_restricted = False

    def __init__(self, post_id, parent, page):
        self.images = list()
        self.post_id = int(post_id)
        self.parent = parent
        self.parsePost(page)
        if not self.is_restricted:
            self.parseBody(page)
            if self.type == 'image':
                self.parseImages(page)

    def parsePost(self, jsPost):
        self.title = jsPost["title"]
        self.coverImageUrl = jsPost["coverImageUrl"]
        self.publishedDatetime = jsPost["publishedDatetime"]
        self.updatedDatetime = jsPost["updatedDatetime"]
        self.type = jsPost["type"]
        self.likeCount = int(jsPost["likeCount"])
        if jsPost["body"] is None:
            self.is_restricted = True

    def parseBody(self, jsPost):
        self.body_text = jsPost["body"]["text"]

    def parseImages(self, jsPost):
        for image in jsPost["body"]["images"]:
            self.images.append(image["originalUrl"])


class FanboxHelper:
    def makeFilename(filename_format, url, artist, post, type, image_pos=0):
        fileUrl = os.path.basename(url)
        splittedUrl = fileUrl.split('.')
        imageExtension = splittedUrl[1]
        imageExtension = imageExtension.split('?')[0]

        # fake it for now
        if type != "cover":
            filename = "{0}/FANBOX {1} {4} {2}.{3}".format(artist.artist_id, post.post_id, splittedUrl[0], imageExtension, image_pos)
        else:
            filename = "{0}/FANBOX {1} cover {2}.{3}".format(artist.artist_id, post.post_id, splittedUrl[0], imageExtension)

        return filename
