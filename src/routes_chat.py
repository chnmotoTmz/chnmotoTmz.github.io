# --- チャンネル識別用ユーティリティ ---
import base64
import hashlib
import hmac
from src.services.multi_channel_line_manager import multi_channel_manager
from typing import Any, Optional, Dict

def _verify_signature(body: str, signature: str, secret: str) -> bool:
    mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    return hmac.compare_digest(expected, signature)

def _identify_channel(body: str, signature: Optional[str]) -> Optional[Dict[str, Any]]:
    logger = logging.getLogger('chat_channel_identify')
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
# --- チャンネル識別用ユーティリティ ---
import base64
import hashlib
import hmac
from src.services.multi_channel_line_manager import multi_channel_manager
from typing import Optional, Dict

def _verify_signature(body: str, signature: str, secret: str) -> bool:
    mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    return hmac.compare_digest(expected, signature)

def _identify_channel(body: str, signature: Optional[str]) -> Optional[Dict[str, Any]]:
    logger = logging.getLogger('chat_channel_identify')
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
from flask import Blueprint, request, jsonify
import logging
from collections import defaultdict, deque

chat_bp = Blueprint('chat_bp', __name__)

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
    # --- チャンネル判定・トークン切り替え ---
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    channel_info = None
    if signature and body:
        channel_info = _identify_channel(body, signature)
        if channel_info:
            from src.services.line_service import LineService
            line_service = LineService()
            line_service.set_channel(channel_info.get('channel_id'))
    channel_id = channel_info.get('channel_id') if channel_info else None

    if not message:
        # LINE webhook形式: events[0]['message']['text']
        events = data.get('events')
        if events and isinstance(events, list) and len(events) > 0:
            event_msg = events[0].get('message', {})
            message = event_msg.get('text')
            logger.info(f"LINE event message: {message}")
            # ユーザーIDもLINEイベントから取得
            if not user_id:
                user_id = events[0].get('source', {}).get('userId')
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
            'message': message,
            'channel_id': channel_id
        }
        result = runner.run(initial_inputs=initial_inputs)
        reply = result.get('ai_reply') or '(AI応答なし)'
        logger.info(f"[chat_workflow] reply: {reply}")
    except Exception as e:
        logger.error(f"chat_workflow error: {e}")
        reply = f"(AI応答エラー) あなた: {message}"

    return jsonify({'reply': reply}), 200
