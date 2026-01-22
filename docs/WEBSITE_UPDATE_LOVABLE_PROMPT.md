# AXIO HUB Website Update - Lovable Implementation Plan

> **Version:** 2.0 (Final)  
> **Last Updated:** January 22, 2026  
> **Status:** Ready for Implementation

---

## Context for Lovable AI

Update the marketing website (axiohub.io) to better communicate our unique competitive advantages. Two features differentiate us from every competitor in the market—and our current site undersells them.

**Brand Slogan (KEEP):** "Your Knowledge, Unified"  
**New Supporting Tagline:** "The AI that knows which source to trust"

---

## SECTION 1: HERO (Landing Page)

### Current
```
Headline: Your Knowledge, Unified.
Subheadline: From Personal Projects to Field Ops.
```

### Updated
```
Headline: Your Knowledge, Unified
Tagline: The AI that knows which source to trust

Body: Connect 12 data sources. Ask anything. Get answers from the right 
context—not a confused mix of everything.

CTA: Start Free → | Watch Demo
```

**Design Notes:**
- Keep headline typography bold and prominent
- Tagline should be slightly smaller, elegant weight
- Consider a subtle animation showing document icons flowing into one unified interface

---

## SECTION 2: THE PROBLEM (New Section - Add Below Hero)

### Content
```
Section Title: Two Problems Every AI Tool Ignores

────────────────────────────────────────────────────
PROBLEM #1: THE BLENDER EFFECT

You upload engineering docs, HR policies, and marketing materials. 
You ask "What's our authentication process?" 

You get an answer mixing code comments, a 2019 PDF, and your sales deck.

Every. Single. Time.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
PROBLEM #2: CONVERSATION AMNESIA

You clarify "I mean the customer support wiki" in message 3. 
Message 4 asks again. Message 5 asks again. 

Forever.
────────────────────────────────────────────────────

We built Axio to solve both.
```

**Design Notes:**
- Use a split-screen or card layout
- Problem cards should feel like "pain points" — subtle red/orange accent
- Transition to solution section should feel like relief

---

## SECTION 3: HOW WE SOLVE IT (Intelligence Features)

### Content
```
Section Title: Intelligence That Works

Subheadline: Not AI that guesses. AI that asks.

────────────────────────────────────────────────────
Feature 1: SCOPE DOMINANCE GUARD™

Our AI doesn't guess—it calculates.

For every query, we analyze which sources the answer comes from:

┌─────────────────────────────────────────────────────────────┐
│  ≥85% from one source → DOMINANT                            │
│  Answer confidently. Cite the source. Move on.              │
│                                                             │
│  "Based on Backend Docs: Here's how authentication works…"  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  60-84% from one source → CONTESTED                         │
│  Answer from primary. Show alternatives.                    │
│                                                             │
│  "Based on Backend Docs: [answer]                          │
│   Also found in: Product Manual, Engineering Wiki"          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  <60% fragmented → ASK THE USER                             │
│  Don't guess. Clarify.                                      │
│                                                             │
│  "I found relevant information in 3 sources.               │
│   Which should I focus on?"                                 │
└─────────────────────────────────────────────────────────────┘

No other AI knowledge tool does this. They all blend and hope.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
Feature 2: STICKY SCOPE SESSIONS

Tell us once. We remember.

When you select a scope—or when one source dominates 3 times 
in a row—we lock it for the entire conversation.

• Message 1: "Which source?" → You select "Engineering Wiki"
• Messages 2, 3, 4, 5…: All queries automatically scoped
• Visual indicator: 🔒 Searching in: Engineering Wiki
• Say "search all sources" anytime to unlock

No more repeating yourself.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
Feature 3: SOURCE CITATIONS

Every answer includes clickable citations to the exact document 
and passage. Verify AI responses instantly. Never wonder 
"where did that come from?"
────────────────────────────────────────────────────

────────────────────────────────────────────────────
Feature 4: HYBRID SEARCH

Combines keyword matching with semantic understanding. 
Find information even when you don't know the exact words.
────────────────────────────────────────────────────
```

**Design Notes:**
- Use a visual flowchart for the 85%/60%/<60% decision tree
- Color code: Green (DOMINANT), Amber (CONTESTED), Blue (CLARIFY)
- Animate the decision flow on scroll
- Show actual UI mockups for each path

---

## SECTION 4: HOW IT WORKS (Updated)

### Content
```
Section Title: How It Works

────────────────────────────────────────────────────
STEP 1: Connect Your Data

Link your Google Drive, Notion, GitHub, Dropbox, and 8 more 
sources in seconds. No complex setup. No data migration.

[Icons: Google Drive, Notion, GitHub, Dropbox, OneDrive, 
Confluence, SharePoint, Slack, S3, SFTP, Web, YouTube]
────────────────────────────────────────────────────

────────────────────────────────────────────────────
STEP 2: AI Processes & Understands

Ghost Protocol encrypts your data with zero-retention security.
Our Scope Analysis maps which documents belong to which projects.
Your data stays yours.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
STEP 3: Ask Anything

Chat naturally. When your question could come from multiple 
sources, we ask—we don't guess. Context-aware answers, 
every time.
────────────────────────────────────────────────────

────────────────────────────────────────────────────
STEP 4: Get Trusted Answers

Every response cites its source. If one source dominates, 
we tell you. If sources conflict, we ask you to choose.
Full transparency. No hallucinations hiding in plain sight.
────────────────────────────────────────────────────
```

**Design Notes:**
- Horizontal timeline on desktop, vertical on mobile
- Use connector icons for Step 1
- Show the encryption/lock visual for Step 2
- Chat bubble animation for Step 3
- Citation highlight animation for Step 4

---

## SECTION 5: RELIABILITY (New Section)

### Content
```
Section Title: Always-On Intelligence

Headline: When Your AI Provider Goes Down, You Don't

Most AI tools are single-provider wrappers. When that provider 
has problems—and they do, 2-3 times per month—your entire 
workflow stops.

Axio is different.

────────────────────────────────────────────────────
TRIPLE-REDUNDANT AI

┌─────────────────────────────────────────────────┐
│ PRIMARY: Industry-Leading LLM Provider          │
│                    ↓                            │
│      Circuit Breaker (5 failures)               │
│                    ↓                            │
│ FALLBACK 1: High-Performance Alternative        │
│                    ↓                            │
│ FALLBACK 2: Enterprise Backup Provider          │
└─────────────────────────────────────────────────┘

How it works:
• Normal operation: Queries route to primary provider
• 5 consecutive failures: Circuit breaker opens automatically
• All traffic routes to backup providers seamlessly
• After 60 seconds: Test request checks primary health
• If healthy: Normal operation resumes

Your team never sees an error page.
────────────────────────────────────────────────────

Key Stats:
• 99.9% effective uptime
• 3 AI providers
• 60-second automatic recovery
• Zero manual intervention required
```

**Design Notes:**
- Use a diagram showing the failover chain
- Subtle animation showing traffic flowing to backup when primary fails
- Display uptime stat prominently
- Consider a "status" indicator showing current provider health

---

## SECTION 6: SECURITY (Ghost Protocol - Keep Existing + Enhance)

### Content
```
Section Title: Ghost Protocol™ Security

Headline: Your Data Stays Yours

────────────────────────────────────────────────────
ZERO-RETENTION ARCHITECTURE

• We never store your raw documents
• Content is encrypted, chunked, and indexed
• Original files remain in your storage
• Delete anytime—truly gone

────────────────────────────────────────────────────
ENCRYPTION STANDARDS

• AES-256 encryption at rest
• TLS 1.3 in transit
• Key rotation support
• SOC 2 compliance ready

────────────────────────────────────────────────────
ENTERPRISE CONTROLS

• Row-Level Security (RLS)
• Organization isolation
• Audit logging
• SSO integration ready

────────────────────────────────────────────────────
MALWARE PROTECTION

• Real-time ClamAV scanning
• Infected files quarantined
• Admin notifications
• Automatic file rejection
────────────────────────────────────────────────────
```

---

## SECTION 7: LIVE DEMO (Updated)

### Content
```
Tab: For Teams (Disambiguation Demo)

[Chat Interface Mockup]

USER: How do we handle refunds?

AXIO: I found relevant information in 2 sources:
      
      📁 Customer Support Wiki (12 matches)
      📁 HR Policy Handbook (4 matches)
      
      Which should I focus on?
      
      [Customer Support Wiki]  [HR Policy Handbook]  [Search All]

[User clicks: Customer Support Wiki]

AXIO: Based on **Customer Support Wiki**:

      Refunds are processed within 5-7 business days. 
      For orders over $500, manager approval is required. 
      See the Escalation Matrix for edge cases.
      
      📎 Sources: refund-policy.md, escalation-guide.pdf
      
      ─────────────────────────────────
      🔒 Now searching in: Customer Support Wiki
      (Type "search all" to unlock)
```

**Design Notes:**
- Make this an interactive demo, not just a static image
- Show the scope lock appearing with subtle animation
- Highlight the citation links

---

## SECTION 8: COMPARISON TABLE (Features Page)

### Content
```
Section Title: How We Compare

| Capability                  | Traditional RAG | Other AI Tools | Axio Hub |
|-----------------------------|-----------------|----------------|----------|
| Multi-source ingestion      | ❌ Limited      | ⚠️ Varies      | ✅ 12 connectors |
| Source disambiguation       | ❌              | ❌              | ✅ Scope Guard |
| Asks before assuming        | ❌              | ❌              | ✅ Clarification flow |
| Conversation scope memory   | ❌              | ❌              | ✅ Sticky scope |
| Multi-provider failover     | ❌              | ❌              | ✅ 3 providers |
| Zero-retention security     | ❌              | ⚠️ Varies      | ✅ Ghost Protocol |
| Token quota management      | ❌              | ⚠️ Varies      | ✅ Per-plan limits |

Footnote: Comparison based on standard RAG implementations and 
publicly documented features as of January 2026.
```

**Design Notes:**
- Use ✅ (green), ⚠️ (amber), ❌ (red) for visual scanning
- Highlight Axio column with subtle brand color background
- Responsive: convert to comparison cards on mobile
- Keep it factual, not aggressive

---

## SECTION 9: TESTIMONIALS (Social Proof)

### Content
```
────────────────────────────────────────────────────
"Finally, an AI that doesn't mix up our internal docs with 
client materials. The clarification feature alone saved us 
from embarrassing mistakes."

— Engineering Manager, SaaS Company
────────────────────────────────────────────────────

────────────────────────────────────────────────────
"Our old AI tool went down during a client presentation. 
Embarrassing. With Axio's failover, we've never had that 
problem again."

— Operations Director, Consulting Firm
────────────────────────────────────────────────────

────────────────────────────────────────────────────
"I connect my Google Drive, Notion, and GitHub. Ask one 
question, get the right answer from the right source. 
That's it. That's the product."

— Solo Developer
────────────────────────────────────────────────────
```

**Design Notes:**
- Use a carousel or grid layout
- Include role/industry, not full names (privacy)
- Consider adding company logos if testimonials are from named companies

---

## SECTION 10: PRICING (Keep Existing + Add Badge)

### Content
```
Add to "All plans include" footer:

All plans include:
✓ Ghost Protocol zero-retention security
✓ AES-256 encryption  
✓ Malware scanning
✓ Multi-provider AI failover    ← NEW
✓ Source citations
```

---

## SECTION 11: FAQ (Add New Questions)

### Content
```
### Intelligence & Context

**Q: What happens when my question matches multiple sources?**

A: Axio's Scope Dominance Guard analyzes the distribution of relevant 
content across your sources. If one source clearly dominates (≥85% of 
matches), we answer from that source and tell you. If sources are 
contested (60-84%), we answer from the primary but show alternatives. 
If truly fragmented (<60%), we list the sources and ask you to choose.

**Q: What is "Sticky Scope"?**

A: When you select a source during clarification, or when one source 
dominates your queries 3 times in a row, we "lock" that scope for the 
rest of your conversation. You won't be asked the same clarification 
question repeatedly. Say "search all sources" to unlock anytime.

**Q: Does Axio mix up answers from different projects?**

A: No. This is exactly the problem we built Axio to solve. Traditional 
RAG tools retrieve chunks from all documents indiscriminately, leading 
to confused answers mixing context from different projects. Our Scope 
Dominance Guard prevents this by detecting conflicts and either asking 
for clarification or clearly attributing answers to specific sources.

### Reliability

**Q: What happens if your AI provider goes down?**

A: Your work continues uninterrupted. Axio uses a circuit breaker pattern 
with automatic failover to backup providers. If the primary experiences 
issues (5 consecutive failures), queries automatically route to backups. 
After 60 seconds, we test the primary again and resume normal operation 
if healthy. You may never notice an outage.

**Q: Do you depend on a single AI provider?**

A: No. We use a primary provider with multiple backup providers for 
redundancy. This triple-redundant architecture means your team stays 
productive even during major API outages.

### Security

**Q: What is Ghost Protocol?**

A: Ghost Protocol is our zero-retention security architecture. We never 
store your raw documents—content is encrypted, chunked, and indexed while 
originals stay in your storage. Delete anytime, and it's truly gone.

**Q: Is my data used to train AI models?**

A: Absolutely not. Your data is never used for training. It's processed, 
encrypted, and used only to serve your queries. Ghost Protocol ensures 
zero data retention beyond what's needed for your knowledge base.
```

---

## SECTION 12: FEATURES PAGE HERO (Updated)

### Content
```
Headline: Features That Actually Solve the Problem

Subheadline: Context intelligence no other tool has. 
             Enterprise security. 12 native connectors.
```

---

## DESIGN GUIDELINES

### Typography
- Keep existing font family for brand consistency
- Headline: Bold weight, large
- Tagline: Medium weight, elegant
- Body: Regular weight, comfortable reading

### Colors
- Keep existing brand palette
- Add accent colors for feature highlights:
  - Green: DOMINANT/Success states
  - Amber: CONTESTED/Warning states  
  - Blue: FRAGMENTED/Info states

### Animations
- Subtle, purposeful animations only
- Scroll-triggered reveals for sections
- Interactive elements for demo section
- No excessive motion that distracts

### Responsive
- All sections must work on mobile
- Comparison table → cards on mobile
- Flowcharts → vertical stacks on mobile
- Demo → simplified on mobile

---

## IMPLEMENTATION PRIORITY

| Priority | Section | Reason |
|----------|---------|--------|
| 1 | Hero | First impression, primary message |
| 2 | The Problem | Sets up the "why" |
| 3 | Intelligence Features | Core differentiator |
| 4 | Reliability | Enterprise buyers care |
| 5 | Comparison Table | Quick differentiation scan |
| 6 | Live Demo | Show, don't tell |
| 7 | FAQ Updates | Sales support |
| 8 | Testimonials | Social proof |

---

## CONTENT PRINCIPLES

1. **Be specific**: "85% threshold" not "smart detection"
2. **Name the problem**: "The Blender Effect" gives vocabulary
3. **Show the alternative**: "Other tools do X. We do Y."
4. **Keep it factual**: No aggressive competitor bashing
5. **Make it tangible**: Demo sequences showing actual UX

---

## WHAT TO KEEP (Already Good)

- ✅ "Your Knowledge, Unified" slogan
- ✅ Ghost Protocol messaging
- ✅ 12 connectors list with icons
- ✅ Pricing structure and tiers
- ✅ Trust badges and compliance info
- ✅ Use case demos (Personal/Teams/Operations)
- ✅ Overall visual design and brand identity

---

## SEO CONSIDERATIONS

### Target Keywords
- "RAG platform with source disambiguation"
- "AI knowledge management enterprise"
- "Multi-source document AI"
- "Context-aware AI assistant"
- "Zero-retention AI security"

### Meta Descriptions
- Home: "Your Knowledge, Unified. Axio Hub connects 12 data sources and delivers answers that cite the right source—never a confused mix."
- Features: "Context intelligence no other RAG tool has. Scope Dominance Guard, Sticky Scope Sessions, and Ghost Protocol security."

---

## FINAL CHECKLIST

Before deployment, verify:

- [ ] Hero displays combined slogan correctly
- [ ] No competitor names appear anywhere
- [ ] All feature percentages are accurate (85%, 60%)
- [ ] Comparison table uses generic terms only
- [ ] All animations are subtle and performant
- [ ] Mobile responsive on all sections
- [ ] FAQ answers are accurate to product behavior
- [ ] All CTAs link to correct destinations
- [ ] Page load time < 3 seconds
- [ ] All images have alt text

---

## END OF IMPLEMENTATION PLAN

Copy this document into Lovable to update axiohub.io with messaging 
that accurately reflects your true competitive advantages while 
maintaining professional, factual positioning.
