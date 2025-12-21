"""
note.com unofficial API integration.
"""

import logging
import requests
import re
import time
from typing import Optional, Tuple, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

class NoteService:
    def __init__(self, cookies: Dict[str, str]):
        self.cookies = cookies
        self.session = requests.Session()
        self.base_url = "https://note.com/api"
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }

    def create_article(self, title: str, content: str) -> Optional[Tuple[str, str]]:
        try:
            data = {'body': content, 'name': title, 'template_key': None}
            response = self.session.post(f'{self.base_url}/v1/text_notes', cookies=self.cookies, headers=self.headers, json=data, timeout=30)
            if response.status_code in (200, 201):
                res = response.json().get('data', {})
                return res.get('id'), res.get('key')
        except Exception as e:
            logger.error(f"Note create error: {e}")
        return None

    def upload_image(self, image_path: str) -> Optional[Tuple[str, str]]:
        try:
            path = Path(image_path)
            if not path.exists(): return None
            with open(image_path, 'rb') as f:
                headers = {k: v for k, v in self.headers.items() if k != 'Content-Type'}
                response = self.session.post(f'{self.base_url}/v1/upload_image', cookies=self.cookies, headers=headers, files={'file': f}, timeout=60)
                if response.status_code == 200:
                    res = response.json().get('data', {})
                    return res.get('key'), res.get('url')
        except Exception as e:
            logger.error(f"Note upload error: {e}")
        return None

    def post_to_note_draft(self, title: str, markdown_content: str, image_path: Optional[str] = None) -> bool:
        try:
            res = self.create_article(title, markdown_content)
            if not res: return False
            article_id, _ = res
            
            image_key = None
            if image_path:
                img_res = self.upload_image(image_path)
                if img_res: image_key, _ = img_res

            data = {'body': markdown_content, 'name': title, 'status': 'draft'}
            if image_key: data['eyecatch_image_key'] = image_key
            
            response = self.session.put(f'{self.base_url}/v1/text_notes/{article_id}', cookies=self.cookies, headers=self.headers, json=data, timeout=30)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Note draft post error: {e}")
            return False