# AI Email Automation CRM Rebuild Audit

## Architecture Map
- `backend/main.py`: FastAPI entry point with auth, Google OAuth, CRM, email, campaign, analytics, tasks, and websocket routers.
- `backend/models/crm.py`: SaaS CRM entities: contacts, leads, interactions, activities, notes, deals, campaigns, email metadata, Gmail cursors, task records, AI insights.
- `backend/crm_email`: executable Gmail incremental-sync package. `backend/email` is retained as the requested architecture folder, but not imported because `email` shadows Python's standard library.
- `backend/tasks` and `backend/workers`: Celery-first async execution with Redis-backed task status and in-memory fallback for low-friction local development.
- `backend/ai`: Ollama local model configuration, prompt compression, response cache, and idle unload hook.
- `frontend/src/crm`: lazy-loaded SaaS workspace pages, virtualized inbox, lazy body loading, campaign builder, analytics, AI task polling.

## Dependency Map
- API depends on SQLAlchemy models, auth JWT dependencies, and routers.
- Gmail sync depends on Google credentials, encrypted token access, `GmailSyncCursor`, and metadata-only Gmail requests.
- AI generation depends on queued tasks, prompt optimizer, Ollama HTTP API, and Redis/memory cache.
- Frontend depends on React Router, Axios, Recharts, Lucide, and Tailwind.

## Reusable Modules
- FastAPI app pattern, JWT auth, password hashing, Google OAuth flow, SQLite DB foundation, existing React auth context.

## Removed/Rerouted Risks
- Synchronous `/email/sync` full-body fetching is replaced with `POST /email/sync` task enqueue.
- AI generation is no longer performed in the API request path.
- Gmail list loads metadata only; full body fetch happens from `/email/body/{gmail_message_id}`.
- OAuth token encryption is supported via Fernet `TOKEN_ENCRYPTION_KEY`.
- Hardcoded JWT secret moved to environment configuration.
- Redis and Celery are optional at import time, enabling low-RAM local development without crashing.

## Optimization Strategy
- Page Gmail sync at `GMAIL_PAGE_SIZE=10`.
- Store `nextPageToken` and `after:<timestamp>` cursor.
- Use virtualized inbox rows and lazy email body fetch.
- Cache AI responses and analytics summaries in Redis with fallback memory cache.
- Use `tinyllama` by default, `num_ctx=1024`, compressed prompts, and `keep_alive` idle unload.
- Celery `worker_prefetch_multiplier=1`, solo pool in Docker Compose for Windows/low-RAM compatibility.

## Migration Strategy
- Keep the existing SQLite database file if needed, but new tables are created on startup.
- Existing `users` remain compatible. New CRM tables hydrate as Gmail metadata is synced.
- Existing legacy `emails` table remains for compatibility, but new inbox uses `email_metadata`.
- Existing Streamlit/CSV files are no longer part of runtime architecture and can be archived after validation.
