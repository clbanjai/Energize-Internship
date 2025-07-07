import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
from config import EMAIL_ADDRESS, EMAIL_PASSWORD, IMAP_SERVER, WATCHLIST
from uid_tracker import is_uid_seen, mark_uid_seen


def fetch_unread_newsletters():
    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    imap.select("Inbox")

    messages = []

    for sender in WATCHLIST:
        sender = sender.strip()
    
        status, response = imap.search(None, f'FROM "{sender}"')
        if status != "OK":
            print(f"❌ Failed to search inbox for {sender}")
            continue

        email_ids = response[0].split()
        for eid in reversed(email_ids):  # latest first
            uid = eid.decode()
            # if is_uid_seen(sender, uid):
            #     continue

            status, msg_data = imap.fetch(eid, "(RFC822)")
            if status != "OK":
                continue
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            html_content = None
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        html_content = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        break
            else:
                html_content = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            if html_content:
                messages.append({
                    "sender": sender,
                    "uid": uid,
                    "html": html_content,
                    "subject": msg["Subject"]
                })
                mark_uid_seen(sender, uid)

    imap.logout()
    return messages


import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
from config import EMAIL_ADDRESS, EMAIL_PASSWORD, IMAP_SERVER, WATCHLIST
from uid_tracker import is_uid_seen, mark_uid_seen


def fetch_unread_newsletters():
    imap = imaplib.IMAP4_SSL(IMAP_SERVER)
    imap.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    imap.select("Inbox")

    messages = []

    for sender in WATCHLIST:
        sender = sender.strip()
        status, response = imap.search(None, f'FROM "{sender}"')
        if status != "OK":
            print(f"❌ Failed to search inbox for {sender}")
            continue

        email_ids = response[0].split()
        for eid in reversed(email_ids):  # latest first
            uid = eid.decode()
            # if is_uid_seen(sender, uid):
            #     continue

            status, msg_data = imap.fetch(eid, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            html_content = None
            text_content = None
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    # print(f"THIS IS THE CONTENT TYPE {content_type}")
                    if content_type == "text/html":
                        html_content = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    elif content_type == "text/plain":
                        text_content = part.get_payload(decode=True).decode("utf-8", errors="ignore")
            else:
                content_type = msg.get_content_type()
                # print(f"THIS IS THE CONTENT TYPE {content_type}")

                if content_type == "text/html":
                    html_content = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                elif content_type == "text/plain":
                    text_content = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

            if html_content or text_content:
                messages.append({
                    "sender": sender,
                    "uid": uid,
                    "html": html_content,
                    "text": text_content,
                    "subject": msg["Subject"]
                })
                mark_uid_seen(sender, uid)

    imap.logout()
    return messages


