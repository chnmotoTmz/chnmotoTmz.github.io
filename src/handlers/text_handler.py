"""
テキストメッセージハンドラ。

LINEから受信したテキストメッセージイベントを処理します。
ユーザー情報を確認・作成し、メッセージをデータベースに保存後、
バッチ処理サービスに処理をキューイングします。
"""
import logging
import re
import os
import subprocess
from typing import Dict, Any
from sqlalchemy.exc import SQLAlchemyError

from src.database import db, User, Message
from src.services.batch_service import BatchService
from src.services.line_service import LineService

logger = logging.getLogger(__name__)

class TextHandler:
    """LINEからのテキストメッセージイベントを処理するクラス。"""

    def __init__(self, line_service: LineService, batch_service: BatchService):
        """
        コンストラクタ。依存するサービスを注入します。

        Args:
            line_service (LineService): LINE APIとの連携サービス。
            batch_service (BatchService): メッセージのバッチ処理サービス。
        """
        self.line_service = line_service
        self.batch_service = batch_service

    def _get_youtube_content(self, url: str) -> str:
        """
        YouTubeのURLからタイトルと説明文をAPIで取得する（字幕なし・最小バージョン）。
        """
        from googleapiclient.discovery import build
        from urllib.parse import urlparse, parse_qs
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            logger.error("YouTube APIキーが設定されていません")
            return f"[YouTubeリンク]: {url}"

        # Video ID 抽出
        try:
            parsed = urlparse(url)
            if 'youtu.be' in parsed.netloc:
                video_id = parsed.path.lstrip('/')
            else:
                query_params = parse_qs(parsed.query)
                video_id = query_params.get("v", [None])[0]
        except Exception:
            logger.error("YouTube Video ID の抽出に失敗しました")
            return f"[YouTubeリンク]: {url}"

        if not video_id:
            logger.error(f"YouTube Video ID が見つかりません: {url}")
            return f"[YouTubeリンク]: {url}"

        try:
            youtube = build("youtube", "v3", developerKey=api_key)
            response = youtube.videos().list(
                part="snippet",
                id=video_id
            ).execute()

            if not response["items"]:
                return f"[YouTubeリンク]: {url}"

            snippet = response["items"][0]["snippet"]
            title = snippet.get("title", "")
            description = snippet.get("description", "")

            combined_content = (
                f"[YouTubeリンク]: {url}\n\n"
                f"Title: {title}\n\n"
                f"Description:\n{description}\n"
            )
            return combined_content

        except Exception as e:
            logger.error(f"YouTube Data API取得中にエラーが発生: {e}")
            return f"[YouTubeリンク]: {url}"


    def handle(self, event: Dict[str, Any]):
        """
        テキストメッセージイベントを処理するメインのメソッド。

        Args:
            event (Dict[str, Any]): LINEから受信したイベントペイロード。
        """
        # チャンネル情報を取得
        channel_info = event.get('channel_info', {})
        channel_id = channel_info.get('channel_id')
        blog_name = channel_info.get('blog_name', 'Unknown')
        channel_id_for_log = channel_id or 'Unknown'

        line_user_id = event.get('source', {}).get('userId')
        message_info = event.get('message', {})
        line_message_id = message_info.get('id')
        text_content = message_info.get('text', '')

        logger.info(
            "テキストメッセージ処理開始: チャンネル=%s (ID: %s), ユーザー=%s",
            blog_name,
            channel_id_for_log,
            line_user_id,
        )

        if not line_user_id or not line_message_id:
            logger.warning("TextHandler: イベント情報にユーザーIDまたはメッセージIDがありません。処理をスキップします。")
            return


        # すべてのURLを抽出
        url_pattern = r'(https?://[\w\-._~:/?#\[\]@!$&\'()*+,;=%]+)'
        urls_found = re.findall(url_pattern, text_content)
        if urls_found:
            logger.info(f"検出されたURLリスト: {urls_found}")
        else:
            logger.info("メッセージ内にURLは検出されませんでした。")

        # YouTube URLが含まれていれば個別処理
        for url in urls_found:
            youtube_pattern = r'(?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.be)/'
            if re.match(youtube_pattern, url):
                logger.info(f"YouTubeのURLを検出: {url}。コンテンツを取得します。")
                text_content = self._get_youtube_content(url)
                break  # 1つ目のみ処理（複数対応は要件次第）


        try:
            # ステップ1: ユーザー情報をデータベースで確認、存在しなければ新規作成
            user = User.query.filter_by(line_user_id=line_user_id).first()
            if not user:
                profile = self.line_service.get_user_profile(line_user_id)
                user = User(line_user_id=line_user_id, display_name=profile.get('displayName'))
                db.session.add(user)
                db.session.flush()  # user.id を確定させるため

            # ステップ2: 受信したメッセージをデータベースに保存
            new_message = Message(
                line_message_id=line_message_id,
                user_id=user.id,
                message_type='text',
                content=text_content
            )
            db.session.add(new_message)
            db.session.commit()

            # ステップ2.5: 受信時の自動返信は行わない（記事公開時またはエラー時のみ通知）
            # ここでは何も送信しない

            # ステップ3: バッチ処理サービスにメッセージIDをキューイング
            self.batch_service.add_message(user.line_user_id, {
                'id': new_message.id,
                'message_type': 'text',
                'channel_id': channel_id
            })
            
            logger.info(f"テキストメッセージ (ID: {new_message.id}) をLINEユーザー (ID: {line_user_id}) から正常に処理し、キューに追加しました。")

        except SQLAlchemyError as e:
            # データベース関連のエラーが発生した場合はロールバック
            db.session.rollback()
            logger.error(f"テキストメッセージ処理中にデータベースエラーが発生しました (Msg ID: {line_message_id}): {e}", exc_info=True)
        except Exception as e:
            # その他の予期せぬエラー
            db.session.rollback()
            logger.error(f"テキストメッセージ処理中に予期せぬエラーが発生しました (Msg ID: {line_message_id}): {e}", exc_info=True)
