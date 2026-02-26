# Connector Production Transition — Go-Live Checklist

> **Date:** 2026-02-24
> **Status:** Pre-production
> **Production Domain:** `app.axiohub.io`
> **Callback URL:** `https://app.axiohub.io/oauth/callback`

---

## Priority Order

| # | Connector | Priority | Platform | Review Time |
|---|-----------|----------|----------|-------------|
| 1 | Google Drive | CRITICAL | Google Cloud Console | 3-5 business days |
| 2 | Microsoft OneDrive/SharePoint | HIGH | Azure Portal | Instant (publisher verification separate) |
| 3 | Notion | HIGH | Notion Integrations | 1-3 business days |
| 4 | Box | MEDIUM | Box Developer Console | Admin authorization needed |
| 5 | Dropbox | LOW | Dropbox App Console | 1-2 business days |
| 6 | GitHub | LOW | GitHub Developer Settings | Instant (no review) |

---

## 1. Google Drive (CRITICAL — Do First)

**Why critical:** Test-mode refresh tokens expire after 7 days. Until the app is published, all connected users must re-authenticate weekly.

**Platform:** [Google Cloud Console](https://console.cloud.google.com/) > APIs & Services > OAuth consent screen

### Pre-requisites

- [ ] Production domain (`axiohub.io`) verified in Google Search Console
- [ ] Privacy policy URL hosted: `https://axiohub.io/privacy`
- [ ] Terms of service URL (recommended): `https://axiohub.io/terms`
- [ ] App logo (120x120 px PNG)

### Platform Steps

1. Go to **OAuth consent screen** in Google Cloud Console
2. Click **"Publish App"** to move from Testing to Production
3. Fill out the verification form:
   - App name: **Axial**
   - App logo: 120x120 px
   - App homepage: `https://axiohub.io`
   - Privacy policy: `https://axiohub.io/privacy`
   - Authorized domains: `axiohub.io`
4. **Scope justification** for `drive.readonly`:
   > "Axial reads files from users' Google Drive to index and search their documents. We only require read access and never modify or delete files."
5. Submit for Google review (3-5 business days)
6. **While waiting:** the app works but users see an "unverified app" warning they must click through

### Environment Variables

```bash
# Backend (.env)
GOOGLE_CLIENT_ID=<production-client-id>
GOOGLE_CLIENT_SECRET=<production-secret>
GOOGLE_REDIRECT_URI=https://app.axiohub.io/oauth/callback

# Frontend (.env)
NEXT_PUBLIC_GOOGLE_CLIENT_ID=<same-as-backend>
NEXT_PUBLIC_GOOGLE_REDIRECT_URI=https://app.axiohub.io/oauth/callback
```

### Verification

- [ ] OAuth flow completes without "unverified app" warning (post-approval)
- [ ] Refresh tokens persist beyond 7 days
- [ ] File listing and content download work
- [ ] Run: `python backend/scripts/smoke_test_connectors.py --connector google`

---

## 2. Microsoft OneDrive & SharePoint (HIGH)

**Platform:** [Azure Portal](https://portal.azure.com/) > App registrations

### Pre-requisites

- [ ] Azure AD tenant configured
- [ ] Production domain ownership verified
- [ ] Microsoft Partner Network (MPN) ID or DNS TXT record for publisher verification

### Platform Steps

1. Go to **App registrations** > your app > **Branding & properties**
2. **Verify publisher** (removes "unverified" warning):
   - Add MPN ID, or
   - Verify via DNS TXT record on `axiohub.io`
3. Go to **Authentication** > **Redirect URIs**:
   - Add: `https://app.axiohub.io/oauth/callback`
   - Remove localhost/test URIs
4. Go to **API permissions** — ensure these are listed:
   - `offline_access`
   - `User.Read`
   - `Files.Read.All`
   - `Sites.Read.All` (for SharePoint)
   - Click **"Grant admin consent"** if you're the tenant admin
5. For multi-tenant (`MICROSOFT_TENANT_ID=common`):
   - Enterprise customers' IT admins may need to grant consent
   - Admin consent URL: `https://login.microsoftonline.com/common/adminconsent?client_id=<YOUR_CLIENT_ID>`

### Environment Variables

```bash
# Backend (.env)
MICROSOFT_CLIENT_ID=<production-app-id>
MICROSOFT_CLIENT_SECRET=<production-secret>
MICROSOFT_REDIRECT_URI=https://app.axiohub.io/oauth/callback
MICROSOFT_TENANT_ID=common

# Frontend (.env)
NEXT_PUBLIC_MICROSOFT_CLIENT_ID=<same-as-backend>
NEXT_PUBLIC_MICROSOFT_REDIRECT_URI=https://app.axiohub.io/oauth/callback
NEXT_PUBLIC_MICROSOFT_TENANT_ID=common
```

### Verification

- [ ] OAuth flow works without "unverified app" warning
- [ ] OneDrive file listing works
- [ ] SharePoint site listing and file access work
- [ ] Token refresh works correctly (PKCE flow)
- [ ] Run: `python backend/scripts/smoke_test_connectors.py --connector microsoft`

---

## 3. Notion (HIGH)

**Platform:** [Notion Integrations](https://www.notion.so/my-integrations)

### Pre-requisites

- [ ] Privacy policy URL: `https://axiohub.io/privacy`
- [ ] Company website: `https://axiohub.io`
- [ ] Integration icon/logo

### Platform Steps

1. Go to **notion.so/my-integrations** > select your integration
2. Go to **Distribution** tab
3. Toggle from **Internal** to **Public**
4. Fill out the submission form:
   - Integration name: **Axial**
   - Redirect URI: `https://app.axiohub.io/oauth/callback`
   - Company name: Axial / AxioHub
   - Website: `https://axiohub.io`
   - Privacy policy: `https://axiohub.io/privacy`
   - Tagline: "Axial indexes and searches your Notion pages and databases"
   - Integration logo
5. Submit for Notion review (1-3 business days)
6. **After approval:** public integrations get a **new** client ID/secret

### Environment Variables

```bash
# Backend (.env) — UPDATE after Notion approves public integration
NOTION_CLIENT_ID=<new-public-client-id>
NOTION_CLIENT_SECRET=<new-public-secret>
NOTION_REDIRECT_URI=https://app.axiohub.io/oauth/callback

# Frontend (.env)
NEXT_PUBLIC_NOTION_CLIENT_ID=<same-as-backend>
NEXT_PUBLIC_NOTION_REDIRECT_URI=https://app.axiohub.io/oauth/callback
```

### Verification

- [ ] External users (outside your workspace) can connect via OAuth
- [ ] Page and database listing works
- [ ] Auto-ingestion triggers correctly on connect
- [ ] Token persistence works (Notion tokens are long-lived, no refresh needed)
- [ ] Run: `python backend/scripts/smoke_test_connectors.py --connector notion`

---

## 4. Box (MEDIUM)

**Platform:** [Box Developer Console](https://app.box.com/developers/console)

### Pre-requisites

- [ ] Box enterprise admin access (or contact with admin)

### Platform Steps

1. Go to **Box Developer Console** > your app
2. Go to **Configuration** tab:
   - Set OAuth 2.0 Redirect URI: `https://app.axiohub.io/oauth/callback`
   - Ensure scopes include `Read all files and folders stored in Box`
3. Go to **Authorization** tab:
   - Click **"Submit for Review"**
   - Or provide the Client ID to a Box enterprise admin
4. **Enterprise admin** must authorize:
   - Admin Console > Apps > Custom Apps > Authorize
   - Enter your app's Client ID

### Environment Variables

```bash
# Backend (.env)
BOX_CLIENT_ID=<production-client-id>
BOX_CLIENT_SECRET=<production-secret>
BOX_REDIRECT_URI=https://app.axiohub.io/oauth/callback

# Frontend (.env)
NEXT_PUBLIC_BOX_CLIENT_ID=<same-as-backend>
```

### Verification

- [ ] OAuth flow works for enterprise Box users
- [ ] File listing and download work
- [ ] Single-use refresh token rotation works correctly
- [ ] 60-minute access token auto-refresh works
- [ ] Run: `python backend/scripts/smoke_test_connectors.py --connector box`

---

## 5. Dropbox (LOW)

**Platform:** [Dropbox App Console](https://www.dropbox.com/developers/apps)

### Pre-requisites

- [ ] App description and branding ready

### Platform Steps

1. Go to **Dropbox App Console** > your app
2. Go to **Settings** tab:
   - Update redirect URI: `https://app.axiohub.io/oauth/callback`
   - Remove test/localhost URIs
3. Click **"Apply for production"**:
   - Provide app description
   - Explain data usage
   - Dropbox reviews (1-2 business days)

> **Note:** Development status supports up to **500 linked users** — fine for early launch. Apply for production when approaching this limit.

### Environment Variables

```bash
# Backend (.env)
DROPBOX_CLIENT_ID=<production-app-key>
DROPBOX_CLIENT_SECRET=<production-app-secret>
DROPBOX_REDIRECT_URI=https://app.axiohub.io/oauth/callback

# Frontend (.env)
NEXT_PUBLIC_DROPBOX_CLIENT_ID=<same-as-backend>
```

### Verification

- [ ] OAuth flow works (personal and team accounts)
- [ ] Team account auto-detection works (root_namespace_id)
- [ ] Incremental sync works
- [ ] Token refresh works
- [ ] Run: `python backend/scripts/smoke_test_connectors.py --connector dropbox`

---

## 6. GitHub (LOW — Minimal Changes)

**Platform:** [GitHub Developer Settings](https://github.com/settings/developers)

### Platform Steps

1. Go to **GitHub Settings** > Developer settings > OAuth Apps
2. Update:
   - **Homepage URL**: `https://axiohub.io`
   - **Authorization callback URL**: `https://app.axiohub.io/oauth/callback`
3. Consider transferring app ownership to your GitHub organization

> **Note:** GitHub OAuth apps have no test/production mode distinction. Rate limit: 5,000 requests/hour per authenticated user.

### Environment Variables

```bash
# Backend (.env)
GITHUB_CLIENT_ID=<production-client-id>
GITHUB_CLIENT_SECRET=<production-secret>
GITHUB_REDIRECT_URI=https://app.axiohub.io/oauth/callback

# Frontend (.env)
NEXT_PUBLIC_GITHUB_CLIENT_ID=<same-as-backend>
```

### Verification

- [ ] OAuth flow works
- [ ] Repository listing appears in selector modal
- [ ] Code/docs content filtering works
- [ ] Tokens persist (indefinite lifetime, no refresh needed)
- [ ] Run: `python backend/scripts/smoke_test_connectors.py --connector github`

---

## Environment Variable Master Checklist

All redirect URIs must point to: `https://app.axiohub.io/oauth/callback`

### Backend (.env)

| Variable | Status |
|----------|--------|
| `GOOGLE_CLIENT_ID` | [ ] |
| `GOOGLE_CLIENT_SECRET` | [ ] |
| `GOOGLE_REDIRECT_URI` | [ ] |
| `NOTION_CLIENT_ID` | [ ] |
| `NOTION_CLIENT_SECRET` | [ ] |
| `NOTION_REDIRECT_URI` | [ ] |
| `MICROSOFT_CLIENT_ID` | [ ] |
| `MICROSOFT_CLIENT_SECRET` | [ ] |
| `MICROSOFT_REDIRECT_URI` | [ ] |
| `MICROSOFT_TENANT_ID` | [ ] |
| `DROPBOX_CLIENT_ID` | [ ] |
| `DROPBOX_CLIENT_SECRET` | [ ] |
| `DROPBOX_REDIRECT_URI` | [ ] |
| `GITHUB_CLIENT_ID` | [ ] |
| `GITHUB_CLIENT_SECRET` | [ ] |
| `GITHUB_REDIRECT_URI` | [ ] |
| `BOX_CLIENT_ID` | [ ] |
| `BOX_CLIENT_SECRET` | [ ] |
| `BOX_REDIRECT_URI` | [ ] |

### Frontend (.env)

| Variable | Status |
|----------|--------|
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | [ ] |
| `NEXT_PUBLIC_GOOGLE_REDIRECT_URI` | [ ] |
| `NEXT_PUBLIC_NOTION_CLIENT_ID` | [ ] |
| `NEXT_PUBLIC_NOTION_REDIRECT_URI` | [ ] |
| `NEXT_PUBLIC_MICROSOFT_CLIENT_ID` | [ ] |
| `NEXT_PUBLIC_MICROSOFT_REDIRECT_URI` | [ ] |
| `NEXT_PUBLIC_MICROSOFT_TENANT_ID` | [ ] |
| `NEXT_PUBLIC_DROPBOX_CLIENT_ID` | [ ] |
| `NEXT_PUBLIC_GITHUB_CLIENT_ID` | [ ] |
| `NEXT_PUBLIC_BOX_CLIENT_ID` | [ ] |

### Global Production Settings

| Variable | Expected Value | Status |
|----------|---------------|--------|
| `ENVIRONMENT` | `production` | [ ] |
| `APP_URL` | `https://app.axiohub.io` | [ ] |
| `CHUNK_ENCRYPTION_KEY` | (generated Fernet key) | [ ] |
| `MALWARE_SCAN_FAIL_CLOSED` | `true` | [ ] |
| `STRICT_ENCRYPTION_MODE` | `true` | [ ] |

---

## Automated Validation

Run the validation script before and after updating environment variables:

```bash
# Validate all connectors
python backend/scripts/validate_production_oauth.py

# Run post-transition smoke tests
python backend/scripts/smoke_test_connectors.py
```

---

## Post-Transition Smoke Test

After all connectors are updated, run through each manually:

1. [ ] Connect Google Drive > list files > ingest a file > verify content
2. [ ] Connect Notion > verify auto-ingestion of pages
3. [ ] Connect OneDrive > list files > ingest
4. [ ] Connect SharePoint > list sites > list files > ingest
5. [ ] Connect Dropbox > personal & team account test
6. [ ] Connect GitHub > select repo > ingest code files
7. [ ] Connect Box > list files > ingest
8. [ ] Wait 1 hour > verify Box token auto-refresh
9. [ ] Wait 24 hours > verify Google/Microsoft token refresh still works

---

## Rollback Plan

If any connector breaks after transitioning:

1. Revert the environment variables to the previous (dev) values
2. Restart the backend service
3. Affected users will need to re-authenticate
4. For Google: if you've already published, you cannot unpublish — but dev credentials still work alongside production ones

---

## Timeline Estimate

| Phase | Duration |
|-------|----------|
| Pre-requisites (privacy policy, logos, domain verification) | 1-2 days |
| Submit all platform reviews | 1 day |
| Wait for approvals (Google is slowest) | 3-5 business days |
| Update env vars and deploy | 1 day |
| Smoke testing | 1 day |
| Monitor token refresh (24h) | 1 day |
| **Total** | **~7-10 business days** |
