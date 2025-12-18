'use client'

import { useState, useEffect } from "react"
import { authFetch } from "@/lib/api"
import { format } from "date-fns"
import { FileText, Link as LinkIcon, Trash2, HardDrive } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface Document {
    id: string
    title: string
    source_type: 'file' | 'web' | 'drive'
    source_url?: string
    created_at: string
}

export function KnowledgeBase() {
    const [documents, setDocuments] = useState<Document[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchDocuments = async () => {
        setLoading(true)
        setError(null)
        try {
            const data = await authFetch('/documents')
            setDocuments(data)
        } catch (err: any) {
            console.error(err)
            setError(err.message || "Failed to load documents")
        } finally {
            setLoading(false)
        }
    }

    const handleDelete = async (id: string) => {
        if (!confirm("Are you sure you want to delete this document? This action implies deleting all learned knowledge from this source.")) return

        try {
            await authFetch(`/documents/${id}`, { method: 'DELETE' })
            // Optimistic update or refetch
            setDocuments(prev => prev.filter(d => d.id !== id))
        } catch (err: any) {
            alert(err.message || "Failed to delete document")
        }
    }

    useEffect(() => {
        fetchDocuments()
    }, [])

    const getIcon = (type: string) => {
        switch (type) {
            case 'web': return <LinkIcon className="h-4 w-4 text-blue-500" />
            case 'drive': return <HardDrive className="h-4 w-4 text-yellow-500" />
            default: return <FileText className="h-4 w-4 text-slate-500" />
        }
    }

    return (
        <Card className="w-full">
            <CardHeader>
                <CardTitle>Knowledge Base</CardTitle>
                <CardDescription>Manage the documents and links your AI has learned from.</CardDescription>
            </CardHeader>
            <CardContent>
                {/* Refresh / Actions Bar could go here */}

                {loading ? (
                    <div className="p-8 text-center text-slate-500 text-sm">Loading documents...</div>
                ) : error ? (
                    <div className="p-8 text-center text-red-500 text-sm">Error: {error}</div>
                ) : documents.length === 0 ? (
                    <div className="p-12 text-center border-2 border-dashed rounded-lg">
                        <div className="mx-auto h-12 w-12 text-slate-300 mb-3 flex items-center justify-center rounded-full bg-slate-50">
                            <FileText className="h-6 w-6" />
                        </div>
                        <h3 className="text-lg font-medium text-slate-900">No documents found</h3>
                        <p className="text-sm text-slate-500 mt-1">Upload files or add URLs to populate your knowledge base.</p>
                    </div>
                ) : (
                    <div className="rounded-md border">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-slate-50 text-slate-500 font-medium border-b">
                                <tr>
                                    <th className="px-4 py-3 w-[50px]">Type</th>
                                    <th className="px-4 py-3">Name / Source</th>
                                    <th className="px-4 py-3 w-[150px]">Date Added</th>
                                    <th className="px-4 py-3 w-[100px] text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y">
                                {documents.map((doc) => (
                                    <tr key={doc.id} className="hover:bg-slate-50/50 transition-colors">
                                        <td className="px-4 py-3">
                                            {getIcon(doc.source_type)}
                                        </td>
                                        <td className="px-4 py-3 font-medium text-slate-900">
                                            <div className="flex flex-col">
                                                <span>{doc.title}</span>
                                                {doc.source_url && (
                                                    <a href={doc.source_url} target="_blank" rel="noreferrer" className="text-xs text-slate-400 hover:text-blue-500 hover:underline truncate max-w-[300px]">
                                                        {doc.source_url}
                                                    </a>
                                                )}
                                            </div>
                                        </td>
                                        <td className="px-4 py-3 text-slate-500">
                                            {format(new Date(doc.created_at), 'MMM d, yyyy')}
                                        </td>
                                        <td className="px-4 py-3 text-right">
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                className="h-8 w-8 p-0 text-slate-400 hover:text-red-500"
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
        </Card>
    )
}
