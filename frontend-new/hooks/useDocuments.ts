"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Document } from "@/types";
import { useToast } from "@/hooks/use-toast";

/**
 * Map backend document response to frontend Document interface.
 */
function mapDocument(d: any): Document {
    return {
        id: d.id,
        name: d.title || d.name || "Untitled",
        source: d.source_type || "file",
        sourceType: d.source_type || "upload",
        status: d.status || "indexed",
        indexingStatus: d.indexing_status || "completed",
        addedAt: d.created_at || new Date().toISOString(),
        size: d.size || 0
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
        onError: (err: any, _deletedId, context) => {
            // Rollback on error
            if (context?.previousDocs) {
                queryClient.setQueryData(["documents"], context.previousDocs);
            }
            console.error("Failed to delete document", err);
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

    return {
        documents,
        totalCount,
        isLoading,
        error: error ? (error as Error).message : null,
        refresh: refetch,
        deleteDocument: deleteMutation.mutateAsync,
        isDeleting: deleteMutation.isPending,
    };
};
