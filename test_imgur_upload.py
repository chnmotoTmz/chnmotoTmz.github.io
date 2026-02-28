import os
import sys
from PIL import Image
from src.services.imgur_service import ImgurService
import env_loader

def create_dummy_image(path: str):
    """Creates a simple dummy image for testing."""
    img = Image.new('RGB', (100, 100), color = (73, 109, 137))
    img.save(path)
    print(f"Created dummy image at {path}")

def main():
    # Load environment variables
    env_loader.load()
    
    print("--- Imgur Environment Variables ---")
    client_id = os.getenv("IMGUR_CLIENT_ID")
    access_token = os.getenv("IMGUR_ACCESS_TOKEN")
    
    if client_id:
        print(f"IMGUR_CLIENT_ID: {client_id[:4]}...{client_id[-4:]} (Found)")
    else:
        print("IMGUR_CLIENT_ID: Not Found")
        
    if access_token:
        print(f"IMGUR_ACCESS_TOKEN: {access_token[:4]}...{access_token[-4:]} (Found)")
    else:
        print("IMGUR_ACCESS_TOKEN: Not Found")

    if not client_id and not access_token:
        print("Error: No Imgur credentials found. Please set IMGUR_CLIENT_ID or IMGUR_ACCESS_TOKEN.")
        sys.exit(1)

    # Use existing test image or create a dummy one
    test_image_path = "test_image_1765290794374.png"
    if not os.path.exists(test_image_path):
        print(f"Test image {test_image_path} not found. Creating a dummy one.")
        test_image_path = "dummy_test_image.png"
        create_dummy_image(test_image_path)
    else:
        print(f"Using existing test image: {test_image_path}")

    print("\n--- Testing Imgur Upload ---")
    try:
        service = ImgurService()
        result = service.upload_image(test_image_path, title="Test Image from Gemini CLI", description="This is a test upload.")
        
        if result.get("success"):
            print("Upload Successful!")
            print(f"Image Link: {result.get('link')}")
        else:
            print("Upload Failed.")
            print(f"Error: {result.get('error')}")
            print(f"Status Code: {result.get('status')}")
            
    except Exception as e:
        print(f"An exception occurred during upload: {e}")

if __name__ == "__main__":
    main()
