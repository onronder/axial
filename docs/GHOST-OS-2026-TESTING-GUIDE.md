# Ghost OS 2026 Testing Guide

**Date:** 2026-02-03
**Purpose:** Step-by-step verification of all Ghost OS implementations

---

## Prerequisites

### 1. Database Migrations Applied
Verify all migrations are applied:
```bash
supabase db push --include-all
```

Expected migrations:
- ✅ `20260203000000_mcp_api_keys.sql`
- ✅ `20260203000001_scope_guard_approvals.sql`
- ✅ `20260203000002_consent_management.sql`
- ✅ `20260203000010_compliance_tombstones.sql`
- ✅ `20260203000011_compliance_audit_log.sql`
- ✅ `20260203000012_hybrid_search_tombstone_filter.sql`

### 2. Environment Variables
Ensure these are set in production:
```env
CHUNK_ENCRYPTION_KEY=<fernet-key>    # Required for Ghost Protocol
ENCRYPTION_KEY=<fernet-key>          # Required for token encryption
```

### 3. Login
1. Go to https://app.axiohub.io
2. Login with your admin account
3. Ensure you have **admin** or **owner** role

---

## Test 1: Consent Management (GDPR/CCPA/KVKK)

### 1.1 Navigate to Consent Settings
1. Click **Settings** in sidebar
2. Click **Consent** tab (or go to `/dashboard/settings/consent`)

### 1.2 Test Organization-Level Consent
| Action | Expected Result |
|--------|-----------------|
| Toggle "AI Learning" ON | Toggle turns green, timestamp updates |
| Toggle "AI Learning" OFF | Toggle turns gray, timestamp updates |
| Toggle "External Agents" ON | Toggle turns green, timestamp updates |
| Toggle "External Agents" OFF | Toggle turns gray, timestamp updates |

### 1.3 Test Scope-Level Consent (if scopes exist)
1. Expand a scope in the inheritance tree
2. Toggle "Inherit from Organization" OFF
3. Set custom consent for the scope
4. Verify the scope shows override indicator

### 1.4 Verify Compliance Score Widget
- Check that compliance score displays (0-100%)
- Score should increase as you configure consent

### 1.5 API Verification (Optional)
```bash
# Get organization consent
curl -X GET "https://api.axiohub.io/api/v1/consent/organization" \
  -H "Authorization: Bearer <your-token>"

# Update organization consent
curl -X PATCH "https://api.axiohub.io/api/v1/consent/organization" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"consent_type": "ai_learning", "allowed": true}'

# Get compliance report
curl -X GET "https://api.axiohub.io/api/v1/consent/report" \
  -H "Authorization: Bearer <your-token>"
```

---

## Test 2: MCP Server (External AI Agent Access)

### 2.1 Navigate to MCP Settings
1. Go to **Settings** > **API Keys** or **Integrations**
2. Look for "MCP API Keys" section

### 2.2 Create MCP API Key
1. Click "Create API Key"
2. Enter a name (e.g., "Test Key")
3. Select scopes: `*` (all) or specific scopes
4. Set expiration (optional)
5. Click "Create"

**Expected:** API key displayed in format `axio_mcp_xxxxxxxxxxxx`

**IMPORTANT:** Copy the key immediately - it won't be shown again!

### 2.3 Test MCP Endpoint
```bash
# Test info endpoint (no auth required)
curl -X GET "https://api.axiohub.io/api/v1/mcp/info"

# Expected response:
# {
#   "name": "axiohub",
#   "version": "1.0.0",
#   "protocol_version": "2024-11-05",
#   "capabilities": {...}
# }

# Test JSON-RPC with API key
curl -X POST "https://api.axiohub.io/api/v1/mcp/v1/rpc" \
  -H "Authorization: Bearer axio_mcp_<your-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'

# Expected: List of available tools (search_documents, ask_question, etc.)
```

### 2.4 Test MCP Tools
```bash
# List scopes
curl -X POST "https://api.axiohub.io/api/v1/mcp/v1/rpc" \
  -H "Authorization: Bearer axio_mcp_<your-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "list_scopes",
      "arguments": {}
    },
    "id": 2
  }'

# Search documents
curl -X POST "https://api.axiohub.io/api/v1/mcp/v1/rpc" \
  -H "Authorization: Bearer axio_mcp_<your-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_documents",
      "arguments": {
        "query": "test query",
        "limit": 5
      }
    },
    "id": 3
  }'
```

### 2.5 Revoke API Key
1. Go back to API Keys list
2. Click "Revoke" on the test key
3. Confirm revocation
4. Try using the key again - should get 401 error

---

## Test 3: Scope Guard (Human-in-the-Loop Approvals)

### 3.1 Navigate to Approvals
1. Go to **Settings** > **Security** or look for "Pending Approvals" widget
2. Or navigate directly to `/dashboard/settings/security`

### 3.2 Trigger an Approval Request
To test, you need to trigger a destructive action. Choose one:

**Option A: Delete a Scope (via API)**
```bash
curl -X DELETE "https://api.axiohub.io/api/v1/scopes/<scope-id>" \
  -H "Authorization: Bearer <your-token>"
```

**Option B: Bulk Delete Documents (via UI)**
1. Go to Documents
2. Select multiple documents
3. Click "Delete Selected"
4. If Scope Guard is active, this should create an approval request

### 3.3 View Pending Approval
1. Check the "Pending Approvals" widget
2. Should show:
   - Action type (DELETE_SCOPE, BULK_DELETE, etc.)
   - Resource name
   - Requested by
   - Countdown timer (30 min default)
   - Reason/context

### 3.4 Approve the Request
1. Click on the pending approval
2. Review the details in the modal
3. Click "Approve"
4. Verify signature animation plays
5. Action should execute

### 3.5 Test Rejection
1. Trigger another approval request
2. Click "Reject"
3. Enter rejection reason
4. Verify request status changes to "rejected"

### 3.6 Test Expiration
1. Trigger an approval request
2. Wait 30 minutes (or adjust TTL in config)
3. Verify request auto-expires

### 3.7 API Verification
```bash
# Get pending approvals (admin only)
curl -X GET "https://api.axiohub.io/api/v1/approvals/pending" \
  -H "Authorization: Bearer <your-token>"

# Approve an action
curl -X POST "https://api.axiohub.io/api/v1/approvals/<approval-id>/approve" \
  -H "Authorization: Bearer <your-token>"

# Reject an action
curl -X POST "https://api.axiohub.io/api/v1/approvals/<approval-id>/reject?reason=Testing" \
  -H "Authorization: Bearer <your-token>"
```

---

## Test 4: Ghost Protocol (DoD Wipe)

### 4.1 Navigate to Security Log
1. Go to **Settings** > **Security Log**
2. Or navigate to `/dashboard/settings/security-log`

### 4.2 Delete a Test Document
1. Upload a small test file (e.g., test.txt with "Hello World")
2. Wait for indexing to complete
3. Delete the document
4. Observe the wipe progress card (if implemented in UI)

### 4.3 Verify Security Log Entry
1. Check Security Log table
2. Should show entry with:
   - Event type: `document_wiped`
   - Wipe pattern: `dod_5220_22_m`
   - Wipe verified: ✅ (green checkmark)
   - Duration (ms)

### 4.4 Verify DoD 5220.22-M Compliance
The log should confirm 3-pass wipe:
- Pass 1: 0x00 (zeros)
- Pass 2: 0xFF (ones)
- Pass 3: Random data

### 4.5 API Verification
```bash
# Get security log (admin only)
curl -X GET "https://api.axiohub.io/api/v1/admin/security-log" \
  -H "Authorization: Bearer <your-token>"

# Filter by event type
curl -X GET "https://api.axiohub.io/api/v1/admin/security-log?event_type=document_wiped" \
  -H "Authorization: Bearer <your-token>"
```

---

## Test 5: Compliance (GDPR Article 17 / CCPA)

### 5.1 Trigger GDPR Deletion Request
```bash
# Create GDPR Article 17 deletion request
curl -X POST "https://api.axiohub.io/api/v1/compliance/delete-request" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "resource_type": "document",
    "resource_id": "<document-id>",
    "regulation": "gdpr",
    "reason": "User requested deletion under GDPR Article 17"
  }'
```

### 5.2 Verify Tombstone Created
```bash
# List active tombstones
curl -X GET "https://api.axiohub.io/api/v1/compliance/tombstones" \
  -H "Authorization: Bearer <your-token>"
```

The document should be:
1. Immediately blocked from search results
2. Blocked from API retrieval
3. Scheduled for Ghost Protocol deletion

### 5.3 Verify Search Exclusion
1. Search for the deleted document by name
2. Should NOT appear in results
3. Verify tombstone is working

### 5.4 Test CCPA ADMT Opt-out
```bash
curl -X POST "https://api.axiohub.io/api/v1/compliance/admt-optout" \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "scope_ids": ["<scope-id>"],
    "reason": "CCPA ADMT opt-out request"
  }'
```

### 5.5 Generate Compliance Report
```bash
curl -X GET "https://api.axiohub.io/api/v1/compliance/report" \
  -H "Authorization: Bearer <your-token>"
```

Expected fields:
- Total requests
- Completed requests
- Compliance rate (%)
- Average time to access revocation

---

## Test 6: Vision LLM (Image Understanding)

### 6.1 Upload Image Document
1. Go to **Documents** > **Upload**
2. Upload an image with diagrams/charts:
   - Architecture diagram
   - Flowchart
   - Infographic
   - Technical schematic

### 6.2 Verify Vision Processing
After upload completes:
1. View document details
2. Check for extracted metadata:
   - Diagram type detected
   - Entities identified
   - Relationships extracted
   - OCR text content

### 6.3 Search by Image Content
1. Search for terms visible in the uploaded image
2. Verify the image document appears in results
3. Check that semantic understanding works (e.g., search "architecture" finds architecture diagrams)

### 6.4 Verify Secure Deletion of Original
After processing:
- Original image should be deleted via Ghost Protocol
- Only extracted text/metadata remains
- This is the "zero-trace" feature

---

## Test 7: Data Invalidation (Realtime)

### 7.1 Open Two Browser Tabs
1. Tab 1: Dashboard with documents list
2. Tab 2: Same dashboard

### 7.2 Delete Document in Tab 1
1. Delete a document in Tab 1
2. Watch Tab 2

**Expected:** Tab 2 should auto-update within ~50ms showing document removed

### 7.3 Verify via Supabase Realtime
The `compliance_tombstones` table broadcasts deletions via Supabase Realtime, which triggers React Query cache invalidation.

---

## Test 8: Shutdown Handler

### 8.1 Check Logs During Deployment
During a Railway deployment or container restart, check logs for:

```
✅ Graceful shutdown handlers registered
🛑 Received SIGTERM, initiating graceful shutdown...
🥬 Waiting for Celery tasks to complete...
🤖 Clearing LLM client pool...
🔴 Closing Redis connections...
🔌 Closing database connections...
📁 Closing file handles and cleaning temp files...
✅ Graceful shutdown complete
```

**Should NOT see:**
```
Error in shutdown handler: asyncio.run() cannot be called from a running event loop
```

---

## Test 9: Frontend Component Verification

### 9.1 Scope Guard Components
Navigate to approval-related pages and verify:
- [ ] `MandateApprovalModal` - Shows countdown timer, approve/reject buttons
- [ ] `PendingApprovalsWidget` - Shows badge with pending count
- [ ] `IntentExplanationCard` - Shows AI reasoning for action
- [ ] `SignatureAnimation` - Plays on approval

### 9.2 Ghost Protocol Components
- [ ] `WipeProgressCard` - Shows 3-pass progress during deletion
- [ ] `ShredderAnimation` - Visual feedback during wipe
- [ ] `WipeVerificationBadge` - Shows ✅ for verified wipes
- [ ] `SecurityLogTable` - Filterable log of security events

### 9.3 Consent Components
- [ ] `ConsentDashboard` - Main consent management page
- [ ] `ConsentToggle` - Toggle switches for consent types
- [ ] `InheritanceTree` - Shows org > scope > document hierarchy
- [ ] `ComplianceScoreWidget` - Shows compliance percentage
- [ ] `AgentAccessPanel` - Manage which agents can access data

### 9.4 Vision Components
- [ ] `VisionVerifiedBadge` - Shows when image was processed
- [ ] `DiagramPreviewModal` - Preview extracted diagram info
- [ ] `SemanticOverlay` - Shows extracted entities on hover

---

## Test 10: API Health Checks

### 10.1 Backend Health
```bash
curl https://api.axiohub.io/health
```

Expected:
```json
{
  "status": "healthy",
  "services": {
    "database": "up",
    "redis": "up"
  }
}
```

### 10.2 MCP Discovery
```bash
curl https://api.axiohub.io/api/v1/mcp/info
```

### 10.3 Prometheus Metrics (if enabled)
```bash
curl https://api.axiohub.io/metrics | grep -E "(secure_wipe|ghost_protocol)"
```

Expected metrics:
- `secure_wipe_total{result="success"}`
- `secure_wipe_duration_seconds`
- `smart_buffer_allocations_total`

---

## Troubleshooting

### Issue: 401 Unauthorized on Consent/Approval endpoints
**Cause:** Frontend not sending Authorization header
**Fix:** We updated hooks to use `api` client - redeploy frontend

### Issue: asyncio.run() error in shutdown
**Cause:** Old shutdown handler code
**Fix:** We fixed this - redeploy backend

### Issue: KVKK-only mentioned in UI
**Cause:** Old docstrings
**Fix:** We updated to GDPR/CCPA/KVKK - redeploy

### Issue: MCP key not working
**Cause:** Key may be expired or revoked
**Fix:** Create new key, check expiration settings

### Issue: Tombstone not blocking search
**Cause:** Migration not applied or index missing
**Fix:** Run `supabase db push --include-all`

---

## Sign-off Checklist

| Feature | Tested | Works | Notes |
|---------|--------|-------|-------|
| Consent Management | ☐ | ☐ | |
| MCP Server | ☐ | ☐ | |
| Scope Guard Approvals | ☐ | ☐ | |
| Ghost Protocol Wipe | ☐ | ☐ | |
| GDPR/CCPA Compliance | ☐ | ☐ | |
| Vision LLM | ☐ | ☐ | |
| Realtime Invalidation | ☐ | ☐ | |
| Graceful Shutdown | ☐ | ☐ | |
| Frontend Components | ☐ | ☐ | |
| API Health | ☐ | ☐ | |

**Tested By:** _________________
**Date:** _________________
**Approved:** ☐ Yes ☐ No

---

*Document generated: 2026-02-03*
