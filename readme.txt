================================================================================
= Requirement:                                                                 =
================================================================================
- Running from windows binary:
  - Windows XP and up.

- Running from source code:
  - Python 2.7.2++ (http://www.python.org/)
  - mechanize 0.2.5 (http://wwwsearch.sourceforge.net/mechanize/)
  - BeautifulSoup 3.2.0 (http://www.crummy.com/software/BeautifulSoup/)
  - socksipy-branch 1.02+ (https://socksipy-branch.googlecode.com/)

================================================================================
= Capabilities:                                                                =
================================================================================
- Download by member_id
- Download by image_id
- Download by tags
- Download from list (list.txt)
- Download from user bookmark (http://www.pixiv.net/bookmark.php?type=user), 
  including private/hidden bookmarks.
- Download from image bookmark (http://www.pixiv.net/bookmark.php), including
  private/hidden bookmarks.
- Download from tags list (tags.txt)
- Download new illustrations from bookmarks 
  (http://www.pixiv.net/bookmark_new_illust.php)
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
  - Clean Up Database (remove db entry if downloaded file is missing)
- Export user bookmark (member_id) to a text files.

=================================================================================
= FAQs:                                                                         =
=================================================================================
A.Usage:
  Q1. How to paste japanese tags to the console window?
      - Click the top-left icon -> select Edit -> Paste (Cannot use Ctrl-V), if 
        it show up as question mark -> Change the Language for non-Unicode 
        program to Japanese (google it).
      - or use online url encoder (http://meyerweb.com/eric/tools/dencoder/) 
        and paste the encoded tag back to the console.
      - or paste it to tags.txt and select download by tags list. Separate each
        tags with space, and separate with new line for new query.
  Q2. My password doesn't show up in the console!
      - This is normal. The program still read it.
      - or you can put in the config.ini if not sure.
  Q3. I cannot login to pixiv!
      - Check your password.
      - Try to login to the Pixiv Website.
      - Try to use the config.ini on the [Authentication] section.
      - Check your date and time setting (e.g.: http://www.timeanddate.com/)
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

B.Bugs/Source Code/Supports:
  Q1. Where I can report for bugs?
      - just tell me via comment in my blog (http://nandaka.wordpress.com) and I
        will reply you back.
  Q2. Where I can support/donate to you?
      - You can send it to my PayPal account (nchek2000[at]gmail[dot]com).
      - or use the donation button on my blog (http://nandaka.wordpress.com).
  Q3. I want to use/modify the source code!
      - Feel free to use/modify the source code as long you give credit to me and
        make the modificated source code open.
      - if you want to add feature/bug fix, you can do branch from public 
        repository in https://git.bettercodes.org/pixiv-downloader (need to 
        register first) and I will do the merge.
  Q4. I got ValueError: invalid literal for int() with base 10: '<something>'
      - Please modify _html.py from mechanize library, search for 
        'def unescape_charref(data, encoding):' and replace with patch in 
        http://pastebin.com/5bT5HFkb.
  Q5. I got '<library_name> module no found error'
      - Download the library from the source (see links from the Requirements 
        section) and copy the file into your Lib\site-packages directory.
      - Or use pip install (google on how to use).

C.Log Messages:
Q1: HTTPError: HTTP Error 404: Not Found
    - This is because the file doesn't exists in the pixiv server, usually 
       because there is no big images version for the manga mode (currently the
       apps will try to download the big version first then try the normal size
       if failed, this is only for the manga mode and it is normal).

Q2: Error at process_image(): (<type 'exceptions.WindowsError'>, WindowsError
    (32, 'Prosessi ei voi kayttaa tiedostoa, koska se on toisen prosessin 
    kaytossa')
    - The file is being used by another process (google translate). Either you 
      ran multiple instace of pixiv downloader from the same folder, or there 
      are other processes locking the file/db.sqllite (usually from antivirus 
      or some sync/backup application).

Q3: Error at process_image(): (<type 'exceptions.AttributeError'>, 
    AttributeError ("'NoneType' object has no attribute 'find'",)
    - Usually this is because of login failed (cookie not valid). Try to change
      your password to simple one for testing, or copy the cookie from browser:
      1. Open Firefox.
      2. Login to your pixiv, remember to enable [Remember Me] check box.
      3. Right click the page and select View Page Info.
      4. Click the Security tab.
      5. Click the View Cookies button.
      6. Look for Cookie named = PHPSESSID.
      7. Copy the content value.
      8. Open config.ini, go to [Authentication] section, paste the value to 
         cookie, set 'keepsignedin = 1'.
    - Or because pixiv have changed the layout code, so the pixiv 
      downloader cannot parse the page correctly. Please tell me by put a 
      comment if this happen and include the details, such as the member/image id,
      dump html, and log file (check on the application folder).

Q4: URLError: <urlopen error [Errno 11004] getaddrinfo failed>
    - This is because the pixiv downloader cannot resolve the address to 
      download the images, please try to restart the network connection or do 
      ipconfig /flushdns to refresh the dns cache (windows).

Q5: Error at download_image(): (<class 'socket.timeout'>, timeout('timed out',)
    - This is because the pixiv downloaded didn't receive any reply for 
      specified time in config.ini from pixiv. Please retry the download again 
      later.

Q6: httperror_seek_wrapper: HTTP Error 403: request disallowed by robots.txt
    - Set userobots = False in config.ini

=================================================================================
= Command Line Option                                                           =
=================================================================================
  -h, --help            show this help message and exit
  -s STARTACTION, --startaction=STARTACTION
                        Action you want to load your program with:
                        1 - Download by member_id 
                            (required: followed by member_ids separated by space)
                        2 - Download by image_id  
                            (required: folled by image_ids separated by space)
                        3 - Download by tags      
                            (required: [y/n] for wildcard, start page, end page, 
                             followed by tags)
                        4 - Download from list    
                            (optional: followed by path to list)
                        5 - Download from user bookmark
                            (optional: followed by [y/n] for private bookmark)
                        6 - Download from image bookmark
			    (required: followed by [y/n] for private bookmark
                             optional: starting page number and end page number)
                        7 - Download from tags list
                            (required: followed by path to the tags list, 
                             start page, and end page)
                        8 - Download new illust from bookmark
                            (optional: followed by starting page number and end 
                             page number)
                        9 - Download by Title/Caption
                            (required: start page, end page, followed by 
                             title/caption)
			10 - Download by Tag and Member Id
			    (required: member_id, start page, end page, followed 
                             by tags)
                        11 - Download Member's Bookmarked Images
                            (required: followed by member_ids separated by space)
                        12 - Download by Group ID
                            (required: Group ID, limit, and process external[y/n])
                        e - Export online bookmark
                        d - Manage database
  -x, --exitwhendone    Exit programm when done. 
                        (only useful when DB-Manager)
  -i, --irfanview       start IrfanView after downloading images using
                        downloaded_on_%date%.txt
  -n NUMBEROFPAGES, --numberofpages=NUMBEROFPAGES
                        temporarily overwrites numberOfPage set in config.ini

=================================================================================
= error codes                                                                   =
=================================================================================
- 100  = Not Logged in.
- 1001 = User ID not exist/deleted.
- 1002 = User Account is Suspended.
- 1003 = Unknown Member Error.
- 1004 = No image found.
- 2001 = Unknown Error in Image Page.
- 2002 = Not in MyPick List, Need Permission.
- 2003 = Public works can not be viewed by the appropriate level.
- 2004 = Image not found/already deleted.
- 2005 = Image is disabled for under 18, check your setting page (R-18/R-18G).
- 2006 = Unknown Image Error.

=================================================================================
= config.ini                                                                    =
=================================================================================
[Authentication]
username ==> Your pixiv username.
password ==> Your pixiv password, in clear text!
cookie   ==> Your cookies for pixiv login, will be automatically updated in the
             login.
usessl   ==> Use secure form (https://ssl.pixiv.net/login.php).
keepsignedin ==> Set to 1 to tick the keep signed in check box on login form.

[Pixiv]
numberofpage ==> Number of page to be processed, put '0' to process all pages.
r18mode      ==> Only list images tagged R18, for member, member's bookmark,
                 and search by tag.
                 Set to 'True' to apply.

[Settings]
userobots      ==> Download robots.txt for mechanize.
rootdirectory  ==> Your root directory for saving the images.
useproxy       ==> Set 'True' to use proxy server, 'False' to disable it.
retrywait      ==> Waiting time for each retry, in seconds.
proxyaddress   ==> Proxy server address, use this format:                    
		   http://<username>:<password>@<proxy_server>:<port> or 
                   socks5://<username>:<password>@<proxy_server>:<port> or 
                   socks4://<username>:<password>@<proxy_server>:<port>
uselist        ==> set to 'True' to parse list.txt. 
                   This will update the DB content from the list.txt
                   (member_id and custom folder).
daylastupdated ==> Only process member_id which x days from the last check.
processfromdb  ==> Set 'True' to use the member_id from the DB.
retry          ==> Number of retries.
debughttp      ==> Print http header, useful for debuggin. Set 'False' to
                   disable.
timeout        ==> Time to wait before giving up the connection, in seconds.
filenameformat ==> The format for the filename, reserved/illegal character will
                   be replaced with underscore '_', repeated space will be 
                   trimmed to single space.
                -> The filename (+full path) will be trimmed to the first 250
                   character (Windows limitation).
	        -> %member_token% ==> member token, doesn't change.
	        -> %member_id%    ==> member id, in number.
	        -> %image_id%     ==> image id, in number.
	        -> %title%        ==> image title, usually in japanese character.
	        -> %tags%         ==> image tags, usually in japanese character.
	        -> %artist%       ==> artist name, may change.
	        -> %works_date%   ==> works date, complete with time.
	        -> %works_date_only% ==> only the works date.
	        -> %works_res%    ==> image resolution, will be containing the page 
                                      count if manga.
	        -> %works_tools%  ==> tools used for the image.
	        -> %R-18%         ==> Append R-18/R-18 based on image tag, can be used
                                      for creating directory by appending directory
                                      separator, e.g.: %R-18%\%image_id%.
	        -> %urlFilename%  ==> the actual filename stored in server without
                                      the file extensions.
	        -> %page_big%     ==> for manga mode, add big in the filename.
	        -> %page_index%   ==> for manga mode, add page number with 0-index.
	        -> %page_number%  ==> for manga mode, add page number with 1-index.
	        -> %bookmark%     ==> for bookmark mode, add 'Bookmarks' string.
	        -> %original_member_id%    ==> for bookmark mode, put original member
                                               id.
	        -> %original_member_token% ==> for bookmark mode, put original member 
                                               token.
	        -> %original_artist%       ==> for bookmark mode, put original artist
                                               name.
	        -> %searchTags%   ==> for download by tags, put searched tags.
	        -> %date%         ==> current date in YYYYMMMDD format.
	        -> %bookmark_count% ==> Bookmark count, will have overhead except on
                                        download by tags.
                -> %image_response_count%  ==> Image respose count, will have overhead 
					       except on download by tags.
useragent      ==> Browser user agent to spoof.
tagsseparator  ==> Separator for each tag in filename, put %space% for space.
overwrite      ==> Overwrite old files, set 'False' to disable.
downloadlistdirectory ==> list.txt path.
alwaysCheckFileSize   ==> Check the file size, if different then it will be
                          downloaded again, set 'False' to disable.
 		       -> Override the overwrite and image_id checking from db
                          (always fetch the image page for checking the size)
checkUpdatedLimit     ==> Number of already downloaded image to be check before
                          move to the next member. alwaysCheckFileSize must be 
                          set to False.
createDownloadLists   ==> set to <True> to automatically create download-lists.
createmangadir  ==> Create a directory if the imageMode is manga. The directory
                    is created by splitting the image_id by '_pxx' pattern.
                    This setting is depended on %urlFilename% format.
downloadListDirectory ==> set directory for download-lists needed for 
                          createDownloadLists and IrfanView-Handling
	               -> if leaved blank it will create download-lists in 
                          pixivUtil-directory.
startIrfanView  ==> set to <True> to start IrfanView with downloaded images when
                    exiting pixivUtil
	         -> this will create download-lists
	         -> be sure to set IrfanView to load Unicode-Plugin on startup
                    when there are unicode-named files!
startIrfanSlide ==> set to <True> to start IrfanView-Slideshow with downloaded 
                    images when exiting pixivUtil.
	         -> this will create download-lists
	         -> be sure to set IrfanView to load Unicode-Plugin on startup
                    when there are unicode-named files!
	         -> Slideshow-options will be same as you have set in IrfanView 
                    before!
IrfanViewPath   ==> set directory where IrfanView is installed (needed to start 
                    IrfanView)
downloadavatar  ==> set to 'True' to download the member avatar as 'folder.jpg'
usetagsasdir 	==> Append the query tags in tagslist.txt to the root directory 
                    as save folder.
useblacklisttags==> Skip image if containing blacklisted tags.
                    The list is taken from blacklist_tags.txt, each tags is 
                    separated by new line.
usesuppresstags	==> Remove the suppressed tags from %tags% meta for filename.
                    The list is taken from suppress_tags.txt, each tags is 
                    separated by new line.
tagsLimit	==> Number of tags to be used for %tags% meta in filename.
		    Use -1 to use all tags.
writeimageinfo  ==> set to 'True' to export the image information to text file.
                    The filename is following the image filename + .txt.
dateDiff        ==> Gets only pictures that were posted X days before the system 
                    date. Set 0 to disable. Skip to next member id if in Download
                    by Member, stop processing if in Download New Illust.
backupOldFile   ==> Set to True to backup old file if the file size is different.
                    Old filename will be renamed to filename.unix-time.extension.
logLevel        ==> Set log level, valid values are CRITICAL, ERROR, WARNING, 
                    INFO, DEBUG, and NOTSET
enableDump      ==> Enable HTML Dump. Set to False to disable.
skipDumpFilter  ==> Skip HTML Dump based on error code (using regex format).
                    E.g.: 1.*|2.* => skip all HTML dump for error code 1xxx/2xxx.
dumpMediumPage  ==> Dump all medium page for debugging. Set to True to enable.

=================================================================================
= list.txt Format                                                               =
=================================================================================
- This file should be build in the following way, white space will be trimmed, 
  see example:
  
member_id1 directory1
member_id2 directory2
  ...
#comment - lines starting with # will be ignored

- member_id = in number only
- directory = path to download-directory for member_id
  - %root%\directory will save directory in rootFolder specified in config.ini
    \directory will save the folder in the root of your PixivUtil-drive
  - C:\directory will save the folder in drive C: (change to any other
    drive as you wish)
  - .\directory will save the folder in same directory as PixivUtil2.exe
  - directory-path can end with \ or not

- Examples for list:
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
### END EXAMPLE LIST####

=================================================================================
= tags.txt Format                                                               =
=================================================================================
- This file will be used as source for Download from tags list (7)
- Separate tags with space.
- Each line will be treated as one search.
- Save the files with UTF-8 encoding

=================================================================================
= suppress_tags.txt Format                                                      =
=================================================================================
- This file is used for suppressing the tags from being used in %tags%.
- If matches, the tags will be removed from filename.
- Each line is one tag only.
- Save the files with UTF-8 encoding

=================================================================================
= blacklist_tags.txt Format                                                     =
=================================================================================
- This file is used for tag blacklist checking for downloading image.
- If matches, the image will be skipped.
- Each line is one tag only.
- Save the files with UTF-8 encoding

=================================================================================
= Credits                                                                       =
=================================================================================
- Nandaka (Main Developer)
- Yavos (Contributor)
- Joe (Contributor)

*If I forget someone, please leave me a comment in my Blog.

=================================================================================
= License Agreement                                                             =
=================================================================================
Copyright (c) 2011, Nandaka
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this 
    list of conditions and the following disclaimer.
  - Redistributions in binary form must reproduce the above copyright notice, 
    this list of conditions and the following disclaimer in the documentation 
    and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR 
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS 
OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY 
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING 
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN 
IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
