import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "@/lib/api";
import { Document } from "@/lib/mockData";
import { useToast } from "@/hooks/use-toast";

export const useDocuments = () => {
    const { toast } = useToast();
    const [documents, setDocuments] = useState<Document[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const hasFetched = useRef(false);

    const fetchDocuments = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await api.get("/documents");
            // Map backend response to Document interface if necessary
            // Assuming backend returns array of documents matching interface or close to it.
            // If backend fields differ, we might need to map them.
            // Let's assume for now they match or we map them here.
            // Based on previous mock data: id, name, source, sourceType, status, addedAt, size.
            // Backend might return snake_case.
            const mappedDocs: Document[] = response.data.map((d: any) => ({
                id: d.id,
                name: d.title || d.name || "Untitled",
                source: d.source_type || "file",  // Use source_type from backend
                sourceType: d.source_type || "upload",
                status: d.status || "indexed",
                addedAt: d.created_at || new Date().toISOString(),
                size: d.size || 0
            }));
            setDocuments(mappedDocs);
        } catch (err: any) {
            console.error("Failed to fetch documents", err);
            setError(err.message || "Failed to fetch documents");
            toast({
                title: "Error",
                description: "Failed to load documents from server.",
                variant: "destructive",
            });
        } finally {
            setIsLoading(false);
        }
    };

    const deleteDocument = async (id: string) => {
        try {
            await api.delete(`/documents/${id}`);
            setDocuments((prev) => prev.filter((doc) => doc.id !== id));
            toast({
                title: "Document deleted",
                description: "The document has been removed.",
            });
        } catch (err: any) {
            console.error("Failed to delete document", err);
            toast({
                title: "Error",
                description: "Failed to delete document.",
                variant: "destructive",
            });
        }
    };

    // Initial fetch - only once (prevents duplicate calls in Strict Mode)
    useEffect(() => {
        if (hasFetched.current) return;
        hasFetched.current = true;
        fetchDocuments();
    }, []);

    return {
        documents,
        isLoading,
        error,
        refresh: fetchDocuments,
        deleteDocument
    };
};
