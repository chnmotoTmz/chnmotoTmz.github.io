import requests
import json
import time
import os
import sys
import re
from html.parser import HTMLParser

# Ensure stdout handles UTF-8 for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

class NoteHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = ""
        self.in_p = False

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self.in_p = True
        elif tag == "br":
            self.text += "\n"
        elif tag in ["h1", "h2", "h3"]:
            self.text += "\n\n## "
        elif tag == "li":
            self.text += "\n- "

    def handle_endtag(self, tag):
        if tag == "p":
            self.text += "\n"
            self.in_p = False
        elif tag in ["h1", "h2", "h3"]:
            self.text += "\n"

    def handle_data(self, data):
        self.text += data

def html_to_text(html_content):
    if not html_content:
        return ""
    parser = NoteHTMLParser()
    parser.feed(html_content)
    return parser.text

def sanitize_filename(filename):
    # Remove characters that are not allowed in Windows filenames
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def get_articles(username):
    articles = []
    keys = set()
    page = 1
    total_count = None
    
    while True:
        url = f"https://note.com/api/v2/creators/{username}/contents?kind=note&page={page}"
        print(f"Fetching list: {url}")
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Error fetching list: {e}")
            break
            
        if total_count is None:
            total_count = data.get('data', {}).get('totalCount', 0)
            print(f"Total articles to fetch: {total_count}")
        
        items = data.get('data', {}).get('contents', [])
        if not items:
            break
            
        new_items_added = 0
        for item in items:
            key = item['key']
            if key not in keys:
                articles.append({
                    'title': item['name'],
                    'key': key,
                    'date': item.get('publishAt', 'unknown'),
                    'eyecatch': item.get('eyecatch')
                })
                keys.add(key)
                new_items_added += 1
        
        print(f"Collected {len(articles)}/{total_count} articles.")
        
        if new_items_added == 0 or len(articles) >= total_count:
            break
            
        page += 1
        time.sleep(0.5)
        
    return articles

def download_image(url, filepath):
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return False

def get_body(key):
    url = f"https://note.com/api/v3/notes/{key}"
    print(f"Fetching body: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('data', {}).get('body', '')
    except Exception as e:
        print(f"Error fetching body {key}: {e}")
        return ""

def main():
    username = "gifted_otter688"
    output_dir = r"c:\Users\motoc\story\party\articles"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
    
    print(f"Starting scrape for user: {username}")
    articles_meta = get_articles(username)
    print(f"Found {len(articles_meta)} articles in total.")
    
    for i, meta in enumerate(articles_meta):
        # Create a RAG-friendly markdown file for each article
        safe_title = sanitize_filename(meta['title'])
        base_filename = f"{len(articles_meta) - i:03d}_{safe_title}"
        filepath = os.path.join(output_dir, base_filename + ".md")
        
        if os.path.exists(filepath):
            print(f"Skipping ({i+1}/{len(articles_meta)}): {base_filename}.md (Already exists)")
            continue
            
        print(f"Processing ({i+1}/{len(articles_meta)}): {meta['title']}")
        
        # Handle thumbnail if exists
        thumbnail_name = None
        if meta.get('eyecatch'):
            # Try to get extension from URL or default to .jpg
            ext = ".jpg"
            if ".png" in meta['eyecatch']: ext = ".png"
            elif ".jpeg" in meta['eyecatch']: ext = ".jpg"
            
            thumbnail_name = base_filename + ext
            thumbnail_path = os.path.join(output_dir, thumbnail_name)
            print(f"  Downloading thumbnail: {thumbnail_name}")
            download_image(meta['eyecatch'], thumbnail_path)

        body_html = get_body(meta['key'])
        body_text = html_to_text(body_html)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # YAML Frontmatter for RAG metadata
            f.write("---\n")
            f.write(f"title: \"{meta['title'].replace('\"', '\\\"')}\"\n")
            f.write(f"date: {meta['date']}\n")
            f.write(f"url: https://note.com/{username}/n/{meta['key']}\n")
            if thumbnail_name:
                f.write(f"thumbnail: \"{thumbnail_name}\"\n")
            f.write(f"creator: {username}\n")
            f.write("---\n\n")
            f.write(body_text)
            f.write("\n")
        
        time.sleep(0.5)
    
    print(f"Done! All articles saved individually to {output_dir}")

if __name__ == "__main__":
    main()
