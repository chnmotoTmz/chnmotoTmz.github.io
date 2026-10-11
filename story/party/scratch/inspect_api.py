import requests
import json

def inspect_note_api(username):
    url = f"https://note.com/api/v2/creators/{username}/contents?kind=note&page=1"
    response = requests.get(url)
    data = response.json()
    items = data.get('data', {}).get('contents', [])
    if items:
        print(json.dumps(items[0], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    inspect_note_api("gifted_otter688")
