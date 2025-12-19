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

    // Real file operations - pass through to api? 
    // The previous implementation was mock. 
    // We can keep mock file operations for browsing IF the backend doesn't support browsing for all types yet.
    // The prompt only asked to update "Integration Status" logic.
    // So I will keep getFiles/ingestFiles as mocks OR update them if I verified endpoints.
    // Prompt says: "Update hooks/useDataSources.ts (Integration Status)". 
    // I will leave getFiles/ingestFiles as is (mock) to avoid breaking things I am not asked to touch, 
    // BUT I should check if I need to update them. 
    // The prompt says "Modify useDataSources to fetch connected status...". 
    // It does not explicitly say to update getFiles. 
    // I will leave them as is for now to minimize risk.

    const getFiles = async (sourceId: string, path: string = "/") => {
        console.log(`Fetching files for ${sourceId} at ${path}`);
        // If we want real data, we would call /api/v1/integrations/{source_type}/items?parent_id={path}
        // But for "google_drive" it might work.
        // Let's stick to existing logic for browsing unless asked.
        return [
            { id: "f1", name: "Report.pdf", type: "file", size: "1.2 MB" },
            { id: "f2", name: "Images", type: "folder", size: "-" }
        ];
    };

    const ingestFiles = async (sourceId: string, fileIds: string[]) => {
        console.log(`Ingesting files ${fileIds} from ${sourceId}`);
        // Real ingestion is handled in DriveExplorer specific logic usually.
        return true;
    }

    return {
        dataSources,
        connectedSources,
        connect,
        disconnect,
        getFiles,
        ingestFiles
    };
};
