#!/usr/bin/env python3
"""
AI CRM BACKEND - Startup Script
Production-grade FastAPI application
"""
import sys
import os
import logging
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Verify all required packages are installed"""
    logger.info("🔍 Checking dependencies...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "python-jose",
        "passlib",
        "python-dotenv",
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            logger.info(f"✅ {package}")
        except ImportError:
            logger.warning(f"❌ {package}")
            missing.append(package)
    
    if missing:
        logger.error(f"\n❌ Missing packages: {', '.join(missing)}")
        logger.error(f"Run: pip install {' '.join(missing)}")
        return False
    
    return True

def check_database():
    """Initialize database if needed"""
    logger.info("📦 Checking database...")
    
    try:
        from database import engine, Base
        from auth.models import User, Contact, Lead, Email, Notification
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return False

def check_ollama():
    """Check if Ollama is available"""
    logger.info("🤖 Checking Ollama AI...")
    
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            logger.info("✅ Ollama is running")
            return True
        else:
            logger.warning("⚠️  Ollama not responding")
            return False
    except:
        logger.warning("⚠️  Ollama not available (optional)")
        logger.info("    Install: https://ollama.ai")
        logger.info("    Run: ollama pull tinyllama && ollama serve")
        return False

def start_server():
    """Start the FastAPI server"""
    logger.info("🚀 Starting FastAPI server...")
    
    try:
        import uvicorn
        
        config = uvicorn.Config(
            app="app_new:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info",
        )
        
        server = uvicorn.Server(config)
        
        logger.info("\n" + "="*60)
        logger.info("✅ AI CRM BACKEND RUNNING")
        logger.info("="*60)
        logger.info("📍 API: http://127.0.0.1:8000")
        logger.info("📚 Docs: http://127.0.0.1:8000/docs")
        logger.info("="*60 + "\n")
        
        import asyncio
        asyncio.run(server.serve())
        
    except Exception as e:
        logger.error(f"❌ Server startup failed: {e}")
        sys.exit(1)

def main():
    """Main startup sequence"""
    logger.info("\n" + "="*60)
    logger.info("AI CRM BACKEND - STARTUP CHECK")
    logger.info("="*60 + "\n")
    
    # 1. Check dependencies
    if not check_dependencies():
        logger.error("❌ Please install missing packages")
        sys.exit(1)
    
    logger.info()
    
    # 2. Check database
    if not check_database():
        logger.error("❌ Database initialization failed")
        sys.exit(1)
    
    logger.info()
    
    # 3. Check optional dependencies
    check_ollama()
    
    logger.info()
    
    # 4. Start server
    start_server()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n🛑 Shutting down...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
