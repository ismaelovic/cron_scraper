import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Config
TARGET_URL = "https://www.sportsworld.dk/adidas-ultraboost-10-shoes-womens-210232#colcode=21023240"
# TARGET_SIZE = "8 (42)"
TARGET_SIZE = "6.5 (40)"
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

def check_stock():
    """
    Checks stock for a specific size on sportsworld.dk.
    The site provides size status in the initial HTML:
    - data-testid="swatch-button-enabled" for in-stock
    - data-testid="swatch-button-disabled" for out-of-stock
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "da-DK,da;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    try:
        print(f"Checking stock for size '{TARGET_SIZE}'...")
        response = requests.get(TARGET_URL, headers=headers, timeout=15)
        response.raise_for_status()
        
        html = response.text
        
        # We look for the button element that matches our size
        enabled_marker = f'data-testid="swatch-button-enabled" value="{TARGET_SIZE}"'
        disabled_marker = f'data-testid="swatch-button-disabled" value="{TARGET_SIZE}"'
        
        if enabled_marker in html:
            print(f"SUCCESS: Size {TARGET_SIZE} is AVAILABLE!")
            send_alert(f"👟 SNEAKERS IN STOCK! Size {TARGET_SIZE} is available at SportsWorld. Skynd dig: {TARGET_URL}")
        elif disabled_marker in html:
            print(f"Still out of stock: Size {TARGET_SIZE} is currently disabled.")
        else:
            # Fallback check: maybe the value format is slightly different or the site changed
            if TARGET_SIZE in html:
                print(f"Size '{TARGET_SIZE}' found in page, but state markers were missing.")
            else:
                print(f"Error: Size '{TARGET_SIZE}' not found in page source at all.")
                
    except Exception as e:
        print(f"Scrape failed: {e}")

def send_alert(message):
    if not NTFY_TOPIC:
        print(f"Alert (No NTFY_TOPIC set): {message}")
        return
        
    try:
        requests.post(f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={
                "Title": "Sneaker Stock Alert",
                "Priority": "5",
                "Tags": "athletic_shoe,fire"
            })
        print(f"Alert sent to ntfy topic: {NTFY_TOPIC}")
    except Exception as e:
        print(f"Failed to send alert: {e}")

if __name__ == "__main__":
    check_stock()
