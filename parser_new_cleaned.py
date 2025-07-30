import pandas as pd
import numpy as np
import requests
import uuid
import ast
import re
from domain import find_best_company_site

from difflib import SequenceMatcher
import numpy as np
import re

from config import OPENAI_API_KEY, THESIS
from newsletter import ctvc_date, ctvc_deals, fortune_deals, fortune_date, keepcool_date, keepcool_deals, eu_substack_date, eu_substack_deals

from difflib import SequenceMatcher
from openai import OpenAI


def name_similarity(name1, name2):
    """
    Returns a similarity score between 0 and 1 (higher means more similar).
    """
    for i in [name1, name2]:
        if not isinstance(i, str) or not i or pd.isna(i):
            return 0.0
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()


client = OpenAI(api_key=OPENAI_API_KEY)

def create_batch_prompt(deals: str,climate_only = False) -> str:
    if climate_only:
        prompt = f"""
    You are a structured data extractor for venture deals. Below are multiple deal descriptions. 

    For each, extract the following 7 fields and return a Python list of lists (one list per deal), with **no explanations**:

    1. name Name
    2. Deal Size (e.g., "$87M")
    3. Funding series (e.g., "Seed", "series A", "Growth", "Post-IPO Equity", etc.), If the series cannot be found leave it as an empty string.
    4. tagline – a short phrase describing what the company does
    5. Headquarters location (e.g., "City, Country" or "City, State")
    6. investors – names separated by commas
    7. Using the company name, location, and tagline, determine its website domain by performing a google search. If the domain cannot be found, 
    then leave as an empty string, but try as hard as possible to find the domain.
    Do not forget about any of these categories. 
    Make sure that the inner lists have exactly 7 elements
    💡 Ignore any emojis and any symbol mistakes like ~__----///. Maintain original capitalization and punctuation.
    DO NOT 
    ### Format:

    [
    ["name Name", "deal_size", "series", "tagline", "location", "investors","domain"],
    ["name Name", "deal_size", "series", "tagline", "location", "investors","domain"],

    ...
    ]
    ### Example
    For instance if the input was: 
    ⚡ SkyNRG, an Amsterdam, Netherlands-based sustainable aviation fuel producer, raised $284m in Growth funding from APG Asset Management. 

    ⚡ Radiant Nuclear, an El Segundo, CA-based micro nuclear reactor developer, raised $165m in series C funding from DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital, and other investors.

    ⚡ Battery Smart, a Gurgaon, India-based battery swapping network service, raised $29m in series B funding from Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, and responsAbility Investments. 

    🏭 ecop, a Vienna, Austria-based high-tech heat pump manufacturer, raised $12m in Growth funding from European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, and New Energy Technology (AUS). 

    Early-Stage
    ⚡ Heron Power, a Santa Cruz, CA-based power electronics manufacturer, raised $38m in series A funding from Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures, and other investors. 

    🏠 Gridcare, a Redwood City, CA-based grid investment optimization platform, raised $14m in Seed funding from Xora Innovation, Acclimate Ventures, Aina Climate AI Ventures, Breakthrough Energy Ventures, Clearvision Ventures, and other investors. 
    and your output should be:
    [
        ["SkyNRG", "$284M", "Growth", "Sustainable aviation fuel producer", "Amsterdam, Netherlands", "APG Asset Management","https://skynrg.com/"],

        ["Radiant Nuclear", "$165M", "series C", "Micro nuclear reactor developer", "El Segundo, CA", "DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital","https://www.radiantnuclear.com/"],

        ["Battery Smart", "$29M", "series B", "Battery swapping network service", "Gurgaon, India", "Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, responsAbility Investments"in","https://www.batterysmart.in/"],

        ["ecop", "$12M", "Growth", "High-tech heat pump manufacturer", "Vienna, Austria", "European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, New Energy Technology (AUS)","https://www.ecop.at/"],

        ["Heron Power", "$38M", "series A", "Power electronics manufacturer", "Santa Cruz, CA", "Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures", "https://www.heronpower.com/" ],

        ["Gridcare", "$14M", "Seed", "Grid investment optimization platform", "Redwood City, CA", "Xora Innovation, Acclimate Ventures, Aina Climate AI Ventures, Breakthrough Energy Ventures, Clearvision Ventures","https://www.gridcare.ai/"],

    ]
        ### Task
        Now perform this operation for the following input: {deals}
        The final output should be a list of lists
        """
    else:
        prompt = f"""
    You are a structured data extractor for venture deals. Below are multiple deal descriptions. 

    For each, extract the following 7 fields and return a Python list of lists (one list per deal), with **no explanations**:

    1. **name Name**
    2. **Deal Size** – e.g., "$87M"
    3. **Funding series** – e.g., "Seed", "series A", "Growth", "Post-IPO Equity", etc.
    4. **tagline** – a short phrase describing what the company does
    5. **Headquarters location** – formatted as "City, Country" or "City, State"
    6. **investors** – names separated by commas
    7. **name Website domain** – using the company name, location, and tagline, find the official website via Google search; if unavailable, return an empty string
    8. **In Thesis** – Boolean `True` or `False` indicating whether the company fits the following investment thesis:{THESIS}

    > The company should be **asset-light**, primarily **software-based** (but light hardware components are allowed), and focused on enabling the **energy transition**, **sustainability**, **resilience**, **rare earths**, **electrification**, **autonomy**, **digitization**,**infrastructure**,**permitting**.
    > Do **not** include companies operating solely in **finance**, **hospitality**, **customer service**, **blockchain**, **health**, **hiring/employment**, **Marketing**, or other areas unrelated to climate or sustainability.

    ### Format:

    [
    ["name Name", "deal_size", "series", "tagline", "location", "investors","domain", In thesis],
    ["name Name", "deal_size", "series", "tagline", "location", "investors","domain", In thesis],

    ...
    ]
    ### Example
    For instance if the input was: 
    ⚡ SkyNRG, an Amsterdam, Netherlands-based sustainable aviation fuel producer, raised $284m in Growth funding from APG Asset Management. 

    ⚡ Radiant Nuclear, an El Segundo, CA-based micro nuclear reactor developer, raised $165m in series C funding from DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital, and other investors.

    ⚡ Battery Smart, a Gurgaon, India-based battery swapping network service, raised $29m in series B funding from Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, and responsAbility Investments. 

    🏭 ecop, a Vienna, Austria-based high-tech heat pump manufacturer, raised $12m in Growth funding from European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, and New Energy Technology (AUS). 
    Paraform, $4m, Seed, Connect startupts with recruiter networks, Software, Mayfield
    Early-Stage
    ⚡ Heron Power, a Santa Cruz, CA-based power electronics manufacturer, raised $38m in series A funding from Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures, and other investors. 

    🏠 Gridcare, a Redwood City, CA-based grid investment optimization platform, raised $14m in Seed funding from Xora Innovation, Acclimate Ventures, Aina Climate AI Ventures, Breakthrough Energy Ventures, Clearvision Ventures, and other investors. 
    and your output should be:
    [
        ["SkyNRG", "$284M", "Growth", "Sustainable aviation fuel producer", "Amsterdam, Netherlands", "APG Asset Management","https://skynrg.com/"],

        ["Radiant Nuclear", "$165M", "series C", "Micro nuclear reactor developer", "El Segundo, CA", "DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital","https://www.radiantnuclear.com/", True],

        ["Battery Smart", "$29M", "series B", "Battery swapping network service", "Gurgaon, India", "Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, responsAbility Investments"in","https://www.batterysmart.in/", True],

        ["ecop", "$12M", "Growth", "High-tech heat pump manufacturer", "Vienna, Austria", "European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, New Energy Technology (AUS)","https://www.ecop.at/",True],

        ["Heron Power", "$38M", "series A", "Power electronics manufacturer", "Santa Cruz, CA", "Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures", "https://www.heronpower.com/",True ],

        ["Gridcare", "$14M", "Seed", "Grid investment optimization platform", "Redwood City, CA", "Xora Innovation, Acclimate Ventures, Aina Climate AI Ventures, Breakthrough Energy Ventures, Clearvision Ventures","https://www.gridcare.ai/",True],

        ["Paraform", "$4m", "Seed", "Connect startupts with recruiter networks", " ", "Mayfield","https://www.paraform.com/", False]
]
    ]
        ### Task
        Now perform this operation for the following input: {deals}
        The final output should be a list of lists
        """
       
    return prompt

def classify_industry(text,climate_only = False):
    prompt = create_batch_prompt(text,climate_only)

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

def filter(list_of_lists):
    filter_data =[]
    for i in list_of_lists:
        if i[-1]:
            filter_data.append(i[:-1])
    return filter_data

def dataframe_OPENAI(text: str,climate_only=False) -> pd.DataFrame:
    # deals = strip_deal_sections(text)

    def try_classify_once():
        try:
            result = classify_industry(text,climate_only)
            if not climate_only:
                result = filter(result)
            if not isinstance(result, list) or not all(len(item) == 7 for item in result):
                raise ValueError("Invalid result structure")
            return result
        except Exception as e:
            print(f"Classification error: {e}")
            return None

    # First attempt
    categorized_list = try_classify_once()
    # Retry once if failed
    if not categorized_list:
        print("Retrying classify_industry...")
        categorized_list = try_classify_once()
        if not categorized_list:
            print("Retrying a second time")
            categorized_list = try_classify_once()

    # Build dataframe if successful
    if categorized_list:
        columns = [
            "name", "deal_size", "series", "tagline", "location", "investors", "domain"
        ]
        return pd.DataFrame(categorized_list, columns=columns)
    else:
        print("Couldn't extract")
    
    return None


def populate_domains(df):
    df = df.copy()
    for row in df.itertuples():
        domain = find_best_company_site(row.name,row.location)
        if domain:
            df.at[row.Index,"domain"] = domain
    return df
from bs4 import BeautifulSoup


def ctvc(url):
    """
    Extracts the 'Deals of the Week' section from a CTVC newsletter URL and returns it as a DataFrame.
    """
    deals = ctvc_deals(url)
    if deals:
        df = dataframe_OPENAI(deals,climate_only=True)
        if df is not None:
            date = ctvc_date(url)
            df['date'] = date
            df["source"] = url
            try:
                df["domain"] = pd.NA
                df_new = populate_domains(df)
                return df_new
            except Exception as e:
                return df
        return df
    else:# response = requests.get(url, verify=False, timeout=5)
        return None

def fortune(url):
    deals = fortune_deals(url)
    if deals:
        # return "we were able to extract deals"
        df = dataframe_OPENAI(deals,climate_only=False)
        if df is not None and not df.empty:
            date = fortune_date(url)
            df["date"] = date
            df["source"] = url
        return df
    else:
        return None
            
# print(fortune("https://fortune.com/2025/06/27/what-makes-an-ai-avatar-seem-human-according-to-synthesias-ceo/"))
# fortune_data#.to_csv("fortune_data.csv",index=False)    

def keepcool(url):
    deals = keepcool_deals(url)
    if deals:
        df = dataframe_OPENAI(deals,climate_only=True)
        if df is not None and not df.empty:
            date = keepcool_date(url)
            df["date"] = date
            df["source"] = url
        return df
    else:
        return None
    

def eusubstack(url):
    deals = eu_substack_deals(url)
    # return deals
    if deals:
        df = dataframe_OPENAI(deals,climate_only=False)
        if df is not None and not df.empty:
            date = eu_substack_date(url)
            df["date"] = date
            df["source"] = url
            try:
                df["domain"] = pd.NA
                df_new = populate_domains(df)
                return df_new
            except Exception as e:
                return df
        return df
    else:
        return None


def clean_deal_size_column(df, column="deal_size", eur_to_usd=1.08):
    df = df.copy()
    standardized = []
    currencies = []

    for val in df[column]:
        if pd.isna(val):
            standardized.append(None)
            currencies.append(None)
            continue

        val = str(val).strip()

        if val.lower() in {"undisclosed", "na", "n/a", ""}:
            standardized.append(None)
            currencies.append(None)
            continue

        is_eur = "€" in val
        is_usd = "$" in val
        match = re.search(r"([\d.,]+)\s*([kKmMbB]?)", val)
        if match:
            number_str = match.group(1).replace(",", "")
            unit = match.group(2).upper()
            try:
                number = float(number_str)
                if unit in ["B","BN"] :
                    number *= 1000
                elif unit == ["K","k"]:
                    number /= 1000

                if is_usd:
                    currencies.append("USD")
                elif is_eur:
                    number *= eur_to_usd
                    currencies.append("EUR")
                else:
                    currencies.append("Unknown")

                standardized.append(round(number, 2))
            except ValueError:
                standardized.append(None)
                currencies.append(None)
        else:
            standardized.append(None)
            currencies.append(None)

    # Overwrite Deal Size
    df[column] = standardized

    # Ensure Currency column is placed right next to Deal Size
    if "currency" in df.columns:
        df.drop("currency", axis=1, inplace=True)

    deal_size_idx = df.columns.get_loc(column)
    df.insert(deal_size_idx + 1, "currency", currencies)

    return df


def repeated_attribute(df, value,attribute="name"):
    return df[df[attribute].str.lower() == value.lower()]


def normalize_investors_to_set(inv_str: str) -> set:
    if pd.isna(inv_str):
        return set()
    return set(i.strip().lower() for i in inv_str.split(','))


from datetime import datetime


def fuzzy_deduplicate_local(
    df,
    name_col="name",
    deal_col="deal_size",
    series_col="series",
    location_col="location",
    date_col="date",
    threshold=0.7,
    deal_size_tolerance=2.0,
    date_tolerance_days=60,
    window=5
):
    df = df.sort_values(by=name_col).reset_index(drop=True)
    keep_flags = [True] * len(df)
    count = 0

    # Ensure date column is in datetime format
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    for i, row in df.iterrows():
        if not keep_flags[i]:
            continue
        count += 1

        name_i = row[name_col]
        deal_i = row[deal_col]
        series_i = row[series_col]
        loc_i = row[location_col]
        date_i = row[date_col]

        for j in range(max(0, i - window), min(len(df), i + window + 1)):
            if j == i or not keep_flags[j]:
                continue

            other = df.iloc[j]

            name_match = name_similarity(name_i, other[name_col]) > threshold

            deal_match = True
            if pd.notna(deal_i) and pd.notna(other[deal_col]):
                deal_match = abs(deal_i - other[deal_col]) <= deal_size_tolerance

            series_match = True
            if pd.notna(series_i) and pd.notna(other[series_col]) and str(series_i).strip() and str(other[series_col]).strip():
                series_match = name_similarity(str(series_i), str(other[series_col])) > threshold

            loc_match = True
            if pd.notna(loc_i) and pd.notna(other[location_col]) and str(loc_i).strip() and str(other[location_col]).strip():
                loc_match = name_similarity(str(loc_i), str(other[location_col])) > 0.5

            # Always match date if both present
            date_match = True
            if pd.notna(date_i) and pd.notna(other[date_col]):
                date_match = abs((date_i - other[date_col]).days) <= date_tolerance_days
            truth_count = 0
            for truth_value in [name_match, deal_match, series_match, loc_match, date_match]:
                if truth_value:
                    truth_count+=1
            if truth_count >= 4 and date_match and name_match:  # At least 3 out of 5 conditions must match
                keep_flags[j] = False  # mark as duplicate

    return df[keep_flags].reset_index(drop=True)



def deduplicate_funding_deals_two_step_partial_overlap(df: pd.DataFrame, min_overlap=2) -> pd.DataFrame:
    df = df.copy()

    df['name'] = df['name'].str.strip().str.lower()
    df['series'] = df['series'].str.strip().str.upper()
    df['domain'] = df['domain'].str.strip().str.lower()
    df['date'] = pd.to_datetime(df['date'])
    df['deal_size_clean'] = df['deal_size'].fillna(0).astype(float).map(lambda x: f"{x:.2f}")
    df['investor_set'] = df['investors'].map(normalize_investors_to_set)

    # --------------------------
    # Step 1: Dedup by structure
    # --------------------------
    df = df.sort_values(by='name')
    structure_dedup =  fuzzy_deduplicate_local(df)
    # --------------------------
    # Step 2: Dedup by investor overlap
    # --------------------------
    keep_indices = []
    used_sets = []

    for idx, row in structure_dedup.iterrows():
        # if idx % 2 == 0:
        current_set = row['investor_set']
        is_duplicate = False

        for existing_set in used_sets:
            if len(current_set.intersection(existing_set)) >= min_overlap:
                is_duplicate = True
                break

        if not is_duplicate:
            keep_indices.append(idx)
            used_sets.append(current_set)

    deduped_df = structure_dedup.loc[keep_indices]

    return deduped_df.drop(columns=['deal_size_clean', 'investor_set']).reset_index(drop=True).sort_values(by="name")

def check_similarity(current_row, previous_row):
    current_name = current_row["clean_name"]
    previous_name = previous_row["clean_name"]
    current_location = current_row["location"]
    previous_location = previous_row["location"]
    current_domain = current_row["domain"]
    previous_domain = previous_row["domain"]
    company_name_similarity = name_similarity(current_name, previous_name)
    if pd.notna(current_location) and pd.notna(previous_location):
        location_similarity = name_similarity(current_location, previous_location)
        if current_name == previous_name:
            if location_similarity > 0.7:
                return True
        elif company_name_similarity > 0.8:
            if location_similarity > 0.8:
                return True
            elif location_similarity<0.45:
                return False
    if pd.notna(previous_domain) and pd.notna(current_domain):
        domain_similarity = name_similarity(current_domain, previous_domain)
        if current_name == previous_name:
            if domain_similarity > 0.8:
                return True
        elif company_name_similarity > 0.8:
            if domain_similarity > 0.95:
                return True
    if company_name_similarity > 0.9:
        if (pd.notna(domain_similarity) and domain_similarity > 0.95) or \
        (pd.notna(location_similarity) and location_similarity > 0.8):
            return True
        else:
            return False  # Avoid merging just on name similarity
    # print("we are returning false")
    return False

            

def new_deal(deals, row,clean_name, investor_map, id_map, company_uuid=None):
    # companies = companies.copy()
    deals = deals.copy()
    # clean_name = row["clean_name"]
    if clean_name not in investor_map:
        investor_map[clean_name] = []
    lead_investors = row["investors"]
    if not pd.isna(lead_investors):
        lead_investors = lead_investors.strip().lower().split(",")
        if lead_investors:
            investor_map[clean_name] = list(set(lead_investors + investor_map[clean_name]))
    # investor_map[clean_name] = list(set(row["investors"].strip().lower().split(",") + investor_map[clean_name]))

    if clean_name not in id_map:
        company_uuid = str(uuid.uuid4()) 
        id_map[clean_name] = company_uuid

    deal_id = str(uuid.uuid4())
    temp = {
        "deal_uuid": deal_id,
        "company_uuid": id_map[clean_name],
        "name": row["name"],
        "deal_size": row["deal_size"],
        "currency": row["currency"],
        "series": row["series"],
        "date": row["date"],
        "investors": row["investors"],
        "source": row["source"]
    }
    temp_df = pd.DataFrame([temp]).set_index("deal_uuid")
    deals = pd.concat([deals, temp_df])

    return deals, investor_map, id_map

def new_company(companies, row,clean_name, investor_map, id_map, company_uuid=None):
    companies = companies.copy()
  
    if clean_name not in investor_map:
        investor_map[clean_name] = []
    lead_investors = row["investors"]
    if pd.notna(lead_investors):
        lead_investors = lead_investors.strip().lower().split(",")
        investor_map[clean_name] = list(set(lead_investors+ investor_map[clean_name]))


    if clean_name not in id_map:
        company_uuid = str(uuid.uuid4()) 
        id_map[clean_name] = company_uuid

    temp = {
        "company_uuid": company_uuid,
        "name": row["name"],
        "domain": row["domain"],
        "location": row["location"],
        "tagline": row["tagline"],
        "investors": list(set(investor_map[clean_name])),
    }
    temp_df = pd.DataFrame([temp]).set_index("company_uuid")
    companies = pd.concat([companies, temp_df])

    return companies, investor_map, id_map

def update_company(companies, row, clean_name, investor_map, id_map):
    companies = companies.copy()
    company_uuid = id_map.get(clean_name)
    lead_investors = row["investors"]
    if not pd.isna(lead_investors):
        try:
            lead_investors = lead_investors.strip().lower().split(",")
        except Exception as e:
            print(f"Error processing lead investors for {clean_name}: {e}")
            print(f"This is the investor: {type(lead_investors)}")
    else:
        lead_investors = []
    if clean_name not in investor_map:
        investor_map[clean_name] = []
    combined_investors = list(set(investor_map[clean_name] + lead_investors))
    investor_map[clean_name] = combined_investors
    companies.at[company_uuid, "investors"] = combined_investors  # wrap list in another list
    if pd.notna(row["domain"]):
        companies.at[company_uuid, "domain"] = row["domain"]
    return companies

def new_entry(companies, deals, row, name,investor_map, id_map):
    """
    Creates a new entry for a company and its deal in the respective DataFrames.
    """
    companies, investor_map, id_map = new_company(companies, row, name, investor_map, id_map)
    deals, investor_map, id_map = new_deal(deals, row, name, investor_map, id_map)
    return companies, deals, investor_map, id_map


def get_clean_name_with_location(clean_names, name, location):
    for i in clean_names[::-1]:
        if name_similarity(i.split("||")[0], name) > 0.7:
            # Check if locations are also similar
            existing_loc = i.split("||")[1] if "||" in i else ""
            if name_similarity(existing_loc, location) > 0.8:
                return i
    return f"{name}||{location}"


def compact_df(clean_data):
    df = clean_data.copy()
    df["clean_name"] = df["name"].str.strip().str.lower()

    companies = pd.DataFrame(columns=["company_uuid", "name", "domain", "location", "tagline", "investors"]).set_index("company_uuid")
    companies["investors"] = companies["investors"].astype(object)

    deals = pd.DataFrame(columns=["deal_uuid", "company_uuid", "name", "deal_size", "currency", "series", "date", "investors", "source"]).set_index("deal_uuid")

    investor_map = {}
    id_map = {}
    clean_names = []

    for index, row in df.iterrows():
        try:
            print(f"\n🔍 Row {index}: {row['name']} - {row['location']}")
            current_name = row["clean_name"]
            current_location = row["location"]

            clean_name = get_clean_name_with_location(clean_names, current_name, current_location)
            print(f"🧼 clean_name = '{clean_name}'")

            if index != 0:
                previous_row = df.iloc[index - 1]
                if check_similarity(row, previous_row):
                    # ✅ Reuse clean_name from previous row
                    clean_name = get_clean_name_with_location(
                        clean_names, previous_row["clean_name"], previous_row["location"]
                    )
                    print(f"♻️  Reusing clean_name from previous: {clean_name}")

                    companies = update_company(companies, row, clean_name, investor_map, id_map)
                    print(f"🔁 Using id_map.get('{clean_name}') → {id_map.get(clean_name)}")

                    deals, investor_map, id_map = new_deal(
                        deals, row, clean_name, investor_map, id_map,
                        company_uuid=id_map.get(clean_name)
                    )
                else:
                    print("➕ New clean_name — adding entry")
                    clean_names.append(clean_name)

                    companies, deals, investor_map, id_map = new_entry(
                        companies, deals, row, clean_name, investor_map, id_map
                    )
            else:
                print("📌 First row — adding entry")
                clean_names.append(clean_name)

                companies, deals, investor_map, id_map = new_entry(
                    companies, deals, row, clean_name, investor_map, id_map
                )

        except Exception as e:
            print(f"❌ ERROR on row {index} - {row['name']}: {e}")
            import traceback
            traceback.print_exc()

    print("\n✅ Finished compact_df")
    return companies, deals

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

def clean_domains(companies):
    url_list = []
    for _, row in companies.iterrows():
        domain = row["domain"]
        if not pd.isna(domain) and is_valid_company_url(domain):
            url_list.append(domain)
        else:
            url_list.append(pd.NA)
    return url_list

def cleaning(df):
    #first we clean the desl size columns
    df = df.copy()
    df = clean_deal_size_column(df)
    # then we deduplicate
    df = deduplicate_funding_deals_two_step_partial_overlap(df)
    # finally we separate
    companies, deals = compact_df(df)
    # only keep the domains that actually exist
    companies["domain"] = clean_domains(companies)
    return companies, deals


# all_data = pd.read_csv("../all_data.csv")[['name', 'Deal Size', 'series', 'tagline', 'location','investors', 'domain', 'date', 'source']]
# companies, funding = clean_and_split_df(all_data)
# print(funding)