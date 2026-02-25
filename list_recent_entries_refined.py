import app
import xml.etree.ElementTree as ET

keywords = ['みゆき', '美雪', 'ミユキ', '津田']
blogs = ['it_engineer_philosophy', 'daily_world_news']

for b_id in blogs:
    print(f"\n--- Blog: {b_id} ---")
    resp, err = app.hatena_request(b_id, '/entry')
    if err:
        continue
    root = ET.fromstring(resp.content)
    entries = root.findall('atom:entry', app.HATENA_NS)
    for e in entries:
        title = e.find('atom:title', app.HATENA_NS).text or 'No Title'
        content = e.find('atom:content', app.HATENA_NS)
        content_text = content.text if content is not None else ""
        
        found_in_title = [q for q in keywords if q in title]
        found_in_content = [q for q in keywords if q in content_text]
        
        if found_in_title or found_in_content:
            print(f"MATCH: {title}")
            print(f"  Keywords in Title: {found_in_title}")
            print(f"  Keywords in Content: {found_in_content}")
            print(f"  Updated: {e.find('atom:updated', app.HATENA_NS).text}")
print("\nDone.")
