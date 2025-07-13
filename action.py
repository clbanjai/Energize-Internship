import pandas as pd
import requests 
from requests.auth import HTTPBasicAuth
# from config import AFFINITY_API_KEY
import sys
import math
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

# Add at the top

# Load chunk index from argument (1–8)
chunk_index = int(sys.argv[1]) if len(sys.argv) > 1 else 1
assert 1 <= chunk_index <= 8, "Chunk index must be between 1 and 8"

# Load and split data
companies_df = pd.read_csv("./private_data/companies.csv")[["name", "location", "domain", "id"]]
companies = array_to_tuples(companies_df.values)

# Split into 8 equal chunks
chunk_size = math.ceil(len(companies) / 8)
start = (chunk_index - 1) * chunk_size
end = chunk_index * chunk_size
companies_chunk = companies[start:end]

# Enrich only this chunk
final_enriched_companies = []
for row in companies_chunk.head():
    final_enriched_companies.append(affinity_enrich(row))

# Save output with chunk-specific filename
pd.DataFrame(final_enriched_companies).to_csv(f"enriched_chunk_{chunk_index}.csv", index=False)
