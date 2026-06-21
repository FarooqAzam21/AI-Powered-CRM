"""
Forecast Accuracy Service - Phase 7
Tracks forecast vs actual and calculates accuracy metrics
"""
import logging
from datetime import datetime, timedelta
from calendar import monthrange
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from auth.models import ForecastAccuracy
from models.crm import Deal
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ForecastService:
    """Service for forecast accuracy tracking and analysis"""
    
    @staticmethod
    def record_forecast(db: Session, user_id: int, month: str, 
                       forecasted_revenue: float) -> Optional[ForecastAccuracy]:
        """
        Record monthly forecast
        month: 'YYYY-MM' format
        """
        try:
            logger.info(f"📊 Recording forecast for {month}: ${forecasted_revenue:.2f}")
            
            forecast = ForecastAccuracy(
                user_id=user_id,
                forecast_month=month,
                forecast_date=datetime.utcnow(),
                forecasted_revenue=forecasted_revenue,
                actual_revenue=0,  # Will be updated at month end
                forecast_accuracy_pct=0
            )
            
            db.add(forecast)
            db.commit()
            db.refresh(forecast)
            
            logger.info(f"✅ Forecast recorded")
            return forecast
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Forecast recording failed: {e}")
            return None
    
    @staticmethod
    def calculate_month_accuracy(db: Session, user_id: int, month: str) -> Optional[ForecastAccuracy]:
        """
        Calculate forecast accuracy for a month at month end
        month: 'YYYY-MM' format
        """
        try:
            year, month_num = map(int, month.split('-'))
            month_start = datetime(year, month_num, 1)
            _, last_day = monthrange(year, month_num)
            month_end = datetime(year, month_num, last_day, 23, 59, 59)
            
            logger.info(f"📊 Calculating accuracy for {month}...")
            
            # Get forecast record
            forecast = db.query(ForecastAccuracy).filter(
                and_(
                    ForecastAccuracy.user_id == user_id,
                    ForecastAccuracy.forecast_month == month
                )
            ).first()
            
            if not forecast:
                logger.warning(f"No forecast found for {month}")
                return None
            
            # Get actual revenue (won deals)
            won_deals = db.query(Deal).filter(
                and_(
                    Deal.user_id == user_id,
                    Deal.actual_close_date >= month_start,
                    Deal.actual_close_date <= month_end,
                    Deal.status == "won"
                )
            ).all()
            
            actual_revenue = sum(d.value for d in won_deals)
            win_rate = len(won_deals)
            lost_deals_count = len([d for d in won_deals if d.status == "lost"])
            
            # Calculate accuracy
            if forecast.forecasted_revenue > 0:
                accuracy_pct = (actual_revenue / forecast.forecasted_revenue) * 100
            else:
                accuracy_pct = 100 if actual_revenue == 0 else 0
            
            variance = actual_revenue - forecast.forecasted_revenue
            variance_reasons = ForecastService._analyze_variance(variance, actual_revenue, forecast.forecasted_revenue)
            
            # Update forecast record
            forecast.actual_revenue = actual_revenue
            forecast.forecast_accuracy_pct = accuracy_pct
            forecast.win_rate_pct = (win_rate / len(won_deals)) * 100 if won_deals else 0
            forecast.deals_forecast = len(db.query(Deal).filter(
                and_(Deal.user_id == user_id, Deal.stage != "prospecting")
            ).all())
            forecast.deals_won = win_rate
            forecast.deals_lost = lost_deals_count
            forecast.variance_reasons = variance_reasons
            
            db.commit()
            db.refresh(forecast)
            
            logger.info(f"✅ Accuracy calculated: {accuracy_pct:.1f}% (${actual_revenue:.2f} actual vs ${forecast.forecasted_revenue:.2f} forecast)")
            return forecast
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Accuracy calculation failed: {e}")
            return None
    
    @staticmethod
    def _analyze_variance(variance: float, actual: float, forecasted: float) -> list:
        """Analyze why forecast was off"""
        reasons = []
        
        if variance > forecasted * 0.2:  # >20% over
            reasons.append("Higher than expected win rate")
            reasons.append("Larger than expected deal sizes")
        elif variance < forecasted * -0.2:  # >20% under
            reasons.append("Lower than expected win rate")
            reasons.append("Lost deals to competition")
            reasons.append("Deals delayed beyond month")
        
        if abs(variance) < forecasted * 0.1:  # <10% variance
            reasons.append("Forecast was accurate")
        
        return reasons
    
    @staticmethod
    def get_accuracy_trends(db: Session, user_id: int, months: int = 12) -> Dict:
        """Get forecast accuracy trends over time"""
        try:
            forecasts = db.query(ForecastAccuracy).filter(
                ForecastAccuracy.user_id == user_id
            ).order_by(ForecastAccuracy.forecast_month.desc()).limit(months).all()
            
            trends = {
                "total_forecasts": len(forecasts),
                "avg_accuracy_pct": sum(f.forecast_accuracy_pct for f in forecasts) / len(forecasts) if forecasts else 0,
                "forecasts_within_10pct": len([f for f in forecasts if abs(f.forecast_accuracy_pct - 100) <= 10]),
                "forecasts_over": len([f for f in forecasts if f.forecast_accuracy_pct > 100]),
                "forecasts_under": len([f for f in forecasts if f.forecast_accuracy_pct < 100]),
                "total_forecast_revenue": sum(f.forecasted_revenue for f in forecasts),
                "total_actual_revenue": sum(f.actual_revenue for f in forecasts),
                "by_month": {}
            }
            
            for forecast in sorted(forecasts, key=lambda f: f.forecast_month):
                trends["by_month"][forecast.forecast_month] = {
                    "forecasted": forecast.forecasted_revenue,
                    "actual": forecast.actual_revenue,
                    "accuracy_pct": forecast.forecast_accuracy_pct
                }
            
            logger.debug(f"📊 Trends: {trends['avg_accuracy_pct']:.1f}% avg accuracy")
            return trends
            
        except Exception as e:
            logger.error(f"❌ Trends analysis failed: {e}")
            return {}
    
    @staticmethod
    def identify_forecast_drivers(db: Session, user_id: int) -> Dict:
        """Identify what drives forecast accuracy"""
        try:
            # Get recent forecasts
            forecasts = db.query(ForecastAccuracy).filter(
                ForecastAccuracy.user_id == user_id
            ).order_by(ForecastAccuracy.forecast_month.desc()).limit(6).all()
            
            drivers = {
                "primary_win_drivers": [],
                "primary_loss_drivers": [],
                "accuracy_patterns": []
            }
            
            # Analyze patterns
            accurate_forecasts = [f for f in forecasts if abs(f.forecast_accuracy_pct - 100) <= 10]
            inaccurate_forecasts = [f for f in forecasts if abs(f.forecast_accuracy_pct - 100) > 20]
            
            if accurate_forecasts:
                drivers["accuracy_patterns"].append(f"Accurate in {len(accurate_forecasts)} of {len(forecasts)} months")
            
            # Win/loss patterns
            for forecast in forecasts:
                if forecast.variance_reasons:
                    for reason in forecast.variance_reasons:
                        if "win" in reason.lower() or "larger" in reason.lower():
                            drivers["primary_win_drivers"].append(reason)
                        elif "loss" in reason.lower() or "delayed" in reason.lower():
                            drivers["primary_loss_drivers"].append(reason)
            
            return drivers
            
        except Exception as e:
            logger.error(f"❌ Driver analysis failed: {e}")
            return {}
