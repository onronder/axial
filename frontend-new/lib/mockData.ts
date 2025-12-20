/**
 * Application Configuration Data
 * 
 * This file contains static configuration for data sources and UI elements.
 * These are not mock data - they define the available data source types
 * that can be connected and their metadata.
 */

import type { DataSource, DataSourceCategory } from '@/types';

// =============================================================================
// DATA SOURCE CONFIGURATION
// =============================================================================

/**
 * Human-readable labels for data source categories
 */
export const CATEGORY_LABELS: Record<DataSourceCategory, string> = {
    cloud: "Cloud Storage",
    files: "Files",
    web: "Web Resources",
    database: "Databases",
    productivity: "Productivity Tools",
    apps: "Applications",
};

/**
 * Available data sources configuration.
 * 
 * Note: The 'status' and 'lastSync' fields are default values.
 * Actual connection status should be fetched from the backend API.
 */
export const DATA_SOURCES: DataSource[] = [
    // Cloud Storage
    {
        id: "google-drive",
        name: "Google Drive",
        type: "google_drive",
        status: "disconnected",
        lastSync: "-",
        icon: "google-drive",
        description: "Connect your Google Drive to sync documents.",
        category: "cloud",
    },
    {
        id: "onedrive",
        name: "OneDrive",
        type: "onedrive",
        status: "disconnected",
        lastSync: "-",
        icon: "onedrive",
        description: "Connect your Microsoft OneDrive",
        category: "cloud",
    },
    {
        id: "dropbox",
        name: "Dropbox",
        type: "dropbox",
        status: "disconnected",
        lastSync: "-",
        icon: "dropbox",
        description: "Access your Dropbox files",
        category: "cloud",
    },
    {
        id: "box",
        name: "Box",
        type: "box",
        status: "disconnected",
        lastSync: "-",
        icon: "box",
        description: "Connect your Box account",
        category: "cloud",
        comingSoon: true,
    },
    // Files
    {
        id: "sftp",
        name: "SFTP",
        type: "sftp",
        status: "disconnected",
        lastSync: "-",
        icon: "sftp",
        description: "Connect via secure FTP",
        category: "files",
    },
    {
        id: "file-upload",
        name: "Local Upload",
        type: "local",
        status: "active",
        lastSync: "-",
        icon: "upload",
        description: "Upload PDF, DOCX, and TXT files manually.",
        category: "files",
    },
    // Productivity Tools
    {
        id: "notion",
        name: "Notion",
        type: "notion",
        status: "disconnected",
        lastSync: "-",
        icon: "notion",
        description: "Import pages and databases",
        category: "productivity",
    },
    {
        id: "confluence",
        name: "Confluence",
        type: "confluence",
        status: "disconnected",
        lastSync: "-",
        icon: "confluence",
        description: "Connect Atlassian Confluence",
        category: "productivity",
    },
    {
        id: "coda",
        name: "Coda",
        type: "coda",
        status: "disconnected",
        lastSync: "-",
        icon: "coda",
        description: "Import Coda documents",
        category: "productivity",
        comingSoon: true,
    },
    {
        id: "airtable",
        name: "Airtable",
        type: "airtable",
        status: "disconnected",
        lastSync: "-",
        icon: "airtable",
        description: "Connect your Airtable bases",
        category: "productivity",
    },
    // Web Resources
    {
        id: "url-crawler",
        name: "Website Crawler",
        type: "crawler",
        status: "disconnected",
        lastSync: "-",
        icon: "globe",
        description: "Crawl and index your company website.",
        category: "web",
    },
];

// =============================================================================
// CHAT UI CONFIGURATION
// =============================================================================

/**
 * Starter queries shown in the chat empty state.
 * These help users understand what they can do with the AI.
 */
export const starterQueries = [
    {
        title: "Summarize this document",
        description: "Get a quick overview of the key points",
        icon: "file-text",
    },
    {
        title: "Analyze risks",
        description: "Identify potential issues and concerns",
        icon: "alert-triangle",
    },
    {
        title: "Compare versions",
        description: "See what changed between document versions",
        icon: "git-compare",
    },
    {
        title: "Extract data",
        description: "Pull specific data points into a table",
        icon: "file-bar-chart",
    },
];

// =============================================================================
// RE-EXPORT TYPES FOR BACKWARD COMPATIBILITY
// =============================================================================
// These re-exports maintain backward compatibility with existing imports
// from '@/lib/mockData'. New code should import directly from '@/types'.

export type {
    User,
    Message,
    ChatConversation,
    DataSource,
    Document,
    DataSourceCategory,
    DataSourceStatus,
    DocumentSourceType,
    DocumentStatus,
} from '@/types';
