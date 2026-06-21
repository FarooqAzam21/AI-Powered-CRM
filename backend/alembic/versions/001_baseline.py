"""Baseline revision — schema managed via models + create_all for dev SQLite.

Revision ID: 001_baseline
"""
from alembic import op
import sqlalchemy as sa

revision = "001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables are created by SQLAlchemy metadata on app startup.
    # Use `alembic stamp head` on existing databases, then future revisions can ALTER.
    pass


def downgrade() -> None:
    pass
