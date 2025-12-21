import contextvars
import logging
import json
import os
import inspect
from datetime import datetime
from typing import Optional, Any

# Context variable to hold the current log file path
_gemini_log_file = contextvars.ContextVar("gemini_log_file", default=None)

logger = logging.getLogger(__name__)

def set_log_file(filepath: str):
    """Sets the log file path for the current context."""
    _gemini_log_file.set(filepath)
    # Ensure directory exists if path has directory components
    dirname = os.path.dirname(filepath)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    logger.info(f"Gemini interaction logging enabled: {filepath}")

def get_log_file() -> Optional[str]:
    """Gets the current log file path."""
    return _gemini_log_file.get()

def log_gemini_interaction(module_name: str, prompt: Any, response: Any, model: str = "unknown"):
    """
    Logs a Gemini interaction to the context-specific file.

    Args:
        module_name: Name of the module initiating the call.
        prompt: The data sent to Gemini (str or list).
        response: The response received from Gemini (str).
        model: The model used.
    """
    filepath = get_log_file()
    if not filepath:
        return

    entry = {
        "timestamp": datetime.now().isoformat(),
        "module": module_name,
        "model": model,
        "prompt": prompt,
        "response": response
    }

    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to write to Gemini log file: {e}")

def get_caller_module_name() -> str:
    """Attempts to retrieve the caller's module name."""
    try:
        # Inspect stack to find the caller outside of this module and GeminiService
        stack = inspect.stack()
        for frame in stack:
            mod_name = frame.frame.f_globals.get('__name__')
            if mod_name and not mod_name.startswith('src.utils.gemini_logger') and not mod_name.endswith('gemini_service'):
                return mod_name
        return "unknown"
    except Exception:
        return "unknown"


def log_final_article_state(user_id: str, article: dict, quality: dict, extra: dict = None):
    """
    Logs the final article state and quality check to logs/posts/final_quality_{timestamp}_{user_id}.jsonl
    Args:
        user_id: The user ID associated with the article.
        article: Dict containing article info (title, content, tags, etc).
        quality: Dict containing quality check results (review_feedback, has_issues, suggestions, etc).
        extra: Optional dict for additional info (e.g., affiliate link status).
    """
    # Prefer the current Gemini session log file (one per article). If not set, fall back to per-article file.
    filepath = get_log_file()
    if not filepath:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'posts')
        os.makedirs(log_dir, exist_ok=True)
        filename = f"final_quality_{timestamp}_{user_id}.jsonl"
        filepath = os.path.join(log_dir, filename)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "article": article,
        "quality": quality,
        "extra": extra or {}
    }
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to write final article state log: {e}")
