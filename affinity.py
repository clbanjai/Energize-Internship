import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from config import AFFINITY_API_KEY
from difflib import SequenceMatcher
import time

fields_to_extract = [
    "Location",
    "Employees (Current)",
    "Employees: Growth YoY (%)",
    "Investment Stage",
    "Last Funding Amount (USD)",
    "Investors",
    "LinkedIn Profile (Founders/CEOs)"]


def name_similarity(name1, name2):
    """
    Returns a similarity score between 0 and 1 (higher means more similar).
    """
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

def safe_get(url, auth, max_retries=5, backoff_factor=2.0):
    for attempt in range(max_retries):
        response = requests.get(url, auth=auth)
        if response.status_code == 200:
            return response
        elif response.status_code == 429:
            # Check retry-after header
            retry_after = int(response.headers.get("X-Ratelimit-Limit-User-Reset", 5))
            wait_time = retry_after * (backoff_factor ** attempt)
            print(f"🛑 429 Too Many Requests – Retrying in {wait_time:.1f} seconds...")
            time.sleep(wait_time)
        else:
            print(f"❌ Request failed with {response.status_code}: {response.text}")
            break
    return None



all_orgs = pd.read_csv("private_data/energize_affinity_ids.csv")
id_set = set(all_orgs["id"].values)

def in_energize_affinity(id):
    return id in id_set

us_data = pd.read_csv("private_data/uscities.csv")
cities = set(us_data["city"].str.lower().values)
states = set(us_data["state_id"].str.lower().values)
def in_US(location):
    larger_location = location.split(", ")
    if len(larger_location) > 1:
        city, state = larger_location[0].lower(), larger_location[1].lower()
        return city in cities and state in states
    else:
        return larger_location[0].lower() in states or larger_location[0].lower() in cities
    

def get_field_value_by_id(company_id, fields_to_extract = [
    "Employees (Current)",
    "Employees: Growth YoY (%)",
    "Investment Stage",
    "Last Funding Amount (USD)",
    "Investors",
    "LinkedIn Profile (Founders/CEOs)",
    "Location",
    "Investors"
]):
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

    info = {i: None for i in fields_to_extract}
    url = f"https://api.affinity.co/field-values?organization_id={company_id}"
    response = safe_get(url, HTTPBasicAuth("", AFFINITY_API_KEY))
    if response is None:
        return None
    if response.status_code != 200:
        raise Exception(f"Failed to fetch field values: {response.status_code}, {response.text}")

    list_of_field_outputs = response.json()
    if list_of_field_outputs:
        # Invert the mapping to get id → name, but only for requested fields
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

def get_company_info_by_id(company_id):
    response = requests.get(
        f"https://api.affinity.co/organizations/{company_id}",
        auth=HTTPBasicAuth('', AFFINITY_API_KEY)
    )   
    if response.status_code == 200:
        return response.json()  # Return the organization details
    else:
        print("Error:", response.status_code, response.text)
        return None

def get_company_by_name(company_name, domain=None,location=None,investors=None):


    url = f"https://api.affinity.co/organizations?term={company_name}"

    response = response = safe_get(url, HTTPBasicAuth("", AFFINITY_API_KEY))
    if response is None:
        return (None, None)

    if response.status_code == 200:
        json = response.json()
        if json and json["organizations"]:
            data = json["organizations"]
            if len(data)==1:
                org = data[0]
                field_values = get_field_value_by_id(org["id"])
                return org, field_values
            if pd.notna(domain) and domain:
                for org in data:
                    if name_similarity(org["name"], company_name) > 0.6:
                        org_domains = org["domains"]
                        org_id = org["id"]
                        if org_domains:
                            for org_dom in org_domains:
                                if org_dom in domain:
                                    return org, get_field_value_by_id(org_id)
            if pd.notna(location) and location:# if we have the locatoin then we loop through the outputs until there's a match
                location = location.lower()
                for org in data:
                    name_score = name_similarity(org["name"].lower(), company_name)
                    if name_score > 0.6:
                        org_id = org["id"]
                        field_values = get_field_value_by_id(org_id)
                        if field_values and field_values["Location"]:
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
                                if country and country in location or country and country in location:  
                                    return org, field_values
            if investors:
                investors = [inv.lower().strip() for inv in investors]  # Normalize investor names to lowercase
                for org in data:
                    org_id = org["id"]
                    field_values = get_field_value_by_id(org_id)
                    if field_values and field_values["Investors"]:
                        org_investors = field_values["Investors"]
                        for inv in org_investors:
                            inv = inv.lower().strip()  # Normalize investor names to lowercase
                            if inv in investors:
                                return org, field_values
            return (None, None)
        else:
            return (None, None)
    else:
        return f"Error: {response.status_code}, {response.text}"

def affinity_enrich(row):
    in_energize = False
    affinity_ID = None
    name, location, domain, uuid, tagline, investors = row
    enriched_fields = {'id': uuid, 'name': name,"tagline": tagline, 'domain': domain, "Location": location, "Investors": investors}

    for k in fields_to_extract:
        enriched_fields[k] = None
    enriched_fields["In Energize Affinity"] = False
    enriched_fields["Affinty ID"] = "Not in Affinity"
    # return enriched_fields
    try:
        org, field_values = get_company_by_name(name, domain=domain, location=location,investors=investors)
        # return org, field_values
        if org:
            affinity_ID = org["id"]
            # field_values = get_field_value_by_id(id)
            enriched_fields['name'] =  org["name"]
            enriched_fields['domain'] =  org["domain"]

            for k, v in field_values.items():
                if k == "Location":
                    if v:
                        if v["country"].lower() in ["united states of america", "united states", "us", "usa"]:
                            enriched_fields[k] = f"{v['city']}, {v['state']}"
                        else:
                            enriched_fields[k] = f"{v['city']}, {v['country']}"
                    else:
                        enriched_fields[k] = location
                else:
                    enriched_fields[k] = v

            if in_energize_affinity(affinity_ID):
                in_energize = True
        enriched_fields["In Energize Affinity"] = in_energize
        enriched_fields["Affinty ID"] = affinity_ID if affinity_ID else "Not in Affinity"
        return enriched_fields
    except Exception as e:
        print(f"Error enriching {name}: {e}")
        print(f"The output of getting company name is : {get_company_by_name(name, domain=domain, location=location,investors=investors)}")
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

# companies = array_to_tuples(pd.read_csv("../companies.csv")[["name","location","domain","id","tagline"]].values)

def enriched_df(companies_df):

    result = []
    for row in companies_df:
        result.append(affinity_enrich(tuple(row)))
    return pd.DataFrame(result)

# row = ("Archive", None, None,None,"tagline",["Lightspeed Venture Partners", "Bain Capital Ventures", "Firstmark"])
# print(affinity_enrich(row))
print(get_company_by_name("GridCare", "gridcare.ai", "Redwood City, CA"))
# # print(name_similarity("London, UK", "London, United Kingdom"))

# investors = ["VoLo Earth Ventures", "Microsoft Climate Innovation Fund", "Credit Suisse", "Builders Vision", "New York State Ventures", "Unreasonable Collective", "American Family Insurance Institute", "AccelR8", "The Goldman Sachs Urban Investment Group"]
# print(get_company_by_name("blocpower",investors=investors))
