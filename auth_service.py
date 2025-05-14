import os
from dotenv import load_dotenv
from supabase import create_client, Client
from utils import resource_path  # Import resource_path from utils.py

# Load environment variables from .env file using resource_path
load_dotenv(resource_path('.env'))

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) 