import os
import glob
import re
from pathlib import Path
import difflib

posts_dir = Path(r"c:\Users\motoc\chnmotoTmz.github.io\posts")
images_dir = Path(r"c:\Users\motoc\chnmotoTmz.github.io\images")

htmls = list(posts_dir.rglob("*.html"))
images = list(images_dir.glob("*"))

def clean_text(text):
    text = re.sub(r'[^\w\s]', '', text)
    return text

print(f"Found {len(htmls)} posts and {len(images)} images.")

matches = []

for f in htmls:
    content = f.read_text(encoding="utf-8")
    title_match = re.search(r'<title>(.*?)(?: \|.*?)?</title>', content)
    
    if title_match:
        title = title_match.group(1).strip()
    else:
        title = f.stem
        
    # Find best matching image
    best_img = None
    best_ratio = 0
    
    for img in images:
        img_name = img.stem
        ratio = difflib.SequenceMatcher(None, clean_text(title), clean_text(img_name)).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_img = img
            
    matches.append((f, title, best_img, best_ratio))

matches.sort(key=lambda x: x[3], reverse=True)

with open('match_results.txt', 'w', encoding='utf-8') as out:
    for f, title, img, ratio in matches:
        out.write(f"Post: {f.name}\n")
        out.write(f"Title: {title}\n")
        out.write(f"Image: {img.name if img else 'None'}\n")
        out.write(f"Ratio: {ratio:.2f}\n")
        out.write("-" * 40 + "\n")
