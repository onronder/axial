# Production Deployment Checklist

## ✅ Pre-Deployment Verification

### 1. Test Suite Status
- **Frontend Tests**: 2,460+ tests passing ✅
- **Backend Tests**: 2,466+ tests passing ✅
- **Frontend Coverage**: 97.03% ✅
- **No Critical Bugs**: All identified bugs fixed ✅

### 2. Critical Bug Fixes Applied
- [x] **middleware.ts created** - Authentication middleware was not being executed because Next.js requires `middleware.ts` (not `proxy.ts`). Fixed by creating the middleware entry point.

---

## 🔧 Environment Configuration

### Frontend Environment Variables (Required)
```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key

# Backend API
NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app

# Sentry (Error Monitoring)
NEXT_PUBLIC_SENTRY_DSN=your-sentry-dsn
SENTRY_AUTH_TOKEN=your-sentry-auth-token

# Polar.sh (Billing)
NEXT_PUBLIC_POLAR_ORG_ID=your-polar-org-id
```

### Backend Environment Variables (Required)
```env
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=your-openai-key

# Ghost Protocol (Encryption)
CHUNK_ENCRYPTION_KEY=your-fernet-key
ENCRYPTION_KEY=your-encryption-key
STRICT_ENCRYPTION_MODE=true

# Redis
REDIS_URL=redis://your-redis-host:6379

# Polar.sh (Billing)
POLAR_ACCESS_TOKEN=your-polar-token
POLAR_WEBHOOK_SECRET=your-webhook-secret

# Optional: ClamAV
CLAMAV_HOST=localhost
CLAMAV_PORT=3310

# Celery Worker Memory Management (Enterprise 8-Core/32GB)
CELERY_WORKER_MAX_MEMORY_PER_CHILD=3000000
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
CELERY_WORKER_CONCURRENCY=8
```

---

## 🚀 Deployment Steps

### Frontend (Vercel/Next.js)

1. **Build Verification**
   ```bash
   cd frontend-new
   npm run build
   ```

2. **Type Check**
   ```bash
   npm run typecheck
   ```

3. **Lint Check**
   ```bash
   npm run lint
   ```

4. **Environment Variables**
   - Set all required env vars in Vercel dashboard
   - Ensure `NEXT_PUBLIC_*` vars are properly prefixed

5. **Deploy**
   ```bash
   vercel deploy --prod
   ```

### Backend (Railway/Docker)

1. **Build Docker Image**
   ```bash
   docker build -f docker/backend.Dockerfile -t axial-backend ./backend
   ```

2. **Database Migrations**
   ```bash
   # Run any pending Supabase migrations
   supabase db push
   ```

3. **Deploy**
   ```bash
   railway up
   ```

4. **Health Check**
   ```bash
   curl https://your-backend.railway.app/health
   ```

---

## 🔒 Security Checklist

### Authentication
- [x] Supabase Auth configured
- [x] Session validation in middleware
- [x] Protected routes enforced
- [x] OAuth token encryption (AES-256)

### Data Protection
- [x] Ghost Protocol encryption enabled
- [x] Content Security Policy headers
- [x] CORS properly configured
- [x] Rate limiting on all endpoints

### API Security
- [x] JWT validation on all protected endpoints
- [x] Input validation with Pydantic
- [x] SQL injection protection (parameterized queries)
- [x] SSRF protection on connectors

---

## 📊 Monitoring Setup

### Sentry (Error Tracking)
- Frontend: `sentry.client.config.ts`, `sentry.server.config.ts`
- Tunnel route: `/monitoring` (bypasses ad-blockers)

### Health Endpoints
- Backend: `GET /health` - Basic health check
- Webhooks: `GET /api/v1/webhooks/health` - Webhook processor health

---

## 🧪 Post-Deployment Verification

### Smoke Tests
1. **Authentication Flow**
   - [ ] User can register
   - [ ] User can login
   - [ ] OAuth providers work (Google, Notion, GitHub, etc.)
   - [ ] Password reset works

2. **Core Features**
   - [ ] Chat conversations work
   - [ ] File upload works
   - [ ] Document search works
   - [ ] Billing/subscription works

3. **Data Sources**
   - [ ] Google Drive connection works
   - [ ] Notion connection works
   - [ ] Box/Dropbox connections work
   - [ ] SFTP connections work (if enabled)

4. **Admin Features**
   - [ ] DLQ dashboard loads
   - [ ] Audit logs work
   - [ ] Usage metrics display

---

## ⚠️ Known Limitations

1. **Backend Memory Usage**
   - Backend tests require ~4GB RAM when run together
   - Run tests in batches for CI/CD

2. **Deprecation Warning**
   - `clamd` package uses deprecated `pkg_resources`
   - Update when new version available (before Nov 2025)

---

## 📝 Rollback Procedure

### Frontend
```bash
vercel rollback
```

### Backend
```bash
railway rollback
```

### Database
```bash
# Restore from Supabase backup
supabase db restore
```

---

## 📅 Maintenance Schedule

- **Weekly**: Review Sentry errors
- **Monthly**: Update dependencies
- **Quarterly**: Security audit
- **Bi-annual**: Dependency major version updates

---

## 📞 Support Contacts

- **Engineering**: [Your team Slack channel]
- **Infrastructure**: [Your infrastructure team]
- **Security**: [Your security team]

---

**Last Updated**: February 1, 2026
**Verified By**: AI-Assisted Code Review
