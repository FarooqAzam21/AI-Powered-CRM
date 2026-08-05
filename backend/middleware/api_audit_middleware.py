import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from sqlalchemy.orm import Session
from database import SessionLocal
from auth.models import AuditLog

logger = logging.getLogger(__name__)

class APIAuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware that captures API requests executed via API keys,
    measures execution latency, and logs details to the AuditLog database.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Execute down the middleware chain
        response = await call_next(request)
        
        # Extract API key information populated in request.state during auth
        api_key_id = getattr(request.state, "api_key_id", None)
        workspace_id = getattr(request.state, "workspace_id", None)
        
        if api_key_id:
            latency = int((time.time() - start_time) * 1000) # latency in ms
            
            db = SessionLocal()
            try:
                ip_address = request.client.host if request.client else None
                details = (
                    f"API Key ID: {api_key_id} | "
                    f"Method: {request.method} | "
                    f"Status Code: {response.status_code} | "
                    f"Latency: {latency}ms"
                )
                
                audit = AuditLog(
                    action="API_REQUEST",
                    resource=request.url.path,
                    status="ALLOWED" if response.status_code < 400 else "DENIED",
                    workspace_id=workspace_id,
                    details=details,
                    ip_address=ip_address
                )
                db.add(audit)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to log API request audit: {e}")
            finally:
                db.close()
                
        return response
