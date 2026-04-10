/**
 * Documents Page
 * 
 * Main page for document management.
 */

"use client";

import { FileText, Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DocumentsTable } from '@/components/knowledge-base/DocumentsTable';
import { useIngestModal } from '@/hooks/useIngestModal';

export default function DocumentsPage() {
    const { openModal } = useIngestModal();

    return (
        <div className="h-full overflow-auto">
            <div className="max-w-7xl mx-auto p-8 space-y-8">
                {/* Header */}
                <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                    <div className="space-y-1">
                        <h1 className="text-3xl font-bold flex items-center gap-3">
                            <FileText className="h-8 w-8 text-primary" />
                            Documents
                        </h1>
                        <p className="text-muted-foreground">
                            Manage your knowledge base
                        </p>
                    </div>

                    <Button onClick={() => openModal()} className="gap-2">
                        <Upload className="h-4 w-4" />
                        Upload Documents
                    </Button>
                </div>

                {/* Document List */}
                <DocumentsTable showHeader={false} />
            </div>
        </div>
    );
}
