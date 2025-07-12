import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from config import AFFINITY_API_KEY

fields_to_extract = [
    "Location"
    "Employees (Current)",
    "Employees: Growth YoY (%)",
    "Investment Stage",
    "Last Funding Amount (USD)",
    "Investors",
    "LinkedIn Profile (Founders/CEOs)",
]


all_orgs = pd.read_csv("private_data/energize_affinity_ids.csv")
id_set = set(all_orgs["id"].values)

def in_energize_affinity(id):
    return id in id_set

def in_US(location):
    larger_location = location.split(", ")[-1]
    if len(larger_location)==2:
        return True
    else:
        return False


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
    response = requests.get(
        f"https://api.affinity.co/field-values?organization_id={company_id}",
        auth=HTTPBasicAuth("", AFFINITY_API_KEY)
    )

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

def get_company_by_name(company_name, domain=None,location=None):


    url = f"https://api.affinity.co/organizations?term={company_name}"

    response = requests.get(
        url,
        auth=HTTPBasicAuth('', AFFINITY_API_KEY)  
        )

    if response.status_code == 200:
        json = response.json()
        if json and json["organizations"]:
            data = json["organizations"]
            # return data
            if len(data)==1:
                return data[0]
            if not pd.isna(domain):
                for org in data:
                    org_id = org["id"]
                    field_values = get_company_info_by_id(org_id)
                    # return field_values
                    if field_values:
                        org_domains = field_values["domains"]
                        for org_dom in org_domains:
                            # print(f"This is the domain {domain}")
                            # print(f"This is the org domain : {org_dom}")
                            if org_dom in domain:
                                return org
            if location:# if we have the locatoin then we loop through the outputs until there's a match
                for org in data:
                    # print(org)
                    org_id = org["id"]
                    field_values = get_field_value_by_id(org_id)
                    # print(f"{field_values=}")
                    if field_values and field_values["Location"]:
                        if in_US(location):
                            city, state = field_values["Location"]["city"], field_values["Location"]["state"]
                            if city and city in location:
                                return org 
                            elif state and state in location:
                                return org
                        else:
                            city, country = field_values["Location"]["city"], field_values["Location"]["country"]
                            if country and country in location or country and country in location:  
                                return org
            else:
                return None
            # return data
            # return orgs # Return the first organization found
        else:
            return None

def affinity_enrich(row):
    in_energize = False
    name, location, domain, uuid = row
    enriched_fields = {'id': uuid, 'name': name, 'domain': domain, "Location": location}

    for k in fields_to_extract:
        enriched_fields[k] = None
    try:
        org = get_company_by_name(name, domain=None, location=location)
        if org:
            id = org["id"]
            field_values = get_field_value_by_id(id)
            enriched_fields = {'id': id, 'name': org["name"], 'domain': org["domain"]}

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

            org_id = org["id"]
            if in_energize_affinity(org_id):
                in_energize = True

        enriched_fields["In Energize Affinity"] = in_energize
        return enriched_fields
    except Exception as e:
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

# companies = array_to_tuples(pd.read_csv("../companies.csv")[["name","location","domain","id"]].values)

def enriched_df(companies_df):

    result = []
    for row in companies_df:
        result.append(affinity_enrich(tuple(row)))
    return pd.DataFrame(result)
