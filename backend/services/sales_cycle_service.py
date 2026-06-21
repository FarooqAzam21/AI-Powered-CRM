"""
Sales Cycle Tracking Service - Phase 7
Tracks sales cycle metrics and identifies bottlenecks
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from auth.models import SalesCycleMetrics
from models.crm import Deal, DealActivity
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SalesCycleService:
    """Service for sales cycle tracking and optimization"""
    
    @staticmethod
    def calculate_cycle_metrics(db: Session, user_id: int, 
                               period_type: str = "monthly") -> Optional[SalesCycleMetrics]:
        """
        Calculate sales cycle metrics for a period
        period_type: 'monthly', 'quarterly', 'yearly'
        """
        try:
            # Determine period
            now = datetime.utcnow()
            if period_type == "monthly":
                period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            elif period_type == "quarterly":
                quarter = (now.month - 1) // 3
                period_start = now.replace(month=quarter * 3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
                period_end = (period_start + timedelta(days=92)).replace(day=1) - timedelta(seconds=1)
            else:  # yearly
                period_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                period_end = now.replace(month=12, day=31, hour=23, minute=59, second=59)
            
            logger.info(f"📊 Calculating {period_type} cycle metrics...")
            
            # Get deals closed in period
            closed_deals = db.query(Deal).filter(
                and_(
                    Deal.user_id == user_id,
                    Deal.actual_close_date >= period_start,
                    Deal.actual_close_date <= period_end,
                    Deal.status.in_(["won", "lost"])
                )
            ).all()
            
            # Get deals started in period
            started_deals = db.query(Deal).filter(
                and_(
                    Deal.user_id == user_id,
                    Deal.created_at >= period_start,
                    Deal.created_at <= period_end
                )
            ).all()
            
            # Calculate cycle durations
            cycle_durations = []
            for deal in closed_deals:
                if deal.created_at:
                    duration = (deal.actual_close_date - deal.created_at).days
                    cycle_durations.append(duration)
            
            avg_cycle = sum(cycle_durations) / len(cycle_durations) if cycle_durations else 0
            median_cycle = sorted(cycle_durations)[len(cycle_durations)//2] if cycle_durations else 0
            
            # Calculate stage metrics
            stage_durations, conversion_rates, dropout_rates = SalesCycleService._calculate_stage_metrics(
                db, user_id, started_deals
            )
            
            # Compile metrics
            metrics = SalesCycleMetrics(
                user_id=user_id,
                period_start=period_start,
                period_end=period_end,
                period_type=period_type,
                avg_sales_cycle_days=avg_cycle,
                median_sales_cycle_days=median_cycle,
                fastest_close_days=min(cycle_durations) if cycle_durations else 0,
                slowest_close_days=max(cycle_durations) if cycle_durations else 0,
                avg_stage_durations=stage_durations,
                stage_conversion_rates=conversion_rates,
                stage_dropout_rates=dropout_rates,
                deals_started=len(started_deals),
                deals_closed=len([d for d in closed_deals if d.status == "won"]),
                deals_lost=len([d for d in closed_deals if d.status == "lost"]),
                avg_deals_in_pipeline=SalesCycleService._get_avg_pipeline_size(db, user_id, period_start, period_end)
            )
            
            db.add(metrics)
            db.commit()
            db.refresh(metrics)
            
            logger.info(f"✅ Cycle metrics saved: {avg_cycle:.1f} days average")
            return metrics
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Cycle calculation failed: {e}")
            return None
    
    @staticmethod
    def _calculate_stage_metrics(db: Session, user_id: int, deals: list) -> tuple:
        """Calculate stage transition metrics"""
        stages = ["prospecting", "qualification", "proposal", "negotiation"]
        stage_durations = {}
        conversion_rates = {}
        dropout_rates = {}
        
        for i, stage in enumerate(stages):
            stage_deals = [d for d in deals if d.stage == stage]
            
            if stage_deals:
                # Average time in stage
                times = []
                for deal in stage_deals:
                    activities = db.query(DealActivity).filter(
                        DealActivity.deal_id == deal.id
                    ).order_by(DealActivity.created_at).all()
                    
                    stage_activities = [a for a in activities if stage in str(a.activity_type).lower()]
                    if stage_activities:
                        times.append((datetime.utcnow() - stage_activities[0].created_at).days)
                
                stage_durations[stage] = sum(times) / len(times) if times else 0
                
                # Conversion to next stage
                if i < len(stages) - 1:
                    next_stage_count = len([d for d in deals if d.stage in stages and stages.index(d.stage) > i])
                    conversion_rates[stage] = (next_stage_count / len(stage_deals) * 100) if stage_deals else 0
                    dropout_rates[stage] = 100 - conversion_rates.get(stage, 0)
                else:
                    conversion_rates[stage] = 100
                    dropout_rates[stage] = 0
        
        return stage_durations, conversion_rates, dropout_rates
    
    @staticmethod
    def _get_avg_pipeline_size(db: Session, user_id: int, 
                              period_start: datetime, period_end: datetime) -> float:
        """Calculate average deals in pipeline during period"""
        # Simplified: count open deals at period end
        open_deals = db.query(func.count(Deal.id)).filter(
            and_(
                Deal.user_id == user_id,
                Deal.status == "open",
                Deal.created_at <= period_end
            )
        ).scalar()
        
        return open_deals or 0
    
    @staticmethod
    def get_bottleneck_analysis(db: Session, user_id: int) -> Dict:
        """Identify pipeline bottlenecks"""
        try:
            deals = db.query(Deal).filter(
                and_(
                    Deal.user_id == user_id,
                    Deal.status == "open"
                )
            ).all()
            
            bottlenecks = {}
            
            for stage in ["prospecting", "qualification", "proposal", "negotiation"]:
                stage_deals = [d for d in deals if d.stage == stage]
                
                if stage_deals:
                    # Find deals stuck longest in stage
                    max_age = max(
                        (datetime.utcnow() - d.stage_moved_at).days 
                        for d in stage_deals if d.stage_moved_at
                    )
                    
                    if max_age > 14:  # > 2 weeks
                        bottlenecks[stage] = {
                            "deal_count": len(stage_deals),
                            "oldest_days": max_age,
                            "avg_days": sum(
                                (datetime.utcnow() - d.stage_moved_at).days 
                                for d in stage_deals if d.stage_moved_at
                            ) / len(stage_deals),
                            "stalled_deals": len([d for d in stage_deals if max_age > 21])
                        }
            
            logger.debug(f"📊 Bottleneck analysis: {len(bottlenecks)} stages blocked")
            return bottlenecks
            
        except Exception as e:
            logger.error(f"❌ Bottleneck analysis failed: {e}")
            return {}
    
    @staticmethod
    def get_sales_velocity(db: Session, user_id: int, days: int = 30) -> Dict:
        """Calculate sales velocity (deals per day, revenue per day)"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            closed_deals = db.query(Deal).filter(
                and_(
                    Deal.user_id == user_id,
                    Deal.actual_close_date >= cutoff_date,
                    Deal.status == "won"
                )
            ).all()
            
            won_count = len(closed_deals)
            won_revenue = sum(d.value for d in closed_deals)
            
            velocity = {
                "period_days": days,
                "deals_closed": won_count,
                "revenue_closed": won_revenue,
                "deals_per_day": won_count / days if days > 0 else 0,
                "revenue_per_day": won_revenue / days if days > 0 else 0,
                "avg_deal_size": won_revenue / won_count if won_count > 0 else 0
            }
            
            return velocity
            
        except Exception as e:
            logger.error(f"❌ Velocity calculation failed: {e}")
            return {}
