from dotenv import load_dotenv
import os

# This will load environment variables from a .env file
# Ensure you have a .env file in the root directory with the necessary variables
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

SEMANTAI_API_KEY = os.getenv("SEMANTAI_API_KEY")
# NEWSLETTERS = os.getenv("NEWSLETTERS").split(",")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
MAILBOX = os.getenv("MAILBOX")

