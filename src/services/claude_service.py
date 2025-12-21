"""
Minimal Claude (Anthropic) HTTP client wrapper.

Usage:
- Set environment `CLAUDE_API_KEY` with your API key.
- Optionally set `CLAUDE_API_URL` to a custom endpoint. Defaults to Anthropic.
- Optionally set `CLAUDE_MODEL`, default `claude-haiku-4`.
"""
import os
import logging
import requests
import base64
import mimetypes
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class ClaudeService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, api_url: Optional[str] = None):
        self.api_key = api_key or os.getenv('CLAUDE_API_KEY')
        # allow model aliases and safer defaults via env
        raw_model = model or os.getenv('CLAUDE_MODEL', 'claude-haiku-4')
        self.model_aliases = self._parse_aliases(os.getenv('CLAUDE_MODEL_ALIASES', ''))
        self.model = self._resolve_alias(raw_model)

        # Allow overriding the URL (useful for proxies/wrappers)
        self.api_url = api_url or os.getenv('CLAUDE_API_URL', 'https://api.anthropic.com/v1/complete')
        # Messages API support (optional): allows sending image blocks (base64 or URL)
        self.use_messages = os.getenv('CLAUDE_USE_MESSAGES_API', 'false').lower() in ('1', 'true', 'yes')
        self.messages_api_url = os.getenv('CLAUDE_MESSAGES_API_URL', 'https://api.anthropic.com/v1/messages')
        # Optional separate model for messages API (falls back to resolved model)
        self.messages_model = os.getenv('CLAUDE_MESSAGES_MODEL')
        if not self.api_key:
            logger.warning('CLAUDE_API_KEY is not set; ClaudeService will fail on requests')

    def _guess_media_type(self, path_or_url: str) -> str:
        """Guess a media type (mime) from a filename or URL."""
        media_type, _ = mimetypes.guess_type(path_or_url)
        return media_type or 'application/octet-stream'

    def _file_to_base64(self, path: str, max_bytes: int = 5 * 1024 * 1024) -> str:
        """Read a local file and return base64-encoded data (no header). Raises on issues."""
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        size = os.path.getsize(path)
        if size > max_bytes:
            raise ValueError(f'File too large to inline as base64 ({size} bytes)')
        with open(path, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode('ascii')

    def _build_messages_body(self, prompt: str, images: Optional[List[Dict]] = None, max_tokens: int = 2000, temperature: float = 0.0) -> Dict:
        """Build a Messages API request body with optional image blocks.

        `images` is a list of dicts with keys: `type` ('url'|'base64'|'path'), `data` (str), optional `media_type`.
        """
        model = self.messages_model or self.model
        content_blocks = []
        if images:
            for img in images:
                t = img.get('type')
                raw = img.get('data')
                if t == 'path':
                    b64 = self._file_to_base64(raw)
                    media_type = img.get('media_type') or self._guess_media_type(raw)
                    content_blocks.append({'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': b64}})
                elif t == 'base64':
                    media_type = img.get('media_type') or 'image/jpeg'
                    content_blocks.append({'type': 'image', 'source': {'type': 'base64', 'media_type': media_type, 'data': raw}})
                else:  # treat as URL
                    media_type = img.get('media_type') or self._guess_media_type(raw)
                    content_blocks.append({'type': 'image', 'source': {'type': 'url', 'media_type': media_type, 'url': raw}})

        # Append user's text as a text block
        content_blocks.append({'type': 'text', 'text': prompt})

        body = {
            'model': model,
            'max_tokens': int(max_tokens),
            'temperature': float(temperature),
            'messages': [
                {
                    'role': 'user',
                    'content': content_blocks
                }
            ]
        }
        return body

    def _extract_text_from_response(self, data: Dict) -> Optional[str]:
        """Try multiple response shapes to extract a text string.

        This supports a variety of Anthropic/Claude response shapes seen in the
        wild, including classic `completion` keys, a top-level `content` list,
        and the Messages API shape where `message` wraps `content` blocks.
        """
        # Direct legacy fields
        if not isinstance(data, dict):
            return None
        for key in ('completion', 'output', 'text'):
            v = data.get(key)
            if isinstance(v, str) and v.strip():
                return v

        # Top-level content array (Messages API variant) e.g.
        # {'content': [{'type': 'text', 'text': '...'}, ...]}
        content = data.get('content')
        if isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict):
                    txt = c.get('text') or c.get('content') or c.get('html')
                    if isinstance(txt, str):
                        parts.append(txt)
                elif isinstance(c, str):
                    parts.append(c)
            if parts:
                return '\n'.join(parts)

        # Messages API shape: {"message": {"content": [ ... ] } }
        msg = data.get('message') or data.get('response')
        if isinstance(msg, dict):
            content = msg.get('content') or msg.get('content_parts') or []
            parts = []
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict):
                        # text may live under 'text' or 'content' or 'html'
                        text = c.get('text') or c.get('content') or c.get('html')
                        if isinstance(text, str):
                            parts.append(text)
                    elif isinstance(c, str):
                        parts.append(c)
            if parts:
                return '\n'.join(parts)

        # Some wrappers return nested completion dict
        comp = data.get('completion')
        if isinstance(comp, dict):
            text = comp.get('text') or comp.get('content')
            if isinstance(text, str):
                return text

        return None

    def _parse_aliases(self, alias_str: str) -> dict:
        """Parse alias definitions like 'old1:new1,old2:new2' into dict."""
        aliases = {}
        if not alias_str:
            return aliases
        for pair in alias_str.split(','):
            if ':' in pair:
                old, new = pair.split(':', 1)
                aliases[old.strip()] = new.strip()
        return aliases

    def _resolve_alias(self, model_name: str) -> str:
        """Resolve model alias if configured."""
        if not model_name:
            return model_name
        resolved = self.model_aliases.get(model_name, model_name)
        if resolved != model_name:
            logger.info('Resolved Claude model alias %s -> %s', model_name, resolved)
        return resolved
    def generate_text(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.0, images: Optional[List[Dict]] = None) -> Optional[str]:
        """Generate text using Claude-compatible HTTP API.

        This is a lightweight wrapper and intentionally conservative about request shape.
        It supports Anthropic's classic `complete` endpoint. If you use a different
        Claude offering or wrapper, set `CLAUDE_API_URL` accordingly.
        """
        headers = {
            'Content-Type': 'application/json',
        }
        if self.api_key:
            # Some Anthropic/Claude deployments expect an 'x-api-key' header
            # while others accept Bearer tokens. Provide both to maximize compatibility.
            headers['Authorization'] = f'Bearer {self.api_key}'
            headers['x-api-key'] = self.api_key
        # Include Anthropic version header if provided (some endpoints require it)
        anthro_ver = os.getenv('CLAUDE_API_VERSION')
        if anthro_ver:
            headers['anthropic-version'] = anthro_ver
        else:
            # sensible default that works for many classic endpoints
            headers['anthropic-version'] = '2023-06-01'

        # Prefer the Messages API when either configured or when images are provided;
        # Messages API supports image blocks (base64/url/path) while the classic
        # `complete` endpoint often does not for newer image-capable models.
        if self.use_messages or images:
            body = self._build_messages_body(prompt, images=images, max_tokens=max_tokens, temperature=temperature)
            url = self.messages_api_url
        else:
            body = {
                'model': self.model,
                # Anthropic 'complete' endpoint expects the prompt to be conversational,
                # starting with a Human turn. Normalize if necessary.
                'prompt': prompt if prompt.strip().startswith('\n\nHuman:') else f"\n\nHuman: {prompt}\n\nAssistant:",
                'max_tokens_to_sample': int(max_tokens),
                'temperature': float(temperature),
            }
            url = self.api_url

        try:
            # ensure req_id is always defined so we don't raise UnboundLocalError when handling non-JSON errors
            req_id = None
            logger.debug('Calling Claude API url=%s model=%s tokens=%s messages=%s', url, self.model, max_tokens, bool(self.use_messages))
            resp = requests.post(url, json=body, headers=headers, timeout=300)
            if resp.status_code == 200:
                data = resp.json()
                text = self._extract_text_from_response(data)
                if isinstance(text, str):
                    return text
                logger.warning('Claude API returned unexpected JSON shape: %s', data)
                raise RuntimeError(f'Claude API returned unexpected JSON shape: {data}')
            else:
                # Surface authentication errors and other non-200s as exceptions so callers
                # (especially image analysis which MUST use Anthropic) can react appropriately.
                body_preview = resp.text[:1000]
                logger.error('Claude API error status=%s body=%s', resp.status_code, body_preview)
                if resp.status_code == 401:
                    raise PermissionError(f'Claude authentication error (401): {body_preview}')

                # Handle 400 responses that indicate the model is not supported on this endpoint
                # (e.g. "is not supported on this API. Please use the Messages API instead.")
                if resp.status_code == 400:
                    try:
                        err = resp.json()
                        # capture any request id present to aid diagnostics
                        req_id = err.get('request_id') or err.get('requestId') or err.get('id')
                        error_obj = err.get('error') or {}
                        err_type = error_obj.get('type')
                        err_msg = error_obj.get('message', '')
                        # If Anthropic tells us to use the Messages API, retry there
                        if err_type == 'invalid_request_error' and isinstance(err_msg, str) and 'messages api' in err_msg.lower():
                            logger.info('Detected endpoint-specific model support message; retrying with Messages API (request_id=%s)', req_id)
                            body_msg = self._build_messages_body(prompt, images=images, max_tokens=max_tokens, temperature=temperature)
                            resp2 = requests.post(self.messages_api_url, json=body_msg, headers=headers, timeout=300)
                            if resp2.status_code == 200:
                                data2 = resp2.json()
                                text = self._extract_text_from_response(data2)
                                if isinstance(text, str):
                                    return text
                                logger.warning('Messages API returned unexpected JSON: %s', data2)
                            else:
                                logger.warning('Messages API retry failed status=%s body=%s', resp2.status_code, resp2.text[:1000])
                    except ValueError:
                        # not JSON; nothing to do here
                        pass

                # Model not found errors are common when specifying non-existent models.
                # Try configured fallback model names before giving up. Detect model-not-found
                # more precisely by parsing the JSON error body when available.
                if resp.status_code == 404:
                    problem = None
                    try:
                        err = resp.json()
                        # common shape: {"type":"error","error":{"type":"not_found_error","message":"model: claude-haiku-4"},"request_id":"req_x"}
                        req_id = err.get('request_id') or err.get('requestId')
                        error_obj = err.get('error') or {}
                        err_type = error_obj.get('type')
                        err_msg = error_obj.get('message', '')
                        if err_type == 'not_found_error' or 'model' in err_msg.lower():
                            problem = 'model_not_found'
                        else:
                            # fallback heuristic
                            if 'model' in (err.get('message') or '').lower() or 'model' in resp.text.lower():
                                problem = 'model_not_found'
                    except ValueError:
                        # not JSON; fallback to simple text heuristic
                        if 'model' in body_preview.lower():
                            problem = 'model_not_found'

                    if problem == 'model_not_found':
                        # Try alias mapping if the original model maps to another
                        mapped = self._resolve_alias(self.model)
                        tried = set([self.model])
                        if mapped and mapped != self.model:
                            logger.info('Attempting alias-mapped model due to model-not-found: %s', mapped)
                            body_alt = dict(body)
                            body_alt['model'] = mapped
                            resp2 = requests.post(self.api_url, json=body_alt, headers=headers, timeout=300)
                            if resp2.status_code == 200:
                                data = resp2.json()
                                text = data.get('completion') or data.get('output') or data.get('text')
                                if isinstance(text, str):
                                    return text
                            logger.warning('Alias-mapped model %s failed status=%s', mapped, resp2.status_code)
                            tried.add(mapped)

                        # Use env-configured fallback candidates
                        env_candidates = os.getenv('CLAUDE_FALLBACK_MODELS', 'claude-2,claude-2.1,claude-instant')
                        candidates = [c.strip() for c in env_candidates.split(',') if c.strip()]
                        for alt in candidates:
                            if alt in tried:
                                continue
                            logger.info('Retrying Claude with fallback model: %s', alt)
                            body_alt = dict(body)
                            body_alt['model'] = alt
                            resp2 = requests.post(self.api_url, json=body_alt, headers=headers, timeout=300)
                            if resp2.status_code == 200:
                                data = resp2.json()
                                text = data.get('completion') or data.get('output') or data.get('text')
                                if isinstance(text, str):
                                    return text
                            logger.warning('Fallback model %s failed status=%s', alt, resp2.status_code)

                        logger.warning('All fallback models failed for request_id=%s', req_id)

                raise RuntimeError(f'Claude API error status={resp.status_code} body={body_preview} request_id={req_id}')
        except requests.exceptions.Timeout:
            logger.warning('Claude API request timed out')
            return None
        except requests.exceptions.RequestException as re:
            logger.error('Network error calling Claude API: %s', re)
            raise RuntimeError(f'Network error contacting Claude: {re}') from re
