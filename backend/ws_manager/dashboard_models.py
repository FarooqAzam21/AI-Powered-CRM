"""
Real-time Dashboard Models - Phase 8
Pydantic models for WebSocket messages and dashboard events
"""
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    """Types of real-time events"""
    DEAL_CREATED = "deal_created"
    DEAL_UPDATED = "deal_updated"
    DEAL_STAGE_CHANGED = "deal_stage_changed"
    DEAL_CLOSED = "deal_closed"
    
    TERRITORY_METRIC_UPDATE = "territory_metric_update"
    TERRITORY_OPPORTUNITY_ALERT = "territory_opportunity_alert"
    TERRITORY_RISK_ALERT = "territory_risk_alert"
    
    FORECAST_UPDATED = "forecast_updated"
    FORECAST_ALERT = "forecast_alert"
    
    WIN_LOSS_ANALYSIS = "win_loss_analysis"
    CYCLE_METRIC_UPDATE = "cycle_metric_update"
    
    ACTIVITY_CREATED = "activity_created"
    RECOMMENDATION_GENERATED = "recommendation_generated"
    
    CONNECTION_ESTABLISHED = "connection_established"
    SUBSCRIPTION_CONFIRMED = "subscription_confirmed"
    ERROR = "error"

class WebSocketMessage(BaseModel):
    """Base WebSocket message"""
    type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]

class SubscriptionMessage(BaseModel):
    """Subscribe to channel"""
    action: str = "subscribe"  # subscribe, unsubscribe
    channel: str  # deals, territories, analytics, forecast
    deal_ids: Optional[List[int]] = None
    territories: Optional[List[str]] = None

class DealUpdateEvent(BaseModel):
    """Real-time deal update"""
    type: EventType = EventType.DEAL_UPDATED
    deal_id: int
    deal_name: str
    stage: str
    probability: float
    value: float
    status: str
    expected_close_date: Optional[datetime]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class DealStageChangeEvent(BaseModel):
    """Deal moved to new stage"""
    type: EventType = EventType.DEAL_STAGE_CHANGED
    deal_id: int
    deal_name: str
    old_stage: str
    new_stage: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class DealClosedEvent(BaseModel):
    """Deal won/lost"""
    type: EventType = EventType.DEAL_CLOSED
    deal_id: int
    deal_name: str
    outcome: str  # won, lost
    value: float
    root_cause: Optional[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class TerritoryMetricsEvent(BaseModel):
    """Territory metrics update"""
    type: EventType = EventType.TERRITORY_METRIC_UPDATE
    territory_name: str
    win_rate_pct: float
    pipeline_value: float
    revenue_actual: float
    revenue_target: float
    quota_attainment_pct: float
    opportunity_score: float
    risk_score: float
    active_contacts: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class TerritoryOpportunityAlert(BaseModel):
    """High-opportunity territory alert"""
    type: EventType = EventType.TERRITORY_OPPORTUNITY_ALERT
    territory_name: str
    opportunity_score: float
    reason: str
    action_recommended: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class TerritoryRiskAlert(BaseModel):
    """At-risk territory alert"""
    type: EventType = EventType.TERRITORY_RISK_ALERT
    territory_name: str
    risk_score: float
    stalled_deals_count: int
    lost_deals_recent: int
    action_recommended: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class ForecastUpdateEvent(BaseModel):
    """Forecast updated"""
    type: EventType = EventType.FORECAST_UPDATED
    month: str
    forecasted_revenue: float
    current_pipeline: float
    confidence_pct: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class ForecastAlertEvent(BaseModel):
    """Forecast alert (on track/at risk/exceeding)"""
    type: EventType = EventType.FORECAST_ALERT
    month: str
    status: str  # on_track, at_risk, exceeding
    reason: str
    action_recommended: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class WinLossAnalysisEvent(BaseModel):
    """Win/loss analysis available"""
    type: EventType = EventType.WIN_LOSS_ANALYSIS
    deal_id: int
    outcome: str
    root_cause: str
    key_factors: List[str]
    lessons_learned: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class ActivityEvent(BaseModel):
    """Activity created"""
    type: EventType = EventType.ACTIVITY_CREATED
    activity_id: int
    contact_id: int
    contact_name: str
    activity_type: str
    notes: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class RecommendationEvent(BaseModel):
    """AI recommendation generated"""
    type: EventType = EventType.RECOMMENDATION_GENERATED
    recommendation_id: int
    contact_id: Optional[int]
    deal_id: Optional[int]
    recommendation_type: str
    title: str
    description: str
    confidence_score: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class ConnectionEstablishedEvent(BaseModel):
    """Connection established confirmation"""
    type: EventType = EventType.CONNECTION_ESTABLISHED
    user_id: int
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    message: str = "WebSocket connection established"
    
    class Config:
        use_enum_values = True

class SubscriptionConfirmedEvent(BaseModel):
    """Subscription confirmation"""
    type: EventType = EventType.SUBSCRIPTION_CONFIRMED
    channel: str
    status: str = "subscribed"
    deal_ids: Optional[List[int]] = None
    territories: Optional[List[str]] = None
    
    class Config:
        use_enum_values = True

class ErrorEvent(BaseModel):
    """Error message"""
    type: EventType = EventType.ERROR
    error_code: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True

class DashboardMetrics(BaseModel):
    """Real-time dashboard metrics snapshot"""
    timestamp: datetime
    user_id: int
    
    # Deal metrics
    open_deals_count: int
    won_deals_count: int
    lost_deals_count: int
    total_pipeline_value: float
    
    # Territory metrics
    territories_count: int
    territories_at_risk: int
    territories_high_opportunity: int
    
    # Forecast metrics
    forecast_month: str
    forecast_accuracy_pct: float
    current_vs_forecast: float
    
    # Activity metrics
    recent_activities_count: int
    active_contacts_count: int
    
    class Config:
        use_enum_values = True

class PipelineSnapshot(BaseModel):
    """Real-time pipeline snapshot"""
    timestamp: datetime
    stages: Dict[str, Any]  # {stage: {count, value, avg_deal_size}}
    by_probability: Dict[str, Any]  # {probability_range: {count, value}}
    velocity_deals_per_day: float
    velocity_revenue_per_day: float
    average_deal_size: float
    median_cycle_days: int
    
    class Config:
        use_enum_values = True

class TerritorySnapshot(BaseModel):
    """Real-time territory performance snapshot"""
    timestamp: datetime
    territories: Dict[str, Dict[str, Any]]  # {territory: {metrics}}
    top_performers: List[str]
    at_risk: List[str]
    high_opportunity: List[str]
    total_pipeline: float
    total_revenue_target: float
    total_revenue_actual: float
    
    class Config:
        use_enum_values = True
