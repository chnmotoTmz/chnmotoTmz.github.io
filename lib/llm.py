"""
Standalone LLM service extracted from src/services/gemini_service.py.

Provides two text generation backends:
1. CustomAPIClient - For local Chrome extension wrapper (localhost:3000/api/ask)
2. GeminiRestClient - For Gemini REST API (generativelanguage.googleapis.com)

LLMService is the facade that manages fallback between them.
"""

import json
import logging
import os
import re
import time
import requests
from dataclasses import dataclass
from typing import Optional, Union, List, Dict

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized LLM response."""
    text: Optional[str]
    success: bool
    error: Optional[str] = None
    source: Optional[str] = None


class CustomAPIClient:
    """
    Client for custom LLM API (Chrome extension wrapper at localhost:3000).
    Extracted from src/services/gemini_service.py's CustomAPIClient.
    """
    _current_mode: Optional[str] = None

    def __init__(
        self,
        api_url: Optional[str] = None,
        bearer_token: Optional[str] = None,
        timeout: int = 600,
        retries: int = 2
    ):
        self.api_url = api_url or os.getenv(
            'CUSTOM_LLM_API_URL',
            os.getenv('LOCAL_GEMINI_API_URL', 'http://localhost:3000/api/ask')
        )
        self.bearer_token = bearer_token or os.getenv('CUSTOM_LLM_API_BEARER')
        self.timeout = timeout
        self.retries = retries

    def generate(self, prompt: str, mode: Optional[str] = None) -> LLMResponse:
        """Generate text using the custom API. Forces 'Thinking' mode."""
        if not self.api_url:
            return LLMResponse(text=None, success=False, error="API URL not configured")

        self.set_mode('Thinking')
        logger.info("CustomAPIClient: calling ask (timeout=%ds)", self.timeout)

        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers['Authorization'] = f"Bearer {self.bearer_token}"

        payload = {"prompt": prompt.replace('\n', '\\n')}

        for attempt in range(self.retries + 1):
            try:
                resp = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )

                if resp.status_code == 200:
                    text = self._extract_text(resp.json())
                    if text:
                        logger.info("CustomAPIClient: success (len=%d)", len(text))
                        return LLMResponse(text=text, success=True, source="custom_api")

                error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning("CustomAPIClient: attempt %d failed: %s", attempt + 1, error_msg)

            except Exception as e:
                logger.warning("CustomAPIClient: attempt %d exception: %s", attempt + 1, e)

            if attempt < self.retries:
                time.sleep(10 * (attempt + 1))

        return LLMResponse(text=None, success=False, error="All retries exhausted")

    def _extract_text(self, data: dict) -> Optional[str]:
        """Extract text from API response JSON."""
        if not isinstance(data, dict):
            return None

        if 'answer' in data:
            answer = data['answer']
            if isinstance(answer, dict) and 'text' in answer:
                text = answer['text']
                if isinstance(text, str) and text.strip():
                    return text.strip()

        for key in ('answer', 'text', 'response', 'content'):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            elif isinstance(value, dict):
                text = value.get('text') or value.get('content')
                if isinstance(text, str) and text.strip():
                    return text.strip()

        return None

    def set_mode(self, mode: str) -> bool:
        """Set API mode (idempotent)."""
        if not self.api_url:
            return False

        target_mode = 'Thinking'
        if CustomAPIClient._current_mode == target_mode:
            return True

        try:
            api_root = self.api_url.split('/api', 1)[0]
            resp = requests.post(
                f"{api_root}/api/set_mode",
                json={"mode": target_mode},
                timeout=10
            )
            if resp.status_code == 200:
                logger.info("CustomAPIClient: switched to mode '%s'", target_mode)
                CustomAPIClient._current_mode = target_mode
                return True
            return False
        except Exception as e:
            logger.error("CustomAPIClient: error setting mode: %s", e)
            return False

    def new_chat(self) -> bool:
        """Trigger a new chat session."""
        if not self.api_url:
            return False
        try:
            api_root = self.api_url.split('/api', 1)[0]
            resp = requests.post(f"{api_root}/api/new_chat", json={})
            return resp.status_code == 200
        except Exception:
            return False


class GeminiRestClient:
    """
    Client for Google's Gemini REST API.
    Used by the editor's /api/improve and /api/optimize_all endpoints.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        timeout: int = 60,
    ):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY', '')
        self.model = model
        self.timeout = timeout
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Generate text using Google Gemini REST API."""
        if not self.api_key:
            return LLMResponse(text=None, success=False, error="Gemini API key not configured")

        try:
            resp = requests.post(
                self.api_url,
                params={"key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens,
                    }
                },
                timeout=self.timeout,
            )

            if resp.status_code == 429:
                return LLMResponse(
                    text=None,
                    success=False,
                    error="Gemini APIの制限（Too Many Requests）に達しました。しばらく待ってから再試行してください。",
                    source="gemini_rest"
                )

            resp.raise_for_status()
            result = resp.json()
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
            logger.info("GeminiRestClient: success (len=%d)", len(generated_text))
            return LLMResponse(text=generated_text, success=True, source="gemini_rest")

        except requests.exceptions.RequestException as e:
            return LLMResponse(text=None, success=False, error=f"Gemini API error: {e}")
        except (KeyError, IndexError) as e:
            return LLMResponse(text=None, success=False, error=f"Gemini response parse error: {e}")

    def generate_json(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """Generate and extract JSON from Gemini response."""
        response = self.generate(prompt, temperature, max_tokens)
        if not response.success or not response.text:
            return response

        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                return LLMResponse(
                    text=json.dumps(parsed, ensure_ascii=False),
                    success=True,
                    source=response.source
                )
            except json.JSONDecodeError as e:
                return LLMResponse(text=None, success=False, error=f"JSON parse error: {e}")
        else:
            return LLMResponse(text=None, success=False, error="JSONを抽出できませんでした")


class LLMService:
    """
    Facade for text generation.
    Combines CustomAPIClient (Chrome wrapper) and GeminiRestClient (REST API).
    
    Extracted from src/services/gemini_service.py GeminiService.
    """

    def __init__(
        self,
        custom_client: Optional[CustomAPIClient] = None,
        gemini_client: Optional[GeminiRestClient] = None,
    ):
        self.custom_client = custom_client or CustomAPIClient()
        self.gemini_client = gemini_client

    def generate_text(
        self,
        prompt: str,
        mode: Optional[str] = None,
    ) -> str:
        """
        Generate text using CustomAPIClient.
        
        Returns:
            Generated text string
            
        Raises:
            RuntimeError: If generation fails
        """
        response = self.custom_client.generate(prompt, mode=mode or 'Thinking')

        if response.success and response.text:
            return response.text

        raise RuntimeError(f"Text generation failed: {response.error or 'unknown error'}")

    def generate_with_gemini(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """
        Generate using Gemini REST API.
        Requires gemini_client to be configured.
        """
        if not self.gemini_client:
            return LLMResponse(text=None, success=False, error="GeminiRestClient not configured")
        return self.gemini_client.generate(prompt, temperature, max_tokens)

    def generate_json_with_gemini(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> LLMResponse:
        """
        Generate JSON using Gemini REST API.
        Requires gemini_client to be configured.
        """
        if not self.gemini_client:
            return LLMResponse(text=None, success=False, error="GeminiRestClient not configured")
        return self.gemini_client.generate_json(prompt, temperature, max_tokens)

    def start_new_session(self) -> bool:
        """Start a new chat session via CustomAPIClient."""
        logger.info("LLMService: Starting new chat session.")
        return self.custom_client.new_chat()
