"""
Win/Loss Analysis Service - Phase 7
Analyzes deals won and lost to extract patterns and improve strategy
"""
import logging
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from auth.models import WinLossAnalysis, Email
from models.crm import Deal, Contact, Activity, DealActivity
from ai.ollama_client import generate_cached
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class WinLossService:
    """Service for win/loss analysis and pattern extraction"""
    
    @staticmethod
    def analyze_closed_deal(db: Session, user_id: int, deal_id: int, 
                           outcome: str, competitor: Optional[str] = None) -> Optional[WinLossAnalysis]:
        """
        Analyze a closed deal to extract patterns
        outcome: 'won' or 'lost'
        """
        try:
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            if not deal:
                logger.error(f"Deal {deal_id} not found")
                return None
            
            logger.info(f"📊 Analyzing {outcome} deal: {deal.name}")
            
            # Get deal context
            activities = db.query(Activity).filter(Activity.contact_id == deal.contact_id).all() if deal.contact_id else []
            deal_activities = db.query(DealActivity).filter(DealActivity.deal_id == deal_id).all()
            
            # Calculate sales cycle
            sales_cycle_days = None
            if deal.created_at and (deal.actual_close_date or datetime.utcnow()):
                close_date = deal.actual_close_date or datetime.utcnow()
                sales_cycle_days = (close_date - deal.created_at).days
            
            # Extract key factors using AI
            key_factors = WinLossService._extract_key_factors(
                deal, outcome, activities, deal_activities, sales_cycle_days
            )
            
            # Generate root cause analysis
            root_cause = WinLossService._determine_root_cause(
                deal, outcome, key_factors
            )
            
            # Generate lessons learned
            lessons = WinLossService._extract_lessons(outcome, key_factors, root_cause)
            
            # Create analysis record
            analysis = WinLossAnalysis(
                user_id=user_id,
                deal_id=deal_id,
                outcome=outcome,
                outcome_date=datetime.utcnow(),
                root_cause=root_cause,
                key_factors=key_factors,
                competitor=competitor,
                final_value=deal.value,
                sales_cycle_days=sales_cycle_days,
                contact_count=len(set(a.contact_id for a in activities if a.contact_id)),
                interaction_count=len(activities) + len(deal_activities),
                lessons_learned=lessons
            )
            
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            
            logger.info(f"✅ Analysis complete: {outcome} (cycle: {sales_cycle_days} days)")
            return analysis
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Analysis failed: {e}")
            return None
    
    @staticmethod
    def _extract_key_factors(deal: Deal, outcome: str, 
                            activities: List[Activity], 
                            deal_activities: List[DealActivity],
                            sales_cycle_days: Optional[int] = None) -> List[str]:
        """Extract key factors that led to win/loss"""
        factors = []
        
        if outcome == "won":
            # Win factors
            if deal.probability >= 75:
                factors.append("High probability at close")
            if len(activities) > 5:
                factors.append("High engagement")
            if sales_cycle_days and sales_cycle_days < 45:
                factors.append("Fast sales cycle")
            if any("proposal" in str(a.activity_type).lower() for a in deal_activities):
                factors.append("Strong proposal")
        else:
            # Loss factors
            if deal.probability < 30:
                factors.append("Low probability throughout")
            if len(activities) < 3:
                factors.append("Low engagement")
            if deal.stage == "prospecting":
                factors.append("Lost early in cycle")
            if any("escalation" in str(a.activity_type).lower() for a in deal_activities):
                factors.append("Escalation issues")
        
        return factors
    
    @staticmethod
    def _determine_root_cause(deal: Deal, outcome: str, factors: List[str]) -> str:
        """Determine primary root cause"""
        if outcome == "won":
            if "High engagement" in factors and "Fast sales cycle" in factors:
                return "Strong sales execution and buyer alignment"
            elif "Strong proposal" in factors:
                return "Compelling solution fit"
            else:
                return "Successful deal progression"
        else:
            if "Low engagement" in factors:
                return "Insufficient buyer engagement"
            elif "Lost early in cycle" in factors:
                return "Inadequate qualification"
            elif any("competitor" in str(f).lower() for f in factors):
                return "Lost to competitor"
            else:
                return "Deal did not progress to close"
    
    @staticmethod
    def _extract_lessons(outcome: str, factors: List[str], root_cause: str) -> List[str]:
        """Extract actionable lessons learned"""
        lessons = []
        
        if outcome == "won":
            if "High engagement" in factors:
                lessons.append("Prioritize high-engagement opportunities")
            if "Fast sales cycle" in factors:
                lessons.append("Replicate fast-cycle sales process")
            if "Strong proposal" in factors:
                lessons.append("Use this proposal as template")
        else:
            if "Low engagement" in factors:
                lessons.append("Improve stakeholder engagement early")
            if "Lost early in cycle" in factors:
                lessons.append("Better lead qualification needed")
            if "competitor" in root_cause.lower():
                lessons.append("Strengthen competitive positioning")
        
        lessons.append(f"Primary driver: {root_cause}")
        return lessons
    
    @staticmethod
    def get_win_loss_summary(db: Session, user_id: int, days: int = 90) -> Dict:
        """Get win/loss summary statistics"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            analyses = db.query(WinLossAnalysis).filter(
                and_(
                    WinLossAnalysis.user_id == user_id,
                    WinLossAnalysis.created_at >= cutoff_date
                )
            ).all()
            
            won = [a for a in analyses if a.outcome == "won"]
            lost = [a for a in analyses if a.outcome == "lost"]
            
            win_rate = len(won) / len(analyses) * 100 if analyses else 0
            
            # Calculate metrics
            avg_won_cycle = sum(a.sales_cycle_days for a in won if a.sales_cycle_days) / len([a for a in won if a.sales_cycle_days]) if won else 0
            avg_lost_cycle = sum(a.sales_cycle_days for a in lost if a.sales_cycle_days) / len([a for a in lost if a.sales_cycle_days]) if lost else 0
            
            avg_won_value = sum(a.final_value for a in won) / len(won) if won else 0
            avg_lost_value = sum(a.final_value for a in lost) / len(lost) if lost else 0
            
            summary = {
                "period_days": days,
                "total_deals": len(analyses),
                "won_count": len(won),
                "lost_count": len(lost),
                "win_rate_pct": win_rate,
                "avg_won_cycle_days": avg_won_cycle,
                "avg_lost_cycle_days": avg_lost_cycle,
                "avg_won_value": avg_won_value,
                "avg_lost_value": avg_lost_value,
                "total_won_value": sum(a.final_value for a in won),
                "total_lost_value": sum(a.final_value for a in lost),
                "top_win_factors": WinLossService._get_top_factors(won),
                "top_loss_factors": WinLossService._get_top_factors(lost)
            }
            
            logger.info(f"📊 Summary: {win_rate:.1f}% win rate ({len(won)} won, {len(lost)} lost)")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Summary generation failed: {e}")
            return {}
    
    @staticmethod
    def _get_top_factors(analyses: List[WinLossAnalysis], limit: int = 3) -> List[str]:
        """Get most common factors"""
        factor_counts = {}
        for analysis in analyses:
            for factor in analysis.key_factors or []:
                factor_counts[factor] = factor_counts.get(factor, 0) + 1
        
        sorted_factors = sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)
        return [f[0] for f in sorted_factors[:limit]]
    
    @staticmethod
    def get_competitor_analysis(db: Session, user_id: int) -> Dict:
        """Analyze losses by competitor"""
        try:
            lost_deals = db.query(WinLossAnalysis).filter(
                and_(
                    WinLossAnalysis.user_id == user_id,
                    WinLossAnalysis.outcome == "lost"
                )
            ).all()
            
            competitor_stats = {}
            for deal in lost_deals:
                if deal.competitor:
                    if deal.competitor not in competitor_stats:
                        competitor_stats[deal.competitor] = {
                            "losses": 0,
                            "total_value": 0,
                            "reasons": []
                        }
                    competitor_stats[deal.competitor]["losses"] += 1
                    competitor_stats[deal.competitor]["total_value"] += deal.final_value
                    if deal.root_cause:
                        competitor_stats[deal.competitor]["reasons"].append(deal.root_cause)
            
            logger.debug(f"📊 Competitor analysis: {len(competitor_stats)} competitors")
            return competitor_stats
            
        except Exception as e:
            logger.error(f"❌ Competitor analysis failed: {e}")
            return {}
