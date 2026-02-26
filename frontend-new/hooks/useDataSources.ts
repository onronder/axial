"use client";

import { toast } from "@/lib/toast";

/**
 * useDataSources Hook
 *
 * Manages data source connections with real API integration.
 * Fetches available connectors and user's connected integrations,
 * then merges them into a unified data structure.
 *
 * Features:
 * - OAuth flow management for multiple providers
 * - PKCE support for Microsoft OAuth
 * - File browsing and ingestion
 * - Connection state management
 *
 * @example
 * ```tsx
 * const { dataSources, connect, disconnect } = useDataSources();
 *
 * // Connect a new source
 * await connect('google_drive');
 * 
 * // Disconnect
 * await disconnect('google_drive');
 * ```
 */

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { api } from "@/lib/api";
import { dedupedRequest } from "@/lib/request-dedup";
import { extractErrorMessage } from "@/lib/error-handling";
import {
    getGoogleRedirectUri,
    getGoogleClientId,
    getNotionRedirectUri,
    getNotionClientId,
    getMicrosoftRedirectUri,
    getMicrosoftClientId,
    getMicrosoftTenantId,
    getDropboxClientId,
    getDropboxRedirectUri,
    getGitHubClientId,
    getGitHubRedirectUri,
    getBoxClientId,
    getBoxRedirectUri,
    generatePkcePair,
} from "@/lib/utils";
import { formatSourceTypeLabel, normalizeSourceType } from "@/lib/sourceType";
import type { ConnectorDefinition, UserIntegration, MergedDataSource } from "@/types";

// =============================================================================
// Constants
// =============================================================================

const IS_DEV = process.env.NODE_ENV === 'development';

// =============================================================================
// Types
// =============================================================================

type IntegrationItem = {
    id?: string | number;
    name?: string;
    type?: string;
    size?: number | null;
    mimeType?: string | null;
    mime_type?: string | null;
    parent_id?: string | null;
    web_view_url?: string | null;
};

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Development-only logging utilities.
 * Prevents sensitive information from appearing in production logs.
 */
function devLog(...args: unknown[]): void {
    if (IS_DEV) {
        console.log(...args);
    }
}

function devError(...args: unknown[]): void {
    if (IS_DEV) {
        console.error(...args);
    }
}

function devWarn(...args: unknown[]): void {
    if (IS_DEV) {
        console.warn(...args);
    }
}

/**
 * Logs OAuth configuration status without exposing actual values.
 * Only shows whether credentials are configured, not the actual values.
 */
function logOAuthConfig(provider: string, clientId: string | undefined, redirectUri: string | undefined): void {
    if (IS_DEV) {
        console.log(`🔐 [${provider}] Config:`, {
            clientId: clientId ? '✅ configured' : '❌ missing',
            redirectUri: redirectUri ? '✅ configured' : '❌ missing',
        });
    }
}

// =============================================================================
// Main Hook
// =============================================================================

/**
 * Hook for managing data sources with real API integration.
 * Fetches available connectors and user's connected integrations,
 * then merges them into a unified data structure.
 */
export const useDataSources = () => {
    const [availableConnectors, setAvailableConnectors] = useState<ConnectorDefinition[]>([]);
    const [userIntegrations, setUserIntegrations] = useState<UserIntegration[]>([]);
    const [dataSources, setDataSources] = useState<MergedDataSource[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const hasFetched = useRef(false);
    const abortControllerRef = useRef<AbortController | null>(null);

    // =========================================================================
    // Data Merging
    // =========================================================================

    /**
     * Merge connectors with user integrations into a unified structure.
     */
    const mergeData = useCallback((
        connectors: ConnectorDefinition[],
        integrations: UserIntegration[]
    ): MergedDataSource[] => {
        const integrationMap = new Map(
            integrations.map(int => [int.connector_type, int])
        );

        return connectors.map(connector => {
            const integration = integrationMap.get(connector.type);
            const normalizedType = connector.type?.toLowerCase();
            const rawCategory = (connector.category || "").toLowerCase().replace(/\s+/g, "_");
            let normalizedCategory = rawCategory || "other";
            
            if (normalizedCategory === "cloud_storage" || normalizedCategory === "cloud") {
                normalizedCategory = "cloud";
            } else if (normalizedCategory === "file" || normalizedCategory === "files") {
                normalizedCategory = "files";
            } else if (normalizedCategory === "web" || normalizedCategory === "web_resources") {
                normalizedCategory = "web";
            } else if (normalizedCategory === "database" || normalizedCategory === "databases") {
                normalizedCategory = "database";
            } else if (normalizedCategory === "productivity" || normalizedCategory === "productivity_tools") {
                normalizedCategory = "productivity";
            } else if (normalizedCategory === "apps" || normalizedCategory === "applications") {
                normalizedCategory = "apps";
            }
            
            if (normalizedType === "onedrive" || normalizedType === "sharepoint") {
                normalizedCategory = "cloud";
            }
            
            const rawName = (connector.name || "").trim();
            const normalizedName = rawName.toLowerCase();
            const typeLabel = formatSourceTypeLabel(normalizeSourceType(connector.type));
            const isKeyLikeName = !rawName || rawName === connector.type || rawName.includes("_");
            const displayName =
                normalizedName === "knowledge_base"
                    ? "Knowledge Base"
                    : isKeyLikeName
                        ? typeLabel
                        : rawName;
                        
            return {
                id: connector.type,
                definitionId: connector.id,
                type: connector.type,
                name: displayName,
                description: connector.description || "",
                iconPath: connector.icon_path,
                category: normalizedCategory,
                isConnected: !!integration,
                lastSyncAt: integration?.last_sync_at || null,
                integrationId: integration?.id || null,
            };
        });
    }, []);

    // =========================================================================
    // Data Fetching
    // =========================================================================

    /**
     * Fetch available connectors and user integrations from API.
     */
    const fetchData = useCallback(async () => {
        // Abort any in-flight request
        abortControllerRef.current?.abort();
        const controller = new AbortController();
        abortControllerRef.current = controller;

        devLog('📦 [useDataSources] Fetching data...');
        setLoading(true);
        setError(null);

        try {
            // Fetch both endpoints in parallel (with dedup to prevent duplicate calls
            // when multiple components mount simultaneously)
            const [availableRes, statusRes] = await Promise.all([
                dedupedRequest('integrations:available', () =>
                    api.get('/integrations/available')
                ),
                dedupedRequest('integrations:status', () =>
                    api.get('/integrations/status')
                ),
            ]);

            if (controller.signal.aborted) return;

            const connectors: ConnectorDefinition[] = availableRes.data || [];
            const integrations: UserIntegration[] = statusRes.data || [];

            devLog('📦 [useDataSources] ✅ Available:', connectors.length, 'Status:', integrations.length);

            setAvailableConnectors(connectors);
            setUserIntegrations(integrations);
            setDataSources(mergeData(connectors, integrations));
        } catch (err) {
            if (controller.signal.aborted) return;
            const message = extractErrorMessage(err, 'Failed to fetch data sources');
            devError('📦 [useDataSources] ❌ Fetch failed:', message);
            setError(message);
        } finally {
            if (!controller.signal.aborted) {
                setLoading(false);
            }
        }
    }, [mergeData]);

    // Initial fetch - only once
    useEffect(() => {
        if (hasFetched.current) return;
        hasFetched.current = true;
        fetchData();
        return () => {
            abortControllerRef.current?.abort();
        };
    }, [fetchData]);

    // =========================================================================
    // OAuth Connection
    // =========================================================================

    /**
     * Connect a data source via OAuth redirect.
     */
    const connect = useCallback(async (type: string) => {
        devLog('📦 [useDataSources] Connecting:', type);

        // Google Drive OAuth
        if (type === "google_drive") {
            const clientId = getGoogleClientId();
            const redirectUri = getGoogleRedirectUri();

            logOAuthConfig('Google', clientId, redirectUri);

            if (!clientId) {
                devError('📦 [useDataSources] ❌ Google client ID not configured');
                toast({ title: "Configuration Error", description: "Google OAuth not configured. Please check environment variables.", variant: "destructive" });
                return;
            }

            if (!redirectUri) {
                devError('📦 [useDataSources] ❌ Google redirect URI not configured');
                toast({ title: "Configuration Error", description: "OAuth redirect URI is not configured.", variant: "destructive" });
                return;
            }

            const scope = 'https://www.googleapis.com/auth/drive.readonly';
            const params = new URLSearchParams({
                client_id: clientId,
                redirect_uri: redirectUri,
                response_type: 'code',
                scope: scope,
                access_type: 'offline',
                prompt: 'consent',
                state: 'google'
            });

            window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
            return;
        }
        
        // Notion OAuth
        if (type === "notion") {
            const clientId = getNotionClientId();
            const redirectUri = getNotionRedirectUri();

            logOAuthConfig('Notion', clientId, redirectUri);

            if (!clientId) {
                devError('📦 [useDataSources] ❌ Notion client ID not configured');
                toast({ title: "Configuration Error", description: "Notion OAuth not configured. Please check environment variables.", variant: "destructive" });
                return;
            }

            if (!redirectUri) {
                devError('📦 [useDataSources] ❌ Notion redirect URI not configured');
                toast({ title: "Configuration Error", description: "OAuth redirect URI is not configured.", variant: "destructive" });
                return;
            }

            const params = new URLSearchParams({
                client_id: clientId,
                redirect_uri: redirectUri,
                response_type: 'code',
                owner: 'user',
                state: 'notion'
            });

            window.location.href = `https://api.notion.com/v1/oauth/authorize?${params.toString()}`;
            return;
        }
        
        // Microsoft (OneDrive / SharePoint) OAuth with PKCE
        if (type === "onedrive" || type === "sharepoint") {
            const clientId = getMicrosoftClientId();
            const redirectUri = getMicrosoftRedirectUri();
            const tenantId = getMicrosoftTenantId();

            logOAuthConfig('Microsoft', clientId, redirectUri);

            if (!clientId) {
                devError('📦 [useDataSources] ❌ Microsoft client ID not configured');
                toast({ title: "Configuration Error", description: "Microsoft OAuth not configured. Please check environment variables.", variant: "destructive" });
                return;
            }

            if (!redirectUri) {
                devError('📦 [useDataSources] ❌ Microsoft redirect URI not configured');
                toast({ title: "Configuration Error", description: "OAuth redirect URI is not configured.", variant: "destructive" });
                return;
            }

            const scopes = type === "sharepoint"
                ? "offline_access User.Read Files.Read.All Sites.Read.All"
                : "offline_access User.Read Files.Read.All";

            let pkce;
            try {
                pkce = await generatePkcePair();
                sessionStorage.setItem(`microsoft_pkce_${type}`, pkce.codeVerifier);
            } catch (err) {
                devError('📦 [useDataSources] ❌ PKCE generation failed');
                toast({ title: "OAuth Error", description: "Unable to start Microsoft OAuth. Please refresh and try again.", variant: "destructive" });
                return;
            }

            const params = new URLSearchParams({
                client_id: clientId,
                redirect_uri: redirectUri,
                response_type: "code",
                response_mode: "query",
                scope: scopes,
                prompt: "consent",
                state: type,
                code_challenge: pkce.codeChallenge,
                code_challenge_method: "S256",
            });

            window.location.href = `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/authorize?${params.toString()}`;
            return;
        }
        
        // Dropbox OAuth
        if (type === "dropbox") {
            const clientId = getDropboxClientId();
            const redirectUri = getDropboxRedirectUri();

            logOAuthConfig('Dropbox', clientId, redirectUri);

            if (!clientId) {
                devError('📦 [useDataSources] ❌ Dropbox client ID not configured');
                toast({ title: "Configuration Error", description: "Dropbox OAuth not configured. Please check environment variables.", variant: "destructive" });
                return;
            }

            if (!redirectUri) {
                devError('📦 [useDataSources] ❌ Dropbox redirect URI not configured');
                toast({ title: "Configuration Error", description: "OAuth redirect URI is not configured.", variant: "destructive" });
                return;
            }

            const params = new URLSearchParams({
                client_id: clientId,
                redirect_uri: redirectUri,
                response_type: 'code',
                token_access_type: 'offline',
                state: 'dropbox',
            });

            window.location.href = `https://www.dropbox.com/oauth2/authorize?${params.toString()}`;
            return;
        }
        
        // GitHub OAuth
        if (type === "github") {
            const clientId = getGitHubClientId();
            const redirectUri = getGitHubRedirectUri();

            logOAuthConfig('GitHub', clientId, redirectUri);

            if (!clientId) {
                devError('📦 [useDataSources] ❌ GitHub client ID not configured');
                toast({ title: "Configuration Error", description: "GitHub OAuth not configured. Please check environment variables.", variant: "destructive" });
                return;
            }

            if (!redirectUri) {
                devError('📦 [useDataSources] ❌ GitHub redirect URI not configured');
                toast({ title: "Configuration Error", description: "OAuth redirect URI is not configured.", variant: "destructive" });
                return;
            }

            const params = new URLSearchParams({
                client_id: clientId,
                redirect_uri: redirectUri,
                scope: 'repo read:org',
                state: 'github',
            });

            window.location.href = `https://github.com/login/oauth/authorize?${params.toString()}`;
            return;
        }
        
        // Box OAuth
        if (type === "box") {
            const clientId = getBoxClientId();
            const redirectUri = getBoxRedirectUri();

            logOAuthConfig('Box', clientId, redirectUri);

            if (!clientId) {
                devError('📦 [useDataSources] ❌ Box client ID not configured');
                toast({ title: "Configuration Error", description: "Box OAuth not configured. Please check environment variables.", variant: "destructive" });
                return;
            }

            if (!redirectUri) {
                devError('📦 [useDataSources] ❌ Box redirect URI not configured');
                toast({ title: "Configuration Error", description: "OAuth redirect URI is not configured.", variant: "destructive" });
                return;
            }

            const params = new URLSearchParams({
                client_id: clientId,
                redirect_uri: redirectUri,
                response_type: 'code',
                state: 'box',
            });

            window.location.href = `https://account.box.com/api/oauth2/authorize?${params.toString()}`;
            return;
        }

        // Unknown provider
        devWarn('📦 [useDataSources] Unknown provider type:', type);
    }, []);

    // =========================================================================
    // Disconnection
    // =========================================================================

    /**
     * Disconnect a data source.
     */
    const disconnect = useCallback(async (type: string) => {
        devLog('📦 [useDataSources] Disconnecting:', type);

        try {
            await api.delete(`/integrations/${type}`);
            devLog('📦 [useDataSources] ✅ Disconnected');

            // Update local state
            setUserIntegrations(prev => prev.filter(int => int.connector_type !== type));
            setDataSources(prev => prev.map(ds =>
                ds.type === type
                    ? { ...ds, isConnected: false, lastSyncAt: null, integrationId: null }
                    : ds
            ));
        } catch (err) {
            const message = extractErrorMessage(err, 'Unknown error');
            devError('📦 [useDataSources] ❌ Disconnect failed:', message);
            throw new Error("Failed to disconnect source");
        }
    }, []);

    // =========================================================================
    // File Operations
    // =========================================================================

    /**
     * Get files from a connected source.
     */
    const getFiles = useCallback(async (type: string, parentId?: string) => {
        devLog('📦 [useDataSources] Getting files:', type, parentId ? `parent:${parentId}` : 'root');

        try {
            const { data } = await api.get(`/integrations/${type}/items`, {
                params: parentId ? { parent_id: parentId } : undefined
            });
            
            const normalized = (data || []).map((item: IntegrationItem) => {
                const id = String(item?.id ?? "");
                const name = String(item?.name ?? item?.id ?? "Untitled");
                const typeSafe = item?.type === "folder" ? "folder" : "file";
                return {
                    id,
                    name,
                    type: typeSafe,
                    size: item?.size ?? null,
                    mimeType: item?.mimeType ?? item?.mime_type ?? null,
                    parentId: item?.parent_id ?? null,
                    webViewUrl: item?.web_view_url ?? null,
                };
            });
            
            devLog('📦 [useDataSources] ✅ Got', normalized.length, 'files');
            return normalized;
        } catch (err) {
            devError('📦 [useDataSources] ❌ Get files failed');
            return [];
        }
    }, []);

    /**
     * Ingest files from a source.
     */
    const ingestFiles = useCallback(async (type: string, fileIds: string[]) => {
        devLog('📦 [useDataSources] Ingesting:', type, fileIds.length, 'files');

        try {
            await api.post(`/integrations/${type}/ingest`, {
                item_ids: fileIds
            });
            devLog('📦 [useDataSources] ✅ Ingested');
            return true;
        } catch (err) {
            const message = extractErrorMessage(err, 'Ingestion failed');
            devError('📦 [useDataSources] ❌ Ingest failed:', message);
            throw new Error(message);
        }
    }, []);

    // =========================================================================
    // Sync Operations
    // =========================================================================

    /**
     * Sync an integration manually.
     */
    const syncIntegration = useCallback(async (integrationId: string) => {
        devLog('📦 [useDataSources] Syncing integration:', integrationId);
        
        try {
            const res = await api.post(`/integrations/${integrationId}/sync`);
            devLog('📦 [useDataSources] ✅ Sync started');
            return { success: true, jobId: res.data.job_id };
        } catch (err) {
            const axiosErr = err as { response?: { status?: number }; message?: string };
            devError('📦 [useDataSources] ❌ Sync failed');
            
            if (axiosErr.response?.status === 429) {
                throw new Error("Sync already in progress");
            }
            throw err;
        }
    }, []);

    /**
     * Get list of file IDs that have already been ingested from a source.
     */
    const getIngestedFileIds = useCallback(async (sourceType: string): Promise<Set<string>> => {
        devLog('📦 [useDataSources] Fetching ingested file IDs for:', sourceType);
        
        try {
            const res = await api.get(`/integrations/${sourceType}/ingested-files`);
            const ids = res.data?.ingested_ids || [];
            devLog('📦 [useDataSources] ✅ Found', ids.length, 'ingested files');
            return new Set(ids);
        } catch (err) {
            devError('📦 [useDataSources] ❌ Failed to fetch ingested files');
            return new Set();
        }
    }, []);

    // =========================================================================
    // Utility Functions
    // =========================================================================

    /**
     * Refresh data by re-fetching from API.
     */
    const refresh = useCallback(() => {
        hasFetched.current = false;
        fetchData();
    }, [fetchData]);

    /**
     * Check if a source is connected by ID or type.
     */
    const isConnected = useCallback((idOrType: string) => {
        return dataSources.some(ds =>
            (ds.id === idOrType || ds.type === idOrType) && ds.isConnected
        );
    }, [dataSources]);

    // Legacy: connectedSources array for backward compatibility
    const connectedSources = useMemo(
        () => dataSources.filter(ds => ds.isConnected).map(ds => ds.id),
        [dataSources]
    );

    // =========================================================================
    // Return
    // =========================================================================

    return {
        // New API
        dataSources,
        availableConnectors,
        userIntegrations,
        loading,
        error,
        refresh,
        isConnected,

        // Actions
        connect,
        disconnect,
        getFiles,
        ingestFiles,
        syncIntegration,
        getIngestedFileIds,

        // Legacy compatibility
        connectedSources,
    };
};
