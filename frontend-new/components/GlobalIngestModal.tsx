"use client";

import { IngestModal } from "@/components/ingest-modal";
import { useIngestModal } from "@/hooks/useIngestModal";

/**
 * Global IngestModal that uses context state.
 * Mount this once in the dashboard layout.
 */
export function GlobalIngestModal() {
    const { isOpen, activeTab, closeModal } = useIngestModal();

    return (
        <IngestModal
            isOpen={isOpen}
            onClose={closeModal}
            initialTab={activeTab}
        />
    );
}
