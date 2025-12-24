from flask import Blueprint, request, jsonify
import logging
from collections import defaultdict, deque

# Imports from routes_webhook.py
import base64
import hashlib
import hmac
import json
import os
from typing import Any, Dict, Optional, Set
import threading

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

# chat_bp is already created
chat_bp = Blueprint('chat_bp', __name__)

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


@chat_bp.route("/line", methods=["POST"])
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

    # --- Persist raw webhook to DB and append to line_messages.log ---
    try:
        from src.database import db, LineWebhookEvent
        evt = LineWebhookEvent(
            channel_id=channel_info.get('channel_id'),
            channel_name=channel_info.get('channel_name'),
            raw_body=body,
            events_count=len(events),
            processed=False
        )
        db.session.add(evt)
        db.session.commit()
        logger.info("Saved LINE webhook event id=%s, events=%s", evt.id, len(events))
    except Exception as e:
        logger.warning("Failed to persist LINE webhook event: %s", e)

    try:
        logs_dir = os.path.join(os.getcwd(), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        log_path = os.path.join(logs_dir, 'line_messages.log')
        from datetime import datetime
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.utcnow().isoformat()} | channel={channel_info.get('channel_id')} | events={len(events)} | body={body}\n")
        logger.info("Appended raw webhook to %s", log_path)
    except Exception as e:
        logger.warning("Failed to append webhook to file: %s", e)

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


@chat_bp.route('/line/events', methods=['GET'])
def line_events():
    """Return recent LINE webhook events (most recent first). Query param: ?limit=50"""
    try:
        from src.database import LineWebhookEvent
        limit = int(request.args.get('limit') or 50)
        results = LineWebhookEvent.query.order_by(LineWebhookEvent.created_at.desc()).limit(limit).all()
        return jsonify([r.to_dict() for r in results])
    except Exception as e:
        logger.exception("Failed to fetch line events: %s", e)
        return jsonify({'error': 'failed to fetch events'}), 500


# ユーザーごとの会話履歴（最大10ターン）
user_histories = defaultdict(lambda: deque(maxlen=10))

@chat_bp.route('/chat', methods=['POST'])
def chat_webhook():
    logger = logging.getLogger('chat_webhook')
    logger.info('chat_webhook called')
    data = request.get_json() or {}
    logger.info(f"request data: {data}")
    user_id = data.get('user_id')
    # LINE形式のpayload対応
    message = data.get('message')
    if not message:
        # LINE webhook形式: events[0]['message']['text']
        events = data.get('events')
        if events and isinstance(events, list) and len(events) > 0:
            event_msg = events[0].get('message', {})
            message = event_msg.get('text')
            logger.info(f"LINE event message: {message}")
    if not message:
        logger.info('no message received')
        return jsonify({'reply': 'メッセージが空です。'}), 200

    # ユーザーIDがなければIPアドレス等で代用
    if not user_id:
        user_id = request.remote_addr or 'anonymous'

    # リセットワード判定
    reset_words = ['リセット', 'reset', '新規', 'clear', '会話リセット', '新しく']
    if any(word in message for word in reset_words):
        # 履歴クリアは従来通り
        user_histories[user_id].clear()
        logger.info(f"[chat] 会話履歴リセット: {user_id}")
        return jsonify({'reply': '会話履歴をリセットしました。新しい会話をどうぞ。'}), 200

    # chat_conversation.jsonワークフローをTaskRunnerで実行
    try:
        from src.services.framework.task_runner import TaskRunner
        workflow_path = 'src/workflows/chat_conversation.json'
        runner = TaskRunner(workflow_path=workflow_path)
        initial_inputs = {
            'user_id': user_id,
            'message': message
        }
        result = runner.run(initial_inputs=initial_inputs)
        reply = result.get('ai_reply') or '(AI応答なし)'
        logger.info(f"[chat_workflow] reply: {reply}")
    except Exception as e:
        logger.error(f"chat_workflow error: {e}")
        reply = f"(AI応答エラー) あなた: {message}"

    return jsonify({'reply': reply}), 200