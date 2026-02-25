import app
import xml.etree.ElementTree as ET

keywords = ['みゆき', '美雪', 'ミユキ', '津田']
blogs = app.load_blogs_config()

for b_id, b_info in blogs.items():
    print(f"Deep checking content in blog: {b_id}")
    next_url = '/entry'
    entries_checked = 0
    # Check 2 pages
    for page in range(2):
        resp, err = app.hatena_request(b_id, next_url)
        if err: break
        root = ET.fromstring(resp.content)
        entries = root.findall('atom:entry', app.HATENA_NS)
        for e in entries:
            entries_checked += 1
            title = e.find('atom:title', app.HATENA_NS).text or ''
            content = e.find('atom:content', app.HATENA_NS).text or ''
            
            for q in keywords:
                if q in title or q in content:
                    print(f"  [FOUND '{q}'] Title: {title} | Updated: {e.find('atom:updated', app.HATENA_NS).text}")
        
        # Next
        next_url = None
        for link in root.findall('atom:link', app.HATENA_NS):
            if link.get('rel') == 'next':
                next_url = str(link.get('href'))
                break
        if not next_url: break

print("Done.")
