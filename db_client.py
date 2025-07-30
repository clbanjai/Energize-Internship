import requests
import pandas as pd
import uuid
from config import SUPABASE_API_URL, SUPABASE_API_KEY
from supabase import create_client, Client
from embeddings import semantic_search, create_embedding
import numpy as np
from datetime import datetime
from parser_new_cleaned import name_similarity

# Table names

COMPANIES_TABLE = "companies"
FUNDINGS_TABLE = "funding"


supabase: Client = create_client(SUPABASE_API_URL,SUPABASE_API_KEY)

def fetch_all(table="companies",batch_size=1000, max_rows=50000):
    all_rows = []
    for offset in range(0, max_rows, batch_size):
        response = supabase.table(table)\
            .select("*")\
            .range(offset, offset + batch_size - 1)\
            .execute()

        rows = response.data
        if not rows:
            break  # Exit early if no more results
        all_rows.extend(rows)
    return pd.DataFrame(all_rows)

# db_client.py (or separate utilities module)

EXPECTED_COLUMNS = {
    "companies": [
        "company_uuid", "name", "tagline", "domain", "location", "investors",
        "employees_current", "employees_growth_yoy", "investment_stage",
        "last_funding_amount_usd", "linkedin_profile", "industry",
        "business_models", "technologies", "in_energize_affinity",
        "affinity_id", "embedding"
    ],
    "funding": [
        "deal_uuid", "company_uuid", "name", "deal_size", "currency",
        "series", "date", "investors", "source"
    ]
}

def convert_date_to_string(row):
    if pd.notna(row["date"]):
        return row["date"].strftime('%Y-%m-%d')
    return None

def prepare_dataframe_for_upload(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    df = df.copy()
    if "date" in df.columns:
        df["date"] = df.apply(convert_date_to_string, axis=1)

    # Reset index and drop accidental index column
    df = df.reset_index()
    if "index" in df.columns:
        df = df.drop(columns=["index"])

    
    # Replace NaNs with None for Supabase
    df = df.where(pd.notna(df), None)

    return df

def upload_dataframe(df: pd.DataFrame, table_name: str):
    df = prepare_dataframe_for_upload(df, table_name)
    db = fetch_all(table_name)

    # Determine the primary key
    key = "company_uuid" if "company_uuid" in df.columns else "deal_uuid"

    data = df.to_dict(orient="records")
    for row in data:
        if row.get(key) in db[key].values:
            print(f"⚠️ UUID already exists in DB: {row.get(key)}")
        else:
            print("New UUID")
            supabase.table(table_name).insert(row).execute()

example_deal = [[
    "SolarFlux",                  # Company Name
    "Series A",                   # Series
    "25",                         # Deal Size in millions (as a string to be converted)
    "CleanTech Ventures, SunEdge Capital",  # Lead Investors
    "2025-07-11",                # Date of Deal
    "San Diego, CA",             # Location
    "Thermal solar collector developer",    # Tagline
    "https://www.solarfluxenergy.com",      # Domain
    "https://techcrunch.com/solarflux-25m-series-a"  # Source
]]

# insert_deals(example_deal)
def cosine_similarity(vec1,vec2):
        # Compute cosine similarity
    if isinstance(vec1,list):
        vec1 = np.array(vec1)
    if isinstance(vec2,list):
        vec2 = np.array(vec2)
    if isinstance(vec1,str):
        vec1 = np.array(create_embedding(vec1))
    if isinstance(vec2,str):
        vec2 = np.array(create_embedding(vec2))
    similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    return float(similarity)

def location_match(original_location,potential_matching_location):
        if original_location == potential_matching_location:
            return True
        elif name_similarity(original_location,potential_matching_location)>0.8:
            return True
        else:
            original_loc_emb = create_embedding(original_location)
            matching_loc_emb = create_embedding(potential_matching_location)
            similarity = cosine_similarity(np.array(original_loc_emb),np.array(matching_loc_emb))
            if similarity > 0.45:
                return True
            return False


import pandas as pd

def company_in_database(row: dict, db: pd.DataFrame) -> pd.Series:
    """
    Given a row representing a company, checks if it is already in the database.
    Matching is based on:
    - Affinity ID (if numeric)
    - Domain (exact)
    - Name + Location (exact)
    - Semantic similarity (fallback)
    Returns a single matching Series row or None.
    """
    db = db.copy()
    for column in ["name", "location", "domain", "tagline"]:
        if column in db.columns:
            db[column] = db[column].astype(str).str.lower().str.strip()

    name = str(row.get("name", "")).lower().strip()
    location = str(row.get("location", "")).lower().strip()
    domain = row.get("domain")
    tagline = str(row.get("tagline", "")).lower().strip()
    affinity_id = str(row.get("Affinity ID", "")).strip()

    # A. Match by Affinity ID
    if affinity_id.isnumeric():
        match = db[db["Affinity ID"].astype(str) == affinity_id]
        if not match.empty:
            print("BY affinity ID match")
            return match.iloc[0]

    # B. Match by domain
    if pd.notna(domain):
        domain_str = str(domain).strip().lower()
        match = db[db["domain"] == domain_str]
        if not match.empty:
            print("By domain Match")
            return match.iloc[0]

    # C. Match by name + location
    if name in db["name"].values:
        matching_names = db[db["name"] == name]
        for _, matching_row in matching_names.iterrows():
            matching_location = str(matching_row.get("location", "")).strip().lower()
            if location_match(location, matching_location):
                print("By location Match")
                return matching_row  # Already a Series

    # D. Semantic fallback
    embedding_input = f"{name}, {location}, {tagline}"
    semantic_matches = pd.DataFrame(semantic_search(embedding_input, 5))
    name_emb = create_embedding(name)
    loc_emb = create_embedding(location)
    tag_emb = create_embedding(tagline)

    for _, match in semantic_matches.iterrows():
        name_sim = cosine_similarity(name_emb, match.get("name", ""))
        loc_sim = cosine_similarity(loc_emb, match.get("location", ""))
        tag_sim = cosine_similarity(tag_emb, match.get("tagline", ""))
        avg_sim = (name_sim + loc_sim + tag_sim) / 3
        if avg_sim > 0.7:
            print("By semantic match")
            return match  # Already a Series

    return None

def deal_in_database(row,deals,date_tolerance_days = 60):
    company_uuid = row["company_uuid"]
    if company_uuid in  deals["company_uuid"].values:
        print("company_uuid already in database")
        date = row["date"]
        if isinstance(date,str):
            date = datetime.strptime(date,"%Y-%m-%d")
        matching_deals = deals[deals["company_uuid"] == company_uuid]
        matching_deals["date"] = pd.to_datetime(matching_deals["date"])
        for index, deal in matching_deals.iterrows():
            date_match = False
            if pd.notna(date) and pd.notna(deal["date"]):
                date_match = abs((date - deal["date"]).days)
                if date_match <= date_tolerance_days:
                    print("found a match")
                    return True
    return False

def unseen_deals(df):
    unseen = pd.DataFrame()
    deals = fetch_all("funding")
    for index, deal in df.iterrows():
        if not deal_in_database(deal,deals):
            unseen = pd.concat([unseen,deal.to_frame().T])
    unseen.index.name = "deal_uuid"
    return unseen



# db = pd.read_csv("private_data/enriched_companies.csv")
# print("100ms" in db["name"].str.lower().str.strip().values)
# print(in_database({'name': '8 Rivers', 'tagline': 'Net-zero solutions provider	', 'domain': None, 'location': 'Durham, CA',"Affinity ID": "Not in Affinity"},db))
# print(pd.DataFrame(semantic_search("membrion")))
