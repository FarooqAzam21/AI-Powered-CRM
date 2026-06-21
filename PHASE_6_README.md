# Phase 6: Advanced CRM Features - Quick Reference

## Overview
Phase 6 adds advanced CRM capabilities: deal pipelines, AI customer profiles, activity timelines, relationship graphs, and intelligent recommendations.

## Key Features

### 1. Deal Pipeline Management
**Service**: `services/deal_service.py`
**Models**: Deal, DealActivity

```python
# Create deal
deal = DealService.create_deal(db, user_id, contact_id, "Deal Name", 50000, "prospecting")

# Move through pipeline
DealService.move_deal_stage(db, deal_id, "qualification")

# Add activity
DealService.add_activity(db, deal_id, "proposal_sent", "Description", value_impact=10000)

# Get pipeline summary
summary = DealService.get_pipeline_summary(db, user_id)
```

**Pipeline Stages**: prospecting → qualification → proposal → negotiation → won/lost

**Auto-Calculated Probabilities**:
- Prospecting: 10%
- Qualification: 25%
- Proposal: 50%
- Negotiation: 75%
- Won: 100%
- Lost: 0%

### 2. AI-Generated Customer Profiles
**Service**: `services/profile_service.py`
**Model**: CustomerProfile

```python
# Generate profile from email history
profile = CustomerProfileService.generate_profile(db, contact_id, use_cache=True)

# Profile includes:
# - AI summary
# - Buyer persona detection
# - Pain points extraction
# - Communication style analysis
# - Interest detection
# - Tech stack identification
# - Response time analytics
```

**Profile Components**:
- Summary: AI-generated 2-3 sentence overview
- Buyer Persona: Decision Maker, Technical Influencer, End User, Influencer
- Pain Points: Extracted from emails using keyword analysis
- Interests: Detected from email content
- Communication Style: Professional, Casual, Technical, etc.
- Engagement Level: High, Medium, Low
- Technologies Used: Detected SaaS/tools mentioned

### 3. Activity Timeline Tracking
**Service**: `services/activity_service.py`
**Model**: Activity (enhanced)

```python
# Record activity
activity = ActivityTimelineService.record_activity(
    db, user_id, contact_id, "call", "Discussed ROI", "Follow-up call"
)

# Get timeline (last 30 days, max 50 events)
timeline = ActivityTimelineService.get_contact_timeline(db, contact_id)

# Get summary
summary = ActivityTimelineService.get_user_activity_summary(db, user_id, days=7)

# Get active contacts
active = ActivityTimelineService.get_active_contacts(db, user_id, days=7)
```

**Activity Types**: email_sent, email_received, call, meeting, note, task_completed, stage_change, proposal_sent, deal_created

### 4. Contact Relationship Mapping
**Service**: `services/relationship_service.py`
**Model**: ContactRelationship

```python
# Link contacts
rel = RelationshipService.link_contacts(db, user_id, from_id, to_id, "mentions")

# Get contact relationships
relationships = RelationshipService.get_contact_relationships(db, contact_id)

# Build graph visualization
graph = RelationshipService.build_relationship_graph(db, user_id)
# Returns: {nodes: [...], edges: [...], stats: {...}}

# Identify key influencers
influencers = RelationshipService.identify_key_influencers(db, user_id, limit=10)

# Find connection path
path = RelationshipService.get_connection_path(db, contact1_id, contact2_id)

# Company relationships
company_data = RelationshipService.get_company_relationships(db, user_id, "ACME Corp")
```

**Relationship Types**: mentions, cc'd_with, replied_to, forwarded_to

### 5. AI Recommendation Engine
**Service**: `services/recommendation_service.py`
**Model**: AIRecommendation

```python
# Generate recommendations for contact
recs = RecommendationEngine.generate_contact_recommendations(db, user_id, contact_id)

# Get active recommendations
active_recs = RecommendationEngine.get_active_recommendations(db, user_id, limit=10)

# Mark recommendation as actioned
RecommendationEngine.mark_recommendation_actioned(db, recommendation_id)
```

**Recommendation Types**:
- next_action: What to do next
- best_time: When to reach out
- template_use: Suggested email template
- follow_up_needed: Follow-up action
- deal_strategy: Sales strategy for deal
- risk_alert: Risk alert for opportunity
- win_opportunity: High-probability opportunity

## API Endpoints

### Deals Router (`/api/v1/deals`)

```bash
# Create deal
POST /api/v1/deals
{
  "name": "Enterprise Deal",
  "contact_id": 123,
  "value": 50000,
  "stage": "prospecting"
}

# List deals
GET /api/v1/deals?status=open&stage=proposal&limit=50

# Get deal details
GET /api/v1/deals/{deal_id}

# Update deal
PUT /api/v1/deals/{deal_id}
{
  "value": 60000,
  "stage": "negotiation"
}

# Close deal
POST /api/v1/deals/{deal_id}/close?won=true&reason="Signed contract"

# Pipeline summary
GET /api/v1/deals/pipeline/summary

# Overdue deals
GET /api/v1/deals/overdue/list

# Add activity
POST /api/v1/deals/{deal_id}/activity
{
  "activity_type": "proposal_sent",
  "description": "Sent proposal to stakeholders",
  "value_impact": 10000
}

# Revenue forecast
GET /api/v1/deals/forecast/revenue
```

## Celery Async Tasks

### CRM Queue Tasks
```python
# Generate customer profile
from tasks.crm_tasks import generate_customer_profile
generate_customer_profile.apply_async(args=[contact_id])

# Score deal
from tasks.crm_tasks import score_deal
score_deal.apply_async(args=[deal_id])

# Batch generate profiles
from tasks.crm_tasks import batch_generate_profiles
batch_generate_profiles.apply_async(args=[user_id, contact_ids_list])

# Build relationship graph
from tasks.crm_tasks import build_relationship_graph
build_relationship_graph.apply_async(args=[user_id])

# Identify influencers
from tasks.crm_tasks import identify_influencers
identify_influencers.apply_async(args=[user_id])

# Generate recommendations
from tasks.crm_tasks import generate_recommendations
generate_recommendations.apply_async(args=[user_id, contact_id])
```

### Periodic Tasks (Celery Beat)
- `refresh-customer-profiles-daily`: Daily at 1 AM UTC
- `score-deals-every-6-hours`: Every 6 hours

## Database Models

### Deal
- id, user_id, contact_id
- name, description, value, currency
- stage, probability, expected_close_date, actual_close_date
- status (open, won, lost)
- ai_score, ai_recommendation
- created_at, updated_at

### DealActivity
- id, deal_id
- activity_type, description
- value_impact, probability_impact
- created_at

### CustomerProfile
- id, contact_id, user_id
- summary, buyer_persona, communication_style
- pain_points (JSON), interests (JSON)
- engagement_level, email_frequency
- response_time_avg
- technologies_used (JSON)
- ai_model, generated_at, last_updated_at

### ContactRelationship
- id, user_id
- from_contact_id, to_contact_id
- relationship_type, email_count
- strength (0-100)
- inferred_role
- created_at, updated_at

### AIRecommendation
- id, user_id, contact_id, deal_id
- recommendation_type, title, description
- action_items (JSON)
- confidence_score (0-100)
- status (pending, actioned, dismissed, expired)
- created_at, expires_at

## Test Suite

Run tests:
```bash
python -m pytest test_phase6_crm.py -v
```

Test coverage:
- DealService: create, move stages, update value, pipeline summary
- ActivityTimelineService: record activity, get timeline, summarize
- RelationshipService: link contacts, build graphs, identify influencers
- CustomerProfileService: create profiles, extract insights
- RecommendationEngine: generate recommendations
- Integration tests: full workflows

## Performance Considerations

### Memory Optimization
- Profile generation uses batch processing
- Relationship graphs cached at query time
- Recommendations expire after 7 days (auto-cleanup)
- Activity timelines limit to last 30 days

### Query Optimization
- Contact relationships indexed by from/to contact IDs
- Deal queries indexed by user and status
- Profile queries include email count for pagination

### Async Processing
- Profile generation: 2-3 seconds per contact
- Deal scoring: <500ms per deal
- Graph building: <1s for <1000 contacts
- Recommendations: 1-2 seconds per contact

## Integration Points

### With Phase 5 (AI Optimization)
- Profile generation uses `ollama_client.py` with caching
- Recommendations use token compression for context
- AI insights cached in Redis

### With Phase 4 (Async Infrastructure)
- All async work runs in "crm" queue
- Periodic tasks scheduled via Celery Beat
- Task results stored in Redis DB /1

### With Previous Phases
- Contact model extended with deals relationship
- Activity model extended with timeline querying
- Email model analyzed for profile/recommendation generation

## Deployment Notes

1. **Database Migration**: Run `init_db_simple.py` to create all Phase 6 tables
2. **New Queue**: Add "crm" queue to Celery workers
3. **Router Registration**: Deals router auto-loaded in app_new.py
4. **Periodic Tasks**: Enable Celery Beat for scheduled profile/scoring tasks
5. **Redis Space**: Ensure Redis has >500MB for recommendations cache

## Common Workflows

### Sales Pipeline Workflow
1. Create deal with prospect contact
2. Record email/call activities
3. Move deal through stages as qualified
4. System auto-scores probability
5. Review dashboard with pipeline summary and forecast

### Customer Intelligence Workflow
1. Import contact
2. Trigger profile generation async
3. Review AI insights: pain points, interests, buyer persona
4. Get relationship graph showing company connections
5. Use recommendations for next action

### Territory Management
1. Query active contacts (7-day interaction window)
2. Build relationship graphs by company
3. Identify key influencers in territory
4. Get follow-up recommendations for each contact
5. Track activities on timeline

## Future Enhancements (Phase 7+)
- Predictive deal scoring using ML
- Sentiment tracking from emails over time
- Win/loss analysis and patterns
- Territory optimization
- Account-based marketing sequences
- Forecasting accuracy tracking
