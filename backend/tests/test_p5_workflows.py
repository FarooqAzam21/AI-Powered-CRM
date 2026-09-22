import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

from main import app
from database import Base, get_db
from auth.models import User, Workspace, Organization, WorkspaceMember
from auth.jwt import SECRET_KEY, ALGORITHM
from auth.rbac import Role
from models.workflow import Workflow, WorkflowExecution, WorkflowExecutionStep, WorkflowApproval, WorkflowAuditLog
from models.crm import Contact, Deal
from billing.plans import seed_default_plans
from workflow.condition_evaluator import evaluate_condition, evaluate_all_conditions
from workflow.action_executor import ActionExecutor
from workflow.approval_gate import ApprovalGate
from workflow.engine import WorkflowEngine

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_workflow_p5.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


def create_token(email: str, role: str, org_id: int, ws_id: int):
    payload = {
        "sub": email,
        "role": role,
        "organization_id": org_id,
        "workspace_id": ws_id,
        "exp": datetime.utcnow() + timedelta(hours=2),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@pytest.fixture(scope="module")
def setup_workflow_env():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    seed_default_plans(db)

    uid = uuid.uuid4().hex[:6]
    org = Organization(name=f"Org WF {uid}", slug=f"org-wf-{uid}")
    db.add(org)
    db.commit()
    db.refresh(org)

    ws1 = Workspace(name=f"WS 1 {uid}", organization_id=org.id)
    ws2 = Workspace(name=f"WS 2 {uid}", organization_id=org.id)
    db.add_all([ws1, ws2])
    db.commit()
    db.refresh(ws1)
    db.refresh(ws2)

    user1 = User(
        email=f"admin_wf_{uid}@test.com",
        name=f"Admin WF {uid}",
        password="hash",
        role=Role.WORKSPACE_ADMIN.value,
        organization_id=org.id,
        workspace_id=ws1.id,
        status="active",
    )
    user2 = User(
        email=f"user_ws2_{uid}@test.com",
        name=f"User WS2 {uid}",
        password="hash",
        role=Role.VIEWER.value,
        organization_id=org.id,
        workspace_id=ws2.id,
        status="active",
    )
    db.add_all([user1, user2])
    db.commit()
    db.refresh(user1)
    db.refresh(user2)

    m1 = WorkspaceMember(workspace_id=ws1.id, user_id=user1.id, role=Role.WORKSPACE_ADMIN.value)
    m2 = WorkspaceMember(workspace_id=ws2.id, user_id=user2.id, role=Role.VIEWER.value)
    db.add_all([m1, m2])
    db.commit()

    token_ws1 = create_token(user1.email, Role.WORKSPACE_ADMIN.value, org.id, ws1.id)
    token_ws2 = create_token(user2.email, Role.VIEWER.value, org.id, ws2.id)

    yield {
        "db": db,
        "org": org,
        "ws1": ws1,
        "ws2": ws2,
        "user1": user1,
        "user2": user2,
        "token_ws1": token_ws1,
        "token_ws2": token_ws2,
    }

    db.close()
    Base.metadata.drop_all(bind=engine)


# ── UNIT TESTS: Condition Evaluator ──────────────────────────────────────────

def test_condition_evaluator_operators():
    # equals & not_equals
    assert evaluate_condition({"field": "status", "operator": "equals", "value": "lead"}, {"status": "lead"}) is True
    assert evaluate_condition({"field": "status", "operator": "equals", "value": "customer"}, {"status": "lead"}) is False
    assert evaluate_condition({"field": "status", "operator": "not_equals", "value": "customer"}, {"status": "lead"}) is True

    # contains & not_contains
    assert evaluate_condition({"field": "email", "operator": "contains", "value": "@corp.com"}, {"email": "john@corp.com"}) is True
    assert evaluate_condition({"field": "email", "operator": "not_contains", "value": "@corp.com"}, {"email": "john@gmail.com"}) is True

    # numeric comparisons
    assert evaluate_condition({"field": "score", "operator": "greater_than", "value": 50}, {"score": 75}) is True
    assert evaluate_condition({"field": "score", "operator": "less_than", "value": 50}, {"score": 25}) is True
    assert evaluate_condition({"field": "score", "operator": "greater_than_or_equal", "value": 50}, {"score": 50}) is True
    assert evaluate_condition({"field": "score", "operator": "less_than_or_equal", "value": 50}, {"score": 50}) is True

    # in_list & not_in_list
    assert evaluate_condition({"field": "stage", "operator": "in_list", "value": ["Discovery", "Proposal"]}, {"stage": "Proposal"}) is True
    assert evaluate_condition({"field": "stage", "operator": "not_in_list", "value": ["Won", "Lost"]}, {"stage": "Proposal"}) is True

    # is_empty & is_not_empty
    assert evaluate_condition({"field": "phone", "operator": "is_empty", "value": ""}, {"phone": None}) is True
    assert evaluate_condition({"field": "phone", "operator": "is_not_empty", "value": ""}, {"phone": "123-456"}) is True


def test_condition_groups_logic():
    context = {"status": "lead", "score": 85, "country": "US"}
    # Single group with AND
    conditions = [
        {
            "logic": "AND",
            "conditions": [
                {"field": "status", "operator": "equals", "value": "lead"},
                {"field": "score", "operator": "greater_than", "value": 70},
            ]
        }
    ]
    assert evaluate_all_conditions(conditions, context) is True

    # Single group fails
    conditions_fail = [
        {
            "logic": "AND",
            "conditions": [
                {"field": "status", "operator": "equals", "value": "customer"},
                {"field": "score", "operator": "greater_than", "value": 70},
            ]
        }
    ]
    assert evaluate_all_conditions(conditions_fail, context) is False


# ── UNIT TESTS: Action Executor ───────────────────────────────────────────────

def test_action_executor_sanitization_and_placeholders(setup_workflow_env):
    env = setup_workflow_env
    db = env["db"]
    executor = ActionExecutor(
        workspace_id=env["ws1"].id,
        org_id=env["org"].id,
        user=env["user1"],
        db=db,
    )

    # Placeholders resolution
    text = "Hello {{contact.first_name}}, welcome to {{company}}!"
    resolved = executor._resolve_placeholders(text, {"contact": {"first_name": "Farooq"}, "company": "Antigravity"})
    assert resolved == "Hello Farooq, welcome to Antigravity!"

    # Payload sanitization
    dirty_payload = {"token": "secret123", "password": "pass", "api_key": "k-999", "name": "Valid"}
    clean_payload = executor._sanitize_payload(dirty_payload)
    assert clean_payload["name"] == "Valid"
    assert clean_payload["token"] == "[REDACTED]"
    assert clean_payload["password"] == "[REDACTED]"
    assert clean_payload["api_key"] == "[REDACTED]"


# ── INTEGRATION TESTS: Workflow Engine ────────────────────────────────────────

def test_workflow_engine_validation(setup_workflow_env):
    env = setup_workflow_env
    db = env["db"]
    engine = WorkflowEngine(workspace_id=env["ws1"].id, org_id=env["org"].id, user=env["user1"], db=db)

    # Valid definition
    valid_def = {
        "name": "Lead Nurture Flow",
        "trigger_type": "contact_created",
        "trigger_config": {},
        "nodes": [
            {
                "id": "node-1",
                "type": "create_task",
                "config": {"title": "Follow up with new lead", "assigned_to": env["user1"].id},
                "next_nodes": [],
            }
        ]
    }
    is_valid, errors = engine.validate_definition(valid_def)
    assert is_valid is True
    assert len(errors) == 0

    # Invalid trigger type
    invalid_def = {"name": "Bad Trigger", "trigger_type": "invalid_event", "nodes": []}
    is_valid, errors = engine.validate_definition(invalid_def)
    assert is_valid is False
    assert any("trigger_type" in e for e in errors)


def test_workflow_crud_and_workspace_isolation(setup_workflow_env):
    env = setup_workflow_env
    headers_ws1 = {"Authorization": f"Bearer {env['token_ws1']}"}
    headers_ws2 = {"Authorization": f"Bearer {env['token_ws2']}"}

    # 1. Create in WS1
    payload = {
        "name": "WS1 Auto Welcome",
        "description": "Sends welcome notification when contact created",
        "trigger_type": "contact_created",
        "trigger_config": {},
        "nodes": [
            {
                "id": "action-1",
                "type": "notify",
                "config": {"message": "New contact added!"},
                "next_nodes": [],
            }
        ],
    }
    resp = client.post("/api/v1/workflows", json=payload, headers=headers_ws1)
    assert resp.status_code in (200, 201), resp.text
    wf_data = resp.json()
    wf_id = wf_data["id"]
    assert wf_data["name"] == "WS1 Auto Welcome"
    assert wf_data["status"] == "draft"

    # 2. Workspace isolation check: WS2 should NOT be able to access wf_id
    resp_ws2_get = client.get(f"/api/v1/workflows/{wf_id}", headers=headers_ws2)
    assert resp_ws2_get.status_code == 404

    # 3. Enable workflow in WS1
    resp_enable = client.post(f"/api/v1/workflows/{wf_id}/enable", headers=headers_ws1)
    assert resp_enable.status_code == 200
    assert resp_enable.json()["status"] == "active"

    # 4. Disable workflow in WS1
    resp_disable = client.post(f"/api/v1/workflows/{wf_id}/disable", headers=headers_ws1)
    assert resp_disable.status_code == 200
    assert resp_disable.json()["status"] == "paused"

    # 5. List workflows in WS1
    resp_list = client.get("/api/v1/workflows", headers=headers_ws1)
    assert resp_list.status_code == 200
    workflows_list = resp_list.json().get("workflows", resp_list.json().get("items", []))
    assert len(workflows_list) >= 1

    # 6. Delete workflow
    resp_del = client.delete(f"/api/v1/workflows/{wf_id}", headers=headers_ws1)
    assert resp_del.status_code in (200, 204)
    resp_check = client.get(f"/api/v1/workflows/{wf_id}", headers=headers_ws1)
    assert resp_check.status_code == 404


def test_workflow_test_run(setup_workflow_env):
    env = setup_workflow_env
    headers_ws1 = {"Authorization": f"Bearer {env['token_ws1']}"}

    # Create workflow
    payload = {
        "name": "Test Run Workflow",
        "trigger_type": "contact_created",
        "nodes": [
            {
                "id": "action-notify",
                "type": "notify",
                "config": {"message": "Test contact {{contact.first_name}}"},
                "next_nodes": [],
            }
        ],
    }
    create_resp = client.post("/api/v1/workflows", json=payload, headers=headers_ws1)
    wf_id = create_resp.json()["id"]

    # Test run
    test_data = {"contact": {"first_name": "Zack", "email": "zack@example.com"}}
    test_resp = client.post(f"/api/v1/workflows/{wf_id}/test", json=test_data, headers=headers_ws1)
    assert test_resp.status_code == 200, test_resp.text
    result = test_resp.json()
    assert result["status"] in ("completed", "pending", "running")
    assert result["workflow_id"] == wf_id


def test_approval_gate_lifecycle(setup_workflow_env):
    env = setup_workflow_env
    db = env["db"]
    headers_ws1 = {"Authorization": f"Bearer {env['token_ws1']}"}

    # Create workflow needing approval
    payload = {
        "name": "High Value Approval Flow",
        "trigger_type": "deal_created",
        "nodes": [
            {
                "id": "node-ai",
                "type": "ai_action",
                "config": {
                    "action": "reply",
                    "requires_approval": True,
                    "prompt": "Draft contract terms",
                },
                "next_nodes": [],
            }
        ],
    }
    wf_resp = client.post("/api/v1/workflows", json=payload, headers=headers_ws1)
    wf_id = wf_resp.json()["id"]

    # Trigger test execution which pauses at approval gate
    test_resp = client.post(f"/api/v1/workflows/{wf_id}/test", json={"deal": {"amount": 50000}}, headers=headers_ws1)
    exec_id = test_resp.json()["id"]

    # Verify execution status is awaiting_approval
    exec_record = db.query(WorkflowExecution).filter(WorkflowExecution.id == exec_id).first()
    assert exec_record is not None
    assert exec_record.status == "awaiting_approval"

    # Query pending approvals API
    pending_resp = client.get("/api/v1/workflows/approvals/pending", headers=headers_ws1)
    assert pending_resp.status_code == 200
    pending_data = pending_resp.json()
    pending = pending_data.get("approvals", pending_data) if isinstance(pending_data, dict) else pending_data
    matching = [a for a in pending if a["execution_id"] == exec_id]
    assert len(matching) == 1
    approval_id = matching[0]["id"]

    # Approve action
    appr_resp = client.post(
        f"/api/v1/workflows/approvals/{approval_id}/approve",
        json={"decision": "approved", "notes": "Approved by senior manager"},
        headers=headers_ws1,
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "approved"

    # Verify DB state
    approval_rec = db.query(WorkflowApproval).filter(WorkflowApproval.id == approval_id).first()
    assert approval_rec.status == "approved"
    assert approval_rec.notes == "Approved by senior manager"
