import requests
from bs4 import BeautifulSoup
import sys

url = "https://lifehacking1919.hatenablog.jp/entry/20251125/1764066943"

try:
    response = requests.get(url)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Title
    title = soup.find('h1', class_='entry-title')
    print(f"Title: {title.get_text(strip=True) if title else 'Not found'}")
    
    # Categories
    categories = soup.find_all('a', class_='entry-category-link')
    print(f"Categories: {[c.get_text(strip=True) for c in categories]}")
    
    # Content
    content = soup.find('div', class_='entry-content')
    if content:
        text = content.get_text(strip=True)
        print(f"Full Content Length: {len(text)}")
        print(f"Full Content: {text}")
        
        # Links (Affiliate check)
        links = content.find_all('a')
        print("\n--- Links found ---")
        for link in links:
            href = link.get('href')
            text = link.get_text(strip=True)
            print(f"Link: {text} -> {href}")

    else:
        print("Content div not found")

except Exception as e:
    print(f"Error: {e}")
