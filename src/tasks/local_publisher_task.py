import os
import json
import time
from typing import Dict, Any
from src.framework.base_task import BaseTaskModule

class LocalPublisherTask(BaseTaskModule):
    """
    Publishes content locally for testing.
    """
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        title = inputs.get('title')
        content = inputs.get('content')
        if not title or not content:
            raise ValueError('Title and content are required.')

        ts = int(time.time())
        out_dir = 'data'
        os.makedirs(out_dir, exist_ok=True)
        filename = f'published_{ts}.html'
        filepath = os.path.join(out_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"<html><head><meta charset=\"utf-8\"><title>{title}</title></head><body>{content}</body></html>")

        entry = {
            'url': f'file://{os.path.abspath(filepath)}',
            'title': title,
            'published': ts
        }

        idxpath = os.path.join(out_dir, 'last_published.json')
        try:
            with open(idxpath, 'w', encoding='utf-8') as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        return {'hatena_entry': entry}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            'name': 'LocalPublisher',
            'description': 'Publishes content locally for testing.'
        }