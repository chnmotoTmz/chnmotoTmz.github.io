"""
動画メッセージハンドラ。

LINEから受信した動画メッセージイベントを処理します。
動画のダウンロード、外部サービスへのアップロード、AIによる動画解析、
データベースへの保存、バッチ処理へのキューイングまでの一連の流れを担当します。
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import requests
from sqlalchemy.exc import SQLAlchemyError

from src.database import db, User, Message, Asset
from src.services.line_service import LineService
from src.services.imgur_service import ImgurService
from src.services.gemini_service import GeminiService
from src.services.batch_service import BatchService

logger = logging.getLogger(__name__)

class VideoHandler:
    """LINEからの動画メッセージイベントを処理するクラス。"""

    def __init__(self, line_service: LineService, imgur_service: ImgurService, batch_service: BatchService):
        """
        コンストラクタ。依存するサービスを注入します。

        Args:
            line_service: LINE API連携サービス。
            imgur_service: Imgur API連携サービス（将来的に動画対応も検討）。
            gemini_service: Gemini AI連携サービス（動画解析機能を含む）。
            batch_service: バッチ処理サービス。
        """
        self.line_service = line_service
        self.imgur_service = imgur_service
        # GeminiServiceはblog_configに依存するため、handleメソッド内でインスタンス化します。
        self.batch_service = batch_service

    def handle(self, event: Dict[str, Any], context: Dict[str, Any] = None):
        """
        動画メッセージイベントを処理するメインのメソッド。

        Args:
            event (Dict[str, Any]): LINEから受信したイベントペイロード。
            context (Dict[str, Any], optional): EventRouterから渡されるコンテキスト。
                                                'local_path'が含まれていることを期待します。
        """
        # チャンネル情報を取得
        channel_info = event.get('channel_info', {})
        channel_id = channel_info.get('channel_id')
        blog_name = channel_info.get('blog_name', 'Unknown')
        channel_id_for_log = channel_id or 'Unknown'

        line_user_id = event.get('source', {}).get('userId')
        line_message_id = event.get('message', {}).get('id')

        logger.info(
            "動画メッセージ処理開始: チャンネル=%s (ID: %s), ユーザー=%s",
            blog_name,
            channel_id_for_log,
            line_user_id,
        )

        if not line_user_id or not line_message_id:
            logger.warning("VideoHandler: イベント情報にユーザーIDまたはメッセージIDがありません。処理をスキップします。")
            return

        context = context or {}

        try:
            # ステップ1: コンテンツをダウンロード（時間的制約が厳しいため最優先）
            content_provider = context.get('content_provider', {}) or {}
            provider_type = content_provider.get('type', 'line')

            if provider_type == 'line':
                local_path = self.line_service.download_content(line_message_id, content_type='video', timeout=60)
            else:
                local_path = self._download_external_asset(content_provider, asset_type='video')

            if not local_path or not os.path.exists(local_path):
                raise IOError(f"メッセージID {line_message_id} の動画ダウンロードに失敗しました。")

            # ステップ2: ユーザー情報を確認または作成
            user = self._get_or_create_user(line_user_id)

            # ステップ3: 動画解析はワークフローで実施するためスキップ
            description = "動画が送信されました。解析はワークフローで実施されます。"

            # ステップ4: データベースにメッセージとアセット情報を保存
            new_message = self._save_message_and_asset(
                line_message_id, user.id, local_path, description
            )

            # ステップ4: バッチ処理へのキューイング
            self.batch_service.add_message(user.line_user_id, {
                'id': new_message.id,
                'message_type': 'video',
                'channel_id': channel_id
            })

            db.session.commit()
            logger.info(f"動画メッセージ (DB ID: {new_message.id}) をユーザー (ID: {user.id}) から正常に処理し、キューに追加しました。")

        except Exception as e:
            db.session.rollback()
            logger.error(f"動画メッセージ処理中にエラーが発生しました (Msg ID: {line_message_id}): {e}", exc_info=True)

    def _get_or_create_user(self, line_user_id: str) -> User:
        """ユーザーIDを基にユーザーを取得または新規作成します。"""
        user = User.query.filter_by(line_user_id=line_user_id).first()
        if not user:
            profile = self.line_service.get_user_profile(line_user_id)
            user = User(line_user_id=line_user_id, display_name=profile.get('displayName'))
            db.session.add(user)
            db.session.flush()
        return user

    def _analyze_video(self, local_path: str, gemini_service: GeminiService) -> str:
        """
        動画ファイルを解析して説明文を生成します。
        
        将来的にはGemini APIの動画解析機能を使用する予定ですが、
        現時点では基本的なメタデータのみを記録します。
        
        Args:
            local_path: ローカルに保存された動画ファイルのパス
            gemini_service: GeminiServiceのインスタンス
            
        Returns:
            動画の説明文
        """
        import os
        
        try:
            # 動画ファイルの基本情報を取得
            file_size = os.path.getsize(local_path)
            file_name = os.path.basename(local_path)
            
            # 現時点ではシンプルな説明文を返す
            # TODO: Gemini API の動画解析機能を実装
            description = f"動画ファイル: {file_name} (サイズ: {file_size / 1024 / 1024:.2f} MB)"
            
            logger.info(f"動画ファイル情報を取得: {description}")
            return description
            
        except Exception as e:
            logger.error(f"動画解析中にエラーが発生: {e}", exc_info=True)
            return "動画が送信されました"

    def _save_message_and_asset(
        self, line_message_id: str, user_id: int, local_path: str, description: str
    ) -> Message:
        """メッセージとアセットの情報をデータベースにアトミックに保存します。"""
        new_message = Message(
            line_message_id=line_message_id,
            user_id=user_id,
            message_type='video'
        )
        db.session.add(new_message)
        db.session.flush()

        new_asset = Asset(
            message_id=new_message.id,
            asset_type='video',
            local_path=local_path,
            external_url='',  # 動画は現時点では外部アップロードなし
            description=description
        )
        db.session.add(new_asset)
        return new_message

    def _download_external_asset(self, content_provider: Dict[str, Any], asset_type: str) -> str:
        """LINE以外のコンテンツプロバイダーが提供するURLからメディアをダウンロードします。"""
        url_key = 'originalContentUrl' if asset_type == 'video' else 'previewImageUrl'
        url = content_provider.get('originalContentUrl') or content_provider.get(url_key)
        if not url:
            raise ValueError("外部コンテンツのURLが見つかりませんでした。")

        logger.info(f"外部URLから{asset_type}をダウンロードします: {url}")

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        suffix = '.mp4' if asset_type == 'video' else '.bin'
        filename = f"external_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
        save_dir = Path(self.line_service.upload_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / filename

        with open(file_path, 'wb') as f:
            f.write(response.content)

        return str(file_path)
