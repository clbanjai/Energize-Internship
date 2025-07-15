
from bs4 import BeautifulSoup
import requests
import pandas as pd
import sys
import math

def is_valid_company_url(url: str, timeout: int = 5, min_html_length: int = 2000) -> bool:
    try:
        # Normalize protocol
        if not url.startswith("http"):
            url = "https://" + url

        response = requests.get(url, timeout=timeout)
        if response.status_code >= 400:
            return False  # Unreachable or error

        content = response.text.lower()

        # Check for very short responses
        if len(content) < min_html_length:
            return False

        # Keywords that often indicate a parked or placeholder domain
        parking_signals = [
            "buy this domain", "this domain is for sale", "parked by", "domain parking",
            "is available for purchase", "get this domain", "register your domain"
        ]

        # Keywords often present on legitimate company websites
        company_signals = ["about us", "product", "team", "careers", "contact", "services", "solutions"]

        # If parking phrases are found, it's not valid
        if any(phrase in content for phrase in parking_signals):
            return False

        # If at least one company-related keyword exists, it's likely valid
        if any(keyword in content for keyword in company_signals):
            return True

        # Fallback: HTML is long and no parking signals — assume valid
        return True

    except requests.exceptions.RequestException:
        return False  # Timeout, DNS error, etc.

chunk_index = int(sys.argv[1]) if len(sys.argv) > 1 else 1
assert 1 <= chunk_index <= 8, "Chunk index must be between 1 and 8"

clean_data = pd.read_csv("./private_data/clean_data.csv")
clean_data = clean_data.sort_values(by="Company", ascending=True).reset_index(drop=True)

chunk_size = math.ceil(len(clean_data) / 8)
start = (chunk_index - 1) * chunk_size
end = chunk_index * chunk_size
companies_chunk = clean_data[start:end]
url_list = []
for index, row in companies_chunk[:5].iterrows():
    domain = row["Domain"]
    # if index%20==0:
    #     print(f"Processing {index+1}/{(clean_data.shape[0])}")
    if not pd.isna(domain) and is_valid_company_url(domain):
        url_list.append(domain)
    else:
        url_list.append("Not a valid domain")
url_list = pd.DataFrame(url_list, columns=["Domains"])
url_list.to_csv(f"./domain_list_chunk_{chunk_index}.csv", index=False)
