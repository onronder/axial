/**
 * Help Articles Data
 * 
 * Production content for the in-app Help Center.
 */

export interface HelpArticle {
    id: string;
    title: string;
    category: 'General' | 'Teams' | 'Billing' | 'AI Features';
    content: string; // Markdown
}

export const HELP_ARTICLES: HelpArticle[] = [
    {
        id: 'ai-smart-router',
        title: 'How does the AI choose between models?',
        category: 'AI Features',
        content: `
# Smart Router vs. Fast Mode

Axio Hub uses a sophisticated routing system to give you the best balance of speed and intelligence.

## ⚡ Fast Mode (Llama-3)

For routine tasks like greetings, summarizing short texts, or general questions, we use the **Llama-3** model via Groq. It creates responses in milliseconds.

**Best for:**
- Quick questions
- Summarizing documents
- General chat

## 🧠 Smart Mode (GPT-4o)

For complex tasks requiring deep reasoning, legal analysis, or coding, the system automatically switches to **GPT-4o**.

**Best for:**
- Complex analysis
- Code generation
- Multi-step reasoning

> **Note:** Starter plans are locked to Fast Mode. Upgrade to **Pro** or **Enterprise** to unlock the Smart Router.
        `
    },
    {
        id: 'team-roles',
        title: 'Team Roles & Permissions',
        category: 'Teams',
        content: `
# Understanding Roles

When inviting members to your Enterprise Team, you can assign the following roles:

| Role | Chat & Search | Upload Files | Web Crawl | Invite/Remove Members | Billing |
|------|---------------|--------------|-----------|----------------------|---------|
| **Admin** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Editor** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Viewer** | ✅ Yes | ❌ No | ❌ No | ❌ No | ❌ No |

## When to use each role

- **Admins** are usually Team Owners or IT Managers who need full control
- **Editors** are knowledge contributors (e.g., Senior Engineers) who upload and manage content
- **Viewers** are consumers (e.g., Field Staff) who query the data but don't change it

## Changing roles

1. Go to **Settings → Team Management**
2. Find the team member
3. Click the role dropdown
4. Select the new role
        `
    },
    {
        id: 'bulk-import',
        title: 'How to Bulk Invite via CSV',
        category: 'Teams',
        content: `
# Bulk Import Guide

You can invite your entire organization at once using a CSV file.

## CSV Format

Your file must contain strictly two columns: \`email\` and \`role\`.

\`\`\`csv
email,role
john.doe@company.com,editor
jane.smith@company.com,viewer
field.team01@company.com,viewer
\`\`\`

## Important Rules

1. **Roles:** Must be lowercase ('admin', 'editor', 'viewer')
2. **Limits:** You can upload up to 500 rows at a time
3. **Duplicates:** If a user is already in the team, they will be skipped automatically
4. **Invalid emails:** Will be reported in the error summary

## Steps

1. Go to **Settings → Team Management**
2. Click **Bulk Import**
3. Download the template CSV
4. Fill in your team members
5. Upload and confirm
        `
    },
    {
        id: 'billing-quotas',
        title: 'What happens when I hit my limit?',
        category: 'Billing',
        content: `
# Usage Quotas

Each plan has specific limits for files and storage.

## File Limits

| Plan | File Limit |
|------|------------|
| **Starter** | 20 Files |
| **Pro** | 500 Files |
| **Enterprise** | Unlimited |

## Storage Limits

| Plan | Storage |
|------|---------|
| **Starter** | 100 MB |
| **Pro** | 5 GB |
| **Enterprise** | Unlimited |

## What happens at 100% usage?

1. You **cannot upload** new files
2. You **cannot crawl** new websites
3. Existing files remain **safe and searchable**

## How to continue working

- **Upgrade your plan** for more capacity
- **Delete old files** to free up space
- Contact support for temporary extensions
        `
    },
    {
        id: 'getting-started',
        title: 'Getting Started with Axio Hub',
        category: 'General',
        content: `
# Welcome to Axio Hub

Axio Hub is your AI-powered knowledge assistant. Here's how to get started quickly.

## Step 1: Upload Your Documents

1. Go to **Knowledge Base** in the sidebar
2. Click **Upload** or drag and drop files
3. Supported formats: PDF, DOCX, TXT, MD

## Step 2: Connect Cloud Storage

1. Go to **Settings → Data Sources**
2. Click **Connect** for Google Drive, OneDrive, or Notion
3. Select folders to sync

## Step 3: Start Chatting

1. Click **New Chat** in the sidebar
2. Ask questions about your documents
3. Get AI-powered answers with citations

## Tips for Best Results

- Upload complete documents (not snippets)
- Use descriptive file names
- Organize files in folders for easier searching
        `
    },
    {
        id: 'web-crawling',
        title: 'How to Crawl Websites',
        category: 'AI Features',
        content: `
# Web Crawling

Import entire websites or specific pages into your knowledge base.

## How it works

1. Go to **Knowledge Base**
2. Click **Add Source → Web Crawler**
3. Enter the URL
4. Choose crawl depth (single page or follow links)
5. Click **Start Crawl**

## Supported sites

- Public websites (no login required)
- Blog posts and documentation
- FAQ pages and help centers

## Limitations

- Cannot crawl password-protected pages
- Maximum 100 pages per crawl
- Pro and Enterprise plans only

## Best practices

- Start with a single page to test
- Use sitemap URLs for comprehensive crawls
- Review crawled content in Knowledge Base
        `
    }
];

// Helper to get categories
export const getCategories = (): HelpArticle['category'][] => {
    return ['General', 'AI Features', 'Teams', 'Billing'];
};

// Helper to get articles by category
export const getArticlesByCategory = (category: HelpArticle['category']): HelpArticle[] => {
    return HELP_ARTICLES.filter(article => article.category === category);
};

// Helper to search articles
export const searchArticles = (query: string): HelpArticle[] => {
    const lowerQuery = query.toLowerCase();
    return HELP_ARTICLES.filter(
        article =>
            article.title.toLowerCase().includes(lowerQuery) ||
            article.content.toLowerCase().includes(lowerQuery)
    );
};

// Helper to get article by ID
export const getArticleById = (id: string): HelpArticle | undefined => {
    return HELP_ARTICLES.find(article => article.id === id);
};
