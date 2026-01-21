/**
 * Help Articles Data - Production Grade
 * 
 * Comprehensive in-app Help Center documentation for Axio Hub.
 * All content is verified against the actual codebase implementation.
 * 
 * Categories:
 * - General: Getting started, overview content
 * - AI Features: Model routing, search, Ghost Protocol
 * - Connectors: Individual connector guides with setup, errors, troubleshooting
 * - Teams: Team management, roles, invitations
 * - Billing: Plans, quotas, usage limits
 * - Troubleshooting: Common errors, solutions, FAQs
 */

export interface HelpArticle {
    id: string;
    title: string;
    category: 'General' | 'AI Features' | 'Connectors' | 'Teams' | 'Billing' | 'Troubleshooting';
    content: string; // Markdown
    keywords?: string[]; // For improved search
}

export const HELP_ARTICLES: HelpArticle[] = [
    // =========================================================================
    // GENERAL - Getting Started & Overview
    // =========================================================================
    {
        id: 'getting-started',
        title: 'Getting Started with Axio Hub',
        category: 'General',
        keywords: ['start', 'begin', 'setup', 'first', 'new', 'welcome'],
        content: `
# Welcome to Axio Hub

Axio Hub is your AI-powered knowledge assistant that lets you chat with your documents, code repositories, and cloud files. Here's how to get started.

## Step 1: Upload Your First Documents

1. Click **Knowledge Base** in the left sidebar
2. Click the **Upload** button or drag and drop files
3. Wait for processing to complete (you'll see a progress indicator)

### Supported File Formats

| Format | Extensions | Notes |
|--------|------------|-------|
| **Documents** | PDF, DOCX, DOC, RTF | Full text extraction with OCR for scanned pages |
| **Spreadsheets** | XLSX, XLS, CSV | Row-by-row extraction, preserves structure |
| **Presentations** | PPTX, PPT | Slide-by-slide extraction |
| **Text** | TXT, MD, HTML, XML | Direct text processing |
| **Email** | EML, MSG | Headers, body, and attachment names |
| **Code** | 60+ languages | Python, JavaScript, TypeScript, Go, Rust, Java, etc. |
| **Images** | PNG, JPG, TIFF | OCR text extraction |

**File Size Limit:** 100 MB per file

## Step 2: Connect Cloud Storage (Optional)

1. Go to **Settings → Data Sources**
2. Click **Connect** next to your preferred service
3. Authorize access when prompted
4. Select folders or repositories to sync

**Available Connectors:**
- Google Drive, OneDrive, SharePoint, Dropbox
- Notion, GitHub, Box
- Amazon S3 (Enterprise only)
- SFTP servers
- Web pages and sitemaps

## Step 3: Start Chatting

1. Click **New Chat** in the sidebar
2. Type your question about your documents
3. Get AI-powered answers with **source citations**

## Tips for Best Results

- **Upload complete documents** — not snippets or excerpts
- **Use descriptive file names** — "Q4-2024-Financial-Report.pdf" is better than "doc1.pdf"
- **Organize by project** — use folders in your connected sources for logical grouping
- **Be specific in questions** — "What were the Q3 revenue numbers?" works better than "Tell me about finances"

## Understanding Source Citations

Every AI response includes citations showing exactly where the information came from:

\`\`\`
Based on your documents, the Q3 revenue was $4.2M [1]

Sources:
[1] Q3-Financial-Report.pdf, page 12
\`\`\`

Click any citation to view the original source.
        `
    },
    {
        id: 'supported-file-formats',
        title: 'Supported File Formats & Limits',
        category: 'General',
        keywords: ['format', 'file', 'type', 'pdf', 'docx', 'upload', 'size', 'limit'],
        content: `
# Supported File Formats

Axio Hub supports a wide range of file formats with intelligent parsing and OCR capabilities.

## Document Formats

| Format | Extensions | Max Size | OCR Support | Processing Notes |
|--------|------------|----------|-------------|------------------|
| **PDF** | .pdf | 100 MB | ✅ Yes | 3-tier fallback: cloud parsing → local extraction → OCR |
| **Word** | .docx, .doc | 100 MB | ✅ Yes | Full formatting preserved; legacy .doc uses cloud parsing |
| **Rich Text** | .rtf | 100 MB | ❌ No | Cloud parsing for complex formatting |

### PDF Processing Details

PDFs are processed using a resilient 3-tier architecture:

1. **Tier 1 (Cloud):** LlamaParse for complex layouts, tables, and scanned documents
2. **Tier 2 (Local):** PyMuPDF for standard text-based PDFs
3. **Tier 3 (OCR):** Tesseract for image-only or scanned pages

**Why this matters:** If cloud parsing is temporarily unavailable, your PDFs still process successfully using local methods.

## Spreadsheet Formats

| Format | Extensions | Max Size | Processing Notes |
|--------|------------|----------|------------------|
| **Excel** | .xlsx, .xls | 100 MB | Streaming mode, 200 rows per chunk |
| **CSV** | .csv, .tsv | 100 MB | 500 rows per chunk, auto-delimiter detection |

### Spreadsheet Tips

- **Large files:** Processed in chunks to prevent memory issues
- **Multiple sheets:** Each sheet is processed separately
- **Formulas:** Cell values (not formulas) are extracted
- **Formatting:** Column headers are preserved for context

## Presentation Formats

| Format | Extensions | Max Size | OCR Support |
|--------|------------|----------|-------------|
| **PowerPoint** | .pptx, .ppt | 100 MB | ✅ Yes |

Each slide is extracted as a separate chunk with:
- Slide title and number
- Text content from all text boxes
- Speaker notes (if present)
- Table content

## Text & Markup Formats

| Format | Extensions | Max Size |
|--------|------------|----------|
| **Plain Text** | .txt | 100 MB |
| **Markdown** | .md, .mdx | 100 MB |
| **HTML** | .html, .htm | 100 MB |
| **XML** | .xml | 100 MB |

## Email Formats

| Format | Extensions | Max Size | Notes |
|--------|------------|----------|-------|
| **Email** | .eml | 100 MB | Standard email format |
| **Outlook** | .msg | 100 MB | Microsoft Outlook format |

Extracted information includes:
- From, To, CC, BCC
- Subject line
- Date sent
- Body text (plain text and HTML)
- Attachment filenames (attachments not processed)

## Code Files

Over **60 programming languages** are supported:

| Category | Extensions |
|----------|------------|
| **Web** | .js, .jsx, .ts, .tsx, .html, .css, .scss, .vue, .svelte |
| **Backend** | .py, .go, .rs, .java, .kt, .rb, .php, .cs |
| **Systems** | .c, .cpp, .h, .hpp, .swift, .m |
| **Data** | .sql, .json, .yaml, .yml, .xml |
| **Config** | Dockerfile, Makefile, .gitignore, package.json |
| **Docs** | .md, .rst, .txt, README, LICENSE |

### Code Processing Features

- Syntax-aware chunking (respects function boundaries)
- Automatic filtering of build artifacts and dependencies
- Preserves code structure and comments

## Image Formats (OCR)

| Format | Extensions | Max Size | Notes |
|--------|------------|----------|-------|
| **Images** | .png, .jpg, .jpeg, .tiff, .gif, .webp | 100 MB | Text extraction via OCR |

### OCR Processing

1. **Primary:** Tesseract OCR (local, fast)
2. **Fallback:** LlamaParse (cloud, higher accuracy for complex layouts)

**Best for:** Scanned documents, screenshots, photos of whiteboards

## Unsupported Formats

The following are **not processed** and will be skipped:

- Binary executables (.exe, .dll, .so)
- Compressed archives (.zip, .tar, .gz) — extract first
- Media files (.mp4, .mp3, .wav)
- Database files (.sqlite, .mdb)
- Design files (.psd, .ai, .sketch)

## File Size Limits

| Plan | Per-File Limit | Total Storage |
|------|----------------|---------------|
| **Starter** | 100 MB | 100 MB |
| **Pro** | 100 MB | 10 GB |
| **Enterprise** | 100 MB | 1 TB |

**Note:** The 100 MB per-file limit applies to all plans. Storage limits determine your total capacity.
        `
    },

    // =========================================================================
    // AI FEATURES
    // =========================================================================
    {
        id: 'ai-smart-router',
        title: 'How AI Model Selection Works',
        category: 'AI Features',
        keywords: ['model', 'gpt', 'ai', 'smart', 'fast', 'router', 'llm'],
        content: `
# AI Model Selection (Smart Router)

Axio Hub uses intelligent routing to select the best AI model for each query, balancing speed and intelligence.

## How It Works

When you send a message, our Smart Router analyzes:

1. **Query complexity** — Is this a simple lookup or complex analysis?
2. **Keywords** — Certain terms trigger the smart model
3. **Your plan tier** — Determines available models

## Available Models

### ⚡ Fast Mode (GPT-4o-mini)

Used for routine tasks requiring quick responses:

- Simple questions and lookups
- Document summarization
- Basic search queries
- General conversation

**Response time:** Typically under 2 seconds

### 🧠 Smart Mode (GPT-4o)

Automatically selected for complex tasks:

- Multi-step reasoning
- Code generation and analysis
- Legal or technical document analysis
- Comparisons across multiple documents
- Tasks requiring deep understanding

**Trigger keywords:** Questions containing "refactor", "architect", "optimize", "analyze in detail", or "compare and contrast" may trigger Smart Mode.

## Model Access by Plan

| Plan | Fast Mode | Smart Mode |
|------|-----------|------------|
| **Starter** | ✅ Always | ❌ Not available |
| **Pro** | ✅ Default | ✅ Auto-routed |
| **Enterprise** | ✅ Default | ✅ Auto-routed |

## Token Limits

Each plan includes monthly AI token allocations:

| Plan | Monthly Tokens | Approximate Queries |
|------|----------------|---------------------|
| **Starter** | 1 million | ~500-1,000 queries |
| **Pro** | 10 million | ~5,000-10,000 queries |
| **Enterprise** | 100 million | ~50,000-100,000 queries |

**What counts as tokens?**
- Your question text
- Retrieved document chunks
- AI response text
- System prompts

## Failover Protection

If the primary model is temporarily unavailable, Axio Hub automatically falls back to backup providers to ensure your queries always get answered.

## Tips for Best Results

1. **Be specific** — Clear questions get better answers
2. **Provide context** — "In the Q3 report, what was..." is better than "What was the revenue?"
3. **Use follow-ups** — The AI remembers conversation context
4. **Starter users:** Upgrade to Pro for complex analysis tasks
        `
    },
    {
        id: 'ghost-protocol',
        title: 'Ghost Protocol: Zero-Retention Security',
        category: 'AI Features',
        keywords: ['security', 'privacy', 'encryption', 'ghost', 'protocol', 'wipe', 'zero', 'retention'],
        content: `
# Ghost Protocol: Zero-Retention Security

Ghost Protocol is Axio Hub's military-grade security system that ensures your sensitive documents are protected with enterprise-level encryption and secure deletion.

## What is Ghost Protocol?

Ghost Protocol implements a **zero-retention architecture** where:

1. **Your content is encrypted at rest** using AES-256 encryption
2. **Temporary files are cryptographically wiped** after processing
3. **No plain text is stored** in the database
4. **Search indexes are decoupled** from original content

## How It Protects Your Data

### 1. Encryption at Rest (AES-256)

All document content stored in Axio Hub is encrypted using **AES-256 Fernet encryption** before being written to the database.

- Content is encrypted before storage
- Encryption keys are rotated automatically
- Only your account can decrypt your content

### 2. Secure File Processing

When you upload a document:

\`\`\`
Upload → Staging (Encrypted) → Process in RAM → Encrypt Chunks → Store → Wipe Staging
\`\`\`

At no point does your unencrypted content touch persistent storage.

### 3. Cryptographic Secure Wipe

Temporary files are **overwritten with random data** before deletion:

1. File contents overwritten with \`os.urandom()\` (cryptographic randomness)
2. Changes flushed to physical disk (\`fsync\`)
3. File unlinked (deleted)

**Why this matters:** Standard file deletion only removes the directory entry — data remains recoverable. Secure wipe makes forensic recovery impossible.

### 4. Emergency Cleanup (Dead Man's Switch)

If the system crashes or is forcefully terminated:

- Signal handlers intercept shutdown (SIGTERM, SIGINT)
- All tracked temporary files are emergency-wiped
- No sensitive data remains on disk

## DoD 5220.22-M Compliance (Enterprise)

Enterprise plans include **DoD 5220.22-M compliant** secure wipe:

- **3-pass overwrite** instead of single-pass
- Meets U.S. Department of Defense standards for media sanitization
- Required for defense contractors and regulated industries

## Search Without Exposing Content

Axio Hub uses **decoupled indexing** for search:

| What's Stored | Encrypted? | Purpose |
|---------------|------------|---------|
| Original content | ✅ Yes (AES-256) | Retrieved when you view documents |
| Search stems | ❌ No (word roots only) | Powers full-text search |
| Vector embeddings | ✅ Encrypted | Powers semantic search |

**How it works:** When you search for "financial report", we search against word stems like "financ" and "report" — not your actual content. This enables fast search while keeping your data encrypted.

## Verification

Ghost Protocol cannot be disabled in production:

- If encryption keys are missing, the application **refuses to start**
- This is a **fail-secure** design — security cannot be accidentally bypassed
- Configuration errors result in immediate, clear error messages

## What This Means For You

| Concern | How Ghost Protocol Helps |
|---------|-------------------------|
| "What if Axio Hub is breached?" | Your content is encrypted; attackers get ciphertext |
| "What about temp files?" | Cryptographically wiped, unrecoverable |
| "Can employees see my data?" | No — encryption keys are per-deployment |
| "Regulatory compliance?" | AES-256 + secure wipe meets most requirements |
| "Defense contractor requirements?" | Enterprise DoD mode available |

## Security Certifications

Ghost Protocol is designed to support compliance with:

- SOC 2 Type II requirements
- HIPAA technical safeguards
- GDPR data protection requirements
- DoD 5220.22-M (Enterprise tier)
        `
    },
    {
        id: 'hybrid-search',
        title: 'How Hybrid AI Search Works',
        category: 'AI Features',
        keywords: ['search', 'hybrid', 'semantic', 'keyword', 'find', 'query'],
        content: `
# Hybrid AI Search

Axio Hub uses a sophisticated hybrid search system that combines multiple search techniques for the most accurate results.

## Search Methods Combined

### 1. Keyword Search (Full-Text)

Traditional search that finds exact word matches:

- Finds documents containing your exact search terms
- Supports stemming ("running" matches "run")
- Fast and precise for specific terms

**Best for:** Finding documents with specific names, codes, or technical terms

### 2. Semantic Search (Vector)

AI-powered search that understands meaning:

- Finds conceptually similar content
- Understands synonyms automatically
- Works across languages

**Best for:** Finding documents about a topic, even if they use different words

### 3. Hybrid Ranking

Results are scored using both methods and combined:

\`\`\`
Final Score = (Keyword Relevance × 0.4) + (Semantic Relevance × 0.6)
\`\`\`

This ensures you get:
- Documents with exact matches (keyword)
- Documents about your topic (semantic)
- Ranked by overall relevance

## Search Tips

### Be Specific
❌ "Tell me about the project"
✅ "What is the timeline for Project Apollo phase 2?"

### Use Natural Language
You can ask questions naturally:
- "What were the key findings from the security audit?"
- "How does the authentication system work?"
- "Find all references to customer churn"

### Narrow by Source
Use the context selector to search within specific:
- Connected data sources (e.g., "only Google Drive")
- Projects or folders
- Date ranges (recent files)

## Understanding Results

Each search result includes:

| Element | Description |
|---------|-------------|
| **Title** | Document name |
| **Excerpt** | Relevant snippet with highlighted matches |
| **Source** | Where the document came from |
| **Relevance** | Match confidence score |

## Search Across All Your Data

Hybrid search works across all connected sources:

- Uploaded files
- Google Drive, OneDrive, Dropbox
- Notion pages and databases
- GitHub repositories
- Web pages you've crawled

All sources are searched simultaneously, with results ranked by relevance regardless of origin.
        `
    },
    {
        id: 'source-citations',
        title: 'Understanding Source Citations',
        category: 'AI Features',
        keywords: ['citation', 'source', 'reference', 'verify', 'accuracy'],
        content: `
# Source Citations

Every AI response in Axio Hub includes citations that link directly to the source documents. This ensures transparency and allows you to verify information.

## How Citations Work

When the AI answers your question, it includes numbered references:

\`\`\`
The Q3 revenue was $4.2 million, representing a 15% increase 
from Q2 [1]. This growth was primarily driven by the enterprise 
segment [2].

Sources:
[1] Q3-Financial-Report.pdf, page 12
[2] Board-Meeting-Notes-Sept.docx, section "Revenue Analysis"
\`\`\`

## Citation Information

Each citation includes:

| Field | Example | Description |
|-------|---------|-------------|
| **Document** | Q3-Report.pdf | Original file name |
| **Location** | page 12, section 3 | Where in the document |
| **Source** | Google Drive | Which data source |
| **Confidence** | High | How relevant the match |

## Verifying Information

1. **Click any citation** to open the source document
2. **View the highlighted passage** that the AI used
3. **Read surrounding context** for full understanding

## Why Citations Matter

### Accuracy
- Verify the AI interpreted the information correctly
- Catch any potential misunderstandings
- Trust but verify

### Audit Trail
- Know exactly where information came from
- Required for compliance in many industries
- Useful for research and legal work

### Learning
- Discover documents you may have forgotten
- Find related information in the same sources
- Build deeper understanding of your knowledge base

## No Hallucinations

Unlike general AI chatbots, Axio Hub:

- **Only answers from your documents** — never makes things up
- **Always provides citations** — every claim is backed by a source
- **Says "I don't know"** — when information isn't in your documents

If you ask about something not in your knowledge base, Axio Hub will tell you:

> "I couldn't find information about that topic in your connected documents. 
> Try uploading relevant files or connecting additional data sources."

## Best Practices

1. **Always check citations** for important decisions
2. **Follow up** if a citation seems unexpected
3. **Upload more sources** if answers are incomplete
4. **Use citations to explore** related documents
        `
    },

    // =========================================================================
    // CONNECTORS - Individual Guides
    // =========================================================================
    {
        id: 'connector-google-drive',
        title: 'Google Drive Connector',
        category: 'Connectors',
        keywords: ['google', 'drive', 'gdrive', 'connect', 'oauth'],
        content: `
# Google Drive Connector

Connect your Google Drive to automatically sync documents, spreadsheets, and files into Axio Hub.

## Setup Instructions

### Step 1: Initiate Connection
1. Go to **Settings → Data Sources**
2. Find **Google Drive** and click **Connect**
3. A Google sign-in window will open

### Step 2: Authorize Access
1. Sign in to your Google account
2. Review the permissions Axio Hub is requesting
3. Click **Allow** to grant access

**Permissions requested:**
- View and download files in your Google Drive
- View file metadata (names, dates, folders)

### Step 3: Select Folders
1. After authorization, you'll see your Drive folders
2. Click folders to expand them
3. Check the boxes next to folders you want to sync
4. Click **Save Selection**

## Supported File Types

All file types in the selected folders will be synced, but only supported formats are processed:

| Google Format | Converted To | Notes |
|---------------|--------------|-------|
| Google Docs | Text/Markdown | Full text extraction |
| Google Sheets | CSV data | All sheets included |
| Google Slides | Text | Slide-by-slide extraction |
| PDF, DOCX, etc. | Native format | Standard processing |

## Sync Behavior

- **Initial sync:** All files in selected folders are ingested
- **Incremental sync:** Only new/modified files are re-processed
- **Deleted files:** Removed from Axio Hub on next sync

## Rate Limits

Google Drive API has usage quotas:
- **600 requests per minute** (enforced by Axio Hub)
- Large syncs are automatically throttled
- You'll see progress indicators during sync

## Common Errors & Solutions

### "Google Drive connection expired. Please reconnect in Data Sources."

**Cause:** Your OAuth token has expired or been revoked.

**Solution:**
1. Go to **Settings → Data Sources**
2. Click **Disconnect** next to Google Drive
3. Click **Connect** to re-authorize

### "Access denied - insufficient permissions"

**Cause:** Axio Hub doesn't have permission to access the file.

**Solutions:**
- Ensure you own the file or have viewer access
- For shared drives, verify you have access to the specific folder
- Re-authorize with the correct Google account

### "Rate limit exceeded"

**Cause:** Too many requests in a short period.

**Solution:** Wait a few minutes and try again. Axio Hub automatically retries with backoff.

### Files Not Appearing

**Check:**
1. Is the file in a selected folder?
2. Is the file type supported?
3. Is the file size under 100 MB?
4. Has the sync completed? (Check progress indicator)

## Disconnecting

To remove Google Drive access:

1. Go to **Settings → Data Sources**
2. Click **Disconnect** next to Google Drive
3. Confirm the disconnection

**Note:** This removes synced files from Axio Hub. To also revoke Axio Hub's access to your Google account, visit [Google Security Settings](https://myaccount.google.com/permissions).

## Best Practices

- **Organize first:** Create a folder structure before syncing
- **Be selective:** Don't sync your entire Drive — choose relevant folders
- **Use Shared Drives:** For team access, sync from Shared Drives where all team members have access
        `
    },
    {
        id: 'connector-onedrive',
        title: 'OneDrive Connector',
        category: 'Connectors',
        keywords: ['onedrive', 'microsoft', 'office', '365', 'connect'],
        content: `
# OneDrive Connector

Connect your Microsoft OneDrive to sync documents and files into Axio Hub.

## Setup Instructions

### Step 1: Initiate Connection
1. Go to **Settings → Data Sources**
2. Find **OneDrive** and click **Connect**
3. A Microsoft sign-in window will open

### Step 2: Authorize Access
1. Sign in with your Microsoft account (personal or work/school)
2. Review the permissions
3. Click **Accept** to grant access

**Permissions requested:**
- Read files in your OneDrive
- Read your profile (for account identification)

### Step 3: Select Folders
1. Browse your OneDrive folder structure
2. Check folders to include in sync
3. Click **Save Selection**

## Supported File Types

| Format | Support | Notes |
|--------|---------|-------|
| Word (.docx) | ✅ Full | Text and formatting extracted |
| Excel (.xlsx) | ✅ Full | All sheets processed |
| PowerPoint (.pptx) | ✅ Full | Slide-by-slide extraction |
| PDF | ✅ Full | OCR for scanned pages |
| OneNote | ❌ Limited | Export to PDF first |

## Work vs. Personal Accounts

### Personal OneDrive
- Uses your Microsoft account (outlook.com, hotmail.com)
- Connect directly with OAuth

### OneDrive for Business
- Uses your work/school account
- May require admin approval in your organization
- Contact your IT admin if connection fails

## Common Errors & Solutions

### "OneDrive connection expired. Please reconnect in Data Sources."

**Cause:** Microsoft token expired (typically after 90 days of inactivity).

**Solution:**
1. Go to **Settings → Data Sources**
2. Disconnect and reconnect OneDrive

### "Microsoft integration requires reconnection"

**Cause:** Token refresh failed or was revoked.

**Solution:** Reconnect your OneDrive account.

### "Access denied to file"

**Cause:** File permissions changed or file was moved.

**Solutions:**
- Verify you still have access to the file in OneDrive
- Check if the file was moved to a non-synced folder
- For shared files, confirm share permissions are still active

### Admin Blocked Connection (Work Accounts)

**Error:** "Need admin approval" or "App not approved"

**Solution:** Contact your IT administrator to approve Axio Hub in Azure AD / Entra ID.

## Rate Limits

- **120 requests per minute** (Microsoft Graph API limit)
- Large syncs are automatically paced
- Progress indicators show sync status

## Disconnecting

1. Go to **Settings → Data Sources**
2. Click **Disconnect** next to OneDrive
3. To revoke app access: Visit [Microsoft Account Apps](https://account.live.com/consent/Manage)
        `
    },
    {
        id: 'connector-sharepoint',
        title: 'SharePoint Connector',
        category: 'Connectors',
        keywords: ['sharepoint', 'microsoft', 'teams', 'enterprise', 'connect'],
        content: `
# SharePoint Connector

Connect to SharePoint sites and document libraries to sync corporate documents into Axio Hub.

## Prerequisites

- SharePoint Online (Microsoft 365)
- Appropriate permissions to the SharePoint site
- Organization may require admin approval

## Setup Instructions

### Step 1: Initiate Connection
1. Go to **Settings → Data Sources**
2. Find **SharePoint** and click **Connect**
3. Sign in with your work/school Microsoft account

### Step 2: Authorize Access
1. Review the requested permissions
2. Click **Accept**
3. If prompted for admin consent, contact your IT department

### Step 3: Select Sites & Libraries
1. You'll see SharePoint sites you have access to
2. Expand sites to see document libraries
3. Select specific libraries or folders to sync
4. Click **Save Selection**

## What Can Be Synced

| Content Type | Supported | Notes |
|--------------|-----------|-------|
| Document Libraries | ✅ Yes | Files in libraries |
| Folders | ✅ Yes | Any folder structure |
| List Attachments | ❌ No | Files attached to list items |
| SharePoint Pages | ❌ No | Site pages themselves |

## Permissions Required

For the connector to work, you need:

1. **Read access** to the SharePoint site
2. **Files.Read.All** scope in Microsoft Graph
3. Organization admin may need to approve the app

### Getting Admin Approval

If your organization requires admin consent:

1. Send this request to your IT admin
2. They can approve in Azure AD → Enterprise Applications
3. Once approved, try connecting again

## Common Errors & Solutions

### "SharePoint connection expired. Please reconnect in Data Sources."

**Cause:** Microsoft token expired.

**Solution:** Disconnect and reconnect the SharePoint connector.

### "Access denied - insufficient permissions"

**Causes:**
- Your SharePoint permissions were changed
- Site permissions restrict external apps
- Document library has unique permissions

**Solutions:**
- Verify your access directly in SharePoint
- Contact your SharePoint admin
- Try a different document library

### "Site not found"

**Cause:** Site was deleted, renamed, or you lost access.

**Solution:** Verify the site exists in SharePoint, then reconnect.

### Sync Takes a Long Time

**For large document libraries:**
- Initial sync processes all files — this is expected
- Subsequent syncs only check for changes
- Progress is shown in the UI

## Microsoft Teams Files

Files shared in Microsoft Teams are stored in SharePoint:

1. Each Team has a SharePoint site
2. Each Channel has a folder in the document library
3. Connect the Team's SharePoint site to sync Teams files

**Finding your Team's SharePoint site:**
1. In Teams, open a channel
2. Click **Files** tab
3. Click **Open in SharePoint**
4. Use this site URL when connecting

## Best Practices

- **Start small:** Connect one library first to test
- **Avoid root sites:** Don't sync entire tenant — select specific libraries
- **Check permissions first:** Ensure you have access before troubleshooting
        `
    },
    {
        id: 'connector-dropbox',
        title: 'Dropbox Connector',
        category: 'Connectors',
        keywords: ['dropbox', 'connect', 'cloud', 'storage'],
        content: `
# Dropbox Connector

Connect your Dropbox account to sync files and folders into Axio Hub.

## Setup Instructions

### Step 1: Initiate Connection
1. Go to **Settings → Data Sources**
2. Find **Dropbox** and click **Connect**
3. A Dropbox sign-in window will open

### Step 2: Authorize Access
1. Sign in to your Dropbox account
2. Review the permissions
3. Click **Allow** to grant access

### Step 3: Select Folders
1. Browse your Dropbox folder structure
2. Check folders to sync
3. Click **Save Selection**

## Dropbox Plans

### Dropbox Basic/Plus (Personal)
- Full support
- Connect directly with OAuth

### Dropbox Business
- Full support
- Team folders accessible
- Admin may need to approve third-party apps

### Dropbox Team Spaces
- ✅ Supported
- You can sync from team spaces you have access to

## Common Errors & Solutions

### "Dropbox connection expired. Please reconnect in Data Sources."

**Cause:** OAuth token expired or was revoked.

**Solution:**
1. Go to **Settings → Data Sources**
2. Disconnect Dropbox
3. Reconnect and re-authorize

### "Dropbox rate limit exceeded after retries"

**Cause:** Too many API requests in a short period.

**Solution:** Wait 1-2 minutes and try again. Axio Hub respects Dropbox's Retry-After headers.

### "Dropbox auth failed"

**Causes:**
- Entered wrong credentials
- Account locked or suspended
- App authorization was revoked

**Solutions:**
- Verify you can log into dropbox.com
- Check [Dropbox Security Settings](https://www.dropbox.com/account/connected_apps) for app access
- Reconnect the integration

### Files Not Syncing

**Check:**
1. Is the folder selected for sync?
2. Is the file in a subfolder of the selected folder?
3. Is the file type supported?
4. For Business accounts: Is the file in your accessible space?

## Rate Limits

- **720 requests per minute** (Dropbox allows ~12/second)
- Axio Hub automatically throttles to stay within limits
- Large syncs show progress indicators

## Shared Folders

- Files in shared folders you've added to your Dropbox are synced
- You must have **viewer** or higher permissions
- Changes by others are captured in incremental syncs

## Disconnecting

1. Go to **Settings → Data Sources**
2. Click **Disconnect** next to Dropbox
3. To fully revoke access: [Dropbox Connected Apps](https://www.dropbox.com/account/connected_apps)
        `
    },
    {
        id: 'connector-notion',
        title: 'Notion Connector',
        category: 'Connectors',
        keywords: ['notion', 'connect', 'wiki', 'database', 'pages'],
        content: `
# Notion Connector

Connect your Notion workspace to sync pages, databases, and wikis into Axio Hub.

## Setup Instructions

### Step 1: Initiate Connection
1. Go to **Settings → Data Sources**
2. Find **Notion** and click **Connect**
3. A Notion authorization window will open

### Step 2: Authorize & Select Pages
1. Sign in to Notion
2. **Important:** Select which pages/databases Axio Hub can access
3. You can select individual pages or entire parent pages
4. Click **Allow access**

### Step 3: Verify Access
1. Return to Axio Hub
2. You should see your selected pages
3. Click **Sync** to begin ingestion

## Understanding Notion Permissions

Notion has a unique permission model:

| Selection in Authorization | What Axio Hub Can Access |
|---------------------------|-------------------------|
| Specific pages | Only those pages and their children |
| All pages | Every page in your workspace |
| Databases | The database and all its entries |

**Recommendation:** Select only the pages/databases you want to search. You can always reconnect to grant access to more pages.

## What Gets Synced

| Content Type | Synced | Notes |
|--------------|--------|-------|
| Pages | ✅ Yes | Full text content |
| Databases | ✅ Yes | All entries as individual items |
| Inline databases | ✅ Yes | Part of parent page |
| Comments | ❌ No | Only page content |
| Files/Attachments | ❌ No | Embedded file content not extracted |

### Page Content Extraction

Notion pages are converted to Markdown-like text:
- Headings preserved as structure
- Lists and checkboxes included
- Code blocks retained
- Tables converted to text
- Images referenced (not OCR'd)

## Common Errors & Solutions

### "Notion connection expired. Please reconnect in Data Sources."

**Cause:** Notion token expired or permissions changed.

**Solution:**
1. Go to **Settings → Data Sources**
2. Disconnect Notion
3. Reconnect and select pages again

### "Integration requires reconnection"

**Cause:** The Notion integration was removed from your workspace.

**Solution:**
1. Go to **Settings & Members** in Notion
2. Check **Connections** or **Integrations**
3. Ensure Axio Hub is listed
4. If not, reconnect from Axio Hub

### Pages Not Appearing

**Common causes:**
1. **Not selected during authorization:** Reconnect and select the pages
2. **Page is private:** Share it with the integration
3. **Page is in a different workspace:** Connect that workspace separately

### Rate Limit Errors

**Cause:** Notion has strict rate limits (3 requests/second).

**Solution:** Axio Hub automatically handles this with retries and backoff. Large workspaces may take longer to sync initially.

## Adding More Pages Later

To grant access to additional pages:

1. In Notion, go to the page you want to add
2. Click **•••** (more) menu → **Connections**
3. Add **Axio Hub** to the page
4. The page will appear in your next sync

Or reconnect the integration to re-select pages.

## Notion Databases

Databases are synced with each row as a separate document:

\`\`\`
Database: Project Tasks
├── Task 1 (as document)
├── Task 2 (as document)
└── Task 3 (as document)
\`\`\`

Properties are included in each document's metadata for searchability.

## Disconnecting

1. Go to **Settings → Data Sources** in Axio Hub
2. Click **Disconnect** next to Notion
3. In Notion: **Settings → Connections** → Remove Axio Hub
        `
    },
    {
        id: 'connector-github',
        title: 'GitHub Connector',
        category: 'Connectors',
        keywords: ['github', 'code', 'repository', 'git', 'source'],
        content: `
# GitHub Connector

Connect your GitHub repositories to search and chat with your codebase.

## Setup Instructions

### Step 1: Initiate Connection
1. Go to **Settings → Data Sources**
2. Find **GitHub** and click **Connect**
3. A GitHub authorization window will open

### Step 2: Authorize Access
1. Sign in to GitHub
2. Review the permissions requested
3. Click **Authorize** to grant access

**Permissions requested:**
- Read access to code and metadata
- Read access to your repositories list

### Step 3: Select Repositories
1. You'll see a list of your repositories
2. Check repositories you want to sync
3. Click **Save Selection**

**Note:** Axio Hub does NOT auto-sync all your repositories. You explicitly select which ones to include.

## What Gets Synced

### Included (Automatically)

| Content | Example Extensions |
|---------|-------------------|
| Source code | .py, .js, .ts, .go, .rs, .java, etc. |
| Documentation | .md, .rst, .txt, README |
| Configuration | package.json, Dockerfile, .yml |
| Scripts | .sh, Makefile |

### Excluded (Automatically)

To keep your knowledge base clean, these are filtered out:

| Category | Examples |
|----------|----------|
| Dependencies | node_modules/, vendor/, venv/ |
| Build artifacts | dist/, build/, target/ |
| Cache | __pycache__/, .cache/ |
| IDE settings | .idea/, .vscode/ |
| Git internals | .git/ |
| Binaries | .exe, .dll, .so, images |
| Lock files | package-lock.json, yarn.lock |

### File Size Limit

Files over **1 MB** are skipped to avoid ingesting minified bundles or data files.

## Repository Types

### Public Repositories
- Always accessible
- No special permissions needed

### Private Repositories
- Requires authorization
- You must have at least read access

### Organization Repositories
- You'll see repos you have access to
- Organization admins can restrict third-party app access

## Common Errors & Solutions

### "GitHub connection expired. Please reconnect your GitHub account in Data Sources."

**Cause:** GitHub token expired or was revoked.

**Solution:**
1. Go to **Settings → Data Sources**
2. Disconnect GitHub
3. Reconnect and re-authorize

### "GitHub token has been revoked or is invalid"

**Cause:** You revoked access in GitHub settings.

**Solution:**
1. Reconnect the integration
2. Check [GitHub Applications](https://github.com/settings/applications) for Axio Hub

### "GitHub token lacks required permissions"

**Cause:** Scope was not granted during authorization.

**Solution:** Disconnect and reconnect, ensuring you approve all requested permissions.

### "Access denied to repository"

**Causes:**
- Repository was made private
- Your access was removed
- Organization restricted third-party apps

**Solutions:**
- Verify access at github.com
- For org repos, contact your organization admin

### Repository Not Appearing

**Check:**
1. Did you authorize access to that repository/organization?
2. Is it selected in the repository picker?
3. For organization repos: Is third-party access enabled?

## Rate Limits

- **80 requests per minute** (GitHub allows 5000/hour)
- Rate limit status is tracked in API responses
- Axio Hub automatically pauses when approaching limits

## Large Repositories

For very large codebases (10,000+ files):
- Initial sync may take several minutes
- Only code/doc files are processed (see filters above)
- Progress is shown in the UI

## Organization Settings

If your organization restricts third-party app access:

1. Organization admin must approve Axio Hub
2. In GitHub: **Organization Settings → Third-party Access**
3. Request or approve Axio Hub as an authorized OAuth app

## Best Practices

- **Be selective:** Don't sync every repository — focus on what you need to search
- **Active repos first:** Sync repositories you're actively working on
- **Documentation repos:** Great candidates for syncing — product docs, wikis, runbooks
        `
    },
    {
        id: 'connector-box',
        title: 'Box Connector',
        category: 'Connectors',
        keywords: ['box', 'enterprise', 'cloud', 'storage', 'connect'],
        content: `
# Box Connector

Connect your Box account to sync enterprise documents into Axio Hub.

## Setup Instructions

### Step 1: Initiate Connection
1. Go to **Settings → Data Sources**
2. Find **Box** and click **Connect**
3. A Box sign-in window will open

### Step 2: Authorize Access
1. Sign in to Box
2. Review the permissions
3. Click **Grant access to Box**

### Step 3: Select Folders
1. Browse your Box folder structure
2. Check folders to sync
3. Click **Save Selection**

## Box Account Types

### Box Personal
- Full support
- Connect directly

### Box Business/Enterprise
- Full support
- Admin may need to approve third-party apps
- Custom apps may require additional setup

## Common Errors & Solutions

### "Box connection expired. Please reconnect your Box account in Data Sources."

**Cause:** OAuth token expired.

**Solution:** Disconnect and reconnect the Box integration.

### "Box integration requires reconnection"

**Cause:** Refresh token expired or was revoked.

**Note:** Box refresh tokens expire after 60 days of inactivity.

**Solution:**
1. Disconnect Box in Axio Hub
2. Reconnect and re-authorize

### "Box refresh token has expired or been revoked. Please reconnect your Box account."

**Cause:** Extended inactivity or manual revocation.

**Solution:** Reconnect the integration.

### "Box token invalid or expired"

**Cause:** Token became invalid between requests.

**Solution:** Reconnect the integration.

### "Box access denied - insufficient permissions"

**Cause:** File or folder permissions changed.

**Solutions:**
- Verify your access in Box web interface
- Check if folder was moved or permissions modified
- Contact folder owner for access

### "Box item not found"

**Cause:** File or folder was deleted or moved.

**Solution:** No action needed — Axio Hub will remove it from search results on next sync.

## Rate Limits

- **600 requests per minute** (Business accounts allow 1000/min)
- Axio Hub conservatively throttles to avoid limits
- Retry-After headers are respected

## Enterprise App Approval

For Box Enterprise accounts with app restrictions:

1. Admin must approve Axio Hub in **Box Admin Console**
2. Go to **Apps → Custom Apps**
3. Search for and authorize Axio Hub

Contact your Box administrator if you see approval-related errors.

## Collaborations & Shared Folders

- Files in folders shared with you are accessible
- Collaboration folders appear in your folder list
- External collaborations depend on your enterprise settings
        `
    },
    {
        id: 'connector-s3',
        title: 'Amazon S3 Connector (Enterprise)',
        category: 'Connectors',
        keywords: ['s3', 'aws', 'amazon', 'bucket', 'enterprise', 'cloud'],
        content: `
# Amazon S3 Connector

Connect your AWS S3 buckets to sync documents stored in cloud object storage.

> **⚠️ Enterprise Only:** The S3 connector is exclusively available on Enterprise plans.

## Prerequisites

Before connecting, you'll need:

1. **AWS Account** with an S3 bucket
2. **IAM credentials** (Access Key ID + Secret Access Key)
3. **Appropriate permissions** on the bucket

## Setup Instructions

### Step 1: Create IAM User & Policy

Create an IAM user with minimal required permissions:

\`\`\`json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AxioS3ReadAccess",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:ListBucket",
                "s3:HeadObject",
                "s3:HeadBucket"
            ],
            "Resource": [
                "arn:aws:s3:::YOUR_BUCKET_NAME",
                "arn:aws:s3:::YOUR_BUCKET_NAME/*"
            ]
        }
    ]
}
\`\`\`

Replace \`YOUR_BUCKET_NAME\` with your actual bucket name.

### Step 2: Generate Access Keys

1. In AWS IAM Console, go to your user
2. **Security credentials** tab
3. **Create access key**
4. Select **Third-party service**
5. Save the Access Key ID and Secret Access Key

### Step 3: Connect in Axio Hub

1. Go to **Settings → Data Sources**
2. Find **Amazon S3** and click **Connect**
3. Enter your credentials:
   - **Access Key ID:** Your AWS access key
   - **Secret Access Key:** Your AWS secret key
   - **Region:** e.g., us-east-1, eu-west-1
   - **Bucket Name:** Your S3 bucket name
   - **Prefix (optional):** Folder path like \`documents/\`

4. Click **Connect**

## Supported Storage Classes

| Storage Class | Supported | Notes |
|---------------|-----------|-------|
| Standard | ✅ Yes | Full support |
| Standard-IA | ✅ Yes | Full support |
| Intelligent-Tiering | ✅ Yes | Full support |
| Glacier Instant Retrieval | ✅ Yes | Full support |
| Glacier Flexible | ❌ No | Must restore first |
| Glacier Deep Archive | ❌ No | Must restore first |

**Archived objects** (Glacier Flexible/Deep Archive) are automatically skipped. Restore them to Standard first if needed.

## Common Errors & Solutions

### "S3 access denied"

**Causes:**
- IAM policy doesn't include required actions
- Policy doesn't cover the bucket/prefix
- Bucket policy denies access

**Solutions:**
1. Verify IAM policy includes: s3:GetObject, s3:ListBucket, s3:HeadObject, s3:HeadBucket
2. Check Resource ARN matches your bucket name exactly
3. Check for conflicting bucket policies

### "S3 authentication failed"

**Causes:**
- Invalid Access Key ID
- Invalid Secret Access Key
- Keys were rotated or deleted

**Solutions:**
- Verify keys in AWS IAM Console
- Generate new access keys if needed
- Ensure you're using the correct AWS account

### "S3 bucket not found"

**Causes:**
- Bucket name typo
- Bucket in different region
- Bucket was deleted

**Solutions:**
- Verify bucket name exactly (case-sensitive)
- Confirm the region setting
- Check bucket exists in AWS Console

### "S3 object not accessible (archived)"

**Cause:** File is in Glacier storage class.

**Solution:** Restore the object to a retrieval tier in AWS Console, then re-sync.

### "S3 rate limit"

**Cause:** Extremely rare — S3 has very high limits.

**Solution:** Axio Hub auto-retries. If persistent, check for other applications hitting the same bucket.

## Security Best Practices

1. **Use minimal permissions:** Only grant read access
2. **Scope to specific bucket:** Don't use s3:* on all resources
3. **Rotate keys regularly:** Update in Axio Hub after rotation
4. **Use IAM users, not root:** Never use AWS root account keys
5. **Consider VPC endpoints:** For private network access (Enterprise)

## Prefix Filtering

Use the **Prefix** field to sync only a portion of your bucket:

| Prefix | What's Synced |
|--------|---------------|
| (empty) | Entire bucket |
| \`documents/\` | Only documents/ folder |
| \`projects/2024/\` | Only 2024 subfolder |

**Tip:** Use prefixes to avoid syncing logs, backups, or other non-document content.
        `
    },
    {
        id: 'connector-sftp',
        title: 'SFTP Connector',
        category: 'Connectors',
        keywords: ['sftp', 'ssh', 'ftp', 'server', 'file', 'transfer'],
        content: `
# SFTP Connector

Connect to SFTP servers to sync files from your on-premises or private file servers.

## Prerequisites

You'll need:
- SFTP server hostname or IP address
- Username with read access
- Authentication: Password OR SSH private key

## Setup Instructions

### Step 1: Gather Connection Details

From your SFTP server administrator, obtain:
- **Host:** server.example.com or IP address
- **Port:** Usually 22 (default SFTP port)
- **Username:** Your SFTP username
- **Authentication:** Password or private key

### Step 2: Connect in Axio Hub

1. Go to **Settings → Data Sources**
2. Find **SFTP** and click **Connect**
3. Enter connection details:
   - **Host:** Your server address
   - **Port:** 22 (or custom port)
   - **Username:** Your username
   - **Password:** (if using password auth)
   - **Private Key:** (if using key auth, paste PEM content)
   - **Root Path:** Starting directory (e.g., /data/documents)

4. Click **Test Connection**
5. If successful, click **Save**

## Authentication Methods

### Password Authentication
- Enter password directly
- Simple but less secure

### SSH Key Authentication (Recommended)
- Generate an SSH key pair
- Add public key to SFTP server's authorized_keys
- Paste private key (PEM format) in Axio Hub

**Generating an SSH key:**
\`\`\`bash
ssh-keygen -t rsa -b 4096 -f axio_sftp_key
# Add axio_sftp_key.pub to server's authorized_keys
# Paste contents of axio_sftp_key (private) in Axio Hub
\`\`\`

## Security Features

### SSRF Protection

Axio Hub prevents connections to:
- Private IP ranges (10.x.x.x, 192.168.x.x, etc.)
- Localhost (127.0.0.1)
- Internal network addresses

This protects against Server-Side Request Forgery attacks.

**If you need to connect to internal servers:** Contact Axio Hub support for Enterprise network configurations.

### Connection Timeouts

- **Connection timeout:** 30 seconds
- **Keepalive:** 30 seconds
- Automatic retry on transient failures

## Common Errors & Solutions

### "SFTP credentials missing"

**Cause:** Required fields not provided.

**Solution:** Ensure host, username, and either password or private key are provided.

### "Invalid SFTP configuration"

**Causes:**
- Port is not a valid number
- Root path is not a string
- Neither password nor private key provided

**Solution:** Check all fields are correctly filled.

### "Connection refused"

**Causes:**
- Server is down or unreachable
- Wrong port number
- Firewall blocking connection

**Solutions:**
- Verify server is running and accessible
- Confirm port number with your admin
- Check firewall rules allow connection from Axio Hub

### "Authentication failed"

**Causes:**
- Wrong username
- Wrong password
- Private key doesn't match authorized_keys
- Key format incorrect

**Solutions:**
- Verify credentials with a direct SFTP client first
- For keys: ensure PEM format, no passphrase, matches server config

### "Permission denied"

**Cause:** User doesn't have read access to the directory/file.

**Solution:** Contact your server admin to grant read permissions.

### "Security Violation: Access to private network denied"

**Cause:** Attempting to connect to an internal IP address.

**Solution:** SFTP connector requires public endpoints for security. Contact support for Enterprise network options.

## File Permissions

The SFTP user needs:
- **Read (r)** permission on files to sync
- **Execute (x)** permission on directories to list contents

## Best Practices

1. **Use key authentication:** More secure than passwords
2. **Create a dedicated user:** Don't use personal accounts
3. **Set root path:** Limit to specific directory, not /
4. **Regular key rotation:** Rotate SSH keys periodically
        `
    },
    {
        id: 'connector-web-crawler',
        title: 'Web Crawler',
        category: 'Connectors',
        keywords: ['web', 'crawler', 'website', 'url', 'crawl', 'scrape'],
        content: `
# Web Crawler

Import content from websites, documentation sites, and web pages into your knowledge base.

## How It Works

The web crawler:
1. Fetches the HTML content of a URL
2. Extracts readable text (removes navigation, ads, scripts)
3. Optionally follows links to crawl multiple pages
4. Creates searchable documents from each page

## Setup Instructions

### Crawl a Single Page

1. Go to **Knowledge Base**
2. Click **Add Source → Web Crawler**
3. Enter the URL (e.g., \`https://docs.example.com/guide\`)
4. Select **Single Page**
5. Click **Start Crawl**

### Crawl Multiple Pages

1. Enter the starting URL
2. Select crawl mode:
   - **Follow links:** Crawl pages linked from the start page
   - **Use sitemap:** Parse sitemap.xml for all URLs
3. Set **Max Pages** (up to 100)
4. Click **Start Crawl**

## Crawl Modes

### Single Page
- Crawls only the exact URL provided
- Best for: Individual articles, specific documentation pages

### Follow Links
- Starts at URL, follows links on the same domain
- Depth limit prevents infinite crawling
- Best for: Documentation sites, wikis, blog archives

### Sitemap
- Parses sitemap.xml to discover all pages
- Most comprehensive coverage
- Best for: Large sites with well-maintained sitemaps

**To use sitemap:** Enter the sitemap URL directly (e.g., \`https://example.com/sitemap.xml\`)

## What Gets Extracted

| Content | Included | Notes |
|---------|----------|-------|
| Article text | ✅ Yes | Main content extracted |
| Headings | ✅ Yes | Structure preserved |
| Lists | ✅ Yes | Bulleted and numbered |
| Tables | ✅ Yes | Converted to text |
| Code blocks | ✅ Yes | Preserved with formatting |
| Images | ❌ No | Alt text only |
| Videos | ❌ No | Not extracted |
| Navigation | ❌ No | Filtered out |
| Ads/sidebars | ❌ No | Filtered out |

## YouTube Support

The web crawler can extract YouTube transcripts:

1. Enter a YouTube video URL
2. Axio Hub fetches the auto-generated or manual transcript
3. The transcript becomes a searchable document

**Supported YouTube URLs:**
- \`https://www.youtube.com/watch?v=VIDEO_ID\`
- \`https://youtu.be/VIDEO_ID\`

## Common Errors & Solutions

### "Security Violation: Access to private network denied"

**Cause:** URL points to a private IP address or localhost.

**Solution:** Web crawler only works with public URLs for security.

### "Unsafe URL blocked"

**Cause:** URL failed security validation.

**Solutions:**
- Ensure URL uses http:// or https://
- URL must be publicly accessible
- Check for typos in the URL

### "Failed to fetch content"

**Causes:**
- Website is down
- Page requires authentication
- Website blocks crawlers

**Solutions:**
- Verify the page loads in your browser
- Check if login is required (not supported)
- Site may block automated access

### "Content type not allowed"

**Cause:** URL returns non-HTML content (PDF, image, etc.).

**Solution:** For files, use direct upload or file connectors instead.

## Limitations

| Limit | Value |
|-------|-------|
| Max pages per crawl | 100 |
| Max HTML size | 2 MB per page |
| Authentication | Not supported |
| JavaScript rendering | Not supported (static HTML only) |

### JavaScript-Heavy Sites

Sites that load content via JavaScript (SPAs) may not crawl well:
- React, Vue, Angular apps may show minimal content
- Look for static/server-rendered versions
- Documentation sites usually work well

## Robots.txt Compliance

Axio Hub respects robots.txt:
- If robots.txt disallows crawling, the request will fail
- User-agent: AxioBot/1.0
- Be respectful of website owners' preferences

## Rate Limiting

- **120 requests per minute** to any single domain
- Automatic delays between requests
- Progress shown in UI during crawl

## Best Practices

1. **Start with sitemap:** Most reliable for complete coverage
2. **Test single page first:** Verify content extracts well
3. **Be selective:** Don't crawl entire massive sites
4. **Check robots.txt:** Ensure the site allows crawling
5. **Documentation sites work best:** Designed for reading, well-structured
        `
    },
    {
        id: 'connector-file-upload',
        title: 'Direct File Upload',
        category: 'Connectors',
        keywords: ['upload', 'file', 'drag', 'drop', 'local'],
        content: `
# Direct File Upload

Upload files directly from your computer to Axio Hub.

## How to Upload

### Method 1: Drag and Drop
1. Go to **Knowledge Base**
2. Drag files from your computer to the upload area
3. Wait for processing to complete

### Method 2: File Picker
1. Go to **Knowledge Base**
2. Click **Upload**
3. Select files from your computer
4. Click **Open**

### Method 3: Bulk Upload
1. Select multiple files at once
2. Or drag an entire folder
3. All supported files will be processed

## Upload Limits

| Limit | Value |
|-------|-------|
| Per-file size | 100 MB |
| Files per upload | No limit |
| Total storage | Depends on plan |

### Storage by Plan

| Plan | Total Storage |
|------|---------------|
| Starter | 100 MB |
| Pro | 10 GB |
| Enterprise | 1 TB |

## Processing Pipeline

When you upload a file:

1. **Upload** — File transferred to secure staging
2. **Scan** — Malware scan (if enabled)
3. **Parse** — Text extraction based on file type
4. **Chunk** — Split into searchable segments
5. **Embed** — Generate AI vectors for semantic search
6. **Encrypt** — Store with Ghost Protocol encryption
7. **Cleanup** — Staging file securely wiped

You'll see a progress indicator during processing.

## Supported Formats

See [Supported File Formats](#supported-file-formats) for the complete list.

**Quick reference:**
- ✅ PDF, DOCX, XLSX, PPTX, TXT, MD, HTML, CSV, EML
- ✅ Code files (60+ languages)
- ✅ Images (OCR extraction)
- ❌ Videos, audio, archives, binaries

## Common Issues

### "File exceeds 100MB limit"

**Solution:** Reduce file size or split into smaller files.

For PDFs: Use a PDF splitter tool.
For spreadsheets: Export as multiple sheets/files.

### Upload Stalls or Fails

**Causes:**
- Network interruption
- Browser timeout
- File too large

**Solutions:**
- Check your internet connection
- Try a smaller file first
- Use a modern browser (Chrome, Firefox, Edge)

### "Unsupported file type"

**Cause:** File format not recognized or not supported.

**Solution:** Convert to a supported format:
- Presentations → PPTX or PDF
- Documents → DOCX or PDF
- Data → CSV or XLSX

### Processing Takes Long Time

**Normal for:**
- Large PDFs (especially scanned)
- Files requiring OCR
- Multiple files uploaded at once

**If stuck:**
- Check the ingestion jobs in Settings
- Cancel and retry if truly stuck
- Large OCR files may take 2-5 minutes

## Organizing Uploads

All uploads from your account are grouped under a single "Manual Uploads" source.

**Tips for organization:**
- Use descriptive file names
- Consider folder structure before uploading
- For better organization, use cloud connectors (Google Drive, etc.)

## Re-uploading Files

If you upload a file with the same name:
- A new version is created
- Both versions are searchable
- Delete the old version manually if desired
        `
    },

    // =========================================================================
    // TEAMS
    // =========================================================================
    {
        id: 'team-roles',
        title: 'Team Roles & Permissions',
        category: 'Teams',
        keywords: ['team', 'role', 'permission', 'admin', 'editor', 'viewer', 'access'],
        content: `
# Team Roles & Permissions

When you invite members to your team, you assign them roles that determine what they can do.

## Available Roles

| Permission | Admin | Editor | Viewer |
|------------|-------|--------|--------|
| Chat & Search | ✅ | ✅ | ✅ |
| View all documents | ✅ | ✅ | ✅ |
| Upload files | ✅ | ✅ | ❌ |
| Connect data sources | ✅ | ✅ | ❌ |
| Web crawling | ✅ | ✅ | ❌ |
| Invite team members | ✅ | ❌ | ❌ |
| Remove team members | ✅ | ❌ | ❌ |
| Change member roles | ✅ | ❌ | ❌ |
| Manage billing | ✅ | ❌ | ❌ |
| Delete organization | ✅ | ❌ | ❌ |

## Role Descriptions

### Admin
Full control over the team and organization.

**Best for:**
- Organization owners
- IT administrators
- Department heads

**Can do everything** including billing, member management, and data source configuration.

### Editor
Can contribute content but cannot manage the team.

**Best for:**
- Knowledge contributors
- Senior team members
- Content managers

**Can:** Upload files, connect sources, use all search features
**Cannot:** Invite/remove members, access billing

### Viewer
Read-only access to search and chat.

**Best for:**
- Field staff
- Consultants with temporary access
- Team members who only consume information

**Can:** Search, chat, view documents
**Cannot:** Upload, connect sources, manage anything

## Changing Roles

1. Go to **Settings → Team Management**
2. Find the team member
3. Click the role dropdown
4. Select the new role
5. Changes take effect immediately

**Note:** Only Admins can change roles.

## Team Size Limits

| Plan | Maximum Team Members |
|------|---------------------|
| Starter | 1 (no team features) |
| Pro | 5 |
| Enterprise | 100 |

## Inherited Plans

Team members inherit the team owner's plan:
- If owner has Pro, all members get Pro features
- Members don't need individual subscriptions
- Token usage is shared across the team
        `
    },
    {
        id: 'bulk-import',
        title: 'Bulk Invite Team Members via CSV',
        category: 'Teams',
        keywords: ['bulk', 'csv', 'import', 'invite', 'team', 'mass'],
        content: `
# Bulk Import Team Members

Invite your entire team at once using a CSV file.

## CSV Format

Your file must have exactly two columns: \`email\` and \`role\`.

\`\`\`csv
email,role
john.doe@company.com,editor
jane.smith@company.com,viewer
mike.wilson@company.com,admin
field.team01@company.com,viewer
\`\`\`

## Step-by-Step Instructions

### Step 1: Prepare Your CSV

1. Open a spreadsheet application (Excel, Google Sheets)
2. Create two columns: \`email\` and \`role\`
3. Enter team members (one per row)
4. Save as CSV file

### Step 2: Upload the CSV

1. Go to **Settings → Team Management**
2. Click **Bulk Import**
3. Download the template CSV (optional)
4. Upload your prepared CSV
5. Review the preview
6. Click **Confirm Import**

## Role Values

Roles must be lowercase:

| Value | Role |
|-------|------|
| \`admin\` | Admin |
| \`editor\` | Editor |
| \`viewer\` | Viewer |

## Rules & Limits

| Rule | Limit |
|------|-------|
| Max rows per upload | 500 |
| File format | CSV only |
| Header row | Required (\`email,role\`) |

## What Happens After Import

1. **Invitations sent** — Each email receives an invite
2. **Duplicates skipped** — Existing members are not re-invited
3. **Invalid emails reported** — Summary shows any failures

## Handling Errors

### "Invalid email format"
**Solution:** Check for typos or missing @ symbols.

### "Invalid role"
**Solution:** Use lowercase: \`admin\`, \`editor\`, or \`viewer\`.

### "Seat limit exceeded"
**Solution:** Your plan's team size limit reached. Remove members or upgrade.

### "Email already in team"
**Note:** This is informational — the member is already on your team.

## Sample CSV

Download this template to get started:

\`\`\`csv
email,role
alice@example.com,admin
bob@example.com,editor
charlie@example.com,viewer
\`\`\`
        `
    },

    // =========================================================================
    // BILLING
    // =========================================================================
    {
        id: 'billing-quotas',
        title: 'Plan Limits & Usage Quotas',
        category: 'Billing',
        keywords: ['limit', 'quota', 'usage', 'storage', 'files', 'tokens', 'plan'],
        content: `
# Plan Limits & Usage Quotas

Each plan has specific limits for files, storage, data sources, and AI usage.

## Plan Comparison

| Feature | Starter | Pro | Enterprise |
|---------|---------|-----|------------|
| **Price** | $4.99/mo | $29/mo | Custom |
| **Files** | 50 | 2,000 | 100,000 |
| **Storage** | 100 MB | 10 GB | 1 TB |
| **Data Sources** | 5 | 100 | 1,000 |
| **AI Tokens/month** | 1 million | 10 million | 100 million |
| **Team Members** | 1 | 5 | 100 |

## Understanding Limits

### File Limit
Total number of documents in your knowledge base.

**What counts as a file:**
- Each uploaded file = 1 file
- Each synced document from connectors = 1 file
- Each crawled web page = 1 file

### Storage Limit
Total size of your ingested content.

**What counts toward storage:**
- Original file sizes (before processing)
- Applies to uploads and synced files

### Data Source Limit (Scopes)
Number of connected data sources and contexts.

**What counts as a data source:**
- Each folder selected in Google Drive = 1 source
- Each GitHub repository = 1 source
- Each web crawl = 1 source
- Manual uploads = 1 source (shared)

### AI Token Limit
Monthly allocation for AI processing.

**What uses tokens:**
- Your chat messages
- Document chunks retrieved for context
- AI response generation
- Follow-up questions

**Token reset:** First of each calendar month.

## Checking Your Usage

1. Go to **Settings → Billing**
2. View current usage meters
3. See percentage of each limit used

## What Happens at 100% Usage

### Files/Storage Full
- ❌ Cannot upload new files
- ❌ Cannot sync new documents from connectors
- ❌ Cannot crawl new web pages
- ✅ Existing files remain searchable
- ✅ Chat continues to work

### AI Tokens Exhausted
- ❌ Cannot send new chat messages
- ✅ Can still browse and view documents
- ✅ Resets on the 1st of next month

### Data Sources Full
- ❌ Cannot connect new sources
- ✅ Existing sources continue syncing
- ✅ Full functionality otherwise

## How to Continue

### Option 1: Upgrade Your Plan
Click **Upgrade** in Settings → Billing for more capacity.

### Option 2: Free Up Space
- Delete old files you no longer need
- Disconnect unused data sources
- Remove duplicate documents

### Option 3: Wait for Token Reset
If only tokens are exhausted, wait until the 1st of the month.

## Enterprise Custom Limits

Enterprise plans can be customized:
- Higher file limits
- More storage
- Increased token allocations
- Custom retention policies

Contact sales for a custom quote.
        `
    },
    {
        id: 'subscription-management',
        title: 'Managing Your Subscription',
        category: 'Billing',
        keywords: ['subscription', 'upgrade', 'downgrade', 'cancel', 'payment'],
        content: `
# Managing Your Subscription

## Viewing Your Current Plan

1. Go to **Settings → Billing**
2. Your current plan is displayed at the top
3. Usage meters show your current consumption

## Upgrading Your Plan

### Starter → Pro
1. Go to **Settings → Billing**
2. Click **Upgrade to Pro**
3. Enter payment details
4. Confirm upgrade

**What happens:**
- Immediate access to Pro features
- Current billing period prorated
- Higher limits apply immediately

### Pro → Enterprise
1. Go to **Settings → Billing**
2. Click **Contact Sales** on Enterprise
3. Our team will reach out within 1 business day
4. Custom pricing and limits discussed

## Changing Payment Method

1. Go to **Settings → Billing**
2. Click **Manage Subscription**
3. Opens Polar payment portal
4. Update card or payment method

## Viewing Invoices

1. Go to **Settings → Billing**
2. Scroll to **Billing History**
3. Click any invoice to view/download PDF

## Canceling Your Subscription

1. Go to **Settings → Billing**
2. Scroll to **Danger Zone**
3. Click **Cancel Subscription**
4. Confirm cancellation

**After cancellation:**
- Access continues until end of billing period
- Data is retained for 30 days
- You can resubscribe anytime
- Downgrade to Free (no new ingestion)

## Reactivating After Cancellation

If your subscription was canceled:
1. Go to **Settings → Billing**
2. Select a plan and subscribe
3. Your data (if within 30 days) is restored

## FAQ

### When am I charged?
Billing is monthly from your subscription start date.

### Can I get a refund?
Contact support within 7 days of charge for refund requests.

### What payment methods are accepted?
Credit/debit cards via Polar. Enterprise can use invoicing.

### Is my payment information secure?
Payment processing is handled by Polar (PCI compliant). Axio Hub never sees your card details.
        `
    },

    // =========================================================================
    // TROUBLESHOOTING
    // =========================================================================
    {
        id: 'common-errors',
        title: 'Common Errors & Solutions',
        category: 'Troubleshooting',
        keywords: ['error', 'problem', 'issue', 'fix', 'troubleshoot', 'help'],
        content: `
# Common Errors & Solutions

Quick reference for the most common issues and how to fix them.

## Connection Errors

### "[Connector] connection expired. Please reconnect in Data Sources."

**Affects:** All OAuth connectors (Google Drive, OneDrive, Dropbox, etc.)

**Cause:** OAuth tokens expire after periods of inactivity or are revoked.

**Solution:**
1. Go to **Settings → Data Sources**
2. Click **Disconnect** next to the affected connector
3. Click **Connect** to re-authorize
4. Re-select folders/repositories to sync

### "Integration requires reconnection"

**Cause:** Token refresh failed.

**Solution:** Same as above — disconnect and reconnect.

### "Access denied - insufficient permissions"

**Cause:** Your permissions were changed in the source system.

**Solutions:**
- Verify your access directly in the source (Google Drive, etc.)
- Ensure the file/folder still exists
- Reconnect with an account that has access

## Upload Errors

### "File exceeds 100MB limit"

**Solution:** Reduce file size before uploading:
- PDFs: Use a PDF splitter
- Spreadsheets: Export as multiple files
- Documents: Split into sections

### "Unsupported file type"

**Solution:** Convert to a supported format (PDF, DOCX, TXT, etc.)

### "Upload failed"

**Causes & Solutions:**
- Network issue → Check internet, retry
- Browser problem → Try different browser
- File corrupted → Test opening file locally first

## Search & Chat Errors

### "I couldn't find information about that topic"

**Not an error** — the AI is being honest that your documents don't contain that information.

**Solutions:**
- Upload relevant documents
- Connect additional data sources
- Verify the topic is actually in your files

### "Token limit reached"

**Cause:** Monthly AI token allocation exhausted.

**Solutions:**
- Wait for monthly reset (1st of month)
- Upgrade to a higher plan
- Check Settings → Billing for usage

## Sync Errors

### "Rate limit exceeded"

**Cause:** Too many API requests to the source service.

**Solution:** Axio Hub handles this automatically with retries. Wait a few minutes and the sync will resume.

### "Sync taking too long"

**Normal for:**
- Initial sync of large repositories
- Many files being processed
- Files requiring OCR

**If truly stuck:**
1. Check ingestion jobs in Settings
2. Cancel stuck jobs
3. Reconnect the data source

## Account Errors

### "Session expired"

**Solution:** Log out and log back in.

### "Permission denied"

**Cause:** Your role doesn't allow that action.

**Solution:** Contact your team admin for appropriate permissions.

## Still Having Issues?

1. **Check status:** Look for system announcements
2. **Clear cache:** Browser cache can cause issues
3. **Try incognito:** Eliminates extension conflicts
4. **Contact support:** Include error message and steps to reproduce
        `
    },
    {
        id: 'reconnecting-integrations',
        title: 'How to Reconnect Expired Integrations',
        category: 'Troubleshooting',
        keywords: ['reconnect', 'expired', 'token', 'oauth', 'refresh'],
        content: `
# Reconnecting Expired Integrations

OAuth integrations (Google Drive, OneDrive, Dropbox, etc.) can expire and require reconnection. Here's how to handle it.

## Why Integrations Expire

| Reason | Timeframe |
|--------|-----------|
| Token natural expiry | 60-90 days of inactivity |
| Password change | Immediate |
| Revoked in source app | Immediate |
| Organization policy | Varies |
| Security incident | Immediate |

## Reconnection Steps

### Step 1: Disconnect
1. Go to **Settings → Data Sources**
2. Find the affected connector (it may show "Reconnect Required")
3. Click **Disconnect**

### Step 2: Reconnect
1. Click **Connect** on the same connector
2. Complete the OAuth authorization flow
3. Sign in and grant permissions

### Step 3: Re-select Content
1. Choose folders/repositories to sync (your previous selections are cleared)
2. Click **Save Selection**

### Step 4: Verify
1. Check that the connector shows "Connected"
2. Wait for sync to begin
3. Verify files appear in Knowledge Base

## Connector-Specific Notes

### Google Drive
- May need to re-select folders
- Check [Google Security](https://myaccount.google.com/permissions) if issues persist

### Microsoft (OneDrive/SharePoint)
- Work accounts may need admin re-approval
- Personal accounts reconnect directly

### Dropbox
- Refresh tokens expire after 60 days of inactivity
- Business accounts may have organizational restrictions

### GitHub
- Tokens don't auto-refresh — reconnection is required
- Organization repos may need re-approval

### Notion
- Must re-select which pages Axio Hub can access
- Check Notion workspace settings for integration status

### Box
- Refresh tokens expire after 60 days
- Enterprise accounts may require admin approval

## Preventing Expiration

While some expiration is unavoidable, you can minimize disruptions:

1. **Regular use:** Active syncs keep tokens fresh
2. **Avoid password changes:** Or reconnect immediately after
3. **Don't revoke access:** In source app's connected apps settings
4. **Monitor:** Check Data Sources page periodically

## Data After Reconnection

- Previously synced files remain in your knowledge base
- Deleted files (in source) are removed on next sync
- New files are added automatically
- No duplicate processing of unchanged files
        `
    },
    {
        id: 'performance-tips',
        title: 'Performance Tips & Best Practices',
        category: 'Troubleshooting',
        keywords: ['slow', 'performance', 'speed', 'optimize', 'fast'],
        content: `
# Performance Tips

Get the most out of Axio Hub with these best practices.

## Faster Search Results

### Be Specific
❌ "Tell me about the project"
✅ "What is the budget for Project Atlas in Q3 2024?"

Specific questions search fewer documents and return faster.

### Use Filters
- Filter by data source when you know where information is
- Use date ranges for time-sensitive queries
- Select specific contexts/folders

### Shorter Conversations
- Start new chats for new topics
- Long conversations accumulate context tokens
- Fresh chats search more efficiently

## Efficient Syncing

### Initial Sync
- Start with most important folders
- Add more sources incrementally
- Large initial syncs are normal and may take time

### Incremental Sync
- After initial sync, only changes are processed
- Keep connectors connected (don't disconnect/reconnect unnecessarily)

### File Organization
- Organize files before syncing
- Use clear folder structures
- Remove duplicates from source

## Optimizing Uploads

### File Preparation
- Use native formats (.docx over .pdf when possible)
- Split very large documents
- Remove password protection before uploading

### Batch Uploads
- Upload multiple files at once
- Processing happens in parallel
- Monitor progress in Knowledge Base

## Storage Management

### Regular Cleanup
- Delete outdated documents
- Remove duplicates
- Disconnect unused data sources

### Prioritize High-Value Content
- Focus on documents you actively search
- Don't sync "archive" folders you rarely access

## AI Usage Optimization

### Token-Efficient Queries
- Ask focused questions
- Avoid extremely broad requests
- Use follow-ups for refinement (context is preserved)

### Understanding Token Usage
- Short questions use fewer tokens
- Retrieved context uses tokens
- Long responses use more tokens

## Browser Performance

### Recommended Browsers
1. Chrome (latest)
2. Firefox (latest)
3. Edge (latest)

### If Experiencing Issues
- Clear browser cache
- Disable unused extensions
- Try incognito mode
- Check for browser updates
        `
    },
    {
        id: 'data-security-faq',
        title: 'Data Security FAQ',
        category: 'Troubleshooting',
        keywords: ['security', 'privacy', 'safe', 'encryption', 'data', 'protection'],
        content: `
# Data Security FAQ

Common questions about how Axio Hub protects your data.

## Encryption

### Is my data encrypted?
**Yes.** All document content is encrypted using AES-256 (Fernet) encryption before storage. This is part of our Ghost Protocol security system.

### What about data in transit?
**Yes.** All connections use TLS 1.2+ encryption. This includes:
- Browser to Axio Hub
- Axio Hub to cloud providers
- Internal service communication

### Who has the encryption keys?
Encryption keys are per-deployment and managed securely. Axio Hub staff cannot decrypt your content.

## Data Access

### Can Axio Hub employees see my documents?
**No.** Your content is encrypted, and we don't have access to decrypt it. We can see metadata (file names, sizes) for support purposes.

### Is my data used to train AI models?
**No.** Your data is never used for AI training. It's only used to answer your queries.

### Do third-party AI providers see my data?
Document chunks are sent to AI providers (OpenAI) for generating responses, but:
- Minimal context is sent (only relevant chunks)
- OpenAI doesn't train on API data
- No persistent storage at the AI provider

## Data Storage

### Where is my data stored?
- **Database:** Supabase (PostgreSQL) with encryption at rest
- **File staging:** Temporary, securely wiped after processing
- **Embeddings:** Stored encrypted alongside content

### How long is data retained?
- Active accounts: Data retained while subscribed
- Deleted files: Removed immediately
- Canceled accounts: 30-day retention, then permanent deletion

## Secure Deletion

### What happens when I delete a file?
1. Document removed from search index
2. Encrypted content deleted from database
3. Embeddings removed
4. Deletion is permanent and unrecoverable

### What about temporary files?
Temporary files during processing are cryptographically wiped using secure overwrite (not just deleted).

## Compliance

### What certifications do you have?
Ghost Protocol is designed to support:
- SOC 2 Type II
- HIPAA technical safeguards
- GDPR requirements
- DoD 5220.22-M (Enterprise)

### Can I get a security questionnaire completed?
**Enterprise customers:** Contact sales for security reviews, SOC 2 reports, and questionnaire assistance.

## Account Security

### How is my account protected?
- Secure password hashing
- JWT token authentication
- Session management
- Optional: SSO via your identity provider (Enterprise)

### What if I suspect unauthorized access?
1. Change your password immediately
2. Disconnect and reconnect all integrations
3. Contact support for account audit

## Reporting Security Issues

Found a vulnerability? Contact security@axiohub.io

We appreciate responsible disclosure and will acknowledge researchers.
        `
    }
];

// =========================================================================
// HELPER FUNCTIONS
// =========================================================================

/**
 * Get all unique categories from articles
 */
export const getCategories = (): HelpArticle['category'][] => {
    return ['General', 'AI Features', 'Connectors', 'Teams', 'Billing', 'Troubleshooting'];
};

/**
 * Get articles filtered by category
 */
export const getArticlesByCategory = (category: HelpArticle['category']): HelpArticle[] => {
    return HELP_ARTICLES.filter(article => article.category === category);
};

/**
 * Search articles by query (searches title, content, and keywords)
 */
export const searchArticles = (query: string): HelpArticle[] => {
    if (!query.trim()) return [];
    
    const lowerQuery = query.toLowerCase().trim();
    const queryWords = lowerQuery.split(/\s+/);
    
    return HELP_ARTICLES.filter(article => {
        const titleMatch = article.title.toLowerCase().includes(lowerQuery);
        const contentMatch = article.content.toLowerCase().includes(lowerQuery);
        const keywordMatch = article.keywords?.some(kw => 
            queryWords.some(qw => kw.includes(qw) || qw.includes(kw))
        );
        
        return titleMatch || contentMatch || keywordMatch;
    }).sort((a, b) => {
        // Prioritize title matches
        const aTitle = a.title.toLowerCase().includes(lowerQuery) ? 1 : 0;
        const bTitle = b.title.toLowerCase().includes(lowerQuery) ? 1 : 0;
        if (aTitle !== bTitle) return bTitle - aTitle;
        
        // Then keyword matches
        const aKeyword = a.keywords?.some(kw => lowerQuery.includes(kw)) ? 1 : 0;
        const bKeyword = b.keywords?.some(kw => lowerQuery.includes(kw)) ? 1 : 0;
        return bKeyword - aKeyword;
    });
};

/**
 * Get a single article by ID
 */
export const getArticleById = (id: string): HelpArticle | undefined => {
    return HELP_ARTICLES.find(article => article.id === id);
};

/**
 * Get related articles based on shared keywords
 */
export const getRelatedArticles = (articleId: string, limit: number = 3): HelpArticle[] => {
    const currentArticle = getArticleById(articleId);
    if (!currentArticle || !currentArticle.keywords) return [];
    
    const currentKeywords = new Set(currentArticle.keywords);
    
    return HELP_ARTICLES
        .filter(article => article.id !== articleId)
        .map(article => {
            const sharedKeywords = article.keywords?.filter(kw => currentKeywords.has(kw)).length || 0;
            const categoryMatch = article.category === currentArticle.category ? 1 : 0;
            return { article, score: sharedKeywords + categoryMatch };
        })
        .filter(({ score }) => score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, limit)
        .map(({ article }) => article);
};

/**
 * Get count of articles per category
 */
export const getCategoryCounts = (): Record<HelpArticle['category'], number> => {
    const counts: Record<string, number> = {};
    for (const category of getCategories()) {
        counts[category] = getArticlesByCategory(category).length;
    }
    return counts as Record<HelpArticle['category'], number>;
};
