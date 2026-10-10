import os
import random
import uuid
import time
from datetime import datetime, timedelta
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

STUDENT_NAMES = [
    "Rahul Sharma <rahul.sharma99@gmail.com>",
    "Priya Singh <priyasingh.neet@yahoo.com>",
    "Amit Kumar <amitk.jee2025@gmail.com>",
    "Neha Gupta <neha.gupta.study@hotmail.com>",
    "Ravi Verma <raviverma123@gmail.com>",
    "Sneha Patel <snehapatel98@gmail.com>",
    "Vikas Yadav <vikas.yadav.pw@gmail.com>",
    "Pooja Mishra <pooja.mishra11@yahoo.com>",
    "Aditya Raj <adityaraj.dropper@gmail.com>",
    "Kavita Reddy <kavita.reddy22@gmail.com>",
    "Manish Tiwari <manishtiwari.iit@gmail.com>",
    "Shruti Deshmukh <shruti.d@gmail.com>"
]

# (Category, Urgency range, Action, Status)
TEMPLATES = [
    # Academic
    ("academic", (1, 3), "AUTO_REPLY", "RESOLVED"),
    ("academic", (1, 3), "AUTO_REPLY", "RESOLVED"),
    ("academic", (2, 4), "CLARIFY", "PENDING"),
    ("academic", (3, 5), "ESCALATE", "PENDING"),
    
    # Account
    ("account", (2, 4), "AUTO_REPLY", "RESOLVED"),
    ("account", (1, 3), "CLARIFY", "PENDING"),
    
    # Batch Access
    ("batch_access", (4, 5), "APPROVAL_REQUIRED", "PENDING"),
    ("batch_access", (3, 5), "ESCALATE", "PENDING"),
    ("batch_access", (4, 5), "AUTO_REPLY", "RESOLVED"),
    
    # Payment
    ("payment", (4, 5), "ESCALATE", "PENDING"),
    ("payment", (3, 5), "APPROVAL_REQUIRED", "PENDING"),
    
    # Refund
    ("refund", (3, 5), "APPROVAL_REQUIRED", "PENDING"),
    ("refund", (4, 5), "ESCALATE", "PENDING"),
    
    # Technical
    ("technical", (3, 5), "AUTO_REPLY", "RESOLVED"),
    ("technical", (4, 5), "ESCALATE", "PENDING"),
    ("technical", (2, 4), "CLARIFY", "PENDING"),
    
    # Other
    ("other", (1, 2), "AUTO_REPLY", "RESOLVED"),
    ("other", (1, 3), "AUTO_REPLY", "RESOLVED"),
]

def populate():
    print("Generating 40 highly realistic tickets for the dashboard...")
    records = []
    
    now = datetime.utcnow()
    
    for i in range(40):
        student = random.choice(STUDENT_NAMES)
        template = random.choice(TEMPLATES)
        category, urg_range, action, status = template
        
        urgency = random.randint(urg_range[0], urg_range[1])
        
        # Realistic LLM token usage
        prompt_tokens = random.randint(300, 850)
        completion_tokens = random.randint(40, 200)
        
        # Spread the created_at times over the last 24 hours so graphs look natural
        minutes_ago = random.randint(5, 1440)
        created_at = (now - timedelta(minutes=minutes_ago)).isoformat()
        
        records.append({
            "message_id": f"msg_{uuid.uuid4().hex[:12]}",
            "student_email": student,
            "category": category,
            "urgency": urgency,
            "action_taken": action,
            "status": status,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "created_at": created_at
        })
    
    # Insert in batches
    for i in range(0, len(records), 10):
        batch = records[i:i+10]
        supabase.table("triage_logs").insert(batch).execute()
        
    print("✅ Successfully injected 40 realistic tickets into Supabase!")
    print("Refresh your Streamlit dashboard now!")

if __name__ == "__main__":
    populate()
