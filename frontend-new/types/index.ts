/**
 * Shared type definitions for the application.
 * These types define the data structures used across frontend components and hooks.
 */

// =============================================================================
// USER TYPES
// =============================================================================

export interface User {
    id: string;
    name: string;
    email?: string;
    avatar?: string;
}

// =============================================================================
// CHAT TYPES
// =============================================================================

export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp?: string;
    created_at?: string;
    sources?: string[];
}

export interface ChatConversation {
    id: string;
    title: string;
    created_at: string;
    updated_at?: string;
    metadata?: Record<string, unknown>;
}

// =============================================================================
// DATA SOURCE TYPES
// =============================================================================

export type DataSourceStatus = 'active' | 'connected' | 'disconnected' | 'error';
export type DataSourceCategory = 'cloud' | 'files' | 'web' | 'database' | 'productivity' | 'apps';

export interface DataSource {
    id: string;
    name: string;
    type: string;
    status: DataSourceStatus;
    lastSync: string;
    icon: string;
    description: string;
    category: DataSourceCategory;
    comingSoon?: boolean;
}

// =============================================================================
// DOCUMENT TYPES
// =============================================================================

export type DocumentSourceType = 'drive' | 'web' | 'upload' | 'notion' | 'slack' | 'local';
export type DocumentStatus = 'indexed' | 'processing' | 'error';

export interface Document {
    id: string;
    name: string;
    source: string;
    sourceType: DocumentSourceType;
    status: DocumentStatus;
    addedAt: string;
    size?: number;
}

// =============================================================================
// SEARCH TYPES
// =============================================================================

export interface SearchResult {
    id: string;
    content: string;
    metadata: Record<string, unknown>;
    similarity: number;
    source_type: string;
    document_id: string;
}

// =============================================================================
// PROFILE TYPES
// =============================================================================

export type Plan = 'free' | 'pro' | 'enterprise';
export type Theme = 'light' | 'dark' | 'system';

export interface UserProfile {
    id: string;
    user_id: string;
    first_name: string | null;
    last_name: string | null;
    plan: Plan;
    theme: Theme;
    created_at: string;
    updated_at: string;
}

// =============================================================================
// TEAM TYPES
// =============================================================================

export type Role = 'admin' | 'editor' | 'viewer';
export type MemberStatus = 'active' | 'pending' | 'suspended';

export interface TeamMember {
    id: string;
    email: string;
    name: string | null;
    role: Role;
    status: MemberStatus;
    last_active: string | null;
    created_at: string;
    invited_at: string | null;
}

// =============================================================================
// NOTIFICATION TYPES
// =============================================================================

export type NotificationCategory = 'email' | 'system';

export interface NotificationSetting {
    id: string;
    setting_key: string;
    setting_label: string;
    setting_description: string | null;
    category: NotificationCategory;
    enabled: boolean;
}
