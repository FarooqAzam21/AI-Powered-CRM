# P7 — Enterprise Operations, Disaster Recovery & Production Deployment Runbook

## 1. System Architecture Overview

The AI-Powered CRM production deployment consists of:
- **API Server** (FastAPI / Uvicorn, multi-worker behind Nginx reverse proxy)
- **Database** (PostgreSQL 15 with connection pooling, multi-tenant workspace isolation, and automated B-Tree performance indexing)
- **Cache & Rate Limiting** (Redis 7 with resilient MemoryCache failover and TTL expiration)
- **Background Worker Fleet** (Celery 5 async task workers & Celery Beat scheduler with exponential backoff retries and dead-letter handling)
- **AI Inference Engine** (Ollama service for local copilot, RAG, and agent completions)

---

## 2. Disaster Recovery Strategy (DR)

### Backup Frequency & Schedule
- **Database (PostgreSQL)**: Full daily physical `pg_dump` snapshot + continuous WAL archiving for Point-In-Time Recovery (PITR).
- **Retention**: Daily backups retained for 30 days, monthly backups retained for 1 year.
- **Encryption**: All backups encrypted at rest using AES-256 (`gpg --symmetric`).

### Restore Procedure (Tested Step-by-Step)
1. **Prepare Target Database**:
   ```bash
   createdb -h localhost -U postgres -O crm_user crm_restore_db
   ```
2. **Decrypt Snapshot**:
   ```bash
   gpg --decrypt backup_crm_2026-09-22.sql.gpg > backup_crm_2026-09-22.sql
   ```
3. **Restore Data**:
   ```bash
   psql -h localhost -U crm_user -d crm_restore_db -f backup_crm_2026-09-22.sql
   ```
4. **Verify Schema & Indexes**:
   ```bash
   python -m backend.db_schema
   ```

### Tested Failure Recovery Scenarios

| Scenario | Detection Mechanism | Immediate System Impact | Automated Recovery Action |
| :--- | :--- | :--- | :--- |
| **PostgreSQL Outage** | `/health/ready` returns 503 (`database: unhealthy`) | Write API requests return 500 (`DATABASE_ERROR`) | Pool auto-reconnects (`pool_pre_ping=True`). Failover to DB standby replica. |
| **Redis Outage** | `/health/ready` returns 200 (`redis: degraded`) | Caching falls back to local `MemoryCache`. Rate limiting uses local memory. | Resilient client retries connection automatically; core DB CRUD remains 100% operational. |
| **Celery Worker Crash** | Celery beat queue backlog increases | Background email sync & webhooks pause | Supervisor/Docker restarts worker container (`task_acks_late=True` prevents task loss). |
| **Ollama AI Unreachable** | `/health/ready` reports `ollama_ai: degraded` | AI copilot/agents return structured 503 (`ai_service_unavailable`) | Non-blocking. Core CRM contacts, deals, workflows, and billing remain fully functional. |
| **Outbound Webhook Failure** | HTTP response timeouts or 5xx from recipient | Outbound webhook delivery fails | 5 exponential backoff retries (30s, 2m, 10m). Persistent failure (>20) auto-deactivates endpoint. |

---

## 3. Security Hardening Checklist

- **Authentication & RBAC**: Mandatory JWT with refresh token rotation + scope guards on Public API v1.
- **Secret Management**: Production configuration validates non-default `JWT_SECRET_KEY` and non-empty `TOKEN_ENCRYPTION_KEY`.
- **SSRF Protection**: Outbound webhooks validated against private subnets (`127.0.0.1`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254`).
- **Audit Logging**: `APIAuditMiddleware` records request latency, IP address, workspace ID, and HTTP status codes.
- **Redaction**: Structured JSON logging automatically redacts passwords, tokens, API keys, and sensitive authorization headers.
