"""
画像メッセージハンドラ。

LINEから受信した画像メッセージイベントを処理します。
画像のダウンロード、外部サービスへのアップロード、AIによる画像解析、
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
from src.services.claude_service import ClaudeService
from src.services.batch_service import BatchService

logger = logging.getLogger(__name__)

class ImageHandler:
    """LINEからの画像メッセージイベントを処理するクラス。"""

    def __init__(self, line_service: LineService, imgur_service: ImgurService,
                 batch_service: BatchService):
        """
        コンストラクタ。依存するサービスを注入します。

        Args:
            line_service: LINE API連携サービス。
            imgur_service: Imgur API連携サービス。
            gemini_service: Gemini AI連携サービス。
            batch_service: バッチ処理サービス。
        """
        self.line_service = line_service
        self.imgur_service = imgur_service
        # GeminiServiceはblog_configに依存するため、handleメソッド内でインスタンス化します。
        self.batch_service = batch_service

    def handle(self, event: Dict[str, Any], context: Dict[str, Any] = None):
        """
        画像メッセージイベントを処理するメインのメソッド。

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
            "画像メッセージ処理開始: チャンネル=%s (ID: %s), ユーザー=%s",
            blog_name,
            channel_id_for_log,
            line_user_id,
        )

        if not line_user_id or not line_message_id:
            logger.warning("ImageHandler: イベント情報にユーザーIDまたはメッセージIDがありません。処理をスキップします。")
            return

        context = context or {}

        local_path = None
        try:
            # ステップ1: コンテンツのダウンロード
            local_path = self._download_content(line_message_id, context)

            # ステップ2: ユーザー情報の取得・作成
            user = self._get_or_create_user(line_user_id)

            # ステップ3: 外部サービスへのアップロード
            imgur_url = self._upload_to_external_service(local_path)

            # ステップ4: AIによる画像解析を実施（Anthropic/Claude を必ず使用）
            description = self._analyze_image_with_ai(local_path, imgur_url)

            # ステップ5: データベースへの保存
            new_message = self._save_message_and_asset(
                line_message_id, user.id, local_path, imgur_url, description
            )

            # ステップ6: バッチ処理へのキューイング
            self.batch_service.add_message(user.line_user_id, {
                'id': new_message.id,
                'message_type': 'image',
                'channel_id': channel_id
            })

            db.session.commit()
            logger.info(f"画像メッセージ (DB ID: {new_message.id}) をユーザー (ID: {user.id}) から正常に処理し、キューに追加しました。")

        except Exception as e:
            db.session.rollback()
            logger.error(f"画像メッセージ処理中にエラーが発生しました (Msg ID: {line_message_id}): {e}", exc_info=True)

    def _download_content(self, line_message_id: str, context: Dict[str, Any]) -> str:
        """コンテンツをダウンロードします。"""
        content_provider = context.get('content_provider', {}) or {}
        provider_type = content_provider.get('type', 'line')

        if provider_type == 'line' and not content_provider.get('originalContentUrl'):
            local_path = self.line_service.download_content(line_message_id, content_type='image', timeout=30)
        else:
            local_path = self._download_external_asset(content_provider, asset_type='image')

        if not local_path or not os.path.exists(local_path):
            raise IOError(f"メッセージID {line_message_id} の画像ダウンロードに失敗しました。")
        
        logger.info(f"画像コンテンツをダウンロードしました: {local_path}")
        return local_path

    def _get_or_create_user(self, line_user_id: str) -> User:
        """ユーザーIDを基にユーザーを取得または新規作成します。"""
        user = User.query.filter_by(line_user_id=line_user_id).first()
        if not user:
            profile = self.line_service.get_user_profile(line_user_id)
            user = User(line_user_id=line_user_id, display_name=profile.get('displayName'))
            db.session.add(user)
            db.session.flush()
        return user
    
    def _upload_to_external_service(self, local_path: str) -> str:
        """画像をImgurにアップロードします。失敗した場合は警告をログに出力します。"""
        try:
            imgur_resp = self.imgur_service.upload_image(local_path)
            if imgur_resp and imgur_resp.get('success'):
                url = imgur_resp.get('link', '')
                logger.info(f"Imgurへのアップロード成功: {url}")
                return url
            logger.warning(f"Imgurへのアップロードが成功しませんでした: {imgur_resp}")
        except Exception as e:
            logger.warning(f"Imgurへのアップロード中に例外が発生しました: {e}", exc_info=True)
        return ''

    def _analyze_image(self, local_path: str, blog_config: Dict[str, Any]) -> str:
        """Anthropic (Claude) を使用して画像を解析します。"""
        try:
            claude = ClaudeService()
            prompt = "この画像の内容をブログ記事で使えるように、簡潔かつ魅力的に説明してください。"
            # Send the image bytes as an inline path block so Claude can access it reliably
            description = claude.generate_text(prompt, max_tokens=800, temperature=0.0, images=[{'type': 'path', 'data': local_path}])
            logger.info(f"画像解析成功。説明文長: {len(description) if description else 0}")
            return description if description else "画像解析に失敗しました"
        except PermissionError as pe:
            logger.error(f"Claude認証エラー: {pe}")
            # 明示的に認証失敗を示す説明文を保存（運用者が気づきやすくするため）
            return "画像解析に失敗しました（Claude 認証エラー）"
        except Exception as e:
            logger.warning(f"AI画像解析に失敗しました: {e}")
            return "画像解析に失敗しました"

    def _save_message_and_asset(
        self, line_message_id: str, user_id: int, local_path: str,
        external_url: str, description: str
    ) -> Message:
        """メッセージとアセットの情報をデータベースにアトミックに保存します。"""
        new_message = Message(
            line_message_id=line_message_id,
            user_id=user_id,
            message_type='image'
        )
        db.session.add(new_message)
        db.session.flush()

        new_asset = Asset(
            message_id=new_message.id,
            asset_type='image',
            local_path=local_path,
            external_url=external_url,
            description=description
        )
        db.session.add(new_asset)
        return new_message

    def _download_external_asset(self, content_provider: Dict[str, Any], asset_type: str) -> str:
        """LINE以外のコンテンツプロバイダーが提供するURLからメディアをダウンロードします。"""
        url = content_provider.get('originalContentUrl') or content_provider.get('previewImageUrl')
        if not url:
            raise ValueError("外部コンテンツのURLが見つかりませんでした。")

        logger.info(f"外部URLから{asset_type}をダウンロードします: {url}")

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        suffix = '.jpg' if asset_type == 'image' else '.bin'
        filename = f"external_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
        save_dir = Path(self.line_service.upload_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / filename

        with open(file_path, 'wb') as f:
            f.write(response.content)

        return str(file_path)

    def _analyze_image_with_ai(self, image_path: str, external_url: str = '') -> str:
        """
        AIを使って画像を解析し、説明文を生成します。
        
        Args:
            image_path (str): 解析する画像のローカルパス
            
        Returns:
            str: 画像の説明文
        """
        # Anthropic (Claude) を常に使用して画像説明を生成する
        base = "この画像の内容をブログ記事で使えるように、簡潔かつ魅力的に説明してください。"
        try:
            claude = ClaudeService()
            # Always send the image inline (path) so the model can access it reliably.
            # Avoid relying on the model fetching external URLs which many hosted
            # Anthropic deployments cannot reach.
            prompt = base
            images = [{'type': 'path', 'data': image_path}]
            description = claude.generate_text(prompt, max_tokens=800, temperature=0.0, images=images)

            # If the model returns a message asking for more information / can't access,
            # we can try again or signal a friendly error. Detect common failure phrases here.
            if description and ('アクセスすることができません' in description or 'アクセスできません' in description or 'cannot access' in description.lower()):
                logger.info('モデルが画像URLへアクセスできなかったため、ファイルインラインで再試行します')
                # Already sent inline via path; the above branch is defensive in case we earlier sent URL.

            logger.info(f"AI画像解析成功: {description[:100] if description else 'N/A'}...")
            return description if description else "画像が送信されました。"
        except PermissionError as pe:
            logger.error(f"Claude認証エラー: {pe}")
            return "画像が送信されました。AI解析に失敗しました（Claude 認証エラー）"
        except Exception as e:
            logger.warning(f"AI画像解析に失敗しました: {e}")
            return "画像が送信されました。AI解析に失敗したため、詳細は不明です。"