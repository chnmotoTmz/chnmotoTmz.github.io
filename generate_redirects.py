import os
from pathlib import Path

posts_dir = Path('c:/Users/motoc/chnmotoTmz.github.io/posts')
root_dir = posts_dir.parent

# Create index.html redrects in posts/ subdirectories
for dirpath, dirnames, filenames in os.walk(posts_dir):
    depth = len(Path(dirpath).relative_to(root_dir).parts)
    rel = "../" * depth
    redir_html = f'<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0; url={rel}index.html" /></head><body></body></html>'
    idx_path = Path(dirpath) / "index.html"
    idx_path.write_text(redir_html, encoding="utf-8")

print('Index redirects recreated.')
