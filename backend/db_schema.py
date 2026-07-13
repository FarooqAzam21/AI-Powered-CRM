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
