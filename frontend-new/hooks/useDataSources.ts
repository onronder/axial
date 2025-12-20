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
        console.log("Connecting source:", id);
        // For now, these buttons might redirect to auth flow or show modal
        // We just optimistically update for UI feedback if implemented
    };

    const disconnect = async (id: string) => {
        console.log("Disconnecting source:", id);
        const source = dataSources.find(ds => ds.id === id);
        if (!source) return;

        try {
            await api.delete(`/api/v1/integrations/${source.type}`);
            setConnectedSources((prev) => prev.filter((sourceId) => sourceId !== id));
            setDataSources((prev) =>
                prev.map((ds) => (ds.id === id ? { ...ds, status: "disconnected" } : ds))
            );
        } catch (error) {
            console.error("Failed to disconnect:", error);
            alert("Failed to disconnect source.");
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
