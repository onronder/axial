'use client'

import { useState, useEffect, useCallback } from "react"
import { toast } from "@/lib/toast"
import { authFetch } from "@/lib/api"
import { extractErrorMessage } from "@/lib/error-handling"
import { format } from "date-fns"
import { FileText, Link as LinkIcon, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { DataSourceIcon } from "@/components/data-sources/DataSourceIcon"
import { normalizeSourceType } from "@/lib/sourceType"

interface Document {
    id: string
    title: string
    source_type: string
    source_url?: string
    created_at: string
}

interface DocumentsResponse {
    documents: Document[]
}

export function KnowledgeBase() {
    const [searchQuery, setSearchQuery] = useState("")

    const [documents, setDocuments] = useState<Document[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchDocuments = useCallback(async () => {
        setLoading(true)
        setError(null)
        try {
            const response = await authFetch.get('/documents')
            const payload = Array.isArray(response.data)
                ? { documents: response.data }
                : (response.data as DocumentsResponse)
            setDocuments(payload.documents || [])
        } catch (err: unknown) {
            if (process.env.NODE_ENV !== 'production') {
                console.error(err)
            }
            setError(extractErrorMessage(err, "Failed to load documents"))
        } finally {
            setLoading(false)
        }
    }, [])

    const [deleteId, setDeleteId] = useState<string | null>(null)

    const handleDelete = async (id: string) => {
        setDeleteId(id)
    }

    const executeDelete = async () => {
        const id = deleteId
        if (!id) return
        setDeleteId(null)

        try {
            await authFetch.delete(`/documents/${id}`)
            // Optimistic update or refetch
            setDocuments(prev => prev.filter(d => d.id !== id))
        } catch (err: unknown) {
            toast({ title: "Error", description: extractErrorMessage(err, "Failed to delete document"), variant: "destructive" })
        }
    }

    useEffect(() => {
        fetchDocuments()
    }, [fetchDocuments])

    const getIcon = (type: string) => {
        const normalizedType = normalizeSourceType(type) || type;
        switch (normalizedType) {
            case 'web': return <LinkIcon className="h-4 w-4 text-primary" />
            case 'google_drive': return <DataSourceIcon sourceId="google-drive" size="sm" />
            default: return <FileText className="h-4 w-4 text-muted-foreground" />
        }
    }

    const filteredDocuments = documents.filter(doc =>
        doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (doc.source_url && doc.source_url.toLowerCase().includes(searchQuery.toLowerCase()))
    )

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle>Knowledge Base</CardTitle>
                <CardDescription>Manage the documents and links your AI has learned from.</CardDescription>
            </CardHeader>
            <CardContent>
                {/* Search Bar */}
                <div className="mb-4">
                    <div className="relative">
                        <FileText className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                        <Input
                            placeholder="Search documents..."
                            className="pl-9"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                </div>

                {loading ? (
                    <div className="p-8 text-center text-muted-foreground text-sm">Loading documents...</div>
                ) : error ? (
                    <div className="p-8 text-center text-destructive text-sm">Error: {error}</div>
                ) : filteredDocuments.length === 0 ? (
                    <div className="p-12 text-center border-2 border-dashed rounded-lg">
                        <div className="mx-auto h-12 w-12 text-muted-foreground/50 mb-3 flex items-center justify-center rounded-full bg-muted">
                            <FileText className="h-6 w-6" />
                        </div>
                        <h3 className="text-lg font-medium text-foreground">No documents found</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            {searchQuery ? "Try a different search query." : "Upload files or add URLs to populate your knowledge base."}
                        </p>
                    </div>
                ) : (
                    <div className="rounded-md border">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-muted text-muted-foreground font-medium border-b">
                                <tr>
                                    <th className="px-4 py-3 w-[50px]">Type</th>
                                    <th className="px-4 py-3">Name / Source</th>
                                    <th className="px-4 py-3 w-[150px]">Date Added</th>
                                    <th className="px-4 py-3 w-[100px] text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y">
                                {filteredDocuments.map((doc) => (
                                    <tr key={doc.id} className="hover:bg-muted/50 transition-colors">
                                        <td className="px-4 py-3">
                                            {getIcon(doc.source_type)}
                                        </td>
                                        <td className="px-4 py-3 font-medium text-foreground">
                                            <div className="flex flex-col">
                                                <span>{doc.title}</span>
                                                {doc.source_url && (
                                                    <a href={doc.source_url} target="_blank" rel="noopener noreferrer" className="text-xs text-muted-foreground/70 hover:text-primary hover:underline truncate max-w-[300px]">
                                                        {doc.source_url}
                                                    </a>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 text-muted-foreground">
                                            {format(new Date(doc.created_at), 'MMM d, yyyy')}
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                                                onClick={() => handleDelete(doc.id)}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                                <span className="sr-only">Delete</span>
                                            </Button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </CardContent>

            <AlertDialog open={!!deleteId} onOpenChange={(open) => !open && setDeleteId(null)}>
                <AlertDialogContent>
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete this document?</AlertDialogTitle>
                        <AlertDialogDescription>
                            This action cannot be undone. All learned knowledge from this source will be permanently removed.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={executeDelete}
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </Card>
    )
}
