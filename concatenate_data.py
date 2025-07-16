import os
import pandas as pd

private_data = os.listdir("./private_data")  # This shows files in the folder

companies = pd.DataFrame()
for file in private_data:
    if "domain_list_chunk" in file:
        chunk_df = pd.read_csv(f"./private_data/{file}")
        companies = pd.concat([companies, chunk_df], ignore_index=True)

companies.to_csv("./private_data/domain_list.csv", index=False)
