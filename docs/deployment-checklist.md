# Deployment Checklist

## Pre-Deployment

### Code Readiness
- [ ] All tests passing locally (`pytest`)
- [ ] No linting errors
- [ ] Code reviewed and approved
- [ ] Branch merged to main/production

### Environment Configuration
- [ ] `GEMINI_API_KEY` set
- [ ] `SUPABASE_URL` set
- [ ] `SUPABASE_SERVICE_ROLE_KEY` set
- [ ] `SUPABASE_ANON_KEY` set
- [ ] `ENVIRONMENT=production`
- [ ] `LOG_LEVEL=INFO`

### Database Preparation
- [ ] Database migrations tested on staging
- [ ] Backup of production database created
- [ ] Rollback scripts prepared

### Documentation
- [ ] API documentation updated
- [ ] Changelog updated
- [ ] README updated (if needed)

---

## Deployment Steps

### 1. Database Migration
- [ ] Run migration scripts
  ```bash
  psql $DATABASE_URL -f migrations/001_hybrid_impl.sql
  ```
- [ ] Verify tables created
  ```sql
  SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
  ```
- [ ] Verify indexes created
  ```sql
  SELECT indexname FROM pg_indexes WHERE tablename IN ('courses', 'professors', 'sync_metadata');
  ```

### 2. Backend Deployment
- [ ] Deploy backend service
- [ ] Verify service started successfully
- [ ] Check logs for startup errors

### 3. Health Verification
- [ ] `/health` returns 200
  ```bash
  curl http://localhost:8000/health
  ```
- [ ] Status is "healthy"
- [ ] Database shows "connected"
- [ ] All circuit breakers "closed"

### 4. Initial Data Population
- [ ] Trigger course sync for current semester
  ```bash
  curl -X POST http://localhost:8000/api/admin/sync \
    -H "Content-Type: application/json" \
    -d '{"entity_type":"courses","semester":"Spring 2025","university":"Baruch College"}'
  ```
- [ ] Verify sync completes successfully
- [ ] Check course count is reasonable

### 5. Functional Verification
- [ ] `GET /api/courses` returns data
- [ ] `POST /api/schedule/optimize` works
- [ ] `GET /api/professor/{name}` works
- [ ] Response times acceptable

---

## Post-Deployment

### Immediate (First Hour)
- [ ] Monitor error logs continuously
- [ ] Check response times
- [ ] Verify no 500 errors
- [ ] Check circuit breaker states

### Short-term (First 24 Hours)
- [ ] Monitor error rate (< 1%)
- [ ] Check cache hit rate (> 50%)
- [ ] Verify background jobs run successfully
- [ ] Review user feedback (if available)

### Validation Metrics
| Metric | Target | Actual |
|--------|--------|--------|
| Health status | healthy | |
| Error rate | < 1% | |
| P95 response time (cached) | < 100ms | |
| P95 response time (fresh) | < 10s | |
| Cache hit rate | > 50% | |
| Circuit breakers open | 0 | |

---

## Rollback Triggers

Initiate rollback if any of the following occur:
- [ ] Error rate > 10% for 5+ minutes
- [ ] Health status "unhealthy" for 5+ minutes
- [ ] Database connection failures
- [ ] Critical functionality broken (schedule optimization)

### Rollback Steps
1. [ ] Stop deployment/rollout
2. [ ] Checkout previous version
3. [ ] Redeploy previous version
4. [ ] Verify health
5. [ ] Rollback database (if needed)
6. [ ] Document incident

---

## Sign-offs

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Reviewer | | | |
| Deployer | | | |

---

## Notes

_Add any deployment-specific notes here_
