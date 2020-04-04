# -*- coding: utf-8 -*-

PIXIVUTIL_VERSION = '202000404-beta2'
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

HTML_PATTERN = '<!DOCTYPE html> <html lang="ja"> <head> <title>%artistName% - %imageTitle%</title> <meta charset="utf-8"> <style type="text/css"> .container {margin:auto; display:inline-block; padding:10px;} body {text-align:center;} h1 {text-align:left;} h5 {text-align:left;} p {text-align:left;padding-left:5%;} img {max-width:100%;margin:auto} a {margin:auto;} </style> </head> <body> <div class="container"> <div class="cover"> <img src="%coverImageUrl%"/> </div> <div class="title"> <h1>%imageTitle%</h1> <h5>%worksDate%</h5> </div> <div class="caption"> %body_text% </div> </div> </body> </html>'

BUFFER_SIZE = 8192
