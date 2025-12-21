from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncio
import uuid
import os
import logging
import time
import google.generativeai as genai
from anthropic import Anthropic, APIError
from PIL import Image

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env.production at the project root
from llm_api_server.env_loader import load_env_for_llm_api_server
load_env_for_llm_api_server()

app = FastAPI()

# Simple in-memory job buffer
job_queue = asyncio.Queue()
results = {}

# Rate limiting: 30 RPM = 2 seconds between requests
RATE_LIMIT_RPM = 30
RATE_LIMIT_DELAY = 60.0 / RATE_LIMIT_RPM  # 2.0 seconds
last_request_time = 0.0

# Gemini model fallback chain (from environment variables)
def get_gemini_model_chain():
    """Get Gemini model fallback chain from environment variables."""
    primary_model = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
    # Additional fallback models
    fallback_models = os.getenv('GEMINI_FALLBACK_MODELS', 'gemini-1.5-pro,gemini-pro').split(',')
    return [primary_model] + [m.strip() for m in fallback_models if m.strip()]

def get_available_gemini_models():
    """Get list of available Gemini models from API."""
    try:
        models = genai.list_models()
        # Filter models that support generateContent
        available = []
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                # Extract model name (e.g., 'models/gemini-1.5-flash' -> 'gemini-1.5-flash')
                model_name = model.name.replace('models/', '')
                available.append(model_name)
        logger.info(f"Available Gemini models from API: {available}")
        return available
    except Exception as e:
        logger.error(f"Failed to fetch available models from API: {e}")
        # Fallback to environment-based models
        return get_gemini_model_chain()

# Claude model configuration
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20240620')

# --- Pydantic Models ---
class TextRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    max_tokens: Optional[int] = 3000
    temperature: Optional[float] = 0.5

class ImageRequest(BaseModel):
    image_path: str
    prompt: Optional[str] = "この画像の内容をブログ記事で使えるように、簡潔かつ魅力的に説明してください。"

class VideoRequest(BaseModel):
    video_path: str
    prompt: Optional[str] = "動画の内容を要約してください"

class JobResponse(BaseModel):
    text: str

# --- Background Worker ---
async def llm_worker():
    """
    A background worker that processes LLM jobs from a queue.
    Initializes API clients and handles job dispatching.
    Rate limited to 30 RPM (2 seconds between requests).
    """
    global last_request_time
    
    # Configure Gemini
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if gemini_api_key:
        genai.configure(api_key=gemini_api_key)
    
    # Configure Claude
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    claude_client = None
    if claude_api_key:
        claude_client = Anthropic(api_key=claude_api_key)
    
    # Get available models from API
    gemini_models = get_available_gemini_models() if gemini_api_key else []
    
    logger.info(f"LLM Worker Initialized. Gemini Ready: {bool(gemini_api_key)}, Claude Ready: {bool(claude_client)}")
    logger.info(f"Gemini models available: {gemini_models}" if gemini_models else "Gemini models: None")
    logger.info(f"Claude model: {CLAUDE_MODEL}" if claude_client else "Claude: Not configured")
    logger.info(f"Rate limit: {RATE_LIMIT_RPM} RPM ({RATE_LIMIT_DELAY} seconds between requests)")

    while True:
        job_id, req, job_type = await job_queue.get()
        
        # Apply rate limiting
        current_time = time.time()
        time_since_last = current_time - last_request_time
        if time_since_last < RATE_LIMIT_DELAY:
            wait_time = RATE_LIMIT_DELAY - time_since_last
            logger.info(f"Rate limit: waiting {wait_time:.2f}s before processing job {job_id}")
            await asyncio.sleep(wait_time)
        
        last_request_time = time.time()
        
        try:
            if job_type == "text":
                text_result = None
                # 1. Try Gemini with available models from API
                if gemini_api_key:
                    # Use models discovered from API
                    models_to_try = gemini_models.copy()
                    
                    # If specific model requested and not in list, try it first
                    if req.model and req.model not in models_to_try:
                        models_to_try.insert(0, req.model)
                    
                    for model_name in models_to_try:
                        try:
                            logger.info(f"Processing text job {job_id} with Gemini model: {model_name}")
                            gemini_model = genai.GenerativeModel(model_name)
                            response = gemini_model.generate_content(req.prompt)
                            if response.text and response.text.strip():
                                text_result = response.text.strip()
                                logger.info(f"Success with model: {model_name}")
                                break
                            else:
                                logger.warning(f"Gemini model {model_name} returned empty response for job {job_id}")
                        except Exception as e:
                            error_str = str(e).lower()
                            if '429' in error_str or 'quota' in error_str or 'resource exhausted' in error_str:
                                logger.warning(f"Gemini model {model_name} hit quota/rate limit for job {job_id}: {e}")
                                continue  # Try next model
                            elif '404' in error_str or 'not found' in error_str:
                                logger.warning(f"Gemini model {model_name} not found for job {job_id}: {e}")
                                continue  # Try next model
                            else:
                                logger.error(f"Gemini model {model_name} failed for job {job_id}: {e}")
                                continue  # Try next model anyway

                # 2. Fallback to Claude if Gemini failed and Claude is available
                if text_result is None and claude_client:
                    try:
                        logger.info(f"Falling back to Claude for job {job_id}")
                        message = claude_client.messages.create(
                            model=CLAUDE_MODEL,
                            max_tokens=req.max_tokens,
                            temperature=req.temperature,
                            messages=[{"role": "user", "content": req.prompt}]
                        )
                        if message.content:
                            text_blocks = [block.text for block in message.content if hasattr(block, 'text')]
                            text_result = "".join(text_blocks).strip()
                        else:
                            logger.warning(f"Claude returned an empty response for job {job_id}.")
                    except APIError as e:
                        logger.error(f"Claude API error for job {job_id}: {e.status_code} - {e.message}")
                    except Exception as e:
                        logger.error(f"An unexpected error occurred with Claude for job {job_id}: {e}")
                
                results[job_id] = text_result or "[LLM_ERROR] Both Gemini and Claude failed to generate a response."

            elif job_type == "image":
                if not gemini_api_key:
                    results[job_id] = "[LLM_ERROR] Gemini API key not configured for image analysis."
                else:
                    try:
                        logger.info(f"Processing image job {job_id} with Gemini Vision.")
                        if not os.path.exists(req.image_path):
                            raise FileNotFoundError(f"Image file not found: {req.image_path}")
                        
                        img = Image.open(req.image_path)
                        # Use first available model from API (they all support vision)
                        vision_model_name = gemini_models[0] if gemini_models else 'gemini-1.5-flash'
                        logger.info(f"Using Gemini Vision model: {vision_model_name}")
                        vision_model = genai.GenerativeModel(vision_model_name)
                        response = vision_model.generate_content([req.prompt, img])
                        results[job_id] = response.text.strip() if response.text else "[LLM_ERROR] Gemini Vision returned an empty response."
                    except Exception as e:
                        logger.error(f"Image analysis failed for job {job_id}: {e}")
                        results[job_id] = f"[LLM_ERROR] {e}"

            elif job_type == "video":
                results[job_id] = "[LLM_INFO] Video analysis is not implemented."
                
        except Exception as e:
            logger.error(f"A critical error occurred in the LLM worker for job {job_id}: {e}", exc_info=True)
            results[job_id] = f"[LLM_CRITICAL_ERROR] {e}"
        finally:
            job_queue.task_done()

@app.on_event("startup")
async def startup_event():
    """On startup, create the background worker task."""
    asyncio.create_task(llm_worker())

# --- API Endpoints ---
@app.post("/generate_text", response_model=JobResponse)
async def generate_text_endpoint(req: TextRequest):
    job_id = str(uuid.uuid4())
    await job_queue.put((job_id, req, "text"))
    return {"text": job_id}

@app.post("/analyze_image", response_model=JobResponse)
async def analyze_image_endpoint(req: ImageRequest):
    job_id = str(uuid.uuid4())
    await job_queue.put((job_id, req, "image"))
    return {"text": job_id}

@app.post("/analyze_video", response_model=JobResponse)
async def analyze_video_endpoint(req: VideoRequest):
    job_id = str(uuid.uuid4())
    await job_queue.put((job_id, req, "video"))
    return {"text": job_id}

@app.get("/result/{job_id}", response_model=JobResponse)
async def get_result_endpoint(job_id: str):
    text = results.get(job_id)
    if text is None:
        return {"text": "PENDING"}
    return {"text": text}