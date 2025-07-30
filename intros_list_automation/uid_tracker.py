import json
from pathlib import Path

UID_FILE = Path("seen_uids.json")

# Load or initialize UID memory
def load_uids():
    if UID_FILE.exists():
        with open(UID_FILE, "r") as f:
            return json.load(f)
    return {}

# Save UID memory
def save_uids(data):
    with open(UID_FILE, "w") as f:
        json.dump(data, f, indent=2)

# Check if we've already seen this UID for this sender
def is_uid_seen(sender: str, uid: str) -> bool:
    uids = load_uids()
    return uid in uids.get(sender, [])

# Mark this UID as processed
def mark_uid_seen(sender: str, uid: str):
    uids = load_uids()
    if sender not in uids:
        uids[sender] = []
    if uid not in uids[sender]:
        uids[sender].append(uid)
        save_uids(uids)
