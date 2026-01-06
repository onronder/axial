"use client";

import { DLQDashboard } from "@/components/admin/DLQDashboard";

/**
 * Failed Tasks Settings Page
 * 
 * Allows users to view and manage their failed ingestion tasks.
 * Users can retry failed tasks individually or in bulk.
 */
export default function FailedTasksPage() {
    return <DLQDashboard />;
}
