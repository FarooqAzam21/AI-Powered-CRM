#!/usr/bin/env python3
"""
PHASE 4 SETUP & VERIFICATION SCRIPT
Checks all dependencies and confirms system readiness
"""
import sys
from pathlib import Path
import subprocess
import os

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def check_python_version():
    """Verify Python 3.8+"""
    print("🔍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor} (OK)")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor} (Need 3.8+)")
        return False

def check_pip_packages():
    """Verify required packages"""
    print("\n🔍 Checking pip packages...")
    required = {
        "fastapi": "FastAPI",
        "uvicorn": "Uvicorn",
        "sqlalchemy": "SQLAlchemy",
        "pydantic": "Pydantic",
        "python-jose": "JWT Library",
        "passlib": "Password Hashing",
        "python-dotenv": "Environment",
        "redis": "Redis Client",
        "celery": "Celery",
    }
    
    missing = []
    for package, name in required.items():
        try:
            __import__(package)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} - Install with: pip install {package}")
            missing.append(package)
    
    return len(missing) == 0, missing

def check_database():
    """Verify database"""
    print("\n🔍 Checking database...")
    try:
        db_path = Path(__file__).parent / "data" / "app.db"
        if db_path.exists():
            print(f"✅ Database found: {db_path}")
            return True
        else:
            print(f"⚠️  Database not found at {db_path}")
            print("   Run: python init_db_simple.py")
            return False
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

def check_redis():
    """Verify Redis connectivity"""
    print("\n🔍 Checking Redis...")
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running and accessible")
        return True
    except Exception as e:
        print(f"⚠️  Redis not available: {e}")
        print("   Start with: redis-server")
        print("   Or on Windows WSL: wsl redis-server")
        return False

def check_celery():
    """Verify Celery configuration"""
    print("\n🔍 Checking Celery...")
    try:
        from tasks.celery_app import celery_app
        print("✅ Celery app loaded successfully")
        
        # Try to ping broker
        try:
            insp = celery_app.control.inspect()
            stats = insp.stats()
            if stats:
                print(f"✅ Celery workers connected: {len(stats)} worker(s)")
                return True
            else:
                print("⚠️  No Celery workers running")
                print("   Start with: celery -A tasks.celery_app worker --loglevel=info")
                return False
        except Exception as e:
            print(f"⚠️  No workers connected yet: {e}")
            return False
    except Exception as e:
        print(f"❌ Celery check failed: {e}")
        return False

def check_ollama():
    """Verify Ollama (optional)"""
    print("\n🔍 Checking Ollama...")
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama is running")
            return True
    except Exception:
        pass
    
    print("⚠️  Ollama not available (optional)")
    print("   Start with: ollama serve")
    return False

def check_file_structure():
    """Verify all Phase 4 files exist"""
    print("\n🔍 Checking Phase 4 file structure...")
    backend_path = Path(__file__).parent
    
    required_files = {
        "tasks/celery_app.py": "Celery configuration",
        "tasks/email_tasks.py": "Email tasks",
        "tasks/ai_tasks.py": "AI tasks",
        "tasks/lead_tasks.py": "Lead tasks",
        "tasks/campaign_tasks.py": "Campaign tasks",
        "tasks/auth_tasks.py": "Auth tasks",
        "routers/task_router.py": "Task router",
        "test_celery_tasks.py": "Test suite",
    }
    
    missing = []
    for file_path, description in required_files.items():
        full_path = backend_path / file_path
        if full_path.exists():
            print(f"✅ {description}: {file_path}")
        else:
            print(f"❌ {description}: {file_path} NOT FOUND")
            missing.append(file_path)
    
    return len(missing) == 0, missing

def print_summary(results):
    """Print verification summary"""
    print_header("VERIFICATION SUMMARY")
    
    python_ok = results.get("python", False)
    packages_ok, missing_packages = results.get("packages", (False, []))
    db_ok = results.get("database", False)
    redis_ok = results.get("redis", False)
    celery_ok = results.get("celery", False)
    ollama_ok = results.get("ollama", False)
    files_ok, missing_files = results.get("files", (False, []))
    
    print("Core Requirements:")
    print(f"  {'✅' if python_ok else '❌'} Python 3.8+")
    print(f"  {'✅' if packages_ok else '❌'} Python packages")
    print(f"  {'✅' if db_ok else '⚠️ '} Database")
    
    print("\nAsync Infrastructure:")
    print(f"  {'✅' if redis_ok else '⚠️ '} Redis")
    print(f"  {'✅' if celery_ok else '⚠️ '} Celery workers")
    
    print("\nOptional:")
    print(f"  {'✅' if ollama_ok else '⚠️ '} Ollama (AI model)")
    
    print("\nPhase 4 Files:")
    print(f"  {'✅' if files_ok else '❌'} All task files present")
    
    # Determine readiness
    readiness = 100
    if not python_ok: readiness -= 20
    if not packages_ok: readiness -= 20
    if not db_ok: readiness -= 10
    if not files_ok: readiness -= 10
    if not redis_ok: readiness -= 10
    if not celery_ok: readiness -= 10
    
    print(f"\nSystem Readiness: {readiness}%")
    
    if readiness >= 90:
        print("🚀 READY TO START PHASE 4!")
    elif readiness >= 70:
        print("⚠️  PARTIALLY READY - Missing optional components")
    else:
        print("❌ NOT READY - Please install missing components")
    
    # Print next steps
    print_header("NEXT STEPS")
    
    if not packages_ok and missing_packages:
        print(f"1. Install missing packages:")
        for pkg in missing_packages:
            print(f"   pip install {pkg}")
        print()
    
    if not db_ok:
        print("2. Initialize database:")
        print("   python init_db_simple.py\n")
    
    if not redis_ok:
        print("3. Start Redis server:")
        print("   redis-server")
        print("   (or on Windows WSL: wsl redis-server)\n")
    
    if not celery_ok:
        print("4. Start Celery worker (in separate terminal):")
        print("   celery -A tasks.celery_app worker --loglevel=info\n")
    
    print("5. Start backend server:")
    print("   python app_new.py\n")
    
    print("6. Test the system:")
    print("   python test_celery_tasks.py\n")
    
    if not ollama_ok:
        print("7. (Optional) Start Ollama for AI features:")
        print("   ollama serve\n")

def main():
    """Run all checks"""
    print_header("PHASE 4 SETUP & VERIFICATION")
    
    results = {}
    
    # Run checks
    results["python"] = check_python_version()
    packages_ok, missing = check_pip_packages()
    results["packages"] = (packages_ok, missing)
    results["database"] = check_database()
    results["redis"] = check_redis()
    results["celery"] = check_celery()
    results["ollama"] = check_ollama()
    files_ok, missing = check_file_structure()
    results["files"] = (files_ok, missing)
    
    # Print summary
    print_summary(results)
    
    return 0 if results["python"] and packages_ok and files_ok else 1

if __name__ == "__main__":
    sys.exit(main())
