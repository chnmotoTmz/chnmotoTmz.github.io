import os
import time
import base64
import logging
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

class GeminiImageRetriever:
    """Retrieve images from a custom Gemini API endpoint.

    The retriever sends a prompt to the configured API and waits for
    a JSON response containing `answer.images`, each with a `src`.
    Supported `src` formats:
      - data:image/png;base64,...  -> decoded and saved locally
      - http(s)://...              -> downloaded via HTTP GET

    The saved file path is returned on success, otherwise None.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        bearer_token: Optional[str] = None,
        local_thumbnail_dir: Optional[str] = None,
        timeout: int = 180,
    ):
        self.api_url = api_url or os.getenv("CUSTOM_THUMBNAIL_API_URL")
        self.bearer_token = bearer_token or os.getenv("CUSTOM_THUMBNAIL_API_BEARER")
        self.local_thumbnail_dir = local_thumbnail_dir or os.getenv("LOCAL_THUMBNAIL_DIR")
        self.timeout = timeout

        if self.local_thumbnail_dir:
            Path(self.local_thumbnail_dir).mkdir(parents=True, exist_ok=True)

    def retrieve_image(self, prompt: str) -> Optional[str]:
        if not self.api_url:
            logger.warning("CUSTOM_THUMBNAIL_API_URL is not configured; cannot retrieve image")
            return None

        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"

        try:
            resp = requests.post(
                self.api_url,
                json={"prompt": prompt.replace('\n', '\\n')},
                timeout=self.timeout,
                headers=headers,
            )
            if resp.status_code != 200:
                logger.warning("Thumbnail custom API returned non-200: %s", resp.status_code)
                return None

            body = resp.json()
            images = body.get("answer", {}).get("images", [])
            if not images:
                logger.warning(
                    "Custom API response contains no images. "
                    "If you are using the Gemini Web UI, ensure you have selected 'Create images' in the UI before sending image prompts."
                )
                return None

            image_info = images[0]
            src = image_info.get("src")
            if not src:
                logger.warning("Image object contains no 'src' field")
                return None

            # Prepare destination
            dest_folder = self.local_thumbnail_dir or os.path.join(os.getcwd(), "temp_thumbnails")
            Path(dest_folder).mkdir(parents=True, exist_ok=True)

            timestamp = int(time.time() * 1000)
            filename = f"thumb_{timestamp}.png"
            dest_path = os.path.join(dest_folder, filename)

            if src.startswith("data:"):
                # data URI (base64)
                header, b64 = src.split(',', 1)
                try:
                    data = base64.b64decode(b64)
                except Exception as e:
                    logger.warning("Failed to decode base64 image data: %s", e)
                    return None
                with open(dest_path, "wb") as f:
                    f.write(data)
                logger.info("Saved base64 image to %s", dest_path)
                return dest_path

            # Otherwise fetch via HTTP
            get_resp = requests.get(src, timeout=30)
            if get_resp.status_code != 200:
                logger.warning("Failed to download image from %s (status=%s)", src, get_resp.status_code)
                return None

            with open(dest_path, "wb") as f:
                f.write(get_resp.content)
            logger.info("Downloaded image to %s", dest_path)
            return dest_path

        except requests.RequestException as e:
            logger.warning("Network error while retrieving image: %s", e)
            return None
        except Exception as e:
            logger.warning("Unexpected error while retrieving image: %s", e)
            return None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Retrieve an image from a Gemini custom API")
    parser.add_argument("prompt", help="Image generation prompt")
    parser.add_argument("--api-url", help="Custom API URL", default=None)
    parser.add_argument("--out-dir", help="Local thumbnail dir", default=None)
    args = parser.parse_args()

    retriever = GeminiImageRetriever(api_url=args.api_url, local_thumbnail_dir=args.out_dir)
    path = retriever.retrieve_image(args.prompt)
    if path:
        print(path)
    else:
        print("Failed to retrieve image")
