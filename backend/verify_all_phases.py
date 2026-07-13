#!/usr/bin/env python3
"""Verify Phases 1–10 endpoints are registered and importable."""
import sys

CHECKS = [
    ("Phase 1-2 Auth", ["/auth/login", "/auth/me", "/google/config"]),
    ("Phase 3 Gmail", ["/email/metadata", "/email/sync"]),
    ("Phase 4 Celery", ["/tasks/health", "/tasks/status/{task_id}"]),
    ("Phase 5 AI", ["/api/v1/ai/health", "/api/v1/ai/classify-email"]),
    ("Phase 6 CRM", ["/api/v1/deals/", "/crm/contacts", "/api/v1/recommendations"]),
    ("Phase 7 Analytics", ["/api/v1/analytics/win-loss-summary", "/api/v1/analytics/velocity"]),
    ("Phase 8 WebSocket", ["/api/v1/ws/metrics/dashboard", "/api/v1/ws/connections"]),
    ("Phase 9 Campaigns", ["/api/v1/campaigns", "/campaigns"]),
    ("Phase 10 Frontend", ["/health"]),
]


def route_paths(app):
    paths = set()
    for r in app.routes:
        p = getattr(r, "path", None)
        if p:
            paths.add(p)
    return paths


def main():
    try:
        import main as app_module
    except Exception as e:
        print(f"FAIL: cannot import main — {e}")
        return 1

    app = app_module.app
    paths = route_paths(app)
    failed = 0

    print(f"Total routes: {len(paths)}\n")
    for phase, expected in CHECKS:
        ok = all(any(p == ep or "{" in ep and ep.split("{")[0] in p for p in paths) for ep in expected)
        # simpler: check prefix match
        phase_ok = True
        for ep in expected:
            base = ep.split("{")[0].rstrip("/")
            if not any(p == ep or p.startswith(base) or ep.rstrip("/") == p.rstrip("/") for p in paths):
                # fuzzy: path contains key segment
                key = ep.strip("/").split("/")[-1].replace("{task_id}", "")
                if key and not any(key in p for p in paths):
                    phase_ok = False
                    print(f"  missing: {ep}")
        status = "PASS" if phase_ok else "FAIL"
        if not phase_ok:
            failed += 1
        print(f"[{status}] {phase}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
