import app
import xml.etree.ElementTree as ET

q = 'みゆき'
blogs = app.load_blogs_config()

for b_id in blogs.keys():
    print(f"Checking categories in blog: {b_id}")
    resp, err = app.hatena_request(b_id, '/entry')
    if err:
        continue
    root = ET.fromstring(resp.content)
    for e in root.findall('atom:entry', app.HATENA_NS):
        title = e.find('atom:title', app.HATENA_NS).text or ''
        cats = [c.get('term') for c in e.findall('atom:category', app.HATENA_NS)]
        
        # Check if 'みゆき' is in title or any category
        match = False
        if q in title: match = True
        for c in cats:
            if c and q in c: match = True
            
        if match:
            print(f"  !!! MATCH !!!")
            print(f"  Title: {title}")
            print(f"  Categories: {cats}")
            print(f"  URL: {e.find('atom:id', app.HATENA_NS).text}")
print("Check complete.")
