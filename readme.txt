Requirement:
- Python 2.7.2++
- mechanize 0.2.5
- BeautifulSoup 3.2.0

Capabilities:
- Download by member_id
- Download by image_id
- Download by tags
- Download from list (list.txt)
- Download from user bookmark (http://www.pixiv.net/bookmark.php?type=user), including private.
- Download from image bookmark (http://www.pixiv.net/bookmark.php), including private.
- Download from tags list (tags.txt)
- Download new illust from bookmarks (http://www.pixiv.net/bookmark_new_illust.php)
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

By Yavos:

<<< commandline >>>
-s <number> 	will start PixivUtil in mode <number>, allowed are the following ones:
		1 - Download by member_id (optional: followed by member_ids separated by space)
		2 - Download by image_id (optional: folled by image_ids separated by space)
		3 - Download by tags (optional: followed by tags)
		4 - Download from list (optional: followed by path to list)
		5 - Manage database

-n <number>		will temporarily set pagelimit to <number> pages

-i		will load IrfanView with downloaded images when not already set in config.ini

-x		will exit programm when selected mode is finished


<<< config.ini >>>
[Authentication]
username ==> Your pixiv username.
password ==> Your pixiv password, in clear text!
cookie   ==> Your cookies for pixiv login, will be automatically updated when login. 

[Pixiv]
numberofpage ==> Number of page to be processed, put '0' to process all pages.
formorder    ==> Pixiv login form order, do not change.

[Settings]
userobots      ==> Download robots.txt for mechanize.
rootdirectory  ==> Your root directory for saving the images.
useproxy       ==> Set 'True' to use proxy server, 'False' to disable it.
retrywait      ==> Waiting time for each retry, in seconds.
proxyaddress   ==> Proxy server address, use this format: http://<username>:<password>@<proxy_server>:<port>
uselist        ==> set to 'True' to parse list.txt. This will always update the DB content from the list.txt (member_id and custom folder).
daylastupdated ==> Only process member_id which x days from the last check.
processfromdb  ==> Set 'True' to use the DB.
retry          ==> Number of retries.
debughttp      ==> Print http header, useful for debuggin. Set 'False' to disable.
timeout        ==> Time to wait before giving up the connection, in seconds.
filenameformat ==> The format for the filename, reserved/illegal character will be replace with underscore '_'
                -> The filename (+full path) will be trimmed to the first 250 character (Windows limitation).
	        -> %member_token% ==> member token, doesn't change.
	        -> %member_id%    ==> member id, in number.
	        -> %image_id%  ==> image id, in number.
	        -> %title%     ==> image title, usually in japanese character.
	        -> %tags%      ==> image tags, usually in japanese character.
	        -> %artist%    ==> artist name, may change.
useragent      ==> Browser user agent to spoof.
tagsseparator  ==> Separator for each tag, put %space% for space.
overwrite      ==> Overwrite old files, set 'False' to disable.
downloadlistdirectory ==> list.txt path.
alwaysCheckFileSize   ==> Check the file size, if different then it will be downloaded again, set 'False' to disable.
 		       -> Override the overwrite and image_id checking from db (always fetch the image page for checking the size)
checkUpdatedLimit     ==> Number of already downloaded image to be check before move to the next member. alwaysCheckFileSize must be set to False.
createDownloadLists   ==> set to <True> to automatically create download-lists
createmangadir  ==> Create a directory if the imageMode is manga. The directory is created by splitting the image_id by '_pxx' pattern.
downloadListDirectory ==> set directory for download-lists needed for createDownloadLists and IrfanView-Handling
	               -> if leaved blank it will create download-lists in pixivUtil-directory
startIrfanView  ==> set to <True> to start IrfanView with downloaded images when exiting pixivUtil
	         -> this will create download-lists
	         -> be sure to set IrfanView to load Unicode-Plugin on startup when there are unicode-named files!
startIrfanSlide ==> set to <True> to start IrfanView-Slideshow with downloaded images when exiting pixivUtil
	         -> this will create download-lists
	         -> be sure to set IrfanView to load Unicode-Plugin on startup when there are unicode-named files!
	         -> Slideshow-options will be same as you have set in IrfanView before!
IrfanViewPath   ==> set directory where IrfanView is installed (needed to start IrfanView)
downloadavatar  ==> set to 'True' to download the member avatar as 'folder.jpg' 

<<< list.txt >>>
- This file should be build in the following way, white space will be trimmed, see example:
  member_id1 directory1
  member_id2 directory2
  ...
  #comment - lines starting with # will be ignored

- member_id = in number only
- directory = path to download-directory for member_id
            %root%\directory will save directory in rootFolder specified in config.ini
	    \directory will save the folder in the root of your PixivUtil-drive
	    C:\directory will save the folder in drive C: (change to any other drive as you wish)
	    directory will save the folder in same directory as PixivUtil2.exe
	    directory-path can end with \ or not

- Examples for list:
### START EXAMPLE LIST####
#this is a comment line, lines starting with # will be ignored
#here is the first member:
123456
#you can see, the line has only the member id
#usually I use it the following way:
#
#username (so I can recognize it ;) )
123456
#
#next 2 lines contain a special folder for this member
123456 test
123456 "test"
#now all images from member no. 123456 will be safed in directory "test" in the same directory as PixivUtil2
#as you can see you can use it with "" or without ;)
#
#next will be stored at the same partition as PixivUtil, but the directory is located in root-part of it
123456 \test
123456 "\test"
#this will lead to "C:\test" when pixivUtil is located on "C:\"
#
#next line uses complete path to store the files
123456 F:\new Folder\test
123456 "F:\new Folder\test"
#this will set the folder everywhere on your partitions
#
123456 %root%\special folder
123456 "%root%\special folder"
#this will set the download location to "special folder" in your rootDirectory given in config
### END EXAMPLE LIST####
