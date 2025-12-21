import yaml
import os
import re
from typing import Dict, Any, Optional

def _resolve_env_vars(config: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively resolves environment variable placeholders in the config."""
    for key, value in config.items():
        if isinstance(value, dict):
            config[key] = _resolve_env_vars(value)
        elif isinstance(value, str):
            match = re.match(r"\$\{(.+)\}", value)
            if match:
                env_var = match.group(1)
                config[key] = os.getenv(env_var)
    return config

class BlogConfig:
    _config: Optional[Dict[str, Any]] = None

    @classmethod
    def load_config(cls, path: str = 'blogs.yml') -> None:
        """Loads the blog configurations from a YAML file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)
                cls._config = _resolve_env_vars(raw_config)
        except FileNotFoundError:
            cls._config = {'blogs': {}}
            print(f"Warning: Configuration file not found at {path}.")
        except yaml.YAMLError as e:
            cls._config = {'blogs': {}}
            print(f"Error parsing YAML file at {path}: {e}")

    @classmethod
    def get_blog_config(cls, blog_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the configuration for a specific blog."""
        if cls._config is None:
            cls.load_config()

        return cls._config.get('blogs', {}).get(blog_id)

    @classmethod
    def get_all_blogs(cls) -> Dict[str, Any]:
        """Retrieves the configurations for all blogs."""
        if cls._config is None:
            cls.load_config()

        return cls._config.get('blogs', {})

    @classmethod
    def get_blog_config_by_destination(cls, destination: str) -> Optional[Dict[str, Any]]:
        """Finds a blog configuration by its LINE channel ID."""
        if cls._config is None:
            cls.load_config()

        for blog_id, config in cls._config.get('blogs', {}).items():
            if config.get('line_channel_id') == destination:
                return config
        return None

BlogConfig.load_config()
