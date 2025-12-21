#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hatena Blog Content Fetcher
はてなブログの記事URLから内容を取得し、キャッシュするユーティリティ
"""
import logging
import requests
import re
import hashlib
import json
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HatenaBlogContentFetcher:
    """はてなブログの記事内容を取得・キャッシュするクラス"""
    
    def __init__(self, cache_dir: Optional[Path] = None, cache_ttl: int = 86400):
        """
        初期化
        
        Args:
            cache_dir: キャッシュディレクトリ（デフォルト: ./cache/hatena_content）
            cache_ttl: キャッシュの有効期限（秒、デフォルト: 86400 = 24時間）
        """
        self.cache_dir = cache_dir or Path(__file__).parent.parent.parent / 'cache' / 'hatena_content'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = cache_ttl
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_article_content(self, url: str, use_cache: bool = True) -> Optional[str]:
        """
        はてなブログの記事内容を取得
        
        Args:
            url: 記事URL
            use_cache: キャッシュを使用するか
        
        Returns:
            記事の本文（テキスト形式）、またはNone
        """
        # キャッシュを確認
        if use_cache:
            cached_content = self._get_cache(url)
            if cached_content:
                logger.debug(f"キャッシュから取得: {url[:60]}...")
                return cached_content
        
        # URLから記事内容を取得
        logger.info(f"はてなブログから記事を取得中: {url}")
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            # HTMLから本文を抽出
            content = self._extract_content_from_html(response.text)
            
            if content:
                # キャッシュに保存
                if use_cache:
                    self._save_cache(url, content)
                return content
            else:
                logger.warning(f"記事内容を抽出できませんでした: {url}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"記事取得エラー ({url}): {e}")
            return None
    
    def _extract_content_from_html(self, html: str) -> Optional[str]:
        """
        HTMLから本文を抽出
        
        Args:
            html: HTML内容
        
        Returns:
            抽出されたテキスト
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # はてなブログの記事本文は通常 <div class="entry-content"> に含まれる
            entry_content = soup.find('div', class_='entry-content')
            
            if not entry_content:
                # 代替案: <article> タグを探す
                entry_content = soup.find('article')
            
            if not entry_content:
                # さらに代替案: <div class="entry-body"> を探す
                entry_content = soup.find('div', class_='entry-body')
            
            if entry_content:
                # スクリプトとスタイルを削除
                for script in entry_content(['script', 'style']):
                    script.decompose()
                
                # テキストを取得
                text = entry_content.get_text(separator='\n', strip=True)
                
                # 複数の連続改行を単一の改行に統一
                text = re.sub(r'\n\n+', '\n\n', text)
                
                # 先頭と末尾の空白を削除
                text = text.strip()
                
                # 余分な空白を削除（ただし改行は保持）
                lines = [line.strip() for line in text.split('\n')]
                text = '\n'.join(lines)
                
                return text if text else None
            
            return None
            
        except Exception as e:
            logger.error(f"HTML抽出エラー: {e}")
            return None
    
    def _get_cache_key(self, url: str) -> str:
        """URLからキャッシュキーを生成"""
        return hashlib.md5(url.encode()).hexdigest()
    
    def _get_cache(self, url: str) -> Optional[str]:
        """キャッシュから内容を取得"""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            # キャッシュの有効期限を確認
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime > timedelta(seconds=self.cache_ttl):
                logger.debug(f"キャッシュの有効期限切れ: {url[:60]}...")
                cache_file.unlink()
                return None
            
            # キャッシュを読み込み
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('content')
        
        except Exception as e:
            logger.error(f"キャッシュ読み込みエラー: {e}")
            return None
    
    def _save_cache(self, url: str, content: str) -> None:
        """キャッシュに内容を保存"""
        cache_key = self._get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            data = {
                'url': url,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")
    
    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        try:
            for cache_file in self.cache_dir.glob('*.json'):
                cache_file.unlink()
            logger.info(f"キャッシュをクリアしました: {self.cache_dir}")
        except Exception as e:
            logger.error(f"キャッシュクリアエラー: {e}")


# グローバルインスタンス
_fetcher = None


def get_fetcher() -> HatenaBlogContentFetcher:
    """フェッチャーのシングルトンインスタンスを取得"""
    global _fetcher
    if _fetcher is None:
        _fetcher = HatenaBlogContentFetcher()
    return _fetcher


def fetch_article_content(url: str) -> Optional[str]:
    """
    はてなブログの記事内容を取得
    
    Args:
        url: 記事URL
    
    Returns:
        記事の本文（テキスト形式）
    """
    return get_fetcher().get_article_content(url)
