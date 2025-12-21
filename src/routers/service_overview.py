from fastapi import APIRouter, Query, HTTPException
from typing import Any
from pydantic import BaseModel
from typing import Optional
import os
from src.services.chrome_api import call_gemini_api_via_chrome

router = APIRouter(prefix="/api/v1")


@router.post("/articles/batch/process")
def articles_batch_process(message: dict) -> Any:
    # Stub: start a background task to generate articles from a message
    return {"task_id": "task_123", "status": "started"}


@router.get("/tasks/{task_id}/status")
def task_status(task_id: str) -> Any:
    # Stub: return a fake task status
    return {"task_id": task_id, "status": "running"}


@router.post("/tasks/{task_id}/cancel")
def task_cancel(task_id: str) -> Any:
    # Stub: cancel the given task
    return {"task_id": task_id, "status": "cancelling"}


# Article content generation
@router.post("/articles/generate/concept")
def generate_concept(payload: dict) -> Any:
    return {"concept": "簡単レシピで時短調理", "input": payload}


@router.post("/articles/generate/content")
def generate_content(payload: dict) -> Any:
    return {"article_id": 1, "content": "生成された記事本文...", "input": payload}


@router.post("/articles/enhance")
def enhance_article(payload: dict) -> Any:
    return {"enhanced": True, "input": payload}


# Article management
@router.get("/articles")
def list_articles(limit: int = 20, offset: int = 0) -> Any:
    return {"articles": [], "limit": limit, "offset": offset}


@router.post("/articles/drafts")
def save_draft(draft: dict) -> Any:
    return {"draft_id": 1, "saved": True, "draft": draft}


@router.put("/articles/drafts/{id}")
def update_draft(id: int, draft: dict) -> Any:
    return {"draft_id": id, "updated": True, "draft": draft}


@router.delete("/articles/drafts/{id}")
def delete_draft(id: int) -> Any:
    return {"draft_id": id, "deleted": True}


@router.post("/articles/{id}/publish")
def publish_article(id: int) -> Any:
    return {"article_id": id, "published": True}


# Thumbnails
@router.post("/thumbnails/generate")
def generate_thumbnail(payload: dict) -> Any:
    return {"thumbnail_url": "https://example.com/thumb.jpg", "request": payload}


@router.get("/thumbnails/templates")
def list_thumbnail_templates() -> Any:
    return {"templates": ["warm", "minimal", "bold"]}


@router.post("/thumbnails/batch-generate")
def batch_generate_thumbnails(payload: dict) -> Any:
    return {"results": [], "request": payload}


# Assets
@router.post("/assets/upload")
def upload_asset() -> Any:
    return {"asset_id": "asset_1", "uploaded": True}


@router.get("/assets/{id}")
def get_asset(id: str) -> Any:
    return {"asset_id": id, "url": f"/uploads/{id}"}


@router.post("/assets/{id}/imgur-upload")
def imgur_upload(id: str) -> Any:
    return {"asset_id": id, "imgur_url": f"https://i.imgur.com/{id}.jpg"}


@router.delete("/assets/{id}")
def delete_asset(id: str) -> Any:
    return {"asset_id": id, "deleted": True}


# Affiliate (Rakuten)
@router.get("/affiliate/rakuten/search")
def rakuten_search(keyword: str = Query(...), category: str | None = None) -> Any:
    return {"products": [], "keyword": keyword, "category": category}


@router.post("/affiliate/rakuten/generate-links")
def rakuten_generate_links(payload: dict) -> Any:
    return {"links": [], "request": payload}


@router.get("/affiliate/rakuten/categories")
def rakuten_categories() -> Any:
    return {"categories": ["本", "家電", "食品"]}


@router.post("/affiliate/auto-insert")
def affiliate_auto_insert(payload: dict) -> Any:
    return {"inserted": 0, "request": payload}


@router.get("/affiliate/performance")
def affiliate_performance() -> Any:
    return {"performance": {}}


@router.post("/affiliate/optimize")
def affiliate_optimize(payload: dict) -> Any:
    return {"suggestions": [], "request": payload}


# Search
@router.get("/search/duckduckgo")
def ddg_search(q: str = Query(...), limit: int = 10) -> Any:
    return {"results": [], "query": q, "limit": limit}


@router.post("/search/batch-search")
def batch_search(payload: dict) -> Any:
    return {"results": [], "request": payload}


@router.get("/search/trending")
def trending_search() -> Any:
    return {"trending": []}


# Links
@router.post("/links/validate")
def validate_links(payload: dict) -> Any:
    return {"checked": [], "request": payload}


@router.post("/links/replace-broken")
def replace_broken_links(payload: dict) -> Any:
    return {"replaced": [], "request": payload}


@router.get("/links/suggestions")
def link_suggestions(topic: str | None = None) -> Any:
    return {"suggestions": [], "topic": topic}


@router.post("/links/real-urls")
def links_real_urls(payload: dict) -> Any:
    return {"updated_content": payload.get("content", ""), "request": payload}


# Corpus / RAG / Knowledge
@router.post("/corpus/build")
def corpus_build(payload: dict) -> Any:
    return {"status": "building", "request": payload}


@router.get("/corpus/stats")
def corpus_stats() -> Any:
    return {"docs": 0}


@router.post("/corpus/update")
def corpus_update(payload: dict) -> Any:
    return {"updated": True, "request": payload}


@router.post("/rag/search")
def rag_search(payload: dict) -> Any:
    return {"results": [], "request": payload}


@router.post("/rag/summarize")
def rag_summarize(payload: dict) -> Any:
    return {"summary": "", "request": payload}


@router.get("/rag/related-articles")
def rag_related_articles(query: str | None = None) -> Any:
    return {"results": [], "query": query}


@router.post("/knowledge/extract")
def knowledge_extract(payload: dict) -> Any:
    return {"extracted": [], "request": payload}


@router.get("/knowledge/graph")
def knowledge_graph() -> Any:
    return {"nodes": [], "edges": []}


@router.post("/knowledge/recommend")
def knowledge_recommend(payload: dict) -> Any:
    return {"recommendations": [], "request": payload}


# Integrations: LINE
@router.post("/integrations/line/send-message")
def line_send_message(payload: dict) -> Any:
    return {"sent": True, "request": payload}


@router.get("/integrations/line/user-profile")
def line_user_profile(user_id: str | None = None) -> Any:
    return {"user_id": user_id, "profile": {}}


@router.post("/integrations/line/notify")
def line_notify(payload: dict) -> Any:
    return {"notified": True, "request": payload}


# Integrations: Hatena
@router.get("/integrations/hatena/blogs")
def hatena_blogs() -> Any:
    return {"blogs": []}


@router.post("/integrations/hatena/entries")
def hatena_create_entry(payload: dict) -> Any:
    return {"entry_id": 1, "posted": True, "request": payload}


@router.get("/integrations/hatena/stats")
def hatena_stats() -> Any:
    return {"stats": {}}


# v1 health check
@router.get("/health")
def v1_health() -> Any:
    return {"status": "ok", "version": "v1"}


# Chrome API integration
class ImageRequest(BaseModel):
    prompt: str
    bearer: Optional[str] = None

@router.post("/chrome/gemini-image")
async def generate_image_via_chrome(request: ImageRequest):
    """
    Chromeブラウザ経由でGemini APIに画像生成リクエストを送る。
    ブラウザのセッションとクッキーを使って認証を行う。
    """
    try:
        api_url = os.getenv('CUSTOM_THUMBNAIL_API_URL')
        if not api_url:
            raise HTTPException(status_code=500, detail="CUSTOM_THUMBNAIL_API_URL not configured")
        
        bearer = request.bearer or os.getenv('CUSTOM_THUMBNAIL_API_BEARER')
        
        result = call_gemini_api_via_chrome(request.prompt, api_url, bearer)
        
        if result:
            return {"success": True, "image_url": result}
        else:
            raise HTTPException(status_code=500, detail="Failed to generate image")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Health checks
@router.get("/ping")
def ping():
    return "pong"
