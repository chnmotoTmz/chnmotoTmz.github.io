import app
import xml.etree.ElementTree as ET

q = 'みゆき'
blogs_to_check = ['daily_world_news', 'lifehacking1919'] # Correct keys from blogs.yml
# Actually in blogs.yml it is gadget_productivity

blogs_to_check = ['daily_world_news', 'gadget_productivity']

for b_id in blogs_to_check:
    print(f"Deep checking blog: {b_id}")
    resp, err = app.hatena_request(b_id, '/entry')
    if err:
        print(f"  Error: {err}")
        continue
    root = ET.fromstring(resp.content)
    entries = root.findall('atom:entry', app.HATENA_NS)
    for e in entries[:10]:
        title = e.find('atom:title', app.HATENA_NS).text or ''
        content = e.find('atom:content', app.HATENA_NS).text or ''
        if q in title or q in content:
            print(f"  !!! FOUND '{q}' in: {title}")
print("Done.")
