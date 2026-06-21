"""
Dashboard Event Tasks - Phase 8
Celery tasks for generating and broadcasting real-time dashboard events
"""
import logging
import json
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import get_settings
from tasks.celery_app import celery_app
from auth.models import User, Deal, Activity, AIRecommendation, TerritoryMetrics
from services.dashboard_service import DashboardService
from ws_manager.socket import manager

logger = logging.getLogger(__name__)

# Database session
_settings = get_settings()
engine = create_engine(_settings.database_url)
SessionLocal = sessionmaker(bind=engine)

# =================== REAL-TIME EVENT TASKS ===================

@celery_app.task(bind=True, name="tasks.dashboard.broadcast_deal_update")
def broadcast_deal_update(self, deal_id: int, user_id: int):
    """Broadcast deal update to connected clients"""
    db = SessionLocal()
    try:
        logger.info(f"📡 [Dashboard] Broadcasting deal update: deal_id={deal_id}")
        
        event = DashboardService.generate_deal_update_event(db, deal_id)
        if event:
            # Convert to dict for broadcasting
            event_data = event.dict()
            
            # Broadcast through WebSocket manager
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(
                    manager.broadcast_deal_update(deal_id, event_data)
                )
            finally:
                loop.close()
            
            logger.info(f"✅ [Dashboard] Deal update broadcasted")
            return {"status": "success", "deal_id": deal_id}
        else:
            return {"status": "error", "message": "Deal not found"}
            
    except Exception as e:
        logger.error(f"❌ [Dashboard] Broadcast error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.dashboard.broadcast_deal_closed")
def broadcast_deal_closed(self, deal_id: int, user_id: int):
    """Broadcast deal closed event"""
    db = SessionLocal()
    try:
        logger.info(f"📡 [Dashboard] Broadcasting deal closed: deal_id={deal_id}")
        
        event = DashboardService.generate_deal_closed_event(db, deal_id)
        if event:
            event_data = event.dict()
            
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(
                    manager.broadcast_to_channel("deals", event_data)
                )
            finally:
                loop.close()
            
            logger.info(f"✅ [Dashboard] Deal closed broadcasted")
            return {"status": "success", "deal_id": deal_id}
        else:
            return {"status": "error", "message": "Deal not found"}
            
    except Exception as e:
        logger.error(f"❌ [Dashboard] Broadcast error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.dashboard.broadcast_territory_alert")
def broadcast_territory_alert(self, territory_name: str, user_id: int):
    """Broadcast territory alerts"""
    db = SessionLocal()
    try:
        logger.info(f"📡 [Dashboard] Broadcasting territory alert: territory={territory_name}")
        
        territory = db.query(TerritoryMetrics).filter(
            TerritoryMetrics.territory_name == territory_name,
            TerritoryMetrics.user_id == user_id
        ).first()
        
        if territory:
            alerts = DashboardService.generate_territory_alert(territory)
            
            for alert in alerts:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    loop.run_until_complete(
                        manager.broadcast_territory_update(territory_name, alert)
                    )
                finally:
                    loop.close()
            
            logger.info(f"✅ [Dashboard] Territory alerts broadcasted: {len(alerts)} alerts")
            return {"status": "success", "alerts_count": len(alerts)}
        else:
            return {"status": "error", "message": "Territory not found"}
            
    except Exception as e:
        logger.error(f"❌ [Dashboard] Broadcast error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.dashboard.broadcast_forecast_alert")
def broadcast_forecast_alert(self, user_id: int):
    """Broadcast forecast status alert"""
    db = SessionLocal()
    try:
        logger.info(f"📡 [Dashboard] Broadcasting forecast alert: user_id={user_id}")
        
        alert = DashboardService.generate_forecast_alert(db, user_id)
        
        if alert:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(
                    manager.broadcast_metric_update("forecast", user_id, alert)
                )
            finally:
                loop.close()
            
            logger.info(f"✅ [Dashboard] Forecast alert broadcasted: {alert.get('status')}")
            return {"status": "success", "alert": alert}
        else:
            return {"status": "error", "message": "No forecast data"}
            
    except Exception as e:
        logger.error(f"❌ [Dashboard] Broadcast error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.dashboard.broadcast_activity_event")
def broadcast_activity_event(self, activity_id: int):
    """Broadcast activity created event"""
    db = SessionLocal()
    try:
        logger.info(f"📡 [Dashboard] Broadcasting activity event: activity_id={activity_id}")
        
        event = DashboardService.generate_activity_event(db, activity_id)
        
        if event:
            event_data = event.dict()
            
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(
                    manager.broadcast_to_channel("activities", event_data)
                )
            finally:
                loop.close()
            
            logger.info(f"✅ [Dashboard] Activity event broadcasted")
            return {"status": "success", "activity_id": activity_id}
        else:
            return {"status": "error", "message": "Activity not found"}
            
    except Exception as e:
        logger.error(f"❌ [Dashboard] Broadcast error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.dashboard.broadcast_recommendation_event")
def broadcast_recommendation_event(self, recommendation_id: int):
    """Broadcast recommendation generated event"""
    db = SessionLocal()
    try:
        logger.info(f"📡 [Dashboard] Broadcasting recommendation event: rec_id={recommendation_id}")
        
        event = DashboardService.generate_recommendation_event(db, recommendation_id)
        
        if event:
            event_data = event.dict()
            
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(
                    manager.broadcast_to_channel("analytics", event_data)
                )
            finally:
                loop.close()
            
            logger.info(f"✅ [Dashboard] Recommendation event broadcasted")
            return {"status": "success", "recommendation_id": recommendation_id}
        else:
            return {"status": "error", "message": "Recommendation not found"}
            
    except Exception as e:
        logger.error(f"❌ [Dashboard] Broadcast error: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

# =================== PERIODIC REFRESH TASKS ===================

@celery_app.task(bind=True, name="tasks.dashboard.periodic_metrics_refresh")
def periodic_metrics_refresh(self):
    """Periodic task: Refresh dashboard metrics for all connected users every 30 seconds"""
    db = SessionLocal()
    try:
        logger.info("📡 [Periodic] Refreshing dashboard metrics for all users")
        
        # Get all connected users
        connected_user_ids = list(manager.active_connections.keys())
        
        if not connected_user_ids:
            logger.debug("No connected users")
            return {"status": "success", "users_updated": 0}
        
        updated_count = 0
        
        for user_id in connected_user_ids:
            try:
                # Get current metrics
                metrics = DashboardService.get_dashboard_metrics(db, user_id)
                
                if metrics:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        loop.run_until_complete(
                            manager.send_personal_message(
                                user_id,
                                {
                                    "type": "metrics_update",
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "data": metrics.dict()
                                }
                            )
                        )
                        updated_count += 1
                    finally:
                        loop.close()
                        
            except Exception as e:
                logger.error(f"❌ Metrics refresh error for user {user_id}: {e}")
        
        logger.info(f"✅ [Periodic] Metrics refreshed for {updated_count}/{len(connected_user_ids)} users")
        return {"status": "success", "users_updated": updated_count}
        
    except Exception as e:
        logger.error(f"❌ [Periodic] Metrics refresh failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.dashboard.periodic_pipeline_refresh")
def periodic_pipeline_refresh(self):
    """Periodic task: Refresh pipeline snapshots every 60 seconds"""
    db = SessionLocal()
    try:
        logger.info("📡 [Periodic] Refreshing pipeline snapshots")
        
        connected_user_ids = list(manager.active_connections.keys())
        updated_count = 0
        
        for user_id in connected_user_ids:
            try:
                # Get pipeline snapshot
                snapshot = DashboardService.get_pipeline_snapshot(db, user_id)
                
                if snapshot:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        loop.run_until_complete(
                            manager.send_personal_message(
                                user_id,
                                {
                                    "type": "pipeline_update",
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "data": snapshot.dict()
                                }
                            )
                        )
                        updated_count += 1
                    finally:
                        loop.close()
                        
            except Exception as e:
                logger.error(f"❌ Pipeline refresh error for user {user_id}: {e}")
        
        logger.info(f"✅ [Periodic] Pipeline refreshed for {updated_count} users")
        return {"status": "success", "users_updated": updated_count}
        
    except Exception as e:
        logger.error(f"❌ [Periodic] Pipeline refresh failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.dashboard.periodic_territory_refresh")
def periodic_territory_refresh(self):
    """Periodic task: Refresh territory snapshots every 60 seconds"""
    db = SessionLocal()
    try:
        logger.info("📡 [Periodic] Refreshing territory snapshots")
        
        connected_user_ids = list(manager.active_connections.keys())
        updated_count = 0
        
        for user_id in connected_user_ids:
            try:
                # Get territory snapshot
                snapshot = DashboardService.get_territory_snapshot(db, user_id)
                
                if snapshot:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        loop.run_until_complete(
                            manager.send_personal_message(
                                user_id,
                                {
                                    "type": "territory_update",
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "data": snapshot.dict()
                                }
                            )
                        )
                        updated_count += 1
                    finally:
                        loop.close()
                        
            except Exception as e:
                logger.error(f"❌ Territory refresh error for user {user_id}: {e}")
        
        logger.info(f"✅ [Periodic] Territory refreshed for {updated_count} users")
        return {"status": "success", "users_updated": updated_count}
        
    except Exception as e:
        logger.error(f"❌ [Periodic] Territory refresh failed: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

logger.info("✅ Dashboard event tasks loaded successfully")
