"""
Hatena Blog service integration.
"""

import os
import logging
import requests
import hashlib
import random
import base64
from datetime import datetime
from xml.etree import ElementTree
from xml.dom import minidom
from typing import Dict, Optional, List, Any

from src.utils.markdown_converter import convert_custom_tags_to_markdown
from src.utils.product_linker import insert_product_links

logger = logging.getLogger(__name__)

class HatenaService:
    def __init__(self, blog_config: Dict[str, Any]):
        self.hatena_id = blog_config.get('hatena_id')
        self.blog_id = blog_config.get('hatena_blog_id')
        self.api_key = blog_config.get('hatena_api_key') or blog_config.get('api_key')

        if not all([self.hatena_id, self.blog_id, self.api_key]):
            raise ValueError("Hatena credentials incomplete.")
            
        self.base_url = f"https://blog.hatena.ne.jp/{self.hatena_id}/{self.blog_id}/atom"
    
    def publish_article(
        self, title: str, content: str, tags: Optional[List[str]] = None,
        category: str = "", draft: bool = False, content_type: str = "text/x-markdown",
        product_links: Optional[dict] = None
    ) -> Dict:
        content = convert_custom_tags_to_markdown(content)
        if product_links:
            content = insert_product_links(content, product_links)
            
        try:
            tags = tags or []
            if category: tags.append(category)
            
            entry_xml = self._create_entry_xml(title, content, tags=tags, draft=draft, content_type=content_type)
            response = self._post_to_hatena(entry_xml)
            
            if response and response.status_code == 201:
                result = self._parse_response(response.text)
                return {
                    'id': result.get('entry_id', ''),
                    'url': result.get('url', ''),
                    'status': 'published' if not draft else 'draft'
                }
            else:
                raise RuntimeError(f"Hatena API error: {response.status_code if response else 'N/A'}")
        except Exception as e:
            logger.error(f"Hatena publish error: {e}")
            raise

    def _create_entry_xml(self, title: str, content: str, tags: Optional[List[str]] = None, draft: bool = False, content_type: str = "text/x-markdown") -> str:
        tags = tags or []
        entry = ElementTree.Element('entry', {'xmlns': 'http://www.w3.org/2005/Atom', 'xmlns:app': 'http://www.w3.org/2007/app'})
        
        title_elem = ElementTree.SubElement(entry, 'title')
        title_elem.text = title
        
        content_elem = ElementTree.SubElement(entry, 'content', {'type': content_type})
        content_elem.text = content
        
        for tag in tags:
            ElementTree.SubElement(entry, 'category', {'term': tag})
        
        app_control = ElementTree.SubElement(entry, 'app:control')
        app_draft = ElementTree.SubElement(app_control, 'app:draft')
        app_draft.text = 'yes' if draft else 'no'
        
        rough_string = ElementTree.tostring(entry, 'unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def _create_wsse_header(self) -> str:
        nonce = hashlib.sha1(str(random.random()).encode()).digest()
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        password_digest = base64.b64encode(hashlib.sha1(nonce + now.encode() + self.api_key.encode()).digest()).decode()
        return f'UsernameToken Username="{self.hatena_id}", PasswordDigest="{password_digest}", Nonce="{base64.b64encode(nonce).decode()}", Created="{now}"'
    
    def _post_to_hatena(self, xml_data: str) -> requests.Response:
        url = f"{self.base_url}/entry"
        headers = {'Content-Type': 'application/xml', 'X-WSSE': self._create_wsse_header()}
        return requests.post(url, data=xml_data.encode('utf-8'), headers=headers, timeout=30)

    def _parse_response(self, response_xml: str) -> Dict[str, str]:
        try:
            root = ElementTree.fromstring(response_xml)
            namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
            entry_id_elem = root.find('atom:id', namespaces)
            entry_id = entry_id_elem.text.split('-')[-1] if entry_id_elem is not None else ''
            url_elem = root.find('atom:link[@rel="alternate"]', namespaces)
            url = url_elem.get('href', '') if url_elem is not None else ''
            return {'entry_id': entry_id, 'url': url}
        except: return {}
