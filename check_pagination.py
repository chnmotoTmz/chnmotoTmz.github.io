import app
import xml.etree.ElementTree as ET

blogs = app.load_blogs_config()

for b_id in blogs.keys():
    print(f"Checking blog: {b_id}")
    next_url = '/entry'
    for i in range(1, 21): # Check up to 20 pages
        resp, err = app.hatena_request(b_id, next_url)
        if err:
            print(f"  Error on page {i}: {err}")
            break
        root = ET.fromstring(resp.content)
        entries = root.findall('atom:entry', app.HATENA_NS)
        if not entries:
            print(f"  No entries found on page {i}")
            break
        
        last_entry = entries[-1]
        updated = last_entry.find('atom:updated', app.HATENA_NS).text
        print(f"  Page {i:02} last entry: {updated}")
        
        # Keyword search while we are at it
        for e in entries:
            title = e.find('atom:title', app.HATENA_NS).text or ''
            if 'みゆき' in title or '津田' in title:
                 print(f"  !!! Found in Page {i}: {title} (Updated: {e.find('atom:updated', app.HATENA_NS).text})")

        # Next link
        next_url = None
        for link in root.findall('atom:link', app.HATENA_NS):
            if link.get('rel') == 'next':
                next_url = str(link.get('href'))
                break
        if not next_url:
            break
print("Finished pagination check.")
