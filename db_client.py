import requests
import pandas as pd
from config import SUPABASE_API_URL, SUPABASE_API_KEY, SUPABASE_TABLE

def is_duplicate(deal, existing):
    return (
        deal[2] == existing["Series"] and
        deal[1] == existing["Deal Size"] and
        deal[5] == existing["Lead Investors"]
    )

def fetch_existing_deals(company_name):
    url = f"{SUPABASE_API_URL}/rest/v1/{SUPABASE_TABLE}?Company=eq.{company_name}"
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    }
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json()
    else:
        print(f"❌ Failed to fetch existing deals: {res.status_code} {res.text}")
        return []

def insert_deals(deals):
    if not deals:
        print("⚠️ No deals to insert.")
        return

    url = f"{SUPABASE_API_URL}/rest/v1/{SUPABASE_TABLE}"
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = []
    for deal in deals:
        try:
            existing_deals = fetch_existing_deals(deal[0])
            if any(is_duplicate(deal, existing) for existing in existing_deals):
                print(f"⏩ Skipping duplicate deal for {deal[0]}")
                continue

            payload.append({
                "Company": deal[0],
                "Deal Size": deal[1],
                "Series": deal[2],
                "Tagline": deal[3],
                "Location": deal[4],
                "Lead Investors": deal[5],
                "domain": deal[6],
                "Date" : deal[7],
                "source": deal[8],
            })
        except IndexError:
            print(f"⚠️ Skipping malformed deal: {deal}")

    if not payload:
        print("✅ All deals already exist in Supabase.")
        return

    res = requests.post(url, json=payload, headers=headers)

    if res.status_code in [200, 201]:
        print(f"✅ Inserted {len(payload)} new deals into Supabase.")
    else:
        print("❌ Failed to insert into Supabase:", res.status_code, res.text)

ctvc = pd.read_csv("clean_ctvc.csv")
head = ctvc.head().values.tolist()
insert_deals(head)