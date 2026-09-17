"""
Real-time Dashboard Models - Phase 8
Re-exported from ws_manager.dashboard_models to avoid package shadowing collisions
"""
from ws_manager.dashboard_models import (
    EventType,
    WebSocketMessage,
    SubscriptionMessage,
    DealUpdateEvent,
    DealStageChangeEvent,
    DealClosedEvent,
    TerritoryMetricsEvent,
    TerritoryOpportunityAlert,
    TerritoryRiskAlert,
    ForecastUpdateEvent,
    ForecastAlertEvent,
    WinLossAnalysisEvent,
    ActivityEvent,
    RecommendationEvent,
    ConnectionEstablishedEvent,
    SubscriptionConfirmedEvent,
    ErrorEvent,
    DashboardMetrics,
    PipelineSnapshot,
    TerritorySnapshot,
)

__all__ = [
    "EventType",
    "WebSocketMessage",
    "SubscriptionMessage",
    "DealUpdateEvent",
    "DealStageChangeEvent",
    "DealClosedEvent",
    "TerritoryMetricsEvent",
    "TerritoryOpportunityAlert",
    "TerritoryRiskAlert",
    "ForecastUpdateEvent",
    "ForecastAlertEvent",
    "WinLossAnalysisEvent",
    "ActivityEvent",
    "RecommendationEvent",
    "ConnectionEstablishedEvent",
    "SubscriptionConfirmedEvent",
    "ErrorEvent",
    "DashboardMetrics",
    "PipelineSnapshot",
    "TerritorySnapshot",
]
