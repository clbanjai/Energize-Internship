import time
import imaplib
import email
from bs4 import BeautifulSoup
from uid_tracker import is_uid_seen, mark_uid_seen
from parser import extract_html_text
from deal_extractor import extract_deals_from_text
from db_client import insert_deals
from config import EMAIL_ADDRESS, EMAIL_PASSWORD, IMAP_SERVER, WATCHLIST

# Establish connection to IMAP
imap = imaplib.IMAP4_SSL(IMAP_SERVER)
imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

def fetch_and_process():
    imap.select("inbox")
    for sender in WATCHLIST:
        status, data = imap.uid('search', None, f'FROM "{sender}"')
        if status != "OK":
            continue
        uids = data[0].split()
        for uid in uids:
            uid_str = uid.decode()
            if is_uid_seen(sender, uid_str):
                continue
            print(f"\n📩 New email from {sender} (UID: {uid_str})")
            status, msg_data = imap.uid('fetch', uid, '(RFC822)')
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            html = None
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        html = part.get_payload(decode=True).decode()
                        break
            else:
                html = msg.get_payload(decode=True).decode()

            if html:
                text = extract_html_text(html)
                print("🧠 Extracting structured data...")
                deals = extract_deals_from_text(text)
                print(f"✅ Extracted {len(deals)} deals.")
                insert_deals(deals)

            mark_uid_seen(sender, uid_str)

def run_monitor(interval=600):
    print("📡 Monitoring newsletters...")
    try:
        while True:
            fetch_and_process()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 Monitor stopped.")
        imap.logout()

if __name__ == "__main__":
    run_monitor()

