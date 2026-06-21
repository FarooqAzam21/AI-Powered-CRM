# Phase 4: Async Task Queue System - README

## Overview

Phase 4 implements a scalable, production-grade async task queue using **Celery** and **Redis**. This enables:
- Non-blocking email processing
- Background AI model inference
- Scheduled maintenance tasks
- Lead scoring and automation
- Campaign batch sending

## Architecture

### Queue System
```
Frontend/API → FastAPI → Task Router → Redis Broker → Celery Workers → Results
```

### 5 Dedicated Queues
1. **Email Queue** - Gmail sync, classification, reply generation
2. **AI Queue** - Intent detection, sentiment analysis, batch classification
3. **Leads Queue** - Scoring, follow-ups, conversions
4. **Campaigns Queue** - Batch sending, tracking
5. **Maintenance Queue** - Token cleanup, account management

### Benefits
- ✅ Non-blocking API responses
- ✅ Scalable (add workers as needed)
- ✅ Memory efficient (queue isolation)
- ✅ Retry on failure
- ✅ Task monitoring and status tracking

## Installation

### 1. Install Python Packages
```bash
pip install redis celery
```

### 2. Start Redis Server

**Linux/Mac:**
```bash
redis-server
```

**Windows (WSL2):**
```bash
wsl redis-server
```

**Docker:**
```bash
docker run -d -p 6379:6379 redis:latest
```

### 3. Verify Setup
```bash
cd backend
python setup_and_verify.py
```

## Quick Start

### Terminal 1: Start Redis
```bash
redis-server
```

### Terminal 2: Start Celery Worker
```bash
cd backend
celery -A tasks.celery_app worker --loglevel=info
```

### Terminal 3: Start Backend Server
```bash
cd backend
python app_new.py
```

### Terminal 4: Test
```bash
cd backend
python test_celery_tasks.py
```

## Task Reference

### Email Tasks (`tasks/email_tasks.py`)
| Task | Description | Queue |
|------|-------------|-------|
| `sync_gmail_emails(user_id)` | Sync emails from Gmail | email |
| `classify_email(email_id)` | AI classification | email |
| `generate_reply(email_id, tone)` | Draft reply generation | email |
| `link_email_to_contact(email_id)` | Auto-link to contact | email |

### AI Tasks (`tasks/ai_tasks.py`)
| Task | Description | Queue |
|------|-------------|-------|
| `classify_email_batch(email_ids)` | Batch classification | ai |
| `detect_intent(email_id)` | Hiring/buying/support intent | ai |
| `extract_sentiment(email_id)` | Sentiment analysis | ai |

### Lead Tasks (`tasks/lead_tasks.py`)
| Task | Description | Schedule | Queue |
|------|-------------|----------|-------|
| `score_lead(lead_id)` | 0-100 scoring | On demand | leads |
| `check_follow_ups()` | Find overdue leads | Hourly | leads |
| `convert_lead(lead_id)` | Mark as converted | On demand | leads |
| `mark_lost(lead_id, reason)` | Mark as lost | On demand | leads |

### Campaign Tasks (`tasks/campaign_tasks.py`)
| Task | Description | Schedule | Queue |
|------|-------------|----------|-------|
| `process_campaigns()` | Batch send campaigns | Every minute | campaigns |
| `send_campaign_email(campaign_id, contact_id)` | Send single email | On demand | campaigns |
| `send_follow_up_email(lead_id)` | Auto follow-up | On demand | campaigns |
| `track_email_open(campaign_id, contact_id)` | Track open | On demand | campaigns |
| `track_email_click(campaign_id, contact_id, link)` | Track click | On demand | campaigns |

### Auth Tasks (`tasks/auth_tasks.py`)
| Task | Description | Schedule | Queue |
|------|-------------|----------|-------|
| `cleanup_expired_tokens()` | Clean tokens | Daily 2 AM | maintenance |
| `disable_inactive_accounts(days)` | Disable inactive | On demand | maintenance |
| `audit_failed_logins()` | Security audit | On demand | maintenance |

## API Endpoints

### Task Status Endpoints
```bash
# Check task status
GET /api/v1/tasks/status/{task_id}

# Celery health check
GET /api/v1/tasks/health

# Classify email (async)
POST /api/v1/tasks/classify-email/{email_id}

# Score lead (async)
POST /api/v1/tasks/score-lead/{lead_id}

# Sync Gmail (async)
POST /api/v1/tasks/sync-gmail

# Generate reply (async)
POST /api/v1/tasks/generate-reply/{email_id}

# Process campaigns (async)
POST /api/v1/tasks/process-campaigns
```

### Example: Submit Classification Task
```bash
curl -X POST http://localhost:8000/api/v1/tasks/classify-email/1 \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
{
  "task_id": "abc123def456",
  "status": "pending",
  "message": "Email classification queued. Task ID: abc123def456"
}
```

### Example: Check Task Status
```bash
curl http://localhost:8000/api/v1/tasks/status/abc123def456

# Response:
{
  "task_id": "abc123def456",
  "status": "success",
  "result": {
    "category": "sales",
    "confidence": 0.95,
    "action": "reply"
  },
  "progress": 100
}
```

## Monitoring

### Command Line
```bash
# Watch task execution
celery -A tasks.celery_app events
```

### Web UI (Flower)
```bash
pip install flower

celery -A tasks.celery_app flower --port=5555

# Open: http://localhost:5555
```

## Performance Characteristics

### Memory Usage
- Base Celery: ~50MB
- Per Worker: ~100-150MB  
- Redis: ~10-20MB
- Total: Safe for 4GB system

### Processing Times
- Email sync: ~30 seconds (batch)
- AI classification: ~5 seconds per email
- Lead scoring: ~1 second
- Campaign batch: Throttled to 2 emails/minute

## Configuration

### Edit `tasks/celery_app.py` to customize:
- Broker URL: `CELERY_BROKER_URL = "redis://localhost:6379/0"`
- Result backend: `CELERY_RESULT_BACKEND = "redis://localhost:6379/1"`
- Concurrency: `worker_prefetch_multiplier = 1` (memory efficient)
- Task time limits: Set per task if needed

## Troubleshooting

### Redis not running
```
Error: Error connecting to Redis
Fix: Start Redis with: redis-server
```

### Tasks not processing
```
Error: Tasks stuck in pending state
Fix: Start Celery worker:
celery -A tasks.celery_app worker --loglevel=info
```

### Memory issues
```
Error: Worker keeps crashing
Fix: Reduce concurrency:
celery -A tasks.celery_app worker --concurrency=1
```

### Celery not importing
```
Error: ModuleNotFoundError: No module named 'celery'
Fix: pip install celery redis
```

## Next Steps (Phase 5)

After Phase 4 verification, move to:

### Phase 5: AI Model Optimization
- Ollama warmup and context reuse
- Redis caching for responses
- Token compression for long emails
- Batch AI processing

### Phase 6: Advanced CRM Features
- Deal pipeline tracking
- AI customer profiles
- Activity timelines

### Phase 7: Gmail Integration
- Incremental sync with cursors
- Real-time email updates
- Lazy loading for performance

## Files Created in Phase 4

```
backend/
├── tasks/
│   ├── celery_app.py           # Celery broker configuration
│   ├── email_tasks.py          # Email processing (4 tasks)
│   ├── ai_tasks.py             # AI processing (3 tasks)
│   ├── lead_tasks.py           # Lead management (4 tasks)
│   ├── campaign_tasks.py       # Campaign automation (5 tasks)
│   └── auth_tasks.py           # Auth & maintenance (3 tasks)
├── routers/
│   └── task_router.py          # Task status API
├── test_celery_tasks.py        # Comprehensive tests
├── setup_and_verify.py         # Setup verification
├── PHASE_4_COMPLETION.py       # This guide
└── app_new.py                  # (Updated with task router)
```

## Quick Reference

### Start Development Stack
```bash
# Terminal 1
redis-server

# Terminal 2
cd backend
celery -A tasks.celery_app worker --loglevel=info

# Terminal 3
cd backend
python app_new.py

# Terminal 4
python test_celery_tasks.py
```

### Check System Health
```bash
# All services running?
python setup_and_verify.py

# API healthy?
curl http://localhost:8000/health

# Celery healthy?
curl http://localhost:8000/api/v1/tasks/health

# Database working?
curl -X GET http://localhost:8000/api/v1/contacts \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Support

For issues, check:
1. `PHASE_4_COMPLETION.py` - Detailed setup guide
2. `test_celery_tasks.py` - Test all components
3. `setup_and_verify.py` - Verify system state
4. Redis logs: Check if broker is running
5. Celery worker terminal: Check for errors

---

**Phase 4 Status**: ✅ COMPLETE

**Ready for Phase 5**: AI Model Optimization
