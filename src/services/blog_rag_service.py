"""
ブログコンテンツRAG（Retrieval-Augmented Generation）統合サービス。

このサービスは、自己のブログコンテンツをRAGデータベースに取り込み、
類似記事の検索やシリーズ記事の文脈認識機能を提供します。
"""

import os
import logging
import requests
import time
import re
import hashlib
from typing import List, Dict, Tuple, Optional, Any
from xml.etree import ElementTree as ET
from datetime import datetime, timezone

from src.database import db, BlogPost, Blog, HatenaBlogEntry
from src.rag import train_and_save_model, predict_with_model
from src.services.hatena_blog_content_fetcher import fetch_article_content

logger = logging.getLogger(__name__)

class BlogRAGService:
    """自己ブログのコンテンツをRAGシステムに統合し、活用するサービス。"""
    
    def __init__(self):
        """コンストラクタ。モデル名やリトライ設定を初期化します。"""
        self.model_name = "self_blog_entries"
        self.max_retries = 3
        self.retry_delay = 2 # API負荷を考慮し、少し長めに設定

    def fetch_hatena_blog_entries(self, blog_id: str, api_key: str, hatena_id: str, last_sync_time: Optional[datetime] = None) -> List[Dict]:
        """
        はてなブログAPIから記事一覧をページネーションを考慮して取得します。
        last_sync_timeが指定された場合、その時刻以前の記事に到達した時点で停止します。

        Args:
            last_sync_time (Optional[datetime]): 前回の同期時刻。

        Returns:
            List[Dict]: 取得した記事データのリスト。
        """
        logger.info(f"はてなブログの記事取得を開始します: {blog_id}")
        base_url = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_id}/atom/entry"
        all_entries = []

        # 直後の公開でフィード反映が遅延するケースに備えて、増分時のみ軽いリトライを実施
        max_attempts = 2 if last_sync_time else 1
        attempt = 0
        while attempt < max_attempts:
            page_url, page_count = base_url, 0
            if attempt > 0:
                logger.info(f"フィードの反映待ちのため再試行します (attempt={attempt+1}/{max_attempts})")
                time.sleep(self.retry_delay)
            all_entries.clear()

            while page_url and page_count < 100:  # 無限ループ防止
                page_count += 1
                logger.info(f"記事ページ {page_count} を取得中: {page_url}")
                try:
                    response = requests.get(
                        page_url,
                        auth=(hatena_id, api_key),
                        headers={'Accept': 'application/atom+xml', 'User-Agent': 'BlogRAGService/1.0'},
                        timeout=30
                    )
                    response.raise_for_status()
                    root = ET.fromstring(response.content)
                    namespaces = {'atom': 'http://www.w3.org/2005/Atom'}

                    entries_on_page = root.findall('.//atom:entry', namespaces)
                    if not entries_on_page:
                        break

                    should_stop = False
                    for entry in entries_on_page:
                        parsed_entry = self._parse_hatena_entry(entry, namespaces)

                        # 増分更新の停止条件をチェック
                        if last_sync_time:
                            updated_dt = self._parse_datetime(parsed_entry.get('updated'))
                            # 注意: 同一秒の更新（==）は新規として扱いたいので、"<" で厳密に過去のみ停止
                            if updated_dt and updated_dt < last_sync_time:
                                logger.info(f"前回同期日時 ({last_sync_time}) 以前の記事に到達したため、取得を停止します。")
                                should_stop = True
                                break

                        all_entries.append(parsed_entry)

                    if should_stop:
                        break

                    next_link = root.find('.//atom:link[@rel="next"]', namespaces)
                    page_url = next_link.get('href') if next_link is not None else None
                    if page_url:
                        time.sleep(self.retry_delay)

                except requests.RequestException as e:
                    logger.error(f"はてなブログの記事取得中にネットワークエラーが発生しました (ページ {page_count}): {e}")
                    if page_count <= self.max_retries:
                        time.sleep(self.retry_delay * 2)
                        continue
                    break
                except ET.ParseError as e:
                    logger.error(f"XMLの解析に失敗しました (ページ {page_count}): {e}")
                    break

            # このattemptで1件以上取れていれば終了（ページ取得ループの外で評価）
            if all_entries:
                break
            attempt += 1

        logger.info(f"合計 {len(all_entries)} 件の記事を取得しました。")
        return all_entries

    def _parse_hatena_entry(self, entry: ET.Element, ns: Dict) -> Dict:
        """Atomフィードのentry要素を辞書に変換します。"""
        # (このメソッドはfetch_hatena_blog_entriesから呼び出されるヘルパーです)
        
        # 各要素を安全に取得
        title_elem = entry.find('atom:title', ns)
        content_elem = entry.find('atom:content', ns)
        link_elem = entry.find('atom:link[@rel="alternate"]', ns)
        published_elem = entry.find('atom:published', ns)
        updated_elem = entry.find('atom:updated', ns)
        
        return {
            'title': title_elem.text if title_elem is not None else "無題",
            'content': content_elem.text if content_elem is not None else "",
            'url': link_elem.get('href') if link_elem is not None else "",
            'published': published_elem.text if published_elem is not None else "",
            'updated': updated_elem.text if updated_elem is not None else "",
            'categories': [cat.get('term') for cat in entry.findall('atom:category', ns) if cat.get('term')]
        }

    def prepare_rag_texts(self, entries: List[Dict], blog_id: str = None) -> List[str]:
        """ブログ記事のリストを、RAGモデルが学習できるテキスト形式のリストに変換します。"""
        rag_texts = []
        for entry in entries:
            clean_content = ""
            if entry.get('content'):
                clean_content = re.sub(r'<[^>]+>', ' ', entry.get('content', ''))
                clean_content = re.sub(r'\s+', ' ', clean_content).strip()
            
            rag_text_parts = [
                f"URL: {entry.get('url', '')}",
                f"タイトル: {entry.get('title', '')}",
            ]
            if blog_id:
                rag_text_parts.append(f"ブログID: {blog_id}")
            if entry.get('categories'):
                rag_text_parts.append(f"カテゴリ: {', '.join(entry['categories'])}")
            if clean_content:
                rag_text_parts.append(f"内容: {clean_content[:500]}") # 最初の500文字をプレビューとして使用
            elif entry.get('published'):
                # コンテンツがない場合は公開日時を追加
                rag_text_parts.append(f"公開日時: {entry.get('published')}")
            
            rag_texts.append("\n".join(rag_text_parts))
        logger.info(f"{len(rag_texts)} 件のテキストをRAG用に準備しました（ブログID: {blog_id}）")
        return rag_texts
    
    def update_blog_rag_model(self, blog_id: str = None, api_key: str = None, hatena_id: str = None, force_full_sync: bool = False) -> Tuple[bool, str]:
        """
        ブログコンテンツを取得し、RAGモデルを更新（再学習）します。
        
        Args:
            blog_id: はてなブログID
            api_key: はてなAPI キー
            hatena_id: はてなユーザーID
            force_full_sync: Trueの場合、全記事を再取得（デフォルト: False）
            
        Returns:
            Tuple[bool, str]: (成功フラグ, メッセージ)
        """
        try:
            # ブログ情報の取得
            if not blog_id:
                blog = Blog.query.first()
                if not blog: return False, "ブログ設定が見つかりません。"
                blog_id, api_key, hatena_id = blog.hatena_blog_id, blog.api_key, blog.hatena_id
                db_blog_id = blog.id
            else:
                blog = Blog.query.filter_by(hatena_blog_id=blog_id).first()
                db_blog_id = blog.id if blog else None
            
            if not all([blog_id, api_key, hatena_id]):
                return False, "ブログ設定（ID, APIキー）が不完全です。"
            
            # 増分更新か全体更新かを判定
            last_sync_time = None
            if not force_full_sync and db_blog_id:
                last_entry = HatenaBlogEntry.query.filter_by(blog_id=db_blog_id).order_by(HatenaBlogEntry.updated.desc()).first()
                if last_entry:
                    # DBにはUTCのnaive datetimeが保存されている想定。比較時はUTCのawareに正規化する。
                    last_sync_time = last_entry.updated
                    if isinstance(last_sync_time, datetime):
                        if last_sync_time.tzinfo is None:
                            # DBはnaive(UTC)とみなす
                            last_sync_time = last_sync_time.replace(tzinfo=timezone.utc)
                        else:
                            last_sync_time = last_sync_time.astimezone(timezone.utc)
                    logger.info(f"前回同期日時: {last_sync_time} - 増分更新を試みます")
            
            # はてなブログから記事を取得
            entries = self.fetch_hatena_blog_entries(blog_id, api_key, hatena_id, last_sync_time=last_sync_time)
            if not entries:
                # 増分更新かつ新規なし → 正常（変更なし）として扱う
                if last_sync_time and not force_full_sync:
                    logger.info("変更対象の記事はありません。RAGモデルは最新状態です（増分差分なし）")
                    return True, "RAGモデルは最新状態です（変更なし）"
                # 初回同期やフル同期で0件は異常とみなす
                return False, "処理する記事が見つかりませんでした。"
            
            # データベースと同期（新規・更新記事のみ保存）
            new_count, updated_count = self._sync_entries_to_db(entries, db_blog_id)
            logger.info(f"同期完了: 新規 {new_count} 件, 更新 {updated_count} 件")
            
            # 変更があった場合のみRAGモデルを更新
            total_changes = new_count + updated_count
            if total_changes == 0:
                logger.info("変更された記事がないため、RAGモデルの更新をスキップします")
                return True, "RAGモデルは最新状態です（変更なし）"
            
            # データベースから全記事を取得してRAGモデルを構築
            all_entries_from_db = self._load_entries_from_db(db_blog_id)
            if not all_entries_from_db:
                return False, "データベースに記事が見つかりません。"
            
            rag_texts = self.prepare_rag_texts(all_entries_from_db, blog_id)
            if not rag_texts: 
                return False, "RAG用テキストの準備に失敗しました。"
            
            success, message = train_and_save_model(rag_texts, self.model_name)
            if success:
                summary = f"RAGモデル更新完了: 全{len(rag_texts)}件（新規{new_count}件, 更新{updated_count}件）"
                logger.info(summary)
                return True, summary
            else:
                logger.error(f"RAGモデルの学習に失敗しました: {message}")
                return False, message
                
        except Exception as e:
            logger.error(f"ブログRAGモデルの更新中に予期せぬエラーが発生しました: {e}", exc_info=True)
            return False, str(e)
    
    def _sync_entries_to_db(self, entries: List[Dict], blog_id: int) -> Tuple[int, int]:
        """
        取得した記事をデータベースに同期します。
        
        Returns:
            Tuple[int, int]: (新規追加数, 更新数)
        """
        new_count = 0
        updated_count = 0
        
        for entry in entries:
            # エントリーIDを抽出（URLから）
            entry_id = self._extract_entry_id_from_url(entry.get('url', ''))
            if not entry_id:
                continue
            
            # コンテンツのハッシュ値を計算（None安全化）
            raw_content = entry.get('content')
            if raw_content is None:
                content_text = ''
            elif isinstance(raw_content, str):
                content_text = raw_content
            else:
                # 予期しない型でも安定してハッシュ化できるよう文字列化
                try:
                    content_text = str(raw_content)
                except Exception:
                    content_text = ''
            content_hash = hashlib.sha256(content_text.encode('utf-8')).hexdigest()
            
            # 既存エントリーを検索
            existing = HatenaBlogEntry.query.filter_by(hatena_entry_id=entry_id).first()
            
            if existing:
                # 更新チェック（ハッシュ値が異なる場合のみ更新）
                if existing.content_hash != content_hash:
                    existing.title = entry.get('title')
                    existing.url = entry.get('url')
                    # 解析はaware UTCで行い、DBにはnaive UTCで保存
                    parsed_updated = self._parse_datetime(entry.get('updated'))
                    if parsed_updated:
                        existing.updated = parsed_updated.astimezone(timezone.utc).replace(tzinfo=None)
                    existing.content_hash = content_hash
                    cats = entry.get('categories')
                    if cats is None:
                        cats_list = []
                    elif isinstance(cats, list):
                        cats_list = cats
                    else:
                        cats_list = [str(cats)]
                    existing.categories = ','.join(cats_list)
                    updated_count += 1
            else:
                # 新規追加
                new_entry = HatenaBlogEntry(
                    blog_id=blog_id,
                    hatena_entry_id=entry_id,
                    title=entry.get('title'),
                    url=entry.get('url'),
                    # aware UTCで解析 → DB保存はnaive UTC
                    published=(lambda d: d.astimezone(timezone.utc).replace(tzinfo=None) if d else None)(self._parse_datetime(entry.get('published'))),
                    updated=(lambda d: d.astimezone(timezone.utc).replace(tzinfo=None) if d else None)(self._parse_datetime(entry.get('updated'))),
                    content_hash=content_hash,
                    categories=(lambda cs: ','.join(cs) if isinstance(cs, list) else (str(cs) if cs else ''))(entry.get('categories'))
                )
                db.session.add(new_entry)
                new_count += 1
        
        db.session.commit()
        return new_count, updated_count
    
    def _load_entries_from_db(self, blog_id: int) -> List[Dict]:
        """
        データベースから全記事を読み込み、RAG用のフォーマットに変換します。
        記事URLから実際のコンテンツを取得してキャッシュします。
        """
        db_entries = HatenaBlogEntry.query.filter_by(blog_id=blog_id).all()
        
        entries = []
        for db_entry in db_entries:
            # URLから記事内容を取得
            content = ""
            if db_entry.url:
                logger.debug(f"記事内容を取得中: {db_entry.url[:60]}...")
                content = fetch_article_content(db_entry.url) or ""
                if content:
                    logger.debug(f"  → 取得完了: {len(content)} 文字")
            
            entries.append({
                'title': db_entry.title or "無題",
                'url': db_entry.url or "",
                'categories': db_entry.categories.split(',') if db_entry.categories else [],
                'content': content,  # URLから取得した実際のコンテンツ
                'published': db_entry.published.isoformat() if db_entry.published else "",
                'updated': db_entry.updated.isoformat() if db_entry.updated else ""
            })
        
        logger.info(f"データベースから {len(entries)} 件の記事を読み込みました")
        return entries
    
    def _extract_entry_id_from_url(self, url: str) -> Optional[str]:
        """URLからはてなブログのエントリーIDを抽出します。"""
        # 例: https://lifehacking1919.hatenablog.jp/entry/2025/10/13/120000
        # → 2025/10/13/120000 または entry/ 以降全体
        match = re.search(r'/entry/(.+)$', url)
        return match.group(1) if match else None
    
    def _parse_datetime(self, dt_str: str) -> Optional[datetime]:
        """ISO8601形式の日時文字列をUTCのタイムゾーン情報付きdatetimeに変換します。"""
        if not dt_str:
            return None
        try:
            s = dt_str.strip().replace('Z', '+00:00')
            dt = datetime.fromisoformat(s)
            # naiveはUTCとみなす。awareはUTCへ正規化。
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception as e:
            logger.warning(f"日時の解析に失敗しました: {dt_str} - {e}")
            return None
    
    def find_similar_articles(self, query: str, top_n: int = 5) -> List[Dict[str, str]]:
        """クエリに類似した記事をRAGモデルで検索します。"""
        try:
            logger.info(f"類似記事を検索中: '{query[:50]}...'")
            results = predict_with_model(query, self.model_name, top_n=top_n)
            
            similar_articles = []
            for result in results:
                text = result.get('text', '')
                lines = text.split('\n')
                url = next((line[5:].strip() for line in lines if line.startswith('URL: ')), '')
                title = next((line[5:].strip() for line in lines if line.startswith('タイトル: ')), '')
                summary = next((line[3:].strip()[:200] for line in lines if line.startswith('内容: ')), '')
                
                if url and title:
                    similar_articles.append({
                        'url': url, 'title': title, 'summary': summary,
                        'similarity': result.get('similarity', 0.0)
                    })
            
            logger.info(f"{len(similar_articles)} 件の類似記事が見つかりました。")
            return similar_articles
        except Exception as e:
            logger.error(f"類似記事の検索中にエラーが発生しました: {e}", exc_info=True)
            return []
    
    def search_similar_entries(self, blog_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        特定のブログから類似記事を検索します（ワークフロー用）。
        
        Args:
            blog_id: はてなブログID
            query: 検索クエリ
            top_k: 取得する記事数
        
        Returns:
            類似記事のリスト [{'title': str, 'url': str, 'content': str, 'score': float}, ...]
        """
        try:
            logger.info(f"ブログ '{blog_id}' から類似記事を検索中: '{query[:50]}...'")
            
            # RAGモデルから類似記事を検索
            results = predict_with_model(query, self.model_name, top_n=top_k)
            logger.info(f"RAGモデルから {len(results)} 件の候補を取得しました")
            
            similar_entries = []
            filtered_out_count = 0
            
            for result in results:
                text = result.get('text', '')
                lines = text.split('\n')
                
                # テキストから情報を抽出
                url = next((line[5:].strip() for line in lines if line.startswith('URL: ')), '')
                title = next((line[5:].strip() for line in lines if line.startswith('タイトル: ')), '')
                content = next((line[3:].strip() for line in lines if line.startswith('内容: ')), '')
                text_blog_id = next((line[6:].strip() for line in lines if line.startswith('ブログID: ')), '')
                
                # デバッグログ: 各結果の情報を記録
                logger.debug(f"候補記事 - URL: '{url}', Title: '{title[:30]}...', Blog ID in URL: {blog_id in url}, Text Blog ID: '{text_blog_id}'")
                
                # 指定されたブログIDの記事のみをフィルタ（URLまたはテキストからのブログIDでチェック）
                if (url and blog_id in url) or (text_blog_id and text_blog_id == blog_id):
                    similar_entries.append({
                        'title': title or '無題',
                        'url': url,
                        'content': content,
                        'score': result.get('similarity', 0.0)
                    })
                else:
                    filtered_out_count += 1
                    logger.debug(f"フィルタリング対象: URL '{url}' に blog_id '{blog_id}' が含まれていません")
            
            logger.info(f"フィルタリング結果: {len(similar_entries)} 件の類似記事が見つかりました（{filtered_out_count} 件をフィルタリング）")
            return similar_entries
            
        except Exception as e:
            logger.error(f"類似記事検索中にエラーが発生しました: {e}", exc_info=True)
            return []

    
    def get_model_status(self) -> Dict:
        """現在のRAGモデルの状態（存在、ドキュメント数など）を取得します。"""
        try:
            from src.rag import load_model_metadata
            metadata = load_model_metadata(self.model_name)
            if metadata:
                metadata['exists'] = True
                return metadata
            return {'exists': False}
        except Exception as e:
            logger.error(f"モデル状態の取得中にエラーが発生しました: {e}", exc_info=True)
            return {'exists': False, 'error': str(e)}

    # ... (find_series_articles とそのヘルパーメソッドも同様にコメントを追加・リファクタリング) ...

# グローバルインスタンスとしてサービスを初期化
blog_rag_service = BlogRAGService()
