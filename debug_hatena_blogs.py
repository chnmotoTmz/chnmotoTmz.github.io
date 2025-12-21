import os
import requests
from requests.auth import HTTPBasicAuth
import env_loader
import xml.etree.ElementTree as ET

# Load environment variables
env_loader.load()

accounts = [
    {"id": "yamasan1969", "key_var": "YAMASAN_HATENA_API_KEY"},
    {"id": "motochan1969", "key_var": "MOTOCHAN_HATENA_API_KEY"},
    {"id": "kaigot", "key_var": "KAIGOT_HATENA_API_KEY"},
]

for account in accounts:
    hatena_id = account["id"]
    api_key = os.environ.get(account["key_var"])
    
    print(f"\n--- Checking account: {hatena_id} ---")

    if not api_key:
        print(f"Error: {account['key_var']} not found in environment.")
        continue

    url = f"https://blog.hatena.ne.jp/{hatena_id}/atom"

    # print(f"Fetching service document from: {url}")

    response = requests.get(url, auth=HTTPBasicAuth(hatena_id, api_key))

    if response.status_code == 200:
        # print("Successfully fetched service document.")
        try:
            root = ET.fromstring(response.content)
            # Namespaces
            ns = {'app': 'http://www.w3.org/2007/app', 'atom': 'http://www.w3.org/2005/Atom'}
            
            workspaces = root.findall('app:workspace', ns)
            for workspace in workspaces:
                title = workspace.find('atom:title', ns).text
                # print(f"Workspace: {title}")
                collections = workspace.findall('app:collection', ns)
                for collection in collections:
                    href = collection.get('href')
                    title_elem = collection.find('atom:title', ns)
                    c_title = title_elem.text if title_elem is not None else "No Title"
                    print(f"  - Blog: {c_title}")
                    print(f"    URL: {href}")
        except Exception as e:
            print(f"Error parsing XML: {e}")
    else:
        print(f"Failed to fetch service document. Status: {response.status_code}")
