"use client";

import { useState, useEffect } from "react";
import { DATA_SOURCES, DataSource } from "@/lib/mockData";
import { api } from "@/lib/api";

export const useDataSources = () => {
    const [dataSources, setDataSources] = useState<DataSource[]>(DATA_SOURCES);
    const [connectedSources, setConnectedSources] = useState<string[]>([]);
    // const [connectedSources, setConnectedSources] = useState<string[]>(
    //     DATA_SOURCES.filter((ds) => ds.status === "connected" || ds.status === "active").map((ds) => ds.id)
    // );

    // Fetch real status
    useEffect(() => {
        const fetchStatus = async () => {
            try {
                // api.get returns AxiosResponse, so we await it and get .data
                const { data: statusMap } = await api.get('/api/v1/integrations/status');
                // statusMap: { [key: string]: boolean } e.g., { "google_drive": true }

                const newConnectedSources: string[] = [];
                const updatedDataSources = dataSources.map(ds => {
                    const isConnected = statusMap[ds.type]; // ds.type matches "google_drive", "notion", etc.

                    if (isConnected) {
                        newConnectedSources.push(ds.id);
                        return { ...ds, status: 'connected' as const };
                    }
                    return { ...ds, status: 'disconnected' as const };
                });

                setConnectedSources(newConnectedSources);
                setDataSources(updatedDataSources);
            } catch (error) {
                console.error("Failed to fetch integration status:", error);
            }
        };

        fetchStatus();
    }, []); // Run once on mount

    const connect = (id: string) => {
        const source = dataSources.find(ds => ds.id === id);
        if (!source) return;

        // Handle different source types
        if (source.id === "google-drive") {
            // Redirect to Google OAuth
            const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
            const redirectUri = process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI
                || (typeof window !== 'undefined' ? `${window.location.origin}/dashboard/oauth/callback` : undefined);

            if (!clientId || !redirectUri) {
                console.error('Google OAuth not configured');
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
        // For other sources like sftp, onedrive, etc. - would be handled differently
        // These might open modals or redirect to other OAuth flows
    };

    const disconnect = async (id: string) => {
        const source = dataSources.find(ds => ds.id === id);
        if (!source) return;

        try {
            await api.delete(`/api/v1/integrations/${source.type}`);
            setConnectedSources((prev) => prev.filter((sourceId) => sourceId !== id));
            setDataSources((prev) =>
                prev.map((ds) => (ds.id === id ? { ...ds, status: "disconnected" } : ds))
            );
        } catch (error) {
            // Re-throw error for callers to handle with their own toast/UI
            throw new Error("Failed to disconnect source");
        }
    };

    /**
     * Fetch files/folders from a connected data source
     */
    const getFiles = async (sourceId: string, path: string = "") => {
        const source = dataSources.find(ds => ds.id === sourceId);
        if (!source) {
            console.error("Source not found:", sourceId);
            return [];
        }

        try {
            const { data } = await api.get(`/api/v1/integrations/${source.type}/items`, {
                params: path ? { parent_id: path } : undefined
            });
            return data;
        } catch (error) {
            console.error(`Failed to fetch files for ${sourceId}:`, error);
            return [];
        }
    };

    /**
     * Ingest selected files from a data source
     */
    const ingestFiles = async (sourceId: string, fileIds: string[]) => {
        const source = dataSources.find(ds => ds.id === sourceId);
        if (!source) {
            console.error("Source not found:", sourceId);
            return false;
        }

        try {
            await api.post(`/api/v1/integrations/${source.type}/ingest`, {
                item_ids: fileIds
            });
            return true;
        } catch (error) {
            console.error(`Failed to ingest files from ${sourceId}:`, error);
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
