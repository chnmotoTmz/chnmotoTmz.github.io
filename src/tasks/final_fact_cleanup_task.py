import re
import requests
from typing import Dict, Any, List
from src.framework.base_task import BaseTaskModule

class FinalFactCleanupTask(BaseTaskModule):
    """
    Cleans up the reference/fact-check section of the article.
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        title = inputs.get("title", "")
        content = inputs.get("content", "")
        web_summaries = inputs.get("web_summaries", [])
        similar_articles = inputs.get("similar_articles", [])

        title2url = {}
        for ws in web_summaries:
            t, u = ws.get("title"), ws.get("url")
            if t and u: title2url[t.strip()] = u
        for sa in similar_articles:
            t, u = sa.get("title"), sa.get("url")
            if t and u: title2url[t.strip()] = u

        def search_duckduckgo(query):
            try:
                resp = requests.get("https://duckduckgo.com/html/", params={"q": query}, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                if resp.status_code == 200:
                    m = re.search(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', resp.text)
                    if m: return m.group(1)
            except: pass
            return None

        # Pattern for reference section
        pattern = r'(📚[\s]*Reference[\s\S]*?)(\n{2,}|$)'
        match = re.search(pattern, content)
        if match:
            section = match.group(1)
            lines = []
            for line in section.splitlines():
                if re.search(r'example\.com|TempURL', line): continue
                m = re.match(r'Ref[:]\s*(.+)', line)
                if m:
                    ref_title = m.group(1).strip()
                    url = title2url.get(ref_title) or search_duckduckgo(ref_title)
                    if url: lines.append(f"- [{ref_title}]({url})")
                    continue
                if line.strip() and not line.strip().startswith('📚'):
                    lines.append(line)
            
            new_section = '📚 Reference\n' + '\n'.join(lines) + '\n' if lines else ''
            content = content.replace(section, new_section)
        
        return {"title": title, "content": content}

    @classmethod
    def get_module_info(cls) -> Dict[str, Any]:
        return {
            "name": "FinalFactCleanupTask",
            "description": "Cleans up reference section."
        }
