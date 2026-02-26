# Lovable Prompt — AxioHub Website Complete Fix

Below is the prompt to paste into Lovable. Copy everything between the `---START---` and `---END---` markers.

---START---

I need you to make a comprehensive set of fixes across my entire axiohub.io website. These are organized by priority. Please implement ALL of them in a single update.

---

## PART 1: CRITICAL CONTENT FIXES (Legal & Credibility Risks)

### 1.1 — /security page: Fix SOC 2 claim

Find any mention of "SOC 2 Type II" on the security page. Change it to:

"SOC 2 Type II — Architecture Ready (certification roadmap 2026)"

If there's a badge or icon for SOC 2, keep the icon but update the label to "SOC 2 Ready" instead of "SOC 2 Type II".

### 1.2 — /security page: Fix HIPAA claim

Find any mention of "HIPAA" on the security page. Change it to:

"HIPAA-Ready Architecture"

If there is a badge, update label to "HIPAA-Ready". Do NOT claim full HIPAA compliance.

### 1.3 — /solutions/teams page: Remove "subpoena-proof" language

Find and replace ALL instances of language about data being "subpoena-proof", "cannot be subpoenaed", "subpoena edilemeyecek", or similar legal claims.

Replace with this exact wording:

"Minimal Discovery Surface — By not retaining original documents after processing, AxioHub significantly reduces the scope of data subject to potential discovery or regulatory requests."

Also find the "Privilege by Design" section. Keep the heading but rewrite the description to:

"Data that doesn't exist can't be requested. AxioHub's zero-retention architecture means processed documents are cryptographically destroyed — leaving only encrypted intelligence vectors with no recoverable source material."

### 1.4 — /solutions/individuals page: Remove "whistleblower" and "burner" language

Make these specific changes:

1. Find "Digital Burner Mode" — rename to "Ephemeral Analysis Mode"
2. Find any mention of "whistleblowers" in the target audience — replace with "independent analysts"
3. Find "Zero-Trace Operations" — keep this, it's fine
4. Find "Single-Session Memory" — keep this, it's fine

The target audience description should read:
"Built for independent consultants, legal professionals, research analysts, and anyone who needs to analyze sensitive documents without creating persistent data copies."

Remove any references to "journalists investigating", "traders avoiding", or any language that positions the product as a tool for evading oversight.

### 1.5 — /solutions/enterprise page: Rename "Kill Switch"

Find "24/7 Kill Switch" — rename to "24/7 Emergency Data Purge"

Update the description to:
"Instant compliance response. Trigger an organization-wide data purge at any time — all vectors, indexes, and encrypted chunks are cryptographically destroyed within minutes. Full audit trail maintained for regulatory documentation."

---

## PART 2: SEO FIXES (Missing Meta Tags)

The following pages are missing custom title, canonical, og:url, and Twitter tags. They are currently falling back to the default homepage meta tags, which causes duplicate content issues for Google.

Add unique meta tags to each of these 8 pages:

### /features
```
title: "Features | Scope Guard, Ghost Protocol & AI Chat — Axio Hub"
description: "Scope Dominance Guard, hybrid search, source citations, 3-provider AI failover, and zero-retention security. The most reliable enterprise RAG platform."
canonical: "https://axiohub.io/features"
og:url: "https://axiohub.io/features"
og:title: "Features | Scope Guard, Ghost Protocol & AI Chat — Axio Hub"
og:description: "Scope Dominance Guard, hybrid search, source citations, 3-provider AI failover, and zero-retention security. The most reliable enterprise RAG platform."
twitter:title: "Features | Scope Guard, Ghost Protocol & AI Chat — Axio Hub"
twitter:description: "Scope Dominance Guard prevents context collision. Ghost Protocol ensures zero retention. 3-provider failover guarantees 99.9% uptime. See all features."
```

### /pricing
```
title: "Pricing | Starter, Pro & Enterprise Plans — Axio Hub"
description: "Simple, transparent pricing. Starter from $4.99/mo, Pro $29/mo, Enterprise custom. All plans include Ghost Protocol zero-retention security and AES-256 encryption."
canonical: "https://axiohub.io/pricing"
og:url: "https://axiohub.io/pricing"
og:title: "Pricing | Starter, Pro & Enterprise Plans — Axio Hub"
og:description: "Simple, transparent pricing. Starter from $4.99/mo, Pro $29/mo, Enterprise custom. All plans include Ghost Protocol zero-retention security and AES-256 encryption."
twitter:title: "Pricing | Starter, Pro & Enterprise Plans — Axio Hub"
twitter:description: "All plans include Ghost Protocol, AES-256 encryption, and malware scanning. Start with Starter at $4.99/mo or go Pro at $29/mo."
```

### /about
```
title: "About Us | The Team Behind Axio Hub"
description: "We believe AI should amplify intelligence without creating data liability. Meet the team building the zero-retention AI knowledge platform."
canonical: "https://axiohub.io/about"
og:url: "https://axiohub.io/about"
og:title: "About Us | The Team Behind Axio Hub"
og:description: "We believe AI should amplify intelligence without creating data liability. Meet the team building the zero-retention AI knowledge platform."
twitter:title: "About Us | The Team Behind Axio Hub"
twitter:description: "AI should amplify intelligence without creating data liability. Learn about the mission and team behind Axio Hub."
```

### /contact
```
title: "Contact Us — Axio Hub"
description: "Get in touch with the Axio Hub team. Enterprise demos, partnership inquiries, and support. We respond within 24 hours."
canonical: "https://axiohub.io/contact"
og:url: "https://axiohub.io/contact"
og:title: "Contact Us — Axio Hub"
og:description: "Get in touch with the Axio Hub team. Enterprise demos, partnership inquiries, and support. We respond within 24 hours."
twitter:title: "Contact Us — Axio Hub"
twitter:description: "Questions about Axio Hub? Reach out for enterprise demos, partnerships, or support."
```

### /privacy
```
title: "Privacy Policy | Zero-Copy Architecture — Axio Hub"
description: "How Axio Hub protects your data with Zero-Copy Architecture. GDPR, KVKK, and CCPA compliant. Original files are never stored — only encrypted vectors."
canonical: "https://axiohub.io/privacy"
og:url: "https://axiohub.io/privacy"
og:title: "Privacy Policy | Zero-Copy Architecture — Axio Hub"
og:description: "How Axio Hub protects your data with Zero-Copy Architecture. GDPR, KVKK, and CCPA compliant. Original files are never stored."
twitter:title: "Privacy Policy — Axio Hub"
twitter:description: "Zero-Copy Architecture means your files stay where they are. We only store encrypted vector embeddings. Read our full privacy policy."
```

### /solutions/individuals
```
title: "For Individuals | Ephemeral Document Analysis — Axio Hub"
description: "Analyze sensitive documents without creating persistent copies. Ephemeral processing, single-session memory, and Ghost Protocol security for independent professionals."
canonical: "https://axiohub.io/solutions/individuals"
og:url: "https://axiohub.io/solutions/individuals"
og:title: "For Individuals | Ephemeral Document Analysis — Axio Hub"
og:description: "Analyze sensitive documents without creating persistent copies. Ephemeral processing with Ghost Protocol security."
twitter:title: "For Individuals — Axio Hub"
twitter:description: "Your second brain. Off the record. Ephemeral document analysis with zero-retention security for independent professionals."
```

### /solutions/enterprise
```
title: "For Enterprise | Zero-Retention AI with BYOK & VPC — Axio Hub"
description: "Deploy enterprise AI without data liability. Bring Your Own Key encryption, VPC deployment options, emergency data purge, and 99.9% uptime SLA."
canonical: "https://axiohub.io/solutions/enterprise"
og:url: "https://axiohub.io/solutions/enterprise"
og:title: "For Enterprise | Zero-Retention AI with BYOK & VPC — Axio Hub"
og:description: "Deploy enterprise AI without data liability. BYOK encryption, VPC deployment, emergency data purge, and 99.9% uptime SLA."
twitter:title: "For Enterprise — Axio Hub"
twitter:description: "Intelligence without liability. BYOK encryption, VPC deployment, 24/7 emergency data purge, and 99.9% uptime SLA for regulated industries."
```

Also update the **keywords** meta tag on each page to be page-specific instead of the same generic keywords everywhere:

- /features → "scope guard, ghost protocol features, AI chat with citations, hybrid search, enterprise RAG features, zero-retention AI"
- /pricing → "axio hub pricing, AI knowledge base cost, enterprise RAG pricing, ghost protocol plans"
- /about → "axio hub team, fittechs, AI startup Istanbul, zero-retention AI company"
- /contact → "contact axio hub, enterprise demo, AI knowledge base support"
- /privacy → "axio hub privacy policy, zero-copy architecture, GDPR KVKK CCPA compliance"
- /solutions/individuals → "individual AI knowledge base, personal document analysis, ephemeral AI processing"
- /solutions/enterprise → "enterprise AI knowledge base, BYOK encryption, VPC AI deployment, zero-retention enterprise"

---

## PART 3: BRAND CONSISTENCY FIXES

### 3.1 — /contact page: Fix email address

Find `support@fittechs.com` on the contact page. Replace with `support@axiohub.io`.

Keep the company name "FITTECHS YAZILIM ANONIM ŞİRKETİ" and the Istanbul address — those are correct for legal purposes.

### 3.2 — Standardize product name

Search the ENTIRE site for inconsistencies in the product name. The official name is **"Axio Hub"** (with a space). Make sure:
- All page titles use "Axio Hub" (not "AxioHub", "Axio", or "AXIO HUB")
- Footer copyright uses "Axio Hub"
- Any references in body text use "Axio Hub"

Exception: The domain "axiohub.io" stays as-is (no space in URLs).

---

## PART 4: STRUCTURED DATA (JSON-LD)

Add the following JSON-LD structured data:

### On every page (in the root layout or head):
```json
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Axio Hub",
  "applicationCategory": "BusinessApplication",
  "operatingSystem": "Web",
  "url": "https://axiohub.io",
  "description": "AI-powered knowledge base with zero-retention security. Connect data sources, chat with documents, retain nothing.",
  "offers": {
    "@type": "AggregateOffer",
    "lowPrice": "4.99",
    "highPrice": "29.00",
    "priceCurrency": "USD",
    "offerCount": "3"
  },
  "provider": {
    "@type": "Organization",
    "name": "FITTECHS YAZILIM ANONIM ŞİRKETİ",
    "url": "https://axiohub.io",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "Gayrettepe Mahallesi Yıldız Posta Caddesi Akın Sitesi 8/34",
      "addressLocality": "Beşiktaş",
      "addressRegion": "İstanbul",
      "addressCountry": "TR"
    },
    "contactPoint": {
      "@type": "ContactPoint",
      "email": "hello@axiohub.io",
      "contactType": "sales"
    }
  }
}
```

### On /faq page only — add FAQ structured data:
Take each question-answer pair on the /faq page and wrap them in FAQPage schema:
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "[question text]",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "[answer text]"
      }
    }
  ]
}
```
Include ALL questions from the FAQ page in this schema.

### On /pricing page only:
```json
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Axio Hub",
  "description": "AI Knowledge Base with Ghost Protocol Security",
  "offers": [
    {
      "@type": "Offer",
      "name": "Starter",
      "price": "4.99",
      "priceCurrency": "USD",
      "priceValidUntil": "2026-12-31",
      "availability": "https://schema.org/InStock"
    },
    {
      "@type": "Offer",
      "name": "Pro",
      "price": "29.00",
      "priceCurrency": "USD",
      "priceValidUntil": "2026-12-31",
      "availability": "https://schema.org/InStock"
    }
  ]
}
```

---

## PART 5: MINOR CONTENT IMPROVEMENTS

### 5.1 — /pricing page: Add human-readable token limits

Next to each plan's token limit, add a parenthetical explanation:
- Starter "1M tokens" → "1,000,000 AI tokens (~300-1,000 questions/month)"
- Pro "10M tokens" → "10,000,000 AI tokens (~3,000-10,000 questions/month)"
- Enterprise "100M tokens" → "100,000,000 AI tokens (~30,000-100,000 questions/month)"

### 5.2 — /pricing page: Add annual pricing toggle

Add a monthly/annual toggle to the pricing page. Annual prices:
- Starter: $49/year (save ~18%)
- Pro: $290/year (save ~17%)
- Enterprise: remains "Custom"

Show both options with a toggle switch. Default to monthly view. When annual is selected, show the monthly equivalent with strikethrough on the regular price and the annual savings percentage.

### 5.3 — Update legal document dates

On /privacy and /terms pages, update "Effective Date: December 25, 2025" to "Effective Date: February 2026" or the actual current date.

### 5.4 — /blog: Make sure all 4 blog posts from sitemap are visible

The sitemap lists these blog posts:
1. /blog/what-is-an-ai-knowledge-base
2. /blog/how-to-chat-with-documents-using-ai
3. /blog/enterprise-rag-vs-chatgpt-for-business
4. /blog/multi-source-document-ai-why-it-matters

Make sure all 4 are published and visible on the /blog listing page. If any are in draft state, publish them.

---

## SUMMARY OF ALL CHANGES

- **7 critical content fixes** (SOC 2, HIPAA, subpoena-proof, whistleblowers, burner mode, kill switch, email)
- **8 pages need unique meta tags** (title, description, canonical, OG, Twitter)
- **8 pages need unique keywords**
- **Brand name standardization** across all pages
- **3 JSON-LD structured data blocks** (Organization/Software on all pages, FAQ on /faq, Product on /pricing)
- **Annual pricing toggle** on /pricing
- **Human-readable token limits** on /pricing
- **Legal document date updates**
- **Blog post visibility check**

Please implement all changes and confirm each section is complete.

---END---
