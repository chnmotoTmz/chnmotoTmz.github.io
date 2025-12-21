"""Utilities to fetch cookies from a local Gemini API wrapper and format them for requests.

The wrapper exposes `/api/cookies` (GET) which returns JSON like:
{
  "success": true,
  "cookies": {
     "google.com": [ {"name":"__Secure-1PSID","value":"..."}, ...]
  }
}

This module provides a small helper to fetch cookies and format a Cookie header.
"""

from typing import Dict, Any
import logging
import requests

logger = logging.getLogger(__name__)


def fetch_cookies_from_wrapper(api_root: str, timeout: int = 10) -> Dict[str, str]:
    """Fetch cookies from the given wrapper root URL and return a flat mapping name->value.

    Args:
        api_root: Base URL of the wrapper (e.g. http://localhost:3000)
        timeout: request timeout in seconds

    Returns:
        dict mapping cookie name to cookie value. Empty dict on failure.
    """
    if not api_root:
        return {}
    url = api_root.rstrip('/') + '/api/cookies'
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            logger.warning("Failed to fetch cookies from %s: status=%s", url, resp.status_code)
            return {}
        data = resp.json()
        cookies_field = data.get('cookies')
        if not cookies_field:
            logger.debug("No cookies field in response from %s", url)
            return {}

        flat: Dict[str, str] = {}
        # cookies_field may be a dict mapping domain -> list of cookie dicts
        if isinstance(cookies_field, dict):
            for domain, cookie_list in cookies_field.items():
                if not isinstance(cookie_list, list):
                    continue
                for c in cookie_list:
                    name = c.get('name')
                    value = c.get('value')
                    if name and value:
                        flat[name] = value
        # or it may be a list directly (from /api/request_cookies)
        elif isinstance(cookies_field, list):
            for c in cookies_field:
                name = c.get('name')
                value = c.get('value')
                if name and value:
                    flat[name] = value

        # Normalize to essential cookie set expected by python-gemini-api
        required = ['__Secure-1PSID', '__Secure-1PSIDTS', '__Secure-1PSIDCC']
        essential = {k: v for k, v in flat.items() if k in required}

        if len(essential) == len(required):
            logger.info(f"Successfully fetched essential cookies: {list(essential.keys())}")
            return essential
        else:
            missing = [k for k in required if k not in essential]
            if essential:
                logger.warning(f"Partial cookie set fetched; missing required cookies: {missing}")
                return essential
            logger.warning(f"No essential cookies found in wrapper response; missing: {missing}")
            return {}
    except Exception as e:
        logger.warning("Error fetching cookies from wrapper %s: %s", api_root, e)
        return {}


def format_cookie_header(cookies: Dict[str, str]) -> str:
    """Return a Cookie header string for the given mapping."""
    return '; '.join(f"{k}={v}" for k, v in cookies.items()) if cookies else ''
