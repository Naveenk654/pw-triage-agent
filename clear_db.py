import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

try:
    print("Clearing triage_logs...")
    # Delete where category is not equal to a fake string to delete all
    supabase.table("triage_logs").delete().neq("category", "DELETE_ALL_TRIGGER").execute()
    
    print("Clearing processed_emails...")
    supabase.table("processed_emails").delete().neq("message_id", "DELETE_ALL_TRIGGER").execute()
    
    print("Clearing response_cache...")
    supabase.table("response_cache").delete().neq("prompt_hash", "DELETE_ALL_TRIGGER").execute()
    
    print("Database wiped successfully! Clean slate ready for presentation.")
except Exception as e:
    print(f"Error wiping DB: {e}")
