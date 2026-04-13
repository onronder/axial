"use client";

import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { api } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import type { Document } from "@/types";
import {
    DOCUMENTS_KEY,
    bulkDeleteDocumentsApi,
    deleteDocumentApi,
    mapDocument,
} from "@/hooks/useDocuments";
import { extractErrorMessage } from "@/lib/error-handling";

export interface TreeBreadcrumb {
    id: string;
    name: string;
    path: string;
}

export interface FolderTreeItem {
    id: string;
    name: string;
    path: string;
    type: "folder";
    sourceType?: string;
    documentCount: number;
}

export interface FileTreeItem {
    id: string;
    name: string;
    path: string;
    type: "file";
    document: Document;
}

export type DocumentTreeItem = FolderTreeItem | FileTreeItem;

interface BackendDocument {
    id: string;
    title?: string;
    name?: string;
    source_type?: string;
    source_url?: string;
    path?: string;
    status?: string;
    indexing_status?: "pending" | "processing" | "completed" | "failed";
    created_at?: string;
    size?: number;
    file_size_bytes?: number;
    metadata?: Record<string, unknown> | null;
}

interface BackendTreeItem {
    id: string;
    name: string;
    path: string;
    type: "folder" | "file";
    source_type?: string;
    document_count?: number;
    source_url?: string;
    created_at?: string;
    indexing_status?: "pending" | "processing" | "completed" | "failed";
    size?: number;
    metadata?: Record<string, unknown> | null;
}

interface BackendTreeResponse {
    current_path: string;
    breadcrumbs: TreeBreadcrumb[];
    items: BackendTreeItem[];
    total_items: number;
    total_documents: number;
    page: number;
    page_size: number;
    failed_files?: BackendDocument[];
    failed_count?: number;
}

const DOCUMENT_TREE_KEY = ["documentTree"] as const;

const documentTreeQueryKey = (
    path: string,
    page: number,
    pageSize: number,
    search: string
) => [...DOCUMENT_TREE_KEY, path, page, pageSize, search] as const;

function mapTreeItem(item: BackendTreeItem): DocumentTreeItem {
    if (item.type === "folder") {
        return {
            id: item.id,
            name: item.name,
            path: item.path,
            type: "folder",
            sourceType: item.source_type,
            documentCount: item.document_count ?? 0,
        };
    }

    return {
        id: item.id,
        name: item.name,
        path: item.path,
        type: "file",
        document: mapDocument({
            id: item.id,
            title: item.name,
            source_type: item.source_type,
            source_url: item.source_url,
            path: item.path,
            created_at: item.created_at,
            indexing_status: item.indexing_status,
            size: item.size,
            metadata: item.metadata || {},
        }),
    };
}

function mapFailedTreeDocument(item: BackendDocument): Document {
    return mapDocument({
        ...item,
        metadata: item.metadata || {},
    });
}

async function fetchDocumentTree(params: {
    path: string;
    page: number;
    pageSize: number;
    search?: string;
    signal?: AbortSignal;
}) {
    const response = await api.get<BackendTreeResponse>("/documents/tree", {
        params: {
            path: params.path,
            page: params.page,
            page_size: params.pageSize,
            q: params.search || undefined,
        },
        signal: params.signal,
    });

    return response.data;
}

function shouldRetryDocumentTreeQuery(
    failureCount: number,
    error: unknown
): boolean {
    if (failureCount >= 1) {
        return false;
    }

    if (error instanceof AxiosError) {
        const status = error.response?.status;

        // Deterministic client/database failures should not hammer the API.
        if (status && status < 500) {
            return false;
        }
    }

    return true;
}

export function useDocumentTree(
    path: string,
    page: number,
    pageSize: number,
    search: string = ""
) {
    const { toast } = useToast();
    const queryClient = useQueryClient();

    const { data, isLoading, isFetching, isPlaceholderData, refetch } = useQuery({
        queryKey: documentTreeQueryKey(path, page, pageSize, search),
        queryFn: ({ signal }) =>
            fetchDocumentTree({ path, page, pageSize, search, signal }),
        staleTime: 60 * 1000,
        gcTime: 5 * 60 * 1000,
        placeholderData: (previousData) => previousData,
        retry: shouldRetryDocumentTreeQuery,
    });

    const deleteMutation = useMutation({
        mutationFn: deleteDocumentApi,
        onSuccess: () => {
            toast({
                title: "Document deleted",
                description: "The document has been removed.",
            });
        },
        onError: (error: Error) => {
            toast({
                title: "Delete failed",
                description: extractErrorMessage(error, "Failed to delete document."),
                variant: "destructive",
            });
        },
        onSettled: async () => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: DOCUMENT_TREE_KEY }),
                queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY }),
                queryClient.invalidateQueries({ queryKey: ["documentCount"] }),
            ]);
        },
    });

    const bulkDeleteMutation = useMutation({
        mutationFn: bulkDeleteDocumentsApi,
        onSuccess: () => {
            toast({
                title: "Documents deleted",
                description: "Selected documents were removed.",
            });
        },
        onError: (error: Error) => {
            toast({
                title: "Bulk delete failed",
                description: extractErrorMessage(error, "Failed to delete documents."),
                variant: "destructive",
            });
        },
        onSettled: async () => {
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: DOCUMENT_TREE_KEY }),
                queryClient.invalidateQueries({ queryKey: DOCUMENTS_KEY }),
                queryClient.invalidateQueries({ queryKey: ["documentCount"] }),
            ]);
        },
    });

    const items = useMemo(
        () => (data?.items || []).map(mapTreeItem),
        [data?.items]
    );

    const failedFiles = useMemo(
        () => (data?.failed_files || []).map((item) => mapFailedTreeDocument(item)),
        [data?.failed_files]
    );

    return {
        currentPath: data?.current_path ?? path,
        breadcrumbs: data?.breadcrumbs ?? [],
        items,
        totalItems: data?.total_items ?? 0,
        totalDocuments: data?.total_documents ?? 0,
        currentPage: data?.page ?? page,
        pageSize: data?.page_size ?? pageSize,
        failedFiles,
        failedCount: data?.failed_count ?? 0,
        isLoading,
        isFetching,
        isPlaceholderData,
        refresh: refetch,
        deleteDocument: deleteMutation.mutateAsync,
        bulkDeleteDocuments: bulkDeleteMutation.mutateAsync,
        isBulkDeleting: bulkDeleteMutation.isPending,
    };
}
