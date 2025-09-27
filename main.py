import warnings
import pandas as pd

from parser_new_cleaned import ctvc, fortune, keepcool, eusubstack, cleaning
from newsletter import get_new_ctvc, get_new_forutne, get_new_keepcool, get_new_eusubstack
from affinity import enrich_df
import sys
import os 
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# from shared_files.embeddings import embed_companies
# from shared_files.db_client import company_in_database, fetch_all, unseen_deals, upload_dataframe
from embeddings import embed_companies
from db_client import company_in_database, fetch_all, unseen_deals, upload_dataframe


warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

NEWSLETTER_SOURCES = {
    "ctvc": (get_new_ctvc, ctvc),
    "fortune": (get_new_forutne, fortune),
    "keepcool": (get_new_keepcool, keepcool),
    "eusubstack": (get_new_eusubstack, eusubstack),
}

def fetch_newsletter_data(sources: dict) -> pd.DataFrame:
    all_data = pd.DataFrame()
    for name, (fetch_urls, parse_func) in sources.items():
        new_urls = fetch_urls(update=True) or []
        print(f"Found {len(new_urls)} new {name} newsletters")
        if new_urls:
            for i, url in enumerate(new_urls, start=1):
                print(f"   ↳ Parsing {name} newsletter #{i}")
                df = parse_func(url)
                if df is not None and not df.empty:
                    all_data = pd.concat([all_data, df])
                else:
                    print(f"Failed to parse {name} newsletter #{i}")
    return all_data


def resolve_companies(companies: pd.DataFrame, deals: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    db_companies = fetch_all("companies")
    new_companies = pd.DataFrame()

    for _, row in companies.iterrows():
        match = company_in_database(row, db_companies)
        temp_id = row["company_uuid"]

        if match is not None and not match.empty:
            existing_id = match["company_uuid"]
            existing_name = match["name"]
            deals.loc[deals["company_uuid"] == temp_id, "company_uuid"] = existing_id
            deals.loc[deals["company_uuid"] == existing_id, "name"] = existing_name
            print(f"Matched existing company: {existing_name}")
        else:
            print(f"New company: {row['name']} ({row['location']})")
            new_companies = pd.concat([new_companies, row.to_frame().T])

    return new_companies.reset_index(drop=True), deals


def upload_new_companies(companies: pd.DataFrame):
    if companies.empty:
        print("No new companies to upload.")
        return

    print(f"\n🧬 Enriching and uploading {len(companies)} new companies...")
    companies["embedding"] = companies.apply(embed_companies, axis=1)

    for i, row in companies.iterrows():
        try:
            print(f"Uploading company: {row['name']} (UUID: {row['company_uuid']})")
            upload_dataframe(row.to_frame().T, "companies")
        except Exception as e:
            print(f"Failed to upload company: {row.get('name', '[unknown]')}")
            print(f"Error: {e}\n")
            continue


def upload_new_deals(deals: pd.DataFrame):
    print("\Checking for unseen deals")
    new = unseen_deals(deals)

    if new is None or new.empty:
        print("No new deals to upload.")
        return

    print(f"Uploading {len(new)} new deals")
    new = new.reset_index()  # <-- Critical fix

    for i, row in new.iterrows():
        try:
            print(f"Uploading deal for company UUID: {row['company_uuid']}")
            upload_dataframe(row.to_frame().T, "funding")
        except Exception as e:
            print(f"Failed to upload deal (UUID: {row.get('company_uuid', '[unknown]')})")
            print(f"Error: {e}\n")
            continue


def main():
    print("Starting newsletter ingestion pipeline\n")
    import json
    
    raw_data = fetch_newsletter_data(NEWSLETTER_SOURCES)
    # raw_data = pd.read_csv("raw_data.csv")
    if raw_data is not None and not raw_data.empty:        
        
        companies, deals = cleaning(raw_data)
        # raw_data.to_csv("raw_data.csv",index=False)
        enriched_companies = enrich_df(companies)


        new_companies, updated_deals = resolve_companies(enriched_companies, deals)
        upload_new_companies(new_companies)

        upload_new_deals(updated_deals)

        print(f"\nPipeline complete: {new_companies.shape[0]} new companies, {updated_deals.shape[0]} total deals processed.")

if __name__ == "__main__":
    main()
    