"""
GIF thumbnails (Google Doodles) をPicsum画像に差し替えるスクリプト。
- images/ 内の 99,092 bytes の .gif を検出
- 各GIFに対してユニークなPicsum画像をダウンロード
- 同じベース名の .jpg として保存
- posts/ 内のHTMLと index.html 内の参照を .gif → .jpg に更新
"""
import os
import re
import sys
import time
import urllib.request

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IMAGES_DIR = os.path.join(REPO_DIR, 'images')
POSTS_DIR = os.path.join(REPO_DIR, 'posts')
INDEX_HTML = os.path.join(REPO_DIR, 'index.html')
DOODLE_SIZE = 99092  # exact size of the Google Doodle GIF

def find_doodle_gifs():
    """Find all GIF files that are exactly the Google Doodle size."""
    gifs = []
    for f in os.listdir(IMAGES_DIR):
        if f.lower().endswith('.gif'):
            fp = os.path.join(IMAGES_DIR, f)
            if os.path.getsize(fp) == DOODLE_SIZE:
                gifs.append(f)
    return gifs

def download_picsum(dest_path, seed, width=1200, height=675):
    """Download a unique Picsum image."""
    url = f"https://picsum.photos/seed/{seed}/{width}/{height}.jpg"
    print(f"  Downloading: {url}")
    try:
        urllib.request.urlretrieve(url, dest_path)
        print(f"  → Saved: {os.path.basename(dest_path)} ({os.path.getsize(dest_path)} bytes)")
        return True
    except Exception as e:
        print(f"  ✗ Download failed: {e}")
        return False

def replace_in_file(filepath, old_text, new_text):
    """Replace text in a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        if old_text in content:
            content = content.replace(old_text, new_text)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    except Exception as e:
        print(f"  Warning: Could not process {filepath}: {e}")
    return False

def find_html_files(directory):
    """Recursively find all HTML files."""
    html_files = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith('.html'):
                html_files.append(os.path.join(root, f))
    return html_files

def main():
    gifs = find_doodle_gifs()
    print(f"Found {len(gifs)} Google Doodle GIF(s) to replace.\n")
    
    if not gifs:
        print("Nothing to do!")
        return
    
    # Collect all HTML files to update
    html_files = find_html_files(POSTS_DIR)
    if os.path.exists(INDEX_HTML):
        html_files.append(INDEX_HTML)
    print(f"Will scan {len(html_files)} HTML file(s) for references.\n")
    
    replaced = 0
    for i, gif_name in enumerate(gifs):
        print(f"[{i+1}/{len(gifs)}] {gif_name}")
        
        # New filename: same basename but .jpg
        base_name = os.path.splitext(gif_name)[0]
        jpg_name = base_name + '.jpg'
        jpg_path = os.path.join(IMAGES_DIR, jpg_name)
        
        # Skip if jpg already exists and is a real image
        if os.path.exists(jpg_path) and os.path.getsize(jpg_path) > 10000:
            print(f"  → JPG already exists ({os.path.getsize(jpg_path)} bytes), skipping download")
        else:
            # Use a hash of the filename as seed for consistent unique images
            seed = abs(hash(gif_name)) % 100000
            if not download_picsum(jpg_path, seed):
                print(f"  ✗ Skipping {gif_name}")
                continue
            time.sleep(0.3)  # polite delay
        
        # Update HTML references: .gif → .jpg
        refs_updated = 0
        for html_file in html_files:
            if replace_in_file(html_file, gif_name, jpg_name):
                refs_updated += 1
        
        # Also check for URL-encoded or partial references
        # Handle relative path references like ../../images/NAME.gif
        rel_gif = f"images/{gif_name}"
        rel_jpg = f"images/{jpg_name}"
        for html_file in html_files:
            replace_in_file(html_file, rel_gif, rel_jpg)
        
        # Delete the old GIF
        gif_path = os.path.join(IMAGES_DIR, gif_name)
        try:
            os.remove(gif_path)
            print(f"  → Deleted old GIF")
        except Exception as e:
            print(f"  Warning: Could not delete {gif_name}: {e}")
        
        replaced += 1
        print(f"  → Updated {refs_updated} HTML reference(s)\n")
    
    print(f"\nDone! Replaced {replaced}/{len(gifs)} thumbnails.")
    print("Run 'npm run build' to regenerate index.html, then commit & push.")

if __name__ == '__main__':
    main()
