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

companies = array_to_tuples(pd.read_csv("./private_data/companies.csv").head(30)[["name","location","domain","id"]].values)
final_enriched_companies = []
for index, row in enumerate(companies):
    final_enriched_companies.append(affinity_enrich(row))
    
pd.DataFrame(final_enriched_companies).to_csv("final_enriched.csv")
