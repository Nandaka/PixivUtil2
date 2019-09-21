#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable=C0330


import codecs
import os
import re
import sqlite3
import sys
from datetime import datetime

import PixivConfig
import PixivHelper
from PixivModel import PixivListItem

script_path = PixivHelper.module_path()


class PixivDBManager(object):
    """Pixiv Database Manager"""
    __config__ = None

    def __init__(self, target='', config=None, timeout=5 * 60):
        if target is None or len(target) == 0:
            target = script_path + os.sep + "db.sqlite"
            PixivHelper.print_and_log('info', "Using default DB Path: " + target)
        else:
            PixivHelper.print_and_log('info', "Using custom DB Path: " + target)

        self.conn = sqlite3.connect(target, timeout)
        if config is not None:
            self.__config__ = config
        else:
            self.__config__ = PixivConfig.PixivConfig()
            self.__config__.loadConfig()

    def close(self):
        self.conn.close()

##########################################
## I. Create/Drop Database              ##
##########################################
    def createDatabase(self):
        print('Creating database...', end=' ')

        try:
            c = self.conn.cursor()

            c.execute('''CREATE TABLE IF NOT EXISTS pixiv_master_member (
                            member_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
                            name TEXT,
                            save_folder TEXT,
                            created_date DATE,
                            last_update_date DATE,
                            last_image INTEGER
                            )''')

            self.conn.commit()

            # add column isDeleted
            # 0 = false, 1 = true
            try:
                c.execute('''ALTER TABLE pixiv_master_member ADD COLUMN is_deleted INTEGER DEFAULT 0''')
                self.conn.commit()
            except BaseException:
                pass

            c.execute('''CREATE TABLE IF NOT EXISTS pixiv_master_image (
                            image_id INTEGER PRIMARY KEY,
                            member_id INTEGER,
                            title TEXT,
                            save_name TEXT,
                            created_date DATE,
                            last_update_date DATE
                            )''')
            # add column isManga
            try:
                c.execute('''ALTER TABLE pixiv_master_image ADD COLUMN is_manga TEXT''')
            except BaseException:
                pass

            c.execute('''CREATE TABLE IF NOT EXISTS pixiv_manga_image (
                            image_id INTEGER,
                            page INTEGER,
                            save_name TEXT,
                            created_date DATE,
                            last_update_date DATE,
                            PRIMARY KEY (image_id, page)
                            )''')
            self.conn.commit()

            print('done.')
        except BaseException:
            print('Error at createDatabase():', str(sys.exc_info()))
            print('failed.')
            raise
        finally:
            c.close()

    def dropDatabase(self):
        try:
            c = self.conn.cursor()
            c.execute('''DROP IF EXISTS TABLE pixiv_master_member''')
            self.conn.commit()

            c.execute('''DROP IF EXISTS TABLE pixiv_master_image''')
            self.conn.commit()
        except BaseException:
            print('Error at dropDatabase():', str(sys.exc_info()))
            print('failed.')
            raise
        finally:
            c.close()
        print('done.')

    def compactDatabase(self):
        print('Compacting Database, this might take a while...')
        try:
            c = self.conn.cursor()
            c.execute('''VACUUM''')
            self.conn.commit()
        except BaseException:
            print('Error at compactDatabase():', str(sys.exc_info()))
            raise
        finally:
            c.close()
        print('done.')

##########################################
## II. Export/Import DB                 ##
##########################################
    def importList(self, listTxt):
        print('Importing list...', end=' ')
        print('Found', len(listTxt), 'items', end=' ')
        try:
            c = self.conn.cursor()

            for item in listTxt:
                c.execute('''INSERT OR IGNORE INTO pixiv_master_member VALUES(?, ?, ?, datetime('now'), '1-1-1', -1, 0)''',
                                  (item.memberId, str(item.memberId), r'N\A'))
                c.execute('''UPDATE pixiv_master_member
                             SET save_folder = ?
                             WHERE member_id = ? ''',
                          (item.path, item.memberId))
            self.conn.commit()
        except BaseException:
            print('Error at importList():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()
        print('done.')
        return 0

    def exportList(self, filename, include_artist_token=True):
        print('Exporting list...', end=' ')
        try:
            c = self.conn.cursor()
            c.execute('''SELECT member_id, save_folder, name
                         FROM pixiv_master_member
                         WHERE is_deleted = 0
                         ORDER BY member_id''')
            if not filename.endswith(".txt"):
                filename = filename + '.txt'

            writer = codecs.open(filename, 'wb', encoding='utf-8')
            writer.write('###Export date: ' + str(datetime.today()) + '###\r\n')
            for row in c:
                if include_artist_token:
                    data = str(row[2])
                    writer.write("# ")
                    writer.write(data)
                    writer.write("\r\n")
                writer.write(str(row[0]))
                if len(row[1]) > 0:
                    writer.write(' ' + str(row[1]))
                writer.write('\r\n')
            writer.write('###END-OF-FILE###')
        except BaseException:
            print('Error at exportList():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            if writer is not None:
                writer.close()
            c.close()
        print('done.')

    def exportDetailedList(self, filename):
        print('Exporting detailed list...', end=' ')
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM pixiv_master_member
                            WHERE is_deleted = 0
                            ORDER BY member_id''')
            filename = filename + '.csv'
            writer = codecs.open(filename, 'wb', encoding='utf-8')
            writer.write('member_id,name,save_folder,created_date,last_update_date,last_image,is_deleted\r\n')
            for row in c:
                for string in row:
                    # Unicode write!!
                    data = str(string)
                    writer.write(data)
                    writer.write(',')
                writer.write('\r\n')
            writer.write('###END-OF-FILE###')
            writer.close()
        except BaseException:
            print('Error at exportDetailedList(): ' + str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()
        print('done.')

##########################################
## III. Print DB                        ##
##########################################
    def printMemberList(self, isDeleted=False):
        print('Printing member list:')
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM pixiv_master_member
                         WHERE is_deleted = ?
                            ORDER BY member_id''', (int(isDeleted), ))
            print('%10s %25s %25s %20s %20s %10s %s' % ('member_id', 'name',
                'save_folder', 'created_date', 'last_update_date', 'last_image',
                'is_deleted'))
            i = 0
            for row in c:
                PixivHelper.safePrint('%10d %#25s %#25s %20s %20s %10d %5s' % (row[0], str(row[1]).strip(), row[2], row[3], row[4], row[5], row[6]))
                i = i + 1
                if i == 79:
                    select = input('Continue [y/n]? ')
                    if select == 'n':
                        break
                    else:
                        print('member_id\tname\tsave_folder\tcreated_date\tlast_update_date\tlast_image')
                        i = 0
        except BaseException:
            print('Error at printList():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()
        print('done.')

    def printImageList(self):
        print('Printing image list:')
        try:
            c = self.conn.cursor()
            c.execute(''' SELECT COUNT(*) FROM pixiv_master_image''')
            result = c.fetchall()
            if result[0][0] > 10000:
                print('Row count is more than 10000 (actual row count:', str(result[0][0]), ')')
                print('It may take a while to retrieve the data.')
                answer = input('Continue [y/n]')
                if answer == 'y':
                    c.execute('''SELECT * FROM pixiv_master_image
                                    ORDER BY member_id''')
                    print('')
                    for row in c:
                        for string in row:
                            print('   ', end=' ')
                            PixivHelper.safePrint(str(string), False)
                        print('')
                else:
                    return
            # Yavos: it seems you forgot something ;P
            else:
                c.execute('''SELECT * FROM pixiv_master_image
                                    ORDER BY member_id''')
                print('')
                for row in c:
                    for string in row:
                        print('   ', end=' ')
                        PixivHelper.safePrint(str(string), False)   # would it make more sense to set output to file?
                    print('')
            # Yavos: end of change
        except BaseException:
            print('Error at printImageList():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()
        print('done.')

##########################################
## IV. CRUD Member Table                ##
##########################################
    def insertNewMember(self):
        try:
            c = self.conn.cursor()
            member_id = 0
            while True:
                temp = input('Member ID: ')
                try:
                    member_id = int(temp)
                except BaseException:
                    pass
                if member_id > 0:
                    break

            c.execute('''INSERT OR IGNORE INTO pixiv_master_member VALUES(?, ?, ?, datetime('now'), '1-1-1', -1, 0)''',
                                  (member_id, str(member_id), r'N\A'))
        except BaseException:
            print('Error at insertNewMember():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def selectAllMember(self, isDeleted=False):
        l = list()
        try:
            c = self.conn.cursor()
            c.execute('''SELECT member_id, save_folder FROM pixiv_master_member WHERE is_deleted = ? ORDER BY member_id''', (int(isDeleted), ))
            result = c.fetchall()

            for row in result:
                item = PixivListItem(row[0], row[1])
                l.append(item)

        except BaseException:
            print('Error at selectAllMember():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

        return l

    def selectMembersByLastDownloadDate(self, difference):
        l = list()
        try:
            c = self.conn.cursor()
            try:
                int_diff = int(difference)
            except ValueError:
                int_diff = 7

            c.execute('''SELECT member_id, save_folder,  (julianday(Date('now')) - julianday(last_update_date)) as diff
                         FROM pixiv_master_member
                         WHERE is_deleted <> 1 AND ( last_image == -1 OR diff > ? ) ORDER BY member_id''', (int_diff, ))
            result = c.fetchall()
            for row in result:
                item = PixivListItem(row[0], row[1])
                l.append(item)

        except BaseException:
            print('Error at selectMembersByLastDownloadDate():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

        return l

    def selectMemberByMemberId(self, member_id):
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM pixiv_master_member WHERE member_id = ? ''', (member_id, ))
            return c.fetchone()
        except BaseException:
            print('Error at selectMemberByMemberId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def selectMemberByMemberId2(self, member_id):
        try:
            c = self.conn.cursor()
            c.execute('''SELECT member_id, save_folder FROM pixiv_master_member WHERE member_id = ? ''', (member_id, ))
            row = c.fetchone()
            if row is not None:
                return PixivListItem(row[0], row[1])
            else:
                return PixivListItem(int(member_id), '')
        except BaseException:
            print('Error at selectMemberByMemberId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def printMembersByLastDownloadDate(self, difference):
        rows = self.selectMembersByLastDownloadDate(difference)

        for row in rows:
            for string in row:
                print('   ', end=' ')
                PixivHelper.safePrint(str(string), False)
            print('\n')

    def updateMemberName(self, memberId, memberName):
        try:
            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_member
                            SET name = ?
                            WHERE member_id = ?
                            ''', (memberName, memberId))
            self.conn.commit()
        except BaseException:
            print('Error at updateMemberId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def updateSaveFolder(self, memberId, saveFolder):
        try:
            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_member
                            SET save_folder = ?
                            WHERE member_id = ?
                            ''', (saveFolder, memberId))
            self.conn.commit()
        except BaseException:
            print('Error at updateSaveFolder():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def updateLastDownloadedImage(self, memberId, imageId):
        try:
            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_member
                            SET last_image = ?, last_update_date = datetime('now')
                            WHERE member_id = ?''',
                            (imageId, memberId))
            self.conn.commit()
        except BaseException:
            print('Error at updateMemberId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def deleteMemberByMemberId(self, memberId):
        try:
            c = self.conn.cursor()
            c.execute('''DELETE FROM pixiv_master_member
                            WHERE member_id = ?''',
                            (memberId, ))
            self.conn.commit()
        except BaseException:
            print('Error at deleteMemberByMemberId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def deleteCascadeMemberByMemberId(self, memberId):
        try:
            c = self.conn.cursor()
            c.execute('''DELETE FROM pixiv_master_image
                            WHERE member_id = ?''',
                            (memberId, ))
            c.execute('''DELETE FROM pixiv_master_member
                            WHERE member_id = ?''',
                            (memberId, ))
            self.conn.commit()
        except BaseException:
            print('Error at deleteCascadeMemberByMemberId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def setIsDeletedFlagForMemberId(self, memberId):
        try:
            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_member
                            SET is_deleted = 1, last_update_date = datetime('now')
                            WHERE member_id = ?''',
                            (memberId,))
            self.conn.commit()
        except BaseException:
            print('Error at setIsDeletedMemberId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

##########################################
## V. CRUD Image Table                  ##
##########################################
    def insertImage(self, member_id, image_id, isManga=""):
        try:
            c = self.conn.cursor()
            member_id = int(member_id)
            image_id = int(image_id)
            c.execute('''INSERT OR IGNORE INTO pixiv_master_image VALUES(?, ?, 'N/A' ,'N/A' , datetime('now'), datetime('now'), ? )''',
                      (image_id, member_id, isManga))
            self.conn.commit()
        except BaseException:
            print('Error at insertImage():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def insertMangaImage(self, imageId, page, filename):
        try:
            c = self.conn.cursor()
            c.execute('''INSERT OR IGNORE INTO pixiv_manga_image VALUES(?, ?, ?, datetime('now'), datetime('now'))''',
                              (imageId, page, filename))
            self.conn.commit()
        except BaseException:
            print('Error at insertMangaImage():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def blacklistImage(self, memberId, ImageId):
        try:
            c = self.conn.cursor()
            c.execute('''INSERT OR REPLACE INTO pixiv_master_image VALUES(?, ?, '**BLACKLISTED**' ,'**BLACKLISTED**' , datetime('now'), datetime('now') )''',
                              (ImageId, memberId))
            self.conn.commit()
        except BaseException:
            print('Error at insertImage():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def selectImageByMemberId(self, member_id):
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM pixiv_master_image WHERE member_id = ? ''', (member_id,))
            return c.fetchall()
        except BaseException:
            print('Error at selectImageByImageId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def selectImageByMemberIdAndImageId(self, member_id, image_id):
        try:
            c = self.conn.cursor()
            c.execute('''SELECT image_id FROM pixiv_master_image WHERE image_id = ? AND save_name != 'N/A' AND member_id = ?''', (image_id, member_id))
            return c.fetchone()
        except BaseException:
            print('Error at selectImageByImageId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def selectImageByImageId(self, image_id, cols='*'):
        try:
            c = self.conn.cursor()
            c.execute('''SELECT %s FROM pixiv_master_image WHERE image_id = ? AND save_name != 'N/A' ''' % (cols,), (image_id,))
            return c.fetchone()
        except BaseException:
            print('Error at selectImageByImageId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def selectImageByImageIdAndPage(self, imageId, page):
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM pixiv_manga_image WHERE image_id = ? AND page = ? ''', (imageId, page))
            return c.fetchone()
        except BaseException:
            print('Error at selectImageByImageIdAndPage():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def updateImage(self, imageId, title, filename, isManga=""):
        try:
            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_image
                        SET title = ?, save_name = ?, last_update_date = datetime('now'), is_manga = ?
                        WHERE image_id = ?''',
                        (title, filename, isManga, imageId))
            self.conn.commit()
        except BaseException:
            print('Error at updateImage():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def deleteImage(self, imageId):
        try:
            c = self.conn.cursor()
            c.execute('''DELETE FROM pixiv_master_image
                        WHERE image_id = ?''',
                        (imageId, ))
            self.conn.commit()
        except BaseException:
            print('Error at deleteImage():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def checkFilenames(self, base_filename, exts):
        for ext2 in exts:
            check_name = base_filename + ext2
            if os.path.exists(check_name):
                return True
        return False

    def cleanupFileExists(self, filename):
        anim_ext = ['.zip', '.gif', '.apng', '.ugoira', '.webm']
        fileExists = False
        if filename is not None or len(filename) > 0:
            if os.path.exists(filename):
                return True
            for ext in anim_ext:
                # check filename in db against all combination possible filename in disk
                if filename.endswith(ext):
                    base_filename = filename.rsplit(ext, 1)[0]
                    if self.checkFilenames(base_filename, anim_ext):
                        fileExists = True
                        break
        return fileExists

    def cleanUp(self):
        anim_ext = ['.zip', '.gif', '.apng', '.ugoira', '.webm']
        try:
            print("Start clean-up operation.")
            print("Selecting all images, this may take some times.")
            c = self.conn.cursor()
            c.execute('''SELECT image_id, save_name from pixiv_master_image''')
            print("Checking images.")
            for row in c:
                # Issue 340
                filename = row[1]
                fileExists = False

                if filename is not None and len(filename) > 0:
                    if os.path.exists(filename):
                        continue

                    for ext in anim_ext:
                        # check filename in db against all combination possible filename in disk
                        if filename.endswith(ext):
                            base_filename = filename.rsplit(ext, 1)[0]
                            if self.checkFilenames(base_filename, anim_ext):
                                fileExists = True
                                break

                if not fileExists:
                    PixivHelper.safePrint("Missing: {0} at {1}".format(row[0], row[1]))
                    self.deleteImage(row[0])
            self.conn.commit()
        except BaseException:
            print('Error at cleanUp():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def interactiveCleanUp(self):
        l = []
        try:
            print("Start clean-up operation.")
            print("Selecting all images, this may take some times.")
            c = self.conn.cursor()
            print("Collecting missing images.")
            c.execute('''SELECT image_id, save_name from pixiv_master_image''')
            for row in c:
                # Issue 340
                filename = row[1]
                fileExists = self.cleanupFileExists(filename)
                if not fileExists:
                    l.append(row)
                    PixivHelper.safePrint("Missing: {0} at \n{1}".format(row[0], row[1]))

            while not len(l) == 0:
                # End scan
                print(l)
                regex = input("Please provide a search regex, use empty string to skip(Empty to stop now):")
                if regex == "":
                    break
                repl = input("Replace regex with what?")
                regex = re.compile(regex)

                # Replace any paths where replacement results in a correct path
                ll = []
                for row in l:
                    new_name = regex.sub(repl, row[1])
                    if self.cleanupFileExists(filename):
                        c.execute('''UPDATE pixiv_master_image
                            SET save_name = ?
                            WHERE id = ?''', (new_name, row[0]))
                    else:
                        ll.append(l)
                l = ll
            c.close()
            self.conn.commit()
        except BaseException:
            print('Error at interactiveCleanUp():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

        # TODO check mangaimage
        # TODO check for files which exist but don't have a DB entry

    def replaceRootPath(self):
        oldPath = input("Old Path to Replace = ")
        PixivHelper.safePrint("Replacing " + oldPath + " to " + self.__config__.rootDirectory)
        cont = input("continue[y/n]?") or 'n'
        if cont != "y":
            print("Aborted")
            return

        try:
            print("Start replace Root Path operation.")
            print("Updating images, this may take some times.")

            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_image
                         SET save_name = replace(save_name, ?, ?)
                         WHERE save_name like ?''', (oldPath, self.__config__.rootDirectory, oldPath + "%", ))
            print("Updated image:", c.rowcount)

            print("Updating manga images, this may take some times.")

            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_manga_image
                         SET save_name = replace(save_name, ?, ?)
                         WHERE save_name like ?''', (oldPath, self.__config__.rootDirectory, oldPath + "%", ))
            print("Updated manga image:", c.rowcount)

            print("Done")

        except BaseException:
            print('Error at replaceRootPath():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

##########################################
## VI. Utilities                        ##
##########################################
# def getInt(self, inputStr):
##        inputInt = None
# while True:
# try:
##                inputInt = int(inputStr)
# except:
# pass
# if inputInt != None:
# return inputInt
    def menu(self):
        print('Pixiv DB Manager Console')
        print('1. Show all member')
        print('2. Show all images')
        print('3. Export list (member_id only)')
        print('4. Export list (detailed)')
        print('5. Show member by last downloaded date')
        print('6. Show image by image_id')
        print('7. Show member by member_id')
        print('8. Show image by member_id')
        print('9. Delete member by member_id')
        print('10. Delete image by image_id')
        print('11. Delete member and image (cascade deletion)')
        print('12. Blacklist image by image_id')
        print('13. Show all deleted member')
        print('===============================================')
        print('c. Clean Up Database')
        print('i. Interactive Clean Up Database')
        print('p. Compact Database')
        print('r. Replace Root Path')
        print('x. Exit')
        selection = input('Select one?')
        return selection

    def main(self):
        try:
            while True:
                selection = self.menu()

                if selection == '1':
                    self.printMemberList()
                elif selection == '2':
                    self.printImageList()
                elif selection == '3':
                    filename = input('Filename? ')
                    includeArtistToken = input('Include Artist Token[y/n]? ')
                    if includeArtistToken.lower() == 'y':
                        includeArtistToken = True
                    else:
                        includeArtistToken = False
                    self.exportList(filename, includeArtistToken)
                elif selection == '4':
                    filename = input('Filename? ')
                    self.exportDetailedList(filename)
                elif selection == '5':
                    date = input('Number of date? ')
                    rows = self.selectMembersByLastDownloadDate(date)
                    if rows is not None:
                        for row in rows:
                            PixivHelper.safePrint("{0}\t\t{1}\n".format(row.memberId, row.path), False)
                    else:
                        print('Not Found!\n')
                elif selection == '6':
                    image_id = input('image_id? ')
                    row = self.selectImageByImageId(image_id)
                    if row is not None:
                        for string in row:
                            print('	', end=' ')
                            PixivHelper.safePrint(str(string), False)
                        print('\n')
                    else:
                        print('Not Found!\n')
                elif selection == '7':
                    member_id = input('member_id? ')
                    row = self.selectMemberByMemberId(member_id)
                    if row is not None:
                        for string in row:
                            print('	', end=' ')
                            PixivHelper.safePrint(str(string), False)
                        print('\n')
                    else:
                        print('Not Found!\n')
                elif selection == '8':
                    member_id = input('member_id? ')
                    rows = self.selectImageByMemberId(member_id)
                    if rows is not None:
                        for row in rows:
                            for string in row:
                                print('	', end=' ')
                                PixivHelper.safePrint(str(string), False)
                            print('\n')
                    else:
                        print('Not Found!\n')
                elif selection == '9':
                    member_id = input('member_id? ')
                    self.deleteMemberByMemberId(member_id)
                elif selection == '10':
                    image_id = input('image_id? ')
                    self.deleteImage(image_id)
                elif selection == '11':
                    member_id = input('member_id? ')
                    self.deleteCascadeMemberByMemberId(member_id)
                elif selection == '12':
                    member_id = input('member_id? ')
                    image_id = input('image_id? ')
                    self.blacklistImage(member_id, image_id)
                elif selection == '13':
                    self.printMemberList(isDeleted=True)
                elif selection == 'c':
                    self.cleanUp()
                elif selection == 'i':
                    self.interactiveCleanUp()
                elif selection == 'p':
                    self.compactDatabase()
                elif selection == 'r':
                    self.replaceRootPath()
                elif selection == 'x':
                    break
            print('end PixivDBManager.')
        except BaseException:
            print('Error: ', sys.exc_info())
            self.main()


if __name__ == '__main__':
    apps = PixivDBManager()
    apps.main()
