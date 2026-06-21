"""
Real-time Dashboard Service - Phase 8
Generates real-time events and metrics for live dashboards
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from auth.models import (
    Deal, Contact, Activity, WinLossAnalysis, TerritoryMetrics, 
    ForecastAccuracy, AIRecommendation
)
from websocket.dashboard_models import (
    DealUpdateEvent, DealStageChangeEvent, DealClosedEvent,
    TerritoryMetricsEvent, TerritoryOpportunityAlert, TerritoryRiskAlert,
    ForecastUpdateEvent, ForecastAlertEvent, WinLossAnalysisEvent,
    ActivityEvent, RecommendationEvent, DashboardMetrics, PipelineSnapshot,
    TerritorySnapshot
)
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class DashboardService:
    """Service for generating real-time dashboard events and metrics"""
    
    @staticmethod
    def get_pipeline_snapshot(db: Session, user_id: int) -> PipelineSnapshot:
        """Get real-time pipeline snapshot"""
        try:
            deals = db.query(Deal).filter(Deal.user_id == user_id).all()
            
            # Group by stage
            stages = {}
            for stage in ["prospecting", "qualification", "proposal", "negotiation"]:
                stage_deals = [d for d in deals if d.stage == stage]
                stages[stage] = {
                    "count": len(stage_deals),
                    "value": sum(d.value for d in stage_deals),
                    "avg_deal_size": sum(d.value for d in stage_deals) / len(stage_deals) if stage_deals else 0
                }
            
            # Group by probability
            by_probability = {
                "0-25": {"count": 0, "value": 0},
                "25-50": {"count": 0, "value": 0},
                "50-75": {"count": 0, "value": 0},
                "75-100": {"count": 0, "value": 0}
            }
            
            for deal in deals:
                if deal.status == "open":
                    prob = deal.probability
                    if prob <= 25:
                        bucket = "0-25"
                    elif prob <= 50:
                        bucket = "25-50"
                    elif prob <= 75:
                        bucket = "50-75"
                    else:
                        bucket = "75-100"
                    
                    by_probability[bucket]["count"] += 1
                    by_probability[bucket]["value"] += deal.value
            
            # Calculate velocity (guard against None actual_close_date)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            closed_deals = [
                d for d in deals
                if d.status in ["won", "lost"]
                and d.actual_close_date is not None
                and d.actual_close_date >= thirty_days_ago
            ]
            velocity_deals = len(closed_deals) / 30
            velocity_revenue = sum(d.value for d in closed_deals) / 30
            
            # Calculate average deal size and median cycle
            open_deals = [d for d in deals if d.status in ["open", "active"]]
            avg_deal = sum(d.value for d in deals) / len(deals) if deals else 0
            
            cycle_times = []
            for deal in closed_deals:
                if deal.created_at and deal.actual_close_date:
                    cycle_times.append((deal.actual_close_date - deal.created_at).days)
            median_cycle = sorted(cycle_times)[len(cycle_times)//2] if cycle_times else 0
            
            snapshot = PipelineSnapshot(
                timestamp=datetime.utcnow(),
                stages=stages,
                by_probability=by_probability,
                velocity_deals_per_day=velocity_deals,
                velocity_revenue_per_day=velocity_revenue,
                average_deal_size=avg_deal,
                median_cycle_days=median_cycle
            )
            
            logger.debug(f"📊 Pipeline snapshot: {len(deals)} deals")
            return snapshot
            
        except Exception as e:
            logger.error(f"❌ Pipeline snapshot error: {e}")
            return None
    
    @staticmethod
    def get_territory_snapshot(db: Session, user_id: int) -> TerritorySnapshot:
        """Get real-time territory performance snapshot"""
        try:
            territories = db.query(TerritoryMetrics).filter(
                TerritoryMetrics.user_id == user_id
            ).all()
            
            territory_data = {}
            for territory in territories:
                territory_data[territory.territory_name] = {
                    "win_rate_pct": territory.win_rate_pct,
                    "pipeline_value": territory.pipeline_value,
                    "revenue_actual": territory.revenue_actual,
                    "revenue_target": territory.revenue_target,
                    "quota_attainment_pct": territory.quota_attainment_pct,
                    "opportunity_score": territory.opportunity_score,
                    "risk_score": territory.risk_score,
                    "active_contacts": territory.active_contacts,
                    "growth_rate_pct": territory.growth_rate_pct
                }
            
            # Identify top/at-risk/opportunities
            sorted_by_win_rate = sorted(territories, key=lambda t: t.win_rate_pct, reverse=True)
            top_performers = [t.territory_name for t in sorted_by_win_rate[:3]]
            
            at_risk = [t.territory_name for t in territories if t.risk_score > 60]
            high_opportunity = [t.territory_name for t in territories if t.opportunity_score > 70]
            
            snapshot = TerritorySnapshot(
                timestamp=datetime.utcnow(),
                territories=territory_data,
                top_performers=top_performers,
                at_risk=at_risk,
                high_opportunity=high_opportunity,
                total_pipeline=sum(t.pipeline_value for t in territories),
                total_revenue_target=sum(t.revenue_target for t in territories),
                total_revenue_actual=sum(t.revenue_actual for t in territories)
            )
            
            logger.debug(f"📊 Territory snapshot: {len(territories)} territories")
            return snapshot
            
        except Exception as e:
            logger.error(f"❌ Territory snapshot error: {e}")
            return None
    
    @staticmethod
    def get_dashboard_metrics(db: Session, user_id: int) -> Optional[DashboardMetrics]:
        """Get current dashboard metrics"""
        try:
            deals = db.query(Deal).filter(Deal.user_id == user_id).all()
            activities = db.query(Activity).filter(
                Activity.created_at >= datetime.utcnow() - timedelta(days=7)
            ).all()
            
            open_deals = [d for d in deals if d.status in ["open", "active"]]
            won_deals = [d for d in deals if d.status == "won"]
            lost_deals = [d for d in deals if d.status == "lost"]
            
            # Territory metrics
            territories = db.query(TerritoryMetrics).filter(
                TerritoryMetrics.user_id == user_id
            ).all()
            at_risk_territories = [t for t in territories if t.risk_score > 60]
            high_opp_territories = [t for t in territories if t.opportunity_score > 70]
            
            # Forecast
            current_month = datetime.utcnow().strftime("%Y-%m")
            forecast = db.query(ForecastAccuracy).filter(
                and_(
                    ForecastAccuracy.user_id == user_id,
                    ForecastAccuracy.forecast_month == current_month
                )
            ).first()
            
            # Contacts
            contacts = db.query(Contact).filter(Contact.user_id == user_id).all()
            recent_contacts = [c for c in contacts if 
                              db.query(Activity).filter(Activity.contact_id == c.id).first()]
            
            metrics = DashboardMetrics(
                timestamp=datetime.utcnow(),
                user_id=user_id,
                open_deals_count=len(open_deals),
                won_deals_count=len(won_deals),
                lost_deals_count=len(lost_deals),
                total_pipeline_value=sum(d.value for d in open_deals),
                territories_count=len(territories),
                territories_at_risk=len(at_risk_territories),
                territories_high_opportunity=len(high_opp_territories),
                forecast_month=current_month,
                forecast_accuracy_pct=forecast.forecast_accuracy_pct if forecast else 0,
                current_vs_forecast=(sum(d.value for d in open_deals) / forecast.forecasted_revenue * 100) if forecast else 0,
                recent_activities_count=len(activities),
                active_contacts_count=len(recent_contacts)
            )
            
            logger.debug(f"📊 Dashboard metrics: {len(deals)} deals, {len(territories)} territories")
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Dashboard metrics error: {e}")
            return None
    
    @staticmethod
    def generate_deal_update_event(db: Session, deal_id: int) -> Optional[DealUpdateEvent]:
        """Generate real-time deal update event"""
        try:
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            if not deal:
                return None
            
            event = DealUpdateEvent(
                deal_id=deal.id,
                deal_name=deal.name,
                stage=deal.stage,
                probability=deal.probability,
                value=deal.value,
                status=deal.status,
                expected_close_date=deal.expected_close_date
            )
            
            logger.debug(f"📨 Deal update event: {deal.name}")
            return event
            
        except Exception as e:
            logger.error(f"❌ Deal event generation error: {e}")
            return None
    
    @staticmethod
    def generate_stage_change_event(deal_id: int, old_stage: str, 
                                   new_stage: str, deal_name: str) -> DealStageChangeEvent:
        """Generate deal stage change event"""
        event = DealStageChangeEvent(
            deal_id=deal_id,
            deal_name=deal_name,
            old_stage=old_stage,
            new_stage=new_stage
        )
        
        logger.debug(f"📨 Stage change event: {deal_name} {old_stage} → {new_stage}")
        return event
    
    @staticmethod
    def generate_deal_closed_event(db: Session, deal_id: int) -> Optional[DealClosedEvent]:
        """Generate deal closed event"""
        try:
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            if not deal:
                return None
            
            # Get win/loss analysis if exists
            analysis = db.query(WinLossAnalysis).filter(
                WinLossAnalysis.deal_id == deal_id
            ).first()
            
            event = DealClosedEvent(
                deal_id=deal.id,
                deal_name=deal.name,
                outcome=deal.status,
                value=deal.value,
                root_cause=analysis.root_cause if analysis else None
            )
            
            logger.debug(f"📨 Deal closed event: {deal.name} ({deal.status})")
            return event
            
        except Exception as e:
            logger.error(f"❌ Deal closed event error: {e}")
            return None
    
    @staticmethod
    def generate_territory_alert(territory: TerritoryMetrics) -> Optional[List[Dict]]:
        """Generate territory alerts (opportunity/risk)"""
        try:
            alerts = []
            
            # Opportunity alert
            if territory.opportunity_score > 70:
                alerts.append({
                    "type": "opportunity_alert",
                    "territory": territory.territory_name,
                    "opportunity_score": territory.opportunity_score,
                    "reason": "High growth potential detected",
                    "action": "Allocate additional resources"
                })
            
            # Risk alert
            if territory.risk_score > 60:
                alerts.append({
                    "type": "risk_alert",
                    "territory": territory.territory_name,
                    "risk_score": territory.risk_score,
                    "reason": "Multiple at-risk factors detected",
                    "action": "Review stalled deals and engagement"
                })
            
            if alerts:
                logger.debug(f"📨 Territory alerts: {len(alerts)} for {territory.territory_name}")
            return alerts
            
        except Exception as e:
            logger.error(f"❌ Territory alert error: {e}")
            return []
    
    @staticmethod
    def generate_forecast_alert(db: Session, user_id: int) -> Optional[Dict]:
        """Generate forecast status alert"""
        try:
            current_month = datetime.utcnow().strftime("%Y-%m")
            forecast = db.query(ForecastAccuracy).filter(
                and_(
                    ForecastAccuracy.user_id == user_id,
                    ForecastAccuracy.forecast_month == current_month
                )
            ).first()
            
            if not forecast:
                return None
            
            # Get current pipeline
            deals = db.query(Deal).filter(
                and_(Deal.user_id == user_id, Deal.status == "open")
            ).all()
            current_pipeline = sum(d.value for d in deals)
            
            # Determine status
            if current_pipeline >= forecast.forecasted_revenue * 0.9:
                status = "on_track"
                reason = "Pipeline meets forecast expectations"
            elif current_pipeline >= forecast.forecasted_revenue * 0.7:
                status = "caution"
                reason = "Pipeline slightly below forecast"
            else:
                status = "at_risk"
                reason = "Pipeline significantly below forecast"
            
            alert = {
                "type": "forecast_alert",
                "month": current_month,
                "status": status,
                "reason": reason,
                "forecasted": forecast.forecasted_revenue,
                "current_pipeline": current_pipeline,
                "variance_pct": ((current_pipeline - forecast.forecasted_revenue) / forecast.forecasted_revenue * 100)
            }
            
            logger.debug(f"📨 Forecast alert: {status}")
            return alert
            
        except Exception as e:
            logger.error(f"❌ Forecast alert error: {e}")
            return None
    
    @staticmethod
    def generate_activity_event(db: Session, activity_id: int) -> Optional[ActivityEvent]:
        """Generate activity created event"""
        try:
            activity = db.query(Activity).filter(Activity.id == activity_id).first()
            if not activity:
                return None
            
            contact = db.query(Contact).filter(Contact.id == activity.contact_id).first()
            
            event = ActivityEvent(
                activity_id=activity.id,
                contact_id=activity.contact_id,
                contact_name=contact.name if contact else "Unknown",
                activity_type=activity.type,
                notes=activity.description or ""
            )
            
            logger.debug(f"📨 Activity event: {activity.type}")
            return event
            
        except Exception as e:
            logger.error(f"❌ Activity event error: {e}")
            return None
    
    @staticmethod
    def generate_recommendation_event(db: Session, 
                                    recommendation_id: int) -> Optional[RecommendationEvent]:
        """Generate recommendation event"""
        try:
            recommendation = db.query(AIRecommendation).filter(
                AIRecommendation.id == recommendation_id
            ).first()
            if not recommendation:
                return None
            
            event = RecommendationEvent(
                recommendation_id=recommendation.id,
                contact_id=recommendation.contact_id,
                deal_id=recommendation.deal_id,
                recommendation_type=recommendation.recommendation_type,
                title=recommendation.title,
                description=recommendation.description or "",
                confidence_score=recommendation.confidence_score
            )
            
            logger.debug(f"📨 Recommendation event: {recommendation.title}")
            return event
            
        except Exception as e:
            logger.error(f"❌ Recommendation event error: {e}")
            return None
