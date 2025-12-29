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
 * Fetch all documents from the API.
 */
async function fetchDocuments(): Promise<Document[]> {
    const response = await api.get("/documents");
    return response.data.map(mapDocument);
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
 * - Automatic caching (5 min stale time)
 * - Background refetching on window focus
 * - Optimistic delete with rollback on error
 * - Request deduplication
 */
export const useDocuments = () => {
    const { toast } = useToast();
    const queryClient = useQueryClient();

    // Query for fetching documents
    const {
        data: documents = [],
        isLoading,
        error,
        refetch
    } = useQuery({
        queryKey: ["documents"],
        queryFn: fetchDocuments,
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000,   // 10 minutes cache
    });

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
        isLoading,
        error: error ? (error as Error).message : null,
        refresh: refetch,
        deleteDocument: deleteMutation.mutateAsync,
        isDeleting: deleteMutation.isPending,
    };
};
