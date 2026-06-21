"""
Analytics Async Tasks - Phase 7
Celery tasks for analytics calculations and report generation
"""
import logging
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import get_settings
from tasks.celery_app import celery_app
from auth.models import User
from models.crm import Deal
from services.winloss_service import WinLossService
from services.sales_cycle_service import SalesCycleService
from services.forecast_service import ForecastService
from services.territory_service import TerritoryService

logger = logging.getLogger(__name__)

# Database session
engine = create_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine)

# =================== WIN/LOSS TASKS ===================

@celery_app.task(bind=True, name="tasks.analytics.analyze_deal_outcome")
def analyze_deal_outcome(self, deal_id: int, user_id: int, outcome: str, competitor: str = None):
    """Analyze a closed deal and extract patterns"""
    db = SessionLocal()
    try:
        logger.info(f"📊 [Task] Analyzing deal outcome: deal_id={deal_id}, outcome={outcome}")
        
        analysis = WinLossService.analyze_closed_deal(
            db, user_id, deal_id, outcome, competitor
        )
        
        if analysis:
            logger.info(f"✅ [Task] Deal analysis complete: {analysis.root_cause}")
            return {
                "status": "success",
                "analysis_id": analysis.id,
                "root_cause": analysis.root_cause,
                "factors": analysis.key_factors
            }
        else:
            logger.error(f"❌ [Task] Deal analysis failed")
            return {"status": "error", "message": "Analysis failed"}
            
    except Exception as e:
        logger.error(f"❌ [Task] Exception: {e}", exc_info=True)
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

# =================== SALES CYCLE TASKS ===================

@celery_app.task(bind=True, name="tasks.analytics.calculate_cycle_metrics")
def calculate_cycle_metrics(self, user_id: int, period_type: str = "monthly"):
    """Calculate sales cycle metrics"""
    db = SessionLocal()
    try:
        logger.info(f"📊 [Task] Calculating cycle metrics: user_id={user_id}, period={period_type}")
        
        metrics = SalesCycleService.calculate_cycle_metrics(db, user_id, period_type)
        
        if metrics:
            logger.info(f"✅ [Task] Cycle metrics: {metrics.avg_sales_cycle_days:.1f} days avg")
            return {
                "status": "success",
                "metrics_id": metrics.id,
                "avg_cycle_days": metrics.avg_sales_cycle_days,
                "deals_closed": metrics.deals_closed
            }
        else:
            return {"status": "error", "message": "Metrics calculation failed"}
            
    except Exception as e:
        logger.error(f"❌ [Task] Exception: {e}", exc_info=True)
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

# =================== FORECAST TASKS ===================

@celery_app.task(bind=True, name="tasks.analytics.calculate_forecast_accuracy")
def calculate_forecast_accuracy(self, user_id: int, month: str):
    """Calculate forecast accuracy for a month"""
    db = SessionLocal()
    try:
        logger.info(f"📊 [Task] Calculating forecast accuracy: month={month}")
        
        forecast = ForecastService.calculate_month_accuracy(db, user_id, month)
        
        if forecast:
            logger.info(f"✅ [Task] Forecast accuracy: {forecast.forecast_accuracy_pct:.1f}%")
            return {
                "status": "success",
                "forecast_id": forecast.id,
                "accuracy_pct": forecast.forecast_accuracy_pct,
                "actual_revenue": forecast.actual_revenue
            }
        else:
            return {"status": "error", "message": "Forecast calculation failed"}
            
    except Exception as e:
        logger.error(f"❌ [Task] Exception: {e}", exc_info=True)
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

# =================== TERRITORY TASKS ===================

@celery_app.task(bind=True, name="tasks.analytics.calculate_territory_metrics")
def calculate_territory_metrics(self, user_id: int, territory_name: str):
    """Calculate territory metrics"""
    db = SessionLocal()
    try:
        logger.info(f"📊 [Task] Calculating territory metrics: territory={territory_name}")
        
        metrics = TerritoryService.create_territory_metrics(db, user_id, territory_name)
        
        if metrics:
            logger.info(f"✅ [Task] Territory metrics: {metrics.win_rate_pct:.1f}% win rate")
            return {
                "status": "success",
                "metrics_id": metrics.id,
                "win_rate_pct": metrics.win_rate_pct,
                "pipeline_value": metrics.pipeline_value,
                "opportunity_score": metrics.opportunity_score
            }
        else:
            return {"status": "error", "message": "Territory calculation failed"}
            
    except Exception as e:
        logger.error(f"❌ [Task] Exception: {e}", exc_info=True)
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

# =================== PERIODIC TASKS ===================

@celery_app.task(bind=True, name="tasks.analytics.periodic_analytics_refresh")
def periodic_analytics_refresh(self):
    """Periodic task: Refresh all analytics for all users daily"""
    db = SessionLocal()
    try:
        logger.info("📊 [Periodic Task] Starting daily analytics refresh...")
        
        users = db.query(User).all()
        success_count = 0
        
        for user in users:
            try:
                # Calculate cycle metrics
                SalesCycleService.calculate_cycle_metrics(db, user.id, "monthly")
                
                # Calculate forecast if it's month-end
                today = datetime.utcnow()
                if today.day >= 28:  # Near month end
                    month = today.strftime("%Y-%m")
                    ForecastService.calculate_month_accuracy(db, user.id, month)
                
                # Update territories
                # (assuming user has territories)
                territories = set()
                for deal in db.query(Deal).filter(Deal.user_id == user.id).all():
                    if hasattr(deal, 'territory') and deal.territory:
                        territories.add(deal.territory)
                
                for territory in territories:
                    TerritoryService.create_territory_metrics(db, user.id, territory)
                
                success_count += 1
                logger.info(f"✅ [Periodic] Analytics updated for user {user.id}")
                
            except Exception as e:
                logger.error(f"❌ [Periodic] User {user.id} failed: {e}")
        
        logger.info(f"✅ [Periodic Task] Daily refresh complete: {success_count}/{len(users)} users")
        return {"status": "success", "users_updated": success_count}
        
    except Exception as e:
        logger.error(f"❌ [Periodic Task] Exception: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, name="tasks.analytics.generate_analytics_report")
def generate_analytics_report(self, user_id: int):
    """Generate comprehensive monthly analytics report"""
    db = SessionLocal()
    try:
        logger.info(f"📊 [Task] Generating analytics report for user {user_id}")
        
        report = {
            "user_id": user_id,
            "generated_at": datetime.utcnow().isoformat(),
            "sections": {}
        }
        
        # Win/Loss summary
        win_loss = WinLossService.get_win_loss_summary(db, user_id)
        report["sections"]["win_loss_summary"] = win_loss
        
        # Sales cycle metrics
        cycle_metrics = SalesCycleService.calculate_cycle_metrics(db, user_id, "monthly")
        if cycle_metrics:
            report["sections"]["sales_cycle"] = {
                "avg_cycle_days": cycle_metrics.avg_sales_cycle_days,
                "deals_closed": cycle_metrics.deals_closed
            }
        
        # Forecast accuracy
        forecast_trends = ForecastService.get_accuracy_trends(db, user_id)
        report["sections"]["forecast_trends"] = forecast_trends
        
        # Territory analysis
        territory_comparison = TerritoryService.get_territory_comparison(db, user_id)
        report["sections"]["territories"] = territory_comparison
        
        logger.info(f"✅ [Task] Report generated: {len(report['sections'])} sections")
        return {"status": "success", "report": report}
        
    except Exception as e:
        logger.error(f"❌ [Task] Exception: {e}", exc_info=True)
        db.rollback()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()

logger.info("✅ Analytics tasks loaded successfully")
