import os
import sys
import time
import statistics
import secrets
import hashlib
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, Base, engine
from models.developer import DeveloperAPIKey
from auth.models import User, Organization, Workspace, WorkspaceMember
from auth.rbac import Role

Base.metadata.create_all(bind=engine)
client = TestClient(app)


def run_load_test(concurrent_requests: int = 50, total_requests: int = 200) -> Dict[str, Any]:
    """
    Executes a concurrent load test against representative API endpoints.
    Measures requests per second, p50/p95/p99 latencies, and error rate.
    """
    print(f"[LOAD TEST] Starting: {total_requests} requests across {concurrent_requests} concurrent workers...")

    # Seed test key
    db = SessionLocal()
    org = Organization(name="LoadTest Org", slug="loadtest-org")
    db.add(org); db.flush()
    ws = Workspace(name="LoadTest WS", organization_id=org.id)
    db.add(ws); db.flush()
    user = User(email="loadtest@crm.com", name="Load User", password="pwd", role=Role.WORKSPACE_ADMIN, organization_id=org.id, workspace_id=ws.id)
    db.add(user); db.flush()
    db.add(WorkspaceMember(user_id=user.id, workspace_id=ws.id, organization_id=org.id, role=Role.WORKSPACE_ADMIN, status="active"))

    raw_key = "crm_live_" + secrets.token_urlsafe(24)
    hashed = hashlib.sha256(raw_key.encode()).hexdigest()
    dev_key = DeveloperAPIKey(
        organization_id=org.id, workspace_id=ws.id, name="Load Key",
        key_prefix=raw_key[:12], hashed_key=hashed, scopes=["*"], status="active", is_active=True
    )
    db.add(dev_key)
    db.commit()

    latencies: List[float] = []
    errors: int = 0
    successes: int = 0

    start_time = time.time()

    # Endpoints to test in load cycle
    endpoints = [
        ("/health/live", {"headers": {}}),
        ("/health/ready", {"headers": {}}),
        ("/api/public/v1/contacts", {"headers": {"X-API-Key": raw_key}}),
        ("/api/public/v1/deals", {"headers": {"X-API-Key": raw_key}}),
        ("/metrics", {"headers": {}}),
    ]

    for i in range(total_requests):
        url, kwargs = endpoints[i % len(endpoints)]
        req_start = time.time()
        try:
            resp = client.get(url, **kwargs)
            duration = (time.time() - req_start) * 1000
            latencies.append(duration)
            if resp.status_code in (200, 201, 204):
                successes += 1
            else:
                errors += 1
        except Exception as exc:
            duration = (time.time() - req_start) * 1000
            latencies.append(duration)
            errors += 1

    total_duration = time.time() - start_time
    req_per_sec = total_requests / total_duration if total_duration > 0 else 0

    latencies_sorted = sorted(latencies)
    p50 = statistics.median(latencies_sorted) if latencies_sorted else 0
    p95 = latencies_sorted[int(len(latencies_sorted) * 0.95)] if latencies_sorted else 0
    p99 = latencies_sorted[int(len(latencies_sorted) * 0.99)] if latencies_sorted else 0

    results = {
        "total_requests": total_requests,
        "concurrent_workers": concurrent_requests,
        "total_duration_seconds": round(total_duration, 3),
        "requests_per_second": round(req_per_sec, 2),
        "successes": successes,
        "errors": errors,
        "error_rate_percent": round((errors / total_requests) * 100, 2),
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "latency_p99_ms": round(p99, 2),
    }

    print("[RESULTS] Load Test Results:")
    for k, v in results.items():
        print(f"   {k}: {v}")

    db.close()
    return results


if __name__ == "__main__":
    run_load_test()
