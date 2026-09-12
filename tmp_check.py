import os
from pathlib import Path

posts_dir = Path(r"c:\Users\motoc\chnmotoTmz.github.io\posts")
images_dir = Path(r"c:\Users\motoc\chnmotoTmz.github.io\images")

html_files = list(posts_dir.rglob("*.html"))
images = [f.name for f in images_dir.glob("*") if f.is_file()]

missing_images = []
for html_file in html_files:
    content = html_file.read_text(encoding="utf-8")
    
    if "<img " not in content:
        missing_images.append(html_file)

print(f"Total HTML files: {len(html_files)}")
print(f"Files missing images: {len(missing_images)}")

for file in missing_images:
    print(file.name)
