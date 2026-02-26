# AxioHub — Go-Live Action Plan & Positioning Fixes

**Date:** February 2026 | **Priority:** CRITICAL — Required Before VC Meetings & Public Launch

---

## CRITICAL FINDING: The Marketing Website Does Not Exist

After analyzing the actual frontend codebase (`frontend-new/`), a major discovery was made:

**The entire public-facing marketing website planned in `sitetexts.md` has NOT been built.** The current axiohub.io is exclusively a protected SaaS dashboard application. When someone visits axiohub.io, they are redirected to `/dashboard`, which requires authentication. There is:

- ❌ No landing page
- ❌ No features page
- ❌ No pricing page
- ❌ No security/Ghost Protocol page
- ❌ No integrations showcase
- ❌ No about/team page
- ❌ No contact page
- ❌ No FAQ page
- ❌ No public navigation header
- ❌ No footer (except minimal legal pages)

**What DOES exist:**
- ✅ Login page (email + Google OAuth)
- ✅ Register page (with password strength meter)
- ✅ Legal pages (/legal/terms, /legal/privacy)
- ✅ Full SaaS dashboard (chat, documents, settings, billing, team management)
- ✅ Production-grade security headers (CSP, HSTS, etc.)
- ✅ 404 page

This means **a VC visiting axiohub.io today sees a login wall** — no product explanation, no value proposition, no pricing, no team. This must be fixed before any investor conversation.

---

## PHASE 1: EMERGENCY — Build Before VC Meeting (1-2 Weeks)

### 1.1 Landing Page (/)

**Priority:** P0 — This is the #1 blocker

**What to build:**
The homepage must stop redirecting to `/dashboard` and instead show a compelling marketing page. Create a new route group `(marketing)` with a landing page.

**Required sections (minimum viable):**
1. **Hero** — "Your Knowledge, Unified" headline + "The intelligence layer for your files" subline + "Start Free Trial" CTA
2. **Trust Badges** — Ghost Protocol, AES-256, Zero-Retention, Malware Protected (drop "SOC 2 Ready" until you have a timeline)
3. **How It Works** — 3-step visual (Connect → Process & Secure → Ask Anything)
4. **Connector Grid** — Show all 12 logos with names
5. **Ghost Protocol Section** — 6 feature cards (Zero-Copy, AES-256, Forensic Wipe, SmartBuffer, Malware Scan, Dead Man's Switch)
6. **Pricing Preview** — 3 cards with CTA buttons
7. **Final CTA** — "Start Your Free Trial" with "No credit card required"

**Positioning fix:** Remove "Join thousands of teams" — replace with "Built for privacy-conscious teams" or "Trusted by teams who take data seriously."

**Technical approach:** Build as a static/SSG page within the existing Next.js app. Use the `(marketing)` route group with its own layout (no auth required).

### 1.2 Navigation Header & Footer

**Priority:** P0

**Header:** Logo + Features / Security / Pricing links + Sign In / Sign Up buttons. Must appear on all public pages.

**Footer:** 4 columns (Product, Resources, Company, Legal) + "© 2026 Axio Hub. Your data stays yours."

**Positioning fix:** Remove "Axial" references everywhere — the product is "AxioHub" or "Axio Hub." Ensure consistent branding.

### 1.3 Pricing Page (/pricing)

**Priority:** P0

**What to show:**
| | Starter | Pro | Enterprise |
|---|---------|-----|-----------|
| Price | $9.99/mo | $29/mo | Custom |
| Files | 50 | 2,000 | 100,000 |
| Storage | 100 MB | 10 GB | 1 TB |
| Team | 1 | 5 | 100 |
| AI Model | GPT-4o-mini | GPT-4o | GPT-4o |
| Connectors | All (except S3) | All (except S3) | All + S3 |

**Positioning fixes:**
- **Raise Starter from $4.99 to $9.99** — $4.99 signals "toy product." At $9.99 you're still accessible but signal real value. Ghost Protocol + AES-256 + ClamAV costs you money per user.
- **Add annual pricing** — $99/year for Starter (17% off), $290/year for Pro (17% off)
- **Add human-readable token limits** — "~500 questions/month" instead of "1M tokens"
- **Enterprise "Starting at $99/user/month"** — Give a price signal. "Custom" with no anchor drives prospects away.

### 1.4 Security Page (/security)

**Priority:** P0 — This is your strongest differentiator

**What to show:**
- Ghost Protocol 6-step flow visualization
- Technical specs table (AES-256-CBC, DoD 5220.22-M, ClamAV)
- "What We DON'T Store" section
- Data isolation explanation
- Compliance badges (GDPR, KVKK, CCPA)

**Positioning fixes:**
- **Remove "HIPAA Considerations"** — Either commit to HIPAA or don't mention it. "Considerations" is a non-statement that erodes trust.
- **Remove "SOC 2 Ready"** — Replace with "SOC 2 compliance on our 2026 roadmap" or remove entirely. "Ready" ≠ certified and VCs know this.
- **Add "Key Rotation" information** — The codebase supports it, mention it.

### 1.5 About Page with Team (/about)

**Priority:** P0 — VCs invest in people

**What to show:**
- Company mission (2-3 sentences)
- Founder bio with photo, LinkedIn link, relevant background
- Key team members (if any)
- Company info: FITTECHS YAZILIM A.S., Istanbul, Turkey
- Contact: hello@axiohub.io (standardize to ONE domain)

**Positioning fixes:**
- **Use ONLY @axiohub.io emails** — The site currently mixes axiohub.io and fittechs.com. Pick one for public communications.
- **Add a "Why We Built This" narrative** — VCs love origin stories. 2-3 sentences about the problem you personally experienced.

---

## PHASE 2: PRE-LAUNCH — Build Before Public Launch (2-4 Weeks)

### 2.1 Features Page (/features)

**6 sections:**
1. Unified Data Connectivity (12 connectors)
2. Intelligent AI Chat (streaming, citations, conversation memory)
3. Scope-Aware Intelligence (Scope Guard, Smart Clarification)
4. Ghost Protocol Security (zero-retention, encryption, wipe)
5. Team Collaboration (RBAC, invites, audit logs)
6. Enterprise Ready (org isolation, RLS, compliance)

**Positioning fix:** Add **product screenshots**. Without visuals, features are just claims. Take 3-5 screenshots of: (1) the chat interface with source citations, (2) the connector setup flow, (3) the document dashboard, (4) the scope clarification dialog, (5) the security/audit log.

### 2.2 Integrations Page (/integrations)

Show all 12 connectors with:
- Logo, name, category
- 1-line description
- Auth method (OAuth/Credentials)
- "Coming Soon" section (Jira, Slack, Monday.com, Asana, Trello, Confluence)

**Positioning fix:** Add "Request an Integration" form or link. This signals customer-centricity and helps you prioritize the roadmap.

### 2.3 Contact Page (/contact)

Simple form: Name, Email, Subject, Message + company address.

**Positioning fix:** Add "Response Time: We typically respond within 24 hours." Set expectations.

### 2.4 FAQ Page (/faq)

Use the content from sitetexts.md — it's well-written. Key topics: What is AxioHub, Is my data safe, Does your AI train on my data, What are vector embeddings, pricing questions.

### 2.5 Product Screenshots & Demo Video

**Priority:** HIGH — This is the second biggest gap after the landing page

**Options (in order of effort):**
1. **Static screenshots** (1 day) — Take 5 screenshots of the live dashboard, annotate with captions
2. **Animated GIF demo** (2 days) — Record a 30-second flow: connect → upload → ask → get answer with citations
3. **Video walkthrough** (3-5 days) — 60-90 second narrated product tour
4. **Interactive sandbox** (1-2 weeks) — Pre-loaded demo environment with sample data

At minimum, do option 1 before any VC meeting.

---

## PHASE 3: POSITIONING FIXES (Apply Across All Pages)

### 3.1 Messaging Hierarchy Fix

**Current problem:** The site (in sitetexts.md) tries to be everything — "personal projects to field ops." This dilutes the message.

**Recommended positioning hierarchy:**

**Primary message (Hero):**
> "The zero-retention AI knowledge platform. Connect your data, ask anything, keep nothing."

**Secondary message (Subhero):**
> "AxioHub connects your tools, processes your documents with military-grade security, and lets you chat with your knowledge base — with source citations for every answer."

**Why this works:**
- Leads with the differentiator (zero-retention)
- Immediately tells you what category (AI knowledge platform)
- Three clear value props in one sentence (connect, secure, chat)
- Closes with a proof point (source citations)

### 3.2 Target Audience Positioning

**Current problem:** Trying to serve freelancers ($4.99/mo), teams ($29/mo), and enterprises (custom) simultaneously dilutes focus.

**Recommended focus for seed stage:**

**Primary:** Privacy-conscious SMBs and mid-market teams (5-50 employees) in regulated industries
- Legal firms (contract analysis, case research)
- Healthcare organizations (policy compliance, clinical protocols)
- Financial services (regulatory documents, audit trails)
- Energy/industrial (maintenance manuals, safety protocols)

**Secondary:** Tech-forward startups with compliance requirements (SOC 2 aspirants, GDPR-bound)

**Why:** These customers (a) have budget, (b) care deeply about Ghost Protocol, (c) have clear pain points, and (d) are reachable through targeted marketing.

### 3.3 Competitive Positioning

**Add a "Why AxioHub" or comparison section:**

| | AxioHub | Glean | Notion AI | Guru |
|---|---------|-------|-----------|------|
| Data retention | Zero (Ghost Protocol) | Stores copies | Stores copies | Stores copies |
| Connectors | 12 native | 100+ | 1 (Notion only) | 40+ |
| Context disambiguation | Scope Guard | None | None | None |
| Pricing | From $9.99/mo | $10/user/mo (enterprise only) | $10/user/mo | $15/user/mo |
| Compliance | GDPR, CCPA, KVKK | GDPR, SOC 2 | GDPR | GDPR, SOC 2 |
| Security | AES-256 + DoD wipe | Enterprise encryption | Standard | Standard |
| Self-serve signup | Yes | No (sales only) | Yes | Yes |

**Key differentiator narrative:**
> "Glean and Guru connect more tools but store copies of your data indefinitely. Notion AI only works within Notion. AxioHub is the only platform that gives you multi-source knowledge search with zero data retention — your files are encrypted, processed, and cryptographically wiped."

### 3.4 Social Proof Strategy

**Immediate (before VC):**
- Remove all anonymous testimonials
- Replace with: "Currently in private beta with select teams" or show actual beta metrics
- If you have ANY real users, get 1-2 quotes with names/titles

**Short-term (1 month):**
- Product Hunt launch → collect reviews
- Reach out to 3-5 beta users for case studies
- Get listed on G2, Capterra

**Medium-term (3 months):**
- 2-3 published case studies with ROI metrics
- Logo bar with customer companies (with permission)
- Third-party review aggregation

### 3.5 SEO Foundation

**Before launch:**
1. Create `robots.txt` allowing indexing of marketing pages
2. Generate `sitemap.xml` for all public pages
3. Set up Google Search Console and submit sitemap
4. Add Open Graph tags to all pages (title, description, image)
5. Add Twitter Card meta tags
6. Set canonical URLs
7. Create a blog section at /blog with 2-3 initial posts:
   - "What is Zero-Retention AI and Why It Matters"
   - "How Ghost Protocol Protects Your Data"
   - "RAG vs Traditional Search: Why Context Matters"

### 3.6 Brand Consistency Fixes

| Issue | Current | Fix |
|-------|---------|-----|
| Product name | "Axial" / "Axio Hub" / "AxioHub" mixed | Standardize to **"AxioHub"** everywhere |
| Email domain | @axiohub.io and @fittechs.com | Use **@axiohub.io** for all public comms |
| Company name | Sometimes FITTECHS, sometimes omitted | Use "AxioHub by FITTECHS" or just "AxioHub" |
| Copyright | "Axio Hub" | Match product name: "AxioHub" |
| Support email | support@fittechs.com | Change to support@axiohub.io |

---

## PHASE 4: CONVERSION OPTIMIZATION

### 4.1 CTA Strategy

**Primary CTA:** "Start Free Trial" (not "Join Now" or "Get Started")
- "Start Free Trial" converts 2-3x better than generic CTAs
- Add "No credit card required" beneath every primary CTA
- Specify trial length: "14-day free trial" consistently

**Secondary CTA:** "See How It Works" → links to demo video or interactive tour

**Enterprise CTA:** "Book a Demo" → Calendly link or form

### 4.2 Trust Signal Placement

On every page, show at minimum:
- Ghost Protocol badge
- AES-256 encryption badge
- "Your data stays yours" tagline in footer

On pricing page, add:
- "Cancel anytime"
- "No long-term contracts"
- "Enterprise SLA available"

### 4.3 Exit Intent / Lead Capture

Add email capture for visitors who don't sign up:
- "Get our Security Whitepaper" — captures enterprise leads
- "Subscribe to product updates" — captures interested but not ready leads

---

## IMPLEMENTATION PRIORITY MATRIX

### Week 1 (Before VC Meeting)

| # | Task | Type | Effort | Impact |
|---|------|------|--------|--------|
| 1 | Build landing page with hero, trust badges, how-it-works, Ghost Protocol, pricing preview, CTA | Dev | 3-4 days | Critical |
| 2 | Build global header + footer | Dev | 1 day | Critical |
| 3 | Build pricing page | Dev | 1 day | Critical |
| 4 | Build security page | Dev | 1 day | Critical |
| 5 | Add team bio to about page | Content | 2 hours | Critical |
| 6 | Take 5 product screenshots | Content | 2 hours | High |
| 7 | Standardize branding (AxioHub, @axiohub.io) | Content | 1 hour | High |
| 8 | Update pricing (Starter $9.99, add annual) | Code + Content | 2 hours | High |

### Week 2 (Before Public Launch)

| # | Task | Type | Effort | Impact |
|---|------|------|--------|--------|
| 9 | Build features page with screenshots | Dev | 1 day | High |
| 10 | Build integrations page | Dev | 1 day | Medium |
| 11 | Build contact page | Dev | 0.5 day | Medium |
| 12 | Build FAQ page | Dev | 0.5 day | Medium |
| 13 | SEO setup (sitemap, robots, OG tags, Search Console) | Dev | 1 day | High |
| 14 | Create 2 blog posts | Content | 2 days | High |
| 15 | Record product demo video (60s) | Content | 1 day | High |
| 16 | Remove anonymous testimonials | Content | 1 hour | High |

### Week 3-4 (Launch)

| # | Task | Type | Effort | Impact |
|---|------|------|--------|--------|
| 17 | Product Hunt launch prep + submission | Marketing | 2 days | High |
| 18 | LinkedIn company page + first 5 posts | Marketing | 1 day | Medium |
| 19 | Twitter/X account + first posts | Marketing | 0.5 day | Medium |
| 20 | G2/Capterra listing | Marketing | 1 day | Medium |
| 21 | "AxioHub vs Glean" comparison page | Content | 1 day | High |
| 22 | Security whitepaper PDF | Content | 2 days | Medium |

---

## POSITIONING SUMMARY — The AxioHub Story for VCs

### Elevator Pitch (30 seconds):
> "AxioHub is the first zero-retention AI knowledge platform. We connect an organization's data sources — Google Drive, Notion, GitHub, 12 connectors total — and let teams chat with their knowledge base using AI. What makes us different: Ghost Protocol. We process your documents, extract knowledge as encrypted vectors, then cryptographically wipe the originals. Your data literally disappears after processing. This unlocks regulated industries — legal, healthcare, finance — that can't use Glean or Notion AI because of data retention policies."

### One-Liner (for email/LinkedIn):
> "AxioHub: AI-powered knowledge search with zero data retention. Connect everything, ask anything, keep nothing."

### Tagline Options:
1. "Your Knowledge, Unified. Your Data, Protected." (current — good)
2. "The Zero-Retention Knowledge Platform." (sharper)
3. "Ask Your Data Anything. Keep Nothing." (provocative)
4. "Ghost Protocol Intelligence." (brand-forward)

---

*This action plan was created based on analysis of the actual frontend codebase (frontend-new/), site content plan (sitetexts.md), production documentation, backend configuration, and competitive landscape research.*
