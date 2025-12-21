import os
import hashlib
import base64
import requests

OUTDIR = os.path.join(os.getcwd(), "temp_thumbnails")
os.makedirs(OUTDIR, exist_ok=True)

url = "https://via.placeholder.com/150"
local_path = os.path.join(OUTDIR, "download_test.png")

print(f"Downloading {url} -> {local_path}")
resp = requests.get(url, timeout=10)
resp.raise_for_status()
with open(local_path, "wb") as f:
    f.write(resp.content)

size = os.path.getsize(local_path)
sha256 = hashlib.sha256(open(local_path, "rb").read()).hexdigest()
head_b64 = base64.b64encode(open(local_path, "rb").read()[:32]).decode('ascii')

print(f"Saved file: {local_path}")
print(f"Size (bytes): {size}")
print(f"SHA256: {sha256}")
print(f"First 32 bytes (base64): {head_b64}")
print("Done.")
