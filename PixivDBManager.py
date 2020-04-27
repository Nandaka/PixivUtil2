#!C:/Python37-32/python
# -*- coding: utf-8 -*-

import codecs
import os
import re
import sqlite3
import sys
from datetime import datetime

import PixivHelper
from PixivListItem import PixivListItem

script_path = PixivHelper.module_path()


class PixivDBManager(object):
    """Pixiv Database Manager"""
    rootDirectory = "."

    def __init__(self, root_directory, target='', timeout=5 * 60):
        if target is None or len(target) == 0:
            target = script_path + os.sep + "db.sqlite"
            PixivHelper.print_and_log(
                'info', "Using default DB Path: " + target)
        else:
            PixivHelper.print_and_log(
                'info', "Using custom DB Path: " + target)
        self.rootDirectory = root_directory
        self.conn = sqlite3.connect(target, timeout)

    def close(self):
        self.conn.close()

    ##########################################
    # I. Create/Drop Database                #
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
                c.execute(
                    '''ALTER TABLE pixiv_master_member ADD COLUMN is_deleted INTEGER DEFAULT 0''')
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
                c.execute(
                    '''ALTER TABLE pixiv_master_image ADD COLUMN is_manga TEXT''')
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

            # just to keep track of posts, not to record the details, so no columns like saved_to or caption or whatsoever
            c.execute('''CREATE TABLE IF NOT EXISTS fanbox_master_post (
                            member_id INTEGER,
                            post_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
                            title TEXT,
                            fee_required INTEGER,
                            published_date DATE,
                            updated_date DATE,
                            post_type TEXT,
                            last_update_date DATE
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

            c.execute('''DROP TABLE IF EXISTS pixiv_manga_image''')
            self.conn.commit()

            c.execute('''DROP TABLE IF EXISTS fanbox_master_post''')
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
    # II. Export/Import DB                  #
    ##########################################
    def importList(self, listTxt):
        print('Importing list...', end=' ')
        print('Found', len(listTxt), 'items', end=' ')
        try:
            c = self.conn.cursor()

            for item in listTxt:
                c.execute(
                    '''INSERT OR IGNORE INTO pixiv_master_member VALUES(?, ?, ?, datetime('now'), '1-1-1', -1, 0)''',
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
            writer.write('###Export date: {0} ###\r\n'.format(datetime.today()))
            for row in c:
                if include_artist_token:
                    data = row[2]
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
            writer.write(
                'member_id,name,save_folder,created_date,last_update_date,last_image,is_deleted\r\n')
            for row in c:
                for string in row:
                    # Unicode write!!
                    data = string
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

    def exportFanboxPostList(self, filename):
        print('Exporting FANBOX post list...', end=' ')
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM fanbox_master_post
                            ORDER BY member_id, post_id''')
            filename = filename + '.csv'
            writer = codecs.open(filename, 'wb', encoding='utf-8')
            writer.write(
                'member_id,post_id,title,fee_required,published_date,update_date,post_type,last_update_date\r\n')
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
            print('Error at exportFanboxPostList(): ' + str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()
        print('done.')

    ##########################################
    # III. Print DB                          #
    ##########################################
    def printMemberList(self, isDeleted=False):
        print('Printing member list:')
        try:
            c = self.conn.cursor()
            c.execute('''SELECT * FROM pixiv_master_member
                         WHERE is_deleted = ? ORDER BY member_id''', (int(isDeleted),))
            print('%10s %25s %25s %20s %20s %10s %s' % ('member_id',
                                                        'name',
                                                        'save_folder',
                                                        'created_date',
                                                        'last_update_date',
                                                        'last_image',
                                                        'is_deleted'))
            i = 0
            for row in c:
                print('%10d %#25s %#25s %20s %20s %10d %5s' %
                      (row[0], row[1].strip(), row[2], row[3], row[4], row[5], row[6]))
                i = i + 1
                if i == 79:
                    select = input('Continue [y/n]? ').rstrip("\r")
                    if select == 'n':
                        break
                    else:
                        print(
                            'member_id\tname\tsave_folder\tcreated_date\tlast_update_date\tlast_image')
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
                print('Row count is more than 10000 (actual row count:',
                      str(result[0][0]), ')')
                print('It may take a while to retrieve the data.')
                answer = input('Continue [y/n]').rstrip("\r")
                if answer == 'y':
                    c.execute('''SELECT * FROM pixiv_master_image
                                    ORDER BY member_id''')
                    print('')
                    for row in c:
                        for string in row:
                            print('   ', end=' ')
                            print(string)
                        print('')
                else:
                    return
            # Yavos: it seems you forgot something ;P
            else:
                c.execute(
                    '''SELECT * FROM pixiv_master_image ORDER BY member_id''')
                print('')
                for row in c:
                    for string in row:
                        print('   ', end=' ')
                        print(string)
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
    # IV. CRUD Member Table                  #
    ##########################################
    def insertNewMember(self, member_id=0):
        try:
            c = self.conn.cursor()
            if member_id == 0:
                while True:
                    temp = input('Member ID: ').rstrip("\r")
                    try:
                        member_id = int(temp)
                    except BaseException:
                        pass
                    if member_id > 0:
                        break

            c.execute('''INSERT OR IGNORE INTO pixiv_master_member VALUES(?, ?, ?, datetime('now'), '1-1-1', -1, 0)''',
                      (member_id, str(member_id), r'N\A'))
            self.conn.commit()
        except BaseException:
            print('Error at insertNewMember():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def selectAllMember(self, isDeleted=False):
        members = list()
        try:
            c = self.conn.cursor()
            c.execute(
                '''SELECT member_id, save_folder FROM pixiv_master_member WHERE is_deleted = ? ORDER BY member_id''',
                (int(isDeleted),))
            result = c.fetchall()

            for row in result:
                item = PixivListItem(row[0], row[1])
                members.append(item)

        except BaseException:
            print('Error at selectAllMember():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

        return members

    def selectMembersByLastDownloadDate(self, difference):
        members = list()
        try:
            c = self.conn.cursor()
            try:
                int_diff = int(difference)
            except ValueError:
                int_diff = 7

            c.execute('''SELECT member_id, save_folder,  (julianday(Date('now')) - julianday(last_update_date)) as diff
                         FROM pixiv_master_member
                         WHERE is_deleted <> 1 AND ( last_image == -1 OR diff > ? ) ORDER BY member_id''', (int_diff,))
            result = c.fetchall()
            for row in result:
                item = PixivListItem(row[0], row[1])
                members.append(item)

        except BaseException:
            print('Error at selectMembersByLastDownloadDate():',
                  str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

        return members

    def selectMemberByMemberId(self, member_id):
        try:
            c = self.conn.cursor()
            c.execute(
                '''SELECT * FROM pixiv_master_member WHERE member_id = ? ''', (member_id,))
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
            c.execute(
                '''SELECT member_id, save_folder FROM pixiv_master_member WHERE member_id = ? ''', (member_id,))
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
                print(string)
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
                         WHERE member_id = ?''', (imageId, memberId))
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
                      WHERE member_id = ?''', (memberId,))
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
                      WHERE member_id = ?''', (memberId,))
            c.execute('''DELETE FROM pixiv_master_member
                      WHERE member_id = ?''', (memberId,))
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
                         WHERE member_id = ?''', (memberId,))
            self.conn.commit()
        except BaseException:
            print('Error at setIsDeletedMemberId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    ##########################################
    # V. CRUD Image Table                    #
    ##########################################
    def insertImage(self, member_id, image_id, isManga=""):
        try:
            c = self.conn.cursor()
            member_id = int(member_id)
            image_id = int(image_id)
            c.execute(
                '''INSERT OR IGNORE INTO pixiv_master_image VALUES(?, ?, 'N/A' ,'N/A' , datetime('now'), datetime('now'), ? )''',
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
            c.execute('''INSERT OR IGNORE INTO pixiv_manga_image
                      VALUES(?, ?, ?, datetime('now'), datetime('now'))''',
                      (imageId, page, filename))
            self.conn.commit()
        except BaseException:
            print('Error at insertMangaImage():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def insertPost(self, member_id, post_id, title, fee_required, published_date, post_type):
        try:
            c = self.conn.cursor()
            post_id = int(post_id)
            c.execute(
                '''INSERT OR IGNORE INTO fanbox_master_post (member_id, post_id, last_update_date)
                VALUES(?, ?, datetime('now'))''', (member_id, post_id))
            c.execute(
                '''UPDATE fanbox_master_post SET title = ?, fee_required = ?, published_date = ?, post_type = ?
                WHERE post_id = ?''',
                (title, fee_required, published_date, post_type, post_id))
            self.conn.commit()
        except BaseException:
            print('Error at insertPost():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def selectPostByPostId(self, post_id):
        try:
            c = self.conn.cursor()
            post_id = int(post_id)
            c.execute(
                '''SELECT * FROM fanbox_master_post WHERE post_id = ?''',
                (post_id,))
            return c.fetchone()
        except BaseException:
            print('Error at selectPostByPostId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def updatePostLastUpdateDate(self, post_id, updated_date):
        try:
            c = self.conn.cursor()
            post_id = int(post_id)
            c.execute(
                '''UPDATE fanbox_master_post SET updated_date = ?
                WHERE post_id = ?''',
                (updated_date, post_id))
            self.conn.commit()
        except BaseException:
            print('Error at updatePostLastUpdateDate():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def deleteFanboxPost(self, id, by):
        id = int(id)
        if by not in ["member_id", "post_id"]:
            return
        sql = f'''DELETE FROM fanbox_master_post WHERE {by} = ?'''

        try:
            c = self.conn.cursor()
            c.execute(sql, (id,))
            self.conn.commit()
        except BaseException:
            print('Error at deleteFanboxPost():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def blacklistImage(self, memberId, ImageId):
        try:
            c = self.conn.cursor()
            c.execute('''INSERT OR REPLACE INTO pixiv_master_image
                      VALUES(?, ?, '**BLACKLISTED**' ,'**BLACKLISTED**' , datetime('now'), datetime('now') )''',
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
            c.execute(
                '''SELECT * FROM pixiv_master_image WHERE member_id = ? ''', (member_id,))
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
            c.execute('''SELECT image_id FROM pixiv_master_image
                      WHERE image_id = ? AND save_name != 'N/A' AND member_id = ?''', (image_id, member_id))
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
            c.execute(
                '''SELECT %s FROM pixiv_master_image WHERE image_id = ? AND save_name != 'N/A' ''' % (cols,),
                (image_id,))
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
            c.execute(
                '''SELECT * FROM pixiv_manga_image WHERE image_id = ? AND page = ? ''', (imageId, page))
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
                      WHERE image_id = ?''', (title, filename, isManga, imageId))
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
            c.execute(
                '''DELETE FROM pixiv_master_image WHERE image_id = ?''', (imageId,))
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
        ''' check if file or converted file exists '''
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
                    print("Missing: {0} at {1}".format(row[0], row[1]))
                    self.deleteImage(row[0])
            self.conn.commit()
        except BaseException:
            print('Error at cleanUp():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def interactiveCleanUp(self):
        items = []
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
                    items.append(row)
                    print("Missing: {0} at \n{1}".format(row[0], row[1]))

            while len(items) != 0:
                # End scan
                print(items)
                regex = input(
                    "Please provide a search regex, use empty string to skip(Empty to stop now):").rstrip("\r")
                if regex == "":
                    break
                repl = input("Replace regex with what?").rstrip("\r")
                regex = re.compile(regex)

                # Replace any paths where replacement results in a correct path
                ll = []
                for row in items:
                    new_name = regex.sub(repl, row[1])
                    if self.cleanupFileExists(filename):
                        c.execute('''UPDATE pixiv_master_image
                            SET save_name = ?
                            WHERE id = ?''', (new_name, row[0]))
                    else:
                        ll.append(items)
                items = ll
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
        oldPath = input("Old Path to Replace = ").rstrip("\r")
        print("Replacing " + oldPath + " to " + self.rootDirectory)
        cont = input("continue[y/n]?").rstrip("\r") or 'n'
        if cont != "y":
            print("Aborted")
            return

        try:
            print("Start replace Root Path operation.")
            print("Updating images, this may take some times.")

            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_master_image
                         SET save_name = replace(save_name, ?, ?)
                         WHERE save_name like ?''', (oldPath, self.rootDirectory, oldPath + "%",))
            print("Updated image:", c.rowcount)

            print("Updating manga images, this may take some times.")

            c = self.conn.cursor()
            c.execute('''UPDATE pixiv_manga_image
                         SET save_name = replace(save_name, ?, ?)
                         WHERE save_name like ?''', (oldPath, self.rootDirectory, oldPath + "%",))
            print("Updated manga image:", c.rowcount)

            print("Done")

        except BaseException:
            print('Error at replaceRootPath():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    ##########################################
    # VI. Utilities                          #
    ##########################################

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
        print('f1. Export FANBOX post list')
        print('f2. Delete FANBOX download history by post_id')
        print('f3. Delete FANBOX download history by member_id')
        print('===============================================')
        print('c. Clean Up Database')
        print('i. Interactive Clean Up Database')
        print('p. Compact Database')
        print('r. Replace Root Path')
        print('x. Exit')
        selection = input('Select one?' ).rstrip("\r")
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
                    filename = input('Filename? ').rstrip("\r")
                    includeArtistToken = input(
                        'Include Artist Token[y/n]? ').rstrip("\r")
                    if includeArtistToken.lower() == 'y':
                        includeArtistToken = True
                    else:
                        includeArtistToken = False
                    self.exportList(filename, includeArtistToken)
                elif selection == '4':
                    filename = input('Filename? ').rstrip("\r")
                    self.exportDetailedList(filename)
                elif selection == '5':
                    date = input('Number of date? ').rstrip("\r")
                    rows = self.selectMembersByLastDownloadDate(date)
                    if rows is not None:
                        for row in rows:
                            print("{0}\t\t{1}\n".format(
                                row.memberId, row.path))
                    else:
                        print('Not Found!\n')
                elif selection == '6':
                    image_id = input('image_id? ').rstrip("\r")
                    row = self.selectImageByImageId(image_id)
                    if row is not None:
                        for string in row:
                            print('	', end=' ')
                            print(string)
                        print('\n')
                    else:
                        print('Not Found!\n')
                elif selection == '7':
                    member_id = input('member_id? ').rstrip("\r")
                    row = self.selectMemberByMemberId(member_id)
                    if row is not None:
                        for string in row:
                            print('	', end=' ')
                            print(string)
                        print('\n')
                    else:
                        print('Not Found!\n')
                elif selection == '8':
                    member_id = input('member_id? ').rstrip("\r")
                    rows = self.selectImageByMemberId(member_id)
                    if rows is not None:
                        for row in rows:
                            for string in row:
                                print('	', end=' ')
                                print(string)
                            print('\n')
                    else:
                        print('Not Found!\n')
                elif selection == '9':
                    member_id = input('member_id? ').rstrip("\r")
                    self.deleteMemberByMemberId(member_id)
                elif selection == '10':
                    image_id = input('image_id? ').rstrip("\r")
                    self.deleteImage(image_id)
                elif selection == '11':
                    member_id = input('member_id? ').rstrip("\r")
                    self.deleteCascadeMemberByMemberId(member_id)
                elif selection == '12':
                    member_id = input('member_id? ').rstrip("\r")
                    image_id = input('image_id? ').rstrip("\r")
                    self.blacklistImage(member_id, image_id)
                elif selection == '13':
                    self.printMemberList(isDeleted=True)
                elif selection == 'f1':
                    filename = input('Filename? ').rstrip("\r")
                    self.exportFanboxPostList(filename)
                elif selection == 'f2':
                    member_id = input('member_id? ').rstrip("\r")
                    self.deleteFanboxPost(member_id, "post_id")
                elif selection == 'f3':
                    post_id = input('post_id? ').rstrip("\r")
                    self.deleteFanboxPost(post_id, "member_id")
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
