import logging
import os
import time
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from config.settings import get_settings

logger = logging.getLogger("database.sql")
settings = get_settings()

Path("data").mkdir(exist_ok=True)

DATABASE_URL = os.getenv("DATABASE_URL", settings.database_url)
is_sqlite = DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
    "future": True,
}

if not is_sqlite:
    engine_kwargs.update({
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout,
        "pool_recycle": settings.db_pool_recycle,
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
Base = declarative_base()


@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_start_time", []).append(time.time())


@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total_time_ms = 0.0
    try:
        start_time = conn.info["query_start_time"].pop()
        total_time_ms = (time.time() - start_time) * 1000
    except (IndexError, KeyError):
        pass

    try:
        from services.metrics_service import metrics_service
        metrics_service.inc("db_queries_total")
        metrics_service.observe_latency("db_query_duration_seconds", total_time_ms / 1000.0)

        if total_time_ms > settings.slow_query_threshold_ms:
            metrics_service.inc("db_slow_queries_total")
            logger.warning(
                f"Slow Query Detected ({total_time_ms:.2f}ms): {statement[:300]}"
            )
    except Exception:
        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
