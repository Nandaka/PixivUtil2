#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Enhanced Author Profile Batch Fetcher
使用新的统一AuthorInfoFetcher和AuthorProfile的改进版批量获取脚本
"""

import os
import sys
import json
import time
import re
import argparse
import logging
import random
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import common.PixivBrowserFactory as PixivBrowserFactory
from common.PixivConfig import PixivConfig
import common.PixivHelper as PixivHelper
from handler.AuthorInfoFetcher import AuthorInfoFetcher
from model.AuthorProfile import AuthorProfile


def setup_logging(log_file=None):
    """设置日志"""
    log_level = logging.INFO
    
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    return logging.getLogger(__name__)


def find_author_directories(base_dir):
    """
    扫描基目录，找到所有已有的作者文件夹
    返回 {member_id: (folder_path, author_name)} 字典
    """
    author_dirs = {}
    
    if not os.path.isdir(base_dir):
        print(f"Base directory not found: {base_dir}")
        return author_dirs
    
    # 正则匹配作者ID（数字）
    id_pattern = re.compile(r'^(\d+)')
    
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            match = id_pattern.match(item)
            if match:
                member_id = int(match.group(1))
                # 提取作者名（去掉ID部分）
                author_name = item[len(str(member_id)):].strip(' -_')
                author_dirs[member_id] = (item_path, author_name)
    
    return author_dirs


def process_author_profile(member_id, author_dir, fetcher, force_update=False, method='auto'):
    """
    处理单个作者的信息
    
    Args:
        member_id: 作者ID
        author_dir: 作者目录
        fetcher: AuthorInfoFetcher实例
        force_update: 是否强制更新
        method: API方法
    
    Returns:
        (success: bool, profile: AuthorProfile or None)
    """
    profile_file = os.path.join(author_dir, 'author_profile.json')
    
    # 检查是否需要跳过
    if os.path.exists(profile_file) and not force_update:
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                # 检查是否已有有效数据
                if existing.get('name') and existing.get('avatar_url'):
                    print(f"  ℹ Profile already exists, skipping")
                    return True, AuthorProfile.from_dict(existing)
        except Exception as e:
            print(f"  ⚠ Error reading existing profile: {e}")
    
    # 获取新的信息
    print(f"  ↓ Fetching author info...")
    profile = fetcher.fetch_profile(member_id, force_refresh=force_update, method=method)
    
    if not profile or not profile.is_valid():
        print(f"  ✗ Failed to fetch valid profile")
        return False, None
    
    # 保存JSON
    os.makedirs(author_dir, exist_ok=True)
    try:
        with open(profile_file, 'w', encoding='utf-8') as f:
            json.dump(profile.to_dict(), f, ensure_ascii=False, indent=2)
        print(f"  ✓ Profile saved to author_profile.json")
    except Exception as e:
        print(f"  ✗ Error saving profile: {e}")
        return False, profile
    
    # 下载图片
    download_author_images(profile, author_dir)
    
    return True, profile


def download_author_images(profile, author_dir):
    """下载作者头像和背景"""
    
    # 下载头像
    if profile.has_avatar():
        avatar_file = os.path.join(author_dir, 'author_avatar.jpg')
        if not os.path.exists(avatar_file):
            try:
                print(f"  ↓ Downloading avatar...")
                import urllib.request
                urllib.request.urlretrieve(profile.avatar_url, avatar_file)
                print(f"  ✓ Avatar downloaded")
            except Exception as e:
                print(f"  ⚠ Avatar download failed: {e}")
    
    # 下载背景
    if profile.has_background():
        bg_file = os.path.join(author_dir, 'author_background.jpg')
        if not os.path.exists(bg_file):
            try:
                print(f"  ↓ Downloading background...")
                import urllib.request
                urllib.request.urlretrieve(profile.background_url, bg_file)
                print(f"  ✓ Background downloaded")
            except Exception as e:
                print(f"  ⚠ Background download failed: {e}")


def parse_delay(delay_str):
    """解析延迟参数，支持固定值或范围"""
    if '-' in delay_str:
        try:
            min_delay, max_delay = map(float, delay_str.split('-'))
            return min_delay, max_delay
        except ValueError:
            raise ValueError(f"Invalid delay range: {delay_str}")
    else:
        try:
            fixed_delay = float(delay_str)
            return fixed_delay, fixed_delay
        except ValueError:
            raise ValueError(f"Invalid delay value: {delay_str}")


def main():
    parser = argparse.ArgumentParser(description='Enhanced Author Profile Batch Fetcher')
    parser.add_argument('--base-dir', default='G:\\Porn\\Pixiv', help='Base directory with author folders')
    parser.add_argument('--force', action='store_true', help='Force refresh all profiles')
    parser.add_argument('--delay', default='3-5', help='Delay between requests (seconds, can be range like "2-5")')
    parser.add_argument('--log-file', help='Log file path')
    parser.add_argument('--max-authors', type=int, default=0, help='Maximum authors to process (0=all)')
    parser.add_argument('--method', choices=['oauth', 'ajax', 'auto'], default='auto', help='API method to use (oauth/ajax/auto)')
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logging(args.log_file)
    
    # 加载配置
    try:
        config = PixivConfig()
        config.loadConfig('config.ini')
        PixivHelper.set_config(config)
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    # 初始化浏览器和获取器
    try:
        browser = PixivBrowserFactory.getBrowser(config=config)
        fetcher = AuthorInfoFetcher(browser=browser, config=config)
    except Exception as e:
        print(f"Error initializing browser: {e}")
        return
    
    # 查找所有作者目录
    print("="*80)
    print("Finding author directories...")
    author_dirs = find_author_directories(args.base_dir)
    print(f"Found {len(author_dirs)} author directories")
    
    if not author_dirs:
        print("No author directories found!")
        return
    
    # 限制数量
    if args.max_authors > 0:
        author_dirs = dict(list(author_dirs.items())[:args.max_authors])
        print(f"Processing {len(author_dirs)} authors (limited)")
    
    # 解析延迟参数
    try:
        min_delay, max_delay = parse_delay(args.delay)
        print(f"Delay range: {min_delay}-{max_delay}s")
    except ValueError as e:
        print(f"Error parsing delay: {e}")
        return
    
    # 处理每个作者
    print("="*80)
    print(f"Processing authors (force={args.force}, delay={args.delay}s)...")
    print("="*80)
    
    results = {
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'total': len(author_dirs)
    }
    
    start_time = time.time()
    
    for i, (member_id, (author_dir, author_name)) in enumerate(author_dirs.items(), 1):
        print(f"\n[{i}/{results['total']}] Processing: {member_id} {author_name}")
        
        try:
            success, profile = process_author_profile(
                member_id, author_dir, fetcher, 
                force_update=args.force, method=args.method
            )
            
            if success:
                if profile:
                    results['success'] += 1
                    print(f"  ✓ Complete: {profile.name}")
                else:
                    results['skipped'] += 1
                    print(f"  ℹ Skipped (already exists)")
            else:
                results['failed'] += 1
                print(f"  ✗ Failed to fetch profile")
        
        except Exception as e:
            results['failed'] += 1
            print(f"  ✗ Error: {e}")
        
        # 间隔
        if i < results['total']:
            delay = random.uniform(min_delay, max_delay)
            print(f"  Waiting {delay:.1f}s...")
            time.sleep(delay)
    
    # 统计结果
    elapsed_time = time.time() - start_time
    
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)
    print(f"Total:    {results['total']}")
    print(f"Success:  {results['success']}")
    print(f"Failed:   {results['failed']}")
    print(f"Skipped:  {results['skipped']}")
    print(f"Time:     {elapsed_time:.1f}s ({elapsed_time/results['total']:.1f}s per author)")
    print("="*80)


if __name__ == '__main__':
    main()
