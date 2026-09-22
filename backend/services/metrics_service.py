import threading
import time
from typing import Dict

class MetricsService:
    """
    Lightweight, thread-safe application metrics collector.
    Formats metrics in standard Prometheus exposition text format.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_metrics()
            return cls._instance

    def _init_metrics(self):
        self.counters: Dict[str, float] = {
            "http_requests_total": 0,
            "http_requests_2xx_total": 0,
            "http_requests_4xx_total": 0,
            "http_requests_5xx_total": 0,
            "db_queries_total": 0,
            "db_slow_queries_total": 0,
            "redis_hits_total": 0,
            "redis_misses_total": 0,
            "redis_errors_total": 0,
            "celery_tasks_queued_total": 0,
            "celery_tasks_failed_total": 0,
            "crm_contacts_created_total": 0,
            "crm_deals_created_total": 0,
            "workflows_executed_total": 0,
            "webhooks_dispatched_total": 0,
            "ai_requests_total": 0,
            "ai_failures_total": 0,
            "quota_violations_total": 0,
        }
        self.latency_sum: Dict[str, float] = {
            "http_request_duration_seconds": 0.0,
            "db_query_duration_seconds": 0.0,
            "ai_request_duration_seconds": 0.0,
        }
        self.gauges: Dict[str, float] = {
            "db_pool_active_connections": 0,
            "redis_memory_used_bytes": 0,
        }

    def inc(self, metric_name: str, amount: float = 1.0):
        with self._lock:
            if metric_name in self.counters:
                self.counters[metric_name] += amount
            else:
                self.counters[metric_name] = amount

    def observe_latency(self, metric_name: str, duration_seconds: float):
        with self._lock:
            if metric_name in self.latency_sum:
                self.latency_sum[metric_name] += duration_seconds
            else:
                self.latency_sum[metric_name] = duration_seconds

    def set_gauge(self, metric_name: str, value: float):
        with self._lock:
            self.gauges[metric_name] = value

    def generate_prometheus_format(self) -> str:
        with self._lock:
            lines = []
            lines.append("# HELP http_requests_total Total number of HTTP requests")
            lines.append("# TYPE http_requests_total counter")
            lines.append(f"http_requests_total {self.counters.get('http_requests_total', 0)}")
            lines.append(f"http_requests_status_group{{group=\"2xx\"}} {self.counters.get('http_requests_2xx_total', 0)}")
            lines.append(f"http_requests_status_group{{group=\"4xx\"}} {self.counters.get('http_requests_4xx_total', 0)}")
            lines.append(f"http_requests_status_group{{group=\"5xx\"}} {self.counters.get('http_requests_5xx_total', 0)}")

            lines.append("\n# HELP crm_domain_events_total Total CRM domain events")
            lines.append("# TYPE crm_domain_events_total counter")
            lines.append(f"crm_contacts_created_total {self.counters.get('crm_contacts_created_total', 0)}")
            lines.append(f"crm_deals_created_total {self.counters.get('crm_deals_created_total', 0)}")
            lines.append(f"workflows_executed_total {self.counters.get('workflows_executed_total', 0)}")
            lines.append(f"webhooks_dispatched_total {self.counters.get('webhooks_dispatched_total', 0)}")

            lines.append("\n# HELP ai_requests_total Total AI platform prompt completions")
            lines.append("# TYPE ai_requests_total counter")
            lines.append(f"ai_requests_total {self.counters.get('ai_requests_total', 0)}")
            lines.append(f"ai_failures_total {self.counters.get('ai_failures_total', 0)}")

            lines.append("\n# HELP db_operations_total Total DB queries and slow queries")
            lines.append("# TYPE db_operations_total counter")
            lines.append(f"db_queries_total {self.counters.get('db_queries_total', 0)}")
            lines.append(f"db_slow_queries_total {self.counters.get('db_slow_queries_total', 0)}")

            lines.append("\n# HELP redis_operations_total Total Redis cache operations")
            lines.append("# TYPE redis_operations_total counter")
            lines.append(f"redis_hits_total {self.counters.get('redis_hits_total', 0)}")
            lines.append(f"redis_misses_total {self.counters.get('redis_misses_total', 0)}")
            lines.append(f"redis_errors_total {self.counters.get('redis_errors_total', 0)}")

            lines.append("\n# HELP quota_violations_total Total billing quota violations")
            lines.append("# TYPE quota_violations_total counter")
            lines.append(f"quota_violations_total {self.counters.get('quota_violations_total', 0)}")

            return "\n".join(lines) + "\n"

metrics_service = MetricsService()
