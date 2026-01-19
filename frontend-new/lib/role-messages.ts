/**
 * Role-based Access Messages - Single Source of Truth
 * 
 * Centralized constants for role-based access control messages.
 * Used across components for consistent messaging when users lack permissions.
 */

// =============================================================================
// Toast Titles
// =============================================================================

export const ROLE_TOAST_TITLES = {
    VIEW_ONLY: "View only",
    ACTION_LOCKED: "Action locked",
    UPGRADE_REQUIRED: "Upgrade required",
} as const;

// =============================================================================
// Access Messages
// =============================================================================

export const ROLE_MESSAGES = {
    /** Generic message for editor/admin access requirement */
    NEED_EDITOR_ACCESS: "You need editor or admin access to perform this action.",
    
    /** Specific messages for different actions */
    NEED_EDITOR_UPLOAD: "You need editor or admin access to upload files.",
    NEED_EDITOR_INGEST: "You need editor or admin access to ingest data.",
    NEED_EDITOR_CONNECT: "You need editor or admin access to connect data sources.",
    NEED_EDITOR_DISCONNECT: "You need editor or admin access to manage connections.",
    NEED_EDITOR_SYNC: "You need editor or admin access to sync data.",
    NEED_EDITOR_DELETE: "You need editor or admin access to delete documents.",
    NEED_EDITOR_CRAWL: "You need editor or admin access to run crawls.",
    NEED_EDITOR_INGEST_VIDEOS: "You need editor or admin access to ingest videos.",
    NEED_EDITOR_BROWSE: "You need editor or admin access to browse files.",
    
    /** Plan-based restrictions */
    WEB_CRAWL_UPGRADE: "Web crawling is available on Starter and above plans.",
    YOUTUBE_UPGRADE: "YouTube ingestion requires Starter or Pro plan.",
} as const;

// =============================================================================
// Helper Function
// =============================================================================

/**
 * Checks if a user role has edit permissions.
 * 
 * @param role - The user's role (e.g., "viewer", "editor", "admin", "owner")
 * @returns true if the role has edit permissions
 */
export function hasEditPermission(role: string | undefined | null): boolean {
    if (!role) return false;
    const editRoles = ["editor", "admin", "owner"];
    return editRoles.includes(role.toLowerCase());
}

/**
 * Checks if a user role is view-only.
 * 
 * @param role - The user's role
 * @returns true if the role is view-only
 */
export function isViewerRole(role: string | undefined | null): boolean {
    return role?.toLowerCase() === "viewer";
}
