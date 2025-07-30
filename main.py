import warnings
import pandas as pd

from db_client import company_in_database, fetch_all, unseen_deals, upload_dataframe
from parser_new_cleaned import ctvc, fortune, keepcool, eusubstack, cleaning
from newsletter import get_new_ctvc, get_new_forutne, get_new_keepcool, get_new_eusubstack
from affinity import enrich_df
from embeddings import embed_companies

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

NEWSLETTER_SOURCES = {
    "ctvc": (get_new_ctvc, ctvc),
    "fortune": (get_new_forutne, fortune),
    "keepcool": (get_new_keepcool, keepcool),
    "eusubstack": (get_new_eusubstack, eusubstack),
}

# ─────────────────────────────────────────────────────────────
# PIPELINE STAGES
# ─────────────────────────────────────────────────────────────
def fetch_newsletter_data(sources: dict) -> pd.DataFrame:
    all_data = pd.DataFrame()
    for name, (fetch_urls, parse_func) in sources.items():
        new_urls = fetch_urls() or []
        print(f"📩 Found {len(new_urls)} new {name} newsletters")
        if new_urls:
            for i, url in enumerate(new_urls, start=1):
                print(f"   ↳ Parsing {name} newsletter #{i}")
                df = parse_func(url)
                if df is not None and not df.empty:
                    all_data = pd.concat([all_data, df])
                else:
                    print(f"   ⚠️ Failed to parse {name} newsletter #{i}")
    return all_data


def resolve_companies(companies: pd.DataFrame, deals: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    db_companies = fetch_all("companies")
    new_companies = pd.DataFrame()

    for _, row in companies.iterrows():
        match = company_in_database(row, db_companies)
        temp_id = row["company_uuid"]

        if match is not None:
            existing_id = match["company_uuid"]
            existing_name = match["name"]
            deals.loc[deals["company_uuid"] == temp_id, "company_uuid"] = existing_id
            deals.loc[deals["company_uuid"] == existing_id, "name"] = existing_name
            print(f"🔁 Matched existing company: {existing_name}")
        else:
            print(f"➕ New company: {row['name']} ({row['location']})")
            new_companies = pd.concat([new_companies, row.to_frame().T])

    return new_companies.reset_index(drop=True), deals


def upload_new_companies(companies: pd.DataFrame):
    if companies.empty:
        print("✅ No new companies to upload.")
        return

    print(f"\n🧬 Enriching and uploading {len(companies)} new companies...")
    companies["embedding"] = companies.apply(embed_companies, axis=1)
    upload_dataframe(companies, "companies")


def upload_new_deals(deals: pd.DataFrame):
    print("\n🔎 Checking for unseen deals...")
    new = unseen_deals(deals)
    if new is not None and not new.empty:
        print(f"✅ Uploading {len(new)} new deals")
        upload_dataframe(new, "funding")
    else:
        print("✅ No new deals to upload.")


# ─────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────────────────────
def main():
    print("🚀 Starting newsletter ingestion pipeline...\n")
    
    # 1. Fetch and parse all newsletter data
    raw_data = fetch_newsletter_data(NEWSLETTER_SOURCES)
    if raw_data is not None and not raw_data.empty:
        # 2. Clean and separate into companies / deals
        print(raw_data)
        
        companies, deals = cleaning(raw_data)

        # 3. Enrich company data from Affinity
        enriched_companies = enrich_df(companies)

        # 4. Match or add new companies
        new_companies, updated_deals = resolve_companies(enriched_companies, deals)

        # 5. Upload new companies to Supabase
        upload_new_companies(new_companies)

        # 6. Upload deals that are not yet in Supabase
        upload_new_deals(updated_deals)

        print(f"\n🎉 Pipeline complete: {new_companies.shape[0]} new companies, {updated_deals.shape[0]} total deals processed.")

if __name__ == "__main__":
    main()
