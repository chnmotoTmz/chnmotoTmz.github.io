import os
import hashlib
import base64
import threading
import time
from http.server import SimpleHTTPRequestHandler
import socketserver
import requests

BASE_DIR = os.path.join(os.getcwd(), "temp_thumbnails")
os.makedirs(BASE_DIR, exist_ok=True)

# Create a small 1x1 PNG file as source
source_path = os.path.join(BASE_DIR, "local_source.png")
if not os.path.exists(source_path):
    b64 = (
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVQI12NgYAAAAAMA'
        'ASsJTYQAAAAASUVORK5CYII='
    )
    with open(source_path, "wb") as f:
        f.write(base64.b64decode(b64))

# Start a local HTTP server serving BASE_DIR
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

os.chdir(BASE_DIR)

with socketserver.TCPServer(("127.0.0.1", 0), QuietHandler) as httpd:
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    print(f"Local HTTP server running at http://127.0.0.1:{port}/")

    # Download the file via requests
    url = f"http://127.0.0.1:{port}/local_source.png"
    dest = os.path.join(BASE_DIR, "downloaded_local.png")
    print(f"Downloading {url} -> {dest}")
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        f.write(resp.content)

    size = os.path.getsize(dest)
    sha256 = hashlib.sha256(open(dest, "rb").read()).hexdigest()
    head_b64 = base64.b64encode(open(dest, "rb").read()[:32]).decode('ascii')

    print(f"Saved file: {dest}")
    print(f"Size (bytes): {size}")
    print(f"SHA256: {sha256}")
    print(f"First 32 bytes (base64): {head_b64}")

    # Shutdown server
    httpd.shutdown()
    thread.join()
    print("Server stopped")
