"""
Production-Grade Backend Application
FastAPI + SQLAlchemy + Redis + Celery
Optimized for 4GB RAM systems
"""
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from database import engine, Base, SessionLocal
from config.settings import Settings

# Initialize settings
settings = Settings()
DEBUG = settings.environment == "development"
API_V1_PREFIX = "/api/v1"
CORS_ORIGINS = settings.cors_origins
LOG_LEVEL = settings.log_level

# ================== LOGGING ==================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================== ROUTERS ==================
from auth.auth_router import router as auth_router

# ================== LIFESPAN EVENTS ==================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events
    """
    logger.info("🚀 Starting Backend Server...")
    
    # Initialize database
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
    
    yield
    
    logger.info("🛑 Shutting down Backend Server...")

# ================== FASTAPI APP ==================
app = FastAPI(
    title="AI Email Automation + CRM Platform",
    description="Production-grade AI-powered email and CRM system",
    version="2.0.0",
    debug=DEBUG,
    lifespan=lifespan
)

# ================== MIDDLEWARE ==================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)

# ================== HEALTH CHECKS ==================
@app.get("/health")
def health_check():
    """Application health check"""
    return {
        "status": "healthy",
        "service": "AI CRM Backend",
        "version": "2.0.0",
    }

@app.get("/api/status")
def api_status():
    """Detailed API status"""
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    return {
        "api": "online",
        "database": db_status,
        "debug": DEBUG,
    }

# ================== EXCEPTION HANDLERS ==================
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "error": True},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": True},
    )

# ================== INCLUDE ROUTERS ==================
app.include_router(auth_router, prefix=API_V1_PREFIX)

# Import and include other routers
try:
    from routers.contacts import router as contacts_router
    app.include_router(contacts_router, prefix=API_V1_PREFIX)
    logger.info("✅ Contacts router loaded")
except ImportError:
    logger.warning("⚠️  Contacts router not available")

try:
    from routers.task_router import router as tasks_router
    app.include_router(tasks_router, prefix=API_V1_PREFIX)
    logger.info("✅ Tasks router loaded")
except ImportError:
    logger.warning("⚠️  Tasks router not available")

try:
    from routers.deals import router as deals_router
    app.include_router(deals_router)
    logger.info("✅ Deals router loaded")
except ImportError:
    logger.warning("⚠️  Deals router not available")

try:
    from routers.analytics import router as analytics_router
    app.include_router(analytics_router)
    logger.info("✅ Analytics router loaded")
except ImportError:
    logger.warning("⚠️  Analytics router not available")

try:
    from routers.websocket import router as websocket_router
    app.include_router(websocket_router)
    logger.info("✅ WebSocket router loaded")
except ImportError:
    logger.warning("⚠️  WebSocket router not available")

try:
    from routers.campaigns import router as campaigns_router
    app.include_router(campaigns_router)
    logger.info("✅ Campaigns router loaded")
except ImportError:
    logger.warning("⚠️  Campaigns router not available")

logger.info("✅ Backend application initialized successfully")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("🚀 AI CRM BACKEND SERVER")
    print("="*60)
    print(f"Environment: {('DEVELOPMENT' if DEBUG else 'PRODUCTION').upper()}")
    print(f"API Prefix: {API_V1_PREFIX}")
    print(f"CORS Origins: {CORS_ORIGINS}")
    print("="*60 + "\n")
    
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=DEBUG,
        log_level=LOG_LEVEL.lower(),
    )
