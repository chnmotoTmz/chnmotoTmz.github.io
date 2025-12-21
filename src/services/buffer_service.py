import json
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class BufferService:
    """
    Manages simple user buffers stored in a JSON file.
    """

    def __init__(self, data_path: str = "data/v2_user_buffers.json"):
        self.data_path = data_path
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        if not os.path.exists(self.data_path):
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump({}, f)

    def save_to_buffer(self, user_id: str, slot: int, content: str):
        data = self._load_data()
        if user_id not in data:
            data[user_id] = {}
        data[user_id][str(slot)] = content
        self._save_data(data)
        logger.info(f"Saved content to buffer for user {user_id}, slot {slot}")

    def get_from_buffer(self, user_id: str, slot: int) -> Optional[str]:
        data = self._load_data()
        return data.get(user_id, {}).get(str(slot))

    def _load_data(self) -> Dict:
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load buffer data: {e}")
            return {}

    def _save_data(self, data: Dict):
        try:
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save buffer data: {e}")
