from fastapi import FastAPI, Request
import requests
from requests.auth import HTTPBasicAuth
import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Now you can import from config.py
from config import AFFINITY_API_KEY

app = FastAPI()

def get_all_organizations():
    url = "https://api.affinity.co/organizations"
    headers = {"Content-Type": "application/json"}
    params = {"page_size": 500}

    all_orgs = []
    next_page_token = None

    while True:
        if next_page_token:
            params["page_token"] = next_page_token

        response = requests.get(url, headers=headers, auth=HTTPBasicAuth("", AFFINITY_API_KEY), params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch organizations: {response.status_code} - {response.text}")

        data = response.json()
        all_orgs.extend(data.get("organizations", []))
        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break

    return all_orgs

@app.post("/trigger-affinity-fetch")
async def trigger_affinity_fetch(req: Request):
    payload = await req.json()
    all_orgs = get_all_organizations()

    # Option 1: return to Zapier (if small enough)
    return {"count": len(all_orgs), "first": all_orgs[0] if all_orgs else {}}

    # Option 2: write to database or callback a Zapier webhook

# Removed module-level print statement to prevent execution on import