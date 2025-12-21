"""
Claude 4 API連携サービス。

Anthropic社のClaude 4 APIを利用したテキスト生成機能を提供します。
APIキーの読み込みと、SDKクライアントの初期化を管理します。
"""

import os
import logging
from typing import Optional
from anthropic import Anthropic, APIError

logger = logging.getLogger(__name__)


class Claude4Service:
    """Anthropic Claude 4 APIとの連携を管理するサービスクラス。"""

    def __init__(self, api_key: Optional[str] = None):
        """
        コンストラクタ。
        環境変数からAPIキーを読み込み、Anthropicクライアントを初期化します。
        """
        # APIキーを環境変数から取得、なければ引数から取得
        self.api_key = os.environ.get("CLAUDE_API_KEY") or api_key

        # ローカル開発用に.env.productionからの読み込みも試みる
        if not self.api_key:
            try:
                env_path = os.path.join(os.path.dirname(__file__), '../../.env.production')
                if os.path.exists(env_path):
                    with open(env_path, encoding='utf-8') as f:
                        for line in f:
                            if line.strip().startswith('CLAUDE_API_KEY='):
                                self.api_key = line.strip().split('=', 1)[1].strip().strip('"')
                                break
            except IOError as e:
                logger.warning(f".env.productionの読み込み中にエラーが発生しました: {e}")

        # 使用するモデル名を指定
        self.model = "claude-3-5-sonnet-20240620"  # 最新のClaude 3.5 Sonnetモデル

        # APIキーがあればクライアントを初期化
        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("CLAUDE_API_KEYが設定されていないため、Claude4Serviceは無効です。")

    def generate_content(self, prompt: str, max_tokens: int = 3000, temperature: float = 0.5) -> Optional[str]:
        """
        Claude 4モデルを使用して、指定されたプロンプトからテキストを生成します。

        Args:
            prompt (str): AIに渡すプロンプト。
            max_tokens (int): 生成するテキストの最大トークン数。
            temperature (float): 生成のランダム性を制御する値 (0.0-1.0)。

        Returns:
            Optional[str]: 生成されたテキスト。エラー時はNone。
        """
        if not self.client:
            logger.error("Claude APIクライアントが初期化されていません。APIキーの設定を確認してください。")
            return None

        try:
            logger.info(f"Claude 4 APIにリクエストを送信します (モデル: {self.model})。")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}]
            )

            # response.contentはリスト形式で返される
            if response.content:
                text_blocks = [block.text for block in response.content if hasattr(block, 'text')]
                full_text = "".join(text_blocks).strip()
                logger.info(f"Claude 4から {len(full_text)} 文字の応答を受信しました。")
                return full_text

            logger.warning("Claude APIから空のコンテンツが返されました。")
            return None

        except APIError as e:
            # Anthropic SDKが提供する具体的なAPIエラーを捕捉
            logger.error(f"Claude APIエラーが発生しました: {e.status_code} - {e.message}", exc_info=True)
            return None
        except Exception as e:
            # その他の予期せぬエラー
            logger.error(f"Claudeコンテンツ生成中に予期せぬエラーが発生しました: {e}", exc_info=True)
            return None
