# -*- coding: utf-8 -*-
"""
Unified Author Profile Data Model
统一的作者信息数据模型，支持多个API来源
"""

from datetime import datetime
from typing import Dict, Optional
import json


class AuthorProfile:
    """
    统一的作者信息数据模型
    支持从多个API来源（OAuth, AJAX, HTML）创建一致的数据结构
    """
    
    def __init__(self, member_id: int):
        self.member_id = member_id
        self.name = ""
        self.avatar_url = ""
        self.background_url = ""
        self.comment = ""
        self.webpage = ""
        self.twitter = ""
        self.external_links: Dict[str, str] = {}
        
        # 完整的OAuth profile数据
        self.oauth_profile: Optional[Dict] = None
        
        # 元数据
        self.fetched_at: Optional[datetime] = None
        self.source = ""  # 'oauth', 'ajax', 'html'
        self.is_valid_data = False
    
    def is_valid(self) -> bool:
        """检查是否有有效数据"""
        return bool(self.member_id and self.name)
    
    def has_avatar(self) -> bool:
        """是否有头像URL"""
        return bool(self.avatar_url and self.avatar_url.startswith('http'))
    
    def has_background(self) -> bool:
        """是否有背景图URL"""
        return bool(self.background_url and self.background_url.startswith('http'))
    
    def to_dict(self) -> Dict:
        """转换为字典（用于JSON保存）"""
        result = {
            'member_id': self.member_id,
            'name': self.name,
            'avatar_url': self.avatar_url,
            'background_url': self.background_url,
            'comment': self.comment,
            'webpage': self.webpage,
            'twitter': self.twitter,
            'external_links': self.external_links,
            'fetched_at': self.fetched_at.isoformat() if self.fetched_at else None,
            'source': self.source
        }
        
        # 添加完整的OAuth profile数据
        if self.oauth_profile:
            result['oauthProfile'] = self.oauth_profile
            
        return result
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AuthorProfile':
        """从字典创建对象"""
        profile = cls(data.get('member_id', 0))
        profile.name = data.get('name', '')
        profile.avatar_url = data.get('avatar_url', '')
        profile.background_url = data.get('background_url', '')
        profile.comment = data.get('comment', '')
        profile.webpage = data.get('webpage', '')
        profile.twitter = data.get('twitter', '')
        profile.external_links = data.get('external_links', {})
        profile.source = data.get('source', '')
        
        # 加载完整的OAuth profile数据
        if 'oauthProfile' in data:
            profile.oauth_profile = data['oauthProfile']
        
        fetched_at_str = data.get('fetched_at')
        if fetched_at_str:
            profile.fetched_at = datetime.fromisoformat(fetched_at_str)
        
        return profile
    
    def merge_with(self, other: 'AuthorProfile', overwrite=False) -> None:
        """
        与另一个profile合并（补充缺失的字段）
        
        Args:
            other: 另一个AuthorProfile对象
            overwrite: 是否允许覆盖已有字段
        """
        if not other:
            return
        
        # 合并逻辑：优先保留当前值，除非overwrite=True或当前为空
        fields = ['name', 'avatar_url', 'background_url', 'comment', 'webpage', 'twitter']
        
        for field in fields:
            current_val = getattr(self, field, '')
            other_val = getattr(other, field, '')
            
            if overwrite or not current_val:
                if other_val:
                    setattr(self, field, other_val)
        
        # 外部链接合并（字典）
        if other.external_links:
            if overwrite:
                self.external_links = other.external_links.copy()
            else:
                # 只补充缺失的链接
                for key, value in other.external_links.items():
                    if key not in self.external_links:
                        self.external_links[key] = value
        
        # 更新fetch信息
        if other.fetched_at and (not self.fetched_at or other.fetched_at > self.fetched_at):
            self.fetched_at = other.fetched_at
    
    def __repr__(self) -> str:
        return f"AuthorProfile(id={self.member_id}, name={self.name}, source={self.source})"
    
    def __str__(self) -> str:
        return f"Author: {self.name} (ID: {self.member_id})\n" \
               f"  Avatar: {self.avatar_url[:50]}{'...' if len(self.avatar_url) > 50 else ''}\n" \
               f"  Background: {self.background_url[:50]}{'...' if len(self.background_url) > 50 else ''}\n" \
               f"  Comment: {self.comment[:100]}{'...' if len(self.comment) > 100 else ''}\n" \
               f"  Source: {self.source}"
