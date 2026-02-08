# Axial — Disaster Recovery Runbook

## Table of Contents

1. [Critical Assets](#critical-assets)
2. [Backup Strategy](#backup-strategy)
3. [Encryption Key Management](#encryption-key-management)
4. [Service Restoration Sequence](#service-restoration-sequence)
5. [Database Recovery](#database-recovery)
6. [Migration Rollback Procedures](#migration-rollback-procedures)
7. [Incident Response Checklist](#incident-response-checklist)
8. [Contact & Escalation](#contact--escalation)

---

## Critical Assets

| Asset | Location | Backup Method | RPO |
|-------|----------|---------------|-----|
| PostgreSQL (Supabase) | Supabase Cloud | PITR (Point-in-Time Recovery) | Minutes |
| `CHUNK_ENCRYPTION_KEY` | Environment / Secrets Manager | Manual secure backup | N/A (static) |
| Redis (cache/queues) | Docker volume | Ephemeral — rebuilt on restart | N/A |
| File storage (Supabase Storage) | Supabase Cloud | Platform-managed | Hours |
| OAuth tokens (encrypted in DB) | PostgreSQL | Included in DB backup | Minutes |

---

## Backup Strategy

### Supabase PostgreSQL

Supabase Cloud projects include automatic daily backups. For production:

1. **Enable PITR** (Point-in-Time Recovery) in Supabase Dashboard > Database > Backups
2. PITR allows restoration to any point within the retention window (typically 7 days)
3. For additional safety, schedule periodic `pg_dump` exports:

```bash
# Manual logical backup (run from a machine with DB access)
pg_dump "$DATABASE_URL" --format=custom --file="axial-backup-$(date +%Y%m%d-%H%M%S).dump"
```

### Redis

Redis is used for caching, rate limiting, and Celery task queues. It is **ephemeral by design**:
- Cache entries will be repopulated on access
- In-flight Celery tasks will be lost on Redis failure — workers will re-pick pending tasks from the database job table
- No backup needed; Redis restores from AOF/RDB if persistence is enabled in production (see `docker-compose.prod.yml`)

### File Storage

Supabase Storage handles file backup automatically. For self-hosted deployments, ensure the storage volume is backed up independently.

---

## Encryption Key Management

### `CHUNK_ENCRYPTION_KEY` (CRITICAL)

This Fernet AES-256 key encrypts all document chunk content at rest. **If this key is lost, all encrypted data is permanently unrecoverable.**

#### Backup Requirements

1. **Generate the key** (if not already done):
   ```bash
   python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
   ```

2. **Store the key in at least 2 separate secure locations**:
   - Primary: Cloud secrets manager (AWS Secrets Manager, GCP Secret Manager, or Vault)
   - Secondary: Encrypted offline backup (e.g., encrypted USB in a safe, or printed QR code in secure storage)

3. **Never store the key in**:
   - Git repositories (even private ones)
   - Plaintext files on servers
   - Email or chat messages
   - Shared environment files without encryption

4. **Key rotation**: Currently not supported for existing data. If key rotation is needed, a migration script must decrypt all chunks with the old key and re-encrypt with the new key. Plan for this as a future enhancement.

### `ENCRYPTION_KEY`

Used for general-purpose encryption of sensitive fields. Same backup requirements apply, though impact of loss is lower (OAuth tokens can be re-authorized).

---

## Service Restoration Sequence

When recovering from a full outage, restore services in this order:

```
1. Redis           (no dependencies)
2. Backend API     (depends on: Redis, Supabase)
3. Celery Workers  (depends on: Redis, Supabase, Backend)
4. Flower          (depends on: Redis, Celery)
5. Frontend        (depends on: Backend API, Supabase)
```

### Step-by-Step

```bash
# 1. Start infrastructure
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d redis

# 2. Wait for Redis health check to pass
docker compose ps redis  # Should show "healthy"

# 3. Start backend API
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d backend

# 4. Verify backend health
curl -f http://localhost:8000/health

# 5. Start monitoring
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d flower

# 6. Deploy frontend (Next.js — typically via Vercel or separate container)
# Verify: curl -f https://app.axiohub.io/api/health
```

---

## Database Recovery

### Restoring from Supabase PITR

1. Go to Supabase Dashboard > Your Project > Database > Backups
2. Select the desired recovery point (timestamp)
3. Click "Restore" — this will create a new project with the restored data
4. Update `SUPABASE_URL` and keys in your environment to point to the restored project
5. Verify data integrity: check document counts, user accounts, and encryption status

### Restoring from pg_dump

```bash
# Restore to a new database
pg_restore --dbname="$NEW_DATABASE_URL" --format=custom axial-backup-YYYYMMDD-HHMMSS.dump

# Verify row counts
psql "$NEW_DATABASE_URL" -c "SELECT count(*) FROM document_chunks;"
psql "$NEW_DATABASE_URL" -c "SELECT count(*) FROM auth.users;"
```

### Post-Restore Verification

After any database restore:

1. Verify encryption key works: attempt to decrypt a document chunk
2. Check OAuth tokens: users may need to re-authorize connectors if tokens expired
3. Verify pgvector indices exist: `SELECT * FROM pg_indexes WHERE indexname LIKE '%embedding%';`
4. Run pending migrations: `cd backend && alembic upgrade head`

---

## Migration Rollback Procedures

The project uses Supabase migrations (120+ forward migrations). There are no automated rollback scripts.

### Manual Rollback for Recent Migrations

If a migration causes issues:

1. **Identify the problematic migration** in `supabase/migrations/`
2. **Write a reverse SQL script** that undoes the changes:
   - `ALTER TABLE ... DROP COLUMN` for added columns
   - `DROP TABLE IF EXISTS` for added tables
   - `DROP INDEX IF EXISTS` for added indices
   - `ALTER TABLE ... ADD COLUMN` for dropped columns (from backup)
3. **Execute via Supabase SQL Editor** or `psql`
4. **Remove the migration file** from the migrations directory
5. **Test thoroughly** before re-deploying

### Prevention

For future migrations, consider adding a `-- ROLLBACK:` comment at the top of each migration file documenting the reverse SQL.

---

## Incident Response Checklist

### Severity 1: Full Outage (All Services Down)

- [ ] Assess: Is it infrastructure (cloud provider) or application?
- [ ] Check Supabase status: https://status.supabase.com
- [ ] Check deployment platform status (Vercel/Railway/etc.)
- [ ] If infrastructure: wait for provider recovery, then follow restoration sequence
- [ ] If application: check logs (`docker compose logs --tail=100 backend`)
- [ ] Restore from backup if data corruption detected

### Severity 2: Data Corruption

- [ ] Immediately stop write operations (`docker compose stop backend`)
- [ ] Assess scope: which tables/rows are affected?
- [ ] Identify the timestamp of corruption
- [ ] Restore from PITR to just before corruption
- [ ] Verify `CHUNK_ENCRYPTION_KEY` matches the backup
- [ ] Re-deploy with the fix that caused corruption

### Severity 3: Encryption Key Compromise

- [ ] Immediately rotate all API keys and OAuth secrets
- [ ] Generate new `CHUNK_ENCRYPTION_KEY`
- [ ] Run key migration script (decrypt with old key, encrypt with new)
- [ ] Rotate `SUPABASE_SECRET_KEY` and `SUPABASE_JWT_SECRET`
- [ ] Invalidate all active sessions
- [ ] Notify affected users per compliance requirements

### Severity 4: Single Service Degradation

- [ ] Check service health: `docker compose ps`
- [ ] Review logs: `docker compose logs --tail=200 <service>`
- [ ] Restart the affected service: `docker compose restart <service>`
- [ ] If persistent: check resource limits, memory usage, disk space
- [ ] Escalate if not resolved within 30 minutes

---

## Contact & Escalation

| Role | Contact | Escalation Time |
|------|---------|-----------------|
| On-Call Engineer | [TODO: Add contact] | Immediate |
| Backend Lead | [TODO: Add contact] | 15 minutes |
| Infrastructure Lead | [TODO: Add contact] | 30 minutes |
| Security Officer | [TODO: Add contact] | Immediate (for Sev 3) |

### External Services

| Service | Status Page | Support |
|---------|-------------|---------|
| Supabase | https://status.supabase.com | support@supabase.io |
| OpenAI | https://status.openai.com | Through dashboard |
| Vercel | https://www.vercel-status.com | Through dashboard |
| Polar.sh | https://polar.sh | Through dashboard |
