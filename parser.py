from openai import OpenAI
import ast
from config import OPENAI_API_KEY
from config import THESIS
import pandas as pd
import uuid



client = OpenAI(api_key=OPENAI_API_KEY)
def create_batch_prompt(deals: str,climate_only = False) -> str:
    if climate_only:
        prompt = f"""
    You are a structured data extractor for venture deals. Below are multiple deal descriptions. 

    For each, extract the following 7 fields and return a Python list of lists (one list per deal), with **no explanations**:

    1. Company Name
    2. Deal Size (e.g., "$87M")
    3. Funding Series (e.g., "Seed", "Series A", "Growth", "Post-IPO Equity", etc.), If the series cannot be found leave it as an empty string.
    4. Tagline – a short phrase describing what the company does
    5. Headquarters Location (e.g., "City, Country" or "City, State")
    6. Lead Investors – names separated by commas
    7. Using the company name, location, and tagline, determine its website domain by performing a google search. If the domain cannot be found, 
    then leave as an empty string, but try as hard as possible to find the domain.
    Do not forget about any of these categories. 
    Make sure that the inner lists have exactly 7 elements
    💡 Ignore any emojis and any symbol mistakes like ~__----///. Maintain original capitalization and punctuation.
    DO NOT 
    ### Format:

    [
    ["Company Name", "Deal Size", "Series", "Tagline", "Location", "Lead Investors","domain"],
    ["Company Name", "Deal Size", "Series", "Tagline", "Location", "Lead Investors","domain"],

    ...
    ]
    ### Example
    For instance if the input was: 
    ⚡ SkyNRG, an Amsterdam, Netherlands-based sustainable aviation fuel producer, raised $284m in Growth funding from APG Asset Management. 

    ⚡ Radiant Nuclear, an El Segundo, CA-based micro nuclear reactor developer, raised $165m in Series C funding from DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital, and other investors.

    ⚡ Battery Smart, a Gurgaon, India-based battery swapping network service, raised $29m in Series B funding from Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, and responsAbility Investments. 

    🏭 ecop, a Vienna, Austria-based high-tech heat pump manufacturer, raised $12m in Growth funding from European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, and New Energy Technology (AUS). 

    Early-Stage
    ⚡ Heron Power, a Santa Cruz, CA-based power electronics manufacturer, raised $38m in Series A funding from Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures, and other investors. 

    🏠 Gridcare, a Redwood City, CA-based grid investment optimization platform, raised $14m in Seed funding from Xora Innovation, Acclimate Ventures, Aina Climate AI Ventures, Breakthrough Energy Ventures, Clearvision Ventures, and other investors. 
    and your output should be:
    [
        ["SkyNRG", "$284M", "Growth", "Sustainable aviation fuel producer", "Amsterdam, Netherlands", "APG Asset Management","https://skynrg.com/"],

        ["Radiant Nuclear", "$165M", "Series C", "Micro nuclear reactor developer", "El Segundo, CA", "DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital","https://www.radiantnuclear.com/"],

        ["Battery Smart", "$29M", "Series B", "Battery swapping network service", "Gurgaon, India", "Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, responsAbility Investments"in","https://www.batterysmart.in/"],

        ["ecop", "$12M", "Growth", "High-tech heat pump manufacturer", "Vienna, Austria", "European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, New Energy Technology (AUS)","https://www.ecop.at/"],

        ["Heron Power", "$38M", "Series A", "Power electronics manufacturer", "Santa Cruz, CA", "Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures", "https://www.heronpower.com/" ],

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

    1. **Company Name**
    2. **Deal Size** – e.g., "$87M"
    3. **Funding Series** – e.g., "Seed", "Series A", "Growth", "Post-IPO Equity", etc.
    4. **Tagline** – a short phrase describing what the company does
    5. **Headquarters Location** – formatted as "City, Country" or "City, State"
    6. **Lead Investors** – names separated by commas
    7. **Company Website Domain** – using the company name, location, and tagline, find the official website via Google search; if unavailable, return an empty string
    8. **In Thesis** – Boolean `True` or `False` indicating whether the company fits the following investment thesis:{THESIS}

    > The company should be **asset-light**, primarily **software-based** (but light hardware components are allowed), and focused on enabling the **energy transition**, **sustainability**, **resilience**, **rare earths**, **electrification**, **autonomy**, **digitization**,**infrastructure**,**permitting**.
    > Do **not** include companies operating solely in **finance**, **hospitality**, **customer service**, **blockchain**, **health**, **hiring/employment**, **Marketing**, or other areas unrelated to climate or sustainability.

    ### Format:

    [
    ["Company Name", "Deal Size", "Series", "Tagline", "Location", "Lead Investors","domain", In thesis],
    ["Company Name", "Deal Size", "Series", "Tagline", "Location", "Lead Investors","domain", In thesis],

    ...
    ]
    ### Example
    For instance if the input was: 
    ⚡ SkyNRG, an Amsterdam, Netherlands-based sustainable aviation fuel producer, raised $284m in Growth funding from APG Asset Management. 

    ⚡ Radiant Nuclear, an El Segundo, CA-based micro nuclear reactor developer, raised $165m in Series C funding from DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital, and other investors.

    ⚡ Battery Smart, a Gurgaon, India-based battery swapping network service, raised $29m in Series B funding from Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, and responsAbility Investments. 

    🏭 ecop, a Vienna, Austria-based high-tech heat pump manufacturer, raised $12m in Growth funding from European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, and New Energy Technology (AUS). 
    Paraform, $4m, Seed, Connect startupts with recruiter networks, Software, Mayfield
    Early-Stage
    ⚡ Heron Power, a Santa Cruz, CA-based power electronics manufacturer, raised $38m in Series A funding from Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures, and other investors. 

    🏠 Gridcare, a Redwood City, CA-based grid investment optimization platform, raised $14m in Seed funding from Xora Innovation, Acclimate Ventures, Aina Climate AI Ventures, Breakthrough Energy Ventures, Clearvision Ventures, and other investors. 
    and your output should be:
    [
        ["SkyNRG", "$284M", "Growth", "Sustainable aviation fuel producer", "Amsterdam, Netherlands", "APG Asset Management","https://skynrg.com/"],

        ["Radiant Nuclear", "$165M", "Series C", "Micro nuclear reactor developer", "El Segundo, CA", "DCVC, Crossbeam Venture Partners, Giant Ventures, Gigascale Capital","https://www.radiantnuclear.com/", True],

        ["Battery Smart", "$29M", "Series B", "Battery swapping network service", "Gurgaon, India", "Rising Tide Energy, Ecosystem Integrity Fund, LeapFrog Investments, responsAbility Investments"in","https://www.batterysmart.in/", True],

        ["ecop", "$12M", "Growth", "High-tech heat pump manufacturer", "Vienna, Austria", "European Innovation Council, KSB, EIT InnoEnergy, Finadvice AG, New Energy Technology (AUS)","https://www.ecop.at/",True],

        ["Heron Power", "$38M", "Series A", "Power electronics manufacturer", "Santa Cruz, CA", "Capricorn Investment Group, Breakthrough Energy Ventures, Energy Impact Partners, Gigascale Capital, Powerhouse Ventures", "https://www.heronpower.com/",True ],

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

    # Build dataframe if successful
    if categorized_list:
        columns = [
            "Company", "Deal Size", "Series", "Tagline", "Location", "Lead Investors", "domain"
        ]
        return pd.DataFrame(categorized_list, columns=columns)
    else:
        print("Couldn't extract")
    
    return None


from bs4 import BeautifulSoup

def ctvc(html):
    pass

def keepcool(html):
    pass

def fortune(html):
    pass

def european_substack(html):
    pass

def general_text_parser(html):
    soup = BeautifulSoup(html,"html.parser")
    return soup.get_text()

from difflib import SequenceMatcher
import numpy as np
import re

def clean_deal_size_column(df, column="Deal Size", eur_to_usd=1.08):
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
    if "Currency" in df.columns:
        df.drop("Currency", axis=1, inplace=True)

    deal_size_idx = df.columns.get_loc(column)
    df.insert(deal_size_idx + 1, "Currency", currencies)

    return df

def repeated_attribute(df, value,attribute="Company"):
    return df[df[attribute].str.lower() == value.lower()]

def normalize_investors_to_set(inv_str: str) -> set:
    if pd.isna(inv_str):
        return set()
    return set(i.strip().lower() for i in inv_str.split(','))

def deduplicate_funding_deals_two_step_partial_overlap(df: pd.DataFrame, min_overlap=2) -> pd.DataFrame:
    df = df.copy()

    # --------------------
    # Normalize base fields
    # --------------------
    df['Company'] = df['Company'].str.strip().str.lower()
    df['Series'] = df['Series'].str.strip().str.upper()
    df['Domain'] = df['Domain'].str.strip().str.lower()
    df['Date'] = pd.to_datetime(df['Date'])
    df['Deal Size Clean'] = df['Deal Size'].fillna(0).astype(float).map(lambda x: f"{x:.2f}")
    df['Investor Set'] = df['Lead Investors'].map(normalize_investors_to_set)

    # --------------------------
    # Step 1: Dedup by structure
    # --------------------------
    df = df.sort_values(by='Date')
    structure_dedup = df.drop_duplicates(
        subset=['Company', 'Deal Size Clean', 'Series'],
        keep='first'
    ).reset_index(drop=True)

    # --------------------------
    # Step 2: Dedup by investor overlap
    # --------------------------
    keep_indices = []
    used_sets = []

    for idx, row in structure_dedup.iterrows():
        current_set = row['Investor Set']
        is_duplicate = False

        for existing_set in used_sets:
            if len(current_set.intersection(existing_set)) >= min_overlap:
                is_duplicate = True
                break

        if not is_duplicate:
            keep_indices.append(idx)
            used_sets.append(current_set)

    deduped_df = structure_dedup.loc[keep_indices]
    return deduped_df.drop(columns=['Deal Size Clean', 'Investor Set']).reset_index(drop=True).sort_values(by="Company")



def transform_to_relational_json(df: pd.DataFrame) -> dict:
    df = df.copy()
    df['Company Clean'] = df['Company'].str.strip().str.lower()

    company_map = {}
    companies = []
    funding_rounds = []

    # Track canonical fields per company
    domain_cache = {}
    tagline_cache = {}

    for _, row in df.iterrows():
        company_key = row['Company Clean']
        name = row['Company']
        tagline = row.get('Tagline')
        location = row.get('Location')
        domain = row.get('Domain')

        # Initialize company if not seen
        if company_key not in company_map:
            company_id = str(uuid.uuid4())
            company_map[company_key] = company_id
            domain_cache[company_key] = domain if pd.notna(domain) else None
            tagline_cache[company_key] = tagline if isinstance(tagline, str) else ""

            companies.append({
                "id": company_id,
                "name": name,
                "tagline": tagline_cache[company_key],
                "location": location,
                "domain": domain_cache[company_key]
            })
        else:
            # Update domain if we don't have one yet and this row has it
            if pd.notna(domain) and not domain_cache[company_key]:
                domain_cache[company_key] = domain
                for comp in companies:
                    if comp["id"] == company_map[company_key]:
                        comp["domain"] = domain
                        break

            # Update tagline if this one is longer
            current_tagline = tagline_cache.get(company_key, "")
            if isinstance(tagline, str) and len(tagline) > len(current_tagline):
                tagline_cache[company_key] = tagline
                for comp in companies:
                    if comp["id"] == company_map[company_key]:
                        comp["tagline"] = tagline
                        break

        # Add funding round
        funding_rounds.append({
            "id": str(uuid.uuid4()),
            "company_id": company_map[company_key],
            "date": row.get('Date'),
            "series": row.get('Series'),
            "deal_size": row.get('Deal Size'),
            "lead_investors": row.get('Lead Investors'),
            "source": row.get('Source')
        })

    return {
        "companies": companies,
        "funding_rounds": funding_rounds
    }

import json
import pandas as pd

# Helper: Recursively replace NaN/NaT with None in nested dicts/lists
def clean_nans(obj):
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(item) for item in obj]
    elif pd.isna(obj):
        return None
    else:
        return obj


def clean_and_split_df(df):
    df = df.copy()
    df = clean_deal_size_column(df)
    df = deduplicate_funding_deals_two_step_partial_overlap(df)
    relational_data = transform_to_relational_json(df)
    clean_data = clean_nans(relational_data)
    return pd.DataFrame(clean_data["companies"]), pd.DataFrame(clean_data["funding_rounds"])


all_data = pd.read_csv("../all_data.csv")[['Company', 'Deal Size', 'Series', 'Tagline', 'Location','Lead Investors', 'Domain', 'Date', 'Source']]
companies, funding = clean_and_split_df(all_data)
print(funding)