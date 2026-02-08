'use client'

import { useState, useEffect } from "react"
import { authFetch } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"
import { useIngestionProgress } from "@/hooks/useIngestionProgress"
import { Folder, FileText, ChevronRight, Home, Upload, CheckSquare, Square } from "lucide-react"

import { Spinner } from "@/components/ui/spinner";
type ConnectorItem = {
    id: string
    name: string
    type: 'file' | 'folder'
    mime_type?: string
    icon?: string
    parent_id?: string
}

export function DriveExplorer() {
    const [isLoading, setIsLoading] = useState(true)
    const [items, setItems] = useState<ConnectorItem[]>([])
    const [currentPath, setCurrentPath] = useState<{ id: string | null, name: string }[]>([{ id: null, name: 'Google Drive' }])
    const [selection, setSelection] = useState<Set<string>>(new Set())
    const [ingesting, setIngesting] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const { toast } = useToast()

    // Use centralized ingestion progress context - GlobalProgress renders the UI
    const { registerJob } = useIngestionProgress()

    // Load Items for Current Folder
    useEffect(() => {
        const fetchItems = async () => {
            setIsLoading(true)
            setError(null)
            try {
                const currentFolder = currentPath[currentPath.length - 1]
                const query = currentFolder.id ? `?parent_id=${currentFolder.id}` : ''

                const response = await authFetch.get(`/integrations/google_drive/items${query}`)
                const res = response.data

                if (Array.isArray(res)) {
                    setItems(res)
                } else if (res && Array.isArray(res.items)) {
                    setItems(res.items)
                } else {
                    if (process.env.NODE_ENV !== 'production') {
                        console.error("[DriveExplorer] Unexpected response format:", res)
                    }
                    setItems([])
                    setError("Received invalid data from Google Drive.")
                }

            } catch {
                setError("Failed to load files. Please try again.")
            } finally {
                setIsLoading(false)
            }
        }
        fetchItems()
    }, [currentPath])

    const handleNavigate = (folderId: string, folderName: string) => {
        setCurrentPath(prev => [...prev, { id: folderId, name: folderName }])
    }

    const handleBreadcrumbClick = (index: number) => {
        setCurrentPath(prev => prev.slice(0, index + 1))
    }

    const toggleSelection = (id: string) => {
        const next = new Set(selection)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        setSelection(next)
    }

    const handleIngest = async () => {
        if (selection.size === 0) return
        setIngesting(true)
        try {
            const response = await authFetch.post('/integrations/google_drive/ingest', { item_ids: Array.from(selection) })
            const jobId = response.data?.job_id

            if (jobId) {
                // Register job with centralized context - GlobalProgress will show UI
                registerJob(jobId)
            }

            toast({
                title: "Ingestion Started",
                description: `${selection.size} item(s) are now being processed.`,
            })
            setSelection(new Set())
        } catch {
            toast({
                title: "Ingestion Failed",
                description: "Could not queue items for ingestion. Please try again.",
                variant: "destructive",
            })
        } finally {
            setIngesting(false)
        }
    }

    // Filter out folders from selection logic if we only want to ingest files? 
    // Actually BaseConnector supports recursive ingestion now so folders are OK to select if supported.
    // For now assuming we CAN select folders.

    return (
        <div className="flex flex-col h-[500px] border-t border-border">
            {/* Toolbar */}
            <div className="flex items-center justify-between p-4 bg-muted/50 border-b border-border">
                {/* Breadcrumbs */}
                <div className="flex items-center gap-1 text-sm text-muted-foreground overflow-x-auto no-scrollbar mask-linear-fade">
                    {currentPath.map((item, idx) => (
                        <div key={idx} className="flex items-center whitespace-nowrap">
                            {idx > 0 && <ChevronRight className="h-4 w-4 mx-1 flex-shrink-0 text-muted-foreground" />}
                            <button
                                onClick={() => handleBreadcrumbClick(idx)}
                                className={`flex items-center hover:text-primary transition-colors px-1 rounded hover:bg-muted ${idx === currentPath.length - 1 ? "font-semibold text-foreground" : ""}`}
                            >
                                {item.id === null ? <Home className="h-4 w-4 mr-1" /> : null}
                                {item.name}
                            </button>
                        </div>
                    ))}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                    {selection.size > 0 && (
                        <Button onClick={handleIngest} disabled={ingesting} size="sm" className="ml-4 shadow-sm animate-in fade-in zoom-in-95">
                            {ingesting ? <Spinner className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                            Ingest {selection.size} Items
                        </Button>
                    )}
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div className="p-4 bg-destructive/10 text-destructive text-sm text-center border-b border-destructive/20">
                    {error}
                </div>
            )}

            {/* File List Table */}
            <div className="flex-1 overflow-y-auto bg-background">
                {isLoading ? (
                    <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
                        <Spinner className="h-8 w-8 animate-spin mb-2" />
                        <span className="text-sm">Loading contents...</span>
                    </div>
                ) : items.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-muted-foreground">
                        <div className="p-4 bg-muted rounded-full mb-3">
                            <Folder className="h-8 w-8 opacity-20" />
                        </div>
                        <span className="font-medium text-foreground">This folder is empty</span>
                        <span className="text-xs mt-1">No files found in {currentPath[currentPath.length - 1].name}</span>
                    </div>
                ) : (
                    <table className="w-full text-sm text-left">
                        <thead className="bg-muted sticky top-0 z-10 text-muted-foreground font-medium border-b border-border">
                            <tr>
                                <th className="p-3 w-10 text-center"></th>
                                <th className="p-3 w-10">Type</th>
                                <th className="p-3">Name</th>
                                <th className="p-3 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                            {items.map((item) => {
                                const isSelected = selection.has(item.id)
                                const isFolder = item.type === 'folder'
                                return (
                                    <tr
                                        key={item.id}
                                        className={`group transition-colors ${isSelected ? "bg-primary/10" : "hover:bg-muted/50"}`}
                                    >
                                        <td className="p-3 text-center">
                                            <button
                                                onClick={(e) => { e.stopPropagation(); toggleSelection(item.id) }}
                                                className="focus:outline-none"
                                            >
                                                {isSelected ? (
                                                    <CheckSquare className="h-5 w-5 text-primary" />
                                                ) : (
                                                    <Square className="h-5 w-5 text-muted-foreground/30 group-hover:text-muted-foreground/50" />
                                                )}
                                            </button>
                                        </td>
                                        <td className="p-3 text-muted-foreground">
                                            {isFolder ? (
                                                <Folder className="h-5 w-5 text-primary fill-primary/10" />
                                            ) : (
                                                <div className="relative">
                                                    <FileText className="h-5 w-5 text-muted-foreground" />
                                                    {/* Attempt to show mime type hint */}
                                                </div>
                                            )}
                                        </td>
                                        <td className="p-3">
                                            {isFolder ? (
                                                <button
                                                    onClick={() => handleNavigate(item.id, item.name)}
                                                    className="font-medium text-foreground hover:text-primary hover:underline truncate text-left w-full block"
                                                >
                                                    {item.name}
                                                </button>
                                            ) : (
                                                <div className="flex flex-col">
                                                    <span className="text-foreground font-medium truncate">{item.name}</span>
                                                    {item.mime_type && <span className="text-[10px] text-muted-foreground">{item.mime_type}</span>}
                                                </div>
                                            )}
                                        </td>
                                        <td className="p-3 text-right">
                                            {isFolder && (
                                                <div className="flex gap-1 justify-end">
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => toggleSelection(item.id)}
                                                        className={`h-8 ${isSelected ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-primary"}`}
                                                    >
                                                        {isSelected ? "Selected" : "Select All"}
                                                    </Button>
                                                    <Button
                                                        variant="ghost"
                                                        size="sm"
                                                        onClick={() => handleNavigate(item.id, item.name)}
                                                        className="h-8 text-muted-foreground hover:text-primary"
                                                    >
                                                        Open
                                                    </Button>
                                                </div>
                                            )}
                                            {!isFolder && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => toggleSelection(item.id)}
                                                    className={`h-8 ${isSelected ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-primary"}`}
                                                >
                                                    {isSelected ? "Selected" : "Select"}
                                                </Button>
                                            )}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                )}
            </div>

            {/* Progress UI is now rendered by GlobalProgress - single source of truth */}
        </div>
    )
}
