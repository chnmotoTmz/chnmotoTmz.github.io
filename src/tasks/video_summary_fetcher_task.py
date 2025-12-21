import requests
import os
import logging
import re
from typing import List, Dict, Any, Optional
from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class VideoSummaryFetcher(BaseTaskModule):
    """
    Fetches YouTube video title, description, and thumbnail.
    """
    YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("YOUTUBE_API_KEY", "")
        self.llm_service = GeminiService()

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        youtube_links = inputs.get("youtube_links", [])
        if not youtube_links:
            return {"video_summaries": []}
        summaries = self.fetch(youtube_links)
        return {"video_summaries": summaries}

    def fetch(self, youtube_links: List[str]) -> List[Dict]:
        summaries = []
        for url in youtube_links:
            video_id = self.extract_video_id(url)
            if not video_id: continue
            info = self.get_video_info(video_id)
            if info: summaries.append(info)
        return summaries

    def extract_video_id(self, url: str) -> Optional[str]:
        match = re.search(r"(?:v=|youtu.be/)([\w-]{11})", url)
        return match.group(1) if match else None

    def get_video_info(self, video_id: str) -> Optional[Dict]:
        params = {"id": video_id, "key": self.api_key, "part": "snippet"}
        try:
            resp = requests.get(self.YOUTUBE_API_URL, params=params, timeout=5)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items: return None
            
            snippet = items[0]["snippet"]
            title = snippet.get("title", "")
            description = snippet.get("description", "")
            summary = self._generate_summary(title, description)
            
            return {
                "video_id": video_id,
                "title": title,
                "description": description[:500],
                "summary": summary,
                "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
                "url": f"https://www.youtube.com/watch?v={video_id}"
            }
        except Exception:
            return None

    def _generate_summary(self, title: str, description: str) -> str:
        if not description or len(description) < 30:
            return f"「{title}」に関するYouTube動画"
        
        try:
            prompt = f"以下のYouTube動画を100字以内で要約してください。\n\n【タイトル】{title}\n\n【説明文】\n{description[:1500]}"
            summary = self.llm_service.generate_text(prompt, max_tokens=200)
            return summary.strip()[:200] if summary else description[:100] + "..."
        except Exception:
            return description[:100] + "..."

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {"name": "VideoSummaryFetcher", "description": "Fetches YouTube video summaries."}