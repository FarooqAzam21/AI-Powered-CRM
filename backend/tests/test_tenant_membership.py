from auth.models import WorkspaceMember


def test_workspace_member_model_exists():
    assert WorkspaceMember.__tablename__ == "workspace_members"
