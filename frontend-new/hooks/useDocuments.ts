"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Document } from "@/types";
import { useToast } from "@/hooks/use-toast";

/**
 * Backend document response interface.
 */
interface BackendDocument {
    id: string;
    title?: string;
    name?: string;
    source_type?: string;
    source_url?: string;
    status?: string;
    indexing_status?: string;
    created_at?: string;
    size?: number;
    metadata?: { error?: string };
}

/**
 * Map backend document response to frontend Document interface.
 */
function mapDocument(d: BackendDocument): Document {
    return {
        id: d.id,
        name: d.title || d.name || "Untitled",
        source: d.source_type || "file",
        sourceType: (d.source_type as Document['sourceType']) || "upload",
        sourceUrl: d.source_url || undefined,
        status: (d.status as Document['status']) || "indexed",
        indexingStatus: (d.indexing_status as Document['indexingStatus']) || "completed",
        addedAt: d.created_at || new Date().toISOString(),
        size: d.size || 0,
        errorMessage: d.metadata?.error
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

    return {
        documents: response.data.map(mapDocument),
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

    const documents = data?.documents || [];
    const totalCount = data?.total || 0;

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
        onError: (err: any) => {
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
        updateDocument: updateMutation.mutateAsync,
        isUpdating: updateMutation.isPending,
    };
};
