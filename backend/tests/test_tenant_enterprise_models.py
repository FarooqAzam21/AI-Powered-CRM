from auth.models import WorkspaceMember, WorkspaceSetting, Workspace, Organization
from models.campaigns import Campaign


def test_workspace_member_has_enterprise_membership_fields():
    member_columns = {column.name for column in WorkspaceMember.__table__.columns}
    assert "organization_id" in member_columns
    assert "status" in member_columns
    assert "invited_by" in member_columns
    assert "joined_at" in member_columns
    assert "last_active" in member_columns
    assert "permissions" in member_columns


def test_workspace_settings_support_feature_flags_and_workspace_identity():
    settings_columns = {column.name for column in WorkspaceSetting.__table__.columns}
    assert "workspace_id" in settings_columns
    assert "feature_flags" in settings_columns


def test_campaign_model_supports_workspace_tenant_scoping():
    campaign_columns = {column.name for column in Campaign.__table__.columns}
    assert "workspace_id" in campaign_columns


def test_workspace_and_organization_models_remain_backwards_compatible():
    assert Workspace.__tablename__ == "workspaces"
    assert Organization.__tablename__ == "organizations"
