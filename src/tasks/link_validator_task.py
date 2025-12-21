import re
import requests
import time
from typing import Dict, Any
from src.framework.base_task import BaseTaskModule

class LinkValidatorTask(BaseTaskModule):
    """
    Checks all URLs in the article for dead/broken links.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.timeout = config.get("timeout", 7)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        title = inputs.get("title", "")
        content = inputs.get("content", "")

        md_links = re.findall(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', content)
        raw_urls = set(re.findall(r'(https?://[\w\-\./%#?=&;:_~]+)', content))
        used_urls = set(u for _, u in md_links)
        all_urls = list(used_urls) + list(raw_urls - used_urls)

        new_content = content
        for url in all_urls:
            try:
                resp = requests.head(url, allow_redirects=True, timeout=self.timeout)
                if resp.status_code >= 400:
                    # Remove broken links but keep text
                    new_content = re.sub(rf'\[([^\]]+)\]\({re.escape(url)}\)', r'\1', new_content)
                    new_content = re.sub(rf'(?<!\()(?<!\[){re.escape(url)}', '', new_content)
            except Exception:
                new_content = re.sub(rf'\[([^\]]+)\]\({re.escape(url)}\)', r'\1', new_content)
                new_content = re.sub(rf'(?<!\()(?<!\[){re.escape(url)}', '', new_content)

        return {"title": title, "content": new_content}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "LinkValidatorTask",
            "description": "Validates links in the content."
        }