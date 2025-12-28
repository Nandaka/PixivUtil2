#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Batch fetch author profiles for already downloaded artists
Usage: python fetch_author_profiles_batch.py [--list followed_artis        
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
            break
        except Exception as ex:
            logging.error(f"  [X] Error processing member {member_id}: {ex}")
            fail_count += 1
    
    # Summary
    logging.info("\n" + "="*60)
    logging.info("Batch fetch completed!")
    logging.info(f"  Success: {success_count}")
    logging.info(f"  Updated: {update_count}")
    logging.info(f"  Skipped: {skip_count}")
    logging.info(f"  Failed:  {fail_count}")
    logging.info(f"  Total:   {len(members)}")
    logging.info("="*60)
    
    return success_count, skip_count, fail_countdir G:\\Porn\\Pixiv]

This script reads a list of member IDs from a file and fetches their profile information
(bio, external links, avatar, background) without downloading their artworks.
"""

import os
import sys
import json
import argparse
import time
import logging

# Add parent directory to path to import PixivUtil2 modules
sys.path.insert(0, os.path.dirname(__file__))

import common.PixivBrowserFactory as PixivBrowserFactory
import common.PixivHelper as PixivHelper
import handler.PixivDownloadHandler as PixivDownloadHandler
import handler.PixivAuthorProfileHandler as PixivAuthorProfileHandler
from common.PixivConfig import PixivConfig
from common.PixivException import PixivException
from model.PixivArtist import PixivArtist


class DummyCaller:
    """Minimal caller object for standalone script"""
    def __init__(self, config=None):
        self.DEBUG_SKIP_PROCESS_IMAGE = False
        self.errorList = []
        self.__dbManager__ = None  # No database manager in batch mode
        self.__config__ = config  # Store config for download handler
        self.UTF8_FS = False  # Use UTF-8 for filenames


def setup_logging(log_level=logging.DEBUG):
    """Setup logging configuration"""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('fetch_author_profiles.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def load_member_list(list_file):
    """Load member IDs from file"""
    members = []
    try:
        with open(list_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Handle format: member_id or member_id artist_name
                    parts = line.split()
                    if parts:
                        try:
                            member_id = int(parts[0])
                            members.append(member_id)
                        except ValueError:
                            logging.warning(f"Invalid member ID: {parts[0]}")
    except FileNotFoundError:
        logging.error(f"List file not found: {list_file}")
        return None
    
    logging.info(f"Loaded {len(members)} member IDs from {list_file}")
    return members


def get_author_directory(member_id, base_dir, artist_name=None):
    """
    Get existing author directory path
    Follows PixivUtil2's naming convention: {member_id} {artist_name}
    Returns existing directory or creates new one if artist_name provided
    """
    member_id_str = str(member_id)
    
    # First, try to find existing directory with pattern "{member_id} *" or "{member_id}"
    try:
        for entry in os.listdir(base_dir):
            entry_lower = entry.lower()
            # Match "{member_id} " or exact "{member_id}"
            if entry == member_id_str or entry.startswith(f"{member_id_str} "):
                full_path = os.path.join(base_dir, entry)
                if os.path.isdir(full_path):
                    return full_path
    except Exception as ex:
        logging.warning(f"Error listing directory {base_dir}: {ex}")
    
    # If no existing directory found and we have artist name, create new one
    if artist_name:
        return os.path.join(base_dir, f"{member_id_str} {artist_name}")
    
    # Fallback to just member_id
    return os.path.join(base_dir, member_id_str)


def fetch_author_info(browser, member_id):
    """Fetch author info from Pixiv API to get name - DEPRECATED, not needed"""
    # This function is no longer used since we work with existing folders
    return None


def process_member_profiles(config, members, base_dir, skip_existing=True, force_update=False):
    """Process author profiles in batch"""
    
    logging.info(f"Starting batch fetch for {len(members)} authors")
    logging.info(f"Output directory: {base_dir}")
    if force_update:
        logging.info(f"Mode: FORCE UPDATE (overwrite existing profiles)")
    else:
        logging.info(f"Mode: Skip existing profiles")
    
    browser = PixivBrowserFactory.getBrowser(config=config)
    caller = DummyCaller(config=config)
    
    success_count = 0
    skip_count = 0
    fail_count = 0
    update_count = 0
    
    for idx, member_id in enumerate(members, 1):
        logging.info(f"[{idx}/{len(members)}] Processing member_id: {member_id}")
        
        try:
            # Get author directory (must exist already)
            author_dir = get_author_directory(member_id, base_dir, artist_name=None)
            profile_file = os.path.join(author_dir, 'author_profile.json')
            
            # Check if directory exists - skip if not found
            if not os.path.isdir(author_dir):
                logging.info(f"  [SKIP] Directory not found")
                skip_count += 1
                continue
            
            logging.info(f"  Using directory: {author_dir}")
            
            # Check if profile exists
            profile_exists = os.path.exists(profile_file)
            
            # Skip if already has profile and not forcing update
            if profile_exists and not force_update:
                logging.info(f"  [SKIP] Profile already exists")
                skip_count += 1
                continue
            
            if profile_exists and force_update:
                logging.info(f"  [UPDATE] Force updating existing profile")
                update_count += 1
            
            # Fetch and save profile using OAuth API
            try:
                # Get OAuth data
                oauth_response = browser._oauth_manager.get_user_info(member_id)
                if oauth_response.status_code == 200:
                    oauth_data = oauth_response.json()
                    
                    # Create artist object and parse OAuth data
                    artist = PixivArtist(member_id)
                    artist.ParseInfo(oauth_data)
                    
                    # Use the enhanced fetch_and_save_author_profile method
                    success = PixivAuthorProfileHandler.fetch_and_save_author_profile(
                        caller, config, member_id, artist, author_dir, PixivHelper.dummy_notifier
                    )
                    
                    if success:
                        logging.info(f"  [OK] Profile saved with OAuth data")
                        success_count += 1
                    else:
                        logging.warning(f"  [X] Failed to save profile")
                        fail_count += 1
                else:
                    logging.error(f"  [X] OAuth API failed: {oauth_response.status_code}")
                    fail_count += 1
                    
            except Exception as ex:
                logging.error(f"  [X] Error processing member {member_id}: {ex}")
                fail_count += 1
            
            # Rate limiting
            time.sleep(config.downloadDelay)
        
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
            break
        except Exception as ex:
            logging.error(f"  ✗ Error processing member {member_id}: {ex}")
            fail_count += 1
    
    # Summary
    logging.info("\n" + "="*60)
    logging.info("Batch fetch completed!")
    logging.info(f"  Success: {success_count}")
    logging.info(f"  Skipped: {skip_count}")
    logging.info(f"  Failed:  {fail_count}")
    logging.info(f"  Total:   {len(members)}")
    logging.info("="*60)
    
    return success_count, skip_count, fail_count


def main():
    print("DEBUG: Starting main()")
    parser = argparse.ArgumentParser(
        description='Batch fetch author profiles for downloaded Pixiv artists'
    )
    parser.add_argument(
        '--list',
        default='followed_artists.txt',
        help='Member ID list file (default: followed_artists.txt)'
    )
    parser.add_argument(
        '--output-dir',
        default=None,
        help='Output directory (default: config.rootDirectory)'
    )
    parser.add_argument(
        '--config',
        default='config.ini',
        help='Config file (default: config.ini)'
    )
    parser.add_argument(
        '--no-skip',
        action='store_true',
        help='Re-fetch even if profile already exists (deprecated, use --force)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force update existing profiles (overwrite)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    print("DEBUG: Parsing arguments")
    args = parser.parse_args()
    
    print("DEBUG: Setting up logging")
    # Setup logging
    logger = setup_logging(getattr(logging, args.log_level))
    
    logger.info("Author Profile Batch Fetch Tool")
    logger.info("="*60)
    
    # Load config
    try:
        config = PixivConfig()
        config.loadConfig(args.config)
        logger.info(f"Loaded config from: {args.config}")
        
        # Set config for PixivHelper (global config used by download_image and other functions)
        PixivHelper.set_config(config)
        
        # Setup PixivHelper logger
        PixivHelper.get_logger(level=logging.DEBUG, reload=True)
    except Exception as ex:
        logger.error(f"Failed to load config: {ex}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Determine output directory
    output_dir = args.output_dir or config.rootDirectory
    if not os.path.isdir(output_dir):
        logger.error(f"Output directory does not exist: {output_dir}")
        return 1
    
    # Load member list
    members = load_member_list(args.list)
    if not members:
        logger.error(f"No members loaded from: {args.list}")
        return 1
    
    # Determine force update flag
    force_update = args.force or args.no_skip
    
    # Process
    try:
        process_member_profiles(
            config,
            members,
            output_dir,
            skip_existing=not force_update,
            force_update=force_update
        )
        return 0
    except Exception as ex:
        logger.error(f"Fatal error: {ex}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
