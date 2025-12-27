import logging
import os
import re
from typing import Dict, Any, List, Tuple
from PIL import Image

from src.framework.base_task import BaseTaskModule
from src.services.imgur_service import ImgurService
from src.database import db, Asset
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class PromptPreparerTask(BaseTaskModule):
    """
    Prepares inputs for an AI prompt by processing messages and uploading images.
    """

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        messages: List[Dict[str, Any]] = inputs.get("messages", [])
        assets: List[Dict[str, Any]] = inputs.get("assets", [])

        logger.info(f"[PromptPreparerTask] Messages: {len(messages)}, Assets: {len(assets)}")

        if not messages:
            return {"texts": [], "images_for_prompt": []}

        texts = [m['content'] for m in messages if m.get('message_type') == 'text' and m.get('content')]
        
        imgur_service = ImgurService()
        images_for_prompt: List[Dict[str, str]] = []
        asset_by_message_id: Dict[int, Dict[str, Any]] = {}
        assets_to_update: List[int] = []

        for asset_data in assets:
            if asset_data.get('asset_type') == 'image':
                asset_id = asset_data.get('id')
                external_url = asset_data.get('external_url')
                local_path = asset_data.get('local_path')

                if not external_url and local_path and os.path.exists(local_path):
                    try:
                        # Resize image to 320px width
                        img = Image.open(local_path)
                        w, h = img.size
                        if w > 320:
                            new_h = int(h * 320 / w)
                            img = img.resize((320, new_h))
                            img.save(local_path)
                        
                        upload_result = imgur_service.upload_image(local_path)
                        if upload_result.get('success'):
                            external_url = upload_result['link']
                            db.session.query(Asset).filter(Asset.id == asset_id).update({"external_url": external_url})
                            assets_to_update.append(asset_id)
                    except Exception as e:
                        logger.warning(f"Imgur upload failed for Asset {asset_id}: {e}")

                if asset_data.get('message_id'):
                    # Prefer external_url (public). If missing, include a file:// URL based on local_path
                    # so downstream tasks can use it in prompts and the publisher can detect and upload it.
                    if external_url:
                        public_url = external_url
                    elif local_path:
                        # Normalize to file:// scheme for consistent detection
                        normalized = local_path
                        if not normalized.startswith('file://'):
                            normalized = f"file://{normalized}"
                        public_url = normalized
                    else:
                        public_url = ''

                    asset_by_message_id[asset_data['message_id']] = {
                        "url": public_url,
                        "description": asset_data.get("description"),
                        "local_path": local_path
                    }

        if assets_to_update:
            try:
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()

        for msg in messages:
            if msg.get('message_type') == 'image' and msg.get('id') in asset_by_message_id:
                images_for_prompt.append(asset_by_message_id[msg['id']])

        youtube_links = self._extract_youtube_links(texts)
        
        url_pattern = r'(https?://[\w\-._~:/?#\[\]@!$&\'()*+,;=%]+)'
        all_urls = set()
        for text in texts:
            all_urls.update(re.findall(url_pattern, text))
        
        web_links = [url for url in all_urls if url not in youtube_links]

        return {
            "texts": texts,
            "images_for_prompt": images_for_prompt,
            "youtube_links": youtube_links,
            "web_links": web_links
        }

    def _extract_youtube_links(self, texts: List[str]) -> List[str]:
        youtube_links = []
        pattern = r'(https?://(?:www\[.)?(?:youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]{11})'
        for text in texts:
            found_links = re.findall(pattern, text)
            youtube_links.extend(found_links)
        return list(set(youtube_links))

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "PromptPreparer",
            "description": "Prepares texts and image URLs for an AI prompt."
        }