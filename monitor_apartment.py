import os
import re
import requests
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# List of projects to monitor at findbolig.nu
PROJECTS = [
    {"id": "arendal", "name": "Boligfond Arendal"},
    {"id": "vibehusene", "name": "Vibehusene"},
    {"id": "frederiksberg-boligfond", "name": "Frederiksberg Boligfond"},
    {"id": "solgaarden", "name": "Solgaarden"},
    {"id": "fuglevaenget", "name": "Fuglevænget"},
    {"id": "hvidkildegaard", "name": "Hvidkildegaard"},
    {"id": "oestergaarden", "name": "Østergaarden"},
    # Add more projects here as you find them
]

KEYWORDS_OPEN = ["tilmeld", "ansøg","først", "første", "ledig", "åben", "begrænset"]

BASE_URL = "https://www.findbolig.nu/da-dk/udlejere/{id}/"
NTFY_TOPIC = os.getenv("NTFY_TOPIC_APARTMENT") or os.getenv("NTFY_TOPIC")

def check_portal():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        
        for project in PROJECTS:
            page = context.new_page()
            url = BASE_URL.format(id=project['id'])
            try:
                print(f"Checking {project['name']} ({url})...")
                page.goto(url, wait_until="load", timeout=30000)
                page.wait_for_timeout(2000) # Wait for text to render
                
                # Logic: If 'Lukket for opskrivning' is NOT visible, it might be open!
                # We check for the presence of the "Closed" message.
                is_closed = page.get_by_text("Lukket for opskrivning", exact=False).is_visible()
                
                if not is_closed:
                    print(f"Potential opening for {project['name']}! Checking venteliste page...")
                    venteliste_url = url + "ekstern-venteliste"
                    page.goto(venteliste_url, wait_until="load", timeout=20000)
                    page.wait_for_timeout(2000)
                    # Look for high-confidence signup keywords using Case-Insensitive Regex
                    pattern = re.compile("|".join(KEYWORDS_OPEN), re.IGNORECASE)
                    has_button = page.get_by_text(pattern).filter(visible=True).count() > 0
                    
                    if has_button:
                        send_alert(f"🟢 VERIFIED OPEN: {project['name']} is now accepting signups! Link: {venteliste_url}")
                    else:
                        send_alert(f"⚠️ POSSIBLE CHANGE: {project['name']} 'Closed' message disappeared, but no signup button found. Check manually: {url}")
                else:
                    print(f"{project['name']} is still closed.")
                    
            except Exception as e:
                print(f"Failed to check {project['name']}: {e}")
            finally:
                page.close()
                
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

    # Optional test trigger for verifying notifications
    if os.getenv("TEST_NOTIFY") == "true":
        print("Sending test alert to verify notification pipeline...")
        send_alert("🏠 TEST ALERT: Apartment monitor pipeline is live!")
