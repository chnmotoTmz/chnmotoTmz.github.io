"""
Unified LLM service wrapper.

Provides a common interface for text generation across multiple large language models
(Anthropic Claude 4 and Google Gemini). This allows callers to switch providers by
configuration while keeping business logic unchanged.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict

from src.services.claude4_service import Claude4Service
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class UnifiedLLMService:
    def _init_model_key_connectivity_check(self):
        """全モデル・APIキーで短い疎通テストを行い、最初に成功した組み合わせを記憶する。"""
        test_prompt = "疎通テスト"
        for model in self.GEMINI_MODEL_CANDIDATES:
            try:
                gemini = GeminiService()
                # GeminiServiceの内部でAPIキーをローテーションしながらテスト
                text = gemini.generate_text(test_prompt, model_name=model)
                if text and text.strip():
                    self._working_model = model
                    logger.info(f"[LLM疎通テスト] 最初に利用可能なモデル: {model}")
                    return
            except Exception as e:
                logger.warning(f"[LLM疎通テスト] モデル {model} で失敗: {e}")
        raise RuntimeError("利用可能なGeminiモデル/APIキーが見つかりませんでした")
    """Facade that exposes a common text-generation API over multiple LLM providers."""

    # 利用可能なモデル群（優先順）
    # APIで利用可能なモデル名のみ（抽象名やサポート外は除外）
    GEMINI_MODEL_CANDIDATES = [
        "gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-2.5-flash-lite",
        "gemini-2.0-flash-exp", "gemini-2.0-flash-preview-image-generation"
    ]
    GEMMA_MODEL_CANDIDATES = [
        "gemma-3-27b", "gemma-3-12b", "gemma-3-4b", "gemma-3-2b", "gemma-3-1b"
    ]
    SUPPORTED_MODELS = {
        # APIで直接利用可能なモデル名のみ（値も具体モデル名にする）
        **{m: m for m in GEMINI_MODEL_CANDIDATES},
        **{m: m for m in GEMMA_MODEL_CANDIDATES},
    }

    def __init__(self, default_model: str = "gemini"):
        # 抽象名やサポート外モデルの場合は最初の有効な具体的モデル名を使う
        try:
            self.default_model = self._normalize_model(default_model)
        except ValueError:
            import warnings
            logger.warning(f"指定されたデフォルトモデル '{default_model}' はサポート外です。'" + self.GEMINI_MODEL_CANDIDATES[0] + "' に自動で切り替えます。")
            self.default_model = self.GEMINI_MODEL_CANDIDATES[0]
        self._clients: Dict[str, object] = {}
        # 疎通テストを実施し、最初に使えるモデル・APIキーを記憶
        self._working_model = None
        self._working_key = None
        self._init_model_key_connectivity_check()

    def _normalize_model(self, model: str) -> str:
        key = (model or "").lower().strip()
        if key not in self.SUPPORTED_MODELS:
            raise ValueError(f"Unsupported LLM model '{model}'. Supported: {sorted(self.SUPPORTED_MODELS)}")
        return self.SUPPORTED_MODELS[key]

    def _get_client(self, model: str):
        normalized = self._normalize_model(model)
        if normalized in self._clients:
            return self._clients[normalized]

        if normalized.startswith("gemini"):
            client = GeminiService()
        elif normalized.startswith("gemma"):
            # TODO: Gemmaモデル用クライアント実装時に追加
            raise NotImplementedError("Gemmaモデルは未実装です")
        else:
            raise ValueError(f"Unsupported normalized model '{normalized}'")

        self._clients[normalized] = client
        return client

    def generate_text(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_tokens: int = 3500,
        temperature: float = 0.4,
        retry_models: bool = True,
    ) -> Optional[str]:
        """Generate text using the selected LLM provider. Gemini系でエラー時は他モデルへ自動ローテーション。"""
        tried_models = set()
        # 優先モデルリストを決定
        if model:
            # 指定モデルが抽象名（"gemini"等）の場合は候補リスト全体を使う
            if model in self.GEMINI_MODEL_CANDIDATES + self.GEMMA_MODEL_CANDIDATES:
                model_candidates = [model]
            else:
                model_candidates = self.GEMINI_MODEL_CANDIDATES + self.GEMMA_MODEL_CANDIDATES
        else:
            model_candidates = self.GEMINI_MODEL_CANDIDATES + self.GEMMA_MODEL_CANDIDATES

        last_error = None
        for m in model_candidates:
            if m in tried_models:
                continue
            tried_models.add(m)
            try:
                normalized = self._normalize_model(m)
                
                # Gemmaモデルは未実装なのでスキップ
                if normalized.startswith("gemma"):
                    logger.debug(f"Skipping unimplemented Gemma model: {m}")
                    continue

                client = self._get_client(normalized)
                if normalized.startswith("gemini"):
                    result = client.generate_text(prompt, model_name=m)
                else:
                    # 将来的に他のモデル（Claudeなど）を追加する場合
                    logger.warning(f"Model '{m}' is supported but has no generation logic.")
                    continue
                
                if result:
                    return result
            except Exception as e:
                last_error = e
                # 404エラーやAPI上限・エラー時は次候補へ
                if retry_models and ("404" in str(e) or any(token in str(e).lower() for token in ["quota", "429", "rate", "resource_exhausted", "api key", "invalid", "unavailable", "error"])):
                    continue
                else:
                    break
        if last_error:
            raise RuntimeError(f"全モデルでテキスト生成に失敗: {last_error}") from last_error
        return None

    def analyze_image(
        self,
        image_path: str,
        *,
        model: Optional[str] = None,
        prompt: str = "この画像の内容をブログ記事で使えるように、簡潔かつ魅力的に説明してください。",
    ) -> str:
        """Delegate image analysis to Gemini (the currently supported vision model)."""
        target_model = model or self.default_model
        normalized = self._normalize_model(target_model)

        if normalized != "gemini":
            raise NotImplementedError("Image analysis is only supported via Google Gemini at this time.")

        client = self._get_client("gemini")
        return client.analyze_image_from_path(image_path, prompt=prompt)
