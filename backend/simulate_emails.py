import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

# varied test cases
EMAILS = [
    {
        "user_email": "testuser@gmail.com",
        "sender": "recruiter@techcorp.com",
        "subject": "Interview Invitation - Software Engineer",
        "body": "Hi, we were impressed by your profile and would like to schedule an interview next Tuesday at 2 PM using Google Meet. Please let us know if this works."
    },
    {
        "user_email": "testuser@gmail.com",
        "sender": "spam@offers.com",
        "subject": "WIN A FREE IPHONE NOW!!!",
        "body": "Click here to claim your prize. Limited time offer. Buy now!"
    },
    {
        "user_email": "testuser@gmail.com",
        "sender": "boss@company.com",
        "subject": "URGENT: Server Down",
        "body": "The production database is unresponsive. Customers are complaining. Please fix this ASAP."
    },
    {
        "user_email": "testuser@gmail.com",
        "sender": "client@business.com",
        "subject": "Project Update",
        "body": "Just checking in on the status of the Q3 deliverables. When can we expect the next draft?"
    }
]

print(f"Starting Email Simulation on {BASE_URL}...\n")

for email in EMAILS:
    print(f"Sending: {email['subject']}")
    try:
        response = requests.post(f"{BASE_URL}/email/process", json=email)
        if response.status_code == 200:
            data = response.json()
            print(f"   Processed!")
            print(f"      Category: {data['category']} ({data['confidence']})")
            print(f"      Action:   {data['action']}")
            print(f"      Reason:   {data['reason']}")
            if data['draft_reply']:
                print(f"      Draft:    {data['draft_reply'][:100]}...")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Connection Failed: {e}")
    
    print("-" * 50)
    time.sleep(1)

print("\nChecking Dashboard Data...")
try:
    history = requests.get(f"{BASE_URL}/email/history").json()
    drafts = requests.get(f"{BASE_URL}/email/drafts").json()
    print(f"   Total Emails: {len(history)}")
    print(f"   Pending Drafts: {len(drafts)}")
except:
    print("   Failed to fetch history")
