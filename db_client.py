import requests
import pandas as pd
import uuid
from config import SUPABASE_API_URL, SUPABASE_API_KEY

# Table names
COMPANIES_TABLE = "companies"
FUNDINGS_TABLE = "fundings"

HEADERS = {
    "apikey": SUPABASE_API_KEY,
    "Authorization": f"Bearer {SUPABASE_API_KEY}",
    "Content-Type": "application/json"
}

def get_existing_companies():
    url = f"{SUPABASE_API_URL}/rest/v1/{COMPANIES_TABLE}?select=id,name"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        return pd.DataFrame(res.json())
    else:
        print("❌ Failed to fetch existing companies", res.status_code, res.text)
        return pd.DataFrame()

def insert_company_if_new(company, existing_df):
    name = company[0].strip()
    if not (existing_df['name'].str.lower() == name.lower()).any():
        payload = {
            "id": str(uuid.uuid4()),
            "name": company[0],
            "tagline": company[1],
            "location": company[2],
            "domain": company[3],
        }
        url = f"{SUPABASE_API_URL}/rest/v1/{COMPANIES_TABLE}"
        print(payload)
        res = requests.post(url, headers=HEADERS, json=[payload])
        if res.status_code in [200, 201]:
            print(f"✅ Inserted new company: {name}")
            return payload["id"]
        else:
            print(f"❌ Failed to insert company {name}:", res.status_code, res.text)
            return None
    else:
        matched = existing_df[existing_df['name'].str.lower() == name.lower()]
        return matched.iloc[0]['id']

def insert_funding_record(company_id, deal):
    payload = {
        "id": str(uuid.uuid4()),
        "company_id": company_id,
        "date": deal[4],
        "series": deal[1],
        "deal_size": float(deal[2]) if deal[2] else None,
        "lead_investors": deal[3],
        "source": deal[5],
    }
    url = f"{SUPABASE_API_URL}/rest/v1/{FUNDINGS_TABLE}"
    res = requests.post(url, headers=HEADERS, json=[payload])
    if res.status_code in [200, 201]:
        print(f"✅ Inserted funding for company ID {company_id}")
    else:
        print(f"❌ Failed to insert funding for company {company_id}:", res.status_code, res.text)

def insert_deals(deals):
    existing_companies = get_existing_companies()
    for deal in deals:
        try:
            name, tagline, location, domain = deal[0], deal[6], deal[5], deal[7]
            company_tuple = [name, tagline, location, domain]
            company_id = insert_company_if_new(company_tuple, existing_companies)
            if company_id:
                insert_funding_record(company_id, deal)
        except Exception as e:
            print(f"⚠️ Skipping malformed deal: {deal} | Error: {e}")
example_deal = [[
    "SolarFlux",                  # Company Name
    "Series A",                   # Series
    "25",                         # Deal Size in millions (as a string to be converted)
    "CleanTech Ventures, SunEdge Capital",  # Lead Investors
    "2025-07-11",                # Date of Deal
    "San Diego, CA",             # Location
    "Thermal solar collector developer",    # Tagline
    "https://www.solarfluxenergy.com",      # Domain
    "https://techcrunch.com/solarflux-25m-series-a"  # Source
]]

insert_deals(example_deal)
