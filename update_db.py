from aiohttp import BasicAuth
import aiohttp
import asyncio
from affinity import fetch_list, in_energize_affinity, extract_field_values, array_columns
import pandas as pd
import ast
# import sys
# import os 
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config import AFFINITY_API_KEY
from db_client import supabase, fetch_all
import json
with open("private_data/field_mapping.json","r") as f:
    field_mapping = json.load(f)
# print("Fetching companies")
# companies = pd.read_csv("companies.csv")
# print("Finished fetching")
semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent requests

def literal(input):
    if isinstance(input,list):
        return input
    if pd.isna(input):
        return None
    else:
        try:
            return ast.literal_eval(input)
        except Exception as e:
            return input

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


# Step 2: Loop over the DataFrame rows with the fetched results
def generate_updates(df, all_field_outputs, pipeline,field_mapping,pod_name_map):

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

        new_values = extract_field_values(fields,field_mapping,pod_name_map)
        current = [
            row.employees_current,
            row.employees_growth_yoy,
            row.investment_stage,
            row.last_funding_amount_usd,
            row.in_energize_affinity,
            row.industry,
            row.business_models,
            row.technologies,
            row.deep_dive_tag,
            row.pod
        ]
        current = [literal(i) for i in current]

        new = [
            new_values["Employees (Current)"],
            new_values["Employees: Growth YoY (%)"],
            new_values["Investment Stage"],
            new_values["Last Funding Amount (USD)"],
            in_energize_affinity(row.affinity_id, pipeline),
            array_columns(new_values["Industry"]),
            array_columns(new_values["Business Models"]),
            array_columns(new_values["Technologies"]),
            array_columns(new_values["Deep Dive"]),
            array_columns(new_values["Pod"])
        ]

        if current != new:
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
                "deep_dive_tag":new[8],
                "pod":new[9]
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
    import json
    with open("private_data/pod_name_map.json","r") as f:
        pod_name_map = json.load(f)
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

    updates = generate_updates(df, all_field_outputs,pipeline,field_mapping,pod_name_map)

    print(f"Pushing {len(updates)} updates to Supabase...")
    update_supabase(updates)
    print(f"✅ Done. updated a total of {len(updates)} companies")

if __name__ == '__main__':
    main()
    