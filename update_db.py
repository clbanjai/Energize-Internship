from aiohttp import BasicAuth
import aiohttp
import asyncio
from affinity import fetch_list, in_energize_affinity
import pandas as pd
import ast
# import sys
# import os 
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import AFFINITY_API_KEY
from db_client import supabase, fetch_all

# print("Fetching companies")
# companies = pd.read_csv("companies.csv")
# print("Finished fetching")
semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent requests

def literal(string):
    if pd.isna(string):
        return None
    else:
        try:
            return ast.literal_eval(string)
        except Exception as e:
            return string

async def fetch_field_values(session, org_id):
    url = f"https://api.affinity.co/field-values?organization_id={org_id}"
    async with semaphore:
        for attempt in range(5):
            async with session.get(url, auth=BasicAuth('', AFFINITY_API_KEY)) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    wait = int(response.headers.get("Retry-After", 60))
                    print(f"[{org_id}] 429 Too Many Requests - retrying in {wait}s...")
                    await asyncio.sleep(wait)
                elif response.status >= 500:
                    print(f"[{org_id}] Server error {response.status} - retrying...")
                    await asyncio.sleep(60)
                else:
                    print(f"[{org_id}] Unrecoverable error {response.status}")
                    return None
        print(f"[{org_id}] Max retries reached - skipping.")
        return None


async def fetch_all_field_values(org_ids):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_field_values(session, oid) for oid in org_ids]
        return await asyncio.gather(*tasks)

 
field_mapping = {'Investment Stage': 3007023, 
                     'Description': 3007050,
                    'Year Founded': 3007049,
                    'Number of Employees': 3007043, 
                    'Location': 3007052, 
                    'Industry': 3007051, 
                    'Last Funding Date': 3007032, 
                    'Investors': 3007025, 
                    'Source of Introduction': 3007022, 
                    'Total Funding Amount (USD)': 3007029, 
                    'Last Funding Amount (USD)': 3007030, 
                    'LinkedIn URL': 3698262, 
                    'LinkedIn Headcount': 5188170, 
                    'Dealroom.co URL': 3007034, 
                    'Corporate Industries': 3007044, 
                    'Service Industries': 3007040, 
                    'Technologies': 3007039, 
                    'Income Streams': 3007042, 
                    'Business Models': 3007046, 
                    'Ownership Types': 3007041, 
                    'Total Tweets': 3007038, 
                    'Last Month Change in Twitter Followers': 3007036, 
                    'Last Month Twitter Favorites': 3007037, 
                    'Client Focus': 3007045, 
                    'Total Funding Amount (EUR)': 3007048, 
                    'Last Funding Amount (EUR)': 3007047, 'Last Month Twitter Followers': 3007035, 'Employee Departures: Last 3 Months (#)': 3051579, 'Employee Departures: Last 3 Months (%)': 3051578, 'Employee Departures: Last 3 Months (Leadership)': 3051581, 'Employee Hires: Last 3 Months (#)': 3051577, 'Employee Hires: Last 3 Months (%)': 3051576, 'Employee Hires: Last 3 Months (Leadership)': 3051580, 'Employees (Current)': 3051587, 'Employees: 1 Month Ago': 3051586, 'Employees: 3 Months Ago': 3051585, 'Employees: 6 Months Ago': 3051584, 'Employees: 12 Months Ago': 3051583, 'Employees: 24 Months Ago': 3051582, 'Employees: Growth MoM (%)': 3051575, 'Employees: Growth QoQ (%)': 3051574, 'Employees: Growth YoY (%)': 3051573, 'LinkedIn Profile (Founders/CEOs)': 3051572, 'Strategy': 4075354, 'Diverse Founder (Y/N)?': 3069421, 'ARR 2023 ($)': 3226858, 'Relevant Events': 3364216, 'ARR 2024': 4367478, 'Energize Relationship': 3026453, 'Margin': 3068948, 'ARR 2021 ($)': 3068961, 'ARR 2022 ($)': 3068970, 'Deep Dive': 3010026, 'Financial Impact': 4582456, 'Engagement Tier': 3713299, 'Engagement Impact': 4582457}

def extract_field_values(list_of_field_outputs,fields_to_extract= [
    "Location",
    "Employees (Current)",
    "Employees: Growth YoY (%)",
    "Investment Stage",
    "Last Funding Amount (USD)",
    "Investors",
    "LinkedIn Profile (Founders/CEOs)",
    "Industry",
    "Business Models",
    "Technologies",
    "Deep Dive"]):
    info = {i: None for i in fields_to_extract}
    reverse_mapping = {v: k for k, v in field_mapping.items() if k in fields_to_extract}

    for field_output in list_of_field_outputs: 
        field_id = field_output.get("field_id")
        if field_id in reverse_mapping:
            field_value = field_output.get("value")
            field_name = reverse_mapping[field_id]
            if field_value is not None:
                if field_name in info and info[field_name] is not None:
                    if not isinstance(info[field_name], list):
                        info[field_name] = [info[field_name]]
                    info[field_name].append(field_value)
                else:
                    info[field_name] = field_value

    return info


# Step 2: Loop over the DataFrame rows with the fetched results
def generate_updates(df, all_field_outputs, pipeline):
    print(f"this is pipeline info:\n it's an object of type {type(pipeline)} of length {len(pipeline)}")

    # Build the dictionary once
    field_output_dict = {
        entry[0]['entity_id']: entry
        for entry in all_field_outputs
        if entry and isinstance(entry, list) and len(entry) > 0
    }

    updates = []

    for row in df.itertuples():
        try:
            affinity_id = int(row.affinity_id)
        except ValueError:
            continue

        fields = field_output_dict.get(affinity_id)

        if not fields:
            continue

        new_values = extract_field_values(fields)

        current = [
            row.employees_current,
            row.employees_growth_yoy,
            row.investment_stage,
            row.last_funding_amount_usd,
            row.in_energize_affinity,
            row.industry,
            row.business_models,
            row.technologies,
            row.deep_dive_tag
        ]
        current = [literal(i) for i in current]

        new = [
            new_values["Employees (Current)"],
            new_values["Employees: Growth YoY (%)"],
            new_values["Investment Stage"],
            new_values["Last Funding Amount (USD)"],
            in_energize_affinity(row.affinity_id, pipeline),
            new_values["Industry"],
            new_values["Business Models"],
            new_values["Technologies"],
            new_values["Deep Dive"]
        ]

        if current != new:
            print(f"Updating {row.name} ({row.affinity_id})\nFrom: {current}\nTo:   {new}")
            updates.append({
                "company_uuid": row.company_uuid,
                "employees_current": new[0],
                "employees_growth_yoy": new[1],
                "investment_stage": new[2],
                "last_funding_amount_usd": new[3],
                "in_energize_affinity": new[4],
                "industry": new[5],
                "business_models": new[6],
                "technologies": new[7],
                "deep_dive_tag":new[8]
            })

    return updates


def update_supabase(updates):
    for update in updates:
        try:
            company_uuid = update["company_uuid"]
            update_fields = {k: v for k, v in update.items() if k != "company_uuid"}
            supabase.table("companies").update(update_fields).eq("company_uuid", company_uuid).execute()
        except Exception as e:
            print(f"Updating {company_uuid} with: {update_fields}")
            raise e

# ---- MAIN WORKFLOW ----
def main():
    print("Fetching data from Supabase...")

    all_companies = fetch_all()
    df = all_companies[all_companies["affinity_id"]!="Not in Affinity"]
    df = df.drop(columns=["embedding"], errors="ignore")
    org_ids = df["affinity_id"].tolist()
    print("Fetching data from Affinity...")
    import time

    print("bulk fetching")
    start_time = time.time()
    all_field_outputs = asyncio.run(fetch_all_field_values(org_ids))

    end_time = time.time()
    print(f"Time taken: {end_time - start_time:.2f} seconds")

    print("finished fetching from affinity")
    print("Comparing and preparing updates...")
    pipeline = set(fetch_list()["entity_id"].to_list())
    updates = generate_updates(df, all_field_outputs,pipeline)

    print(f"Pushing {len(updates)} updates to Supabase...")
    print(updates)
    update_supabase(updates)
    print(f"✅ Done. updated a total of {len(updates)} companies")

if __name__ == '__main__':
    main()

# print(main())
# print((main()))
# print("fetching companies")
# companies  = fetch_all()
# print("done fetching")
# df = companies[companies["affinity_id"]!="Not in Affinity"]
# print("starting to extract field_values")

# all_field_outputs = asyncio.run(fetch_all_field_values(df["affinity_id"].to_list()))

# import json 
# print("dumping into json")
# with open("field_outs.json",mode="w") as f:
#     json.dump(all_field_outputs,f,indent=4)