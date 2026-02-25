import app
import xml.etree.ElementTree as ET

q = '美雪'
blogs = app.load_blogs_config()

for b_id in blogs.keys():
    print(f"Checking blog for '{q}': {b_id}")
    resp, err = app.hatena_request(b_id, '/entry')
    if err:
        continue
    root = ET.fromstring(resp.content)
    for e in root.findall('atom:entry', app.HATENA_NS):
        title = e.find('atom:title', app.HATENA_NS).text or ''
        content = e.find('atom:content', app.HATENA_NS).text or ''
        
        if q in title or q in content:
            print(f"  !!! FOUND '{q}' in article !!!")
            print(f"  Title: {title}")
print("Check complete.")
