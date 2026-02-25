import os
import requests
import json
import env_loader

def check_credits():
    env_loader.load()
    client_id = os.getenv("IMGUR_CLIENT_ID")
    
    if not client_id:
        print("Error: IMGUR_CLIENT_ID not found.")
        return

    url = "https://api.imgur.com/3/credits"
    headers = {"Authorization": f"Client-ID {client_id}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                credits = data.get("data", {})
                print("--- Imgur API Credits ---")
                print(f"User Limit: {credits.get('UserLimit')}")
                print(f"User Remaining: {credits.get('UserRemaining')}")
                print(f"User Reset: {credits.get('UserReset')} (timestamp)")
                print(f"Client Limit: {credits.get('ClientLimit')}")
                print(f"Client Remaining: {credits.get('ClientRemaining')}")
            else:
                print(f"API Error: {data}")
        else:
            print(f"Failed to get credits. Response: {response.text}")

    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    check_credits()
