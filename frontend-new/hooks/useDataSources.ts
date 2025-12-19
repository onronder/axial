"use client";

import { useState } from "react";
import { DATA_SOURCES, DataSource } from "@/lib/mockData";

export const useDataSources = () => {
    const [dataSources, setDataSources] = useState<DataSource[]>(DATA_SOURCES);
    const [connectedSources, setConnectedSources] = useState<string[]>(
        DATA_SOURCES.filter((ds) => ds.status === "connected" || ds.status === "active").map((ds) => ds.id)
    );

    const connect = (id: string) => {
        console.log("Connecting source:", id);
        setConnectedSources((prev) => [...prev, id]);
        // Mock updating status
        setDataSources((prev) =>
            prev.map((ds) => (ds.id === id ? { ...ds, status: "connected" } : ds))
        );
    };

    const disconnect = (id: string) => {
        console.log("Disconnecting source:", id);
        setConnectedSources((prev) => prev.filter((sourceId) => sourceId !== id));
        // Mock updating status
        setDataSources((prev) =>
            prev.map((ds) => (ds.id === id ? { ...ds, status: "disconnected" } : ds))
        );
    };

    // Mock file operations
    const getFiles = async (sourceId: string, path: string = "/") => {
        console.log(`Fetching files for ${sourceId} at ${path}`);
        return [
            { id: "f1", name: "Report.pdf", type: "file", size: "1.2 MB" },
            { id: "f2", name: "Images", type: "folder", size: "-" }
        ];
    };

    const ingestFiles = async (sourceId: string, fileIds: string[]) => {
        console.log(`Ingesting files ${fileIds} from ${sourceId}`);
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
