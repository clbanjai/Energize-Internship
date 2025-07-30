from aiohttp import BasicAuth
import aiohttp
import asyncio
from config import AFFINITY_API_KEY
from db_client import fetch_all
import pandas as pd
print("Fetching companies")
companies = pd.read_csv("companies.csv")
print("Finished fetching")
semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent requests

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


async def fetch_all(org_ids):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_field_values(session, oid) for oid in org_ids]
        return await asyncio.gather(*tasks)

org_ids = ['283677000',
 '268252178',
 '224626100',
 '1555826',
 '290584264',
 '114272919',
 '263185041',
 '297884313',
 '287971148',
 '224686696',
 '286194309',
 '291928705',
 '222181321',
 '145558012',
 '278518352',
 '299967428',
 '1607977',
 '162592950',
 '287621926',
 '125394565']
 
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

def extract_field_values(list_of_field_outputs,fields_to_extract=[
    "Employees (Current)",
    "Employees: Growth YoY (%)",
    "Investment Stage",
    "Last Funding Amount (USD)",
    "Investors",
    "LinkedIn Profile (Founders/CEOs)",
    "Location",
    "Investors",
    "Description"
]):
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


df = companies[companies["affinity_id"] != "Not in Affinity"]
df = df.drop("embedding",axis=1)
df.to_csv("befre.csv",index=False)
print("saved original into csv")
# Step 1: Fetch all field values in bulk
import time

print("bulk fetching")
start_time = time.time()

all_field_outputs = asyncio.run(fetch_all(df["affinity_id"].tolist()))

end_time = time.time()
print("finished fetching from affinity")
print(f"Time taken: {end_time - start_time:.2f} seconds")

# Step 2: Loop over the DataFrame rows with the fetched results
for row, fields in zip(df.itertuples(), all_field_outputs):
    if fields is None:
        print(f"[{row.affinity_id}] Skipped due to fetch failure.")
        continue
    current = [
        row.employees_current,
        row.employees_growth_yoy,
        row.investment_stage,
        row.last_funding_amount_usd
    ]

    # Parse new field values
    new_values = extract_field_values(fields)
    new = [
        new_values["Employees (Current)"],
        new_values["Employees: Growth YoY (%)"],
        new_values["Investment Stage"],
        new_values["Last Funding Amount (USD)"]
    ]

    if current != new:
        df.loc[row.Index, [
            "employees_current",
            "employees_growth_yoy",
            "investment_stage",
            "last_funding_amount_usd"
        ]] = new

print("saving to csv")
df.to_csv("after.csv",index=False)

