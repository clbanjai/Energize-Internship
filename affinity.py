import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from difflib import SequenceMatcher
import time
import ast
from config import AFFINITY_API_KEY
import json
from embeddings import generate_embedding
from db_client import cosine_similarity
import re
import time
import requests
from requests.auth import HTTPBasicAuth

# Mapping of Affinity field names to internal names in supabse
AFFINITY_FIELD_NAME_MAP = {
    "Description": "description",
    "LinkedIn Profile (Founders/CEOs)": "linkedin_profile",
    "Employees (Current)": "employees_current",
    "Employees: Growth YoY (%)": "employees_growth_yoy",
    "Investment Stage": "investment_stage",
    "Last Funding Amount (USD)": "last_funding_amount_usd",
    "Industry": "industry",
    "Business Models": "business_models",
    "Technologies": "technologies",
    "Location": "location",
    "Investors": "investors",
    "Deep Dive": "deep_dive_tag",
    "Pod":"pod"
}

# pod name map to match energize employees with their affinity ids to save computational time
with open("data/pod_name_map.json","r") as f:
    pod_name_map = json.load(f)

#common field values of interest
fields_to_extract = [
    "Location",
    "Employees (Current)",
    "Employees: Growth YoY (%)",
    "Investment Stage",
    "Last Funding Amount (USD)",
    "Investors",
    "LinkedIn Profile (Founders/CEOs)",
    "Industry",
    "Business Models",
    "Technologies"]


def name_similarity(name1, name2):
    """
    Returns a similarity score between 0 and 1 (higher means more similar).
    """
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()


def location_check(location,field_values):
    """ Check if the location in field_values matches the provided location."""
    if field_values and "Location" in field_values and field_values["Location"] and location:
        if in_US(location):
            city, state = field_values["Location"]["city"], field_values["Location"]["state"]
            city = city.lower() if city else None
            state = state.lower() if state else None # to standerdize and avoid issues with capitalization
            if city and city in location:
                return True 
            elif state and state in location:
                return True
        else:
            city, country = field_values["Location"]["city"], field_values["Location"]["country"]
            city = city.lower() if city else None# to standerdize and avoid issues with capitalization
            country = country.lower() if country else None
            if country and country in location or country and country in location:  
                return True
    return False


def patient_get(url, auth = HTTPBasicAuth("",AFFINITY_API_KEY), max_retries=5, base_wait=61, backoff_factor=1.0):
    """
    Retry GET request on 429s or temporary server errors, with exponential backoff.
    """
    for attempt in range(max_retries):
        response = requests.get(url, auth=auth)

        # Success!
        if response.status_code == 200:
            return response

        #  Rate limited — honor Retry-After if available
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                wait = int(retry_after)
            else:
                wait = base_wait 
            print(f" 429 Too Many Requests - retrying in {wait:.1f}s...")
            time.sleep(wait)

        # 🔁 Retry on 5xx errors too
        elif response.status_code >= 500:
            wait = base_wait 
            print(f"{response.status_code} Server Error - retrying in {wait:.1f}s...")
            time.sleep(wait)

        else:
            print(f" Unrecoverable error: {response.status_code} - {response.text}")
            return response

    print("Max retries reached - giving up.")
    return None





def fetch_list(id=153336):
    """Fetches entries from a specific Affinity list by ID. Default set to Pipeline"""
    url = f'https://api.affinity.co/lists/{id}/list-entries'
    response = requests.get(url, auth=HTTPBasicAuth(" ",AFFINITY_API_KEY))
    if response.status_code == 200:
        data = response.json()
        return pd.DataFrame(data)
    
def in_energize_affinity(id,pipeline):
    "Checks if a company is in the energize affinity pipeline"
    if not isinstance(id,int):
        id = int(id)
    if id in pipeline:
        return True
    else:
        return False

# loading us cities and states data for later locational check
us_data = pd.read_csv("data/uscities.csv")
cities = set(us_data["city"].str.lower().values)
states = set(us_data["state_id"].str.lower().values)
def in_US(location):
    larger_location = location.split(", ")
    if len(larger_location) > 1:
        city, state = larger_location[0].lower(), larger_location[1].lower()
        return city in cities and state in states
    else:
        return larger_location[0].lower() in states or larger_location[0].lower() in cities
def get_person_info(id):
    """Fetches person information from Affinity by ID."""
    url = f"https://api.affinity.co/persons/{id}?with_current_organizations=true"
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.get(url, headers=headers, auth=HTTPBasicAuth("", AFFINITY_API_KEY))
    if response.status_code==200:
        data = response.json()
        return data

def extract_field_values(list_of_field_outputs,field_mapping,pod_name_map,fields_to_extract=list(AFFINITY_FIELD_NAME_MAP.keys()), extra_fields=None):
    """Given a list of raw field values, extracts and normalizes them based on the provided field mapping."""
    if extra_fields:
        fields_to_extract+=extra_fields
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
                    if field_name == "Pod":
                        if str(field_value) in pod_name_map:
                            field_value = pod_name_map[str(field_value)]
                        else:
                            person_info = get_person_info(field_value)
                            field_value = f"{person_info['first_name']} {person_info['last_name']}"
                    info[field_name].append(field_value)
                else:
                    if field_name=="Pod":
                        if str(field_value) in pod_name_map:
                            field_value = pod_name_map[str(field_value)]
                        else:
                            person_info = get_person_info(field_value)
                            field_value = f"{person_info['first_name']} {person_info['last_name']}"
                    info[field_name] = field_value

    return info

def get_field_value_by_id(company_id, pod_name_map = pod_name_map,extra_fields=None):
    """Performs the initial API call to fetch field values for a company by its ID."""
    field_mapping = {'Investment Stage': 3007023, 
                     'Description': 3007050,
                    'Year Founded': 3007049,
                    "Pod":3009283,
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

    info = {i: None for i in fields_to_extract}
    url = f"https://api.affinity.co/field-values?organization_id={company_id}"
    response = patient_get(url)
    if response is None:
        return None
    if response.status_code != 200:
        raise Exception(f"Failed to fetch field values: {response.status_code}, {response.text}")

    list_of_field_outputs = response.json()
    # return list_of_field_outputs
    if list_of_field_outputs:
        # Invert the mapping to get id → name, but only for requested fields
        info = extract_field_values(list_of_field_outputs,field_mapping,pod_name_map,extra_fields=extra_fields)

    return info


def get_company_by_name(company_name, domain=None,location=None,investors=None,description=None,strict = True):
    """Fetches a company from Affinity by name, domain, location, and investors. Performs a fuzzy match on the name and checks for domain, location, and investors."""
    url = f"https://api.affinity.co/organizations?term={company_name}"
    company_name = company_name.strip().lower()
    response = patient_get(url)
    if response is None:
        return (None, None)
    if description:
        description_embedding = generate_embedding(description.strip().lower())
        desciption_hash = {}
    if response.status_code == 200:
        json = response.json()
        if json and json["organizations"]:
            data = json["organizations"]
            if pd.notna(domain) and domain:
                for org in data:
                    if name_similarity(org["name"], company_name) > 0.6:
                        org_domains = org["domains"]
                        org_id = org["id"]
                        if org_domains:
                            for org_dom in org_domains:
                                if org_dom in domain:
                                    if pd.notna(location) and location:
                                        location = location.lower()
                                    field_values = get_field_value_by_id(org_id)
                                    if strict and location_check(location,field_values):
                                        return org, field_values
                                    else: 
                                        return org, field_values
            if pd.notna(location) and location:# if we have the locatoin then we loop through the outputs until there's a match
                location = location.lower()
                for org in data:
                    name_score = name_similarity(org["name"].lower(), company_name)
                    if name_score > 0.6:
                        org_id = org["id"]
                        field_values = get_field_value_by_id(org_id)
                        if field_values and "Location" in field_values and field_values["Location"]:
                            if in_US(location):
                                city, state = field_values["Location"]["city"], field_values["Location"]["state"]
                                city = city.lower() if city else None
                                state = state.lower() if state else None # to standerdize and avoid issues with capitalization
                                if city and city in location:
                                    return org, field_values 
                                elif state and state in location:
                                    return org, field_values
                            else:
                                city, country = field_values["Location"]["city"], field_values["Location"]["country"]
                                city = city.lower() if city else None# to standerdize and avoid issues with capitalization
                                country = country.lower() if country else None
                                if country and country in location or city and city in location:  
                                    return org, field_values
            if investors:
                investors = [inv.lower().strip() for inv in investors]  # Normalize investor names to lowercase
                for org in data:
                    name_score = name_similarity(org["name"].lower(), company_name)
                    if name_score>0.7:
                        org_id = org["id"]
                        field_values = get_field_value_by_id(org_id)
                        if field_values and "Investors" in field_values and field_values["Investors"]:
                            org_investors = field_values["Investors"]
                            for inv in org_investors:
                                inv = inv.lower().strip()  # Normalize investor names to lowercase
                                if inv in investors:
                                    return org, field_values
            if description and not strict:
                description = description.lower().strip()
                for org in data:
                    if org["name"].lower().strip()==company_name:

                        org_id = org["id"]
                        field_values = get_field_value_by_id(org_id)
                        if field_values and "Description" in field_values and field_values["Description"]:
                            org_description = field_values["Description"].lower().strip()
                            org_description_embedding = generate_embedding(org_description)
                            desciption_hash[org_id] = cosine_similarity(description_embedding, org_description_embedding)
                sorted_desc = sorted(desciption_hash.items(), key=lambda x: x[1], reverse=True)
                if sorted_desc:
                    best_match_id = sorted_desc[0][0]
                    for org in data:
                        if org["id"] == best_match_id:
                            field_values = get_field_value_by_id(best_match_id)
                            return org, field_values
            if not strict:
                for org in data:
                    if org["name"].lower().strip()==company_name:
                        org_id = org["id"]
                        field_values = get_field_value_by_id(org_id)
                        return org, field_values
            return (None, None)
        else:
            return (None, None)
    else:
        return f"Error: {response.status_code}, {response.text}"


def normalize_key(key):
    return AFFINITY_FIELD_NAME_MAP.get(key, re.sub(r"[^\w\s]", "", key.lower()).replace(" ", "_"))

fields_to_extract = [
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
    "Deep Dive",
    "Pod"
]
fields_to_extract = [normalize_key(f) for f in fields_to_extract]

def affinity_enrich(row,pipeline):
    """Normalizing and enriching a row with Affinity data."""
    in_energize = False
    affinity_ID = None
    name = row.name
    location = row.location
    domain = row.domain
    uuid = row.Index
    tagline = row.tagline
    investors = row.investors

    enriched_fields = {
        "company_uuid": uuid,
        "name": name,
        "tagline": tagline,
        "domain": domain,
        "location": location,
        "investors": investors
    }

    # Ensure all possible columns are initialized to None
    for k in fields_to_extract:
        if k not in enriched_fields:
            enriched_fields[k] = None

    enriched_fields["in_energize_affinity"] = False
    enriched_fields["affinity_id"] = "Not in Affinity"

    try:
        org, field_values = get_company_by_name(name, domain=domain, location=location, investors=investors)
        if org:
            affinity_ID = org["id"]
            enriched_fields["name"] = org.get("name", name)
            enriched_fields["domain"] = org["domain"] if org.get("domain") else domain

            for k, v in field_values.items():
                k_norm = normalize_key(k)
                if k_norm == "location" and isinstance(v, dict):
                    if v.get("country", "").lower() in ["united states", "united states of america", "us", "usa"]:
                        enriched_fields["location"] = f"{v.get('city')}, {v.get('state')}"
                    else:
                        enriched_fields["location"] = f"{v.get('city')}, {v.get('country')}"
                elif k_norm == "description" and v is not None:
                    enriched_fields["tagline"] = v
                elif v is not None:
                    enriched_fields[k_norm] = v

            if in_energize_affinity(affinity_ID,pipeline):
                in_energize = True

        enriched_fields["in_energize_affinity"] = in_energize
        enriched_fields["affinity_id"] = affinity_ID if affinity_ID else "Not in Affinity"
        return enriched_fields

    except Exception as e:
        print(f"❌ Error enriching {name}: {e}")
        print("🔍 Fallback result:", get_company_by_name(name, domain, location, investors))
        return enriched_fields

def array_to_tuples(array):
    """
    Convert a 2D array (list of lists) into a list of tuples.

    Args:
        array (list of list of str): The input 2D array.

    Returns:
        list of tuples: Each tuple corresponds to a row in the input array.
    """
    return [tuple(row) for row in array]

def array_columns(val):
    if isinstance(val,list):
        return val
    if isinstance(val,str):
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed,list):
                return [str(item).strip() for item in parsed]
            return [parsed]
        except Exception:
            return [v.strip() for v in val.split(",") if v.strip()]
    return []
def enrich_df(companies_df):
    result = []
    pipeline = set(fetch_list()["entity_id"].to_list())
    for row in companies_df.itertuples():
        result.append(affinity_enrich(row,pipeline))
    df = pd.DataFrame(result)
    temp = df.copy()
    columns_to_fix = ["linkedin_profile","industry","business_models","technologies","deep_dive_tag","pod"]
    for i in columns_to_fix:
        df[i] = temp[i].apply(array_columns)
    return df


import asyncio

async def async_affinity_enrich(row, pipeline):
    return await asyncio.to_thread(affinity_enrich, row, pipeline)

async def enrich_df_async(companies_df):
    result = []
    pipeline = set(fetch_list()["entity_id"].to_list())

    tasks = [
        async_affinity_enrich(row, pipeline)
        for row in companies_df.itertuples()
    ]
    enriched = await asyncio.gather(*tasks)

    df = pd.DataFrame(enriched)
    temp = df.copy()
    columns_to_fix = ["linkedin_profile", "industry", "business_models", "technologies", "deep_dive_tag", "pod"]
    for i in columns_to_fix:
        df[i] = temp[i].apply(array_columns)
    return df

if __name__=="__main__":
    print(get_company_by_name("archive",domain="archivesale.com",location="San Francisco, CA",investors=None))
    
