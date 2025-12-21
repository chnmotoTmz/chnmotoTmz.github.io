"""
イベントルーター。

LINE Messaging APIから受信したイベントを、そのタイプに応じて
適切なハンドラに振り分ける役割を担います。
依存性の注入（DI）パターンを用いて、各ハンドラを注入できるように設計されています。
"""
import logging
import os
from typing import Any, Dict, Optional

from src.handlers.text_handler import TextHandler
from src.handlers.image_handler import ImageHandler
from src.handlers.video_handler import VideoHandler
from src.services.line_service import LineService
from src.services.batch_service import BatchService
from src.services.workflow_processing_service import WorkflowProcessingService

logger = logging.getLogger(__name__)

class EventRouter:
    """LINEイベントを適切なハンドラにルーティングするクラス。"""

    def __init__(
        self,
        line_service: LineService,
        batch_service: BatchService,
        workflow_service: Optional[WorkflowProcessingService] = None,
    ):
        """
        コンストラクタ。各イベントタイプに対応するハンドラを注入します。

        Args:
            line_service (LineService): LINE APIサービス。
            batch_service (BatchService): バッチ処理サービス。
            workflow_service (WorkflowProcessingService): ワークフロー処理サービス。
        """
        from src.services.imgur_service import ImgurService
        from src.services.gemini_service import GeminiService

        self.line_service = line_service
        self.batch_service = batch_service

        imgur_service = ImgurService()
        gemini_service = GeminiService()
        self.text_handler = TextHandler(self.line_service, self.batch_service)
        self.image_handler = ImageHandler(self.line_service, imgur_service, self.batch_service)
        self.video_handler = VideoHandler(self.line_service, imgur_service, self.batch_service)

    def route(self, event: Dict[str, Any]):
        """
        イベントをそのタイプに基づいて適切なハンドラに振り分けます。

        Args:
            event (Dict[str, Any]): LINEから受信したイベントのペイロード。
        """
        # チャンネル情報を取得
        channel_info = event.get('channel_info', {})
        channel_id = channel_info.get('channel_id')
        blog_name = channel_info.get('blog_name', 'Unknown')

        if channel_id:
            self.line_service.set_channel(channel_id)
        else:
            logger.warning("EventRouter: channel_idが指定されていないイベントを受信しました。デフォルトトークンで処理します。")
        channel_id_for_log = channel_id or 'Unknown'
        
        logger.info(f"LINEメッセージを受信: チャンネル={blog_name} (ID: {channel_id_for_log})")
        
        # 現在はメッセージイベントのみを処理対象とする
        event_type = event.get('type')
        if event_type != 'message':
            logger.info(f"メッセージ以外のイベントタイプ '{event_type}' は無視します。")
            return

        # メッセージのタイプに応じて処理を分岐
        message = event.get('message', {})
        message_type = message.get('type')
        
        # コンテキストを準備（メディアコンテンツのダウンロード情報など）
        context = self._prepare_message_context(event)
        
        if message_type == 'text':
            logger.debug(f"テキストメッセージを受信。TextHandlerにルーティングします。")
            self.text_handler.handle(event)
        elif message_type == 'image':
            logger.debug(f"画像メッセージを受信。ImageHandlerにルーティングします。")
            self.image_handler.handle(event, context)
        elif message_type == 'video':
            logger.debug(f"動画メッセージを受信。VideoHandlerにルーティングします。")
            # The blog_config is now determined within the workflow,
            # so it's no longer passed from the router.
            self.video_handler.handle(event, context=context)
        else:
            # 未対応のメッセージタイプの場合は警告をログに出力
            logger.warning(f"未対応のメッセージタイプ '{message_type}' を受信しました。")

    def _prepare_message_context(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        メディアメッセージ用のコンテキストを準備します。
        外部コンテンツプロバイダーの検出とダウンロード情報を含みます。
        
        Args:
            event (Dict[str, Any]): LINEイベント
            
        Returns:
            Dict[str, Any]: コンテキスト情報（line_message_id, content_provider, local_pathなど）
        """
        message = event.get('message', {})
        message_type = message.get('type')
        context = {}

        # テキストメッセージの場合はコンテキスト不要
        if message_type == 'text':
            return context

        # メディアメッセージの場合はコンテンツプロバイダー情報を取得
        line_message_id = message.get('id')
        content_provider = message.get('contentProvider', {}) or {}
        provider_type = content_provider.get('type', 'line')
        
        context['line_message_id'] = line_message_id
        context['content_provider'] = content_provider
        
        # 外部コンテンツプロバイダーの場合はURL情報を保存
        if provider_type != 'line':
            context['original_content_url'] = content_provider.get('originalContentUrl')
            context['preview_image_url'] = content_provider.get('previewImageUrl')
            logger.info(f"外部コンテンツプロバイダー検出: {provider_type}")
        
        return context