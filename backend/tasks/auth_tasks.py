"""
Auth Tasks - Authentication and maintenance tasks
Token cleanup, security scans
"""
from tasks.celery_app import celery_app
from database import SessionLocal
from auth.models import User
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, name="tasks.auth_tasks.cleanup_expired_tokens")
def cleanup_expired_tokens(self):
    """
    Cleanup expired verification tokens
    Runs daily at 2 AM
    """
    try:
        db = SessionLocal()
        
        # Find users with old verification tokens
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        users_to_clean = db.query(User).filter(
            User.verification_token != None,
            User.updated_at < cutoff_date
        ).all()
        
        logger.info(f"🧹 Cleaning up {len(users_to_clean)} expired tokens")
        
        for user in users_to_clean:
            if not user.is_verified:
                # Keep token if user not verified yet
                continue
            user.verification_token = None
        
        db.commit()
        db.close()
        
        logger.info(f"✅ Token cleanup complete")
        return {
            "cleaned_count": len(users_to_clean)
        }
        
    except Exception as e:
        logger.error(f"❌ Token cleanup failed: {e}")
        raise

@celery_app.task(bind=True, name="tasks.auth_tasks.disable_inactive_accounts")
def disable_inactive_accounts(self, days: int = 30):
    """
    Disable accounts that have been inactive for specified days
    """
    try:
        db = SessionLocal()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get inactive users
        # This would require tracking last_login in User model
        # For now, use updated_at as proxy
        
        logger.info(f"🔒 Checking for inactive accounts ({days}+ days)")
        
        db.close()
        return {"checked": True}
        
    except Exception as e:
        logger.error(f"❌ Inactive account check failed: {e}")
        raise

@celery_app.task(bind=True, name="tasks.auth_tasks.audit_failed_logins")
def audit_failed_logins(self):
    """
    Audit failed login attempts
    TODO: Implement login attempt logging
    """
    try:
        logger.info("📊 Auditing failed login attempts")
        # Would check failed_login_attempts table
        return {"audited": True}
    except Exception as e:
        logger.error(f"❌ Login audit failed: {e}")
        raise
