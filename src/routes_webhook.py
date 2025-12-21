"""
LINE Webhook ルート - バッチ処理強化版
従来版をベースにバッチ処理とフォトライフ統合を追加
"""

import base64
import hashlib
import hmac
import json
import logging
import os
from typing import Any, Dict, Optional, Set
import threading

from flask import Blueprint, jsonify, request

from src.handlers.event_router import EventRouter
from src.services.workflow_processing_service import WorkflowProcessingService
from src.services.batch_service import BatchService
from src.services.line_service import LineService
from src.services.multi_channel_line_manager import multi_channel_manager

_APP = None

logger = logging.getLogger(__name__)


def set_app(app):
    """Batch処理スレッドからFlaskアプリケーションコンテキストへアクセスするために保持する。"""
    global _APP
    _APP = app


BATCH_INTERVAL = int(os.getenv("BATCH_INTERVAL_MINUTES", "2")) * 60

webhook_bp = Blueprint("webhook", __name__)

line_service = LineService()


def _process_user_batch_entry(user_id: str, messages: list):
    """バッチタイマーから呼び出されるエントリポイント。"""
    if _APP is None:
        raise RuntimeError("Batch callback: Flask app not set")

    with _APP.app_context():
        from src.database import Message, User

        message_ids = []
        for message in messages:
            if isinstance(message, dict) and "id" in message:
                message_ids.append(message["id"])
                continue

            line_message_id = message.get("line_message_id") if isinstance(message, dict) else None
            if not line_message_id:
                continue

            msg = Message.query.filter_by(line_message_id=line_message_id).first()
            if msg:
                message_ids.append(msg.id)

        if not message_ids:
            logger.warning("No valid message IDs found for user %s", user_id)
            return

        channel_ids: Set[str] = {
            msg.get("channel_id")
            for msg in messages
            if isinstance(msg, dict) and msg.get("channel_id")
        }

        channel_id: Optional[str] = None
        if len(channel_ids) == 1:
            channel_id = next(iter(channel_ids))
        elif len(channel_ids) > 1:
            logger.warning("Multiple channel_ids detected in batch for user %s: %s", user_id, channel_ids)

        user = User.query.filter_by(line_user_id=user_id).first()
        if not user:
            logger.error("User not found for line_user_id: %s", user_id)
            return

        # WorkflowProcessingServiceを直接呼び出す
        workflow_service = WorkflowProcessingService()
        workflow_service.process_user_batch(user_id, message_ids, channel_id)


batch_service = BatchService(interval_sec=BATCH_INTERVAL, process_callback=_process_user_batch_entry)
event_router = EventRouter(line_service=line_service, batch_service=batch_service)


def _verify_signature(body: str, signature: str, secret: str) -> bool:
    mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    return hmac.compare_digest(expected, signature)


def _identify_channel(body: str, signature: Optional[str]) -> Optional[Dict[str, Any]]:
    if not signature:
        logger.warning("Missing X-Line-Signature header")
        return None

    for channel in multi_channel_manager.list_channels().values():
        secret = channel.get("channel_secret")
        if not secret:
            continue
        try:
            if _verify_signature(body, signature, secret):
                logger.info(
                    "Channel identified: %s (ID: %s)",
                    channel.get("channel_name"),
                    channel.get("channel_id"),
                )
                return channel
        except Exception as exc:
            logger.error("Signature verification error for channel %s: %s", channel.get("channel_id"), exc)

    logger.warning("Signature verification failed for all channels")
    return None


@webhook_bp.route("/line", methods=["POST"])
def line_webhook():
    logger.info("--- line_webhook function entered ---")
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    if not body:
        logger.error("Request body is empty")
        return jsonify({"error": "request body is empty"}), 400

    logger.info("Webhook received. Body length=%s", len(body))

    channel_info = _identify_channel(body, signature)
    if not channel_info:
        logger.error("Signature verification failed")
        return jsonify({"error": "signature verification failed"}), 403

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON: %s", exc)
        return jsonify({"error": "invalid json"}), 400

    events = payload.get("events", []) if isinstance(payload, dict) else []
    if not isinstance(events, list):
        logger.error("events field not list")
        return jsonify({"error": "events field invalid"}), 400

    processed = 0
    line_service.set_channel(channel_info.get("channel_id"))

    for event in events:
        if not isinstance(event, dict):
            logger.warning("Skipping event with unexpected type: %s", type(event))
            continue

        event.setdefault("channel_info", {})
        event["channel_info"].update(
            {
                "channel_id": channel_info.get("channel_id"),
                "channel_name": channel_info.get("channel_name"),
                "blog_name": channel_info.get("channel_name"),
            }
        )

        try:
            event_router.route(event)
            processed += 1
        except Exception as exc:
            logger.exception("Event processing failed (index=%s): %s", processed, exc)
            raise

    return jsonify({"status": "ok", "events_processed": processed})


@webhook_bp.route("/debug/flush/<user_id>", methods=["POST"])
def debug_flush_batch(user_id: str):
    """開発用: 指定ユーザーのバッチを即座に処理"""
    batch_service.flush_now(user_id)
    return jsonify({"message": f"Batch flushed for user {user_id}"}), 200


def _run_workflow_in_background(line_user_id: str, message_ids: list, channel_id: Optional[str]):
    """バックグラウンドでワークフローを実行するためのヘルパー関数"""
    if _APP is None:
        logger.error("Cannot run background task: Flask app context is not available.")
        return

    with _APP.app_context():
        try:
            logger.info(f"Background workflow starting for user {line_user_id}")
            workflow_service = WorkflowProcessingService()
            workflow_service.process_user_batch(line_user_id, message_ids, channel_id)
            logger.info(f"Background workflow finished for user {line_user_id}")
        except Exception as e:
            logger.error(f"Error in background workflow for user {line_user_id}: {e}", exc_info=True)


@webhook_bp.route("/trigger/workflow", methods=["POST"])
def trigger_workflow():
    """
    外部サービスやスケジューラー、GUIワークフロー等からPOSTで呼び出せる汎用エンドポイント。
    記事生成ワークフローを起動します。
    例: IFTTT, Google Apps Script, PowerAutomate, Zapier, cron など
    """
    try:
        payload = request.get_json(force=True)
    except Exception as exc:
        logger.error("Invalid JSON: %s", exc)
        return jsonify({"error": "invalid json"}), 400

    # 必須パラメータの検証
    line_user_id = payload.get("line_user_id")
    message_ids = payload.get("message_ids")
    channel_id = payload.get("channel_id") # オプション

    if not line_user_id or not message_ids:
        return jsonify({"error": "Missing required parameters: 'line_user_id' and 'message_ids' are required."}), 400

    logger.info(f"Received workflow trigger request for user: {line_user_id}")

    # ワークフローをバックグラウンドで実行
    thread = threading.Thread(
        target=_run_workflow_in_background,
        args=(line_user_id, message_ids, channel_id)
    )
    thread.start()

    # 即座にレスポンスを返す
    return jsonify({"status": "accepted", "message": "Workflow triggered successfully."}), 202
