"""
サムネイル画像生成サービス。
Magic Hour APIで画像を生成し、Imgurにアップロードして、
ブログ記事用のサムネイル画像URLを提供します。
"""


import logging
import os
import time
import requests
from typing import Optional
from enum import Enum

from src.services.magichour_service import MagicHourService
from src.services.imgur_service import ImgurService
from src.services.gemini_service import GeminiService
# Use filesystem event watcher for custom API flows that download to LOCAL_THUMBNAIL_DIR
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)

class ImageAcquireMode(Enum):
    BROWSER_DOWNLOAD = "browser"
    LEGACY_BACKEND = "legacy"


class ThumbnailGeneratorService:
    """記事のサムネイル画像を生成・アップロードするサービスクラス。"""

    def __init__(
        self,
        magichour_service: Optional[MagicHourService] = None,
        imgur_service: Optional[ImgurService] = None,
    ):
        """
        コンストラクタ。
        """
        self.magichour = magichour_service or MagicHourService()
        self.imgur = imgur_service or ImgurService()
        
        # 一時画像保存用のディレクトリ
        self.temp_folder = os.path.join(os.getcwd(), 'temp_thumbnails')
        os.makedirs(self.temp_folder, exist_ok=True)
        # ローカルサムネイルの拾い上げ用ディレクトリ
        self.local_thumbnail_dir = os.getenv('LOCAL_THUMBNAIL_DIR')

    def generate_and_upload(self, prompt: str) -> Optional[str]:
        """
        プロンプトから画像を生成し、Imgurにアップロードします。
        
        Returns:
            Imgurにアップロードされた画像のURL
        """
        logger.info(f"サムネイル生成開始: プロンプト='{prompt[:50]}...'")

        # 0. Check if result is already an image URL (Scavenger support)
        if prompt.startswith("__IMAGE_URL__"):
            src_url = prompt.replace("__IMAGE_URL__", "")
            logger.info("🎨 Result already exists as image URL. Scavenging directly: %s", src_url)
            local_image_path = self._acquire_image_path(src_url)
            if local_image_path:
                return self._upload_and_cleanup(local_image_path)
            else:
                logger.warning("Failed to scavenge image from URL: %s. Falling back to new generation.", src_url)
                # Remove the __IMAGE_URL__ prefix and use the rest as a new prompt
                prompt = prompt.replace("__IMAGE_URL__", "").strip()
                if not prompt or prompt.startswith("https://"):
                    # If it's just a URL or empty, generate a generic prompt
                    prompt = "Create a manga-style thumbnail for a blog article about technology and creativity"

        # 1. Custom API Flow (Preferred if configured)
        api_url = os.getenv('CUSTOM_THUMBNAIL_API_URL')
        if api_url:
            logger.info(f"Using Custom Thumbnail API: {api_url}")
            return self._generate_via_custom_api(prompt, api_url)

        # 2. Magic Hour Flow (Default)
        return self._generate_via_magic_hour(prompt)

    def _generate_via_custom_api(self, prompt: str, api_url: str) -> str:
        """
        カスタムAPI経由でサムネイル画像を生成します。
        URLが取得できない場合は例外を発生させ、ワークフローを停止させます。
        """
        body, src_url = self._call_custom_api(prompt, api_url)
        
        if not src_url:
            logger.warning("No image URL returned from Custom API. Falling back to Magic Hour.")
            return self._generate_via_magic_hour(prompt)
            
        local_image_path = self._acquire_image_path(src_url)
        if not local_image_path:
            logger.warning(f"Could not acquire image from {src_url}. Falling back to Magic Hour.")
            return self._generate_via_magic_hour(prompt)
            
        imgur_url = self._upload_and_cleanup(local_image_path)
        if not imgur_url:
            raise RuntimeError("Thumbnail upload failed: Could not upload to Imgur.")
            
        return imgur_url

    def _generate_via_magic_hour(self, prompt: str) -> str:
        """
        Magic Hour APIを使用して画像を生成します。
        """
        logger.info("Falling back to Magic Hour for image generation.")
        response = self.magichour.generate_image(prompt)
        if not response or 'images' not in response or not response['images']:
            raise RuntimeError("Magic Hour generation failed: Empty response.")
        
        image_url = response['images'][0]['url']
        logger.info(f"Magic Hourで画像生成成功: {image_url}")
        
        # 画像をローカルに一時保存
        local_image_path = None
        if image_url.startswith('file://'):
            local_image_path = image_url.replace('file://', '')
        else:
            logger.info(f"画像をダウンロード中: {image_url}")
            image_response = requests.get(image_url, timeout=30)
            if image_response.status_code != 200:
                raise RuntimeError(f"Failed to download image from Magic Hour: HTTP {image_response.status_code}")
            
            timestamp = int(time.time() * 1000)
            local_image_path = os.path.join(self.temp_folder, f"thumb_{timestamp}.png")
            with open(local_image_path, 'wb') as f:
                f.write(image_response.content)

        return self._upload_and_cleanup(local_image_path)

    def _call_custom_api(self, prompt: str, api_url: str):
        """
        API呼び出し＋レスポンス解釈。src_urlを返す。
        """
        logger.info("ステップ1: カスタムAPI画像生成開始: %s", api_url)
        headers = {"Content-Type": "application/json"}
        bearer = os.getenv('CUSTOM_THUMBNAIL_API_BEARER')
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        
        # Ensure mode is Thinking
        GeminiService().set_wrapper_mode('Thinking')

        api_retries = int(os.getenv('CUSTOM_THUMBNAIL_API_RETRIES', 3))
        
        for attempt in range(1, api_retries + 1):
            if attempt == 1:
                image_prompt = f"Create a high-quality image based on this prompt. You MUST trigger the image generation tool.\n\nPrompt: {prompt}"
            else:
                image_prompt = f"ERROR: You provided text previously, but NO IMAGE was generated. Use the image generation tool NOW to create this image: {prompt}"
            
            # CRITICAL: payload must NOT contain 'mode' or 'new_chat' to avoid 400 Bad Request
            # FIX: Escape newlines to prevent early submission in browser automation
            payload = {"prompt": image_prompt.replace('\n', '\\n')}

            try:
                resp = requests.post(
                    api_url,
                    json=payload,
                    timeout=300,
                    headers=headers,
                )
                if resp.status_code == 200:
                    body = resp.json()
                    answer = body.get('answer', {})
                    
                    # Ensure answer is treated correctly if it is a list
                    if isinstance(answer, list):
                        if len(answer) > 0:
                            # Use the first item if available
                            answer = answer[0]
                        else:
                            answer = {}

                    if isinstance(answer, str):
                        logger.warning("attempt %d: answer is string, expected object.", attempt)
                        src_url = None
                    else:
                        images = answer.get('images', [])
                        src_url = None
                        if images:
                            image_info = images[0]
                            src_url = image_info.get('src') or image_info.get('download_url')
                        if not src_url:
                            src_url = answer.get('download_url') or body.get('download_url')
                    
                    if src_url:
                        logger.info("画像URL取得成功: %s", src_url)
                        return body, src_url
                    else:
                        logger.warning("attempt %d: 画像URLが空です（リトライ待機中）", attempt)
                else:
                    logger.warning("attempt %d: status=%d", attempt, resp.status_code)
            except Exception as e:
                logger.warning("attempt %d: 例外発生: %s", attempt, e)
            
            if attempt < api_retries:
                wait_time = 10 * attempt
                logger.info(f"{wait_time}秒待機後に画像生成を再試行します...")
                time.sleep(wait_time)

        return None, None

    def _acquire_image_path(self, src_url: str) -> Optional[str]:
        """ブラウザのダウンロード完了を待機し、最新ファイルを拾う。失敗時はURLから直接ダウンロードを試みる。"""
        logger.info("ブラウザのダウンロード完了を待機中...")
        time.sleep(3)
        
        # 1. Try to pick up from local directory (Scavenger Protocol)
        latest_local = self._pick_latest_local_image()
        if latest_local:
            logger.info(f"Local image found: {latest_local}")
            return latest_local
            
        # 2. Wait for browser download
        downloaded = self._wait_browser_download()
        if downloaded:
            logger.info(f"Browser download detected: {downloaded}")
            return downloaded

        # 3. Fallback: Direct Download from URL
        logger.warning("Local image not found. Attempting direct download from URL.")
        return self._download_from_url(src_url)

    def _download_from_url(self, url: str) -> Optional[str]:
        """URLから画像を直接ダウンロードして一時保存する。

        Implements multiple attempts with browser-like headers and simple
        Googleusercontent URL normalization to reduce HTTP 403 occurrences.
        """
        def _try_get(u: str, headers: dict) -> Optional[requests.Response]:
            try:
                resp = requests.get(u, headers=headers, timeout=30)
                return resp
            except Exception as e:
                logger.warning(f"Direct download attempt exception for {u}: {e}")
                return None

        attempts = []

        # 1) Raw request (existing behavior)
        attempts.append({'url': url, 'headers': {}})

        # 2) Browser-like User-Agent
        ua_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        }
        attempts.append({'url': url, 'headers': ua_headers})

        # 3) Add Referer (some Google-hosted urls require a referer)
        ref_headers = ua_headers.copy()
        ref_headers['Referer'] = 'https://lh3.googleusercontent.com/'
        attempts.append({'url': url, 'headers': ref_headers})

        # 4) Try normalized Googleusercontent URL variants (strip size suffix or set s0)
        if '=s' in url:
            base = url.split('=s')[0]
            attempts.append({'url': base + '=s0', 'headers': ua_headers})
            attempts.append({'url': base, 'headers': ua_headers})

        # 5) Final attempt with lowered headers
        attempts.append({'url': url, 'headers': {'User-Agent': ua_headers['User-Agent']}})

        for idx, a in enumerate(attempts, start=1):
            resp = _try_get(a['url'], a['headers'])
            if resp is None:
                continue
            if resp.status_code == 200:
                try:
                    timestamp = int(time.time() * 1000)
                    local_ext = 'jpg' if 'jpeg' in resp.headers.get('Content-Type', '') or 'image' in resp.headers.get('Content-Type', '') else 'bin'
                    local_path = os.path.join(self.temp_folder, f"download_{timestamp}.{local_ext}")
                    with open(local_path, 'wb') as f:
                        f.write(resp.content)
                    logger.info(f"Direct download successful (attempt {idx}): {a['url']} -> {local_path}")
                    return local_path
                except Exception as e:
                    logger.warning(f"Failed to write downloaded content to file: {e}")
                    return None
            else:
                logger.warning(f"Direct download attempt {idx} returned HTTP {resp.status_code} for URL: {a['url']}")
                # small backoff between attempts
                time.sleep(1)

        logger.error("Direct download failed after all attempts: HTTP 403 or other errors")
        return None

    def _wait_browser_download(self) -> Optional[str]:
        if not self.local_thumbnail_dir:
            return None
        folder = os.path.abspath(self.local_thumbnail_dir)
        if not os.path.isdir(folder):
            return None
            
        event_handler = ImageFileHandler()
        observer = Observer()
        observer.schedule(event_handler, folder, recursive=False)
        observer.start()
        try:
            wait_seconds = int(os.getenv('CUSTOM_THUMBNAIL_WAIT_SECONDS', 60))
            start_time = time.time()
            while time.time() - start_time < wait_seconds:
                if event_handler.new_image_path:
                    return event_handler.new_image_path
                time.sleep(1)
            return None
        finally:
            observer.stop()
            observer.join()

    def _upload_and_cleanup(self, local_image_path: str) -> Optional[str]:
        logger.info("ステップ3: Imgurアップロード開始")
        imgur_result = self.imgur.upload_image(local_image_path)
        if imgur_result and imgur_result.get('success') and imgur_result.get('link'):
            imgur_url = imgur_result['link']
            if local_image_path.startswith(self.temp_folder):
                try: os.remove(local_image_path)
                except: pass
            return imgur_url
        return None

    def _pick_latest_local_image(self) -> Optional[str]:
        if not self.local_thumbnail_dir: return None
        folder = os.path.abspath(self.local_thumbnail_dir)
        if not os.path.isdir(folder): return None
        candidates = []
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if os.path.isfile(path) and os.path.splitext(name)[1].lower() in {'.png', '.jpg', '.jpeg', '.webp'}:
                candidates.append((path, os.path.getmtime(path)))
        if not candidates: return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

class ImageFileHandler(FileSystemEventHandler):
    def __init__(self):
        self.new_image_path = None
    def on_created(self, event):
        if not event.is_directory and os.path.splitext(event.src_path)[1].lower() in ['.png', '.jpg', '.jpeg', '.webp']:
            self.new_image_path = event.src_path