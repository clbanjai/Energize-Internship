from bs4 import BeautifulSoup
import requests
from datetime import datetime 

def ctvc_source(html):
    soup = BeautifulSoup(html,"html.parser")
    link_tag = soup.find("a",class_="view-online-link")
    if link_tag and "href" in link_tag.attrs:
        link = link_tag["href"]
        return link
def ctvc_date(html: str) -> datetime.date:
    """
    Extracts the publication date from a CTVC newsletter URL and returns it as a date object (YYYY-MM-DD).
    """
    try:
        # response = requests.get(url, verify=False, timeout=5)
        # response.raise_for_status()
        soup = BeautifulSoup(html, "html.parser")
        date_element = soup.find('span', class_='post-meta-date')

        if date_element:
            date_text = date_element.get_text(strip=True)
        return datetime.strptime(date_text, "%d %b %Y")

        # date_tag = soup.find("time")
        # if date_tag and 'datetime' in date_tag.attrs:
        #     date_str = date_tag['datetime']
        #     return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        # else:
        #     raise ValueError("No <time> tag with datetime attribute found.")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch or parse date: {e}")
    
def ctvc_deals(html: str) -> str:
    """
    Downloads a CTVC newsletter and extracts the 'Deals of the Week' section.
    """
    # try:
    #     response = requests.get(url, verify=False, timeout=5)
    # except Exception as e:
    #     return f"Failed to fetch page: {e}"

    soup = BeautifulSoup(html, "html.parser")

    # Find the heading for "Deals of the Week"
    headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    deals_header = None
    for header in headers:
        if "deals of the week" in header.get_text(strip=True).lower():
            deals_header = header
            break

    if not deals_header:
        return "No 'Deals of the Week' section found."

    # Extract content until the next heading of same or higher level
    deals_text = []
    current_level = int(deals_header.name[1])  # e.g., h2 → 2

    for sibling in deals_header.find_next_siblings():
        if sibling.name and sibling.name.startswith('h') and sibling.name[1:].isdigit():
            if int(sibling.name[1]) <= current_level:
                break
        deals_text.append(sibling.get_text(separator=" ", strip=True))

    return "\n\n".join(filter(None, deals_text))

def strip_deal_sections(text: str) -> str:
    """
    Removes deal section headers from the text and returns the cleaned text.
    """
    fund_index = text.find("Exits")
    text = text[:fund_index]
    sections = ['Late-Stage / Growth', 'Early-Stage', 'Other']
    for section in sections:
        text = text.replace(section, "")
    return text



