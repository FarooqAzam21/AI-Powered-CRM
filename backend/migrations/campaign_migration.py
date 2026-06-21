"""
Campaign Tables Migration
Creates Campaign, CampaignSend, and CampaignTrack tables for Phase 9

Usage: python campaign_migration.py
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import engine, Base
from models.campaigns import Campaign, CampaignSend, CampaignTrack
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    """Create all campaign tables"""
    try:
        logger.info("🔄 Starting campaign tables migration...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Campaign tables created successfully")
        logger.info("   - Campaign")
        logger.info("   - CampaignSend")
        logger.info("   - CampaignTrack")
        logger.info("\n✅ Migration complete!")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate()
