import app
import xml.etree.ElementTree as ET

keywords = ['みゆき', '津田', '名探偵']
blogs = app.load_blogs_config()

for b_id, b_info in blogs.items():
    print(f"Checking blog: {b_id} ({b_info.get('blog_name')})")
    resp, err = app.hatena_request(b_id, '/entry')
    if err:
        print(f"  Error: {err}")
        continue
        
    root = ET.fromstring(resp.content)
    entries = root.findall('atom:entry', app.HATENA_NS)
    for entry in entries:
        title = entry.find('atom:title', app.HATENA_NS).text or ''
        content = entry.find('atom:content', app.HATENA_NS).text or ''
        
        for q in keywords:
            if q in title or q in content:
                print(f"  !!! FOUND '{q}' in article !!!")
                print(f"  Title: {title}")
                print(f"  Blog: {b_id}")
                print(f"  Content Snippet: {content[:200].replace('\\n', ' ')}")
                print("-" * 30)
                break
print("Search complete.")
