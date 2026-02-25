import app
import xml.etree.ElementTree as ET

blogs = ['it_engineer_philosophy', 'daily_world_news']

for b_id in blogs:
    print(f"\n--- Blog: {b_id} ---")
    resp, err = app.hatena_request(b_id, '/entry')
    if err:
        print(f"Error: {err}")
        continue
    root = ET.fromstring(resp.content)
    entries = root.findall('atom:entry', app.HATENA_NS)
    for e in entries:
        title = e.find('atom:title', app.HATENA_NS).text
        updated = e.find('atom:updated', app.HATENA_NS).text
        content = e.find('atom:content', app.HATENA_NS)
        content_len = len(content.text) if content is not None and content.text else 0
        print(f"Title: {title} | Updated: {updated} | ContentLen: {content_len}")
        if '津田' in title or 'みゆき' in title or 'ミユキ' in title:
            print(f"  !!! KEYWORD FOUND IN TITLE !!!")
        if content is not None and content.text:
            if '津田' in content.text or 'みゆき' in content.text or 'ミユキ' in content.text:
                print(f"  !!! KEYWORD FOUND IN CONTENT !!!")
print("\nDone.")
