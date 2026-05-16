/// PixivUtil2 constants.
library;

const String PIXIVUTIL_VERSION = '20251112';
const String PIXIVUTIL_LINK = 'https://github.com/Nandaka/PixivUtil2/releases';
const String PIXIVUTIL_DONATE = 'https://bit.ly/PixivUtilDonation';

/// Log Settings
const String PIXIVUTIL_LOG_FILE = 'pixivutil.log';
const int PIXIVUTIL_LOG_SIZE = 10485760;
const int PIXIVUTIL_LOG_COUNT = 10;
const String PIXIVUTIL_LOG_FORMAT =
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s';

/// Download Results
const int PIXIVUTIL_NOT_OK = -1;
const int PIXIVUTIL_OK = 0;
const int PIXIVUTIL_SKIP_OLDER = 1;
const int PIXIVUTIL_SKIP_BLACKLIST = 2;
const int PIXIVUTIL_KEYBOARD_INTERRUPT = 3;
const int PIXIVUTIL_SKIP_DUPLICATE = 4;
const int PIXIVUTIL_SKIP_LOCAL_LARGER = 5;
const int PIXIVUTIL_CHECK_DOWNLOAD = 6;
const int PIXIVUTIL_SIZE_LIMIT_LARGER = 7;
const int PIXIVUTIL_SIZE_LIMIT_SMALLER = 8;
const int PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT = 9;
const int PIXIVUTIL_ABORTED = 9999;

const String HTML_TEMPLATE =
    '<!DOCTYPE html> <html lang="ja"> <head> <title>%artistName% - %imageTitle%</title> <meta charset="utf-8"> <style type="text/css"> *{margin:0px; padding:0px; max-width:100%; overflow:auto;} body{text-align:center; background-color:#f3f5f8;} h1, h2, h5, p{text-align:left;} h1, h2, h5, p{padding-left:4%; padding-right:4%;} p{word-break:break-word; padding-top:0.5em; padding-bottom:0.5em;} span{padding:0px;} .title{margin-top:2rem; margin-bottom:2rem;} a{margin:auto;} .root{max-width:1280px; margin:auto; background-color:#ffffff;} .caption{display:grid;} .non-article.main, .non-article.images{position:fixed; overflow-y:scroll; background-color:#ffffff;} .non-article.main{top:0px; left:0px; height:100%; width:360px;} .non-article.images{top:0px; left:360px; height:100%;} @media screen and (max-aspect-ratio:4/5){.non-article.main{height:25%; width:100%;} .non-article.images{top:25%; left:0px; height:75%; width:100%;}} </style> </head> <body> <div class="root"> <div class="main"> %coverImage% <div class="title"> <h1>%imageTitle%</h1> <h5>%worksDate%</h5> </div> %body_text(article)% %text(non-article)% </div> %images(non-article)% </div> </body> </html>';

const String DOWNLOAD_PIXIV = 'Pixiv';
const String DOWNLOAD_FANBOX = 'Fanbox';
const String DOWNLOAD_SKETCH = 'Sketch';
