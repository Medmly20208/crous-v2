"""
Uses a real (headless) browser to load the CROUS Marseille housing search
page -- this is necessary because the page's content is rendered by
JavaScript, so plain HTTP requests (requests library) never see the
actual text.

Polls every N seconds until:
  - the page has fully loaded (header "Mon logement pour l'annee
    prochaine 2026-2027" is present), AND
  - "Aucun logement trouve pour Marseille" (no results) is NO LONGER present

...then sends you an email notification.

SETUP (one-time):
    pip install playwright
    playwright install chromium

USAGE:
    python check_marseille_logement.py

Before running, fill in the EMAIL CONFIG section below with your own
email credentials (see notes at the bottom of this file for Gmail setup).
"""

import time
import smtplib
import ssl
from email.mime.text import MIMEText
from datetime import datetime
import sys
from playwright.sync_api import sync_playwright

# ---- SEARCH CONFIG ----
URL = (
    "https://trouverunlogement.lescrous.fr/tools/47/search"
    "?bounds=5.2286902_43.3910329_5.5324758_43.1696205"
    "&locationName=Marseille+%2813000%29"
)
PAGE_LOADED_TEXT = "Mon logement pour"
NO_RESULTS_TEXT = "aucun logement trouvé pour lyon"
CHECK_INTERVAL_SECONDS = 60  # be polite to the server, don't go too low
PAGE_LOAD_TIMEOUT_MS = 60000  # 30 seconds for the browser to load the page

# ---- EMAIL CONFIG (fill these in) ----
SMTP_SERVER = "smtp.gmail.com"    
SMTP_PORT = 465                      
SENDER_EMAIL = "moulaymohamed856@gmail.com"
SENDER_APP_PASSWORD = "gvonnvmnqklojvud"
RECEIVER_EMAIL = "moulaymohamed856@gmail.com"

def check_once(page):
    """Returns True if page loaded AND listings are available,
    False if page loaded but still shows no results,
    None if the page didn't load as expected."""
    try:
        page.goto(URL, timeout=PAGE_LOAD_TIMEOUT_MS, wait_until="networkidle")
        # Give any lingering JS rendering a moment to settle
        page.wait_for_timeout(1500)
        body_text = page.inner_text("body").lower()
        safe_text = body_text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8", errors="replace"
        )
       
        page_loaded = not( "Aucun logement trouv" in safe_text)
        no_results = "aucun logement trouv" in safe_text

        print(no_results)

        return not no_results
    except Exception as e:
        print(f"   Error loading page: {e}")
        return None


def send_email_alert():
    subject = "Logement disponible à Marseille !"
    body = f"Des logements sont maintenant disponibles.\n\nLien:\n{URL}"

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())

    print("  Email sent!")


def main():
    print(f"Watching: {URL}")
    print(f"Checking every {CHECK_INTERVAL_SECONDS}s. Press Ctrl+C to stop.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        attempt = 0
        try:
            while True:
                attempt += 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                result = check_once(page)

                if result is True:
                    print(f"[{timestamp}] Attempt {attempt}: Listings found! Sending email...")
                    try:
                        send_email_alert()
                    except Exception as e:
                        print(f"  [!] Failed to send email: {e}")
                        print("  Check your EMAIL CONFIG settings at the top of the script.")
                    break
                elif result is False:
                    print(f"[{timestamp}] Attempt {attempt}: No listings yet, waiting...")
                else:
                    print(f"[{timestamp}] Attempt {attempt}: Error checking page, will retry...")

                time.sleep(CHECK_INTERVAL_SECONDS)
        finally:
            browser.close()

    print("\nDone.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")

# -----------------------------------------------------------------------
# SETUP NOTES:
#
# 1. Install dependencies:
#      pip install playwright
#      playwright install chromium
#    (the second command downloads the actual browser binary Playwright
#    controls -- only needs to be run once)
#
# EMAIL SETUP NOTES (Gmail example):
# 1. You cannot use your normal Gmail password for SMTP anymore.
# 2. Enable 2-Step Verification on your Google account:
#    https://myaccount.google.com/security
# 3. Create an "App Password":
#    https://myaccount.google.com/apppasswords
#    (choose "Mail" as the app) -> Google gives you a 16-character password.
# 4. Paste that 16-character password into SENDER_APP_PASSWORD above
#    (remove spaces).
# 5. SENDER_EMAIL and RECEIVER_EMAIL can be the same address if you just
#    want to email yourself.
#
# Using Outlook/Hotmail instead? Set:
#    SMTP_SERVER = "smtp.office365.com"
#    SMTP_PORT = 587
# and use smtplib.SMTP (not SMTP_SSL) with server.starttls() before login.
# Let me know if you're on Outlook and I'll adjust the script for you.
# -----------------------------------------------------------------------
