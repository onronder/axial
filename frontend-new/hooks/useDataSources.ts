"use client";

import { useState, useEffect, useRef } from "react";
import { DATA_SOURCES, DataSource } from "@/lib/mockData";
import { api } from "@/lib/api";

export const useDataSources = () => {
    const [dataSources, setDataSources] = useState<DataSource[]>(DATA_SOURCES);
    const [connectedSources, setConnectedSources] = useState<string[]>([]);
    const hasFetched = useRef(false);

    // Fetch real status - only once
    useEffect(() => {
        if (hasFetched.current) return;
        hasFetched.current = true;

        const fetchStatus = async () => {
            console.log('📦 [useDataSources] Fetching status...');
            try {
                const { data: statusMap } = await api.get('/api/v1/integrations/status');
                console.log('📦 [useDataSources] ✅ Status:', statusMap);

                const newConnectedSources: string[] = [];
                const updatedDataSources = dataSources.map(ds => {
                    const isConnected = statusMap[ds.type];
                    if (isConnected) {
                        newConnectedSources.push(ds.id);
                        return { ...ds, status: 'connected' as const };
                    }
                    return { ...ds, status: 'disconnected' as const };
                });

                setConnectedSources(newConnectedSources);
                setDataSources(updatedDataSources);
            } catch (error: any) {
                console.error("📦 [useDataSources] ❌ Status fetch failed:", error.message);
            }
        };

        fetchStatus();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const connect = (id: string) => {
        console.log('📦 [useDataSources] Connecting:', id);
        const source = dataSources.find(ds => ds.id === id);
        if (!source) return;

        if (source.id === "google-drive") {
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
        }
    };

    const disconnect = async (id: string) => {
        console.log('📦 [useDataSources] Disconnecting:', id);
        const source = dataSources.find(ds => ds.id === id);
        if (!source) return;

        try {
            await api.delete(`/api/v1/integrations/${source.type}`);
            console.log('📦 [useDataSources] ✅ Disconnected');
            setConnectedSources((prev) => prev.filter((sourceId) => sourceId !== id));
            setDataSources((prev) =>
                prev.map((ds) => (ds.id === id ? { ...ds, status: "disconnected" } : ds))
            );
        } catch (error: any) {
            console.error('📦 [useDataSources] ❌ Disconnect failed:', error.message);
            throw new Error("Failed to disconnect source");
        }
    };

    const getFiles = async (sourceId: string, path: string = "") => {
        console.log('📦 [useDataSources] Getting files:', sourceId, path);
        const source = dataSources.find(ds => ds.id === sourceId);
        if (!source) return [];

        try {
            const { data } = await api.get(`/api/v1/integrations/${source.type}/items`, {
                params: path ? { parent_id: path } : undefined
            });
            console.log('📦 [useDataSources] ✅ Got', data?.length || 0, 'files');
            return data;
        } catch (error: any) {
            console.error(`📦 [useDataSources] ❌ Get files failed:`, error.message);
            return [];
        }
    };

    const ingestFiles = async (sourceId: string, fileIds: string[]) => {
        console.log('📦 [useDataSources] Ingesting:', sourceId, fileIds.length, 'files');
        const source = dataSources.find(ds => ds.id === sourceId);
        if (!source) return false;

        try {
            await api.post(`/api/v1/integrations/${source.type}/ingest`, {
                item_ids: fileIds
            });
            console.log('📦 [useDataSources] ✅ Ingested');
            return true;
        } catch (error: any) {
            console.error(`📦 [useDataSources] ❌ Ingest failed:`, error.message);
            return false;
        }
    };

    return {
        dataSources,
        connectedSources,
        connect,
        disconnect,
        getFiles,
        ingestFiles
    };
};
