"""
統合LLMファサード

Gemini（クラウド）とローカルLLMの両方をサポートし、
設定で自動切り替え可能なファサード層。

用途に応じて最適なLLMを選択：
- Gemini: 高品質が必要な場合
- LocalLLM: 無制限・オフラインで回したい場合
"""

import logging
import os
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """LLMプロバイダー選択"""
    GEMINI = "gemini"
    LOCAL = "local"


class UnifiedLLMFacade:
    """
    Gemini / ローカルLLM を統一インターフェースで扱う。
    """

    def __init__(
        self,
        provider: str = None,
        blog_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初期化。
        
        Args:
            provider: "gemini" or "local" (デフォルト: 環境変数から判定)
            blog_config: ブログ設定
        """
        # プロバイダー選択（環境変数で優先）
        # デフォルトを gemini に変更（ユーザーの要求に合わせる）
        provider = os.getenv("LLM_PROVIDER", provider or "gemini")
        
        if provider == "gemini":
            self.provider = LLMProvider.GEMINI
            from src.services.gemini_service import GeminiService
            self._service = GeminiService(blog_config=blog_config)
        elif provider == "local":
            self.provider = LLMProvider.LOCAL
            from src.services.local_llm_service import LocalLLMService
            self._service = LocalLLMService(blog_config=blog_config)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        logger.info(f"UnifiedLLMFacade using provider: {self.provider.value}")

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        テキスト生成（プロバイダー非依存）。

        Args:
            prompt: プロンプト
            temperature: 創造性
            max_tokens: 最大トークン数
            system_prompt: システムプロンプト（LocalLLMのみ対応）

        Returns:
            生成テキスト
        """
        # Gemini用パラメータ
        if self.provider == LLMProvider.GEMINI:
            return self._service.generate_text(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        
        # LocalLLM用パラメータ
        return self._service.generate_text(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt,
            **kwargs
        )

    def analyze_image_from_path(
        self,
        image_path: str,
        prompt: str = "この画像について説明してください。",
        **kwargs
    ) -> str:
        """
        画像解析（プロバイダー非依存）。

        Args:
            image_path: 画像ファイルパス
            prompt: 解析プロンプト

        Returns:
            解析結果
        """
        return self._service.analyze_image_from_path(
            image_path=image_path,
            prompt=prompt,
            **kwargs
        )

    @property
    def is_local(self) -> bool:
        """ローカルLLMを使用しているか"""
        return self.provider == LLMProvider.LOCAL

    @property
    def is_gemini(self) -> bool:
        """Geminiを使用しているか"""
        return self.provider == LLMProvider.GEMINI

    def get_provider_info(self) -> Dict[str, Any]:
        """プロバイダー情報を取得"""
        return {
            "provider": self.provider.value,
            "service_type": type(self._service).__name__,
        }
