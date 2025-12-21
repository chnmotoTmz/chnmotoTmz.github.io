"""
Web検索サービス。

ddgs ライブラリを利用して、指定されたクエリでWeb検索を実行し、
関連情報を取得する機能を提供します。
"""

import logging
import os
import time
from typing import List, Dict, Optional, Any
from ddgs import DDGS

logger = logging.getLogger(__name__)

class SearchService:
    """
    ddgs ライブラリをラップし、Web検索機能を提供します。
    APIの利用制限によるクールダウンを管理します。
    """

    # API制限エラーが発生した際に、サービスを一時停止するためのクールダウンタイムスタンプ。
    # クラス変数としてプロセス内で共有されます。
    _cooldown_until: float = 0.0

    def __init__(self):
        """
        SearchServiceを初期化します。
        ddgs ライブラリは無料で利用可能なので、常に有効化を試みます。
        """
        # ddgs ライブラリは無料で利用可能
        self.enabled = True

        # 現在時刻がクールダウン期間中であれば、サービスを一時的に無効化
        now = time.time()
        if now < SearchService._cooldown_until:
            self.enabled = False
            remaining = int(SearchService._cooldown_until - now)
            logger.warning(f"DuckDuckGo Search APIは一時停止中です（レート制限クールダウン: 残り {remaining}s）")
        else:
            self.enabled = True
            logger.info("DuckDuckGo Search サービスが初期化されました。")
    
    def search_web(self, query: str, num_results: int = 3) -> List[Dict[str, str]]:
        """
        指定されたクエリでWeb検索を実行します。

        Args:
            query (str): 検索クエリ。
            num_results (int): 取得する結果の数（最大10件）。

        Returns:
            List[Dict[str, str]]: 整形された検索結果のリスト。各要素はtitle, link, snippet, displayLinkを含みます。
        """
        if not self.enabled:
            logger.warning("DuckDuckGo Search APIが無効のため、検索をスキップします。")
            return []
        
        try:
            logger.info(f"🔍 Web検索開始: クエリ「{query}」, 最大{num_results}件")
            
            # ddgs ライブラリを使用した検索
            with DDGS(timeout=20) as ddgs:
                results = list(ddgs.text(
                    query,                 # 第1引数: 検索クエリ
                    region='jp-jp',        # 日本のリージョン
                    safesearch='off',      # セーフサーチOFF
                    timelimit=None,        # 期間指定なし
                    max_results=num_results
                ))
            
            # レスポンスを整形
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'title': result.get('title', ''),
                    'link': result.get('href', ''),
                    'snippet': result.get('body', '')[:200] + '...' if len(result.get('body', '')) > 200 else result.get('body', ''),
                    'displayLink': result.get('href', '')
                })
            
            logger.info(f"✅ Web検索が完了しました。クエリ「{query}」で{len(formatted_results)}件の結果を取得。")
            return formatted_results
            
        except Exception as e:
            # レート制限やその他のエラー
            error_msg = str(e).lower()
            if 'ratelimit' in error_msg or '202' in error_msg:
                cooldown_seconds = int(os.getenv('SEARCH_API_COOLDOWN_SECONDS', '300'))  # デフォルト5分
                SearchService._cooldown_until = time.time() + cooldown_seconds
                self.enabled = False
                logger.warning(f"⚠️ Web検索でレート制限エラー。{cooldown_seconds}秒間、機能を自動で無効化します。")
            else:
                logger.error(f"❌ Web検索中にエラーが発生しました: {e}", exc_info=True)
            return []

    def self_check(self) -> Dict[str, Any]:
        """
        サービスの自己診断を実行します。
        クールダウン状態と実際のAPI呼び出しの到達性を確認します。

        Returns:
            Dict[str, Any]: 診断結果を含む辞書。
        """
        now = time.time()
        cooldown_remaining = int(max(0, SearchService._cooldown_until - now))

        if cooldown_remaining > 0:
            logger.warning(f"[SearchService] Self-check: クールダウン中です (残り{cooldown_remaining}秒)")
            return {'enabled': False, 'cooldown_remaining': cooldown_remaining, 'http_ok': False, 'reason': 'cooldown'}

        # 実際のAPI呼び出しによる到達性確認
        try:
            test_query = os.getenv('SEARCH_API_SELFTEST_QUERY', 'Python')
            results = self.search_web(test_query, num_results=1)

            if isinstance(results, list):
                # クールダウンが作動した場合、enabledはFalseになっている
                if not self.enabled:
                    return {'enabled': False, 'cooldown_remaining': int(max(0, SearchService._cooldown_until - now)), 'http_ok': False, 'reason': 'rate_limited'}

                logger.info(f"[SearchService] Self-check: OK (items={len(results)})")
                return {'enabled': True, 'cooldown_remaining': 0, 'http_ok': True, 'items': len(results), 'reason': 'ok'}
            else:
                # 予期しない戻り値の型
                return {'enabled': False, 'cooldown_remaining': 0, 'http_ok': False, 'reason': 'unexpected_return_type'}
        except Exception as e:
            logger.error(f"[SearchService] Self-check中に例外が発生しました: {e}", exc_info=True)
            return {'enabled': False, 'cooldown_remaining': 0, 'http_ok': False, 'reason': 'exception'}
    
    def search_related_info(self, topic: str) -> Optional[str]:
        """
        指定されたトピックに関連する情報をWeb検索し、Markdown形式の要約を生成します。
        
        Args:
            topic (str): 検索トピック。
        
        Returns:
            Optional[str]: 関連情報の要約。検索結果がない場合はNone。
        """
        if not self.enabled:
            return None
        
        try:
            results = self.search_web(topic, num_results=3)
            
            if not results:
                logger.info(f"関連情報検索: クエリ「{topic}」での検索結果はありませんでした。")
                return None
            
            # 結果をMarkdown形式で整形
            summary_parts = [f"## 📚 「{topic}」に関する関連情報"]
            for i, result in enumerate(results, 1):
                summary_parts.append(f"### {i}. {result['title']}")
                summary_parts.append(f"> {result['snippet']}")
                summary_parts.append(f"出典: [{result['displayLink']}]({result['link']})\n")
            
            return "\n".join(summary_parts)
            
        except Exception as e:
            logger.error(f"関連情報の検索中にエラーが発生しました: {e}", exc_info=True)
            return None
    
    def enhance_content_with_search(self, content: str, search_queries: List[str]) -> str:
        """
        既存のコンテンツに、複数の検索クエリから得られた情報を追記します。
        
        Args:
            content (str): 元のコンテンツ。
            search_queries (List[str]): 検索クエリのリスト。
        
        Returns:
            str: 検索情報が追記されたコンテンツ。
        """
        if not self.enabled or not search_queries:
            return content
        
        try:
            search_info_parts = []
            logger.info(f"コンテンツ拡張のため、{len(search_queries)}件のクエリで検索を開始します。")
            
            for query in search_queries:
                info = self.search_related_info(query)
                if info:
                    search_info_parts.append(info)
                    logger.info(f"クエリ「{query}」で関連情報を取得しました。")
            
            if search_info_parts:
                enhanced_content = content + "\n\n---\n\n" + "\n\n".join(search_info_parts)
                logger.info(f"{len(search_info_parts)}件の関連情報をコンテンツに追加しました。")
                return enhanced_content
            
            logger.info("関連情報は見つからなかったため、コンテンツは変更されませんでした。")
            return content
            
        except Exception as e:
            logger.error(f"コンテンツの拡張中にエラーが発生しました: {e}", exc_info=True)
            return content
