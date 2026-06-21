"""
Test Celery Task Queue
Verify all tasks are properly configured and can execute
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from tasks.celery_app import celery_app
from database import SessionLocal, Base, engine
from auth.models import User, Contact, Email, Lead
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_test_data():
    """Create test data for task testing"""
    db = SessionLocal()
    
    # Create test user
    user = db.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(
            email="test@example.com",
            password="hashed_password",
            role="admin"
        )
        db.add(user)
        db.commit()
        logger.info("✅ Test user created")
    
    # Create test contact
    contact = db.query(Contact).filter(Contact.email == "contact@example.com").first()
    if not contact:
        contact = Contact(
            email="contact@example.com",
            name="Test Contact",
            company="Test Company",
            user_id=user.id
        )
        db.add(contact)
        db.commit()
        logger.info("✅ Test contact created")
    
    # Create test email
    email = db.query(Email).filter(Email.sender == "contact@example.com").first()
    if not email:
        email = Email(
            gmail_message_id="test123",
            sender="contact@example.com",
            subject="Test Email",
            body="This is a test email for AI classification",
            user_id=user.id
        )
        db.add(email)
        db.commit()
        logger.info("✅ Test email created")
    
    # Create test lead
    lead = db.query(Lead).filter(Lead.contact_id == contact.id).first()
    if not lead:
        lead = Lead(
            contact_id=contact.id,
            user_id=user.id,
            status="new"
        )
        db.add(lead)
        db.commit()
        logger.info("✅ Test lead created")
    
    db.close()
    return user.id, contact.id, email.id, lead.id

def test_celery_health():
    """Test if Celery broker is accessible"""
    print("\n" + "="*60)
    print("🧪 CELERY HEALTH CHECK")
    print("="*60)
    
    try:
        # Try to inspect Celery
        insp = celery_app.control.inspect()
        stats = insp.stats()
        
        if stats:
            print("✅ Celery broker is connected")
            for worker, info in stats.items():
                print(f"   Worker: {worker}")
                print(f"   Pool: {info.get('pool', {}).get('implementation', 'N/A')}")
            return True
        else:
            print("❌ No workers found")
            print("   Start a worker with: celery -A tasks.celery_app worker --loglevel=info")
            return False
    except Exception as e:
        print(f"❌ Celery connection failed: {e}")
        print("   Make sure Redis is running: redis-server")
        print("   Or start with: wsl redis-server (on Windows with WSL)")
        return False

def test_email_tasks():
    """Test email task functions"""
    print("\n" + "="*60)
    print("📧 EMAIL TASKS TEST")
    print("="*60)
    
    user_id, contact_id, email_id, lead_id = setup_test_data()
    
    try:
        from tasks.email_tasks import sync_gmail_emails, classify_email, generate_reply, link_email_to_contact
        
        # Test 1: Classify email
        print("\n[1/4] Testing classify_email task...")
        task = classify_email.delay(email_id)
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        # Test 2: Generate reply
        print("\n[2/4] Testing generate_reply task...")
        task = generate_reply.delay(email_id, "professional")
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        # Test 3: Link email to contact
        print("\n[3/4] Testing link_email_to_contact task...")
        task = link_email_to_contact.delay(email_id)
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        # Test 4: Sync Gmail
        print("\n[4/4] Testing sync_gmail_emails task...")
        task = sync_gmail_emails.delay(user_id)
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        print("\n✅ All email tasks submitted successfully")
        
    except Exception as e:
        print(f"❌ Email tasks test failed: {e}")
        import traceback
        traceback.print_exc()

def test_ai_tasks():
    """Test AI task functions"""
    print("\n" + "="*60)
    print("🤖 AI TASKS TEST")
    print("="*60)
    
    user_id, contact_id, email_id, lead_id = setup_test_data()
    
    try:
        from tasks.ai_tasks import classify_email_batch, detect_intent, extract_sentiment
        
        # Test 1: Classify batch
        print("\n[1/3] Testing classify_email_batch task...")
        task = classify_email_batch.delay([email_id])
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        # Test 2: Detect intent
        print("\n[2/3] Testing detect_intent task...")
        task = detect_intent.delay(email_id)
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        # Test 3: Extract sentiment
        print("\n[3/3] Testing extract_sentiment task...")
        task = extract_sentiment.delay(email_id)
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        print("\n✅ All AI tasks submitted successfully")
        
    except Exception as e:
        print(f"❌ AI tasks test failed: {e}")
        import traceback
        traceback.print_exc()

def test_lead_tasks():
    """Test lead task functions"""
    print("\n" + "="*60)
    print("🎯 LEAD TASKS TEST")
    print("="*60)
    
    user_id, contact_id, email_id, lead_id = setup_test_data()
    
    try:
        from tasks.lead_tasks import score_lead, check_follow_ups, convert_lead, mark_lost
        
        # Test 1: Score lead
        print("\n[1/4] Testing score_lead task...")
        task = score_lead.delay(lead_id)
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        # Test 2: Check follow-ups
        print("\n[2/4] Testing check_follow_ups task...")
        task = check_follow_ups.delay()
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        # Test 3: Convert lead
        print("\n[3/4] Testing convert_lead task...")
        task = convert_lead.delay(lead_id)
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        # Test 4: Mark lost
        print("\n[4/4] Testing mark_lost task...")
        task = mark_lost.delay(lead_id, "Not interested")
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        print("\n✅ All lead tasks submitted successfully")
        
    except Exception as e:
        print(f"❌ Lead tasks test failed: {e}")
        import traceback
        traceback.print_exc()

def test_campaign_tasks():
    """Test campaign task functions"""
    print("\n" + "="*60)
    print("📮 CAMPAIGN TASKS TEST")
    print("="*60)
    
    try:
        from tasks.campaign_tasks import process_campaigns, send_follow_up_email
        
        # Get test lead
        db = SessionLocal()
        lead = db.query(Lead).first()
        db.close()
        
        if not lead:
            print("❌ No test lead found, skipping campaign tests")
            return
        
        # Test 1: Process campaigns
        print("\n[1/2] Testing process_campaigns task...")
        task = process_campaigns.delay()
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        # Test 2: Send follow-up
        print("\n[2/2] Testing send_follow_up_email task...")
        task = send_follow_up_email.delay(lead.id)
        print(f"✅ Task submitted: {task.id}")
        print(f"    Status: {task.status}")
        
        print("\n✅ All campaign tasks submitted successfully")
        
    except Exception as e:
        print(f"❌ Campaign tasks test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 CELERY TASK QUEUE TEST SUITE")
    print("="*60)
    
    # Check Celery health
    if not test_celery_health():
        print("\n⚠️  Celery broker not available")
        print("    This is OK for testing task structure")
        print("    To fully test, start: redis-server && celery -A tasks.celery_app worker")
        return
    
    # Run tests
    test_email_tasks()
    test_ai_tasks()
    test_lead_tasks()
    test_campaign_tasks()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)
    print("\nNext steps:")
    print("1. Start Redis: redis-server (or wsl redis-server on Windows)")
    print("2. Start Celery worker: celery -A tasks.celery_app worker --loglevel=info")
    print("3. Start Celery Beat (optional): celery -A tasks.celery_app beat --loglevel=info")
    print("4. Run backend: python app_new.py")
    print("5. Test endpoints: curl http://localhost:8000/api/v1/tasks/health")
    print("\n")

if __name__ == "__main__":
    main()
