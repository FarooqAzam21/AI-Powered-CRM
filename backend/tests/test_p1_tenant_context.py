import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

from main import app
from database import Base, get_db
from auth.models import User, Workspace, Organization, WorkspaceMember, TerritoryMetrics, AIRecommendation
from auth.jwt import SECRET_KEY, ALGORITHM
from auth.rbac import Role
from models.crm_unified import Deal, Contact, CustomerProfile, EmailMetadata

from services.dashboard_service import DashboardService
from services.winloss_service import WinLossService
from services.territory_service import TerritoryService
from services.sales_cycle_service import SalesCycleService
from services.relationship_service import RelationshipService
from services.recommendation_service import RecommendationEngine
from services.profile_service import CustomerProfileService
from tasks.analytics_tasks import generate_analytics_report
from tasks.crm_tasks import check_deal_health

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_p1_tenant_context.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_p1_db():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    org = Organization(name="Tenant Org", slug="tenant-org")
    db.add(org)
    db.commit()
    db.refresh(org)

    ws_1 = Workspace(name="Workspace 1", organization_id=org.id)
    ws_2 = Workspace(name="Workspace 2", organization_id=org.id)
    db.add(ws_1)
    db.add(ws_2)
    db.commit()
    db.refresh(ws_1)
    db.refresh(ws_2)

    user_1 = User(
        name="User One",
        email="user1@example.com",
        password="password",
        role=Role.WORKSPACE_ADMIN,
        workspace_id=ws_1.id,
        organization_id=org.id,
        is_verified=True
    )
    user_2 = User(
        name="User Two",
        email="user2@example.com",
        password="password",
        role=Role.WORKSPACE_ADMIN,
        workspace_id=ws_2.id,
        organization_id=org.id,
        is_verified=True
    )
    db.add(user_1)
    db.add(user_2)
    db.commit()
    db.refresh(user_1)
    db.refresh(user_2)

    member_1 = WorkspaceMember(workspace_id=ws_1.id, organization_id=org.id, user_id=user_1.id, role=Role.WORKSPACE_ADMIN, status="active")
    member_2 = WorkspaceMember(workspace_id=ws_2.id, organization_id=org.id, user_id=user_2.id, role=Role.WORKSPACE_ADMIN, status="active")
    db.add(member_1)
    db.add(member_2)
    db.commit()

    # Seed WS 1 Data
    contact_1 = Contact(name="Alice 1", email="alice1@client.com", user_id=user_1.id, workspace_id=ws_1.id)
    db.add(contact_1)
    db.commit()
    db.refresh(contact_1)

    deal_1 = Deal(
        name="Deal Alpha",
        value=50000.0,
        stage="closed_won",
        status="won",
        probability=100.0,
        user_id=user_1.id,
        workspace_id=ws_1.id,
        contact_id=contact_1.id,
        actual_close_date=datetime.utcnow() - timedelta(days=5),
        created_at=datetime.utcnow() - timedelta(days=20),
        stage_moved_at=datetime.utcnow() - timedelta(days=5)
    )
    deal_1_overdue = Deal(
        name="Deal Overdue",
        value=15000.0,
        stage="negotiation",
        status="open",
        probability=50.0,
        user_id=user_1.id,
        workspace_id=ws_1.id,
        contact_id=contact_1.id,
        expected_close_date=datetime.utcnow() - timedelta(days=10),
        created_at=datetime.utcnow() - timedelta(days=40),
        stage_moved_at=datetime.utcnow() - timedelta(days=35)
    )
    db.add(deal_1)
    db.add(deal_1_overdue)

    t_metrics_1 = TerritoryMetrics(
        user_id=user_1.id,
        workspace_id=ws_1.id,
        territory_name="North America",
        territory_type="geographic",
        win_rate_pct=75.0,
        pipeline_value=65000.0,
        deal_count=2,
        opportunity_score=85.0,
        risk_score=15.0
    )
    db.add(t_metrics_1)

    profile_1 = CustomerProfile(
        contact_id=contact_1.id,
        user_id=user_1.id,
        workspace_id=ws_1.id,
        buyer_persona="Decision Maker",
        summary="Key VIP Client"
    )
    db.add(profile_1)

    rec_1 = AIRecommendation(
        user_id=user_1.id,
        workspace_id=ws_1.id,
        contact_id=contact_1.id,
        recommendation_type="follow_up_needed",
        title="Follow up with Alice",
        description="Schedule demo call",
        confidence_score=0.95,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(days=5)
    )
    db.add(rec_1)
    db.commit()

    # Seed WS 2 Data
    contact_2 = Contact(name="Bob 2", email="bob2@client.com", user_id=user_2.id, workspace_id=ws_2.id)
    db.add(contact_2)
    db.commit()
    db.refresh(contact_2)

    deal_2 = Deal(
        name="Deal Beta",
        value=30000.0,
        stage="closed_lost",
        status="lost",
        probability=0.0,
        user_id=user_2.id,
        workspace_id=ws_2.id,
        contact_id=contact_2.id,
        actual_close_date=datetime.utcnow() - timedelta(days=2),
        created_at=datetime.utcnow() - timedelta(days=15),
        stage_moved_at=datetime.utcnow() - timedelta(days=2)
    )
    db.add(deal_2)
    db.commit()

    # Seed WinLoss analysis for both deals
    WinLossService.analyze_closed_deal(db, user_1.id, deal_1.id, outcome="won", workspace_id=ws_1.id)
    WinLossService.analyze_closed_deal(db, user_2.id, deal_2.id, outcome="lost", workspace_id=ws_2.id)

    # Bind testing session to Celery task modules
    import tasks.crm_tasks
    import tasks.analytics_tasks
    import tasks.dashboard_tasks
    tasks.crm_tasks.SessionLocal = TestingSessionLocal
    tasks.analytics_tasks.SessionLocal = TestingSessionLocal
    tasks.dashboard_tasks.SessionLocal = TestingSessionLocal

    yield {
        "db": db,
        "org": org,
        "ws_1": ws_1,
        "ws_2": ws_2,
        "user_1": user_1,
        "user_2": user_2,
        "contact_1": contact_1,
        "contact_2": contact_2,
        "deal_1": deal_1,
        "deal_2": deal_2,
    }

    db.close()
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.pop(get_db, None)


def create_token(email: str, workspace_id: int, organization_id: int):
    return jwt.encode({"sub": email, "workspace_id": workspace_id, "organization_id": organization_id}, SECRET_KEY, algorithm=ALGORITHM)


def test_dashboard_service_workspace_isolation(setup_p1_db):
    data = setup_p1_db
    db = data["db"]

    # WS 1 pipeline snapshot should only contain WS 1 deals
    snapshot_1 = DashboardService.get_pipeline_snapshot(db, data["user_1"].id, workspace_id=data["ws_1"].id)
    assert snapshot_1.average_deal_size == 32500.0
    assert snapshot_1.stages["negotiation"]["count"] == 1
    assert snapshot_1.stages["negotiation"]["value"] == 15000.0

    # WS 2 pipeline snapshot should only contain WS 2 deals
    snapshot_2 = DashboardService.get_pipeline_snapshot(db, data["user_2"].id, workspace_id=data["ws_2"].id)
    assert snapshot_2.average_deal_size == 30000.0
    assert snapshot_2.stages["negotiation"]["count"] == 0

    # Cross-tenant query: querying user_1 with ws_2 returns empty
    snapshot_cross = DashboardService.get_pipeline_snapshot(db, data["user_1"].id, workspace_id=data["ws_2"].id)
    assert snapshot_cross.average_deal_size == 0
    assert snapshot_cross.stages["negotiation"]["count"] == 0


def test_win_loss_service_workspace_isolation(setup_p1_db):
    data = setup_p1_db
    db = data["db"]

    # WS 1 has 1 won deal
    summary_1 = WinLossService.get_win_loss_summary(db, data["user_1"].id, days=90, workspace_id=data["ws_1"].id)
    assert summary_1["total_deals"] == 1
    assert summary_1["won_count"] == 1
    assert summary_1["lost_count"] == 0

    # WS 2 has 1 lost deal
    summary_2 = WinLossService.get_win_loss_summary(db, data["user_2"].id, days=90, workspace_id=data["ws_2"].id)
    assert summary_2["total_deals"] == 1
    assert summary_2["won_count"] == 0
    assert summary_2["lost_count"] == 1

    # Cross workspace check
    summary_cross = WinLossService.get_win_loss_summary(db, data["user_1"].id, days=90, workspace_id=data["ws_2"].id)
    assert summary_cross["total_deals"] == 0


def test_territory_service_workspace_isolation(setup_p1_db):
    data = setup_p1_db
    db = data["db"]

    # WS 1 territory comparison includes North America
    comp_1 = TerritoryService.get_territory_comparison(db, data["user_1"].id, workspace_id=data["ws_1"].id)
    assert "North America" in comp_1["top_performers"]

    # WS 2 territory comparison does not leak North America
    comp_2 = TerritoryService.get_territory_comparison(db, data["user_2"].id, workspace_id=data["ws_2"].id)
    assert "North America" not in comp_2["top_performers"]


def test_profile_and_recommendations_workspace_isolation(setup_p1_db):
    data = setup_p1_db
    db = data["db"]

    # Profile lookup in correct workspace succeeds
    prof = CustomerProfileService.get_profile(db, data["contact_1"].id, workspace_id=data["ws_1"].id)
    assert prof is not None
    assert prof.buyer_persona == "Decision Maker"

    # Profile lookup in foreign workspace returns None
    prof_foreign = CustomerProfileService.get_profile(db, data["contact_1"].id, workspace_id=data["ws_2"].id)
    assert prof_foreign is None

    # Recommendations in WS 1
    recs_1 = RecommendationEngine.get_active_recommendations(db, data["user_1"].id, workspace_id=data["ws_1"].id)
    assert len(recs_1) == 1
    assert recs_1[0]["title"] == "Follow up with Alice"

    # Recommendations in WS 2
    recs_2 = RecommendationEngine.get_active_recommendations(db, data["user_1"].id, workspace_id=data["ws_2"].id)
    assert len(recs_2) == 0


def test_celery_task_context_isolation(setup_p1_db):
    data = setup_p1_db

    # Celery task check_deal_health with WS 1 sees overdue deal
    health_1 = check_deal_health(data["user_1"].id, workspace_id=data["ws_1"].id)
    assert health_1["status"] == "success"
    assert health_1["total_alerts"] == 1
    assert health_1["alerts"][0]["type"] == "overdue"

    # Celery task check_deal_health with WS 2 sees 0 alerts
    health_2 = check_deal_health(data["user_1"].id, workspace_id=data["ws_2"].id)
    assert health_2["status"] == "success"
    assert health_2["total_alerts"] == 0

    # Analytics report task scoping
    report_1 = generate_analytics_report(data["user_1"].id, workspace_id=data["ws_1"].id)
    assert report_1["status"] == "success"
    assert report_1["report"]["sections"]["win_loss_summary"]["won_count"] == 1

    report_cross = generate_analytics_report(data["user_1"].id, workspace_id=data["ws_2"].id)
    assert report_cross["status"] == "success"
    assert report_cross["report"]["sections"]["win_loss_summary"]["won_count"] == 0


def test_api_analytics_router_isolation(setup_p1_db):
    data = setup_p1_db

    token_1 = create_token(data["user_1"].email, data["ws_1"].id, data["org"].id)
    headers_1 = {
        "Authorization": f"Bearer {token_1}",
        "X-Workspace-ID": str(data["ws_1"].id)
    }

    # User 1 requesting win-loss summary in WS 1
    res = client.get("/api/v1/analytics/win-loss-summary", headers=headers_1)
    assert res.status_code == 200
    res_data = res.json()["data"]
    assert res_data["won_count"] == 1
    assert res_data["total_deals"] == 1

    # User 2 requesting win-loss summary in WS 2
    token_2 = create_token(data["user_2"].email, data["ws_2"].id, data["org"].id)
    headers_2 = {
        "Authorization": f"Bearer {token_2}",
        "X-Workspace-ID": str(data["ws_2"].id)
    }
    res_2 = client.get("/api/v1/analytics/win-loss-summary", headers=headers_2)
    assert res_2.status_code == 200
    res_2_data = res_2.json()["data"]
    assert res_2_data["won_count"] == 0
    assert res_2_data["lost_count"] == 1
