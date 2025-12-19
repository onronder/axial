"use client";

import { DataSourcesGrid } from "@/components/data-sources/DataSourcesGrid";

export default function DataSourcesPage() {
    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-2">
                <h1 className="font-display text-2xl font-bold tracking-tight">Data Sources</h1>
                <p className="text-muted-foreground">
                    Connect external platforms to ingest documents and data.
                </p>
            </div>
            <DataSourcesGrid />
        </div>
    );
}
