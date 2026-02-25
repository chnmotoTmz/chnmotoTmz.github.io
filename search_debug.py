import app
import xml.etree.ElementTree as ET

q = '津田'
blogs = app.load_blogs_config()
results = []
count_scanned = 0

for b_id, b_info in blogs.items():
    print(f"Scanning blog: {b_id}")
    next_url = '/entry'
    pages_scanned = 0
    blog_entries_count = 0
    while next_url and pages_scanned < 2:  # 2ページに制限
        resp, err = app.hatena_request(b_id, next_url)
        if err:
            print(f"  Error: {err}")
            break
            
        root = ET.fromstring(resp.content)
        entries = root.findall('atom:entry', app.HATENA_NS)
        for entry in entries:
            count_scanned += 1
            blog_entries_count += 1
            title_el = entry.find('atom:title', app.HATENA_NS)
            content_el = entry.find('atom:content', app.HATENA_NS)
            categories = [c.get('term') for c in entry.findall('atom:category', app.HATENA_NS)]
            
            title = title_el.text if title_el is not None and title_el.text else ''
            content = content_el.text if content_el is not None and content_el.text else ''
            
            if blog_entries_count <= 5:
                print(f"  [Top {blog_entries_count}] {title}")

            match_found = False
            if q in title or q in content:
                match_found = True
            for cat in categories:
                if cat and q in cat:
                    match_found = True
            
            if match_found:
                print(f"  [Match] Title: {title}")
                results.append((b_id, title))
                
        # Get next page link
        next_url = None
        for link in root.findall('atom:link', app.HATENA_NS):
            if link.get('rel') == 'next':
                next_url = str(link.get('href'))
                break
        pages_scanned += 1
                
print(f"Total entries scanned: {count_scanned}")
print("Final matches:", results)
