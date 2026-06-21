"""
Phase 6 CRM Features - Test Suite
Tests for deals, profiles, timelines, relationships, and recommendations
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from auth.models import (
    Base, User, Contact, Lead, Deal, DealActivity, CustomerProfile, 
    ContactRelationship, AIRecommendation, Email, Activity
)
from services.deal_service import DealService
from services.profile_service import CustomerProfileService
from services.activity_service import ActivityTimelineService
from services.relationship_service import RelationshipService
from services.recommendation_service import RecommendationEngine

# =================== TEST DATABASE ===================
@pytest.fixture
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def test_user(test_db: Session):
    """Create test user"""
    user = User(
        email="test@example.com",
        password="hashed_password",
        name="Test User",
        role="user"
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def test_contact(test_db: Session, test_user: User):
    """Create test contact"""
    contact = Contact(
        user_id=test_user.id,
        email="contact@example.com",
        name="John Doe",
        company="ACME Corp",
        title="Manager",
        interaction_count=5,
        score=75
    )
    test_db.add(contact)
    test_db.commit()
    test_db.refresh(contact)
    return contact

# =================== DEAL SERVICE TESTS ===================

class TestDealService:
    """Tests for DealService"""
    
    def test_create_deal(self, test_db: Session, test_user: User, test_contact: Contact):
        """Test deal creation"""
        deal = DealService.create_deal(
            db=test_db,
            user_id=test_user.id,
            contact_id=test_contact.id,
            name="Enterprise Deal",
            value=50000,
            stage="prospecting"
        )
        
        assert deal.id is not None
        assert deal.name == "Enterprise Deal"
        assert deal.value == 50000
        assert deal.status == "open"
        assert deal.probability == 10  # Default for prospecting
    
    def test_move_deal_stage(self, test_db: Session, test_user: User, test_contact: Contact):
        """Test moving deal through pipeline"""
        deal = DealService.create_deal(
            db=test_db, user_id=test_user.id, contact_id=test_contact.id,
            name="Test Deal", value=25000
        )
        
        # Move to qualification
        deal = DealService.move_deal_stage(test_db, deal.id, "qualification")
        assert deal.stage == "qualification"
        assert deal.probability == 25
        
        # Move to won
        deal = DealService.move_deal_stage(test_db, deal.id, "won")
        assert deal.status == "won"
        assert deal.probability == 100
        assert deal.actual_close_date is not None
    
    def test_update_deal_value(self, test_db: Session, test_user: User, test_contact: Contact):
        """Test updating deal value"""
        deal = DealService.create_deal(
            db=test_db, user_id=test_user.id, contact_id=test_contact.id,
            name="Test Deal", value=10000
        )
        
        deal = DealService.update_deal_value(test_db, deal.id, 15000)
        assert deal.value == 15000
    
    def test_pipeline_summary(self, test_db: Session, test_user: User, test_contact: Contact):
        """Test pipeline summary generation"""
        # Create deals at different stages
        DealService.create_deal(test_db, test_user.id, test_contact.id, "Deal 1", 10000, "prospecting")
        DealService.create_deal(test_db, test_user.id, test_contact.id, "Deal 2", 20000, "qualification")
        DealService.create_deal(test_db, test_user.id, test_contact.id, "Deal 3", 30000, "proposal")
        
        summary = DealService.get_pipeline_summary(test_db, test_user.id)
        
        assert summary["total_deals"] == 3
        assert summary["total_pipeline_value"] == 60000
        assert "by_stage" in summary
        assert "prospecting" in summary["by_stage"]

# =================== ACTIVITY TIMELINE TESTS ===================

class TestActivityTimelineService:
    """Tests for ActivityTimelineService"""
    
    def test_record_activity(self, test_db: Session, test_user: User, test_contact: Contact):
        """Test recording activity"""
        activity = ActivityTimelineService.record_activity(
            db=test_db,
            user_id=test_user.id,
            contact_id=test_contact.id,
            activity_type="call",
            subject="Client Call",
            description="Discussed pricing"
        )
        
        assert activity.id is not None
        assert activity.type == "call"
        assert activity.contact_id == test_contact.id
    
    def test_contact_timeline(self, test_db: Session, test_user: User, test_contact: Contact):
        """Test getting contact timeline"""
        # Record multiple activities
        ActivityTimelineService.record_activity(test_db, test_user.id, test_contact.id, "email_sent", "Sent proposal")
        ActivityTimelineService.record_activity(test_db, test_user.id, test_contact.id, "call", "Follow up call")
        ActivityTimelineService.record_activity(test_db, test_user.id, test_contact.id, "meeting", "Demo meeting")
        
        timeline = ActivityTimelineService.get_contact_timeline(test_db, test_contact.id)
        
        assert len(timeline) == 3
        assert timeline[0]["type"] in ["email_sent", "call", "meeting"]
    
    def test_activity_summary(self, test_db: Session, test_user: User, test_contact: Contact):
        """Test activity summary generation"""
        for i in range(5):
            ActivityTimelineService.record_activity(
                test_db, test_user.id, test_contact.id, 
                activity_type="email_sent" if i % 2 == 0 else "call"
            )
        
        summary = ActivityTimelineService.get_user_activity_summary(test_db, test_user.id, days=7)
        
        assert summary["total_activities"] == 5
        assert "activities_by_type" in summary

# =================== RELATIONSHIP SERVICE TESTS ===================

class TestRelationshipService:
    """Tests for RelationshipService"""
    
    def test_link_contacts(self, test_db: Session, test_user: User):
        """Test linking contacts"""
        contact1 = Contact(user_id=test_user.id, email="user1@example.com", name="User 1")
        contact2 = Contact(user_id=test_user.id, email="user2@example.com", name="User 2")
        test_db.add_all([contact1, contact2])
        test_db.commit()
        
        rel = RelationshipService.link_contacts(
            test_db, test_user.id, contact1.id, contact2.id, "email_exchange"
        )
        
        assert rel.from_contact_id == contact1.id
        assert rel.to_contact_id == contact2.id
        assert rel.email_count == 1
    
    def test_relationship_graph(self, test_db: Session, test_user: User):
        """Test relationship graph generation"""
        contacts = []
        for i in range(3):
            contact = Contact(user_id=test_user.id, email=f"user{i}@example.com", name=f"User {i}")
            test_db.add(contact)
            contacts.append(contact)
        test_db.commit()
        
        # Link contacts
        RelationshipService.link_contacts(test_db, test_user.id, contacts[0].id, contacts[1].id)
        RelationshipService.link_contacts(test_db, test_user.id, contacts[1].id, contacts[2].id)
        
        graph = RelationshipService.build_relationship_graph(test_db, test_user.id)
        
        assert graph["stats"]["total_contacts"] == 3
        assert graph["stats"]["total_connections"] == 2
        assert len(graph["nodes"]) == 3
        assert len(graph["edges"]) == 2

# =================== CUSTOMER PROFILE TESTS ===================

class TestCustomerProfileService:
    """Tests for CustomerProfileService"""
    
    def test_create_empty_profile(self, test_db: Session, test_user: User, test_contact: Contact):
        """Test creating empty profile"""
        profile = CustomerProfileService._create_empty_profile(
            test_db, test_contact.id, test_user.id
        )
        
        assert profile.contact_id == test_contact.id
        assert profile.user_id == test_user.id
    
    def test_extract_pain_points(self):
        """Test pain point extraction"""
        email_context = "We are struggling with slow implementation and expensive solutions"
        pain_points = CustomerProfileService._extract_pain_points(email_context)
        
        assert len(pain_points) > 0
        assert any("performance" in pp.lower() or "cost" in pp.lower() for pp in pain_points)
    
    def test_extract_interests(self):
        """Test interest extraction"""
        email_context = "We need better CRM solutions and marketing automation"
        interests = CustomerProfileService._extract_interests(email_context)
        
        assert len(interests) > 0

# =================== RECOMMENDATION ENGINE TESTS ===================

class TestRecommendationEngine:
    """Tests for RecommendationEngine"""
    
    def test_build_contact_context(self, test_user: User, test_contact: Contact):
        """Test context building"""
        context = RecommendationEngine._build_contact_context(
            contact=test_contact,
            profile=None,
            emails=[],
            activities=[],
            lead=None,
            deals=[]
        )
        
        assert "Test User" in context or test_contact.name in context
        assert "ACME Corp" in context
    
    def test_best_time_recommendation(self, test_db: Session, test_user: User, test_contact: Contact):
        """Test best time recommendation"""
        profile = CustomerProfile(
            contact_id=test_contact.id,
            user_id=test_user.id,
            response_time_avg=2.5
        )
        test_db.add(profile)
        test_db.commit()
        
        rec = RecommendationEngine._generate_best_time(test_db, test_user.id, test_contact.id, profile)
        
        assert rec is not None
        assert rec.recommendation_type == "best_time"

# =================== INTEGRATION TESTS ===================

class TestPhase6Integration:
    """Integration tests for Phase 6"""
    
    def test_full_deal_workflow(self, test_db: Session, test_user: User, test_contact: Contact):
        """Test complete deal workflow"""
        # Create deal
        deal = DealService.create_deal(
            test_db, test_user.id, test_contact.id,
            "Integration Test Deal", 50000, "prospecting"
        )
        
        # Record activities
        DealService.add_activity(test_db, deal.id, "proposal_sent", "Sent proposal", value_impact=10000)
        
        # Move through stages
        DealService.move_deal_stage(test_db, deal.id, "qualification")
        DealService.move_deal_stage(test_db, deal.id, "proposal")
        
        # Get summary
        summary = DealService.get_pipeline_summary(test_db, test_user.id)
        
        assert summary["total_deals"] == 1
        assert summary["total_pipeline_value"] == 60000  # 50k + 10k impact
    
    def test_full_profile_workflow(self, test_db: Session, test_user: User, test_contact: Contact):
        """Test complete profile generation workflow"""
        # Create profile
        profile = CustomerProfileService._create_empty_profile(test_db, test_contact.id, test_user.id)
        assert profile is not None
        
        # Get profile
        retrieved = CustomerProfileService.get_profile(test_db, test_contact.id)
        assert retrieved.id == profile.id

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
