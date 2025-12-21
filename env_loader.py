"""
Unified YAML environment loader for the whole project.
Loads repo_root/config/env.yml into process environment (non-destructive: only sets when unset).
Also loads .env files (.env.production, .env.blog1, etc.) if they exist.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict
import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _read_yaml(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            with path.open('r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _read_dotenv(path: Path) -> Dict[str, str]:
    """Read .env file format (KEY=VALUE pairs, ignore comments and blank lines)."""
    result = {}
    try:
        if path.exists():
            with path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        result[key] = value
    except Exception:
        pass
    return result


def load() -> None:
    """
    Load environment from multiple sources (non-destructive):
    1. config/env.yml (canonical YAML configuration)
    2. .env.production (if it exists)
    3. .env.blog1, .env.blog2, etc. (blog-specific configs)
    
    Only sets env vars that are not already set.
    """
    root = _repo_root()
    
    # First, load from config/env.yml
    env_yaml = root / 'config' / 'env.yml'
    data = _read_yaml(env_yaml)
    for k, v in data.items():
        if not isinstance(k, str):
            continue
        if os.getenv(k) is None:
            os.environ[k] = str(v)
    
    # Load from standard .env if it exists
    env_base = root / '.env'
    data = _read_dotenv(env_base)
    for k, v in data.items():
        if os.getenv(k) is None:
            os.environ[k] = v
    
    # Second, try loading .env.production if it exists
    env_prod = root / '.env.production'
    data = _read_dotenv(env_prod)
    for k, v in data.items():
        if os.getenv(k) is None:
            os.environ[k] = v

    # Also support development override files: .env.develop and .env.development
    # These are helpful when running locally and should take precedence when present
    for dev_file_name in ('.env.develop', '.env.development'):
        env_dev = root / dev_file_name
        data = _read_dotenv(env_dev)
        # Development files should override existing environment values so local dev secrets take precedence
        for k, v in data.items():
            os.environ[k] = v

    # Third, try loading .env.blog* files
    # Look for .env.blog1, .env.blog2, etc.
    for env_file in sorted(root.glob('.env.blog*')):
        data = _read_dotenv(env_file)
        for k, v in data.items():
            if os.getenv(k) is None:
                os.environ[k] = v
