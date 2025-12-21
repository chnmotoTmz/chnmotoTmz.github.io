import os
import base64
import hashlib
import hmac
from typing import Optional, Dict, Any
from src.services.multi_channel_line_manager import multi_channel_manager
import logging

def expand_channel_envvars(channel: Dict[str, Any]) -> Dict[str, Any]:
    """
    access_tokenやsecretが${...}形式なら環境変数展開した値を返す。
    それ以外はそのまま返す。
    """
    result = dict(channel)
    for key in ("access_token", "channel_secret", "secret"):
        if key in result and isinstance(result[key], str):
            result[key] = os.path.expandvars(result[key])
    return result

def verify_line_signature(body: str, signature: str, secret: str) -> bool:
    mac = hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
    expected = base64.b64encode(mac).decode()
    return hmac.compare_digest(expected, signature)


def identify_line_channel(body: str, signature: Optional[str]) -> Optional[Dict[str, Any]]:
    logger = logging.getLogger('line_channel_identify')
    if not signature:
        logger.warning("Missing X-Line-Signature header")
        return None

    for channel in multi_channel_manager.list_channels().values():
        secret = channel.get("channel_secret")
        if not secret:
            continue
        try:
            if verify_line_signature(body, signature, secret):
                logger.info(
                    "Channel identified: %s (ID: %s)",
                    channel.get("channel_name"),
                    channel.get("channel_id"),
                )
                # access_token等をos.path.expandvarsで展開したものを返す
                return expand_channel_envvars(channel)
        except Exception as exc:
            logger.error("Signature verification error for channel %s: %s", channel.get("channel_id"), exc)

    logger.warning("Signature verification failed for all channels")
    return None
