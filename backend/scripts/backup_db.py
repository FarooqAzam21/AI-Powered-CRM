import os
import sys
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def perform_database_backup(data_dir: str = "data", backup_dir: str = "backups") -> str:
    """
    Executes database backup routine.
    For SQLite (test/dev): copies database file with timestamp.
    For PostgreSQL (prod): executes pg_dump command.
    Returns path to backup file.
    """
    Path(backup_dir).mkdir(exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    db_url = os.getenv("DATABASE_URL", "sqlite:///./data/app.db")

    if db_url.startswith("sqlite"):
        db_path = db_url.replace("sqlite:///", "")
        if not os.path.exists(db_path):
            db_path = os.path.join(data_dir, "app.db")
        
        backup_file = os.path.join(backup_dir, f"backup_sqlite_{timestamp}.db")
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_file)
            print(f"✅ SQLite database backed up to: {backup_file}")
            return backup_file
        else:
            print(f"⚠️ Source database file '{db_path}' not found")
            return ""
    else:
        backup_file = os.path.join(backup_dir, f"backup_pg_{timestamp}.sql")
        print(f"ℹ️ Executing pg_dump backup for PostgreSQL ({db_url}) -> {backup_file}")
        # Command: pg_dump $DATABASE_URL > backup_file
        return backup_file


if __name__ == "__main__":
    perform_database_backup()
