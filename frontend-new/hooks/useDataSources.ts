"use client";

import { useState, useEffect } from "react";
import { DATA_SOURCES, DataSource } from "@/lib/mockData";
import { api } from "@/lib/api";

export const useDataSources = () => {
    const [dataSources, setDataSources] = useState<DataSource[]>(DATA_SOURCES);
    const [connectedSources, setConnectedSources] = useState<string[]>([]);

    // Fetch real status
    useEffect(() => {
        const fetchStatus = async () => {
            console.log('📦 [useDataSources] Fetching integration status...');
            try {
                const { data: statusMap } = await api.get('/api/v1/integrations/status');
                console.log('📦 [useDataSources] ✅ Status fetched:', statusMap);

                const newConnectedSources: string[] = [];
                const updatedDataSources = dataSources.map(ds => {
                    const isConnected = statusMap[ds.type];
                    console.log(`📦 [useDataSources] Source ${ds.id} (${ds.type}): ${isConnected ? 'connected' : 'disconnected'}`);

                    if (isConnected) {
                        newConnectedSources.push(ds.id);
                        return { ...ds, status: 'connected' as const };
                    }
                    return { ...ds, status: 'disconnected' as const };
                });

                setConnectedSources(newConnectedSources);
                setDataSources(updatedDataSources);
                console.log('📦 [useDataSources] Connected sources:', newConnectedSources);
            } catch (error: any) {
                console.error("📦 [useDataSources] ❌ Failed to fetch integration status:", error);
                console.error("📦 [useDataSources] Error response:", error.response?.data);
                console.error("📦 [useDataSources] Error status:", error.response?.status);
            }
        };

        console.log('📦 [useDataSources] Hook mounted, fetching status');
        fetchStatus();
    }, []); // Run once on mount

    const connect = (id: string) => {
        console.log('📦 [useDataSources] Connect called for:', id);
        const source = dataSources.find(ds => ds.id === id);
        if (!source) {
            console.error('📦 [useDataSources] ❌ Source not found:', id);
            return;
        }

        // Handle different source types
        if (source.id === "google-drive") {
            console.log('📦 [useDataSources] Initiating Google OAuth flow...');
            const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
            const redirectUri = process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI
                || (typeof window !== 'undefined' ? `${window.location.origin}/dashboard/oauth/callback` : undefined);

            console.log('📦 [useDataSources] OAuth config:', {
                clientId: clientId ? `${clientId.substring(0, 20)}...` : 'MISSING',
                redirectUri
            });

            if (!clientId || !redirectUri) {
                console.error('📦 [useDataSources] ❌ Google OAuth not configured! Missing:', {
                    clientId: !clientId ? 'NEXT_PUBLIC_GOOGLE_CLIENT_ID' : 'present',
                    redirectUri: !redirectUri ? 'NEXT_PUBLIC_GOOGLE_REDIRECT_URI' : 'present'
                });
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

            const oauthUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
            console.log('📦 [useDataSources] Redirecting to:', oauthUrl);
            window.location.href = oauthUrl;
        } else {
            console.log('📦 [useDataSources] Source type not handled:', source.id);
        }
    };

    const disconnect = async (id: string) => {
        console.log('📦 [useDataSources] Disconnect called for:', id);
        const source = dataSources.find(ds => ds.id === id);
        if (!source) {
            console.error('📦 [useDataSources] ❌ Source not found:', id);
            return;
        }

        try {
            console.log(`📦 [useDataSources] Making DELETE request to /api/v1/integrations/${source.type}`);
            await api.delete(`/api/v1/integrations/${source.type}`);
            console.log('📦 [useDataSources] ✅ Disconnected successfully');
            setConnectedSources((prev) => prev.filter((sourceId) => sourceId !== id));
            setDataSources((prev) =>
                prev.map((ds) => (ds.id === id ? { ...ds, status: "disconnected" } : ds))
            );
        } catch (error: any) {
            console.error('📦 [useDataSources] ❌ Failed to disconnect:', error);
            console.error('📦 [useDataSources] Error response:', error.response?.data);
            throw new Error("Failed to disconnect source");
        }
    };

    /**
     * Fetch files/folders from a connected data source
     */
    const getFiles = async (sourceId: string, path: string = "") => {
        console.log('📦 [useDataSources] getFiles called:', { sourceId, path });
        const source = dataSources.find(ds => ds.id === sourceId);
        if (!source) {
            console.error("📦 [useDataSources] ❌ Source not found:", sourceId);
            return [];
        }

        try {
            console.log(`📦 [useDataSources] Making GET request to /api/v1/integrations/${source.type}/items`);
            const { data } = await api.get(`/api/v1/integrations/${source.type}/items`, {
                params: path ? { parent_id: path } : undefined
            });
            console.log('📦 [useDataSources] ✅ Files fetched:', data?.length || 0, 'items');
            return data;
        } catch (error: any) {
            console.error(`📦 [useDataSources] ❌ Failed to fetch files for ${sourceId}:`, error);
            console.error('📦 [useDataSources] Error response:', error.response?.data);
            return [];
        }
    };

    /**
     * Ingest selected files from a data source
     */
    const ingestFiles = async (sourceId: string, fileIds: string[]) => {
        console.log('📦 [useDataSources] ingestFiles called:', { sourceId, fileIds });
        const source = dataSources.find(ds => ds.id === sourceId);
        if (!source) {
            console.error("📦 [useDataSources] ❌ Source not found:", sourceId);
            return false;
        }

        try {
            console.log(`📦 [useDataSources] Making POST request to /api/v1/integrations/${source.type}/ingest`);
            await api.post(`/api/v1/integrations/${source.type}/ingest`, {
                item_ids: fileIds
            });
            console.log('📦 [useDataSources] ✅ Files ingested successfully');
            return true;
        } catch (error: any) {
            console.error(`📦 [useDataSources] ❌ Failed to ingest files from ${sourceId}:`, error);
            console.error('📦 [useDataSources] Error response:', error.response?.data);
            return false;
        }
    };

    // Log current state
    console.log('📦 [useDataSources] Current state:', {
        dataSourcesCount: dataSources.length,
        connectedCount: connectedSources.length,
        connectedSources
    });

    return {
        dataSources,
        connectedSources,
        connect,
        disconnect,
        getFiles,
        ingestFiles
    };
};
