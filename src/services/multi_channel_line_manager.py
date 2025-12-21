"""
マルチチャンネル対応のLINE管理サービス (v2 SDK)
"""
import logging
import yaml
import os
from typing import Optional, Dict, Any
from linebot import LineBotApi, WebhookHandler

logger = logging.getLogger(__name__)

def _resolve_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively resolves environment variable placeholders in the config."""
    for key, value in config.items():
        if isinstance(value, dict):
            config[key] = _resolve_env_vars(value)
        elif isinstance(value, str):
            import re
            match = re.match(r"\$\{(.+)\}", value)
            if match:
                env_var = match.group(1)
                config[key] = os.getenv(env_var)
    return config

class MultiChannelLineManager:
    """複数のLINEチャンネルを管理（v2 SDK）"""

    def __init__(self):
        self.channels: Dict[str, Dict[str, Any]] = {}
        self._secret_to_id: Dict[str, str] = {}  # O(1)逆引き用
        self.test_users: list = []
        self._load_channels()

    def _load_channels(self):
        """channels.ymlから全チャンネル情報を読み込む"""
        # 環境変数を読み込む
        from dotenv import load_dotenv
        load_dotenv('hatena_accounts.env')
        
        try:
            with open('channels.yml', 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
                channels_config = _resolve_env_vars(raw_config.get('channels', {}))
                self.test_users = raw_config.get('test_users', [])
        except FileNotFoundError:
            logger.error("channels.ymlファイルが見つかりません")
            return
        except yaml.YAMLError as e:
            logger.error(f"channels.ymlのYAML解析エラー: {e}")
            return

        for ch_id, config in channels_config.items():
            # 型安全性の担保: 各チャンネル設定は辞書である必要がある
            if not isinstance(config, dict):
                logger.warning(f"[スキップ] チャンネル {ch_id}: 設定が辞書ではありません (type={type(config).__name__})")
                continue

            secret = config.get('secret')
            token = config.get('access_token')

            if not (secret and token):
                logger.warning(f"[スキップ] チャンネル {ch_id}: 認証情報不完全")
                continue

            self.channels[ch_id] = {
                'channel_id': ch_id,
                'channel_name': config.get('channel_name'),
                'channel_description': config.get('channel_description'),
                'channel_email': config.get('channel_email'),
                'app_type': config.get('app_type'),
                'permissions': config.get('permissions'),
                'channel_secret': secret,  # キー名を統一
                'access_token': token,
                'owner_user_id': config.get('owner_user_id'),
                'test_users': config.get('test_users', []),
            }
            self._secret_to_id[secret] = ch_id
            logger.info(f"[登録] {config.get('channel_name')} (ID: {ch_id})")

        logger.info(f"合計 {len(self.channels)} チャンネル登録")

    def get_channel_by_secret(self, secret: str) -> Optional[Dict[str, Any]]:
        """署名検証用シークレットからチャンネル情報取得（O(1)）"""
        channel_id = self._secret_to_id.get(secret)
        return self.channels.get(channel_id) if channel_id else None

    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """チャンネルIDから情報取得"""
        return self.channels.get(channel_id)

    def get_line_bot_api(self, channel_id: str) -> Optional[LineBotApi]:
        """LineBotApiインスタンス取得（メッセージ送信・コンテンツダウンロード）"""
        info = self.get_channel(channel_id)
        if not info:
            logger.error(f"チャンネルID {channel_id} 未登録")
            return None
        return LineBotApi(info['access_token'])

    def get_webhook_handler(self, channel_id: str) -> Optional[WebhookHandler]:
        """WebhookHandler取得（署名検証）"""
        info = self.get_channel(channel_id)
        if not info:
            logger.error(f"チャンネルID {channel_id} 未登録")
            return None
        return WebhookHandler(info['channel_secret'])

    def list_channels(self) -> Dict[str, Dict[str, Any]]:
        """全チャンネル情報取得"""
        return self.channels.copy()

    def get_test_users(self) -> list:
        """テストユーザーIDリスト取得"""
        return self.test_users.copy()

    def reload(self):
        """設定再読み込み"""
        self.channels.clear()
        self._secret_to_id.clear()
        self.test_users.clear()
        self._load_channels()

# グローバルインスタンス
multi_channel_manager = MultiChannelLineManager()
