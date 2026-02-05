import os
import requests
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Config - Adjust these to match the rental portal
TARGET_URL = "https://example-rental-portal.com/waiting-list"
NTFY_TOPIC = os.getenv("NTFY_TOPIC") 

def check_portal():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            print(f"Checking apartment portal: {TARGET_URL}")
            page.goto(TARGET_URL, wait_until="load", timeout=30000)
            
            # Logic for unknown behavior:
            # 1. Look for common 'Open' keywords
            # 2. Check if a previously 'disabled' element becomes 'enabled'
            # 3. Check for the disappearance of 'Closed' messages
            
            # Example: Search for typical "Join" or "Available" button texts
            positive_keywords = ["Join", "Open", "Available", "Tilmeld", "Ledig", "Ansøg"]
            found_positive = False
            
            for word in positive_keywords:
                if page.get_by_text(word, exact=False).is_visible():
                    print(f"Found positive keyword: {word}")
                    found_positive = True
                    break
            
            # We can also check for a specific button known to be the waitlist button
            # Replace '.waitlist-button' with a selector if you find one
            button = page.query_selector("button") 
            
            if found_positive:
                send_alert(f"🏠 POTENTIAL APARTMENT OPENING! Found '{word}' on page. {TARGET_URL}")
            else:
                print("No positive signals found yet.")
                
        except Exception as e:
            print(f"Scrape failed: {e}")
        finally:
            browser.close()

def send_alert(message):
    if not NTFY_TOPIC:
        print(f"Alert (No NTFY_TOPIC): {message}")
        return
        
    requests.post(f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode('utf-8'),
        headers={"Priority": "5", "Tags": "house,rotating_light"})

if __name__ == "__main__":
    check_portal()