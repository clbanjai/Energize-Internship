from parser_new_cleaned import dataframe_OPENAI, cleaning
from affinity import enrich_df
import pandas as pd

# Step 1: Simulate CTVC-style deal blurb
test_text = """
⚡ Volt, a Berlin, Germany-based EV charging infrastructure company, raised $60M in Series B funding from Breakthrough Energy Ventures and Future Energy Ventures.
"""

# Step 2: Run OpenAI-based parsing
df = dataframe_OPENAI(test_text, climate_only=True)
print("🧾 Parsed dataframe:")
print(df)

# Step 3: Clean + deduplicate
companies, deals = cleaning(df)
print("\n🏗️ Cleaned companies:")
print(companies)
print("\n💸 Cleaned deals:")
print(deals)

# Step 4: Enrich using local logic (simulate offline run)
enriched = enrich_df(companies)
print("\n📈 Enriched companies:")
print(enriched.head())
