# Requirements:
- Running from Windows binary:
  - minimum Windows 7 SP1 with latest updates installed.

- Running from source code:
  - Python 3.9.0+ (https://www.python.org/)
  - Additional library listed in requirements.txt
  - IDE Environment: see https://github.com/Nandaka/PixivUtil2/wiki/IDE-Enviroment-(Windows)

- Dependent software
  - FFmpeg (https://www.ffmpeg.org/) - used for converting ugoira to video.

# Capabilities:
- Download by member_id
- Download by image_id
- Download by tags
- Download from list (list.txt)
- Download from bookmarked artists (/bookmark.php?type=user)
  including private/hidden bookmarks.
- Download from bookmarked images (/bookmark.php)
  including private/hidden bookmarks.
- Download from tags list (tags.txt)
- Download new illustrations from bookmarked artist (/bookmark_new_illust.php)
- Download by Title/Caption
- Download by Tag and Member Id
- Download Member Bookmark (/bookmark.php?id=)
- Download by Group Id
- Download from supported artists (FANBOX)
- Download by artist/creator id (FANBOX)
- Download by post id (FANBOX)
- Download from followed artists (FANBOX)
- Batch Download from batch_job.json (experimental)
  See https://github.com/Nandaka/PixivUtil2/wiki/Using-Batch-Job-(Experimental)
- Manage database:
  - Show all member
  - Show all downloaded images
  - Export list (member_id only)
  - Export list (detailed)
  - Show member by last downloaded date
  - Show image by image_id
  - Show member by member_id
  - Show image by member_id
  - Delete member by member_id
  - Delete image by image_id
  - Delete member and image (cascade deletion)
  - Blacklist image by image_id
  - Show all deleted member
  - Export FANBOX post list
  - Delete FANBOX download history by member_id
  - Delete FANBOX download history by post_id
  - Clean Up Database (remove db entry if downloaded file is missing)
- Export user bookmark (member_id) to a text files.

# Docker

```sh
$ docker build -t pixivutil2 .
$ docker run -it --rm \
  -v $(pwd):/workdir \
  -w /workdir \
  pixivutil2 \
  /bin/bash -c "python PixivUtil2.py"
```

# WARNING
Overusage can lead to Pixiv blocking your IP for a few hours.

# FAQs

## A. Usage
```
Q1. How to paste Japanese tags to the console window?
    - Click the top-left icon -> select Edit -> Paste (Cannot use Ctrl-V), if
      it show up as question mark -> Change the Language for non-Unicode
      program to Japanese (google it).
    - or use online url encoder (http://meyerweb.com/eric/tools/dencoder/)
      and paste the encoded tag back to the console.
    - or paste it to tags.txt and select download by tags list. Separate each
      tags with space, and separate with new line for new query.

Q2. My password doesn't show up in the console!
    - This is normal. The program still reads it.
    - or you can put in the config.ini if not sure.

Q3. I cannot login to Pixiv!
    - Check your password.
    - Try to login to the Pixiv Website.
    - Try to use the config.ini on the [Authentication] section.
    - Check your date and time setting (e.g.: https://www.timeanddate.com/)
    - Disable Daylight Saving Time and try again.
    - Copy your session values from browser:
      1. Open Firefox.
      2. Go to Pixiv website and login, remember to enable [Remember Me]
          check box.
      3. Right click the page and select View Page Info.
      4. Click the Security tab.
      5. Click the View Cookies button.
      6. Look for Cookie named = PHPSESSID.
      7. Copy the content value.
      8. Open config.ini, go to [Authentication] section, paste the value
          to cookie, set keepsignedin = 1.

Q4. PixivUtil working from local terminal on Linux box but not working when I
    used SSH with PuTTY!
    - export LANG=en_US.UTF-8. PuTTY does not set locales right, when they are
      not set, python does not know what to write (Thanks to nho!)
    - ... and export PYTHONIOENCODING=utf-8, so it can create DB and populate
      it properly (Thanks to Mailia!)

Q5. How to delete member id from Database?
    - Open the application and choose Manage Database (d) then select delete
      Member by Member Id.
    - Open the database (db.sqlite) directly using sqlite browser and use sql
      command to delete it.
    - If you are downloading using Download from List.txt (3), you can create
      ignore_list.txt to skip the member id.

Q6. The app doesn't download all the images! (I want to download SFW images too).
    - Pixiv only allow to search up to 1000 pages if you don't have Pixiv
      Premium.
    - Check your pixiv website settings (refer to https://goo.gl/gQi09v),
      then delete the cookie value in config.ini and retry.
    - Check the value of r18mode in config.ini. Setting it to True will only
      download R-18 images.

Q7. The apps show square/question mark texts in the console output!
    - This is because your Windows is not set to Japanese for the Regional Settings
      in control panel.
    - Since 20161114+ version, you need to set the console font properties to
      use font with unicode support (e.g. Arial Unicode, MS Gothic).

Q8. Where to get FFmpeg software? How to enable `createwebm`?
    - Download the stable version of FFmpeg from https://www.ffmpeg.org/download.html.
    - For Windows:
      - Extract the archive to a folder.
      - Open the extracted folder and open to the `/bin` folder.
      - Copy the application `ffmpeg.exe` to your PixivUtil2 folder.
    - For Linux:
      - Install the package using your favorite package manager.

Q9. The downloaded images are corrupted, how to redownload it again?
    - You can delete the download history in databases by manually delete the image id
      from databases (enter d, followed by 10).
    - Or, you can set alwaysCheckFileSize = True and verifyimage = True in config.ini
      and retry the download.
      
Q10. I got this error またはメールアドレス、パスワードが正しいかチェックしてください。
    - Use your email address for the username, or check your password in config.ini

```
## B.Bugs/Source Code/Supports
```
Q1. Where I can report bugs?
    - Please report any bug to https://github.com/Nandaka/PixivUtil2/issues.

Q2. Where I can support/donate to you?
    - You can send it to my PayPal account (nchek2000[at]gmail[dot]com).
    - or visit https://bit.ly/PixivUtilDonation.

Q3. I want to use/modify the source code!
    - Feel free to use/modify the source code as long you give credit to me
      and make the modificated source code open.
    - if you want to add feature/bug fix, you can do fork the repository in
      https://github.com/Nandaka/PixivUtil2 and issue Pull Requests.

Q4. I got ValueError: invalid literal for int() with base 10: '<something>'
    - Please modify _html.py from mechanize library, search for
      'def unescape_charref(data, encoding):' and replace with patch in
      https://pastebin.com/5bT5HFkb.

Q5. I got '<library_name> module no found error'
    - Download the library from the source (see links from the Requirements
      section) and copy the file into your Lib\site-packages directory.
    - Or use pip install (google on how to use).
```
## C.Log Messages
```
Q1: HTTPError: HTTP Error 404: Not Found
    - This is because the file doesn't exist in the pixiv server, usually
       because there is no big images version for the manga mode (currently the
       apps will try to download the big version first then try the normal size
       if failed, this is only for the manga mode and it is normal).

Q2: Error at process_image(): (<type 'exceptions.WindowsError'>, WindowsError
    (32, 'Prosessi ei voi kayttaa tiedostoa, koska se on toisen prosessin
    kaytossa')
    - The file is being used by another process (google translate). Either you
      ran multiple instace of Pixiv downloader from the same folder, or there
      are other processes locking the file/db.sqllite (usually from antivirus
      or some sync/backup application).

Q3: Error at process_image(): (<type 'exceptions.AttributeError'>,
    AttributeError ("'NoneType' object has no attribute 'find'",)
    - Usually this is because of failed login (cookie not valid). Try to change
      your password to simple one for testing, or copy the cookie from browser:
      1. Open Firefox/Chrome.
      2. Login to your Pixiv.
      3. On Pixiv page, press F12 and choose the Storage tab (Firefox), or
         Right click on the leftmost address bar/the (i) icon (Chrome)
      5. Click the View Cookies button.
      6. Look for Cookie named = PHPSESSID.
      7. Copy the content value.
      8. Open config.ini, go to [Authentication] section, paste the value to
         cookie.
    - Or because Pixiv has changed the layout code, so the Pixiv
      downloader cannot parse the page correctly. Please tell me by posting a
      comment if this happens and include the details, such as the member/image
      id, dump html, and log file (check on the application folder).

Q4: URLError: <urlopen error [Errno 11004] getaddrinfo failed>
    - This is because the Pixiv downloader cannot resolve the address to
      download the images, please try to restart the network connection or do
      ipconfig /flushdns to refresh the dns cache (windows).

Q5: Error at download_image(): (<class 'socket.timeout'>, timeout('timed out',)
    - This is because the Pixiv downloader didn't receive any reply for
      specified time in config.ini from Pixiv. Please retry the download again
      later.

Q6: httperror_seek_wrapper: HTTP Error 403: request disallowed by robots.txt
    - Set userobots = False in config.ini
```

# Command Line Option
Please refer run with `--help` for latest information.
```
  -h, --help            show this help message and exit
  -s STARTACTION, --startaction=STARTACTION
                        Action you want to load your program with:
                        1 - Download by member_id
                            (required: list of member_ids separated by space
                             optional: --include_sketch to also download Pixiv Sketch)
                        2 - Download by image_id
                            (required: followed by image_ids separated by space)
                        3 - Download by tags
                            (required: tags
                             optional: --use_wildcard_tag, --sp=START_PAGE, and --ep=END_PAGE, --start_date, --end_date)
                        4 - Download from list
                            (required: -f LIST_FILE and followed with optional tag)
                        5 - Download from user bookmark
                            (optional: -p BOOKMARK_FLAG [y/n/o] for private bookmark, --sp=START_PAGE, and --ep=END_PAGE)
                        6 - Download from image bookmark
                            (required: -p BOOKMARK_FLAG [y/n/o] for private bookmark
                             optional: --sp=START_PAGE, and --ep=END_PAGE, and followed with tag)
                        7 - Download from tags list
                            (required: -f LIST_FILE,
                             optional: --sp=START_PAGE, and --ep=END_PAGE, --start_date, --end_date)
                        8 - Download new illust from bookmark
                            (optional: --sp=START_PAGE, and --ep=END_PAGE)
                        9 - Download by Title/Caption
                            (required: title/caption
                             optional: --sp=START_PAGE, and --ep=END_PAGE, --start_date, --end_date)
                        10 - Download by Tag and Member Id
                            (required: member_id, followed by tags
                             optional: --sp=START_PAGE, and --ep=END_PAGE)
                        11 - Download Member's Bookmarked Images
                            (required: followed by member_ids separated by space)
                        12 - Download by Group ID
                            (required: Group ID, limit, and process external[y/n])
                        13 - Download by Manga Series ID
                            (required: Manga Series ID separated by space
                             optional: --sp=START_PAGE, and --ep=END_PAGE))
                        f1 - Download from supported artists (FANBOX)
                            (optional: End Page)
                        f2 - Download by artist/creator id (FANBOX)
                            (required: artist(digits only)/creator ids separated by space,
                             optional: end page)
                        f3 - Download by post id (FANBOX)
                            (required: post ids, separated with space)
                        f4 - Download from followed artists (FANBOX)
                            (optional: End Page)
                        f5 - Download from custom artist list (FANBOX)
                            (optional: End page, path to list)
                        b - Batch Download from batch_job.json (experimental)
                            (optional: --bf=BATCH_FILE)
                        e - Export online bookmark
                            (required: -p BOOKMARK_FLAG [y/n/o] for private bookmark
                             optional: filename)
                        m - Export online user bookmark
                            (required: member_id, optional: followed by filename)
                        d - Manage database
  -x, --exitwhendone    Exit programm when done.
                        (only useful when DB-Manager)
  -i, --irfanview       start IrfanView after downloading images using
                        downloaded_on_%date%.txt
  -n NUMBEROFPAGES, --numberofpages=NUMBEROFPAGES
                        temporarily overwrites numberOfPage set in config.ini
  -c [PATH], --config [PATH] provide different config.ini
```

# Error Codes
- 100  = Not Logged in.
- 1001 = User ID not exist/deleted.
- 1002 = User Account is Suspended.
- 1003 = Unknown Member Error.
- 1004 = No image found.
- 1005 = Cannot login.
- 2001 = Unknown Error in Image Page.
- 2002 = Not in MyPick List, Need Permission.
- 2003 = Public works can not be viewed by the appropriate level.
- 2004 = Image not found/already deleted.
- 2005 = Image is disabled for under 18, check your setting page (R-18/R-18G).
- 2006 = Unknown Image Error.
- 9000 = Download Failed.
- 9001 = Download Failed: Harddisk related.
- 9002 = Download Failed: Network related.
- 9005 = Server Error.

# config.ini
## [Authentication]
- username

  Your pixiv username. Needed for OAuth. Please make sure the combination of username and password is valid in case of OAuth error. If you get error 103, please try changing username from pixiv ID to email address or the other way around.
- password

  Your pixiv password, in clear text! Needed for OAuth. Please make sure the combination of username and password is valid in case of OAuth error.
- cookie

  Your cookies for pixiv login, will be automatically updated in the login. See https://github.com/Nandaka/PixivUtil2/issues/814#issuecomment-711182644 for details.
- cookieFanbox

  Cookie for fanbox.cc, normally no need to fill in.
- refresh_token

  Used for OAuth refresh token to avoid relogin too many time. Automatically generated upon succesful OAuth login.

## [Pixiv]
- numberofpage

  Number of page to be processed, put `0` to process all pages.
- r18mode

  Only list images tagged R18, for member, member's bookmark, and search by tag. Set to `True` to enable.
- dateformat

  Pixiv DateTime format, leave blank to use default format (YYYY-MM-DD).
  Refer to http://strftime.org/ for syntax. Quick Reference:
  - %d = Day, %m = Month, %Y = Year (4 digit)
  - %H = Hour (24h), %M = Minute, %S = Seconds
- autoAddMember

  Automatically save member id to db for all download.

## [FANBOX]
- filenameFormatFanboxContent

  Similar to filename format, but for files inside FANBOX posts.
- filenameFormatFanboxCover

  Similar to filename format, but for FANBOX post cover images
- filenameFormatFanboxInfo

  Similar to filename format, but for info dumps.
- writeHtml

  A switch to decide whether to write FANBOX posts into HTMLs or not.
  - If set to `True`, article type posts will for sure be written into HTMLs, while non-article type posts are controlled with `minTextLengthForNonArticle` and `minImageCountForNonArticle`.
  - If set to `False`, no post will be written into HTMLs.
  - `filenameFormatFanboxInfo` will be used for filename.
  - For HTML format, please refer to 'HTML Format' section
- minTextLengthForNonArticle

  Works with `minImageCountForNonArticle`.
  When 'writeHtml' is True, a non-article post should contain text longer than this value to be written into HTML.
- minImageCountForNonArticle

  Works with `minTextLengthForNonArticle`.
  When `writeHtml` is True, a non-article post should contain at least this many files/images to be written into HTML.
- useAbsolutePathsInHtml

  Set to `True` to use absolute paths in HTMLs.
  Set to `False` to use relative paths.
- downloadCoverWhenRestricted

  Set to `True` to download FANBOX post cover images even if they are restricted.
- checkDBProcessHistory
  Each FANBOX post has a updated_date value, which will be recorded/updated in database after it is processed.
  - When this is `True`, the values in database would be checked when processing each post. If record is no earlier than the newly retrieved date, which means that the post has not been processed at all or changed since last time, the post would be skipped.
  - When this is `False`, posts will be processed anyways.
- listPathFanbox

  The list file for fanbox creators. One creator per line.
  Doesn't support custom path.

## [Network]
- useproxy

  Set `True` to use proxy server, or `False` to disable it.
- proxyaddress

  Proxy server address, use this format:
  - http://<username>:<password>@<proxy_server>:<port> or
  - socks5://<username>:<password>@<proxy_server>:<port> or
  - socks4://<username>:<password>@<proxy_server>:<port>
- useragent
  
  Browser user agent to spoof. You can check it from https://www.whatismybrowser.com/detect/what-is-my-user-agent
- userobots

  Download robots.txt for mechanize.
- timeout

  Time to wait before giving up the connection, in seconds.
- retry

  Number of retries.
- retrywait

  Waiting time for each retry, in seconds.
- downloadDelay

  Set random delay up to n seconds for each image post.
  Set to 0 to disable.
- checkNewVersion

  Set to `True` to check new releases in github.
- notifyBetaVersion

  Set to `False` to ignore beta releases.
- openNewVersion

  Set to `False` to disable opening new releases in browser.
- enableSSLVerification

  Enable SSL verication, only set to `False` if you always encounter SSL Error (this disable the security)

## [Debug]
- logLevel

  Set log level, valid values are CRITICAL, ERROR, WARNING, INFO, DEBUG, and NOTSET
- enableDump

  Enable HTML Dump. Set to False to disable.
- skipDumpFilter

  Skip HTML Dump based on error code (using regex format).
  E.g.: 1.*|2.* => skip all HTML dump for error code 1xxx/2xxx.
- dumpMediumPage

  Dump all medium page for debugging. Set to True to enable.
- dumpTagSearchPage

  Dump tags search page for debugging.
- debughttp

  Print http header, useful for debuggin. Set 'False' to disable.

## [IrfanView]
- IrfanViewPath

  Set directory where IrfanView is installed (needed to start IrfanView)
- startIrfanView

  Set to `True` to start IrfanView with downloaded images when exiting pixivUtil
  - This will create download-lists
  - Be sure to set IrfanView to load Unicode-Plugin on startup when there are unicode-named files!
- startIrfanSlide

  Set to `True` to start IrfanView-Slideshow with downloaded images when exiting pixivUtil.
  - This will create download-lists
  - Be sure to set IrfanView to load Unicode-Plugin on startup when there are unicode-named files!
  - Slideshow-options will be same as you have set in IrfanView before!
- createDownloadLists

  Set to `True` to automatically create download-lists.

## [Settings]
- downloadlistdirectory

  list.txt path, also used for download-lists needed for `createDownloadLists` and IrfanView-Handling
  If leaved blank it will create download-lists in pixivUtil-directory.
- uselist

  Set to `True` to parse list.txt.
  This will update the DB content from the list.txt (member_id and custom folder).
- processfromdb

  Set `True` to use the member_id from the DB.
- rootdirectory

  Your root directory for saving the images.
- downloadavatar

  Set to `True` to download the member avatar as 'folder.jpg'
- usesuppresstags

  Remove the suppressed tags from %tags% meta for filename.
  The list is taken from suppress_tags.txt, each tags is separated by new line.
- tagsLimit

  Number of tags to be used for %tags% meta in filename.
  Use -1 to use all tags.
- writeimageinfo

  Set to `True` to export the image information to text file.
  The filename is following `filename(Manga)Infoformat` + .txt.
- writeImageJSON

  Set to `True` to export the image information to JSON.
  The filename is following `filename(Manga)Infoformat` + .json.
- writeRawJSON

  Set to `True` to export the image JSON untouched.
  The filename is following `filename(Manga)Infoformat` + .json.
- RawJSONFilter

  Enter the JSON keys which you want to filter out. Keys are seperated by a comma.
- writeSeriesJSON

  Set to `True` to export the series information to JSON.
  The filename is following `filenameSeriesJSON` + .json.
- verifyimage

  Do image and zip checking after download. Set the value to `True` to enable.
- writeUrlInDescription

  Write all url found in the image description to a text file. Set to `True` to enable. The list will be saved to to the application folder as url_list_<timestamp>.txt
- urlBlacklistRegex
  
  Used to filter out the url in the description using regular expression.
- dbPath

  Use different database.
- setLastModified

  Set last modified timestamp based on pixiv upload timestamp.
- useLocalTimezone

  Use local timezone when setting last modified timestamp/works date.

## [DownloadControl]
- minFileSize

  Skip if file size is less than minFileSize, set `0` to disable.
- maxFileSize

  Skip if file size is more than minFileSize, set `0` to disable.
- overwrite

  Overwrite old files, set `False` to disable.
- backupOldFile

  Set to True to backup old file if the file size is different.
  Old filename will be renamed to filename.unix-time.extension.
- daylastupdated

  Only process member_id which were processed at least x days since the last check.
- alwaysCheckFileSize

  Check the file size, if different then it will be downloaded again, set `False` to disable.
  This will override the image_id checking from db (always fetch the image page to check the remote size).
- checkUpdatedLimit

  Jump to the next member id if already see n-number of previously downloaded images.
  `alwaysCheckFileSize` must be set to False.
- useblacklisttags

  Skip image if containing blacklisted tags.
  The list is taken from `blacklist_tags.txt`, each tags is separated by new line.
- useblacklisttitles

  Skip image if the title contains a blacklisted character sequence.
  The list is taken from `blacklist_titles.txt`, each sequence is separated by new line.
- useblacklisttitlesregex

  Make the title blacklist check interpret each sequence as a regular expression.
- dateDiff

  Process only new images within the given date difference.
  Set `0` to disable. Skip to next member id if in 'Download by Member', stop processing if in 'Download New Illust' mode.
- enableInfiniteLoop

  Enable infinite loop for download by tags.
  Only applicable for download in descending order (newest first).
- useBlacklistMembers

  Skip image by member id based on `blacklist_members.txt` in the same folder of the application.
- downloadResized

  Download the medium size, rather than the original size.
- checkLastModified

  Compare local file's last-modified timestamp with works date.
  Require `setlastmodified = True` in config.ini to work properly
- skipUnknownSize

  Skip downloading if the remote size is not known when `alwaysCheckFileSize` is set to True.

## [FFmpeg]
- ffmpeg

  Path to ffmpeg executable.
- ffmpegcodec

  Codec to be used for encoding webm, default is using `libvpx-vp9`.
- ffmpegparam

  Parameter to be used to encode webm. default is `-lossless 1 -vsync 2 -r 999 -pix_fmt yuv420p`
- webpcodec

  Codec to be used for encoding webm, default is using `libwebp`.
- webpparam

  Parameter to be used to encode webm.
  default is `lossless 0 -q:v 90 -loop 0 -vsync 2 -r 999`

## [Ugoira]
- writeugoirainfo

  If set to `True`, it will dump the .js to external file.
- createugoira

  If set to `True`, it will create .ugoira file.
  This is Pixiv own format for animated images. You can use Honeyview to see the animation.
- deleteZipFile

  If set to `True`, it will delete the zip files from ugoira.
  Only active if `createUgoira = True`.
- creategif

  Set to True to convert ugoira file to gif.
  Required `createUgoira = True` and ffmpeg executeable.
- createapng

  Set to True to convert ugoira file to animated png.
  Required `createUgoira = True` and ffmpeg executeable.
- deleteugoira

  Set to True to delete original ugoira after conversion.
- createwebm

  Set to True to create webm file (video format).
  Required `createUgoira = True` and ffmpeg executeable.
- createwebp

  Set to True to create webp file (image format).
  Required `createUgoira = True` and ffmpeg executeable.

## [Filename]
- filenameformat

  The format for the filename, reserved/illegal character will be replaced with underscore '_', repeated space will be trimmed to single space. The filename (+full path) will be trimmed to the first 250 character (Windows limitation).
  Refer to Filename Format Syntax for available format.
- filenamemangaformat

  Similar to filename format, but for manga pages.
- filenameinfoformat

  Similar to filename format, but for info dumps.
- filenameSeriesJSON

  Similar to filename format, but for series JSON dumps.
- avatarNameFormat

  Similar to filename format, but for the avatar image.
  Not all formats are available.
- backgroundNameFormat

  Similar to filename format, but for the background image.
  Not all formats are available.
- tagsseparator

  Separator for each tag in filename, put %space% for space and %ideo_space% for ideographic space ("　").
- createmangadir

  Create a directory if the imageMode is manga. The directory is created by splitting the image_id by '_pxx' pattern.
  This setting is depends on %urlFilename% format.
- usetagsasdir

  Append the query tags in tagslist.txt to the root directory as save folder.
- urlDumpFilename

  Define the dump filename, use python strftime() format.
  Default value is 'url_list_%Y%m%d'
- filenameFormatSketch

  Similar to filename format, but for Pixiv Sketch.
- customBadChars

  For sanitizing filenames with custom rules. Supports regular expressions.
  For detailed syntax, please refer to 'Bad chars' section.

# Filename Format Syntax
Available for filenameFormat, filenameMangaFormat, avatarNameFormat, filenameInfoFormat,
filenameFormatFanboxCover, filenameFormatFanboxContent and filenameFormatFanboxInfo:
```
-> %member_token%
   Member token, might change.
-> %member_id%
   Member id, in number.
-> %artist%
   Artist name, might change too.
-> %urlFilename%
   The actual filename stored in server without the file extensions.
-> %date%
   Current date in YYYYMMMDD format.
-> %date_fmt{format}%
   Current date using custom format.
   Use Python string format notation, refer: https://goo.gl/3UiMAb
   e.g. %date_fmt{%Y-%m-%d}%
```
Available for filenameFormat and filenameMangaFormat:
```
-> %image_id%
   Image id, in number.
-> %title%
   Image title, usually in japanese character.
-> %tags%
   Image tags, usually in japanese character. (not implemented for FANBOX yet)
-> %works_date%
   Works date, complete with time.
-> %works_date_only%
   Only the works date.
-> %works_date_fmt{<format>}%
   works date using custom format.
   Use Python string format notation, refer: https://goo.gl/3UiMAb
   e.g. %works_date_fmt{%Y-%m-%d}%
-> %works_res%
   Image resolution, will be containing the page count if manga.
-> %works_tools%
   Tools used for the image.
-> %R-18%
   Append R-18/R-18 based on image tag, can be used for creating directory
   by appending directory separator, e.g.: %R-18%\%image_id%.
-> %page_big%
   for manga mode, add big in the filename.
-> %page_index%
   for manga mode, add page number with 0-index.
-> %page_number%
   for manga mode, add page number with 1-index.
-> %bookmark%
   for bookmark mode, add 'Bookmarks' string.
-> %original_member_id%
   for bookmark mode, put original member id.
-> %original_member_token%
   for bookmark mode, put original member token.
-> %original_artist%
   for bookmark mode, put original artist name.
-> %searchTags%
   for download by tags and bookmarked images, put searched tags.
-> %bookmark_count%
   Bookmark count, will have overhead except on download by tags.
-> %image_response_count%
   Image respose count, will have overhead except on download by tags.
-> %manga_series_order%
   the order in the manga series.
-> %manga_series_id%
   original manga series id.
-> %manga_series_title%
   original manga series title, different from work title.
```
Specific for PixivSketch (option 1 if PixivSketch included, s1, and s2 ):
```
-> %sketch_member_id%
   Pixiv Sketch artist id, might be different from Pixiv's artist id.
```
# list.txt Format
- This file should be build in the following way, white space will be trimmed,
  see example:
```
member_id1 directory1
member_id2 directory2
  ...
#comment - lines starting with # will be ignored
```
- member_id = in number only
- directory = path to download-directory for member_id
  - %root%\directory will save directory in rootFolder specified in config.ini
    \directory will save the folder in the root of your PixivUtil-drive
  - C:\directory will save the folder in drive C: (change to any other
    drive as you wish)
  - .\directory will save the folder in same directory as PixivUtil2.exe
  - directory-path can end with \ or not

- Examples for list:
```
### START EXAMPLE LIST####
# this is a comment line, lines starting with # will be ignored
# here is the first member:
123456
# you can see, the line has only the member id
# usually I use it the following way:
#
# username (so I can recognize it ;) )
123456
#
# next 2 lines contain a special folder for this member
123456 .\test
123456 ".\test"
# now all images from member no. 123456 will be safed in directory "test" in the
# same directory as PixivUtil2
# as you can see you can use it with "" or without ;)
#
# next will be stored at the same partition as PixivUtil, but the directory is
# located in root-part of it
123456 \test
123456 "\test"
# this will lead to "C:\test" when pixivUtil is located on "C:\"
#
# next line uses complete path to store the files
123456 F:\new Folder\test
123456 "F:\new Folder\test"
# this will set the folder everywhere on your partitions
#
123456 %root%\special folder
123456 "%root%\special folder"
# this will set the download location to "special folder" in your rootDirectory
# given in config
http://www.pixiv.net/member.php?id=123456
http://www.pixiv.net/member_illust.php?id=123456
# also support url format.
### END EXAMPLE LIST####
```

# tags.txt Format
- This file will be used as source for Download from tags list (7)
- Separate tags with space, ensure to set Use Wildcard to 'y'.
- Each line will be treated as one search.
- Save the files with UTF-8 encoding.

# suppress_tags.txt Format
- This file is used for suppressing the tags from being used in %tags%.
- If matches, the tags will be removed from filename.
- Each line is one tag only.
- Save the files with UTF-8 encoding


# blacklist_tags.txt Format
- This file is used for tag blacklist checking for downloading image.
- If matches, the image will be skipped.
- Each line is one tag only.
- Save the files with UTF-8 encoding

# blacklist_members.txt Format
- similar to list.txt, but without custom folder.

# HTML Format
- A simple default format will be used when no 'template.html' is provided.
- Urls originally in the post will be overwritten with local paths.
- Currently available syntaxes are:
```
-> %coverImage%
   A 'div' tag with its 'class' set to 'cover', and a child 'img' tag with 
   the url to the cover image as its 'src' attribute.
-> %coverImageUrl%
   Simply the url to the cover image in clear text.
-> %artistName%
   Same as %artist% in 'Filename Format Syntax' in clear text.
-> %imageTitle%"
   Title of the post in clear text.
-> "%worksDate%"
   Published date of the post in clear text.
-> %body_text(article)%
   This works for article type posts only.
   A 'div' tag with its 'class' set to 'article', and the post's content,
   which is already formatted HTML if the post is article, as its inner text.
-> %images(non-article)%
   This works for none-article type posts only.
   A 'div' tag with its 'class' set to 'non-article images', and 'a' tags
   of all files in the post as its children tokens.
   For each 'a' tag, its 'href' would be url to the file, and the inner text
   would be an 'img' tag with its 'src' set to the url to the file if the
   file's extension is 'jpg', 'jpeg', 'png' or 'bmp'. Otherwise the inner text
   would simply be the url to the file.
-> %text(non-article)%
   This works for none-article type posts only.
   A 'div' tag with its 'class' set to 'non-article text' and all paragraphs
   of text put in 'p' tags as its children tokens.
```
- If there is a 'div' tag with 'main' in its 'class' in the template, 'article' or 
  'non-article' would be appended to its 'class' depending on the type of the post.

# Bad chars
- Originally for removing single bad chars for use between different OSs.
- Now also supports strings and regular expressions.
- The value set in option `customBadChars` would be parsed from left to right.
- Currently available syntaxes are:
```
-> %replace<default>(your_default_replace_with)%
   Use this syntax to define default value to replace with.
   If this syntax gets used multiple times in the option value, the first value would be used.
   If this value is not set, "_" would be used.
-> %pattern<you_group_name>(your_pattern)%
-> %replace<you_group_name>(your_replace_with)%
   Use these two syntaxes to set groups of rules. Supports regular expression.
   You should not use "default" as group names, otherwise the first replace would
   be parsed as default value to replace with, while the others would be ignored.
   Groups with no "pattern" would be ignored.
   Groups with no "replace" use default value.
   If multiple "pattern"s or "replace"s share the same group name, the last value set
   would be used.
```
- Chars/string not wrapped with syntaxes above would be considered single chars
  to be replaced with global replacement char/string, "_" if unset.
- When configuration file gets written to file, `customBadChars` would be
  replaced with parsed valid value. Single chars would be placed first, followed by
  `%replace<default>(your_default_replace_with)%`, and each group.
- Examples:
```
# If you just want to replace some single chars with "_"
\@[]
# If you want to replace them with "@":
\@[]%replace<default>(@)%
# If you want to replace certain words:
# This example would first replace all "maze" with "labyrinth",
# then all "labyrinth" with "nevermind"
%pattern<1>(maze)%%replace<1>(labyrinth)%%pattern<2>(labyrinth)%%replace<2>(nevermind)%
# If you want to replace characters within certain unicode range,
# then remove all continuous "_"s with a single "_":
%pattern<unicode>([\U0001d400-\U0001ffff])%%pattern<1>(_+)%%replace<1>(_)%
```


# Credits/Contributor
- Nandaka (Main Developer) - https://nandaka.devnull.zone
- Yavos (Contributor)
- Joe (Contributor)
- Hamuko <hamuko@burakku.com>
- Kwang Ketcham <prototype27+github@prototype27.com>
- woky <nechtom@gmail.com>
- a.evseev <nmbr213@gmail.com>
- pixtrix
- Abram Wiebe <awiebe@burningthumb.com>
- Masaki Takano
- hi117
- Wildfoot
- J.Gocke
- Magnus Boman
- Abdulah Jasim
- Yifei Fu
- nixxquality
- DukeValentine
- NHOrus
- whinette
- yzaoui
- Kieri Suizahn
- amatuerCoder
- Alex
- wmjdgla
- fireattack
- Jared Shields
- DenDen047

** If I forget someone, please send me a pull request with the commit/merge id.

# License Agreement
See LICENSE.


[![Run on Repl.it](https://repl.it/badge/github/Nandaka/PixivUtil2)](https://repl.it/github/Nandaka/PixivUtil2)
