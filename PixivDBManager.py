#!C:/Python37-32/python
# -*- coding: utf-8 -*-

import codecs
import os
import re
import sqlite3
import sys
from datetime import datetime

# import colorama
from colorama import Back, Fore, Style

import common.PixivHelper as PixivHelper
from model.PixivListItem import PixivListItem

from common.PixivException import PixivException

script_path = PixivHelper.module_path()


class PixivDBManager(object):
    """Pixiv Database Manager"""

    rootDirectory = "."

    def __init__(self, root_directory, target="", timeout=5 * 60):
        if target is None or len(target) == 0:
            target = script_path + os.sep + "db.sqlite"
            PixivHelper.print_and_log("info", "Using default DB Path: " + target)
        else:
            # allow folder-specific DB path; keep behavior unchanged otherwise
            PixivHelper.print_and_log("info", "Using custom DB Path: " + target)
        self.rootDirectory = root_directory

        # ensure directory for DB exists
        try:
            db_dir = os.path.dirname(os.path.abspath(target))
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        except Exception:
            pass
        self.conn = sqlite3.connect(target, timeout)

    def close(self):
        self.conn.close()

    ##########################################
    # I. Create/Drop Database                #
    ##########################################
    def createDatabase(self):
        print("Creating database...", end=" ")

        try:
            c = self.conn.cursor()

            c.execute("""CREATE TABLE IF NOT EXISTS pixiv_master_member (
                            member_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
                            name TEXT,
                            save_folder TEXT,
                            created_date DATE,
                            last_update_date DATE,
                            last_image INTEGER
                            )""")

            self.conn.commit()

            # add column isDeleted
            # 0 = false, 1 = true
            try:
                c.execute(
                    """ALTER TABLE pixiv_master_member ADD COLUMN is_deleted INTEGER DEFAULT 0"""
                )
                self.conn.commit()
            except BaseException:
                pass

            # add column for artist token
            try:
                c.execute(
                    """ALTER TABLE pixiv_master_member ADD COLUMN member_token TEXT"""
                )
                self.conn.commit()
            except BaseException:
                pass

            # add column for total images (full works count on Pixiv)
            try:
                c.execute(
                    """ALTER TABLE pixiv_master_member ADD COLUMN total_images INTEGER"""
                )
                self.conn.commit()
            except BaseException:
                pass

            c.execute("""CREATE TABLE IF NOT EXISTS pixiv_master_image (
                            image_id INTEGER PRIMARY KEY,
                            member_id INTEGER,
                            title TEXT,
                            save_name TEXT,
                            created_date DATE,
                            last_update_date DATE
                            )""")
            # add column isManga
            try:
                c.execute("""ALTER TABLE pixiv_master_image ADD COLUMN is_manga TEXT""")
            except BaseException:
                pass
            # add column caption
            try:
                c.execute("""ALTER TABLE pixiv_master_image ADD COLUMN caption TEXT""")
            except BaseException:
                pass

            c.execute("""CREATE TABLE IF NOT EXISTS pixiv_manga_image (
                            image_id INTEGER,
                            page INTEGER,
                            save_name TEXT,
                            created_date DATE,
                            last_update_date DATE,
                            PRIMARY KEY (image_id, page)
                            )""")
            self.conn.commit()

            # Pixiv Tags
            c.execute("""CREATE TABLE IF NOT EXISTS pixiv_master_tag (
                            tag_id VARCHAR(255) PRIMARY KEY,
                            created_date DATE,
                            last_update_date DATE
                            )""")

            c.execute("""CREATE TABLE IF NOT EXISTS pixiv_tag_translation (
                            tag_id VARCHAR(255) REFERENCES pixiv_master_tag(tag_id),
                            translation_type VARCHAR(255),
                            translation VARCHAR(255),
                            created_date DATE,
                            last_update_date DATE,
                            PRIMARY KEY (tag_id, translation_type)
                            )""")

            c.execute("""CREATE TABLE IF NOT EXISTS pixiv_image_to_tag (
                            image_id INTEGER REFERENCES pixiv_master_image(image_id),
                            tag_id VARCHAR(255) REFERENCES pixiv_master_tag(tag_id),
                            created_date DATE,
                            last_update_date DATE,
                            PRIMARY KEY (image_id, tag_id)
                            )""")
            
            # image ID is primary key, may not reference to pixiv_master_image as it may not
            # be downloaded. Used for filtering out AI images.
            c.execute("""CREATE TABLE IF NOT EXISTS pixiv_ai_info (
                            image_id INTEGER PRIMARY KEY,
                            ai_type INTEGER,
                            created_date DATE,
                            last_update_date DATE
            )""")

            self.conn.commit()

            # Pixiv Series
            c.execute("""CREATE TABLE IF NOT EXISTS pixiv_master_series (
                            series_id VARCHAR(255) PRIMARY KEY,
                            series_title VARCHAR(255),
                            series_type VARCHAR(255),
                            series_description TEXT,
                            created_date DATE,
                            last_update_date DATE
                            )""")

            c.execute("""CREATE TABLE IF NOT EXISTS pixiv_image_to_series (
                            series_id VARCHAR(255) REFERENCES pixiv_master_series(series_id),
                            series_order INTEGER,
                            image_id INTEGER REFERENCES pixiv_master_image(image_id),
                            created_date DATE,
                            last_update_date DATE,
                            PRIMARY KEY (series_id, series_order),
                            UNIQUE (image_id)
                            )""")

            # FANBOX
            c.execute("""CREATE TABLE IF NOT EXISTS fanbox_master_post (
                            member_id INTEGER,
                            post_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
                            title TEXT,
                            fee_required INTEGER,
                            published_date DATE,
                            updated_date DATE,
                            post_type TEXT,
                            last_update_date DATE
                            )""")

            c.execute("""CREATE TABLE IF NOT EXISTS fanbox_post_image (
                            post_id INTEGER,
                            page INTEGER,
                            save_name TEXT,
                            created_date DATE,
                            last_update_date DATE,
                            PRIMARY KEY (post_id, page)
                            )""")
            self.conn.commit()

            # Sketch
            c.execute("""CREATE TABLE IF NOT EXISTS sketch_master_post (
                            member_id INTEGER,
                            post_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
                            title TEXT,
                            published_date DATE,
                            updated_date DATE,
                            post_type TEXT,
                            last_update_date DATE
                            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS sketch_post_image (
                            post_id INTEGER,
                            page INTEGER,
                            save_name TEXT,
                            created_date DATE,
                            last_update_date DATE,
                            PRIMARY KEY (post_id, page)
                            )""")

            # Novel
            self.create_update_novel_table(c)
            self.conn.commit()

            print("done.")
        except BaseException:
            print("Error at createDatabase():", str(sys.exc_info()))
            print("failed.")
            raise
        finally:
            c.close()

    def dropDatabase(self):
        try:
            c = self.conn.cursor()

            c.execute("""DROP TABLE IF EXISTS pixiv_image_to_tag""")
            c.execute("""DROP TABLE IF EXISTS pixiv_tag_translation""")
            c.execute("""DROP TABLE IF EXISTS pixiv_master_tag""")
            self.conn.commit()

            c.execute("""DROP TABLE IF EXISTS pixiv_master_member""")
            self.conn.commit()

            c.execute("""DROP TABLE IF EXISTS pixiv_master_image""")
            self.conn.commit()

            c.execute("""DROP TABLE IF EXISTS pixiv_manga_image""")
            self.conn.commit()

            c.execute("""DROP TABLE IF EXISTS fanbox_master_post""")
            c.execute("""DROP TABLE IF EXISTS fanbox_post_image""")
            self.conn.commit()

            c.execute("""DROP TABLE IF EXISTS sketch_master_post""")
            c.execute("""DROP TABLE IF EXISTS sketch_post_image""")
            self.conn.commit()

        except BaseException:
            print("Error at dropDatabase():", str(sys.exc_info()))
            print("failed.")
            raise
        finally:
            c.close()
        print("done.")

    def compactDatabase(self):
        print("Compacting Database, this might take a while...")
        try:
            c = self.conn.cursor()
            c.execute("""VACUUM""")
            self.conn.commit()
        except BaseException:
            print("Error at compactDatabase():", str(sys.exc_info()))
            raise
        finally:
            c.close()
        print("done.")

    ##########################################
    # II. Export/Import DB                  #
    ##########################################
    def importList(self, listTxt):
        print("Importing list...", end=" ")
        print("Found", len(listTxt), "items", end=" ")
        try:
            c = self.conn.cursor()

            for item in listTxt:
                c.execute(
                    """INSERT OR IGNORE INTO pixiv_master_member VALUES(?, ?, ?, datetime('now'), '1-1-1', -1, 0, '')""",
                    (item.memberId, str(item.memberId), r"N\A"),
                )
                c.execute(
                    """UPDATE pixiv_master_member
                             SET save_folder = ?
                             WHERE member_id = ? """,
                    (item.path, item.memberId),
                )
            self.conn.commit()
        except BaseException:
            print("Error at importList():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()
        print("done.")
        return 0

    def exportImageTable(self, name):
        print(f"Exporting {name} table ...", end=" ")
        im_list = list()
        if name == "Pixiv":
            table = "pixiv_master_image"
            key = "image_id"
        elif name == "Fanbox":
            table = "fanbox_master_post"
            key = "post_id"
        elif name == "Sketch":
            table = "sketch_master_post"
            key = "post_id"
        else:
            raise
        try:
            c = self.conn.cursor()
            c.execute(f""" SELECT COUNT(*) FROM {table}""")
            result = c.fetchall()
            if result[0][0] > 10000:
                print(
                    "Row count is more than 10000 (actual row count:",
                    str(result[0][0]),
                    ")",
                )
                print("It may take a while to retrieve the data.")
                arg = input("Continue [y/n, default is yes]").rstrip("\r") or "y"
                answer = arg.lower()
                if answer not in ("y", "n", "o"):
                    PixivHelper.print_and_log(
                        "error",
                        f"Invalid args for TODO: {arg}, valid values are [y/n/o].",
                    )
                    return
                if answer == "y":
                    c = self.conn.cursor()
                    c.execute(f"""SELECT {key}
                                FROM {table}
                                ORDER BY member_id""")
                    for row in c:
                        im_list.append(row[0])
            else:
                c.execute(f"""SELECT {key}
                            FROM {table}
                            ORDER BY member_id""")
                for row in c:
                    im_list.append(row[0])
            c.close()
            print("done.")
            return im_list
        except BaseException:
            print("Error at exportImageTable():", str(sys.exc_info()))
            print("failed")
            raise

    def exportList(self, filename, include_artist_token=True):
        print("Exporting list...", end=" ")
        try:
            c = self.conn.cursor()
            c.execute("""SELECT member_id, save_folder, name, member_token
                         FROM pixiv_master_member
                         WHERE is_deleted = 0
                         ORDER BY member_id""")
            if not filename.endswith(".txt"):
                filename = filename + ".txt"

            writer = codecs.open(filename, "wb", encoding="utf-8")
            writer.write("###Export date: {0} ###\r\n".format(datetime.today()))
            for row in c:
                if include_artist_token:
                    data = row[2]
                    token = row[3]
                    writer.write(f"# name: {data},token: {token}")
                    writer.write("\r\n")
                writer.write(str(row[0]))
                if len(row[1]) > 0:
                    writer.write(" " + str(row[1]))
                writer.write("\r\n")
            writer.write("###END-OF-FILE###")
        except BaseException:
            print("Error at exportList():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            if writer is not None:
                writer.close()
            c.close()
        print("done.")

    def exportDetailedList(self, filename):
        print("Exporting detailed list...", end=" ")
        try:
            c = self.conn.cursor()
            c.execute("""SELECT * FROM pixiv_master_member
                            WHERE is_deleted = 0
                            ORDER BY member_id""")
            filename = filename + ".csv"
            writer = codecs.open(filename, "wb", encoding="utf-8")
            writer.write(
                "member_id,name,save_folder,created_date,last_update_date,last_image,is_deleted,member_token\r\n"
            )
            for row in c:
                for string in row:
                    # Unicode write!!
                    data = string
                    writer.write(data)
                    writer.write(",")
                writer.write("\r\n")
            writer.write("###END-OF-FILE###")
            writer.close()
        except BaseException:
            print("Error at exportDetailedList(): " + str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()
        print("done.")

    def exportFanboxPostList(self, filename, sep=","):
        print("Exporting FANBOX post list...", end=" ")
        try:
            c = self.conn.cursor()
            c.execute("""SELECT * FROM fanbox_master_post
                            ORDER BY member_id, post_id""")
            filename = filename + ".csv"
            writer = codecs.open(filename, "wb", encoding="utf-8")
            columns = [
                "member_id",
                "post_id",
                "title",
                "fee_required",
                "published_date",
                "update_date",
                "post_type",
                "last_update_date",
            ]
            writer.write(sep.join(columns))
            writer.write("\r\n")
            for row in c:
                writer.write(sep.join([str(x) for x in row]))
                writer.write("\r\n")
            writer.write("###END-OF-FILE###")
            writer.close()
        except BaseException:
            print("Error at exportFanboxPostList(): " + str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()
        print("done.")

    ##########################################
    # III. Print DB                          #
    ##########################################
    def printMemberList(self, isDeleted=False):
        print("Printing member list:")
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT * FROM pixiv_master_member
                         WHERE is_deleted = ? ORDER BY member_id""",
                (int(isDeleted),),
            )
            print(
                "%10s %25s %25s %20s %20s %10s %s %s"
                % (
                    "member_id",
                    "name",
                    "save_folder",
                    "created_date",
                    "last_update_date",
                    "last_image",
                    "is_deleted",
                    "member_token",
                )
            )
            i = 0
            for row in c:
                print(
                    "%10d %#25s %#25s %20s %20s %10d %5s"
                    % (row[0], row[1].strip(), row[2], row[3], row[4], row[5], row[6])
                )
                i = i + 1
                if i == 79:
                    select = input("Continue [y/n, default is yes]? ").rstrip("\r")
                    if select == "n":
                        break
                    else:
                        print(
                            "member_id\tname\tsave_folder\tcreated_date\tlast_update_date\tlast_image"
                        )
                        i = 0
        except BaseException:
            print("Error at printMemberList():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()
        print("done.")

    def printImageList(self):
        print("Printing image list:")
        try:
            c = self.conn.cursor()
            c.execute(""" SELECT COUNT(*) FROM pixiv_master_image""")
            result = c.fetchall()
            if result[0][0] > 10000:
                print(
                    "Row count is more than 10000 (actual row count:",
                    str(result[0][0]),
                    ")",
                )
                print("It may take a while to retrieve the data.")
                answer = input("Continue [y/n, default is no]").rstrip("\r")
                if answer == "y":
                    c.execute("""SELECT * FROM pixiv_master_image
                                    ORDER BY member_id""")
                    print("")
                    for row in c:
                        for string in row:
                            print("   ", end=" ")
                            print(string)
                        print("")
                else:
                    return
            # Yavos: it seems you forgot something ;P
            else:
                c.execute("""SELECT * FROM pixiv_master_image ORDER BY member_id""")
                print("")
                for row in c:
                    for string in row:
                        print("   ", end=" ")
                        print(string)
                    print("")
            # Yavos: end of change
        except BaseException:
            print("Error at printImageList():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()
        print("done.")

    ##########################################
    # IV. CRUD Member Table                  #
    ##########################################
    def insertNewMember(self, member_id=0, member_token=None):
        try:
            c = self.conn.cursor()
            if member_id == 0:
                while True:
                    temp = input("Member ID: ").rstrip("\r")
                    try:
                        member_id = int(temp)
                    except BaseException:
                        pass
                    if member_id > 0:
                        break

            c.execute(
                """INSERT OR IGNORE INTO pixiv_master_member VALUES(?, ?, ?, datetime('now'), '1-1-1', -1, 0, ?)""",
                (member_id, str(member_id), r"N\A", member_token),
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertNewMember():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectAllMember(self, isDeleted=False):
        members = list()
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT member_id, save_folder FROM pixiv_master_member WHERE is_deleted = ? ORDER BY member_id""",
                (int(isDeleted),),
            )
            result = c.fetchall()

            for row in result:
                item = PixivListItem(row[0], row[1])
                members.append(item)

        except BaseException:
            print("Error at selectAllMember():", str(sys.exc_info()))
            print("failed")
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

            c.execute(
                """SELECT member_id, save_folder,  (julianday(Date('now')) - julianday(last_update_date)) as diff
                         FROM pixiv_master_member
                         WHERE is_deleted <> 1 AND ( last_update_date == '1-1-1' OR diff > ? ) ORDER BY member_id""",
                (int_diff,),
            )
            result = c.fetchall()
            for row in result:
                item = PixivListItem(row[0], row[1])
                members.append(item)

        except BaseException:
            print("Error at selectMembersByLastDownloadDate():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

        return members

    def selectMemberByMemberId(self, member_id):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT * FROM pixiv_master_member WHERE member_id = ? """,
                (member_id,),
            )
            return c.fetchone()
        except BaseException:
            print("Error at selectMemberByMemberId():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectMemberByMemberId2(self, member_id):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT member_id, save_folder FROM pixiv_master_member WHERE member_id = ? """,
                (member_id,),
            )
            row = c.fetchone()
            if row is not None:
                return PixivListItem(row[0], row[1])
            else:
                return PixivListItem(int(member_id), "")
        except BaseException:
            print("Error at selectMemberByMemberId2():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def printMembersByLastDownloadDate(self, difference):
        rows = self.selectMembersByLastDownloadDate(difference)

        for row in rows:
            for string in row:
                print("   ", end=" ")
                print(string)
            print("\n")

    def updateMemberName(self, memberId, memberName, member_token):
        try:
            c = self.conn.cursor()
            c.execute(
                """UPDATE pixiv_master_member
                            SET name = ?, member_token = ?
                            WHERE member_id = ?
                            """,
                (memberName, member_token, memberId),
            )
            self.conn.commit()
        except BaseException:
            print("Error at updateMemberName():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def updateSaveFolder(self, memberId, saveFolder):
        try:
            c = self.conn.cursor()
            c.execute(
                """UPDATE pixiv_master_member
                            SET save_folder = ?
                            WHERE member_id = ?
                            """,
                (saveFolder, memberId),
            )
            self.conn.commit()
        except BaseException:
            print("Error at updateSaveFolder():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def updateLastDownloadedImage(self, memberId, imageId):
        try:
            c = self.conn.cursor()
            c.execute(
                """UPDATE pixiv_master_member
                         SET last_image = ?, last_update_date = datetime('now')
                         WHERE member_id = ?""",
                (imageId, memberId),
            )
            self.conn.commit()
        except BaseException:
            print("Error at updateLastDownloadedImage:", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def updateLastDownloadDate(self, memberId):
        try:
            c = self.conn.cursor()
            c.execute(
                """UPDATE pixiv_master_member
                         SET last_update_date = datetime('now')
                         WHERE member_id = ?""",
                (memberId,),
            )
            self.conn.commit()
        except BaseException:
            print("Error at updateLastDownloadDate():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def updateMemberTotalImages(self, memberId, totalImages):
        """Persist full Pixiv works count for a member.

        totalImages can be None to skip.
        """
        try:
            if totalImages is None:
                return
            c = self.conn.cursor()
            c.execute(
                """UPDATE pixiv_master_member
                   SET total_images = ?,
                       last_update_date = datetime('now')
                   WHERE member_id = ?""",
                (int(totalImages), int(memberId)),
            )
            # If row did not exist, ensure member inserted
            if c.rowcount == 0:
                c.execute(
                    """INSERT OR IGNORE INTO pixiv_master_member (member_id, save_folder, name, created_date, last_update_date, last_image, is_deleted, member_token, total_images)
                        VALUES(?, ?, ?, datetime('now'), datetime('now'), -1, 0, '', ?)""",
                    (int(memberId), str(memberId), str(memberId), int(totalImages)),
                )
            self.conn.commit()
        except BaseException:
            PixivHelper.print_and_log('warn', f"Error at updateMemberTotalImages(): {sys.exc_info()}")

    def selectMemberTotalImagesMap(self, member_ids=None):
        """Return {member_id(str): total_images(int)} for members with total_images not null.

        If member_ids is provided, filter to those ids.
        """
        try:
            c = self.conn.cursor()
            if member_ids:
                ids = [int(x) for x in member_ids]
                placeholders = ",".join(["?"] * len(ids))
                rows = c.execute(
                    f"""SELECT member_id, total_images
                        FROM pixiv_master_member
                        WHERE total_images IS NOT NULL
                          AND member_id IN ({placeholders})""",
                    ids,
                ).fetchall()
            else:
                rows = c.execute(
                    """SELECT member_id, total_images
                        FROM pixiv_master_member
                        WHERE total_images IS NOT NULL"""
                ).fetchall()

            return {int(r[0]): int(r[1]) for r in rows if r[1] is not None}
        except BaseException:
            PixivHelper.print_and_log('warn', f"Error at selectMemberTotalImagesMap(): {sys.exc_info()}")
            return {}
    ##########################################
    # V. CRUD Image Table                    #
    ##########################################

    def insertSeries(self, series_id, series_title, series_type, series_desc=None):
        try:
            c = self.conn.cursor()
            c.execute(
                """INSERT OR IGNORE INTO pixiv_master_series VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))""",
                (
                    series_id,
                    series_title,
                    series_type,
                    series_desc,
                ),
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertSeries():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def insertImageToSeries(self, image_id, series_id, series_order):
        try:
            c = self.conn.cursor()
            image_id = int(image_id)
            series_order = int(series_order)
            c.execute(
                """INSERT INTO pixiv_image_to_series(series_id, series_order, image_id, created_date, last_update_date)
                        VALUES (?, ?, ?, datetime('now'), datetime('now'))
                        ON CONFLICT(image_id) DO UPDATE
                        SET series_id = excluded.series_id,
                            series_order = excluded.series_order,
                            last_update_date = datetime('now')""",
                (series_id, series_order, image_id),
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertImageToSeries():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def insertTag(self, tag_id):
        try:
            c = self.conn.cursor()
            c.execute(
                """INSERT OR IGNORE INTO pixiv_master_tag VALUES (?, datetime('now'), datetime('now'))""",
                (tag_id,),
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertTag():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def insertImageToTag(self, image_id, tag_id):
        try:
            c = self.conn.cursor()
            image_id = int(image_id)
            c.execute(
                """INSERT OR IGNORE INTO pixiv_image_to_tag(image_id, tag_id, created_date, last_update_date)
                                  VALUES (?, ?, datetime('now'), datetime('now'))
                              ON CONFLICT(image_id, tag_id) DO UPDATE
                              SET last_update_date = datetime('now')""",
                (image_id, tag_id),
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertImageToTag():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def insertTagTranslation(self, tag_id, translation_type, translation):
        try:
            c = self.conn.cursor()
            c.execute(
                """INSERT OR IGNORE INTO pixiv_tag_translation(tag_id, translation_type, translation, created_date, last_update_date)
                                  VALUES (?, ?, ?, datetime('now'), datetime('now'))
                      ON CONFLICT(tag_id, translation_type) DO UPDATE
                      SET translation = excluded.translation,
                          last_update_date = datetime('now')""",
                (tag_id, translation_type, translation),
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertImageToTag():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectImagesByTagId(self, tag_id):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT pixiv_master_image.*
                     FROM pixiv_master_image
                     JOIN pixiv_image_to_tag ON pixiv_master_image.image_id = pixiv_image_to_tag.image_id
                    WHERE pixiv_image_to_tag.tag_id = ?
                """,
                (tag_id,),
            )
            return c.fetchall()
        except BaseException:
            print("Error at selectImagesByTagId():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectTagsByImageId(self, image_id):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT pixiv_master_tag.*
                    FROM pixiv_master_tag
                    JOIN pixiv_image_to_tag ON pixiv_image_to_tag.tag_id = pixiv_master_tag.tag_id
                   WHERE pixiv_image_to_tag.image_id = ?
                """,
                (image_id,),
            )
            return c.fetchall()
        except BaseException:
            print("Error at selectTagsByImageId():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def deleteImagesByTag(self, tag_id):
        try:
            c = self.conn.cursor()
            c.execute(
                """DELETE FROM pixiv_master_image
                      WHERE image_id IN (SELECT image_id FROM pixiv_image_to_tag WHERE tag_id = ?)""",
                (tag_id,),
            )
            c.execute(
                """DELETE FROM pixiv_manga_image
                      WHERE image_id IN (SELECT image_id FROM pixiv_image_to_tag WHERE tag_id = ?)""",
                (tag_id,),
            )
            c.execute("""DELETE FROM pixiv_image_to_tag WHERE tag_id = ?""", (tag_id,))
            self.conn.commit()
        except BaseException:
            print("Error at deleteImage():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def insertImage(self, member_id, image_id, isManga="", caption=""):
        try:
            c = self.conn.cursor()
            member_id = int(member_id)
            image_id = int(image_id)
            c.execute(
                """INSERT OR IGNORE INTO pixiv_master_image VALUES(?, ?, 'N/A' ,'N/A' , datetime('now'), datetime('now'), ?, ? )""",
                (image_id, member_id, isManga, caption),
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertImage():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def insertMangaImages(self, manga_files):
        try:
            c = self.conn.cursor()
            c.executemany(
                """INSERT OR IGNORE INTO pixiv_manga_image
                          VALUES(?, ?, ?, datetime('now'), datetime('now'))""",
                manga_files,
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertMangaImages():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def upsertMangaImage(self, manga_files):
        try:
            c = self.conn.cursor()
            c.executemany(
                """INSERT INTO pixiv_manga_image
                          VALUES(?, ?, ?, datetime('now'), datetime('now'))
                          ON CONFLICT(image_id, page) DO UPDATE SET
                          save_name = excluded.save_name,
                          last_update_date = datetime('now')""",
                manga_files,
            )
            self.conn.commit()
        except BaseException:
            print("Error at upsertMangaImage():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def blacklistImage(self, memberId, ImageId):
        try:
            c = self.conn.cursor()
            c.execute(
                """INSERT OR REPLACE INTO pixiv_master_image
                      VALUES(?, ?, '**BLACKLISTED**' ,'**BLACKLISTED**' , datetime('now'), datetime('now') )""",
                (ImageId, memberId),
            )
            self.conn.commit()
        except BaseException:
            print("Error at blacklistImage():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectImageByMemberId(self, member_id):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT * FROM pixiv_master_image WHERE member_id = ? """,
                (member_id,),
            )
            return c.fetchall()
        except BaseException:
            print("Error at selectImageByMemberId():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectImageByMemberIdAndImageId(self, member_id, image_id):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT image_id FROM pixiv_master_image
                      WHERE image_id = ? AND save_name != 'N/A' AND member_id = ?""",
                (image_id, member_id),
            )
            return c.fetchone()
        except BaseException:
            print("Error at selectImageByMemberIdAndImageId():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectImageByImageId(self, image_id, cols="*"):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT %s FROM pixiv_master_image WHERE image_id = ? AND save_name != 'N/A' """
                % (cols,),
                (image_id,),
            )
            return c.fetchone()
        except BaseException:
            print("Error at selectImageByImageId():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectImagesByImageId(self, image_id):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT * FROM pixiv_manga_image WHERE image_id = ? ORDER BY page ASC""",
                (image_id,),
            )
            return c.fetchall()
        except BaseException:
            print("Error at selectImagesByImageId():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectImageByImageIdAndPage(self, imageId, page):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT * FROM pixiv_manga_image WHERE image_id = ? AND page = ? """,
                (imageId, page),
            )
            return c.fetchone()
        except BaseException:
            print("Error at selectImageByImageIdAndPage():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def updateImage(self, imageId, title, filename, isManga=None, caption=None):
        try:
            c = self.conn.cursor()
            c.execute(
                """UPDATE pixiv_master_image
                      SET title = ?, save_name = ?, last_update_date = datetime('now'), is_manga = COALESCE(?, is_manga), caption = COALESCE(?, caption)
                      WHERE image_id = ?""",
                (title, filename, isManga, caption, imageId),
            )
            self.conn.commit()
        except BaseException:
            print("Error at updateImage():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def deleteImage(self, imageId):
        try:
            c = self.conn.cursor()
            c.execute(
                """DELETE FROM pixiv_master_image WHERE image_id = ?""", (imageId,)
            )
            c.execute(
                """DELETE FROM pixiv_manga_image WHERE image_id = ?""", (imageId,)
            )
            c.execute(
                """DELETE FROM pixiv_image_to_tag WHERE image_id = ?""", (imageId,)
            )
            self.conn.commit()
        except BaseException:
            print("Error at deleteImage():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def deleteSketch(self, postId):
        try:
            c = self.conn.cursor()
            c.execute("""DELETE FROM sketch_master_post WHERE post_id = ?""", (postId,))
            c.execute("""DELETE FROM sketch_post_image WHERE post_id = ?""", (postId,))
            self.conn.commit()
        except BaseException:
            print("Error at deleteSketch():", str(sys.exc_info()))
            print("failed")
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
        """check if file or converted file exists"""
        anim_ext = [".zip", ".gif", ".apng", ".ugoira", ".webm"]
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

    def insertAiInfo(self, image_id, ai_type):
        try:
            c = self.conn.cursor()
            image_id = int(image_id)
            ai_type = int(ai_type)
            c.execute('''INSERT OR IGNORE INTO pixiv_ai_info (image_id, ai_type, created_date, last_update_date) 
                      VALUES (?, ?, datetime('now'), datetime('now'))
                      ON CONFLICT(image_id) DO UPDATE SET 
                      ai_type = excluded.ai_type,
                      last_update_date = datetime('now')''',
                      (image_id, ai_type))
            self.conn.commit()
        except BaseException:
            print('Error at insertAiInfo():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()
    
    def selectAiTypeByImageId(self, image_id):
        try:
            c = self.conn.cursor()
            image_id = int(image_id)
            c.execute('''SELECT ai_type FROM pixiv_ai_info WHERE image_id = ?''', (image_id,))
            result = c.fetchone()
            return result[0] if result is not None else None
        except BaseException:
            print('Error at selectAiTypeByImageId():', str(sys.exc_info()))
            print('failed')
            raise
        finally:
            c.close()

    def cleanUp(self):
        anim_ext = [".zip", ".gif", ".apng", ".ugoira", ".webm"]
        try:
            print("Start clean-up operation.")
            print("Selecting all images, this may take some times.")
            c = self.conn.cursor()
            c.execute("""SELECT image_id, save_name from pixiv_master_image""")
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
            print("Error at cleanUp():", str(sys.exc_info()))
            print("failed")
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
            c.execute("""SELECT image_id, save_name from pixiv_master_image""")
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
                    "Please provide a search regex, use empty string to skip(Empty to stop now):"
                ).rstrip("\r")
                if regex == "":
                    break
                repl = input("Replace regex with what?").rstrip("\r")
                regex = re.compile(regex)

                # Replace any paths where replacement results in a correct path
                ll = []
                for row in items:
                    new_name = regex.sub(repl, row[1])
                    if self.cleanupFileExists(filename):
                        c.execute(
                            """UPDATE pixiv_master_image
                            SET save_name = ?
                            WHERE id = ?""",
                            (new_name, row[0]),
                        )
                    else:
                        ll.append(items)
                items = ll
            c.close()
            self.conn.commit()
        except BaseException:
            print("Error at interactiveCleanUp():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

        # TODO check mangaimage
        # TODO check for files which exist but don't have a DB entry

    def replaceRootPath(self):
        oldPath = input("Old Path to Replace = ").rstrip(" \\\r\n")
        print("Replacing " + oldPath + " to " + self.rootDirectory)
        cont = input("continue[y/n, default is no]?").rstrip("\r") or "n"
        if cont != "y":
            print("Aborted")
            return

        try:
            print("Start replace Root Path operation.")
            print("Updating images, this may take some times.")

            c = self.conn.cursor()
            c.execute(
                """UPDATE pixiv_master_image
                         SET save_name = replace(save_name, ?, ?)
                         WHERE save_name like ?""",
                (
                    oldPath,
                    self.rootDirectory,
                    oldPath + "%",
                ),
            )
            print("Updated image:", c.rowcount)

            print("Updating manga images, this may take some times.")

            c = self.conn.cursor()
            c.execute(
                """UPDATE pixiv_manga_image
                         SET save_name = replace(save_name, ?, ?)
                         WHERE save_name like ?""",
                (
                    oldPath,
                    self.rootDirectory,
                    oldPath + "%",
                ),
            )
            print("Updated manga image:", c.rowcount)

            print("Updating PIXIV novel details, this may take some times.")

            c = self.conn.cursor()
            c.execute(
                """UPDATE novel_detail
                         SET save_name = replace(save_name, ?, ?)
                         WHERE save_name like ?""",
                (
                    oldPath,
                    self.rootDirectory,
                    oldPath + "%",
                ),
            )
            print("Updated novel detail:", c.rowcount)

            print("Updating SKETCH images, this may take some times.")

            c = self.conn.cursor()
            c.execute(
                """UPDATE sketch_post_image
                         SET save_name = replace(save_name, ?, ?)
                         WHERE save_name like ?""",
                (
                    oldPath,
                    self.rootDirectory,
                    oldPath + "%",
                ),
            )
            print("Updated sketch image:", c.rowcount)

            print("Updating FANBOX post images, this may take some times.")

            c = self.conn.cursor()
            c.execute(
                """UPDATE fanbox_post_image
                         SET save_name = replace(save_name, ?, ?)
                         WHERE save_name like ?""",
                (
                    oldPath,
                    self.rootDirectory,
                    oldPath + "%",
                ),
            )
            print("Updated FANBOX post image:", c.rowcount)

            print("Done")

        except BaseException:
            print("Error at replaceRootPath():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    ##########################################
    # VI. CRUD FANBOX post/image table       #
    ##########################################

    def insertPost(
        self, member_id, post_id, title, fee_required, published_date, post_type
    ):
        try:
            c = self.conn.cursor()
            post_id = int(post_id)
            c.execute(
                """INSERT OR IGNORE INTO fanbox_master_post (member_id, post_id) VALUES(?, ?)""",
                (member_id, post_id),
            )
            c.execute(
                """UPDATE fanbox_master_post SET title = ?, fee_required = ?, published_date = ?,
                post_type = ?, last_update_date = datetime('now') WHERE post_id = ?""",
                (title, fee_required, published_date, post_type, post_id),
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertPost():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def insertPostImages(self, post_files):
        try:
            c = self.conn.cursor()
            c.executemany(
                """INSERT OR REPLACE INTO fanbox_post_image
                          VALUES(?, ?, ?, datetime('now'), datetime('now'))""",
                post_files,
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertPostImages():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectPostByPostId(self, post_id):
        try:
            c = self.conn.cursor()
            post_id = int(post_id)
            c.execute(
                """SELECT * FROM fanbox_master_post WHERE post_id = ?""", (post_id,)
            )
            return c.fetchone()
        except BaseException:
            print("Error at selectPostByPostId():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def updatePostUpdateDate(self, post_id, updated_date):
        try:
            c = self.conn.cursor()
            post_id = int(post_id)
            c.execute(
                """UPDATE fanbox_master_post SET updated_date = ?
                WHERE post_id = ?""",
                (updated_date, post_id),
            )
            self.conn.commit()
        except BaseException:
            print("Error at updatePostUpdateDate():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectFanboxImageByImageIdAndPage(self, post_id, page):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT * FROM fanbox_post_image WHERE post_id = ? AND page = ? """,
                (post_id, page),
            )
            return c.fetchone()
        except BaseException:
            print("Error at selectFanboxImageByImageIdAndPage():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def deleteFanboxPost(self, post_id, by):
        post_id = int(post_id)
        if by not in ["member_id", "post_id"]:
            return

        try:
            c = self.conn.cursor()
            c.execute(
                f"""DELETE FROM fanbox_post_image WHERE post_id in
                          (SELECT post_id FROM fanbox_master_post WHERE {by} = ?)""",
                (post_id,),
            )
            c.execute(f"""DELETE FROM fanbox_master_post WHERE {by} = ?""", (post_id,))
            self.conn.commit()
        except BaseException:
            print("Error at deleteFanboxPost():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def cleanUpFanbox(self):
        print("Start FANBOX clean-up operation.")
        print("Selecting all FANBOX images, this may take some times.")
        items = []
        try:
            c = self.conn.cursor()
            c.execute("""SELECT post_id, page, save_name from fanbox_post_image""")
            print("Checking images.")
            for row in c:
                filename = row[2]

                if filename is not None and len(filename) > 0:
                    if os.path.exists(filename):
                        continue

                print("Missing: {0} at {1}".format(row[0], row[2]))
                items.append(row)

            for item in items:
                c.execute(
                    """DELETE FROM fanbox_post_image WHERE post_id = ? and page = ?""",
                    (item[0], item[1]),
                )
                c.execute(
                    """DELETE FROM fanbox_master_post WHERE post_id = ?""", (item[0],)
                )
            self.conn.commit()
        except BaseException:
            print("Error at cleanUpFanbox():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def interactiveCleanUpFanbox(self):
        items = []
        print("Start FANBOX clean-up operation.")
        print("Selecting all FANBOX images, this may take some times.")
        try:
            c = self.conn.cursor()
            print("Collecting missing images.")
            c.execute("""SELECT post_id, page, save_name from fanbox_post_image""")
            for row in c:
                # Issue 340
                filename = row[2]
                if filename is not None and len(filename) > 0:
                    if os.path.exists(filename):
                        continue
                items.append(row)
                print("Missing: {0} at \n{1}".format(row[0], row[2]))

            while len(items) != 0:
                # End scan
                print(items)
                regex = input(
                    "Please provide a search regex, use empty string to skip(Empty to stop now):"
                ).rstrip("\r")
                if regex == "":
                    break
                repl = input("Replace regex with what?").rstrip("\r")
                regex = re.compile(regex)

                # Replace any paths where replacement results in a correct path
                ll = []
                for row in items:
                    new_name = regex.sub(repl, row[2])
                    if new_name is not None and len(new_name) > 0:
                        if os.path.exists(new_name):
                            c.execute(
                                """UPDATE fanbox_post_image
                                SET save_name = ?
                                WHERE post_id = ? and page = ?""",
                                (new_name, row[0], row[1]),
                            )
                            continue
                    ll.append(items)
                items = ll
            c.close()
            self.conn.commit()
        except BaseException:
            print("Error at interactiveCleanUpFanbox():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    ##########################################
    # VII. CRUD Sketch post/image table      #
    ##########################################

    def insertSketchPost(self, post):
        try:
            c = self.conn.cursor()
            post_id = int(post.imageId)
            c.execute(
                """INSERT OR IGNORE INTO sketch_master_post (member_id, post_id) VALUES(?, ?)""",
                (post.artist.artistId, post_id),
            )
            c.execute(
                """UPDATE sketch_master_post
                            SET title = ?,
                                published_date = ?,
                                post_type = ?,
                                last_update_date = ?
                            WHERE post_id = ?""",
                (
                    post.imageTitle,
                    post.worksDateDateTime,
                    post.imageMode,
                    post.worksUpdateDateTime,
                    post_id,
                ),
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertSketchPost():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def insertSketchPostImages(
        self, post_id, page, save_name, created_date, last_update_date
    ):
        try:
            c = self.conn.cursor()
            c.execute(
                """INSERT OR REPLACE INTO sketch_post_image
                             VALUES(?, ?, ?, ?, ?)""",
                (post_id, page, save_name, created_date, last_update_date),
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertSketchPostImages():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectSketchImageByImageIdAndPage(self, post_id, page):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT * FROM sketch_post_image WHERE post_id = ? AND page = ? """,
                (post_id, page),
            )
            return c.fetchone()
        except BaseException:
            print("Error at selectSketchImageByImageIdAndPage():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectSketchPostByPostId(self, post_id):
        try:
            c = self.conn.cursor()
            post_id = int(post_id)
            c.execute(
                """SELECT * FROM sketch_master_post WHERE post_id = ?""", (post_id,)
            )
            return c.fetchone()
        except BaseException:
            print("Error at selectSketchPostByPostId():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def deleteSketchPost(self, post_id, by):
        post_id = int(post_id)
        if by not in ["member_id", "post_id"]:
            return

        try:
            c = self.conn.cursor()
            c.execute(
                f"""DELETE FROM sketch_post_image WHERE post_id in
                          (SELECT post_id FROM sketch_master_post WHERE {by} = ?)""",
                (post_id,),
            )
            c.execute(f"""DELETE FROM sketch_master_post WHERE {by} = ?""", (post_id,))
            self.conn.commit()
        except BaseException:
            print("Error at deleteSketchPost():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def cleanUpSketch(self):
        try:
            print("Start sketch clean-up operation.")
            print("Selecting all sketches, this may take some times.")
            c = self.conn.cursor()
            c.execute("""SELECT post_id, page, save_name from sketch_post_image""")
            print("Checking images.")
            for row in c:
                # Issue 340
                filename = row[2]
                fileExists = False

                if filename is not None and len(filename) > 0:
                    if os.path.exists(filename):
                        continue

                if not fileExists:
                    print("Missing: {0} at {1}".format(row[0], row[2]))
                    self.deleteSketch(row[0])
            self.conn.commit()
        except BaseException:
            print("Error at cleanUpSketch():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def interactiveSketchCleanUp(self):
        items = []
        try:
            print("Start sketch clean-up operation.")
            print("Selecting all sketches, this may take some times.")
            c = self.conn.cursor()
            print("Collecting missing images.")
            c.execute("""SELECT post_id, page, save_name from sketch_post_image""")
            for row in c:
                # Issue 340
                filename = row[2]
                fileExists = False

                if filename is not None and len(filename) > 0:
                    if os.path.exists(filename):
                        continue

                if not fileExists:
                    items.append(row)
                    print("Missing: {0} at \n{1}".format(row[0], row[2]))

            while len(items) != 0:
                # End scan
                print(items)
                regex = input(
                    "Please provide a search regex, use empty string to skip(Empty to stop now):"
                ).rstrip("\r")
                if regex == "":
                    break
                repl = input("Replace regex with what?").rstrip("\r")
                regex = re.compile(regex)

                # Replace any paths where replacement results in a correct path
                ll = []
                for row in items:
                    new_name = regex.sub(repl, row[2])
                    if new_name is not None and len(new_name) > 0:
                        if os.path.exists(new_name):
                            c.execute(
                                """UPDATE sketch_post_image
                                SET save_name = ?
                                WHERE post_id = ? and page = ?""",
                                (new_name, row[0], row[1]),
                            )
                            continue
                    ll.append(items)
                items = ll
            c.close()
            self.conn.commit()
        except BaseException:
            print("Error at interactiveSketchCleanUp():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    ##########################################
    # VIII. CRUD Novel table                 #
    ##########################################
    def create_update_novel_table(self, c):
        c.execute("""CREATE TABLE IF NOT EXISTS novel_detail (
                        post_id INTEGER,
                        user_id INTEGER,
                        save_name TEXT,
                        created_date DATE,
                        last_update_date DATE,
                        is_original INTEGER,
                        is_bungei INTEGER,
                        language TEXT,
                        x_restrict INTEGER,
                        series_id INTEGER,
                        series_order INTEGER,
                        PRIMARY KEY (post_id, user_id)
                        )""")

    def insertNovelPost(self, post, filename):
        try:
            c = self.conn.cursor()
            post_id = int(post.imageId)
            c.execute(
                """INSERT OR IGNORE INTO novel_detail (user_id, post_id) VALUES(?, ?)""",
                (post.artist.artistId, post_id),
            )
            c.execute(
                """UPDATE novel_detail
                            SET save_name = ?,
                                created_date = ?,
                                last_update_date = ?,
                                is_original = ?,
                                is_bungei = ?,
                                language = ?,
                                x_restrict = ?,
                                series_id = ?,
                                series_order = ?
                            WHERE post_id = ?""",
                (
                    filename,
                    post.worksDateDateTime,
                    post.uploadDate,
                    post.isOriginal,
                    post.isBungei,
                    post.language,
                    post.xRestrict,
                    post.seriesId,
                    post.seriesOrder,
                    post_id,
                ),
            )
            self.conn.commit()
        except BaseException:
            print("Error at insertSketchPost():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    def selectNovelPostByPostId(self, post_id):
        try:
            c = self.conn.cursor()
            post_id = int(post_id)
            c.execute("""SELECT * FROM novel_detail WHERE post_id = ?""", (post_id,))
            return c.fetchone()
        except BaseException:
            print("Error at selectNovelPostByPostId():", str(sys.exc_info()))
            print("failed")
            raise
        finally:
            c.close()

    ##########################################
    # VIII. Utilities                        #
    ##########################################

    def menu(self):
        PADDING = 60
        print(
            Fore.YELLOW
            + Back.BLACK
            + Style.BRIGHT
            + "Pixiv DB Manager Console"
            + Style.RESET_ALL
        )
        print(Style.BRIGHT + "── Pixiv ".ljust(PADDING, "─") + Style.RESET_ALL)
        print("1. Show all member")
        print("2. Show all images")
        print("3. Export list (member_id only)")
        print("4. Export list (detailed)")
        print("5. Show member by last downloaded date")
        print("6. Show image by image_id")
        print("7. Show member by member_id")
        print("8. Show image by member_id")
        print("9. Delete member by member_id")
        print("10. Delete image by image_id")
        print("11. Delete member and image (cascade deletion)")
        print("12. Blacklist image by image_id")
        print("13. Show all deleted member")
        print("14. Delete members by list")
        print("15. Keep members by list")
        print(Style.BRIGHT + "── FANBOX ".ljust(PADDING, "─") + Style.RESET_ALL)
        print("f1. Export FANBOX post list")
        print("f2. Delete FANBOX download history by member_id")
        print("f3. Delete FANBOX download history by post_id")
        print(Style.BRIGHT + "── Sketch ".ljust(PADDING, "─") + Style.RESET_ALL)
        print("s1. Delete Sketch download history by member_id")
        print("s2. Delete Sketch download history by post_id")
        print(
            Style.BRIGHT + "── Batch Manage DB ".ljust(PADDING, "─") + Style.RESET_ALL
        )
        print("c. Clean Up Database")
        print("i. Interactive Clean Up Database")
        print("p. Compact Database")
        print("r. Replace Root Path")
        print(Style.BRIGHT + "── Folder Database (per-folder DB) ".ljust(PADDING, "─") + Style.RESET_ALL)
        print("d2. Manage folder database (compare/sync/replace)")
        print("x. Exit")
        selection = input("Select one? ").rstrip("\r")
        return selection

    def main(self):
        PixivHelper.get_logger().info("DB Manager (d).")
        try:
            while True:
                selection = self.menu()

                if selection == "1":
                    self.printMemberList()
                elif selection == "2":
                    self.printImageList()
                elif selection == "3":
                    filename = input("Filename? ").rstrip("\r")
                    includeArtistToken = input(
                        "Include Artist Token[y/n, default is no]? "
                    ).rstrip("\r")
                    if includeArtistToken.lower() == "y":
                        includeArtistToken = True
                    else:
                        includeArtistToken = False
                    self.exportList(filename, includeArtistToken)
                elif selection == "4":
                    filename = input("Filename? ").rstrip("\r")
                    self.exportDetailedList(filename)
                elif selection == "5":
                    date = input("Number of date? ").rstrip("\r")
                    rows = self.selectMembersByLastDownloadDate(date)
                    if rows is not None:
                        for row in rows:
                            print("{0}\t\t{1}\n".format(row.memberId, row.path))
                    else:
                        print("Not Found!\n")
                elif selection == "6":
                    image_id = input("image_id? ").rstrip("\r")
                    row = self.selectImageByImageId(image_id)
                    if row is not None:
                        for string in row:
                            print("	", end=" ")
                            print(string)
                        print("\n")
                    else:
                        print("Not Found!\n")
                elif selection == "7":
                    member_id = input("member_id? ").rstrip("\r")
                    row = self.selectMemberByMemberId(member_id)
                    if row is not None:
                        for string in row:
                            print("	", end=" ")
                            print(string)
                        print("\n")
                    else:
                        print("Not Found!\n")
                elif selection == "8":
                    member_id = input("member_id? ").rstrip("\r")
                    rows = self.selectImageByMemberId(member_id)
                    if rows is not None:
                        for row in rows:
                            for string in row:
                                print("	", end=" ")
                                print(string)
                            print("\n")
                    else:
                        print("Not Found!\n")
                elif selection == "9":
                    member_id = input("member_id? ").rstrip("\r")
                    self.deleteMemberByMemberId(member_id)
                elif selection == "10":
                    image_id = input("image_id? ").rstrip("\r")
                    self.deleteImage(image_id)
                elif selection == "11":
                    member_id = input("member_id? ").rstrip("\r")
                    self.deleteCascadeMemberByMemberId(member_id)
                elif selection == "12":
                    member_id = input("member_id? ").rstrip("\r")
                    image_id = input("image_id? ").rstrip("\r")
                    self.blacklistImage(member_id, image_id)
                elif selection == "13":
                    self.printMemberList(isDeleted=True)
                elif selection == "14":
                    self.deleteMembersByList()
                elif selection == "15":
                    self.keepMembersByList()
                elif selection == "f1":
                    filename = input("Filename? ").rstrip("\r")
                    sep = input('Separator? (1(default)=",", 2="\\t") ').rstrip("\r")
                    sep = "\t" if sep == "2" else ","
                    self.exportFanboxPostList(filename, sep)
                elif selection == "f2":
                    member_id = input("member_id? ").rstrip("\r")
                    self.deleteFanboxPost(member_id, "member_id")
                elif selection == "f3":
                    post_id = input("post_id? ").rstrip("\r")
                    self.deleteFanboxPost(post_id, "post_id")
                elif selection == "s1":
                    member_id = input("member_id? ").rstrip("\r")
                    self.deleteSketchPost(member_id, "member_id")
                elif selection == "s2":
                    post_id = input("post_id? ").rstrip("\r")
                    self.deleteSketchPost(post_id, "post_id")
                elif selection == "c":
                    self.cleanUp()
                    self.cleanUpFanbox()
                    self.cleanUpSketch()
                elif selection == "i":
                    self.interactiveCleanUp()
                    self.interactiveCleanUpFanbox()
                    self.interactiveSketchCleanUp()
                elif selection == "p":
                    self.compactDatabase()
                elif selection == "r":
                    self.replaceRootPath()
                elif selection == "d2":
                    self.folder_database_menu()
                elif selection == "x":
                    break
            print("end PixivDBManager.")
        except BaseException:
            print("Error: ", sys.exc_info())
            self.main()

    def folder_database_menu(self):
        """Interactive menu for managing folder-specific databases."""
        import datetime
        import re
        
        while True:
            print("\n=== Folder Database Manager ===")
            print("1. Compare main DB with folder DB")
            print("2. Sync folder DB incrementally (add missing from main DB)")
            print("3. Replace folder DB completely (backup old first)")
            print("4. Scan and sync local files into folder DB")
            print("x. Exit")
            
            selection = input("Select one? ").rstrip("\r").lower()
            
            if selection == "1":
                folder_db_path = input("Path to folder DB? ").rstrip("\r")
                if not os.path.exists(folder_db_path):
                    print(f"ERROR: Folder DB not found: {folder_db_path}")
                    continue
                self._compare_databases_interactive(folder_db_path)
                
            elif selection == "2":
                folder_db_path = input("Path to folder DB? ").rstrip("\r")
                if not os.path.exists(folder_db_path):
                    print(f"ERROR: Folder DB not found: {folder_db_path}")
                    continue
                root_dir = input("Root directory for folder DB? ").rstrip("\r")
                if not os.path.isdir(root_dir):
                    print(f"ERROR: Root directory not found: {root_dir}")
                    continue
                self._sync_folder_db_incremental_interactive(folder_db_path, root_dir)
                
            elif selection == "3":
                folder_db_path = input("Path to folder DB? ").rstrip("\r")
                root_dir = input("Root directory for folder DB? ").rstrip("\r")
                if not os.path.isdir(root_dir):
                    print(f"ERROR: Root directory not found: {root_dir}")
                    continue
                self._replace_folder_db_interactive(folder_db_path, root_dir)
                
            elif selection == "4":
                folder_db_path = input("Path to folder DB? ").rstrip("\r")
                if not os.path.exists(folder_db_path):
                    print(f"ERROR: Folder DB not found: {folder_db_path}")
                    continue
                root_dir = input("Root directory to scan? ").rstrip("\r")
                if not os.path.isdir(root_dir):
                    print(f"ERROR: Root directory not found: {root_dir}")
                    continue
                self._scan_local_files_interactive(folder_db_path, root_dir)
                
            elif selection == "x":
                break

    def _compare_databases_interactive(self, folder_db_path):
        """Compare current DB with folder DB."""
        print(f"\n=== Comparing Databases ===")
        folder_conn = sqlite3.connect(folder_db_path)
        
        try:
            c_main = self.conn.cursor()
            c_folder = folder_conn.cursor()
            
            c_main.execute("SELECT COUNT(*) FROM pixiv_master_member")
            main_member_count = c_main.fetchone()[0]
            
            c_folder.execute("SELECT COUNT(*) FROM pixiv_master_member")
            folder_member_count = c_folder.fetchone()[0]
            
            c_main.execute("SELECT COUNT(*) FROM pixiv_master_image")
            main_image_count = c_main.fetchone()[0]
            
            c_folder.execute("SELECT COUNT(*) FROM pixiv_master_image")
            folder_image_count = c_folder.fetchone()[0]
            
            print(f"\nMain DB: {main_member_count} members, {main_image_count} images")
            print(f"Folder DB: {folder_member_count} members, {folder_image_count} images")
            print(f"Difference: {main_member_count - folder_member_count:+d} members, {main_image_count - folder_image_count:+d} images")
            
        finally:
            folder_conn.close()

    def _sync_folder_db_incremental_interactive(self, folder_db_path, root_dir):
        """Incrementally sync: add missing members/images from main DB to folder DB."""
        print(f"\n=== Incremental Sync (Main DB → Folder DB) ===")
        
        folder_conn = sqlite3.connect(folder_db_path)
        
        try:
            c_main = self.conn.cursor()
            c_folder = folder_conn.cursor()
            
            c_main.execute("SELECT member_id FROM pixiv_master_member")
            main_members = set(row[0] for row in c_main.fetchall())
            
            c_folder.execute("SELECT member_id FROM pixiv_master_member")
            folder_members = set(row[0] for row in c_folder.fetchall())
            
            new_members = main_members - folder_members
            print(f"Found {len(new_members)} new members to add.")
            
            if new_members:
                placeholders = ",".join(["?"] * len(new_members))
                c_main.execute(f"SELECT * FROM pixiv_master_member WHERE member_id IN ({placeholders})", tuple(new_members))
                member_rows = c_main.fetchall()
                
                for row in member_rows:
                    try:
                        cols = len(row)
                        q = "INSERT OR IGNORE INTO pixiv_master_member VALUES(" + ",".join(["?"] * cols) + ")"
                        c_folder.execute(q, row)
                    except Exception:
                        continue
                
                c_main.execute(f"SELECT * FROM pixiv_master_image WHERE member_id IN ({placeholders})", tuple(new_members))
                image_rows = c_main.fetchall()
                
                for row in image_rows:
                    try:
                        cols = len(row)
                        q = "INSERT OR IGNORE INTO pixiv_master_image VALUES(" + ",".join(["?"] * cols) + ")"
                        c_folder.execute(q, row)
                    except Exception:
                        continue
                
                folder_conn.commit()
                print(f"Synced {len(new_members)} members and {len(image_rows)} images.")
            
            print(f"Scanning local files...")
            inserted = self._scan_local_files_to_db(folder_conn, root_dir)
            print(f"Added {inserted} new images from local files.")
            
        finally:
            folder_conn.close()

    def _replace_folder_db_interactive(self, folder_db_path, root_dir):
        """Replace folder DB with main DB data."""
        print(f"\n=== Replace Folder DB ===")
        print(f"This will replace {folder_db_path} with data from main DB.")
        
        confirm = input("Are you sure? [y/n, default n]: ").rstrip("\r").lower()
        if confirm != 'y':
            print("Cancelled.")
            return
        
        if os.path.exists(folder_db_path):
            import shutil
            backup_path = folder_db_path + ".backup"
            shutil.copy2(folder_db_path, backup_path)
            print(f"Backed up to {backup_path}")
            os.remove(folder_db_path)
        
        folder_conn = sqlite3.connect(folder_db_path)
        
        try:
            db_mgr = PixivDBManager(root_directory=root_dir, target=folder_db_path)
            db_mgr.createDatabase()
            db_mgr.close()
            
            c_main = self.conn.cursor()
            c_folder = folder_conn.cursor()
            
            c_main.execute("SELECT member_id FROM pixiv_master_member")
            all_members = [row[0] for row in c_main.fetchall()]
            print(f"Copying {len(all_members)} members...")
            
            if all_members:
                placeholders = ",".join(["?"] * len(all_members))
                
                c_main.execute(f"SELECT * FROM pixiv_master_member WHERE member_id IN ({placeholders})", tuple(all_members))
                member_rows = c_main.fetchall()
                
                for row in member_rows:
                    try:
                        cols = len(row)
                        q = "INSERT OR IGNORE INTO pixiv_master_member VALUES(" + ",".join(["?"] * cols) + ")"
                        c_folder.execute(q, row)
                    except Exception:
                        continue
                
                c_main.execute(f"SELECT * FROM pixiv_master_image WHERE member_id IN ({placeholders})", tuple(all_members))
                image_rows = c_main.fetchall()
                
                for row in image_rows:
                    try:
                        cols = len(row)
                        q = "INSERT OR IGNORE INTO pixiv_master_image VALUES(" + ",".join(["?"] * cols) + ")"
                        c_folder.execute(q, row)
                    except Exception:
                        continue
                
                folder_conn.commit()
                print(f"Copied {len(member_rows)} members and {len(image_rows)} images.")
            
            print(f"Scanning local files...")
            inserted = self._scan_local_files_to_db(folder_conn, root_dir)
            print(f"Added {inserted} images from local files.")
            print("Done.")
            
        finally:
            folder_conn.close()

    def _scan_local_files_to_db(self, folder_conn, root_dir):
        """Scan root_dir and insert found image IDs."""
        import re
        import datetime
        
        IMAGE_ID_RE = re.compile(r"(\d{6,9})")
        inserted = 0
        c = folder_conn.cursor()
        
        for dirpath, dirs, files in os.walk(root_dir):
            for f in files:
                if f.startswith('.'):
                    continue
                m = IMAGE_ID_RE.search(f)
                if not m:
                    continue
                try:
                    image_id = int(m.group(1))
                    c.execute("SELECT 1 FROM pixiv_master_image WHERE image_id = ?", (image_id,))
                    if c.fetchone():
                        continue
                    
                    save_name = os.path.relpath(os.path.join(dirpath, f), root_dir)
                    created = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    c.execute("INSERT OR IGNORE INTO pixiv_master_image (image_id, member_id, title, save_name, created_date, last_update_date) VALUES (?,?,?,?,?,?)",
                              (image_id, None, '', save_name, created, created))
                    inserted += 1
                except Exception:
                    continue
        
        folder_conn.commit()
        return inserted

    def _scan_local_files_interactive(self, folder_db_path, root_dir):
        """Scan local files and insert into folder DB."""
        print(f"\n=== Scanning Local Files ===")
        print(f"Scanning {root_dir}...")
        
        folder_conn = sqlite3.connect(folder_db_path)
        
        try:
            inserted = self._scan_local_files_to_db(folder_conn, root_dir)
            print(f"Added {inserted} images from local files.")
        finally:
            folder_conn.close()

    def selectDistinctMembersWithImages(self):
        try:
            c = self.conn.cursor()
            c.execute(
                """SELECT DISTINCT member_id FROM pixiv_master_image WHERE save_name != 'N/A'"""
            )
            rows = c.fetchall()
            return [r[0] for r in rows] if rows else []
        except BaseException:
            print("Error at selectDistinctMembersWithImages():", str(sys.exc_info()))
            return []
        finally:
            c.close()
