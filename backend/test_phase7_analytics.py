"""
Phase 7 Advanced Analytics Test Suite
Tests for win/loss analysis, sales cycle metrics, forecast accuracy, and territory optimization
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from auth.models import (
    Base, User, Deal, Contact, Activity, Email, DealActivity,
    WinLossAnalysis, SalesCycleMetrics, ForecastAccuracy, TerritoryMetrics
)
from services.winloss_service import WinLossService
from services.sales_cycle_service import SalesCycleService
from services.forecast_service import ForecastService
from services.territory_service import TerritoryService
import logging

logger = logging.getLogger(__name__)

# =================== FIXTURES ===================

@pytest.fixture
def db():
    """In-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def test_user(db):
    """Create test user"""
    user = User(
        email="test@example.com",
        password="hashed123",
        name="Test User",
        role="sales"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_contact(db, test_user):
    """Create test contact"""
    contact = Contact(
        user_id=test_user.id,
        name="John Doe",
        email="john@example.com",
        company="Acme Corp"
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

@pytest.fixture
def test_deal(db, test_user, test_contact):
    """Create test deal"""
    deal = Deal(
        user_id=test_user.id,
        contact_id=test_contact.id,
        name="Test Deal",
        value=50000,
        stage="proposal",
        probability=60,
        expected_close_date=datetime.utcnow() + timedelta(days=30),
        created_at=datetime.utcnow() - timedelta(days=45)
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal

# =================== WIN/LOSS ANALYSIS TESTS ===================

class TestWinLossService:
    """Test win/loss analysis functionality"""
    
    def test_analyze_won_deal(self, db, test_user, test_deal):
        """Test analyzing a won deal"""
        test_deal.status = "won"
        test_deal.probability = 80
        test_deal.actual_close_date = datetime.utcnow()
        db.commit()
        
        analysis = WinLossService.analyze_closed_deal(
            db, test_user.id, test_deal.id, "won"
        )
        
        assert analysis is not None
        assert analysis.outcome == "won"
        assert analysis.root_cause is not None
        assert analysis.key_factors is not None
        assert len(analysis.key_factors) > 0
        logger.info(f"✅ Won deal analysis: {analysis.root_cause}")
    
    def test_analyze_lost_deal(self, db, test_user, test_deal):
        """Test analyzing a lost deal"""
        test_deal.status = "lost"
        test_deal.actual_close_date = datetime.utcnow()
        test_deal.probability = 10
        db.commit()
        
        analysis = WinLossService.analyze_closed_deal(
            db, test_user.id, test_deal.id, "lost", "CompetitorXYZ"
        )
        
        assert analysis is not None
        assert analysis.outcome == "lost"
        assert analysis.competitor == "CompetitorXYZ"
        assert analysis.lessons_learned is not None
        logger.info(f"✅ Lost deal analysis: {analysis.root_cause}")
    
    def test_win_loss_summary(self, db, test_user, test_deal):
        """Test win/loss summary generation"""
        # Create multiple deals
        for i in range(3):
            deal = Deal(
                user_id=test_user.id,
                name=f"Deal {i}",
                value=25000 * (i + 1),
                stage="proposal",
                status="won" if i % 2 == 0 else "lost",
                actual_close_date=datetime.utcnow() - timedelta(days=i),
                created_at=datetime.utcnow() - timedelta(days=60 + i * 5)
            )
            db.add(deal)
            db.commit()
            WinLossService.analyze_closed_deal(
                db, test_user.id, deal.id,
                "won" if i % 2 == 0 else "lost"
            )
        
        summary = WinLossService.get_win_loss_summary(db, test_user.id)
        
        assert summary is not None
        assert "win_rate_pct" in summary
        assert summary["total_deals"] > 0
        logger.info(f"✅ Win/Loss summary: {summary['win_rate_pct']:.1f}% win rate")
    
    def test_competitor_analysis(self, db, test_user, test_deal):
        """Test competitor analysis"""
        test_deal.status = "lost"
        test_deal.actual_close_date = datetime.utcnow()
        db.commit()
        
        WinLossService.analyze_closed_deal(
            db, test_user.id, test_deal.id, "lost", "Competitor A"
        )
        
        competitors = WinLossService.get_competitor_analysis(db, test_user.id)
        
        assert competitors is not None
        assert "Competitor A" in competitors
        logger.info(f"✅ Competitor analysis: {len(competitors)} competitors found")

# =================== SALES CYCLE TESTS ===================

class TestSalesCycleService:
    """Test sales cycle tracking functionality"""
    
    def test_calculate_cycle_metrics_monthly(self, db, test_user, test_deal):
        """Test monthly cycle metrics calculation"""
        # Create closed deals
        for i in range(3):
            deal = Deal(
                user_id=test_user.id,
                name=f"Closed Deal {i}",
                value=30000,
                status="won",
                created_at=datetime.utcnow() - timedelta(days=90 - i * 30),
                actual_close_date=datetime.utcnow() - timedelta(days=45 - i * 30)
            )
            db.add(deal)
        db.commit()
        
        metrics = SalesCycleService.calculate_cycle_metrics(
            db, test_user.id, "monthly"
        )
        
        assert metrics is not None
        assert metrics.avg_sales_cycle_days > 0
        assert metrics.deals_closed >= 0
        logger.info(f"✅ Cycle metrics: {metrics.avg_sales_cycle_days:.1f} days avg")
    
    def test_bottleneck_analysis(self, db, test_user, test_deal):
        """Test pipeline bottleneck identification"""
        # Create stalled deals
        stalled_deal = Deal(
            user_id=test_user.id,
            name="Stalled Deal",
            value=50000,
            stage="proposal",
            status="open",
            stage_moved_at=datetime.utcnow() - timedelta(days=45)
        )
        db.add(stalled_deal)
        db.commit()
        
        bottlenecks = SalesCycleService.get_bottleneck_analysis(db, test_user.id)
        
        assert bottlenecks is not None
        logger.info(f"✅ Bottleneck analysis: {len(bottlenecks)} bottlenecks found")
    
    def test_sales_velocity(self, db, test_user):
        """Test sales velocity calculation"""
        # Create won deals
        for i in range(5):
            deal = Deal(
                user_id=test_user.id,
                name=f"Velocity Deal {i}",
                value=20000,
                status="won",
                actual_close_date=datetime.utcnow() - timedelta(days=i * 5)
            )
            db.add(deal)
        db.commit()
        
        velocity = SalesCycleService.get_sales_velocity(db, test_user.id, days=30)
        
        assert velocity is not None
        assert velocity["deals_per_day"] > 0
        assert velocity["revenue_per_day"] > 0
        logger.info(f"✅ Sales velocity: {velocity['deals_per_day']:.2f} deals/day")

# =================== FORECAST ACCURACY TESTS ===================

class TestForecastService:
    """Test forecast accuracy tracking"""
    
    def test_record_forecast(self, db, test_user):
        """Test recording a forecast"""
        month = "2024-12"
        forecasted_revenue = 250000
        
        forecast = ForecastService.record_forecast(
            db, test_user.id, month, forecasted_revenue
        )
        
        assert forecast is not None
        assert forecast.forecast_month == month
        assert forecast.forecasted_revenue == forecasted_revenue
        logger.info(f"✅ Forecast recorded: ${forecasted_revenue:.2f}")
    
    def test_calculate_month_accuracy(self, db, test_user):
        """Test forecast accuracy calculation"""
        month = datetime.utcnow().strftime("%Y-%m")
        forecasted_revenue = 100000
        
        # Record forecast
        ForecastService.record_forecast(db, test_user.id, month, forecasted_revenue)
        
        # Create won deals
        for i in range(3):
            deal = Deal(
                user_id=test_user.id,
                name=f"Forecast Deal {i}",
                value=30000,
                status="won",
                actual_close_date=datetime.utcnow()
            )
            db.add(deal)
        db.commit()
        
        forecast = ForecastService.calculate_month_accuracy(db, test_user.id, month)
        
        assert forecast is not None
        assert forecast.actual_revenue == 90000
        assert forecast.forecast_accuracy_pct > 0
        logger.info(f"✅ Accuracy: {forecast.forecast_accuracy_pct:.1f}%")
    
    def test_accuracy_trends(self, db, test_user):
        """Test forecast accuracy trends"""
        # Create multiple forecasts
        for i in range(3):
            month = (datetime.utcnow() - timedelta(days=30 * i)).strftime("%Y-%m")
            ForecastService.record_forecast(db, test_user.id, month, 150000)
        
        trends = ForecastService.get_accuracy_trends(db, test_user.id, months=3)
        
        assert trends is not None
        assert trends["total_forecasts"] > 0
        logger.info(f"✅ Trends: {trends['total_forecasts']} forecasts tracked")

# =================== TERRITORY TESTS ===================

class TestTerritoryService:
    """Test territory optimization"""
    
    def test_create_territory_metrics(self, db, test_user):
        """Test creating territory metrics"""
        # Create deals for territory
        for i in range(5):
            deal = Deal(
                user_id=test_user.id,
                name=f"Territory Deal {i}",
                value=20000 * (i + 1),
                stage="proposal",
                status="won" if i % 2 == 0 else "lost"
            )
            db.add(deal)
        db.commit()
        
        metrics = TerritoryService.create_territory_metrics(
            db, test_user.id, "North Territory"
        )
        
        assert metrics is not None
        assert metrics.territory_name == "North Territory"
        assert metrics.win_rate_pct > 0
        assert metrics.opportunity_score >= 0
        assert metrics.risk_score >= 0
        logger.info(f"✅ Territory metrics: {metrics.win_rate_pct:.1f}% win rate")
    
    def test_opportunity_score_calculation(self, db, test_user):
        """Test opportunity score calculation"""
        # Create high-value pipeline
        for i in range(5):
            deal = Deal(
                user_id=test_user.id,
                name=f"Opportunity {i}",
                value=100000,
                status="open",
                stage="proposal"
            )
            db.add(deal)
        db.commit()
        
        metrics = TerritoryService.create_territory_metrics(
            db, test_user.id, "High Opportunity Territory"
        )
        
        assert metrics.opportunity_score > 50
        logger.info(f"✅ High opportunity score: {metrics.opportunity_score}")
    
    def test_risk_score_calculation(self, db, test_user):
        """Test risk score calculation"""
        # Create stalled deals
        for i in range(3):
            deal = Deal(
                user_id=test_user.id,
                name=f"Stalled {i}",
                value=50000,
                status="open",
                stage="proposal",
                stage_moved_at=datetime.utcnow() - timedelta(days=60)
            )
            db.add(deal)
        db.commit()
        
        metrics = TerritoryService.create_territory_metrics(
            db, test_user.id, "At Risk Territory"
        )
        
        assert metrics.risk_score > 50
        logger.info(f"✅ High risk score: {metrics.risk_score}")
    
    def test_territory_comparison(self, db, test_user):
        """Test comparing multiple territories"""
        # Create metrics for multiple territories
        for territory_name in ["North", "South", "East"]:
            TerritoryService.create_territory_metrics(
                db, test_user.id, territory_name
            )
        
        comparison = TerritoryService.get_territory_comparison(db, test_user.id)
        
        assert comparison is not None
        assert comparison["territories"] == 3
        logger.info(f"✅ Territory comparison: {comparison['territories']} territories")
    
    def test_optimization_recommendations(self, db, test_user):
        """Test getting optimization recommendations"""
        # Create diverse territories
        for i, territory_name in enumerate(["High Performer", "Low Performer"]):
            for j in range(3 if i == 0 else 1):
                deal = Deal(
                    user_id=test_user.id,
                    name=f"Deal {i}-{j}",
                    value=50000,
                    status="won" if i == 0 else "lost"
                )
                db.add(deal)
            db.commit()
            
            TerritoryService.create_territory_metrics(db, test_user.id, territory_name)
        
        recommendations = TerritoryService.get_optimization_recommendations(
            db, test_user.id
        )
        
        assert recommendations is not None
        logger.info(f"✅ Optimization recommendations: {len(recommendations)} categories")

# =================== INTEGRATION TESTS ===================

class TestPhase7Integration:
    """Integration tests for Phase 7 analytics"""
    
    def test_complete_deal_lifecycle_analytics(self, db, test_user):
        """Test analytics through complete deal lifecycle"""
        # Create deal
        deal = Deal(
            user_id=test_user.id,
            name="Lifecycle Deal",
            value=75000,
            stage="prospecting",
            created_at=datetime.utcnow() - timedelta(days=60)
        )
        db.add(deal)
        db.commit()
        
        # Move through stages
        stages = ["prospecting", "qualification", "proposal", "negotiation"]
        for stage in stages:
            deal.stage = stage
            deal.stage_moved_at = datetime.utcnow()
            db.commit()
        
        # Close as won
        deal.status = "won"
        deal.actual_close_date = datetime.utcnow()
        db.commit()
        
        # Analyze
        analysis = WinLossService.analyze_closed_deal(db, test_user.id, deal.id, "won")
        
        assert analysis is not None
        assert analysis.sales_cycle_days is not None
        assert analysis.sales_cycle_days > 0
        logger.info(f"✅ Complete lifecycle: {analysis.sales_cycle_days} day cycle")
    
    def test_multi_territory_analytics(self, db, test_user):
        """Test analytics across multiple territories"""
        territories = ["EMEA", "AMER", "APAC"]
        results = {}
        
        for territory in territories:
            # Create deals for each territory
            for i in range(4):
                deal = Deal(
                    user_id=test_user.id,
                    name=f"{territory} Deal {i}",
                    value=25000 * (i + 1),
                    status="won" if i % 2 == 0 else "lost"
                )
                db.add(deal)
            db.commit()
            
            metrics = TerritoryService.create_territory_metrics(
                db, test_user.id, territory
            )
            results[territory] = metrics.win_rate_pct
        
        comparison = TerritoryService.get_territory_comparison(db, test_user.id)
        
        assert comparison["territories"] == 3
        logger.info(f"✅ Multi-territory analytics: {len(results)} territories analyzed")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
