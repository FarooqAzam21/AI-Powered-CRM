"""
WebSocket Router - Phase 8
Real-time WebSocket endpoints for live dashboard streaming
"""
import logging
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from auth.dependencies import get_current_user_model
from auth.models import User
from database import SessionLocal
from ws_manager.socket import manager
from websocket.dashboard_models import (
    SubscriptionMessage, ConnectionEstablishedEvent,
    SubscriptionConfirmedEvent, ErrorEvent
)
from services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["WebSocket"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =================== WEBSOCKET ENDPOINTS ===================

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, db: Session = Depends(get_db)):
    """
    WebSocket endpoint for real-time dashboard
    Connection URL: ws://localhost:8000/api/v1/ws/{user_id}
    """
    try:
        # Connect
        await manager.connect(user_id, websocket)
        logger.info(f"🔗 WebSocket connected: user {user_id}")
        
        # Send connection confirmation
        connection_event = ConnectionEstablishedEvent(user_id=user_id)
        event_dict = connection_event.model_dump(mode='json')
        await manager.send_personal_message(user_id, event_dict)
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            logger.debug(f"📨 Received from {user_id}: {data}")
            
            # Handle subscription messages
            if data.get("action") == "subscribe":
                channel = data.get("channel")
                deal_ids = data.get("deal_ids")
                territories = data.get("territories")
                
                # Subscribe
                success = await manager.subscribe(
                    user_id, channel, deal_ids, territories
                )
                
                if success:
                    # Send confirmation
                    confirm_event = SubscriptionConfirmedEvent(
                        channel=channel,
                        deal_ids=deal_ids,
                        territories=territories
                    )
                    await manager.send_personal_message(user_id, confirm_event.model_dump(mode='json'))
                    logger.info(f"✅ User {user_id} subscribed to {channel}")
                else:
                    error_event = ErrorEvent(
                        error_code="SUBSCRIPTION_FAILED",
                        message="Failed to subscribe to channel"
                    )
                    await manager.send_personal_message(user_id, error_event.model_dump(mode='json'))
            
            elif data.get("action") == "unsubscribe":
                channel = data.get("channel")
                
                success = await manager.unsubscribe(user_id, channel)
                if success:
                    logger.info(f"✅ User {user_id} unsubscribed from {channel}")
                else:
                    logger.warning(f"⚠️  Unsubscribe failed for user {user_id}")
            
            elif data.get("action") == "ping":
                # Keep-alive ping
                await manager.send_personal_message(user_id, {"type": "pong"})
            
            else:
                logger.warning(f"⚠️  Unknown action: {data.get('action')}")
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"🔓 WebSocket disconnected: user {user_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}", exc_info=True)
        manager.disconnect(user_id)

# =================== METRICS ENDPOINTS ===================

@router.get("/ws/metrics/dashboard")
async def get_dashboard_metrics(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get current dashboard metrics snapshot"""
    try:
        metrics = DashboardService.get_dashboard_metrics(db, current_user.id)
        if not metrics:
            raise HTTPException(status_code=500, detail="Failed to retrieve metrics")
        
        return {
            "status": "success",
            "data": metrics.model_dump(mode='json')
        }
    except Exception as e:
        logger.error(f"❌ Metrics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ws/metrics/pipeline")
async def get_pipeline_snapshot(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get real-time pipeline snapshot"""
    try:
        snapshot = DashboardService.get_pipeline_snapshot(db, current_user.id)
        if not snapshot:
            raise HTTPException(status_code=500, detail="Failed to retrieve pipeline")
        
        return {
            "status": "success",
            "data": snapshot.model_dump(mode='json')
        }
    except Exception as e:
        logger.error(f"❌ Pipeline snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ws/metrics/territories")
async def get_territories_snapshot(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get real-time territory performance snapshot"""
    try:
        snapshot = DashboardService.get_territory_snapshot(db, current_user.id)
        if not snapshot:
            raise HTTPException(status_code=500, detail="Failed to retrieve territories")
        
        return {
            "status": "success",
            "data": snapshot.model_dump(mode='json')
        }
    except Exception as e:
        logger.error(f"❌ Territory snapshot failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =================== CONNECTION MANAGEMENT ENDPOINTS ===================

@router.get("/ws/connections")
async def get_connection_status(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get WebSocket connection status"""
    try:
        info = manager.get_connection_info()
        return {
            "status": "success",
            "data": info
        }
    except Exception as e:
        logger.error(f"❌ Connection status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ws/broadcast")
async def manual_broadcast(
    channel: str,
    message: dict,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """
    Manually broadcast message to channel (admin only)
    Requires admin role
    """
    try:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        await manager.broadcast_to_channel(channel, message)
        
        return {
            "status": "success",
            "message": f"Broadcast sent to {channel}",
            "channel": channel
        }
    except Exception as e:
        logger.error(f"❌ Broadcast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

logger.info("✅ WebSocket router loaded successfully")
