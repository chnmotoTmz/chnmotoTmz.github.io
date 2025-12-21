import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any

from src.framework.base_task import BaseTaskModule
from src.services.gemini_service import GeminiService

class WebSummaryFetcher(BaseTaskModule):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.timeout = config.get("timeout", 10)
        self.llm_service = GeminiService()
        self.logger = logging.getLogger('src.services.tasks.web_summary_fetcher_task')

    def fetch_and_summarize(self, urls: List[str]) -> List[Dict[str, str]]:
        summaries = []
        for url in urls:
            try:
                resp = requests.get(url, timeout=self.timeout, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else url
                
                main = soup.find('main')
                if main:
                    text = main.get_text(separator='\n', strip=True)
                else:
                    article = soup.find('article')
                    if article:
                        text = article.get_text(separator='\n', strip=True)
                    else:
                        ps = soup.find_all('p')
                        text = '\n'.join(p.get_text(strip=True) for p in ps)
                
                raw_text = text[:2000]
                llm_summary = self._generate_summary(title, raw_text)
                summaries.append({
                    'url': url,
                    'title': title,
                    'summary': llm_summary,
                    'raw_text': text[:500]
                })
            except Exception as e:
                self.logger.error(f"[WebSummaryFetcher] Extraction failed for {url}: {e}")
                summaries.append({
                    'url': url,
                    'title': url,
                    'summary': f'取得失敗: {e}'
                })
        return summaries

    def _generate_summary(self, title: str, content: str) -> str:
        if not content or len(content) < 50:
            return f"「{title}」に関するWebページ"
        
        prompt = f"以下のWebページを100字以内で要約してください。要点のみ簡潔に。\n\n【タイトル】{title}\n\n【本文】\n{content[:1500]}\n\n要約:"
        summary = self.llm_service.generate_text(prompt, max_tokens=200)
        return summary.strip()[:200] if summary else "要約失敗"

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        web_links = inputs.get("web_links", []) or []
        if not web_links:
            return {"web_summaries": []}
        summaries = self.fetch_and_summarize(web_links)
        return {"web_summaries": summaries}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "WebSummaryFetcher",
            "description": "Fetches and summarizes web page content.",
            "inputs": {
                "web_links": "List[str]"
            },
            "outputs": {
                "web_summaries": "List[Dict]"
            }
        }