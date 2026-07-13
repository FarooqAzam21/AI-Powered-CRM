"""
Analytics Router - Phase 7
REST endpoints for advanced analytics and insights
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from auth.dependencies import get_current_user_model
from auth.models import User
from services.winloss_service import WinLossService
from services.sales_cycle_service import SalesCycleService
from services.forecast_service import ForecastService
from services.territory_service import TerritoryService
from database import SessionLocal
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =================== WIN/LOSS ANALYSIS ENDPOINTS ===================

@router.post("/deals/{deal_id}/record-outcome")
async def record_deal_outcome(
    deal_id: int,
    outcome: str,  # 'won' or 'lost'
    competitor: Optional[str] = None,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Record a deal outcome (won/lost) and analyze it"""
    try:
        if outcome not in ["won", "lost"]:
            raise HTTPException(status_code=400, detail="Outcome must be 'won' or 'lost'")
        
        analysis = WinLossService.analyze_closed_deal(
            db, current_user.id, deal_id, outcome, competitor
        )
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Deal not found or analysis failed")
        
        return {
            "status": "success",
            "outcome": analysis.outcome,
            "root_cause": analysis.root_cause,
            "key_factors": analysis.key_factors,
            "lessons_learned": analysis.lessons_learned
        }
    except Exception as e:
        logger.error(f"❌ Outcome recording failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/win-loss-summary")
async def get_win_loss_summary(
    days: int = Query(90),
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get win/loss analysis summary"""
    try:
        summary = WinLossService.get_win_loss_summary(db, current_user.id, days)
        return {
            "status": "success",
            "data": summary
        }
    except Exception as e:
        logger.error(f"❌ Summary retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/winning-factors")
async def get_winning_factors(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get top winning factors"""
    try:
        summary = WinLossService.get_win_loss_summary(db, current_user.id)
        return {
            "status": "success",
            "factors": summary.get("top_win_factors", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/losing-factors")
async def get_losing_factors(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get top losing factors"""
    try:
        summary = WinLossService.get_win_loss_summary(db, current_user.id)
        return {
            "status": "success",
            "factors": summary.get("top_loss_factors", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/competitor-analysis")
async def get_competitor_analysis(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Analyze losses by competitor"""
    try:
        competitors = WinLossService.get_competitor_analysis(db, current_user.id)
        return {
            "status": "success",
            "competitors": competitors
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =================== SALES CYCLE ENDPOINTS ===================

@router.post("/sales-cycles/calculate")
async def calculate_sales_cycle_metrics(
    period_type: str = Query("monthly"),  # monthly, quarterly, yearly
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Calculate sales cycle metrics for a period"""
    try:
        if period_type not in ["monthly", "quarterly", "yearly"]:
            raise HTTPException(status_code=400, detail="Invalid period_type")
        
        metrics = SalesCycleService.calculate_cycle_metrics(db, current_user.id, period_type)
        
        if not metrics:
            raise HTTPException(status_code=500, detail="Calculation failed")
        
        return {
            "status": "success",
            "period_type": metrics.period_type,
            "avg_cycle_days": metrics.avg_sales_cycle_days,
            "median_cycle_days": metrics.median_sales_cycle_days,
            "deals_started": metrics.deals_started,
            "deals_closed": metrics.deals_closed,
            "stage_durations": metrics.avg_stage_durations,
            "conversion_rates": metrics.stage_conversion_rates
        }
    except Exception as e:
        logger.error(f"❌ Cycle calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sales-cycles")
async def get_sales_cycle_metrics(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get latest sales cycle metrics"""
    try:
        metrics = SalesCycleService.calculate_cycle_metrics(db, current_user.id)
        if not metrics:
            raise HTTPException(status_code=404, detail="No cycle metrics found")
        
        return {
            "status": "success",
            "data": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/velocity")
async def get_sales_velocity(
    days: int = Query(30),
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get sales velocity (deals/revenue per day)"""
    try:
        velocity = SalesCycleService.get_sales_velocity(db, current_user.id, days)
        return {
            "status": "success",
            "data": velocity
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bottlenecks")
async def get_bottlenecks(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Identify pipeline bottlenecks"""
    try:
        bottlenecks = SalesCycleService.get_bottleneck_analysis(db, current_user.id)
        return {
            "status": "success",
            "bottlenecks": bottlenecks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =================== FORECAST ACCURACY ENDPOINTS ===================

@router.post("/forecast/record")
async def record_forecast(
    month: str,  # YYYY-MM
    forecasted_revenue: float,
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Record a monthly forecast"""
    try:
        forecast = ForecastService.record_forecast(db, current_user.id, month, forecasted_revenue)
        if not forecast:
            raise HTTPException(status_code=500, detail="Forecast recording failed")
        
        return {
            "status": "success",
            "forecast_month": forecast.forecast_month,
            "forecasted_revenue": forecast.forecasted_revenue
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/forecast/{month}/close")
async def close_forecast_month(
    month: str,  # YYYY-MM
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Close out a month and calculate forecast accuracy"""
    try:
        forecast = ForecastService.calculate_month_accuracy(db, current_user.id, month)
        if not forecast:
            raise HTTPException(status_code=404, detail="Forecast not found")
        
        return {
            "status": "success",
            "month": forecast.forecast_month,
            "forecasted": forecast.forecasted_revenue,
            "actual": forecast.actual_revenue,
            "accuracy_pct": forecast.forecast_accuracy_pct,
            "variance_reasons": forecast.variance_reasons
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast-accuracy")
async def get_forecast_accuracy(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get forecast accuracy trends"""
    try:
        trends = ForecastService.get_accuracy_trends(db, current_user.id)
        return {
            "status": "success",
            "trends": trends
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast-drivers")
async def get_forecast_drivers(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Identify forecast accuracy drivers"""
    try:
        drivers = ForecastService.identify_forecast_drivers(db, current_user.id)
        return {
            "status": "success",
            "drivers": drivers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =================== TERRITORY ENDPOINTS ===================

@router.post("/territories/{territory_name}")
async def create_territory(
    territory_name: str,
    territory_type: str = Query("geographic"),
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Create or update territory metrics"""
    try:
        metrics = TerritoryService.create_territory_metrics(
            db, current_user.id, territory_name, territory_type
        )
        if not metrics:
            raise HTTPException(status_code=500, detail="Territory creation failed")
        
        return {
            "status": "success",
            "territory": metrics.territory_name,
            "win_rate_pct": metrics.win_rate_pct,
            "pipeline_value": metrics.pipeline_value,
            "opportunity_score": metrics.opportunity_score,
            "risk_score": metrics.risk_score
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/territories")
async def list_territories(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Compare all territories"""
    try:
        comparison = TerritoryService.get_territory_comparison(db, current_user.id)
        return {
            "status": "success",
            "data": comparison
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/opportunity-analysis")
async def get_opportunity_analysis(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get territory opportunity analysis"""
    try:
        comparison = TerritoryService.get_territory_comparison(db, current_user.id)
        return {
            "status": "success",
            "opportunities": comparison.get("opportunities", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk-analysis")
async def get_risk_analysis(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get territory risk analysis"""
    try:
        comparison = TerritoryService.get_territory_comparison(db, current_user.id)
        return {
            "status": "success",
            "at_risk": comparison.get("at_risk", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/optimization-recommendations")
async def get_optimization_recommendations(
    current_user: User = Depends(get_current_user_model),
    db: Session = Depends(get_db)
):
    """Get territory optimization recommendations"""
    try:
        recommendations = TerritoryService.get_optimization_recommendations(db, current_user.id)
        return {
            "status": "success",
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

logger.info("✅ Analytics router loaded successfully")
