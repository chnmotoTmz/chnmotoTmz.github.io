import os
import re
from pathlib import Path

posts_dir = Path('c:/Users/motoc/chnmotoTmz.github.io/posts')
images_dir = Path('c:/Users/motoc/chnmotoTmz.github.io/images')

htmls = list(posts_dir.rglob('*.html'))

with open('c:/Users/motoc/chnmotoTmz.github.io/match_results.txt', 'r', encoding='utf-8') as f:
    lines = f.read().strip().split('----------------------------------------\n')

# Parse match results
match_map = {}
for block in lines:
    if not block.strip(): continue
    block_lines = block.strip().split('\n')
    post_name = block_lines[0].replace('Post: ', '').strip()
    img_name = block_lines[2].replace('Image: ', '').strip()
    match_map[post_name] = img_name

for f in htmls:
    # skip if dir index
    if f.name == 'index.html': continue

    content = f.read_text(encoding='utf-8')
    img_name = match_map.get(f.name, 'None')
    if img_name == 'None': continue
    
    # Calculate relative path from html file to images dir
    rel_path = os.path.relpath(images_dir / img_name, f.parent).replace('\\', '/')
    
    # Check if there is already a main-thumbnail figure
    if '<figure class="main-thumbnail">' in content:
        # replace the img src
        content = re.sub(r'(<figure class="main-thumbnail"><img[^>]*?src=)["\'][^"\']+["\']', 
                         r'\g<1>"' + rel_path + '"', content)
    else:
        # insert new figure right after opening <article> tag
        figure_html = f'<figure class="main-thumbnail"><img src="{rel_path}" alt="記事サムネイル" style="width:100%;max-height:400px;object-fit:cover;border-radius:8px;margin-bottom:1.5rem;"></figure>'
        
        if '<article class="premium-article">' in content:
            content = content.replace('<article class="premium-article">', f'<article class="premium-article">\n{figure_html}', 1)
        elif '<article>' in content:
            content = content.replace('<article>', f'<article>\n{figure_html}', 1)
            
    f.write_text(content, encoding='utf-8')

# Create index.html redrects in posts/ subdirectories
for dirpath, dirnames, filenames in os.walk(posts_dir):
    depth = len(Path(dirpath).relative_to(posts_dir.parent).parts) - 1
    rel = "../" * depth
    redir_html = f'<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url={rel}index.html" /></head><body></body></html>'
    idx_path = Path(dirpath) / "index.html"
    idx_path.write_text(redir_html, encoding="utf-8")

print('Thumbnail insertion and redirects complete.')
