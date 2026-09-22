from fastapi import APIRouter, Response
from services.metrics_service import metrics_service

router = APIRouter(tags=["Production Operations & Observability"])


@router.get("/metrics", summary="Prometheus Exposition Metrics Endpoint")
def get_metrics():
    """
    Exposes application metrics formatted for Prometheus / OpenTelemetry collectors.
    """
    content = metrics_service.generate_prometheus_format()
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8")
