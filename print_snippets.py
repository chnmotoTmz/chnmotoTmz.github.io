import app
import xml.etree.ElementTree as ET

blogs = ['it_engineer_philosophy', 'daily_world_news']

for b_id in blogs:
    print(f"\n--- Blog: {b_id} ---")
    resp, err = app.hatena_request(b_id, '/entry')
    if err: continue
    root = ET.fromstring(resp.content)
    # Using full namespace
    ns = {'atom': 'http://www.w3.org/2005/Atom'}
    for e in root.findall('atom:entry', ns):
        title = e.find('atom:title', ns).text
        content = e.find('atom:content', ns)
        snippet = content.text[:100] if content is not None and content.text else "None"
        print(f"Title: {title} | Snippet: {snippet}")
        
        # Internal keyword check
        for q in ['みゆき', '津田']:
            if content is not None and content.text and q in content.text:
                print(f"  !!! Match internal: {q}")
print("\nDone.")
