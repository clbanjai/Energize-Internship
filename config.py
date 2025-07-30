from dotenv import load_dotenv
import os

load_dotenv()

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
IMAP_SERVER = os.getenv("IMAP_SERVER")

# WATCHLIST = os.getenv("WATCHLIST", "").split(",")
THESIS = os.getenv("THESIS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SUPABASE_API_URL = os.getenv("SUPABASE_API_URL")
SUPABASE_API_KEY = os.getenv("SUPABASE_API_KEY")
SUPABASE_TABLE = os.getenv("SUPABASE_TABLE")
AFFINITY_API_KEY = os.getenv("AFFINITY_API_KEY")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
CSE_ID = os.getenv("CSE_ID")
# NEWSLETTERS = os.getenv("NEWSLETTERS").split(",")

