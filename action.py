import pandas as pd
import requests 
from requests.auth import HTTPBasicAuth
# from config import AFFINITY_API_KEY
from affinity import affinity_enrich

# print(os.listdir("./private_data"))  # This shows files in the folder


def array_to_tuples(array):
    """
    Convert a 2D array (list of lists) into a list of tuples.

    Args:
        array (list of list of str): The input 2D array.

    Returns:
        list of tuples: Each tuple corresponds to a row in the input array.
    """
    return [tuple(row) for row in array]
skipped_indeces = pd.read_csv("./private_data/skipped_indices.csv")["skipped_indeces"].values
companies = array_to_tuples(pd.read_csv("./private_data/companies.csv")[["name","location","domain","id"]].values)
enriched_df = pd.read_csv("./private_data/enriched_df_preliminary.csv")

final_enriched_companies = []
skipped_indeces = set(skipped_indeces)
for index, row in enumerate(companies):
    if index in skipped_indeces:
        final_enriched_companies.append(affinity_enrich(row))
        break
    else:
        final_enriched_companies.append(dict(enriched_df.iloc[index]))

pd.DataFrame(final_enriched_companies).to_csv("final_enriched.csv")