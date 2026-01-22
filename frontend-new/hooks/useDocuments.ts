"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Document } from "@/types";
import { formatSourceTypeLabel, normalizeSourceType } from "@/lib/sourceType";
import { useToast } from "@/hooks/use-toast";

// Stable fallback to avoid new array instances while queries are still loading
const EMPTY_DOCS: Document[] = [];

/**
 * Backend document response interface.
 */
type DocumentMetadata = {
    error?: string;
    file_size?: number;
    size?: number;
    [key: string]: unknown;
};

interface BackendDocument {
    id: string;
    title?: string;
    name?: string;
    source_type?: string;
    source_url?: string;
    path?: string;  // File path within source (e.g., folder path, S3 key)
    status?: string;
    indexing_status?: string;
    created_at?: string;
    size?: number;
    file_size_bytes?: number;
    metadata?: DocumentMetadata;
}

/**
 * Map backend document response to frontend Document interface.
 */
function mapDocument(d: BackendDocument): Document {
    const normalizedSource = normalizeSourceType(d.source_type) || "file_upload";
    const meta: DocumentMetadata = d.metadata || {};
    const resolvedSize = d.size ?? d.file_size_bytes ?? meta?.file_size ?? meta?.size ?? 0;
    return {
        id: d.id,
        name: d.title || d.name || "Untitled",
        source: formatSourceTypeLabel(normalizedSource),
        sourceType: normalizedSource as Document['sourceType'],
        sourceUrl: d.source_url || undefined,
        path: d.path || undefined,  // File path within source (folder, S3 key, etc.)
        status: (d.status as Document['status']) || "indexed",
        indexingStatus: (d.indexing_status as Document['indexingStatus']) || "completed",
        addedAt: d.created_at || new Date().toISOString(),
        size: resolvedSize || 0,
        errorMessage: meta?.error
    };
}

/**
 * Fetch document parameters
 */
interface FetchDocsParams {
    page: number;
    pageSize: number;
    search?: string;
}

interface BulkDeletePayload {
    documentIds?: string[];
    sourceType?: string;
}

/**
 * Fetch documents from the API with pagination.
 */
async function fetchDocuments({ page, pageSize, search }: FetchDocsParams): Promise<{ documents: Document[], total: number }> {
    const response = await api.get("/documents", {
        params: {
            limit: pageSize,
            offset: (page - 1) * pageSize,
            q: search
        }
    });

    // Check for X-Total-Count header
    const totalHeader = response.headers['x-total-count'];
    const total = totalHeader ? parseInt(totalHeader, 10) : response.data.length;

    const filtered = response.data.filter((doc: BackendDocument) => {
        const normalized = normalizeSourceType(doc.source_type) || doc.source_type || "";
        return normalized !== "identity" && normalized !== "scope_identity";
    });

    return {
        documents: filtered.map(mapDocument),
        total
    };
}

/**
 * Delete a document by ID.
 */
async function deleteDocumentApi(id: string): Promise<void> {
    await api.delete(`/documents/${id}`);
}

/**
 * Bulk delete documents by ids or source type.
 */
async function bulkDeleteDocumentsApi(payload: BulkDeletePayload): Promise<void> {
    await api.delete("/documents", {
        data: {
            document_ids: payload.documentIds,
            source_type: payload.sourceType
        }
    });
}

/**
 * Document update request interface.
 */
interface DocumentUpdate {
    title?: string;
    description?: string;
    tags?: string[];
}

/**
 * Update document metadata.
 */
async function updateDocumentApi(id: string, update: DocumentUpdate): Promise<Document> {
    const response = await api.patch(`/documents/${id}`, update);
    return mapDocument(response.data);
}

/**
 * Hook for managing documents with React Query.
 * 
 * Features:
 * - Server-side pagination & search
 * - Automatic caching (5 min stale time)
 * - Optimistic delete with rollback on error
 */
export const useDocuments = (
    page: number = 1,
    pageSize: number = 10,
    search: string = ""
) => {
    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Query for fetching documents
    const {
        data,
        isLoading,
        error,
        refetch
    } = useQuery({
        queryKey: ["documents", page, pageSize, search],
        queryFn: () => fetchDocuments({ page, pageSize, search }),
        staleTime: 5 * 60 * 1000,
        gcTime: 10 * 60 * 1000,
        placeholderData: (previousData) => previousData // Keep prev data while fetching
    });

    // Keep stable fallbacks to avoid rerender loops while the query is loading
    const documents = data?.documents ?? EMPTY_DOCS;
    const totalCount = data?.total ?? 0;

    // Mutation for deleting documents
    const deleteMutation = useMutation({
        mutationFn: deleteDocumentApi,
        onMutate: async (deletedId) => {
            // Cancel any outgoing refetches
            await queryClient.cancelQueries({ queryKey: ["documents"] });

            // Snapshot current state for rollback
            const previousDocs = queryClient.getQueryData<Document[]>(["documents"]);

            // Optimistic update - remove immediately from UI
            queryClient.setQueryData<Document[]>(["documents"], (old) =>
                old?.filter((doc) => doc.id !== deletedId) ?? []
            );

            return { previousDocs };
        },
        onSuccess: () => {
            toast({
                title: "Document deleted",
                description: "The document has been removed.",
            });
        },
        onError: (err: Error, _deletedId, context) => {
            // Rollback on error
            if (context?.previousDocs) {
                queryClient.setQueryData(["documents"], context.previousDocs);
            }
            console.error("Failed to delete document", err.message);
            toast({
                title: "Error",
                description: "Failed to delete document.",
                variant: "destructive",
            });
        },
        onSettled: () => {
            // Refetch to ensure consistency
            queryClient.invalidateQueries({ queryKey: ["documents"] });
        },
    });

    // Mutation for bulk deleting documents
    const bulkDeleteMutation = useMutation({
        mutationFn: bulkDeleteDocumentsApi,
        onSuccess: () => {
            toast({
                title: "Documents deleted",
                description: "Selected documents have been removed.",
            });
            queryClient.invalidateQueries({ queryKey: ["documents"] });
        },
        onError: (err: Error) => {
            console.error("Failed to bulk delete documents", err.message);
            toast({
                title: "Error",
                description: "Failed to delete documents.",
                variant: "destructive",
            });
        },
    });

    // Mutation for updating documents
    const updateMutation = useMutation({
        mutationFn: ({ id, update }: { id: string; update: DocumentUpdate }) =>
            updateDocumentApi(id, update),
        onSuccess: () => {
            toast({
                title: "Document updated",
                description: "Document metadata has been updated.",
            });
            queryClient.invalidateQueries({ queryKey: ["documents"] });
        },
        onError: (err: unknown) => {
            console.error("Failed to update document", err);
            toast({
                title: "Error",
                description: "Failed to update document.",
                variant: "destructive",
            });
        },
    });

    return {
        documents,
        totalCount,
        isLoading,
        error: error ? (error as Error).message : null,
        refresh: refetch,
        deleteDocument: deleteMutation.mutateAsync,
        isDeleting: deleteMutation.isPending,
        bulkDeleteDocuments: bulkDeleteMutation.mutateAsync,
        isBulkDeleting: bulkDeleteMutation.isPending,
        updateDocument: updateMutation.mutateAsync,
        isUpdating: updateMutation.isPending,
    };
};
