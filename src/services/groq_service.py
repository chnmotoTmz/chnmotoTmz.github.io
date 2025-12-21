"""
Groq API直接連携サービス。

Groq APIに直接呼び出して、テキスト生成などのAI機能を高速に提供します。
"""

import logging
import os
import time
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class GroqService:
    """
    Groq APIと直接連携し、テキスト生成機能を提供します。
    """

    def __init__(self):
        """
        コンストラクタ。
        環境変数からAPIキーを読み込みます。
        """
        self._api_key = os.getenv('GROQ_API_KEY')
        if not self._api_key:
            raise ValueError("GROQ_API_KEY が設定されていません")

        self._api_url = "https://api.groq.com/openai/v1/chat/completions"
        self._model = "llama-3.1-8b-instant"  # デフォルトモデル

    def generate_text(self, prompt: str, max_tokens: int = 3500, temperature: float = 0.4, model: Optional[str] = None) -> str:
        """
        テキストを生成します。

        Args:
            prompt: 生成プロンプト
            max_tokens: 最大トークン数
            temperature: 生成温度
            model: 使用モデル（指定しない場合はデフォルト）

        Returns:
            生成されたテキスト
        """
        use_model = model or self._model
        logger.info(f"Groqテキスト生成開始 (モデル: {use_model})")

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}"
            }

            payload = {
                "model": use_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False
            }

            logger.info(f"Groq API呼び出し: {self._api_url}")

            response = requests.post(
                self._api_url,
                json=payload,
                headers=headers,
                timeout=300  # 5分タイムアウト
            )

            if response.status_code == 200:
                data = response.json()

                if 'choices' in data and len(data['choices']) > 0:
                    result_text = data['choices'][0]['message']['content'].strip()
                    logger.info(f"Groqテキスト生成成功 (長さ: {len(result_text)}文字)")
                    return result_text
                else:
                    raise RuntimeError("Groq APIが不正なレスポンスを返しました")
            else:
                logger.error(f"Groq APIエラー: status={response.status_code}, body={response.text[:200]}")
                raise RuntimeError(f"Groq API呼び出し失敗: {response.status_code}")

        except requests.exceptions.Timeout:
            logger.warning("Groq APIタイムアウト")
            raise RuntimeError("Groq APIタイムアウト")
        except requests.exceptions.ConnectionError:
            logger.warning("Groq API接続エラー")
            raise RuntimeError("Groq API接続エラー")
        except Exception as e:
            logger.error(f"Groq API呼び出し中にエラー: {e}")
            raise RuntimeError(f"Groq API呼び出し失敗: {e}")

    def test_connection(self) -> bool:
        """
        API接続をテストします。

        Returns:
            接続成功ならTrue
        """
        try:
            result = self.generate_text("Hello, just say 'Groq test successful' and nothing else.", max_tokens=50, temperature=0)
            return "Groq test successful" in result
        except Exception as e:
            logger.error(f"Groq接続テスト失敗: {e}")
            return False