import requests
from bs4 import BeautifulSoup, NavigableString
import json
import os
from urllib.parse import urlparse
from datetime import datetime
from io import BytesIO
from PIL import Image
import pytesseract


def fallback_fortune_deals(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=3)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            for tag in soup:
                text = tag.get_text()
                if "VENTURE DEALS"in text:
                    start_index = text.find("VENTURE DEALS") + len("VENTURE DEALS-")
                else:
                    start_index = 0
                end_keywords = ["FUNDS","Funds of Funds","Funds +","Funds"]
                end_index = len(text)
                for keyword in end_keywords:
                    if keyword in text:
                        end_index = text.find(keyword)
            deals = text[start_index:end_index]
            return deals
        else:
            print(f"Failed to fetch: {response.status_code}")
    except Exception as e:
        print(f"Error occuer {e}")
        return None
    

def fortune_deals(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, verify=False, timeout=5)
        if response.status_code != 200:
            print(f"Failed to fetch: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        # Find the <h3> tag with "VENTURE DEALS"
        venture_header = None
        for h3 in soup.find_all("h3"):
            if "VENTURE DEALS" in h3.get_text(strip=True).upper():
                venture_header = h3
                break

        if not venture_header:
            print("VENTURE DEALS section not found.")
            return None

        deals = []
        current = venture_header.find_next_sibling("p")

        while current:
            # Stop condition: check if a <b> tag contains a section header like "FUNDS + FUNDS OF FUNDS" or "PRIVATE EQUITY"
            b_tag = current.find("b")
            if b_tag:
                b_text = b_tag.get_text(strip=True).upper()
                if "FUNDS + FUNDS OF FUNDS" in b_text or "PRIVATE EQUITY" in b_text:
                    break

            a_tag = current.find("a", href=True)
            if a_tag:
                link = a_tag["href"]
                domain = extract_domain(link)
                raw_text = current.get_text(separator=" ", strip=True).lstrip("–-•·")
                deals.append(f"{raw_text} with a domain of {domain}")

            current = current.find_next_sibling("p")

        return "\n".join(deals) if deals else None

    except Exception as e:
        print(f"Error occurred: {e}")
        return None


def fortune_date(url):
    str_date = url[20:30]
    return datetime.strptime(str_date,"%Y/%m/%d").date()


def fortune_term_sheet_page_news(page_url):
    response = requests.get(page_url, verify=False, timeout=3)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find the correct script tag with ld+json type
        script_tag = soup.find("script", type="application/ld+json", id="json-schema")
        if script_tag:
            try:
                data = json.loads(script_tag.string)
                items = data.get("mainEntity", {}).get("itemListElement", [])
                urls = []
                for item in items:
                    if item.get("url"):
                        url = item.get("url")
                        urls.append(url)
                            # break
                # urls = [item.get("url") for item in items if item.get("url")]
                return urls
            except Exception as e:
                print(f"Error parsing JSON: {e}")
                return None 
        else:
            print("No JSON-LD script tag found.")
            return None 
    else:
        print(f"Failed to scrape. Status code: {response.status_code}")
        return None 

def get_new_forutne(seen_file_path: str = "private_data/fortune_newsletters.json", archive_url: str = "https://fortune.com/tag/term-sheet/") -> list:
    try:
        with open(seen_file_path, "r") as f:
            seen_links = (json.load(f))
            
    except FileNotFoundError:
        seen_links = []
    
    links = fortune_term_sheet_page_news(archive_url)
    new_links = []
    for link in links:
        if link not in seen_links:
            new_links.append(link)
    if new_links:
        seen_links.extend(new_links)
        os.makedirs(os.path.dirname(seen_file_path), exist_ok=True)
        with open(seen_file_path, "w") as f:
            json.dump(sorted(seen_links), f, indent=2)

    return new_links

def extract_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def get_new_keepcool(newsletter_page = "https://www.keepcool.co/archive?tags=Newsletter&page=1",seen_file_path = "private_data/keepcool_newsletters.json"):
    try:
        with open(seen_file_path, "r") as f:
            seen_links = (json.load(f))
            
    except FileNotFoundError:
        seen_links = []
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                  "AppleWebKit/537.36 (KHTML, like Gecko) " +
                  "Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://www.keepcool.co/",
    "Accept-Language": "en-US,en;q=0.9",
}
    response = requests.get(newsletter_page, headers=headers)

    base_url = "https://www.keepcool.co"
    # response = requests.get(newsletter_page,verify=False)
    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    for a in soup.find_all("a", attrs={"data-discover": "true"}):
        href = a.get("href", "")
        if href.startswith("/p/"):
            full_url = base_url + href
            if full_url not in seen_links:
                seen_links.append(full_url)
                # Check if the URL is a newsletter link
                links.append(full_url)
    os.makedirs(os.path.dirname(seen_file_path), exist_ok=True)
    with open(seen_file_path,"w") as f:
        json.dump(seen_links,f,indent=2)
    return links

def keepcool_deals(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                      "AppleWebKit/537.36 (KHTML, like Gecko) " +
                      "Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.keepcool.co/",
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Step 1: Find the <b> tag that contains "curated deals"
    b_tags = soup.find_all("b")
    tag_of_interest = None
    for b in b_tags:
        if "curated deals" in b.text.lower():
            tag_of_interest = b
            break

    if not tag_of_interest:
        print("No 'curated deals' section found.")
        return []

    # Step 2: Collect all bullet point text following the tag
    funding_blurbs = []
    current = tag_of_interest.find_next()
    while current:
        if isinstance(current, NavigableString):
            current = current.next_sibling
            continue

        text = current.get_text(strip=True)
        if text.startswith("•") or text.startswith("·"):
            link_tag = current.find("a", href=True)
            link = link_tag['href'] if link_tag else None

            funding_blurbs.append({
                "raw_text": text,
                "source_link": link
            })
        elif current.name in ["h1", "h2", "h3", "b"]:  # end of blurb section
            break

        current = current.find_next_sibling()
    result = ""
    for deal in funding_blurbs:
        result += f"{deal["raw_text"]} with a domain of {extract_domain(deal["source_link"])} \n"
    return result.replace("•","")

def keepcool_date(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
                      "AppleWebKit/537.36 (KHTML, like Gecko) " +
                      "Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://www.keepcool.co/",
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    span_tags = soup.find_all("span")

    for span in span_tags:
        text = span.get_text(strip=True)
        try:
            parsed_date = datetime.strptime(text, "%B %d, %Y").date()
            return parsed_date
        except ValueError:
            continue

    return None


def ctvc_deals(url: str) -> str:
    """
    Downloads a CTVC newsletter and extracts the 'Deals of the Week' section.
    """
    try:
        response = requests.get(url, verify=False, timeout=5)
    except Exception as e:
        return f"Failed to fetch page: {e}"

    soup = BeautifulSoup(response.text, "html.parser")

    # Find the heading for "Deals of the Week"
    headers = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    deals_header = None
    for header in headers:
        if "deals of the week" in header.get_text(strip=True).lower():
            deals_header = header
            break

    if not deals_header:
        return None

    # Extract content until the next heading of same or higher level
    deals_text = []
    current_level = int(deals_header.name[1])  # e.g., h2 → 2

    for sibling in deals_header.find_next_siblings():
        if sibling.name and sibling.name.startswith('h') and sibling.name[1:].isdigit():
            if int(sibling.name[1]) <= current_level:
                break
        deals_text.append(sibling.get_text(separator=" ", strip=True))
    return "\n\n".join(filter(None, deals_text))



def ctvc_date(url: str) -> datetime.date:
    """
    Extracts the publication date from a CTVC newsletter URL and returns it as a date object (YYYY-MM-DD).
    """
    try:
        response = requests.get(url, verify=False, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        date_tag = soup.find("time")
        if date_tag and 'datetime' in date_tag.attrs:
            date_str = date_tag['datetime']
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        else:
            raise ValueError("No <time> tag with datetime attribute found.")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch or parse date: {e}")


def get_new_ctvc(seen_file_path: str = "private_data/ctvc_newsletters.json",
                 archive_url: str = "https://www.ctvc.co/tag/newsletter/") -> list:
    # Load seen URLs
    try:
        with open(seen_file_path, "r") as f:
            seen_file = json.load(f)
            seen_links = [item.get("url") for item in seen_file if "url" in item]
    except FileNotFoundError:
        seen_file = []
        seen_links = []

    # Fetch current newsletter links from the website
    response = requests.get(archive_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.select("div.loop article")

    new_links = []
    for article in articles:
        title_tag = article.find("h3").find("a")
        link = "https://www.ctvc.co" + title_tag['href']
        if link not in seen_links:
            new_links.append(link)

    # Update seen file with new links
    if new_links:
        with open(seen_file_path, "w") as f:
            updated_seen = seen_file + [{"url": link} for link in new_links]
            json.dump(updated_seen, f, indent=2)

    return new_links


def get_new_eusubstack(seen_file_path = "private_data/eusubstrack_newsletters.json",newsletter_page = "https://europeantech.substack.com/archive"):
    response = requests.get(newsletter_page)
    try:
        with open(seen_file_path, "r") as f:
            seen_links = json.load(f)
    except FileNotFoundError:
        seen_links = []
    new_links = []
    if response.status_code == 200:
        soup = BeautifulSoup(response.text,"html.parser")
        for a in soup.find_all("a",href = True):
            href = a["href"]
            if "substack.com/p/" in href and not href.endswith("/comments"):
                if href not in seen_links:
                    seen_links.append(href)
                    new_links.append(href)
        if new_links:
            with open(seen_file_path, "w") as f:
                json.dump(seen_links, f, indent=2)

        return new_links
    
import requests
from requests.exceptions import Timeout, RequestException
from bs4 import BeautifulSoup


def get_image_from_url(url, target_heading = "Funding Announcements in Europe by Stage"):
    try:
        response = requests.get(url, verify=False, timeout=5)
        if response.status_code != 200:
            print(f"Failed to retrieve page. Status code: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        seen = set()

        # Find the correct <h4> tag by text content
        for h4 in soup.find_all('h4'):
            if h4.get_text(strip=True) == target_heading:
                # Walk forward in the document from the heading
                next_node = h4.find_next()
                while next_node:
                    if next_node.name == 'img':
                        img_url = next_node.get('src')
                        if img_url and img_url not in seen and img_url.startswith(('http', 'https')):
                            seen.add(img_url)
                            try:
                                image_response = requests.get(img_url, timeout=5)
                                img_data = BytesIO(image_response.content)
                                image = Image.open(img_data)
                                width, height = image.size

                                return image
                            except Exception as e:
                                print(f"Failed to open image: {e}")
                                return None
                    next_node = next_node.find_next()

        print("Target heading or image not found.")
        return None

    except Timeout:
        print("Request timed out.")
        return None
    except RequestException as e:
        print(f"Request error: {e}")
        return None
def text_from_image(image):

    # Optional: tell pytesseract where tesseract is installed
    pytesseract.pytesseract.tesseract_cmd = r"C:\Users\ClaudioBanjai\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"

    # Step 1: Load image and perform OCR
    text = pytesseract.image_to_string(image)
    text = text.replace("Al ","AI ")
    text = text.replace("Al-","AI-")
    return text

def eu_substack_deals(url):
    image = get_image_from_url(url)
    text = text_from_image(image)
    return text

def eu_substack_date(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Look for a div that contains the date string in "Mon DD, YYYY" format
    date_div = soup.find("div", string=lambda s: s and "," in s and any(month in s for month in [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ]))

    if date_div:
        try:
            return datetime.strptime(date_div.get_text(strip=True), "%b %d, %Y").date()
        except ValueError:
            pass

    return None

# Example usage



# print(fortune_deals("https://fortune.com/2025/06/27/what-makes-an-ai-avatar-seem-human-according-to-synthesias-ceo/"))