import asyncio
import aiohttp
from requests.auth import _basic_auth_str
from config import AFFINITY_API_KEY
from affinity import get_company_by_name, get_person_info
from datetime import datetime
from config import OPENAI_API_KEY
import ast
from parser_new_cleaned import client
BASE_URL = "https://api.affinity.co"

# Required headers for aiohttp Basic Auth
HEADERS = {
    "Authorization": _basic_auth_str("", AFFINITY_API_KEY)
}

import requests
from requests.auth import HTTPBasicAuth
BASE_URL = "https://api.affinity.co"


def create_prompt(input_text):
    return f""" You are an expert in structuring different types of input data into a structured format.
    Your task is to given the input text, extract the relevant information and return it in a structured format. python list of lists
    You should extract the following information:
    - company name
    - company domain
    - description of the company
    your output should be a list of lists and nothing else, where each list contains the company name and domain.
    [["company_name", "domain","description"], ["company_name", "domain","description"]]
    Make sure to handle cases where the input text may not contain all the required information.
    Make sure to not include any additional information or explanations in your output. Don't include '''python ''' in your output.
    If the input for either does not exist, return None for that field.
    Input: {input_text}"""

def classify_industry(text):
    prompt = create_prompt(text)

    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # Model specification
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    result = completion.choices[0].message.content
    try:
        result = ast.literal_eval(result)
    except Exception:
        result = "["+result+"]"
        result = ast.literal_eval(result)

    return result


def get_linkedin_url(person_id):
    auth = HTTPBasicAuth("", AFFINITY_API_KEY)
    resp = requests.get(f"{BASE_URL}/field-values?person_id={person_id}", auth=auth)

    if resp.status_code != 200:
        raise Exception(f"Error fetching field values: {resp.text}")
    
    for field in resp.json():
        if field.get("field_id") == 3007058:  # Replace 337 with actual field ID for LinkedIn
            return field.get("value")
    
    return None

import asyncio

async def get_company_by_name_async(*args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: get_company_by_name(*args, **kwargs))


async def fetch_json(session, url):
    async with session.get(url, headers=HEADERS) as response:
        if response.status != 200:
            return None
        return await response.json()

async def fetch_relationship_strengths(session, person_id):
    url = f"{BASE_URL}/relationships-strengths?external_id={person_id}"
    data = await fetch_json(session, url)
    if not data:
        return None
    max_entry = max(data, key=lambda s: s["strength"])
    return {
        "external_person_id": person_id,
        "internal_person_id": max_entry["internal_id"],
        "strength": max_entry["strength"]
    }

async def fetch_person_detail(session, person_id):
    url = f"{BASE_URL}/persons/{person_id}"
    return await fetch_json(session, url)

async def get_top_5_contacts_for_org(org_id):
    """
    Returns top 5 people who currently work at the org, based on relationship strength with internal users.
    Each result includes LinkedIn and email, and only includes external people whose current org matches org_id.
    """
    async with aiohttp.ClientSession() as session:
        # Step 1: Fetch org with interaction metadata
        org_url = f"{BASE_URL}/organizations/{org_id}?with_interaction_dates=true&with_interaction_persons=true"
        org_data = await fetch_json(session, org_url)
        person_ids = org_data.get("person_ids", []) if org_data else []
        if not person_ids:
            return [], None

        # Step 2: Fetch relationship strengths in parallel
        strength_tasks = [fetch_relationship_strengths(session, pid) for pid in person_ids]
        raw_strengths = await asyncio.gather(*strength_tasks)
        top_candidates = [s for s in raw_strengths if s]

        if not top_candidates:
            return [], None

        # Step 3: Sort by strength
        top_candidates.sort(key=lambda x: x["strength"], reverse=True)

        # Step 4: Build results with org_id filter and limit to 5
        results = []
        for candidate in top_candidates:
            if len(results) >= 5:
                break

            external_id = candidate["external_person_id"]
            internal_id = candidate["internal_person_id"]

            external_url = f"{BASE_URL}/persons/{external_id}?with_current_organizations=true"
            internal_url = f"{BASE_URL}/persons/{internal_id}"

            ext_resp, int_resp = await asyncio.gather(
                fetch_json(session, external_url),
                fetch_json(session, internal_url)
            )

            if not ext_resp or not int_resp:
                continue

            # Check if current org matches input org_id
            if org_id not in ext_resp.get("current_organization_ids", []):
                continue

            linkedin_url = get_linkedin_url(ext_resp["id"])  # your existing function

            results.append({
                "external_name": f"{ext_resp.get('first_name', '')} {ext_resp.get('last_name', '')}".strip(),
                "external_email": ext_resp.get("primary_email"),
                "external_linkedin": linkedin_url,
                "internal_name": f"{int_resp.get('first_name', '')} {int_resp.get('last_name', '')}".strip(),
                "internal_email": int_resp.get("primary_email"),
                "strength": candidate["strength"]
            })

        return results, org_data.get("interactions", {}).get("last_interaction")
    
import asyncio
import time
from datetime import datetime

async def process_company(session, company):
    name, domain, description = company

    org, _ = await get_company_by_name_async(
        company_name=name, domain=domain, description=description, strict=False
    )
    if not org:
        return [{
                "Company Name": name, 
                "Company Domain": domain, 
                "External Contact Name": "No Match Found In Affinity For This Company",
                "External Contact Email": "No Match Found In Affinity For This Company",
                "External LinkedIn": "No Match Found In Affinity For This Company",
                "Internal Contact Name": "No Match Found In Affinity For This Company",
                "Internal Contact Email": "No Match Found In Affinity For This Company",
                "Relationship Strength": "No Match Found In Affinity For This Company",
                "Last Contact Name": "No Match Found In Affinity For This Company",
                "Last Contact Date": "No Match Found In Affinity For This Company"
            }]


    org_id = org["id"]
    domain = org.get("domain", "")
    try:
        results, last_interaction = await get_top_5_contacts_for_org(org_id)
    except Exception as e:
        return []

    output_rows = []
    last_person_name = ""
    last_contact_date = ""

    if last_interaction and last_interaction.get("person_ids"):
        loop = asyncio.get_event_loop()
        last_person = await loop.run_in_executor(None, get_person_info, last_interaction["person_ids"][0])
        last_person_name = f"{last_person.get('first_name', '')} {last_person.get('last_name', '')}"
        last_contact_date = datetime.fromisoformat(last_interaction["date"]).date()

    if results:
        for r in results:
            output_rows.append({
                "Company Name": name,
                "Company Domain": domain,
                "External Contact Name": r["external_name"],
                "External Contact Email": r["external_email"],
                "External LinkedIn": r["external_linkedin"],
                "Internal Contact Name": r["internal_name"],
                "Internal Contact Email": r["internal_email"],
                "Relationship Strength": r["strength"],
                "Last Contact Name": last_person_name,
                "Last Contact Date": last_contact_date
            })
    else:
        output_rows.append({
            "Company Name": name,
            "Company Domain": domain,
            "External Contact Name": "",
            "External Contact Email": "",
            "External LinkedIn": "",
            "Internal Contact Name": "",
            "Internal Contact Email": "",
            "Relationship Strength": "",
            "Last Contact Name": last_person_name,
            "Last Contact Date": last_contact_date or "No interaction found"
        })

    return output_rows


import pandas as pd

async def process_companies_parallel(input_text, output_csv_path="output.csv"):
    companies = classify_industry(input_text)
    start = time.time()

    all_rows = []

    async with asyncio.Semaphore(10):  # optional concurrency control
        tasks = [process_company(None, company) for company in companies]
        results = await asyncio.gather(*tasks)

    # Flatten results and convert to DataFrame
    for company_result in results:
        all_rows.extend(company_result)
    df = pd.DataFrame(all_rows).sort_values(by=["Company Name"])
    df.to_csv(output_csv_path, index=False)

    end = time.time()
    print(f"\nSaved results to {output_csv_path}")
    print(f"Time taken: {end - start:.2f} seconds")

if __name__ == "__main__":
    with open("input.txt", "r") as f:
        input_text = f.read().strip()
    asyncio.run(process_companies_parallel(input_text))

