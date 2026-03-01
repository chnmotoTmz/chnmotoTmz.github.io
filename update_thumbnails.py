import os
import re

directory = 'posts'
files = [f for f in os.listdir(directory) if f.endswith('.html')]

for filename in files:
    filepath = os.path.join(directory, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if thumbnail already exists
    if '<figure class="main-thumbnail">' in content:
        print(f"Skipping {filename} - already has thumbnail.")
        continue

    # Extract title
    title_match = re.search(r'title:\s*(.*)', content)
    if not title_match:
        print(f"Skipping {filename} - no title found.")
        continue

    title = title_match.group(1).strip()

    # Generate seed from filename
    seed = filename.replace('.html', '').replace('-', '')
    # Or just use the first few chars of the hash of the title
    seed = str(abs(hash(title)))[:8]

    image_url = f"https://picsum.photos/seed/{seed}/800/400"

    # Prepare the snippet
    snippet = f'\n<figure class="main-thumbnail"><img src="{image_url}" alt="{title}"></figure>\n'

    # Insert immediately after the metadata block closing -->
    new_content = re.sub(r'(-->\s*)', r'\1' + snippet, content, count=1)

    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filename}")
    else:
        print(f"Could not find insertion point in {filename}")
