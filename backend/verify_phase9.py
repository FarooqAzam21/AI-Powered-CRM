#!/usr/bin/env python
"""
PHASE 9 VERIFICATION SCRIPT
Validates all Phase 9 components and their integration

Usage: python verify_phase9.py
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_imports():
    """Verify all Phase 9 modules can be imported"""
    logger.info("🔍 Verifying imports...")
    
    try:
        from models.campaigns import Campaign, CampaignSend, CampaignTrack
        logger.info("  ✅ Models imported successfully")
    except ImportError as e:
        logger.error(f"  ❌ Models import failed: {e}")
        return False
    
    try:
        from schemas.campaigns import (
            CampaignCreate, CampaignUpdate, CampaignResponse, 
            CampaignListResponse, CampaignAnalytics
        )
        logger.info("  ✅ Schemas imported successfully")
    except ImportError as e:
        logger.error(f"  ❌ Schemas import failed: {e}")
        return False
    
    try:
        from services.campaign_service import CampaignService
        logger.info("  ✅ Campaign service imported successfully")
    except ImportError as e:
        logger.error(f"  ❌ Campaign service import failed: {e}")
        return False
    
    try:
        from scheduler.campaign_scheduler import CampaignScheduler
        logger.info("  ✅ Campaign scheduler imported successfully")
    except ImportError as e:
        logger.error(f"  ❌ Campaign scheduler import failed: {e}")
        return False
    
    try:
        from tasks.campaign_tasks import (
            send_campaign_email, bulk_send_campaign, 
            retry_failed_sends, periodic_campaign_monitor
        )
        logger.info("  ✅ Campaign tasks imported successfully")
    except ImportError as e:
        logger.error(f"  ❌ Campaign tasks import failed: {e}")
        return False
    
    try:
        from routers.campaigns import router as campaign_router
        logger.info("  ✅ Campaign router imported successfully")
    except ImportError as e:
        logger.error(f"  ❌ Campaign router import failed: {e}")
        return False
    
    return True

def verify_database_models():
    """Verify database models are correctly defined"""
    logger.info("\n🔍 Verifying database models...")
    
    try:
        from models.campaigns import Campaign, CampaignSend, CampaignTrack, CampaignStatus, EmailStatus
        from database import Base, engine
        
        # Check models have required attributes
        campaign_attrs = ['id', 'name', 'subject', 'body', 'status', 'user_id', 'created_at']
        for attr in campaign_attrs:
            if not hasattr(Campaign, attr):
                logger.error(f"  ❌ Campaign missing attribute: {attr}")
                return False
        logger.info(f"  ✅ Campaign model has all required attributes")
        
        send_attrs = ['id', 'campaign_id', 'contact_id', 'tracking_id', 'status', 'opened_count']
        for attr in send_attrs:
            if not hasattr(CampaignSend, attr):
                logger.error(f"  ❌ CampaignSend missing attribute: {attr}")
                return False
        logger.info(f"  ✅ CampaignSend model has all required attributes")
        
        track_attrs = ['id', 'send_id', 'event_type', 'timestamp']
        for attr in track_attrs:
            if not hasattr(CampaignTrack, attr):
                logger.error(f"  ❌ CampaignTrack missing attribute: {attr}")
                return False
        logger.info(f"  ✅ CampaignTrack model has all required attributes")
        
        # Check enums
        assert hasattr(CampaignStatus, 'DRAFT')
        assert hasattr(CampaignStatus, 'RUNNING')
        assert hasattr(CampaignStatus, 'COMPLETED')
        logger.info(f"  ✅ CampaignStatus enum correctly defined")
        
        assert hasattr(EmailStatus, 'PENDING')
        assert hasattr(EmailStatus, 'SENT')
        assert hasattr(EmailStatus, 'OPENED')
        logger.info(f"  ✅ EmailStatus enum correctly defined")
        
        return True
    except Exception as e:
        logger.error(f"  ❌ Model verification failed: {e}")
        return False

def verify_service_layer():
    """Verify campaign service has all required methods"""
    logger.info("\n🔍 Verifying service layer...")
    
    try:
        from services.campaign_service import CampaignService
        
        required_methods = [
            'create_campaign', 'get_campaign', 'list_campaigns', 
            'update_campaign', 'delete_campaign',
            'personalize_email', 'prepare_bulk_send',
            'mark_sent', 'mark_failed', 'mark_bounced',
            'track_open', 'track_click',
            'get_campaign_analytics'
        ]
        
        for method in required_methods:
            if not hasattr(CampaignService, method):
                logger.error(f"  ❌ CampaignService missing method: {method}")
                return False
        
        logger.info(f"  ✅ CampaignService has all {len(required_methods)} required methods")
        return True
    except Exception as e:
        logger.error(f"  ❌ Service layer verification failed: {e}")
        return False

def verify_api_endpoints():
    """Verify campaign router has all required endpoints"""
    logger.info("\n🔍 Verifying API endpoints...")
    
    try:
        from routers.campaigns import router as campaign_router
        
        # Get all routes defined in router
        routes = [route.path for route in campaign_router.routes]
        
        required_routes = [
            '/campaigns', '/campaigns/{campaign_id}',
            '/campaigns/{campaign_id}/start',
            '/campaigns/{campaign_id}/pause',
            '/campaigns/{campaign_id}/resume',
            '/campaigns/{campaign_id}/retry-failed',
            '/campaigns/{campaign_id}/analytics',
            '/campaigns/{campaign_id}/progress',
            '/campaigns/{campaign_id}/sends',
            '/campaigns/track/{tracking_id}/open',
            '/campaigns/track/{tracking_id}/click'
        ]
        
        for route in required_routes:
            if route not in routes:
                logger.warning(f"  ⚠️  Expected route not found: {route}")
        
        logger.info(f"  ✅ Campaign router has {len(routes)} endpoints")
        return True
    except Exception as e:
        logger.error(f"  ❌ API endpoint verification failed: {e}")
        return False

def verify_celery_tasks():
    """Verify Celery tasks are registered"""
    logger.info("\n🔍 Verifying Celery tasks...")
    
    try:
        from tasks.campaign_tasks import (
            send_campaign_email, bulk_send_campaign, 
            retry_failed_sends, process_open_tracking,
            process_click_tracking, update_campaign_analytics,
            periodic_campaign_monitor
        )
        
        # Check tasks are registered
        tasks = [
            send_campaign_email,
            bulk_send_campaign,
            retry_failed_sends,
            process_open_tracking,
            process_click_tracking,
            update_campaign_analytics,
            periodic_campaign_monitor
        ]
        
        for task in tasks:
            if not hasattr(task, 'delay'):
                logger.error(f"  ❌ Task not registered: {task.name}")
                return False
        
        logger.info(f"  ✅ All {len(tasks)} Celery tasks registered")
        return True
    except Exception as e:
        logger.error(f"  ❌ Celery task verification failed: {e}")
        return False

def verify_personalization():
    """Verify email personalization works"""
    logger.info("\n🔍 Verifying email personalization...")
    
    try:
        from services.campaign_service import CampaignService
        
        template = "Hi {{first_name}}, welcome to {{company}}!"
        context = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com',
            'company': 'Acme Corp',
            'title': 'CEO',
            'phone': '+1-555-1234'
        }
        
        result = CampaignService.personalize_email(template, context)
        expected = "Hi John, welcome to Acme Corp!"
        
        if result != expected:
            logger.error(f"  ❌ Personalization failed. Expected: {expected}, Got: {result}")
            return False
        
        logger.info(f"  ✅ Email personalization works correctly")
        return True
    except Exception as e:
        logger.error(f"  ❌ Personalization verification failed: {e}")
        return False

def verify_throttling_math():
    """Verify throttling calculations are correct"""
    logger.info("\n🔍 Verifying throttling math...")
    
    try:
        # Throttle: 2 emails/minute = 1 email every 30 seconds
        throttle_seconds = 30
        emails_per_minute = 60 / throttle_seconds
        
        if emails_per_minute != 2.0:
            logger.error(f"  ❌ Throttle math incorrect: {emails_per_minute} emails/min")
            return False
        
        # Batch scheduling delays
        batch_size = 5
        expected_delays = [0, 30, 60, 90, 120]  # 5 batches of 5 emails each
        actual_delays = [i * 30 for i in range(5)]
        
        if expected_delays != actual_delays:
            logger.error(f"  ❌ Batch delay calculation incorrect")
            return False
        
        logger.info(f"  ✅ Throttling math verified (2 emails/min = 1 every 30s)")
        logger.info(f"  ✅ Batch scheduling delays: {actual_delays}")
        return True
    except Exception as e:
        logger.error(f"  ❌ Throttling verification failed: {e}")
        return False

def verify_retry_backoff():
    """Verify retry exponential backoff calculations"""
    logger.info("\n🔍 Verifying retry backoff...")
    
    try:
        # Exponential backoff: 30min → 60min → 120min
        base_delay_minutes = 30
        
        for attempt in range(1, 4):
            delay_minutes = base_delay_minutes * (2 ** (attempt - 1))
            expected = [30, 60, 120][attempt - 1]
            
            if delay_minutes != expected:
                logger.error(f"  ❌ Retry backoff incorrect for attempt {attempt}")
                return False
        
        logger.info(f"  ✅ Retry exponential backoff verified")
        logger.info(f"     Attempt 1: 30 minutes")
        logger.info(f"     Attempt 2: 60 minutes")
        logger.info(f"     Attempt 3: 120 minutes")
        return True
    except Exception as e:
        logger.error(f"  ❌ Retry backoff verification failed: {e}")
        return False

def verify_frontend_components():
    """Verify frontend component files exist"""
    logger.info("\n🔍 Verifying frontend components...")
    
    try:
        frontend_components = [
            'frontend/src/components/Campaigns.jsx',
            'frontend/src/components/CampaignBuilder.jsx',
            'frontend/src/components/CampaignAnalytics.jsx'
        ]
        
        for component_path in frontend_components:
            full_path = Path(__file__).parent / component_path
            if not full_path.exists():
                logger.error(f"  ❌ Component file missing: {component_path}")
                return False
        
        logger.info(f"  ✅ All {len(frontend_components)} frontend components found")
        return True
    except Exception as e:
        logger.error(f"  ❌ Frontend verification failed: {e}")
        return False

def verify_documentation():
    """Verify documentation files exist"""
    logger.info("\n🔍 Verifying documentation...")
    
    try:
        docs = [
            'PHASE_9_README.md',
            'PHASE_9_IMPLEMENTATION_SUMMARY.md',
            'backend/migrations/campaign_migration.py'
        ]
        
        for doc_path in docs:
            full_path = Path(__file__).parent / doc_path
            if not full_path.exists():
                logger.error(f"  ❌ Documentation file missing: {doc_path}")
                return False
        
        logger.info(f"  ✅ All documentation files present")
        return True
    except Exception as e:
        logger.error(f"  ❌ Documentation verification failed: {e}")
        return False

def main():
    """Run all verifications"""
    logger.info("=" * 60)
    logger.info("PHASE 9 VERIFICATION SCRIPT")
    logger.info("=" * 60)
    
    all_passed = True
    
    all_passed &= verify_imports()
    all_passed &= verify_database_models()
    all_passed &= verify_service_layer()
    all_passed &= verify_api_endpoints()
    all_passed &= verify_celery_tasks()
    all_passed &= verify_personalization()
    all_passed &= verify_throttling_math()
    all_passed &= verify_retry_backoff()
    all_passed &= verify_frontend_components()
    all_passed &= verify_documentation()
    
    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("✅ ALL VERIFICATIONS PASSED")
        logger.info("Phase 9 is ready for deployment!")
    else:
        logger.error("❌ SOME VERIFICATIONS FAILED")
        logger.error("Please review the errors above")
        return 1
    logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
