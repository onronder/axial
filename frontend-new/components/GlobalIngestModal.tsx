"use client";

import { IngestModal } from "@/components/ingest-modal";
import { useIngestModal } from "@/hooks/useIngestModal";

/**
 * Global IngestModal that uses context state.
 * Mount this once in the dashboard layout.
 */
export function GlobalIngestModal() {
    const { isOpen, activeTab, closeModal } = useIngestModal();

    // Enhancement: Toast when closing (assuming successful start if not cancelled explicitly)
    // This is a simplification. Ideally, the IngestModal itself should trigger this on "Upload" click.
    // However, since we want to add "Ingest Feedback" without deep drilling:
    // We will just let the IngestModal and GlobalProgress handle the actual status.
    // The requirement was "Improve visibility". 
    // Ensuring GlobalIngestModal is mounted is Step 1.
    // Step 2 is adding the GlobalProgress component if it's missing in the layout (it was in Sidebar file listed previously).

    return (
        <IngestModal
            isOpen={isOpen}
            onClose={closeModal}
            initialTab={activeTab}
        />
    );
}
