# -*- coding: utf-8 -*-

PIXIVUTIL_VERSION = '20210108-beta4'
PIXIVUTIL_LINK = 'https://github.com/Nandaka/PixivUtil2/releases'
PIXIVUTIL_DONATE = 'https://bit.ly/PixivUtilDonation'

# Log Settings
PIXIVUTIL_LOG_FILE = 'pixivutil.log'
PIXIVUTIL_LOG_SIZE = 10485760
PIXIVUTIL_LOG_COUNT = 10
PIXIVUTIL_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Download Results
PIXIVUTIL_NOT_OK = -1
PIXIVUTIL_OK = 0
PIXIVUTIL_SKIP_OLDER = 1
PIXIVUTIL_SKIP_BLACKLIST = 2
PIXIVUTIL_KEYBOARD_INTERRUPT = 3
PIXIVUTIL_SKIP_DUPLICATE = 4
PIXIVUTIL_SKIP_LOCAL_LARGER = 5
PIXIVUTIL_CHECK_DOWNLOAD = 6
PIXIVUTIL_SIZE_LIMIT_LARGER = 7
PIXIVUTIL_SIZE_LIMIT_SMALLER = 8
PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT = 9
PIXIVUTIL_ABORTED = 9999

HTML_TEMPLATE = '<!DOCTYPE html> <html lang="ja"> <head> <title>%artistName% - %imageTitle%</title> <meta charset="utf-8"> <style type="text/css"> *{margin:0px; padding:0px; max-width:100%;} body{text-align:center;} div{overflow:auto;} h1, h2, h5, p, span{padding-top:0.5em; padding-bottom:0.5em; text-align:left;} p{word-break:break-word;} div, h1, h2, h5, p{padding-left:2%; padding-right:2%;} .non-article.main, .non-article.images{position:fixed; max-height:100%; max-width:100%; padding:0px;} .non-article.main{top:0px; left:0px; height:100%; width:20%; right:80%;} .non-article.images{top:0px; left:20%; height:100%; width:80%; right:0px;} @media only screen and (max-aspect-ratio:0.8){.non-article.main{height:25%; width:100%; right:0px;} .non-article.images{top:25%; left:0px; height:75%; width:100%;}} </style> </head> <body> <div class="root"> <div class="main"> %coverImage% <div class="title"> <h1>%imageTitle%</h1> <h5>%worksDate%</h5> </div> %body_text(article)% %text(non-article)% </div> %images(non-article)% </div> </body> </html>'

BUFFER_SIZE = 8192
