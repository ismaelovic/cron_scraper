import os
import requests
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()

URL = "https://booking.ctm.ma/journeys?dStop=283&oCity=5675&oDate=2026-08-08&fareClasses=BONUS_SCHEME_GROUP.ADULT,1"
TARGET_DEPARTURE = "11:00"
TARGET_ARRIVAL = "17:45"
NTFY_TOPIC = os.getenv("NTFY_TOPIC_BUS") or os.getenv("NTFY_TOPIC")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"


def send_alert(message):
    print(f"ALERT: {message}")
    if not NTFY_TOPIC:
        print("(No NTFY_TOPIC set, skipping push notification)")
        return
    resp = requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Priority": "5",
            "Tags": "bus,rotating_light",
            "Actions": f"view, Book Now, {URL.replace(',', '%2C')}",
        },
    )
    print(f"Notification response: {resp.status_code}")


def check_ctm():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)

        try:
            page.goto(URL, timeout=60000)
            page.wait_for_timeout(8000)

            body_text = page.inner_text("body")

            # Verify our journey is listed
            if TARGET_DEPARTURE not in body_text or TARGET_ARRIVAL not in body_text:
                print(f"Journey {TARGET_DEPARTURE}-{TARGET_ARRIVAL} not found on page.")
                return

            # Extract the section between our departure time and the next journey (or end)
            # Page renders journeys sequentially: "11:00 ... Complet ... 22:15 ..."
            dep_idx = body_text.index(TARGET_DEPARTURE)
            # Find next journey or end of text
            next_section = body_text[dep_idx:dep_idx + 300]

            print(f"Using topic: {NTFY_TOPIC}")

            if "Complet" in next_section:
                print(f"Journey {TARGET_DEPARTURE}-{TARGET_ARRIVAL} is still SOLD OUT (Complet).")
            elif "Réserver" in next_section:
                send_alert(
                    f"🚌 SEAT AVAILABLE! Hurry, the {TARGET_DEPARTURE} - {TARGET_ARRIVAL} Meknes→Al Hoceima bus now has available seats! Book now!"
                )
            else:
                print(f"Unexpected state for journey. Section: {next_section[:200]}")

        except Exception as e:
            print(f"Error checking CTM: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    check_ctm()
