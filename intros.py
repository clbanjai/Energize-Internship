from config import AFFINITY_API_KEY, client_id, client_secret, tenant_id,mailbox
from msal import ConfidentialClientApplication
import requests
from requests.auth import HTTPBasicAuth
import json
from affinity import name_similarity

def get_new_emails(user=mailbox,update_seen=True):
    """
    Fetches the latest emails from the specified mailbox using Microsoft Graph API.
    """
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    app = ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret
    )
    
    token_response = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    
    if "access_token" not in token_response:
        raise Exception("Failed to acquire access token")
    
    access_token = token_response["access_token"]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    url = f"https://graph.microsoft.com/v1.0/users/{user}/mailFolders/Inbox/messages?$top=10"
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        emails = response.json().get("value", [])
        if emails:
            with open("private_data/seen_emails.json", "r") as f:
                seen_emails = json.load(f)
            new_emails = []
            for email in emails:
                email_id = email.get("id")
                if email_id not in seen_emails:
                    seen_emails.append(email_id)
                    new_emails.append(email)
            if update_seen:
                with open("private_data/seen_emails.json", "w") as f:
                    json.dump(seen_emails, f,indent=4)
            if new_emails:
                return new_emails
    else:
        raise Exception(f"Failed to fetch emails: {response.status_code} {response.text}")

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

def get_person_info(id,interaction=False):
    url = f"https://api.affinity.co/persons/{id}?with_current_organizations=true"
    if interaction:
        url+="&with_interaction_persons=true"
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
def get_company_info(id):

    url = f"https://api.affinity.co/organizations/{id}"
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
    

def target(id,list_id):
    url = f"https://api.affinity.co/lists/{list_id}/list-entries" 
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


def extract_details_from(email):
    #use similar logic to this, might need to use openAI to determine status
    # pass
    # ppl = []
    # ppl.append(email["from"]["emailAddress"]["address"])
    
    # for recipient in email["toRecipients"]+email["ccRecipients"]+email["bccRecipients"]:
    #     if "emailAddress" in recipient:
    #         if "address" in recipient["emailAddress"]:
    #             if recipient["emailAddress"]["address"] not in ppl:
    #                 ppl.append(recipient["emailAddress"]["address"])
    owners = []
    people = []
    # ppl = [
    # "ldensham@energizecap.com",
    # "neethi.nayak@rwe.com",
    # "sam@felt.com",
    # "doug@felt.com"
    # ]
    ppl = ["niall.mccarthy@hitachienergy.com",
           "katie@energize.vc",
           "andrew@cruxclimate.com"
            ]
    for individual in ppl:
        address = individual
        if "energizecap.com" in address or "energize.vc" in address:
            owners.append(get_person(address)["id"]) #change to get id
        else:
            people.append(address)
    companies = []
    seen_email = set()
    people_ids = []
    portfolio_list = []
    organizations = []
    portfolio_company = False
    pipeline_company = False
    for address in people:
        print("Processing",address)
        at_start = address.find("@")
        domain = address[at_start:]
        print("Domain",domain)
        person_id = get_person(address)["id"]
        people_ids.append(person_id)
        if domain not in seen_email:
            perosn_info = get_person_info(person_id)
            if "organization_ids" in perosn_info and perosn_info["organization_ids"]:
                name_similarity_map = {}
                for org in perosn_info["organization_ids"]:
                    if org not in companies:
                        org_name = get_company_info(org)["name"]
                        similarity = name_similarity(org_name, domain.replace(".com", ""))
                        name_similarity_map[org] = similarity
                sorted_orgs = sorted(name_similarity_map.items(), key=lambda x: x[1], reverse=True)
                best_match = sorted_orgs[0][0] if sorted_orgs else None
                if best_match and best_match not in companies:
                    companies.append(best_match)
                    seen_email.add(domain)
                    print(f"Adding {domain}")
                    companies.append(perosn_info["organization_ids"][0])
                    seen_email.add(domain)
    for affinity_list in [153382,153336]: # portfolio and pipeline
        for company_id in companies:
            print("Checking",get_company_info(company_id)["name"])
            if target(company_id,affinity_list):
                print("Target company found",get_company_info(company_id)["name"])
                if not portfolio_list:
                    if affinity_list == 153382:
                        portfolio_company = True
                    elif affinity_list == 153336:
                        pipeline_company = True
                    print("Adding to portfolio",get_company_info(company_id)["name"])
                    portfolio_list.append((get_company_info(company_id)["name"],company_id))
                elif company_id not in [id for name, id in portfolio_list] and company_id not in [id for name, id in organizations]:
                    print("Adding to organization passed target test",get_company_info(company_id)["name"])
                    organizations.append((get_company_info(company_id)["name"],company_id))
    for company_id in companies:
        if company_id not in [id for name, id in portfolio_list] and company_id not in [id for name, id in organizations]:
            print("Adding to organizations",get_company_info(company_id)["name"])
            organizations.append((get_company_info(company_id)["name"],company_id))
    name = f"{organizations[0][0]} + {portfolio_list[0][0]}"
    portfolio_ids = [id for name, id in portfolio_list]
    organizations = [id for name, id in organizations]
    return name, organizations, portfolio_ids, owners,people_ids, portfolio_company, pipeline_company
def create_opportunity(name: str, list_id = 185179, person_ids=None, organization_ids=None) -> dict:
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
        "name": name + " Test",
        "list_id": list_id,
    }
    if person_ids:
        payload["person_ids"] = person_ids
    if organization_ids:
        payload["organization_ids"] = organization_ids

    response = requests.post(url, auth=HTTPBasicAuth("", AFFINITY_API_KEY), headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    return response.json()

def create_field_value_map(portfolio_company,target_company,owners,portfolio_target):
    if portfolio_company:
        status = 15229313 # 
    elif target_company:
        status = 15229313 #change this to field_status representing pipeline connection made
    return   [{'field_id': 3489930,"value":status},
        {'field_id': 3489931,"value":owners},
        {'field_id': 3489934,"value":str(portfolio_target[0])}]
def set_opportunity_field_values(opportunity_id: int, list_entry_id: int, field_value_map):
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
        if response.status_code != 200:
            print("❌ Failed payload:", json.dumps(payload, indent=2))
            print("❌ Response:", response.status_code, response.text)
        elif response.status_code == 200:
            print("✅ Successfully set field value:", response.json())
    #     response.raise_for_status()

    #     response.raise_for_status()
    #     results.append(response.json())

    # return results
def main():
    emails = get_new_emails(user = "intros@energizecap.com",update_seen=False)
    emails = [""]
    for email in emails:
        print("Processing email:","test")
        try:
            name, organizations, portfolio_ids, owners, people_ids, portfolio_company, pipeline_company = extract_details_from(email)
            print("Creating opportunity for",name)
            if portfolio_company or pipeline_company:
                opportunity = create_opportunity(name, person_ids=people_ids, organization_ids=organizations)
                print("Created opportunity:", opportunity["id"])
                field_value_map = create_field_value_map(portfolio_company,pipeline_company,owners,portfolio_ids)
                set_opportunity_field_values(opportunity["id"], opportunity["list_entries"][0]["id"], field_value_map)
                print("Set field values for opportunity:", opportunity["id"])
            else:
                print("No portfolio or pipeline company found for email:", email["subject"])
        except Exception as e:
            print("Error processing email:", email["subject"], "Error:", str(e))


if __name__ == "__main__":
    # print(target(219955500,153336))
    # main()
    print(get_new_emails(user="cbanjai@energizecap.com", update_seen=False))