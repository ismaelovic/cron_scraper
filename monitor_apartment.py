import asyncio
import os
import re
import json
import requests
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

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

KEYWORDS_OPEN = ["tilmeld", "ansøg", "først", "første", "ledig", "åben", "begrænset"]
BASE_URL = "https://www.findbolig.nu/da-dk/udlejere/{id}/"
NTFY_TOPIC = os.getenv("NTFY_TOPIC_APARTMENT") or os.getenv("NTFY_TOPIC")
STATE_FILE = Path("state.json")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


async def check_project(browser, project, previous_state):
    url = BASE_URL.format(id=project['id'])
    was_closed = previous_state.get("is_closed", True)
    print(f"Checking {project['name']} ({url})...")

    for attempt in range(2):
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        try:
            response = await page.goto(url, wait_until="load", timeout=30000)

            # Server is down — preserve old state, don't retry
            if response and response.status >= 500:
                print(f"Server error ({response.status}) for {project['name']}, skipping.")
                return {"is_closed": was_closed}

            await page.wait_for_timeout(2000)
            is_closed = await page.get_by_text("Lukket for opskrivning", exact=False).is_visible()

            if not is_closed:
                if was_closed:  # Newly open — alert and do deep check
                    send_alert(
                        f"⚠️ LOW CONFIDENCE: {project['name']} 'Lukket for opskrivning' is no longer visible. Could be a site change or real opening.",
                        action_url=url
                    )
                    venteliste_url = url + "ekstern-venteliste"
                    try:
                        print(f"  Checking venteliste page for {project['name']}...")
                        await page.goto(venteliste_url, wait_until="load", timeout=20000)
                        await page.wait_for_timeout(2000)
                        pattern = re.compile("|".join(KEYWORDS_OPEN), re.IGNORECASE)
                        count = await page.get_by_text(pattern).filter(visible=True).count()
                        if count > 0:
                            send_alert(
                                f"🟢 VERIFIED OPEN: {project['name']} is now accepting signups!",
                                action_url=venteliste_url
                            )
                        else:
                            send_alert(
                                f"⚠️ POSSIBLE CHANGE: {project['name']} 'Closed' message disappeared but no signup button found. Check manually.",
                                action_url=url
                            )
                    except Exception as e:
                        print(f"  Could not check venteliste for {project['name']}: {e}")
                else:
                    print(f"{project['name']} is still open (already alerted).")
            else:
                print(f"{project['name']} is still closed.")

            return {"is_closed": is_closed}

        except Exception as e:
            if attempt == 0:
                print(f"Attempt 1 failed for {project['name']}: {e}. Retrying...")
            else:
                print(f"Failed after 2 attempts for {project['name']}: {e}")
        finally:
            await context.close()

    return {"is_closed": was_closed}


async def check_portal():
    state = load_state()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        results = await asyncio.gather(
            *[check_project(browser, project, state.get(project['id'], {})) for project in PROJECTS],
            return_exceptions=True
        )

        new_state = {}
        for project, result in zip(PROJECTS, results):
            if isinstance(result, Exception):
                print(f"Unexpected error for {project['name']}: {result}")
                new_state[project['id']] = state.get(project['id'], {"is_closed": True})
            else:
                new_state[project['id']] = result

        await browser.close()

    save_state(new_state)


def send_alert(message, action_url=None):
    if not NTFY_TOPIC:
        print(f"Alert (No NTFY_TOPIC): {message}")
        return

    headers = {"Priority": "5", "Tags": "house,rotating_light"}
    if action_url:
        headers["Actions"] = f"view, Open Page, {action_url}"

    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode('utf-8'),
        headers=headers
    )


if __name__ == "__main__":
    asyncio.run(check_portal())

    if os.getenv("TEST_NOTIFY") == "true":
        print("Sending test alert to verify notification pipeline...")
        send_alert("🏠 TEST ALERT: Apartment monitor pipeline is live!")
