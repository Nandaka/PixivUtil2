# -*- coding: utf-8 -*-
"""
Unified Author Info Fetcher
统一的作者信息获取器，支持多个API来源的自动fallback
"""

import sys
import os
import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import common.PixivBrowserFactory as PixivBrowserFactory
import common.PixivHelper as PixivHelper
from common.PixivException import PixivException
from model.AuthorProfile import AuthorProfile


class AuthorInfoFetcher:
    """
    统一的作者信息获取器
    支持OAuth、AJAX、HTML等多个信息来源，智能fallback
    """
    
    def __init__(self, browser=None, config=None):
        """
        初始化获取器
        
        Args:
            browser: PixivBrowser实例
            config: PixivConfig实例
        """
        self.browser = browser
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def fetch_profile(self, member_id: int, force_refresh=False, method='auto') -> Optional[AuthorProfile]:
        """
        获取作者信息
        
        Args:
            member_id: 作者ID
            force_refresh: 是否强制刷新
            method: 'oauth', 'ajax', 或 'auto'
        
        Returns:
            AuthorProfile对象或None
        """
        if method == 'auto':
            methods = [
                ('oauth', self._fetch_via_oauth),
                ('ajax', self._fetch_via_ajax),
            ]
        elif method == 'oauth':
            methods = [('oauth', self._fetch_via_oauth)]
        elif method == 'ajax':
            methods = [('ajax', self._fetch_via_ajax)]
        else:
            PixivHelper.print_and_log('error', f'Unknown method: {method}')
            return None
        
        for method_name, method_func in methods:
            try:
                PixivHelper.print_and_log('info', f'Trying {method_name} method for member {member_id}')
                profile = method_func(member_id)
                
                if profile and profile.is_valid():
                    profile.source = method_name
                    profile.fetched_at = datetime.now()
                    PixivHelper.print_and_log('info', f'✓ Successfully fetched via {method_name}')
                    return profile
            except Exception as e:
                PixivHelper.print_and_log('warn', f'✗ {method_name} failed: {e}')
                continue
        
        PixivHelper.print_and_log('warn', f'All methods failed for member {member_id}')
        return None
    
    def _fetch_via_oauth(self, member_id: int) -> Optional[AuthorProfile]:
        """
        通过OAuth app-api获取信息
        优先级最高，返回最完整的数据
        """
        try:
            if not self.browser:
                return None
            
            url = f'https://app-api.pixiv.net/v1/user/detail?user_id={member_id}'
            
            # 尝试从缓存获取
            response = self.browser._get_from_cache(url)
            if response is None:
                # 使用OAuth获取
                PixivHelper.print_and_log('info', f'OAuth: starting request for {member_id}')
                oauth_mgr = self.browser._oauth_manager
                PixivHelper.print_and_log('info', f'OAuth: got oauth manager')
                resp = oauth_mgr.get_user_info(member_id, timeout=30)
                PixivHelper.print_and_log('info', f'OAuth: request completed, status {resp.status_code}')
                response = json.loads(resp.text)
                PixivHelper.print_and_log('info', f'OAuth: json parsed')
                self.browser._put_to_cache(url, response)
            
            # 提取数据
            user_data = response.get('user', {})
            profile_data = response.get('profile', {})
            profile_publicity = response.get('profile_publicity', {})
            workspace = response.get('workspace', {})
            
            profile = AuthorProfile(member_id)
            profile.name = user_data.get('name', '')
            
            # 头像
            profile_image_urls = user_data.get('profile_image_urls', {})
            if profile_image_urls:
                profile.avatar_url = profile_image_urls.get('medium', '')
            
            # 背景（OAuth有时包含）
            if profile_data:
                profile.background_url = profile_data.get('background_image_url', '')
            
            # 社交信息
            profile.comment = user_data.get('comment', '')
            profile.webpage = profile_data.get('webpage', '')
            profile.twitter = profile_data.get('twitter_url', '') or profile_data.get('twitter_account', '')
            
            # 保存完整的OAuth profile数据
            profile.oauth_profile = {
                'user': user_data,
                'profile': profile_data,
                'profile_publicity': profile_publicity,
                'workspace': workspace
            }
            
            return profile if profile.is_valid() else None
            
        except Exception as e:
            PixivHelper.print_and_log('warn', f'OAuth fetch failed: {e}')
            return None
    
    def _fetch_via_ajax(self, member_id: int) -> Optional[AuthorProfile]:
        """
        通过AJAX API获取信息
        无需认证，返回基础信息+背景
        """
        try:
            if not self.browser:
                return None
            
            url = f'https://www.pixiv.net/ajax/user/{member_id}'
            
            # 尝试从缓存获取
            response = self.browser._get_from_cache(url)
            if response is None:
                res = self.browser.open_with_retry(url)
                response = json.loads(res.read())
                res.close()
                self.browser._put_to_cache(url, response)
            
            # 检查响应结构
            if 'body' not in response:
                return None
            
            body = response['body']
            profile = AuthorProfile(member_id)
            
            # 基本信息
            profile.name = body.get('name', '')
            
            # 头像（优先使用imageBig）
            profile.avatar_url = body.get('imageBig') or body.get('image', '')
            
            # 背景信息
            background = body.get('background')
            if background and isinstance(background, dict):
                profile.background_url = background.get('url', '')
            
            # 社交信息（通常为空）
            profile.comment = body.get('comment', '')
            profile.webpage = body.get('webpage', '')
            profile.twitter = body.get('twitter', '')
            
            # 外部链接
            external_links = body.get('externalLinks', [])
            if external_links:
                for link in external_links:
                    profile.external_links[link.get('title', 'unknown')] = link.get('url', '')
            
            return profile if profile.is_valid() else None
            
        except Exception as e:
            self.logger.debug(f'AJAX fetch failed: {e}')
            return None
    
    def _fetch_via_html(self, member_id: int) -> Optional[AuthorProfile]:
        """
        通过HTML爬取获取信息
        最后的降级方案，从用户主页解析JSON
        """
        try:
            if not self.browser:
                return None
            
            url = f'https://www.pixiv.net/users/{member_id}'
            res = self.browser.open_with_retry(url)
            html = res.read().decode('utf-8', errors='ignore')
            res.close()
            
            # 查找嵌入的JSON数据
            import re
            
            # 尝试多种模式
            patterns = [
                r'window\["__INITIAL_STATE__"\]\s*=\s*(\{.*?\});',
                r'<script[^>]*>\s*window\["__INITIAL_STATE__"\]\s*=\s*(\{.*?\});',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html, re.DOTALL)
                if match:
                    try:
                        json_str = match.group(1)
                        # 简单解析
                        data = json.loads(json_str)
                        # 提取用户信息
                        if 'users' in data:
                            for user_id, user_data in data['users'].items():
                                if int(user_id) == member_id:
                                    profile = AuthorProfile(member_id)
                                    profile.name = user_data.get('name', '')
                                    profile.avatar_url = user_data.get('imageMedium', '')
                                    return profile if profile.is_valid() else None
                    except Exception as e:
                        self.logger.debug(f'HTML JSON parse failed: {e}')
                        continue
            
            return None
            
        except Exception as e:
            self.logger.debug(f'HTML fetch failed: {e}')
            return None
    
    def batch_fetch(self, member_ids: List[int], force_refresh=False, delay=0.5) -> List[AuthorProfile]:
        """
        批量获取作者信息
        
        Args:
            member_ids: 作者ID列表
            force_refresh: 是否强制刷新
            delay: 请求间隔（秒）
        
        Returns:
            AuthorProfile列表
        """
        results = []
        total = len(member_ids)
        
        for i, member_id in enumerate(member_ids, 1):
            try:
                PixivHelper.print_and_log('info', f'[{i}/{total}] Fetching member {member_id}')
                profile = self.fetch_profile(member_id, force_refresh)
                if profile:
                    results.append(profile)
                
                # 间隔以避免限流
                if delay > 0:
                    time.sleep(delay)
            except Exception as e:
                PixivHelper.print_and_log('error', f'[{i}/{total}] Error for member {member_id}: {e}')
        
        return results
