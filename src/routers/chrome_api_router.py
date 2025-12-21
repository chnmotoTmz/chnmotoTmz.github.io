from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
from src.services.chrome_api import call_gemini_api_via_chrome

router = APIRouter()

class ImageRequest(BaseModel):
    prompt: str
    bearer: Optional[str] = None

@router.post("/api/chrome/gemini-image")
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