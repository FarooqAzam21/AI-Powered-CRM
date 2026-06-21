# PHASE 9 DEPLOYMENT GUIDE
## Quick Start for Production Deployment

---

## 📋 Pre-Deployment Checklist

### 1. Verify All Files Created ✅
```bash
# Backend models, services, scheduler, tasks
ls -la backend/models/campaigns.py          # 280 lines
ls -la backend/schemas/campaigns.py         # 150 lines
ls -la backend/services/campaign_service.py # 400 lines
ls -la backend/scheduler/campaign_scheduler.py # 250 lines
ls -la backend/tasks/campaign_tasks.py      # 250 lines
ls -la backend/routers/campaigns.py         # 400 lines

# Frontend components
ls -la frontend/src/components/Campaigns.jsx            # 200 lines
ls -la frontend/src/components/CampaignBuilder.jsx      # 300 lines
ls -la frontend/src/components/CampaignAnalytics.jsx    # 350 lines

# Migration and documentation
ls -la backend/migrations/campaign_migration.py         # 50 lines
ls -la backend/verify_phase9.py                         # 300 lines
ls -la PHASE_9_README.md                                # 350 lines
ls -la PHASE_9_IMPLEMENTATION_SUMMARY.md                # 500 lines
```

### 2. Verify Code Quality ✅
```bash
cd backend
python verify_phase9.py

# Expected output:
# ✅ ALL VERIFICATIONS PASSED
# Phase 9 is ready for deployment!
```

### 3. Check Python Syntax ✅
```bash
python -m py_compile backend/models/campaigns.py
python -m py_compile backend/schemas/campaigns.py
python -m py_compile backend/services/campaign_service.py
python -m py_compile backend/scheduler/campaign_scheduler.py
python -m py_compile backend/tasks/campaign_tasks.py
python -m py_compile backend/routers/campaigns.py
```

---

## 🚀 Deployment Steps

### Step 1: Database Migration
```bash
cd backend

# Create campaign tables
python migrations/campaign_migration.py

# Expected output:
# 🔄 Starting campaign tables migration...
# ✅ Campaign tables created successfully
#    - Campaign
#    - CampaignSend
#    - CampaignTrack
# ✅ Migration complete!

# Verify tables were created
sqlite3 data/app.db ".tables" | grep campaign
# Should show: campaign campaign_send campaign_track
```

### Step 2: Start Backend Server
```bash
cd backend

# Terminal 1: Start FastAPI server
python app_new.py

# Expected output:
# ============================================================
# 🚀 AI CRM BACKEND SERVER
# ============================================================
# Environment: DEVELOPMENT
# API Prefix: /api/v1
# CORS Origins: ['http://localhost:5173', 'http://localhost:3000']
# ============================================================

# Check server is running
curl http://localhost:8000/health
# Expected: {"status": "healthy", ...}
```

### Step 3: Start Celery Infrastructure
```bash
# Terminal 2: Start Celery worker for campaigns
celery -A tasks.celery_app worker -Q campaigns -l info

# Expected output:
# celery@hostname ready. *** mfagic ***
# [Tasks]
#   . tasks.campaign_tasks.send_campaign_email
#   . tasks.campaign_tasks.bulk_send_campaign
#   . tasks.campaign_tasks.retry_failed_sends
#   . tasks.campaign_tasks.periodic_campaign_monitor
#   ... (8 total campaign tasks)
```

```bash
# Terminal 3: Start Celery beat scheduler
celery -A tasks.celery_app beat -l info

# Expected output:
# celery beat v5.x.x
# Starting scheduler: DatabaseScheduler
#   - monitor-active-campaigns-every-minute
#   - process-retry-sends-every-30-minutes
```

### Step 4: Verify Campaign Router Registration
```bash
# Check that campaign router is loaded
curl http://localhost:8000/api/v1/campaigns \
  -H "Authorization: Bearer <your_token>"

# Expected status: 200 OK (or 401 if no token)
# NOT 404 - which would mean router not registered
```

### Step 5: Start Frontend Development Server
```bash
cd frontend

# Terminal 4: Start Vite dev server
npm run dev

# Expected output:
# VITE v4.x ready in xxx ms
# ➜  Local:   http://localhost:5173/
# ➜  press h to show help
```

---

## ✅ Testing Endpoints

### 1. Create Campaign
```bash
curl -X POST http://localhost:8000/api/v1/campaigns \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Q4 Newsletter",
    "subject": "Hi {{first_name}}, check this out",
    "body": "Hi {{first_name}},\n\nWelcome to {{company}}!\n\nBest regards",
    "contact_ids": [1, 2, 3],
    "throttle_per_minute": 2,
    "open_tracking": true,
    "click_tracking": true
  }'

# Expected response (201 Created):
# {
#   "id": 1,
#   "name": "Q4 Newsletter",
#   "status": "draft",
#   "created_at": "2024-...",
#   ...
# }
```

### 2. List Campaigns
```bash
curl http://localhost:8000/api/v1/campaigns \
  -H "Authorization: Bearer $TOKEN"

# Expected response (200 OK):
# {
#   "items": [...],
#   "total": 1,
#   "skip": 0,
#   "limit": 20
# }
```

### 3. Get Campaign Details
```bash
curl http://localhost:8000/api/v1/campaigns/1 \
  -H "Authorization: Bearer $TOKEN"

# Expected response (200 OK):
# {
#   "id": 1,
#   "name": "Q4 Newsletter",
#   "subject": "Hi {{first_name}}, check this out",
#   "status": "draft",
#   "sends": [],
#   ...
# }
```

### 4. Start Campaign
```bash
curl -X POST http://localhost:8000/api/v1/campaigns/1/start \
  -H "Authorization: Bearer $TOKEN"

# Expected response (200 OK):
# {
#   "status": "scheduled",
#   "task_id": "abc-123-def-456",
#   "message": "Campaign started. Emails will be sent according to throttle settings."
# }

# Check Celery worker logs - you should see tasks being queued:
# [tasks] Received task: tasks.campaign_tasks.send_campaign_email[...]
```

### 5. Get Campaign Progress
```bash
curl http://localhost:8000/api/v1/campaigns/1/progress \
  -H "Authorization: Bearer $TOKEN"

# Expected response (200 OK):
# {
#   "total": 3,
#   "sent": 0,
#   "pending": 3,
#   "failed": 0,
#   "progress_percent": 0,
#   "eta_seconds": 90
# }

# Wait a few seconds and check again
# Should show "sent" increasing as emails are processed
```

### 6. Get Campaign Analytics
```bash
curl http://localhost:8000/api/v1/campaigns/1/analytics \
  -H "Authorization: Bearer $TOKEN"

# Expected response (200 OK):
# {
#   "sent_count": 3,
#   "opened_count": 0,
#   "clicked_count": 0,
#   "bounced_count": 0,
#   "failed_count": 0,
#   "open_rate": 0.0,
#   "click_rate": 0.0,
#   "bounce_rate": 0.0
# }

# After tracking events (opens/clicks), these will update
```

### 7. Get Individual Sends
```bash
curl "http://localhost:8000/api/v1/campaigns/1/sends?limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Expected response (200 OK):
# {
#   "items": [
#     {
#       "id": 1,
#       "campaign_id": 1,
#       "recipient_email": "contact@example.com",
#       "status": "sent",
#       "tracking_id": "uuid-...",
#       "opened_count": 0,
#       "clicked_count": 0,
#       "sent_at": "2024-...",
#       ...
#     }
#   ],
#   "total": 3,
#   "limit": 10
# }
```

### 8. Test Tracking (Open Pixel)
```bash
# No auth required!
curl "http://localhost:8000/api/v1/campaigns/track/{tracking_id}/open"

# Expected response:
# Binary data (1x1 transparent GIF)
# Status: 200 OK
# Content-Type: image/gif

# Check campaign sends - opened_count should increment
curl http://localhost:8000/api/v1/campaigns/1/sends \
  -H "Authorization: Bearer $TOKEN"

# Should show opened_count: 1 for that send
```

### 9. Test Click Tracking
```bash
# No auth required!
curl "http://localhost:8000/api/v1/campaigns/track/{tracking_id}/click?url=https://example.com"

# Expected response:
# HTTP 307 Temporary Redirect
# Location: https://example.com

# Check campaign sends - clicked_count should increment
curl http://localhost:8000/api/v1/campaigns/1/sends \
  -H "Authorization: Bearer $TOKEN"

# Should show clicked_count: 1 for that send
```

---

## 🔍 Monitoring & Debugging

### Check Celery Tasks Status
```bash
# List all pending tasks
celery -A tasks.celery_app inspect active

# Get task stats
celery -A tasks.celery_app inspect stats

# Monitor task events (real-time)
celery -A tasks.celery_app events
```

### Check Redis Connection
```bash
# Test Redis connectivity
redis-cli ping
# Expected: PONG

# View Celery queue contents
redis-cli LRANGE celery 0 -1  # All tasks in queue

# Monitor Redis keys
redis-cli MONITOR
```

### Check Database
```bash
# Connect to SQLite database
sqlite3 backend/data/app.db

# Check campaign tables
.tables
# Should show: campaign, campaign_send, campaign_track

# Count records
SELECT COUNT(*) FROM campaign;
SELECT COUNT(*) FROM campaign_send;
SELECT COUNT(*) FROM campaign_track;

# View campaign records
SELECT id, name, status, created_at FROM campaign;

# View sends for campaign 1
SELECT id, recipient_email, status, sent_at FROM campaign_send WHERE campaign_id = 1;

# View tracking events
SELECT event_type, timestamp FROM campaign_track LIMIT 10;
```

### Check Logs
```bash
# Backend logs
tail -f backend/logs/app.log

# Celery worker logs
# Check terminal where celery worker is running

# Celery beat logs
# Check terminal where celery beat is running

# Database logs
sqlite3 backend/data/app.db "PRAGMA journal_mode;"
```

---

## 🧪 Integration Testing Checklist

### Frontend Integration
- [ ] Navigate to Campaigns page in dashboard
- [ ] See "Create Campaign" button
- [ ] Click "Create Campaign" - opens CampaignBuilder modal
- [ ] Fill in campaign details and submit
- [ ] Campaign appears in campaigns list with "draft" status
- [ ] Click "Start" button
- [ ] See status change to "running" or "scheduled"
- [ ] Click "View" - opens CampaignAnalytics dashboard
- [ ] See real-time metrics updating
- [ ] See charts loading correctly

### Throttling Test
- [ ] Create campaign with 10 contacts
- [ ] Start campaign
- [ ] Monitor send_campaign_email tasks in Celery
- [ ] Verify emails sent with ~30 second spacing (2/min)
- [ ] Take 10 sends × 30 seconds = 5 minutes total

### Retry Test
- [ ] Simulate email send failure (stop EmailService)
- [ ] Start campaign with 5 contacts
- [ ] Check failed sends in analytics
- [ ] Restart EmailService
- [ ] Wait for retry_failed_sends periodic task (30 min schedule)
- [ ] Verify failed emails are retried

### Tracking Test
- [ ] Create campaign and start
- [ ] Get tracking_id from campaign_send record
- [ ] Simulate open: `curl http://localhost:8000/api/v1/campaigns/track/{id}/open`
- [ ] Verify opened_count incremented
- [ ] Simulate click: `curl http://localhost:8000/api/v1/campaigns/track/{id}/click?url=...`
- [ ] Verify clicked_count incremented
- [ ] Check analytics updated in real-time

### Performance Test
- [ ] Create campaign with 1000 contacts
- [ ] Start campaign
- [ ] Measure time to queue all tasks (should be < 5 seconds)
- [ ] Monitor CPU/Memory during sending
- [ ] Verify no OOM errors
- [ ] Confirm all 1000 emails queued

---

## 📊 Production Configuration

### Environment Variables (.env)
```bash
# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Campaign Settings
CAMPAIGN_BATCH_SIZE=5              # Emails per batch
CAMPAIGN_THROTTLE_SECONDS=30       # Seconds between batches (= 2/min)
CAMPAIGN_MAX_RETRIES=3             # Retry attempts
CAMPAIGN_TRACKING_ENABLED=true     # Enable pixel/click tracking

# Email Service
EMAIL_SERVICE_PROVIDER=gmail       # or sendgrid, mailgun, etc
GMAIL_SENDER_EMAIL=noreply@crm.com

# Logging
LOG_LEVEL=INFO                      # DEBUG for development
```

### Redis Configuration
```bash
# Ensure Redis is running with sufficient memory
redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru

# Or in /etc/redis/redis.conf:
maxmemory 512mb
maxmemory-policy allkeys-lru
```

### Celery Worker Configuration
```bash
# Production: Multiple workers
celery -A tasks.celery_app worker -Q campaigns -c 4 --loglevel=info
# -Q campaigns: Only handle campaign tasks
# -c 4: 4 concurrent workers
# --loglevel=info: Log level

# Production: Beat scheduler (single instance)
celery -A tasks.celery_app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# OR using crontab:
# Add to crontab for periodic monitoring
* * * * * celery -A tasks.celery_app call tasks.campaign_tasks.periodic_campaign_monitor
```

---

## 🎯 Success Criteria

✅ **All files created and verified**
- 11 new files created (models, schemas, services, scheduler, tasks, routers, components)
- 2 files modified (app_new.py, celery_app.py)

✅ **Database tables created**
- Campaign table with all fields
- CampaignSend table with tracking
- CampaignTrack table for events

✅ **API endpoints functional**
- CRUD operations working
- Campaign lifecycle actions working
- Real-time analytics updating
- Tracking endpoints (no auth) functional

✅ **Celery tasks queued and executing**
- send_campaign_email tasks executing
- Throttling working (2 emails/minute)
- Retry logic functional
- Periodic monitoring running

✅ **Frontend components rendering**
- Campaigns list displaying
- CampaignBuilder form functional
- CampaignAnalytics dashboard updating
- Real-time metrics visible

✅ **End-to-end flow working**
- Create campaign → Start → Monitor → Track → Complete

---

## 🚨 Troubleshooting

### Campaign won't start
**Problem:** POST /campaigns/{id}/start returns error
**Solution:**
1. Verify campaign status is "draft": `SELECT status FROM campaign WHERE id=1;`
2. Verify contacts exist: `SELECT COUNT(*) FROM contact;`
3. Check Celery worker is running: `celery -A tasks.celery_app inspect active`
4. Check Redis connection: `redis-cli ping`

### Emails not sending
**Problem:** CampaignSend records created but status stays "pending"
**Solution:**
1. Verify Celery worker is running for campaigns queue
2. Check EmailService configuration in app
3. Verify Gmail API credentials if using Gmail
4. Check worker logs for errors
5. Manually trigger send: `celery -A tasks.campaign_tasks.send_campaign_email --task-id=1`

### Tracking not working
**Problem:** Open/click tracking pixel not recording events
**Solution:**
1. Verify open_tracking=true in campaign
2. Test tracking URL directly: `curl http://localhost:8000/api/v1/campaigns/track/{id}/open`
3. Check CampaignTrack table: `SELECT COUNT(*) FROM campaign_track;`
4. Verify tracking tasks in Celery worker logs
5. Restart Celery worker

### Analytics not updating
**Problem:** Metrics showing zeros or not updating in real-time
**Solution:**
1. Verify send tasks are completing successfully
2. Check update_campaign_analytics task is running
3. Manually trigger: `celery -A tasks.campaign_tasks.update_campaign_analytics.delay(1)`
4. Check database: `SELECT * FROM campaign WHERE id=1;`

---

## ✅ Final Checklist Before Going Live

- [ ] Database migration completed successfully
- [ ] All files have zero syntax errors
- [ ] verify_phase9.py runs with all tests passing
- [ ] Backend server starts without errors
- [ ] Celery worker starts without errors
- [ ] Celery beat scheduler starts without errors
- [ ] Campaign endpoints return 200 OK
- [ ] Test campaign created and started successfully
- [ ] Frontend displays campaigns correctly
- [ ] Real-time metrics updating in frontend
- [ ] Tracking pixel working (opens recorded)
- [ ] Click tracking working (clicks recorded)
- [ ] Retry logic tested and working
- [ ] Throttling verified (2 emails/minute)
- [ ] Documentation reviewed

---

## 🎉 Deployment Complete!

Once all checks pass, Phase 9 is production-ready:
- ✅ 2,610+ lines of code across 11 files
- ✅ 14 REST API endpoints
- ✅ 8 Celery async tasks
- ✅ 3 React components
- ✅ Enterprise-grade throttling and retry logic
- ✅ Real-time analytics dashboard
- ✅ Production-ready error handling

**Next Phase: Phase 10 - Frontend Rebuild** (Modern React Dashboard)

---

**Support:** Check PHASE_9_README.md or PHASE_9_IMPLEMENTATION_SUMMARY.md for detailed documentation.
