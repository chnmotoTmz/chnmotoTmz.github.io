import app
import xml.etree.ElementTree as ET

keywords = ['みゆき', '美雪', 'ミユキ', '津田']
blogs = app.load_blogs_config()

for b_id in blogs.keys():
    print(f"Scanning {b_id}...")
    resp, err = app.hatena_request(b_id, '/entry')
    if err: continue
    root = ET.fromstring(resp.content)
    for e in root.findall('{http://www.w3.org/2005/Atom}entry'):
        title_el = e.find('{http://www.w3.org/2005/Atom}title')
        title = title_el.text if title_el is not None else ""
        content_el = e.find('{http://www.w3.org/2005/Atom}content')
        content = content_el.text if content_el is not None else ""
        
        for q in keywords:
            if q in title:
                print(f"  [TITLE MATCH '{q}'] {title}")
            if q in content:
                print(f"  [CONTENT MATCH '{q}'] {title} (Content length: {len(content)})")
print("Scan done.")
