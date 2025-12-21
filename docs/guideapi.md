# Gemini Image Retriever

A Python module to retrieve images from a custom Gemini API endpoint.

## Installation

```bash
pip install requests python-dotenv
```

## Usage

### As a Module

```python
from gemini_image_retriever import GeminiImageRetriever

retriever = GeminiImageRetriever()
image_path = retriever.retrieve_image("A beautiful sunset over mountains")
if image_path:
    print(f"Image saved at: {image_path}")
else:
    print("Failed to retrieve image")
```

### As a CLI Tool

```bash
python gemini_image_retriever.py "A beautiful sunset over mountains"
```

## Configuration

Set the following environment variables (e.g., in `.env.production`):

For development, you can place sensitive tokens in a local `.env.develop` (or `.env.development`) file; the loader will read these files and use their values (they override existing env vars when present).

- `CUSTOM_THUMBNAIL_API_URL`: The API endpoint URL
- `CUSTOM_THUMBNAIL_API_BEARER`: Bearer token (optional)
- `LOCAL_THUMBNAIL_DIR`: Directory where images are downloaded (optional)
- `ALLOW_MAGICHOUR_FALLBACK`: If `true`, allow MagicHour to be used as a fallback image generation service (default: `false`).
- `CUSTOM_THUMBNAIL_WAIT_FOREVER`: If `true`, the thumbnail retrieval process will wait indefinitely for a browser-download into `LOCAL_THUMBNAIL_DIR` (default: `false`).
- `CUSTOM_THUMBNAIL_WAIT_SECONDS`: Poll timeout in seconds when waiting for browser-download (default: `60`).
- `CUSTOM_THUMBNAIL_MODE_SET_RETRIES`: Number of attempts to set wrapper mode to `Thinking` before proceeding (default: `3`).
- `CUSTOM_THUMBNAIL_API_RETRIES`: Number of attempts to call the custom thumbnail `/api/ask` endpoint (default: `3`).

**Note about image generation (Gemini Web UI):**

- If you use Gemini's Web UI as the backend, make sure you open the menu on the UI and **select "Create images"** before sending image prompts. If the UI is in text mode, the API response will not contain images and this module will not download any files. Also confirm `CUSTOM_THUMBNAIL_API_URL` is pointed to an endpoint that produces images and that `LOCAL_THUMBNAIL_DIR` is set to a writable directory where images are saved.

- **New:** You can request the extension to switch UI modes programmatically by including an optional `mode` field in the JSON body sent to `/api/ask` (e.g., `{ "prompt": "...", "mode": "Thinking" }`). The extension will attempt to toggle the UI and will emit a `mode_change_result` event with the result. Note: this is best-effort because Gemini's DOM may change. For backward compatibility, submitting `"mode": "image"` or `"images"` is supported and will be mapped to `"Thinking"` by the server.

  - The extension will try a few selectors to find the mode control. If the UI structure has changed, update the following selector(s) in `extension/content.js`:

    - `#app-root > main > side-navigation-v2 > bard-sidenav-container > bard-sidenav-content > div.content-wrapper > div > div.content-container > chat-window > div > input-container > div > input-area-v2 > div > div > div.trailing-actions-wrapper > div.model-picker-container > bard-mode-switcher > div > button`
    - `#app-root > main > side-navigation-v2 > bard-sidenav > side-navigation-content > div > div > mat-action-list.mat-mdc-action-list.mat-mdc-list-base.mdc-list.top-action-list.ng-star-inserted > side-nav-action-button > button`

## API

### Class: GeminiImageRetriever

#### Constructor

```python
GeminiImageRetriever(api_url=None, bearer_token=None, local_thumbnail_dir=None, timeout=180)
```

- `api_url`: API endpoint URL
- `bearer_token`: Authentication token
- `local_thumbnail_dir`: Local directory for image downloads
- `timeout`: Request timeout in seconds

#### Method: retrieve_image(prompt)

Sends a prompt to the API and retrieves the generated image.

- **Args**: `prompt` (str) - The image generation prompt
- **Returns**: Path to the saved image file (str) or None if failed

## License

This module is for testing and development purposes. Ensure compliance with API terms of service.

---

## Testing note ⚠️

- **Missing automated test:** Integration/unit test for the content generation and publisher flows is not included yet. Please create `tests/test_content_publisher.py` to validate:
  - `_generate_content` actually calls the Gemini API (or your local wrapper) and returns expected structure
  - `ContentPublisher.generate_and_publish` sends requests to the configured local endpoints
- **Manual steps for browser validation:** See `IMPLEMENTATION_STATUS.md` in the repo root for a concise checklist on steps to run and validate behavior in the browser and local server.
- **Permission note:** Creating the missing test file requires file creation permissions.
