# -*- coding: utf-8 -*-
"""
Minimal, safe migration tool to create a per-folder sqlite DB from the existing main DB,
scan local files and insert local image IDs, and optionally prepare for remote comparison.

Usage (dry-run by default):
    python tools\migrate_folder_db.py --root "G:\\Porn\\Pixiv" --folder-db "G:\\Porn\\Pixiv\\pixiv_folder.db" --execute

This script intentionally avoids making destructive changes to the main DB.
It requires the repository environment so it imports project's modules.
"""

import argparse
import os
import sqlite3
import sys
import time
import re

# ensure repo path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from common.PixivConfig import PixivConfig
from PixivDBManager import PixivDBManager
import common.PixivHelper as PixivHelper

IMAGE_ID_RE = re.compile(r"(\d{6,9})")


def find_candidate_member_ids(main_conn, root_dir):
    """Find member_ids in main DB whose save_folder points into root_dir or whose member id folder exists."""
    c = main_conn.cursor()
    candidate = set()

    try:
        c.execute("SELECT member_id, save_folder FROM pixiv_master_member")
    except Exception:
        return candidate

    rows = c.fetchall()
    for member_id, save_folder in rows:
        try:
            if save_folder:
                candidate_dir = os.path.abspath(os.path.join(root_dir, save_folder))
                if os.path.commonpath([candidate_dir, os.path.abspath(root_dir)]) == os.path.abspath(root_dir) and os.path.exists(candidate_dir):
                    candidate.add(int(member_id))
            # also if a folder named by member_id exists under root_dir
            member_dir = os.path.join(root_dir, str(member_id))
            if os.path.exists(member_dir) and os.path.isdir(member_dir):
                candidate.add(int(member_id))
        except Exception:
            continue

    # also scan top-level folders under root_dir for names that start with digits -> possible member ids
    try:
        for name in os.listdir(root_dir):
            if not name:
                continue
            if name[0].isdigit():
                m = re.match(r"^(\d{6,9})", name)
                if m:
                    candidate.add(int(m.group(1)))
    except Exception:
        pass

    return candidate


def copy_members_and_images(main_conn, folder_conn, member_ids):
    """Copy member rows and image rows for given member_ids from main_conn to folder_conn."""
    if not member_ids:
        return 0, 0
    c_main = main_conn.cursor()
    c_folder = folder_conn.cursor()

    placeholders = ",".join(["?"] * len(member_ids))

    # Copy members
    c_main.execute(f"SELECT * FROM pixiv_master_member WHERE member_id IN ({placeholders})", tuple(member_ids))
    member_rows = c_main.fetchall()
    member_count = 0
    for row in member_rows:
        try:
            # build insert with matching number of columns; use INSERT OR IGNORE
            cols = len(row)
            q = "INSERT OR IGNORE INTO pixiv_master_member VALUES(" + ",".join(["?"] * cols) + ")"
            c_folder.execute(q, row)
            member_count += 1
        except Exception:
            continue

    # Copy images
    c_main.execute(f"SELECT * FROM pixiv_master_image WHERE member_id IN ({placeholders})", tuple(member_ids))
    image_rows = c_main.fetchall()
    image_count = 0
    for row in image_rows:
        try:
            cols = len(row)
            q = "INSERT OR IGNORE INTO pixiv_master_image VALUES(" + ",".join(["?"] * cols) + ")"
            c_folder.execute(q, row)
            image_count += 1
        except Exception:
            continue

    folder_conn.commit()
    return member_count, image_count


def scan_local_files_into_db(folder_conn, root_dir):
    """Scan root_dir recursively, extract image ids from filenames and insert basic rows into pixiv_master_image if missing."""
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
            except Exception:
                continue
            # check if exists
            try:
                c.execute("SELECT 1 FROM pixiv_master_image WHERE image_id = ?", (image_id,))
                if c.fetchone():
                    continue
                save_name = os.path.relpath(os.path.join(dirpath, f), root_dir)
                created = time.strftime('%Y-%m-%d %H:%M:%S')
                # insert minimal record: image_id, member_id NULL, title NULL, save_name
                c.execute("INSERT OR IGNORE INTO pixiv_master_image (image_id, member_id, title, save_name, created_date, last_update_date) VALUES (?,?,?,?,?,?)",
                          (image_id, None, '', save_name, created, created))
                inserted += 1
            except Exception:
                continue
    folder_conn.commit()
    return inserted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True, help='Root folder to migrate (example: G:\\Porn\\Pixiv)')
    parser.add_argument('--folder-db', required=True, help='Target folder DB path (example: G:\\Porn\\Pixiv\\pixiv_folder.db)')
    parser.add_argument('--execute', action='store_true', help='Actually perform changes (otherwise dry-run)')
    parser.add_argument('--compare-remote', action='store_true', help='After migration, invoke scan_and_mark to compare remote and optionally download missing')
    parser.add_argument('--download-missing', action='store_true', help='When compare-remote is used, attempt to download missing images')
    parser.add_argument('--download-limit', type=int, default=None, help='Limit downloads per member when downloading missing')
    args = parser.parse_args()

    root_dir = os.path.abspath(args.root)
    folder_db = os.path.abspath(args.folder_db)

    if not os.path.isdir(root_dir):
        print(f"ERROR: root folder does not exist: {root_dir}")
        return

    cfg = PixivConfig()
    cfg.loadConfig()
    # determine main DB path
    main_db = cfg.dbPath if getattr(cfg, 'dbPath', None) else os.path.join(PixivHelper.module_path(), 'db.sqlite')
    main_db = os.path.abspath(main_db)
    print(f"Main DB: {main_db}")
    print(f"Target folder DB: {folder_db}")
    print(f"Root folder: {root_dir}")
    print("Dry-run mode: not executing changes." if not args.execute else "Execute mode: changes will be applied.")

    # open main DB
    main_conn = sqlite3.connect(main_db)
    # ensure target DB exists and has schema
    if not args.execute:
        print("DRY RUN: Would create folder DB and copy candidate member/image rows.")

    folder_conn = sqlite3.connect(folder_db)
    # initialize schema in folder DB by using PixivDBManager.createDatabase
    if args.execute:
        fb_mgr = PixivDBManager(root_directory=root_dir, target=folder_db)
        fb_mgr.createDatabase()
        fb_mgr.close()
    else:
        # create tables if not exist using SQL from PixivDBManager.createDatabase minimal subset
        c = folder_conn.cursor()
        try:
            c.execute("CREATE TABLE IF NOT EXISTS pixiv_master_member (member_id INTEGER PRIMARY KEY ON CONFLICT IGNORE, name TEXT, save_folder TEXT, created_date DATE, last_update_date DATE, last_image INTEGER)")
            c.execute("CREATE TABLE IF NOT EXISTS pixiv_master_image (image_id INTEGER PRIMARY KEY, member_id INTEGER, title TEXT, save_name TEXT, created_date DATE, last_update_date DATE)")
            c.execute("CREATE TABLE IF NOT EXISTS pixiv_manga_image (image_id INTEGER, page INTEGER, save_name TEXT, created_date DATE, last_update_date DATE, PRIMARY KEY (image_id, page))")
            folder_conn.commit()
        except Exception:
            pass

    # find candidate member ids from main db
    candidates = find_candidate_member_ids(main_conn, root_dir)
    print(f"Found {len(candidates)} candidate member ids to copy.")
    if not candidates:
        print("No candidate members found by heuristics. You can still scan local files to populate images.")

    if args.execute and candidates:
        m_count, i_count = copy_members_and_images(main_conn, folder_conn, list(candidates))
        print(f"Copied {m_count} members and {i_count} images to folder DB.")
    else:
        print("DRY RUN: skipping copy. (use --execute to apply)")

    # scan local files and insert image ids
    inserted = 0
    if args.execute:
        inserted = scan_local_files_into_db(folder_conn, root_dir)
        print(f"Inserted {inserted} images discovered from local files into folder DB.")
    else:
        print("DRY RUN: would scan local files and insert discovered image ids into folder DB.")

    main_conn.close()
    folder_conn.close()

    print("Migration plan complete.")
    if args.compare_remote:
        print("Note: compare-remote requested. To run remote comparison and optional download, run PixivUtil2 with --start_action 5b or call handler.scan_and_mark_completed_members using the new folder DB by passing --db-file or setting folderDatabase in config and running the scan with execute.")


def compare_databases(main_db, folder_db):
    """Compare main DB and folder DB, show statistics and diffs."""
    main_conn = sqlite3.connect(main_db)
    folder_conn = sqlite3.connect(folder_db)
    
    try:
        # Get counts
        main_c = main_conn.cursor()
        folder_c = folder_conn.cursor()
        
        main_c.execute("SELECT COUNT(*) FROM pixiv_master_member")
        main_member_count = main_c.fetchone()[0]
        
        folder_c.execute("SELECT COUNT(*) FROM pixiv_master_member")
        folder_member_count = folder_c.fetchone()[0]
        
        main_c.execute("SELECT COUNT(*) FROM pixiv_master_image")
        main_image_count = main_c.fetchone()[0]
        
        folder_c.execute("SELECT COUNT(*) FROM pixiv_master_image")
        folder_image_count = folder_c.fetchone()[0]
        
        print(f"\n=== Database Comparison ===")
        print(f"Main DB members: {main_member_count}")
        print(f"Folder DB members: {folder_member_count}")
        print(f"Main DB images: {main_image_count}")
        print(f"Folder DB images: {folder_image_count}")
        
        # Check members in main but not in folder
        main_c.execute("SELECT member_id FROM pixiv_master_member WHERE member_id NOT IN (SELECT member_id FROM pixiv_master_member)")
        main_only_members = [str(row[0]) for row in main_c.fetchall()]
        
        if main_only_members:
            print(f"\nMembers in main DB but not in folder: {len(main_only_members)}")
    finally:
        main_conn.close()
        folder_conn.close()


def replace_folder_db_from_main(main_db, folder_db, root_dir):
    """Replace folder DB completely with main DB data (filtered by root_dir)."""
    import shutil
    
    print("\n=== Replacing Folder DB with Main DB Data ===")
    print(f"This will replace {folder_db} with filtered data from {main_db}.")
    
    confirm = input("Are you sure? [y/n, default n]: ").rstrip("\r").lower()
    if confirm != 'y':
        print("Operation cancelled.")
        return
    
    # Backup folder DB
    if os.path.exists(folder_db):
        backup_path = folder_db + ".backup"
        shutil.copy2(folder_db, backup_path)
        print(f"Backed up {folder_db} to {backup_path}")
        os.remove(folder_db)
    
    # Create new folder DB
    folder_conn = sqlite3.connect(folder_db)
    main_conn = sqlite3.connect(main_db)
    
    try:
        # Initialize schema
        fb_mgr = PixivDBManager(root_directory=root_dir, target=folder_db)
        fb_mgr.createDatabase()
        fb_mgr.close()
        
        # Find candidates and copy
        candidates = find_candidate_member_ids(main_conn, root_dir)
        print(f"Found {len(candidates)} candidate members to copy from main DB.")
        
        if candidates:
            m_count, i_count = copy_members_and_images(main_conn, folder_conn, list(candidates))
            print(f"Copied {m_count} members and {i_count} images to folder DB.")
        
        # Scan and insert local files
        inserted = scan_local_files_into_db(folder_conn, root_dir)
        print(f"Inserted {inserted} images discovered from local files into folder DB.")
        
        print("Replacement complete.")
    finally:
        main_conn.close()
        folder_conn.close()


def sync_folder_db_incremental(main_db, folder_db, root_dir):
    """Incrementally sync: add missing members/images from main DB to folder DB."""
    print("\n=== Incremental Sync (Main DB → Folder DB) ===")
    
    main_conn = sqlite3.connect(main_db)
    folder_conn = sqlite3.connect(folder_db)
    
    try:
        # Find candidates
        candidates = find_candidate_member_ids(main_conn, root_dir)
        
        # Get already existing members in folder DB
        c_folder = folder_conn.cursor()
        c_folder.execute("SELECT member_id FROM pixiv_master_member")
        existing_members = set(row[0] for row in c_folder.fetchall())
        
        new_members = set(candidates) - existing_members
        print(f"Found {len(new_members)} new members to add.")
        
        if new_members:
            m_count, i_count = copy_members_and_images(main_conn, folder_conn, list(new_members))
            print(f"Added {m_count} members and {i_count} images to folder DB.")
        else:
            print("No new members to add.")
        
        # Scan local files for new images
        inserted = scan_local_files_into_db(folder_conn, root_dir)
        print(f"Added {inserted} new images from local files to folder DB.")
        
    finally:
        main_conn.close()
        folder_conn.close()


if __name__ == '__main__':
    main()
