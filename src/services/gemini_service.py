"""
Refactored GeminiService with clear separation of concerns.

Architecture:
- GeminiService: Main interface (facade pattern)
- CustomAPIClient: Handles custom API communication
- ClaudeClient: Handles Claude API communication
- Each client is independently testable and mockable
"""

import logging
import os
import requests
import time
from typing import Optional, Protocol
from dataclasses import dataclass

from src.services.claude_service import ClaudeService
from src.services.claude4_service import Claude4Service
from src.utils import gemini_logger

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """Standardized API response."""
    text: Optional[str]
    success: bool
    error: Optional[str] = None
    source: Optional[str] = None


class TextGeneratorProtocol(Protocol):
    """Protocol for text generation clients."""
    
    def generate(self, prompt: str, **kwargs) -> APIResponse:
        """Generate text from prompt."""
        ...


class CustomAPIClient:
    """Client for custom LLM API (e.g., Chrome extension wrapper)."""
    
    # Class-level variable to track the current mode across instances
    _current_mode: Optional[str] = None
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        bearer_token: Optional[str] = None,
        timeout: int = 600, # Increased to 10 minutes for Thinking mode
        retries: int = 2
    ):
        self.api_url = api_url or os.getenv(
            'CUSTOM_LLM_API_URL',
            os.getenv('LOCAL_GEMINI_API_URL', 'http://localhost:3000/api/ask')
        )
        self.bearer_token = bearer_token or os.getenv('CUSTOM_LLM_API_BEARER')
        self.timeout = timeout
        self.retries = retries
    
    def generate(
        self,
        prompt: str,
        mode: Optional[str] = None,
        **kwargs
    ) -> APIResponse:
        """
        Generate text using custom API.
        Only 'Thinking' mode is allowed.
        """
        if not self.api_url:
            return APIResponse(
                text=None,
                success=False,
                error="API URL not configured"
            )
        
        # Always use Thinking mode regardless of what is requested
        self.set_mode('Thinking')

        logger.info("CustomAPIClient: calling ask (timeout=%ds)", self.timeout)
        
        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers['Authorization'] = f"Bearer {self.bearer_token}"
        
        # Only 'prompt' is allowed in /api/ask to ensure strict separation
        # FIX: Escape newlines to prevent early submission in browser automation (old error fix)
        payload = {
            "prompt": prompt.replace('\n', '\\n')
        }
        
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
                        return APIResponse(
                            text=text,
                            success=True,
                            source="custom_api"
                        )
                
                # Non-200 or no text
                error_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
                logger.warning("CustomAPIClient: attempt %d failed: %s", attempt + 1, error_msg)
                
            except Exception as e:
                logger.warning("CustomAPIClient: attempt %d exception: %s", attempt + 1, e)
                
            if attempt < self.retries:
                time.sleep(10 * (attempt + 1)) # Wait longer between retries for Thinking mode
        
        return APIResponse(
            text=None,
            success=False,
            error="All retries exhausted"
        )
    
    def _extract_text(self, data: dict) -> Optional[str]:
        """Extract text from API response JSON."""
        if not isinstance(data, dict):
            return None
        
        # Try nested answer.text
        if 'answer' in data:
            answer = data['answer']
            if isinstance(answer, dict) and 'text' in answer:
                text = answer['text']
                if isinstance(text, str) and text.strip():
                    return text.strip()
        
        # Try direct fields
        for key in ('answer', 'text', 'response', 'content'):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            elif isinstance(value, dict):
                text = value.get('text') or value.get('content')
                if isinstance(text, str) and text.strip():
                    return text.strip()
        
        # Fallback: if images are present but no text, return the first image URL (Scavenger support)
        answer_obj = data.get('answer', {})
        if isinstance(answer_obj, dict):
            images = answer_obj.get('images', [])
            if images and isinstance(images, list):
                first_image = images[0]
                url = first_image.get('src') or first_image.get('download_url')
                if url:
                    logger.info("No text found but image URL detected. Returning as __IMAGE_URL__.")
                    return f"__IMAGE_URL__{url}"
        
        return None
    
    def set_mode(self, mode: str) -> bool:
        """
        Set API mode (e.g., for Chrome extension).
        Idempotent: skips if mode is already set.
        """
        if not self.api_url:
            logger.error("CustomAPIClient: API URL not configured")
            return False
        
        # Force 'Thinking' mode globally as per current requirement
        target_mode = 'Thinking'
        
        if CustomAPIClient._current_mode == target_mode:
            # logger.debug(f"CustomAPIClient: mode already set to {target_mode}, skipping.")
            return True
        
        try:
            api_root = self.api_url.split('/api', 1)[0]
            resp = requests.post(
                f"{api_root}/api/set_mode",
                json={"mode": target_mode},
                timeout=10 # Mode switch should be fast
            )
            
            if resp.status_code == 200:
                logger.info("CustomAPIClient: successfully switched to mode '%s'", target_mode)
                CustomAPIClient._current_mode = target_mode
                return True
            else:
                logger.error("CustomAPIClient: failed to set mode (status=%s)", resp.status_code)
                return False
                
        except Exception as e:
            logger.error("CustomAPIClient: error setting mode: %s", e)
            return False

    def new_chat(self) -> bool:
        """
        Trigger a new chat session in the custom API.
        
        Returns:
            True if successful
        """
        if not self.api_url:
            logger.error("CustomAPIClient: API URL not configured")
            return False
        
        try:
            api_root = self.api_url.split('/api', 1)[0]
            resp = requests.post(
                f"{api_root}/api/new_chat",
                json={} # No payload needed
            )
            
            if resp.status_code == 200:
                logger.info("CustomAPIClient: successfully triggered new chat")
                return True
            else:
                logger.error(
                    "CustomAPIClient: failed to trigger new chat (status=%s)",
                    resp.status_code
                )
                return False
                
        except Exception as e:
            logger.error("CustomAPIClient: error triggering new chat: %s", e)
            return False

    def press_image_icon(self) -> bool:
        """
        Instruct the browser to press the 'Create images' icon.
        
        Returns:
            True if successful
        """
        if not self.api_url:
            logger.error("CustomAPIClient: API URL not configured")
            return False
        
        try:
            api_root = self.api_url.split('/api', 1)[0]
            resp = requests.post(
                f"{api_root}/api/press_image_icon",
                json={},
                timeout=30 # Handshake might take some time
            )
            
            if resp.status_code == 200:
                logger.info("CustomAPIClient: successfully triggered image icon press")
                return True
            else:
                logger.error(
                    "CustomAPIClient: failed to trigger image icon press (status=%s)",
                    resp.status_code
                )
                return False
                
        except Exception as e:
            logger.error("CustomAPIClient: error triggering image icon press: %s", e)
            return False

    def clear_image_mode(self) -> bool:
        """
        Instruct the browser to clear/exit the image generation mode.
        
        Returns:
            True if successful
        """
        if not self.api_url:
            logger.error("CustomAPIClient: API URL not configured")
            return False
        
        try:
            api_root = self.api_url.split('/api', 1)[0]
            resp = requests.post(
                f"{api_root}/api/clear_image_mode",
                json={},
                timeout=20
            )
            
            if resp.status_code == 200:
                logger.info("CustomAPIClient: successfully cleared image mode")
                return True
            else:
                logger.warning(
                    "CustomAPIClient: failed to clear image mode (status=%s). It might not be active.",
                    resp.status_code
                )
                return False
                
        except Exception as e:
            logger.error("CustomAPIClient: error clearing image mode: %s", e)
            return False


class ClaudeClient:
    """Client for Claude API services."""
    
    def __init__(self):
        self.claude_service = None
        self.claude4_service = None
        
        try:
            self.claude_service = ClaudeService()
            logger.info("ClaudeClient: initialized ClaudeService")
        except Exception as e:
            logger.warning("ClaudeClient: ClaudeService init failed: %s", e)
        
        try:
            self.claude4_service = Claude4Service()
            logger.info("ClaudeClient: initialized Claude4Service")
        except Exception as e:
            logger.debug("ClaudeClient: Claude4Service init failed: %s", e)
            self.claude4_service = None
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.0,
        **kwargs
    ) -> APIResponse:
        """
        Generate text using Claude.
        
        Args:
            prompt: Text prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            
        Returns:
            APIResponse with result
        """
        if not self.claude_service:
            return APIResponse(
                text=None,
                success=False,
                error="Claude service not initialized"
            )
        
        logger.info("ClaudeClient: generating text")
        
        try:
            result = self.claude_service.generate_text(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            if result:
                logger.info("ClaudeClient: success (len=%d)", len(result))
                return APIResponse(
                    text=result,
                    success=True,
                    source="claude"
                )
            else:
                return APIResponse(
                    text=None,
                    success=False,
                    error="Claude returned empty result"
                )
                
        except Exception as e:
            logger.error("ClaudeClient: generation failed: %s", e, exc_info=True)
            return APIResponse(
                text=None,
                success=False,
                error=f"Claude error: {e}"
            )
    
    def analyze_image(
        self,
        image_path: str,
        prompt: str = "この画像の内容をブログ記事で使えるように、簡潔かつ魅力的に説明してください。"
    ) -> APIResponse:
        """
        Analyze image using Claude.
        
        Args:
            image_path: Path to image
            prompt: Analysis prompt
            
        Returns:
            APIResponse with result
        """
        img_prompt = (
            f"{prompt}\n\n"
            f"画像ファイルパス: {image_path}\n\n"
            f"上記の画像をブログ記事向けに説明してください。"
        )
        
        # Try Claude4 first
        if self.claude4_service:
            logger.info("ClaudeClient: using Claude4 for image analysis")
            try:
                result = self.claude4_service.generate_content(
                    img_prompt,
                    max_tokens=800,
                    temperature=0.0
                )
                if result:
                    return APIResponse(
                        text=result,
                        success=True,
                        source="claude4_image"
                    )
            except Exception as e:
                logger.warning("ClaudeClient: Claude4 image analysis failed: %s", e)
        
        # Fallback to Claude
        if not self.claude_service:
            return APIResponse(
                text=None,
                success=False,
                error="No Claude service available for image analysis"
            )
        
        logger.info("ClaudeClient: using Claude for image analysis")
        try:
            result = self.claude_service.generate_text(
                img_prompt,
                max_tokens=800,
                temperature=0.0
            )
            if result:
                return APIResponse(
                    text=result,
                    success=True,
                    source="claude_image"
                )
            else:
                return APIResponse(
                    text=None,
                    success=False,
                    error="Claude returned empty result"
                )
        except Exception as e:
            logger.error("ClaudeClient: image analysis failed: %s", e)
            return APIResponse(
                text=None,
                success=False,
                error=f"Image analysis error: {e}"
            )


class GeminiService:
    """
    Facade for text generation with fallback strategy.
    
    This service tries CustomAPIClient first, then falls back to ClaudeClient
    based on configuration. Designed for easy testing and mocking.
    """
    
    def __init__(
        self,
        custom_client: Optional[CustomAPIClient] = None,
        claude_client: Optional[ClaudeClient] = None,
        enable_claude_fallback: Optional[bool] = None,
        blog_config=None
    ):
        """
        Initialize GeminiService.
        
        Args:
            custom_client: Custom API client (auto-created if None)
            claude_client: Claude client (auto-created if None)
            enable_claude_fallback: Enable Claude fallback (from env if None)
            blog_config: (optional, ignored for backward compatibility)
        """
        self._test_mode = False
        
        # Dependency injection for easy testing
        self.custom_client = custom_client or CustomAPIClient()
        self.claude_client = claude_client or ClaudeClient()
        
        # Fallback configuration
        if enable_claude_fallback is None:
            self.enable_claude_fallback = os.getenv(
                'CUSTOM_LLM_FALLBACK_TO_CLAUDE', 'false'
            ).lower() in ('1', 'true', 'yes')
        else:
            self.enable_claude_fallback = enable_claude_fallback
        
        logger.info(
            "GeminiService initialized (claude_fallback=%s)",
            self.enable_claude_fallback
        )
    
    def generate_text(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        max_tokens: int = 3500,
        temperature: float = 0.4,
        task_priority: str = "normal",
        mode: Optional[str] = None
    ) -> str:
        """
        Generate text with fallback strategy.
        
        Args:
            prompt: Text prompt
            model_name: Model name (unused, for compatibility)
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            task_priority: Priority (unused, for compatibility)
            mode: API mode (Defaults to 'Thinking' per user request)
            
        Returns:
            Generated text
            
        Raises:
            RuntimeError: If all generation methods fail
        """
        # Default to 'Thinking' mode if not specified
        if not mode:
            mode = 'Thinking'

        # Try custom API first
        response = self.custom_client.generate(
            prompt,
            mode=mode
        )
        
        if response.success and response.text:
            self._log_interaction(prompt, response.text, response.source)
            return response.text
        
        logger.warning(
            "Custom API failed: %s",
            response.error or "unknown error"
        )
        
        # Try Claude fallback if enabled
        if self.enable_claude_fallback:
            logger.info("Attempting Claude fallback")
            response = self.claude_client.generate(
                prompt,
                max_tokens=max_tokens or 2000,
                temperature=temperature or 0.0
            )
            
            if response.success and response.text:
                self._log_interaction(prompt, response.text, response.source)
                return response.text
            
            logger.error("Claude fallback failed: %s", response.error)
        else:
            logger.info("Claude fallback disabled")
        
        # All methods failed
        raise RuntimeError(
            f"Text generation failed - Custom API: {response.error or 'failed'}, "
            f"Claude fallback: {'disabled' if not self.enable_claude_fallback else 'failed'}"
        )

    def generate(
        self,
        prompt: str,
        context_text: str = "",
        web_context: str = "",
        video_context: str = "",
        blog_name: str = "",
        **kwargs
    ) -> dict:
        """
        Backwards-compatible adapter used by older callers that expect a dict result.
        Merges context pieces into a single prompt, delegates to `generate_text`, and
        attempts to parse JSON from the response. On parse failure returns `{'raw': <text>}`.
        """
        # Merge contexts into a single prompt so callers can pass structured args
        merged = prompt
        if context_text:
            merged += "\n\n[Context]\n" + context_text
        if web_context:
            merged += "\n\n[WebContext]\n" + web_context
        if video_context:
            merged += "\n\n[VideoContext]\n" + video_context
        if blog_name:
            merged += f"\n\n[Blog]: {blog_name}"

        # Delegate to the normal text generation method
        response_text = self.generate_text(merged, **kwargs)

        # Try to parse JSON out of the response (strip code fences if present)
        try:
            import re, json
            cleaned = re.sub(r"```(?:json)?\s*|\s*```", "", response_text).strip()
            return json.loads(cleaned) if cleaned else {}
        except Exception:
            logger.warning("GeminiService.generate: failed to parse JSON, returning raw text")
            return {"raw": response_text}

    def analyze_image_from_path(
        self,
        image_path: str,
        prompt: str = "この画像の内容をブログ記事で使えるように、簡潔かつ魅力的に説明してください。"
    ) -> str:
        """
        Analyze image using Claude.
        
        Args:
            image_path: Path to image
            prompt: Analysis prompt
            
        Returns:
            Analysis text
            
        Raises:
            RuntimeError: If analysis fails
        """
        response = self.claude_client.analyze_image(image_path, prompt)
        
        if response.success and response.text:
            self._log_interaction(
                f"[Image: {image_path}] {prompt}",
                response.text,
                response.source
            )
            return response.text
        
        raise RuntimeError(
            f"Image analysis failed: {response.error or 'unknown error'}"
        )
    
    def set_wrapper_mode(self, mode: str) -> bool:
        """
        Set custom API mode.
        
        Args:
            mode: Mode to set
            
        Returns:
            True if successful
        """
        return self.custom_client.set_mode(mode)

    def start_new_session(self) -> bool:
        """
        Explicitly start a new chat session.
        This should be called at the beginning of a workflow.
        """
        logger.info("GeminiService: Starting new chat session.")
        return self.custom_client.new_chat()

    def press_image_icon(self) -> bool:
        """
        Instruct the browser to press the 'Create images' icon.
        """
        logger.info("GeminiService: Requesting image icon press.")
        return self.custom_client.press_image_icon()

    def clear_image_mode(self) -> bool:
        """
        Instruct the browser to clear the 'Create images' mode.
        """
        logger.info("GeminiService: Requesting image mode clear.")
        return self.custom_client.clear_image_mode()
    
    def set_test_mode(self, enabled: bool):
        """Enable or disable test mode."""
        self._test_mode = enabled
        logger.info("GeminiService test mode=%s", enabled)
    
    def _log_interaction(self, prompt: str, response: str, source: Optional[str]):
        """Log interaction to gemini_logger."""
        try:
            caller = gemini_logger.get_caller_module_name()
            gemini_logger.log_gemini_interaction(caller, prompt, response, source)
        except Exception as e:
            logger.warning("Failed to log interaction: %s", e)
