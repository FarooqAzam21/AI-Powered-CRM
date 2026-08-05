import logging

from sqlalchemy import inspect, text

logger = logging.getLogger(__name__)


def _has_table(engine, table_name: str) -> bool:
    try:
        return inspect(engine).has_table(table_name)
    except Exception as exc:
        logger.warning("Could not inspect table %s: %s", table_name, exc)
        return False


def _columns(engine, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns(table_name)}


def ensure_auth_schema(engine):
    """Repair legacy auth tables created before the current ORM model."""
    if not _has_table(engine, "users"):
        return

    existing = _columns(engine, "users")
    dialect = engine.dialect.name
    timestamp_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"

    upgrades = {
        "created_at": f"ALTER TABLE users ADD COLUMN created_at {timestamp_type}",
        "updated_at": f"ALTER TABLE users ADD COLUMN updated_at {timestamp_type}",
        "department_id": "ALTER TABLE users ADD COLUMN department_id INTEGER",
        "manager_id": "ALTER TABLE users ADD COLUMN manager_id INTEGER",
        "job_title": "ALTER TABLE users ADD COLUMN job_title VARCHAR",
        "status": "ALTER TABLE users ADD COLUMN status VARCHAR DEFAULT 'active'",
    }

    with engine.begin() as conn:
        for column, statement in upgrades.items():
            if column in existing:
                continue
            try:
                conn.execute(text(statement))
                logger.info("Added missing users.%s column", column)
            except Exception as exc:
                logger.warning("Could not add users.%s column: %s", column, exc)

    # 2. Repair api_keys table with new developer columns
    if _has_table(engine, "api_keys"):
        existing_keys = _columns(engine, "api_keys")
        json_type = "JSON" if dialect == "postgresql" else "TEXT"
        
        upgrades_keys = {
            "owner_id": "ALTER TABLE api_keys ADD COLUMN owner_id INTEGER",
            "hashed_key": "ALTER TABLE api_keys ADD COLUMN hashed_key VARCHAR",
            "key_prefix": "ALTER TABLE api_keys ADD COLUMN key_prefix VARCHAR",
            "status": "ALTER TABLE api_keys ADD COLUMN status VARCHAR DEFAULT 'active'",
            "expires_at": f"ALTER TABLE api_keys ADD COLUMN expires_at {timestamp_type}",
            "last_ip": "ALTER TABLE api_keys ADD COLUMN last_ip VARCHAR",
            "permissions": f"ALTER TABLE api_keys ADD COLUMN permissions {json_type}",
            "rate_limit": "ALTER TABLE api_keys ADD COLUMN rate_limit INTEGER DEFAULT 60",
            "daily_limit": "ALTER TABLE api_keys ADD COLUMN daily_limit INTEGER DEFAULT 1000",
            "requests_today": "ALTER TABLE api_keys ADD COLUMN requests_today INTEGER DEFAULT 0",
            "description": "ALTER TABLE api_keys ADD COLUMN description TEXT",
        }
        
        with engine.begin() as conn:
            for column, statement in upgrades_keys.items():
                if column in existing_keys:
                    continue
                try:
                    conn.execute(text(statement))
                    logger.info("Added missing api_keys.%s column", column)
                except Exception as exc:
                    logger.warning("Could not add api_keys.%s column: %s", column, exc)

    # 3. Repair workspaces table
    if _has_table(engine, "workspaces"):
        existing_ws = _columns(engine, "workspaces")
        upgrades_ws = {
            "organization_id": "ALTER TABLE workspaces ADD COLUMN organization_id INTEGER",
            "slug": "ALTER TABLE workspaces ADD COLUMN slug VARCHAR",
            "type": "ALTER TABLE workspaces ADD COLUMN type VARCHAR DEFAULT 'Team'",
            "storage_quota_mb": "ALTER TABLE workspaces ADD COLUMN storage_quota_mb INTEGER DEFAULT 5000",
            "ai_monthly_quota": "ALTER TABLE workspaces ADD COLUMN ai_monthly_quota INTEGER DEFAULT 10000",
            "brand_logo": "ALTER TABLE workspaces ADD COLUMN brand_logo VARCHAR",
            "brand_color": "ALTER TABLE workspaces ADD COLUMN brand_color VARCHAR DEFAULT '#6366f1'",
        }
        with engine.begin() as conn:
            for column, statement in upgrades_ws.items():
                if column in existing_ws:
                    continue
                try:
                    conn.execute(text(statement))
                    logger.info("Added missing workspaces.%s column", column)
                except Exception as exc:
                    logger.warning("Could not add workspaces.%s column: %s", column, exc)
