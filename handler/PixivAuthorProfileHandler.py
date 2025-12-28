# -*- coding: utf-8 -*-
"""
Handler for fetching and saving author profile information (bio, external links, profile images)
Integrated with PixivUtil2's author processing workflow
"""

import os
import json
import sys
import traceback
from colorama import Fore, Style

import common.PixivBrowserFactory as PixivBrowserFactory
import common.PixivHelper as PixivHelper
import handler.PixivDownloadHandler as PixivDownloadHandler
from common.PixivException import PixivException


def _download_url_to_file(caller, url, filename, config, max_retry=3):
    """Simple URL to file download without complex error handling"""
    retry_count = 0
    while retry_count < max_retry:
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # Get the browser instance from caller or create new one
            if hasattr(caller, '_PixivUtil__br'):
                br = caller._PixivUtil__br
            else:
                # Fallback: create a simple browser
                br = PixivBrowserFactory.getBrowser(config)
            
            # Download with referer
            br.addheaders = [('Referer', 'https://www.pixiv.net/')]
            response = br.open(url, timeout=10)
            data = response.read()
            
            # Save to file
            with open(filename, 'wb') as f:
                f.write(data)
            
            PixivHelper.print_and_log('info', f'Downloaded to {filename}')
            return True
        except Exception as ex:
            retry_count += 1
            if retry_count < max_retry:
                PixivHelper.print_and_log('warning', f'Download retry {retry_count}/{max_retry} for {url}')
            else:
                PixivHelper.print_and_log('error', f'Failed to download {url}: {ex}')
                return False
    
    return False



def fetch_and_save_author_profile(caller, config, member_id, artist, user_dir, notifier=None):
    """
    Fetch author profile information from AJAX API and save locally
    
    Args:
        caller: Caller object with error handling
        config: PixivConfig object
        member_id: Member ID (int or str)
        artist: PixivArtist object with basic info
        user_dir: Target directory for author files
        notifier: Progress notifier callback
    
    Returns:
        True if successful, False otherwise
    """
    
    if notifier is None:
        notifier = PixivHelper.dummy_notifier
    
    if user_dir == '':
        target_dir = config.rootDirectory
    else:
        target_dir = user_dir
    
    try:
        # Fetch author profile from AJAX API
        PixivHelper.print_and_log('info', f'Fetching author profile for member_id: {member_id}')
        
        browser = PixivBrowserFactory.getBrowser()
        profile_data = _fetch_author_profile_ajax(browser, member_id)
        
        if profile_data is None:
            PixivHelper.print_and_log('warn', f'Failed to fetch author profile for member_id: {member_id}')
            # 如果AJAX获取失败，仍然尝试使用artist对象中的数据
            profile_data = {}
        
        # 关键修复: 将artist对象中的字段合并到profile_data中
        # 这些字段来自ParseInfo()从OAuth API提取
        if artist:
            # 基本信息
            if 'member_id' not in profile_data and artist.artistId:
                profile_data['member_id'] = artist.artistId
            if 'name' not in profile_data and artist.artistName:
                profile_data['name'] = artist.artistName
            if 'account' not in profile_data and artist.artistToken:
                profile_data['account'] = artist.artistToken
            if 'profileImageUrl' not in profile_data and artist.artistAvatar and artist.artistAvatar != "no_profile":
                profile_data['profileImageUrl'] = artist.artistAvatar
            if 'backgroundImageUrl' not in profile_data and artist.artistBackground and artist.artistBackground != "no_background":
                profile_data['backgroundImageUrl'] = artist.artistBackground
            
            # 简化的字段（向后兼容）
            if hasattr(artist, 'artistComment') and artist.artistComment:
                profile_data['comment'] = artist.artistComment
            if hasattr(artist, 'artistWebpage') and artist.artistWebpage:
                profile_data['webpage'] = artist.artistWebpage
            if hasattr(artist, 'artistTwitter') and artist.artistTwitter:
                profile_data['twitter'] = artist.artistTwitter
            if hasattr(artist, 'artistExternalLinks') and artist.artistExternalLinks:
                profile_data['externalLinks'] = artist.artistExternalLinks
            
            # 完整的 OAuth profile 数据（包含所有字段）
            if hasattr(artist, 'oauthProfile') and artist.oauthProfile:
                profile_data['oauthProfile'] = artist.oauthProfile
        
        # Save profile information to JSON file (always overwrite to get fresh data)
        profile_file = os.path.join(target_dir, 'author_profile.json')
        _save_profile_json(profile_data, profile_file)
        PixivHelper.print_and_log('info', f'Saved author profile to: {profile_file}')
        
        # Download profile images (avatar and background)
        _download_profile_images(caller, config, profile_data, target_dir, notifier)
        
        return True
        
    except PixivException as ex:
        PixivHelper.print_and_log('warn', f'PixivException while fetching author profile: {ex}')
        return False
    except Exception:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)
        PixivHelper.print_and_log('error', f'Error fetching author profile for member_id {member_id}: {sys.exc_info()}')
        return False


def _fetch_author_profile_ajax(browser, member_id):
    """
    Fetch author profile from Pixiv AJAX API
    
    Returns:
        Dictionary with profile data or None if failed
    """
    try:
        import json
        
        # Use the same API URL that PixivBrowser uses
        url = f"https://www.pixiv.net/ajax/user/{member_id}"
        
        try:
            # Try to get from cache first
            response = browser._get_from_cache(url)
            if response is None:
                # Fetch from API using browser's method
                res = browser.open_with_retry(url)
                info_str = res.read()
                res.close()
                response = json.loads(info_str)
                browser._put_to_cache(url, response)
        except Exception as ex:
            PixivHelper.print_and_log('warn', f'Error fetching from API: {ex}')
            return None
        
        if response and 'body' in response:
            body = response['body']
            
            # Helper function to find first non-empty value from multiple sources
            def get_first_nonempty(*values):
                """Return first non-empty value from list"""
                for v in values:
                    if v and str(v).strip():
                        return str(v).strip()
                return ''
            
            # Extract data - try MANY fallback sources to avoid nulls
            profile_info = {
                'member_id': member_id,
                'name': get_first_nonempty(
                    body.get('name'),
                    body.get('user', {}).get('name') if isinstance(body.get('user'), dict) else None
                ),
                # Bio/comment - try all possible fields
                'comment': get_first_nonempty(
                    body.get('comment'),
                    body.get('profile', {}).get('comment') if isinstance(body.get('profile'), dict) else None,
                    body.get('bio'),
                    body.get('introduction')
                ),
                # Avatar URL - this is critical, try many sources
                'profileImageUrl': get_first_nonempty(
                    body.get('imageBig'),
                    body.get('image'),
                    body.get('profileImageUrl'),
                    body.get('profile', {}).get('profileImageUrl') if isinstance(body.get('profile'), dict) else None,
                    body.get('profile', {}).get('image') if isinstance(body.get('profile'), dict) else None,
                    body.get('user', {}).get('profileImageUrl') if isinstance(body.get('user'), dict) else None,
                    # Fallback to placeholder if truly nothing found
                    'https://i.pximg.net/common/images/no_profile.png'
                ),
                # Background image - ensure null becomes empty string
                'backgroundImageUrl': get_first_nonempty(
                    body.get('backgroundImageUrl'),
                    body.get('profile', {}).get('backgroundImageUrl') if isinstance(body.get('profile'), dict) else None,
                    body.get('background_image_url'),
                    body.get('profile', {}).get('background') if isinstance(body.get('profile'), dict) else None,
                    body.get('background', {}).get('url') if isinstance(body.get('background'), dict) else None
                ),
                # Social links
                'webpage': get_first_nonempty(
                    body.get('webpage'),
                    body.get('profile', {}).get('webpage') if isinstance(body.get('profile'), dict) else None
                ),
                'twitter': get_first_nonempty(
                    body.get('twitter'),
                    body.get('profile', {}).get('twitter') if isinstance(body.get('profile'), dict) else None,
                    body.get('twitterAccountUrl')
                ),
                'externalLinks': _extract_external_links(body)
            }
            
            return profile_info
        
        return None
        
    except Exception as ex:
        PixivHelper.print_and_log('warn', f'Error fetching profile from AJAX: {ex}')
        return None


def _extract_external_links(profile_body):
    """
    Extract external links from profile body
    Looks for social media and support links
    
    Returns:
        Dictionary of link types to URLs
    """
    links = {}
    
    try:
        # Extract links from various possible fields
        if 'externalLinks' in profile_body:
            for link in profile_body['externalLinks']:
                link_type = link.get('title') or 'unknown'
                link_url = link.get('url')
                if link_url:
                    links[link_type] = link_url
        
        # Also capture common social media if available
        common_fields = {
            'twitter': 'Twitter',
            'webpage': 'Webpage',
            'instagram': 'Instagram',
            'tumblr': 'Tumblr',
            'skeb': 'Skeb',
            'fanbox': 'Fanbox'
        }
        
        for field, label in common_fields.items():
            if field in profile_body and profile_body[field]:
                links[label] = profile_body[field]
    
    except Exception as ex:
        PixivHelper.print_and_log('warn', f'Error extracting external links: {ex}')
    
    return links


def _save_profile_json(profile_data, filepath, artist=None):
    """
    Save profile data to JSON file
    Profile data should already contain merged OAuth+AJAX fields
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, ensure_ascii=False, indent=2)
    except Exception as ex:
        PixivHelper.print_and_log('error', f'Error saving profile JSON: {ex}')


def _download_profile_images(caller, config, profile_data, target_dir, notifier):
    """
    Download profile images (avatar and background) if they don't exist
    """
    if caller.DEBUG_SKIP_PROCESS_IMAGE:
        return
    
    try:
        # Download avatar
        avatar_url = profile_data.get('profileImageUrl')
        if avatar_url and avatar_url.startswith('http'):
            avatar_filename = os.path.join(target_dir, 'author_avatar.jpg')
            if not os.path.exists(avatar_filename):
                PixivHelper.print_and_log('info', f'Downloading author avatar from {avatar_url}')
                _download_url_to_file(caller, avatar_url, avatar_filename, config)
        
        # Download background
        bg_url = profile_data.get('backgroundImageUrl')
        if bg_url and bg_url.startswith('http'):
            bg_filename = os.path.join(target_dir, 'author_background.jpg')
            if not os.path.exists(bg_filename):
                PixivHelper.print_and_log('info', f'Downloading author background from {bg_url}')
                _download_url_to_file(caller, bg_url, bg_filename, config)
    
    except Exception as ex:
        PixivHelper.print_and_log('warn', f'Error downloading profile images: {ex}')
