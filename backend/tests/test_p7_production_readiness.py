"""
P7 — Production Infrastructure, Observability, Scalability & Disaster Recovery Test Suite

Tests cover:
  1. Liveness (/health/live) & Readiness (/health/ready) probes
  2. Request correlation (X-Request-ID propagation)
  3. Structured error envelopes ({error: {code, message, request_id}})
  4. Prometheus metrics exposition (/metrics)
  5. SSRF protection guard (blocking loopback, private RFC-1918, metadata IPs)
  6. Distributed tracing W3C traceparent helper
  7. Production configuration validation (detecting dev secrets in production mode)
  8. Resilient Redis & MemoryCache fallback
  9. Celery task signal metrics tracking
"""

import json
import pytest
from fastapi.testclient import TestClient
from main import app
from config.settings import Settings, get_settings
from utils.ssrf_guard import is_ssrf_safe_url
from utils.tracer import get_w3c_traceparent, parse_w3c_traceparent, SimpleSpan
from cache.redis_client import MemoryCache, ResilientRedisClient
from services.metrics_service import metrics_service

client = TestClient(app)


# ===========================================================================
# 1. HEALTH PROBES & READINESS
# ===========================================================================

class TestHealthProbes:
    def test_liveness_probe_returns_200(self):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert "service" in data

    def test_readiness_probe_returns_status(self):
        resp = client.get("/health/ready")
        assert resp.status_code in (200, 503)
        data = resp.json()
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
        # Ollama AI must be marked non-blocking
        assert data["checks"]["ollama_ai"]["blocking"] is False


# ===========================================================================
# 2. REQUEST CORRELATION (X-Request-ID)
# ===========================================================================

class TestRequestCorrelation:
    def test_request_id_generated_if_missing(self):
        resp = client.get("/health/live")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers
        assert resp.headers["X-Request-ID"].startswith("req_")

    def test_incoming_request_id_preserved(self):
        custom_id = "req_custom_test_correlation_12345"
        resp = client.get("/health/live", headers={"X-Request-ID": custom_id})
        assert resp.status_code == 200
        assert resp.headers.get("X-Request-ID") == custom_id


# ===========================================================================
# 3. STRUCTURED ERROR ENVELOPES
# ===========================================================================

class TestStructuredErrorHandling:
    def test_404_error_envelope_structure(self):
        resp = client.get("/api/public/v1/non_existent_route_999")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "request_id" in data["error"]
        assert data["error"]["code"] == "NOT_FOUND"

    def test_validation_error_envelope_structure(self):
        # Invalid payload to trigger 422
        resp = client.post("/api/public/v1/contacts", json={"invalid_field": 123})
        assert resp.status_code in (401, 422)
        data = resp.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]


# ===========================================================================
# 4. PROMETHEUS METRICS EXPOSITION
# ===========================================================================

class TestMetricsExposition:
    def test_metrics_endpoint_returns_prometheus_format(self):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]
        text = resp.text
        assert "http_requests_total" in text
        assert "crm_contacts_created_total" in text
        assert "db_queries_total" in text
        assert "redis_hits_total" in text


# ===========================================================================
# 5. SSRF SECURITY GUARD
# ===========================================================================

class TestSSRFProtection:
    def test_loopback_ip_blocked(self):
        safe, reason = is_ssrf_safe_url("http://127.0.0.1/webhook")
        assert safe is False
        assert "loopback" in reason.lower()

    def test_localhost_domain_blocked(self):
        safe, reason = is_ssrf_safe_url("http://localhost:8000/webhook")
        assert safe is False
        assert "internal domain" in reason.lower()

    def test_private_rfc1918_ip_blocked(self):
        for private_ip in ["http://10.0.0.1/wh", "http://172.16.0.5/wh", "http://192.168.1.100/wh"]:
            safe, reason = is_ssrf_safe_url(private_ip)
            assert safe is False, f"Expected {private_ip} to be blocked"

    def test_cloud_metadata_ip_blocked(self):
        safe, reason = is_ssrf_safe_url("http://169.254.169.254/latest/meta-data/")
        assert safe is False

    def test_public_url_permitted(self):
        safe, reason = is_ssrf_safe_url("https://hooks.slack.com/services/123/456")
        assert safe is True


# ===========================================================================
# 6. DISTRIBUTED TRACING HELPERS
# ===========================================================================

class TestDistributedTracing:
    def test_w3c_traceparent_format(self):
        header = get_w3c_traceparent()
        assert header.startswith("00-")
        assert header.endswith("-01")
        parsed = parse_w3c_traceparent(header)
        assert parsed is not None
        assert "trace_id" in parsed
        assert "span_id" in parsed

    def test_simple_span_context_manager(self):
        with SimpleSpan("test_operation") as span:
            assert span.name == "test_operation"
        assert span.duration_ms >= 0


# ===========================================================================
# 7. PRODUCTION CONFIGURATION VALIDATION
# ===========================================================================

class TestProductionConfigValidation:
    def test_production_mode_detects_default_jwt_secret(self):
        s = Settings()
        s.environment = "production"
        s.jwt_secret_key = "dev-only-change-me"
        s.token_encryption_key = ""
        with pytest.raises(RuntimeError) as exc_info:
            s.validate_for_production()
        assert "JWT_SECRET_KEY" in str(exc_info.value)

    def test_production_mode_passes_with_secure_keys(self):
        s = Settings()
        s.environment = "production"
        s.jwt_secret_key = "secure_prod_jwt_secret_key_12345"
        s.token_encryption_key = "secure_token_enc_key_67890"
        s.validate_for_production()  # Should not raise


# ===========================================================================
# 8. REDIS RELIABILITY & MEMORY CACHE FALLBACK
# ===========================================================================

class TestRedisReliability:
    def test_memory_cache_fallback_operations(self):
        mem = MemoryCache()
        mem.setex("key1", 60, "val1")
        assert mem.get("key1") == "val1"
        assert mem.incr("counter") == 1
        assert mem.incr("counter") == 2
        mem.delete("key1")
        assert mem.get("key1") is None

    def test_resilient_redis_client_handles_unreachable_url(self):
        resilient = ResilientRedisClient("redis://invalid_host_999:6379/0")
        resilient.setex("test_key", 10, "test_val")
        assert resilient.get("test_key") == "test_val"
