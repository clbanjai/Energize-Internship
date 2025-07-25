
from db_client import company_in_database, fetch_all, unseen_deals, upload_dataframe
from parser_new_cleaned import ctvc, fortune, keepcool,eusubstack, cleaning
from affinity import enrich_df
import pandas as pd
from newsletter import get_new_ctvc, get_new_forutne, get_new_keepcool, get_new_eusubstack

import warnings
from embeddings import embed_companies
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

tech_stack = {"ctvc":(get_new_ctvc,ctvc),"fortune":(get_new_forutne,fortune),"keepcool":(get_new_keepcool,keepcool),"eusubstack":(get_new_eusubstack,eusubstack)}

def fetch_newsletter_data(tech_stack = {"ctvc":(get_new_ctvc,ctvc),"fortune":(get_new_forutne,fortune),"keepcool":(get_new_keepcool,keepcool),"eusubstack":(get_new_eusubstack,eusubstack)}):
    all_data = pd.DataFrame()
    for k, v in tech_stack.items():
        new_deal_func, df_func = v
        new_deals = new_deal_func()
        print(f"We have {len(new_deals)} {k} newsletters")
        count = 1
        if new_deals:
            for new_url in new_deals:
                print(count)
                df = df_func(new_url)
                if df is not None and not df.empty:
                    print(f"concatenating {k} to all_data")
                    all_data = pd.concat([all_data,df])
    return all_data


all_data = fetch_newsletter_data()
companies, deals = cleaning(all_data)


enriched = enrich_df(companies)


db_companies = fetch_all("companies")

to_keep = pd.DataFrame()
for index, row in enriched.iterrows():
    match = company_in_database(row, db_companies)
    if match is not None:
        existing_id = match["company_uuid"]
        existing_name = match["name"]
        temp_id = row["company_uuid"]
        to_change = deals[deals["company_uuid"] == temp_id]

        for i, deal in to_change.iterrows():
            print(f"🔁 Updating deal {deal['name']} from {temp_id} → {existing_id}")
            deals.at[i, "company_uuid"] = existing_id
            deals.at[i, "name"] = existing_name
    else:
        print(f"➕ New company to add: {row['name']} ({row['location']})")
        to_keep = pd.concat([to_keep, row.to_frame().T])


print("checking for not seen deals")
new_deals = unseen_deals(deals)
print("\n🧬 Embedding new companies...")
to_keep["embedding"] = to_keep.apply(embed_companies, axis=1)
if to_keep.index.name == "company_uuid":
    to_keep = to_keep.reset_index()

if "index" in to_keep.columns:
    to_keep = to_keep.drop(columns=["index"])

upload_dataframe(to_keep, "companies")
upload_dataframe(new_deals, "funding")  # filtered deals should be final

print(f"✅ Uploaded {to_keep.shape[0]} new companies and {new_deals.shape[0]} total deals.")