from config import AFFINITY_API_KEY
import requests
from requests.auth import HTTPBasicAuth


def unread_emails(credentials):
    pass
def extract_details_from(email):
    #use similar logic to this, might need to use openAI to determine status
    # pass
    # msg = email.message_from_bytes(raw_email)
    # ppl = []
    # if msg.is_multipart():
    #     for part in msg.walk():
    #         content_type = part.get_content_type()
    #         print(content_type)
    #         if content_type == "multipart/alternative":
    #             ppl.append(parseaddr(part["From"]))
    #             ppl.append(parseaddr(part["To"]))
    #             cc_ed = part.get_all("Cc")
    #             if cc_ed:
    #                 for person in cc_ed:
    #                     ppl.append(parseaddr(person))

    # owners = []
    # people = []
    # for individual in ppl:
    #     name, address = individual
    #     if "energizecap.com" in address:
    #         owners.append(address) #change to get id
    #     else:
    #         people.append(address)

    # for external in people:
    pass
        
def get_person(email):
    url = f"https://api.affinity.co/persons?term={email}"
    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "page_size": 500  # maximum per page
    }
    response = requests.get(url, headers=headers, auth=HTTPBasicAuth("", AFFINITY_API_KEY))
    if response.status_code==200:
        data = response.json()
        result = data["persons"]
        return result[0]

def get_person_info(id):
    url = f"https://api.affinity.co/persons/{id}?with_current_organizations=true"
    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "page_size": 500  # maximum per page
    }
    response = requests.get(url, headers=headers, auth=HTTPBasicAuth("", AFFINITY_API_KEY))
    if response.status_code==200:
        data = response.json()
        return data

def portfolio(id):
    url = f"https://api.affinity.co/lists/153382/list-entries" 
    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "page_size": 500  # maximum per page
    }
    response = requests.get(url, headers=headers, auth=HTTPBasicAuth("", AFFINITY_API_KEY))
    if response.status_code==200:
        data = response.json()
        for company in data:
            if company["entity"]["id"] == id:
                return True
        return False

def populate_custom_fields():
    url = f"https://api.affinity.co/lists/185179" 
    headers = {
        "Content-Type": "application/json"
    }
    params = {
        "page_size": 500  # maximum per page
    }
    response = requests.get(url, headers=headers, auth=HTTPBasicAuth("", AFFINITY_API_KEY))
    if response.status_code == 200:
        data = response.json()
        return data["fields"]

import json

def create_opportunity(name: str, list_id: int, person_ids=None, organization_ids=None) -> dict:
    """
    Creates an opportunity in a specific list.

    :param name: Opportunity name
    :param list_id: Affinity list ID of type 'opportunity'
    :param person_ids: Optional list of person IDs
    :param organization_ids: Optional list of organization IDs
    :return: JSON response with opportunity ID and list_entry ID
    """
    url = f"https://api.affinity.co/opportunities"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "name": name,
        "list_id": list_id,
    }


    response = requests.post(url, auth=HTTPBasicAuth("", AFFINITY_API_KEY), headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    return response.json()

def set_opportunity_field_values(opportunity_id: int, list_entry_id: int, field_value_map: list):
    """
    Sets multiple field values on an opportunity.

    :param opportunity_id: The Affinity opportunity ID
    :param list_entry_id: The list_entry_id from list_entries array
    :param field_value_map: List of dicts like:
        [
            {"field_id": 9991, "value": 123},  # enum option ID
            {"field_id": 9992, "value": "2025-07-28"},  # date string
            {"field_id": 9993, "value": "High priority"}  # text/number
        ]
    :return: List of created field value responses
    """
    url = f"https://api.affinity.co/field-values"
    headers = {
        "Content-Type": "application/json"
    }

    results = []

    for field in field_value_map:
        payload = {
            "field_id": field["field_id"],
            "entity_id": opportunity_id,
            "list_entry_id": list_entry_id
        }

        # Determine field type dynamically if needed
        if isinstance(field["value"], int):         # for enum IDs
            payload["value"] = field["value"]
        elif isinstance(field["value"], str) and "-" in field["value"]:  # likely a date
            payload["date"] = field["value"]
        else:                                       # text/number
            payload["value"] = field["value"]

        response = requests.post(url, auth=HTTPBasicAuth("", AFFINITY_API_KEY), headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        results.append(response.json())

    return results

print(create_opportunity("Python Test"),185179)