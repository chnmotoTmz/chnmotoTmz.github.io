"""
Local LLM Service

LLM API Server (FastAPI) と連携し、ローカル（またはプライベートなバックエンド）での
テキスト生成および画像解析を提供します。
非同期ジョブ形式のため、結果の取得にはポーリングを行います。
"""

import logging
import requests
import time
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class LocalLLMService:
    """
    LLM API Server クライアント。
    ポート 8001 で動作するバックエンドサーバーと通信します。
    """

    def __init__(self, blog_config: Optional[Dict[str, Any]] = None):
        # サーバーURLは環境変数またはデフォルト（USAGE.mdに準拠）
        self.base_url = os.getenv("LOCAL_LLM_SERVER_URL", "http://localhost:8001")
        self.timeout = 600  # Thinkingモード等を考慮し長めに設定
        self.polling_interval = 2

    def generate_text(
        self, 
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        テキストを生成します（ジョブ投入後、結果をポーリング取得）。
        """
        url = f"{self.base_url}/generate_text"
        
        # システムプロンプトがあれば結合（サーバー側の TextRequest 形式に合わせる）
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        payload = {
            "prompt": full_prompt,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            logger.info(f"[LocalLLM] Job submitting to {url}")
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            job_id = resp.json().get("text")
            
            if not job_id:
                raise RuntimeError("Failed to get Job ID from LLM API Server")
                
            return self._poll_result(job_id)
            
        except Exception as e:
            logger.error(f"[LocalLLM] Text generation failed: {e}")
            raise

    def analyze_image_from_path(
        self,
        image_path: str,
        prompt: str = "この画像の内容をブログ記事で使えるように、簡潔かつ魅力的に説明してください。",
        **kwargs
    ) -> str:
        """
        画像を解析します（絶対パスで指定）。
        """
        url = f"{self.base_url}/analyze_image"
        
        payload = {
            "image_path": os.path.abspath(image_path),
            "prompt": prompt
        }

        try:
            logger.info(f"[LocalLLM] Image analysis job submitting to {url}")
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            job_id = resp.json().get("text")
            
            if not job_id:
                raise RuntimeError("Failed to get Job ID from LLM API Server")
                
            return self._poll_result(job_id)
            
        except Exception as e:
            logger.error(f"[LocalLLM] Image analysis failed: {e}")
            raise

    def _poll_result(self, job_id: str) -> str:
        """
        結果が PENDING でなくなるまでポーリングします。
        """
        url = f"{self.base_url}/result/{job_id}"
        start_time = time.time()
        
        logger.info(f"[LocalLLM] Polling for Job {job_id}...")
        
        while time.time() - start_time < self.timeout:
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                result = resp.json().get("text")
                
                if result != "PENDING":
                    if result.startswith("[LLM_ERROR]"):
                        raise RuntimeError(f"LLM API Server returned error: {result}")
                    
                    logger.info(f"[LocalLLM] Job {job_id} completed.")
                    return result
                
            except requests.RequestException as e:
                logger.warning(f"[LocalLLM] Polling request failed (retrying): {e}")
            
            time.sleep(self.polling_interval)
            
        raise TimeoutError(f"Job {job_id} timed out after {self.timeout} seconds")
