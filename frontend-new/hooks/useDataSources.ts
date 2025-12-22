"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "@/lib/api";
import type { ConnectorDefinition, UserIntegration, MergedDataSource } from "@/types";

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

    // Merge connectors with user integrations
    const mergeData = useCallback((
        connectors: ConnectorDefinition[],
        integrations: UserIntegration[]
    ): MergedDataSource[] => {
        const integrationMap = new Map(
            integrations.map(int => [int.connector_type, int])
        );

        return connectors.map(connector => {
            const integration = integrationMap.get(connector.type);
            return {
                id: connector.type, // Use type as ID for compatibility
                definitionId: connector.id,
                type: connector.type,
                name: connector.name,
                description: connector.description || "",
                iconPath: connector.icon_path,
                category: connector.category || "other",
                isConnected: !!integration,
                lastSyncAt: integration?.last_sync_at || null,
                integrationId: integration?.id || null,
            };
        });
    }, []);

    // Fetch data from API
    const fetchData = useCallback(async () => {
        console.log('📦 [useDataSources] Fetching data...');
        setLoading(true);
        setError(null);

        try {
            // Fetch both endpoints in parallel
            const [availableRes, statusRes] = await Promise.all([
                api.get('/api/v1/integrations/available'),
                api.get('/api/v1/integrations/status')
            ]);

            const connectors: ConnectorDefinition[] = availableRes.data || [];
            const integrations: UserIntegration[] = statusRes.data || [];

            console.log('📦 [useDataSources] ✅ Available:', connectors.length, 'Status:', integrations.length);

            setAvailableConnectors(connectors);
            setUserIntegrations(integrations);
            setDataSources(mergeData(connectors, integrations));
        } catch (err: any) {
            console.error('📦 [useDataSources] ❌ Fetch failed:', err.message);
            setError(err.message || 'Failed to fetch data sources');
        } finally {
            setLoading(false);
        }
    }, [mergeData]);

    // Initial fetch - only once
    useEffect(() => {
        if (hasFetched.current) return;
        hasFetched.current = true;
        fetchData();
    }, [fetchData]);

    // Connect a data source (OAuth redirect)
    const connect = useCallback((type: string) => {
        console.log('📦 [useDataSources] Connecting:', type);

        if (type === "google_drive") {
            const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
            const redirectUri = process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI
                || (typeof window !== 'undefined' ? `${window.location.origin}/dashboard/oauth/callback` : undefined);

            if (!clientId || !redirectUri) {
                console.error('📦 [useDataSources] ❌ OAuth not configured');
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
                include_granted_scopes: 'true'
            });

            window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
        } else if (type === "notion") {
            // TODO: Implement Notion OAuth
            console.log('📦 [useDataSources] Notion OAuth not yet implemented');
        }
    }, []);

    // Disconnect a data source
    const disconnect = useCallback(async (type: string) => {
        console.log('📦 [useDataSources] Disconnecting:', type);

        try {
            await api.delete(`/api/v1/integrations/${type}`);
            console.log('📦 [useDataSources] ✅ Disconnected');

            // Update local state
            setUserIntegrations(prev => prev.filter(int => int.connector_type !== type));
            setDataSources(prev => prev.map(ds =>
                ds.type === type
                    ? { ...ds, isConnected: false, lastSyncAt: null, integrationId: null }
                    : ds
            ));
        } catch (err: any) {
            console.error('📦 [useDataSources] ❌ Disconnect failed:', err.message);
            throw new Error("Failed to disconnect source");
        }
    }, []);

    // Get files from a connected source
    const getFiles = useCallback(async (type: string, parentId?: string) => {
        console.log('📦 [useDataSources] Getting files:', type, parentId);

        try {
            const { data } = await api.get(`/api/v1/integrations/${type}/items`, {
                params: parentId ? { parent_id: parentId } : undefined
            });
            console.log('📦 [useDataSources] ✅ Got', data?.length || 0, 'files');
            return data || [];
        } catch (err: any) {
            console.error('📦 [useDataSources] ❌ Get files failed:', err.message);
            return [];
        }
    }, []);

    // Ingest files from a source
    const ingestFiles = useCallback(async (type: string, fileIds: string[]) => {
        console.log('📦 [useDataSources] Ingesting:', type, fileIds.length, 'files');

        try {
            await api.post(`/api/v1/integrations/${type}/ingest`, {
                item_ids: fileIds
            });
            console.log('📦 [useDataSources] ✅ Ingested');
            return true;
        } catch (err: any) {
            console.error('📦 [useDataSources] ❌ Ingest failed:', err.message);
            return false;
        }
    }, []);

    // Refresh data
    const refresh = useCallback(() => {
        hasFetched.current = false;
        fetchData();
    }, [fetchData]);

    // Legacy compatibility: check if a source is connected by ID or type
    const isConnected = useCallback((idOrType: string) => {
        return dataSources.some(ds =>
            (ds.id === idOrType || ds.type === idOrType) && ds.isConnected
        );
    }, [dataSources]);

    // Legacy: connectedSources array for backward compatibility
    const connectedSources = dataSources
        .filter(ds => ds.isConnected)
        .map(ds => ds.id);

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

        // Legacy compatibility
        connectedSources,
    };
};
