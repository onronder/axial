'use client'

import { useState, useEffect } from "react"
import { authFetch } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Loader2, Folder, FileText, ChevronRight, Home, Upload, CheckSquare, Square } from "lucide-react"

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

    // Load Items for Current Folder
    useEffect(() => {
        const fetchItems = async () => {
            setIsLoading(true)
            setError(null)
            try {
                const currentFolder = currentPath[currentPath.length - 1]
                const query = currentFolder.id ? `?parent_id=${currentFolder.id}` : ''
                console.log(`[DriveExplorer] Fetching items for current folder: ${currentFolder.name} (${currentFolder.id || 'root'})`)

                const response = await authFetch.get(`/integrations/google_drive/items${query}`)
                const res = response.data

                console.log("[DriveExplorer] API Response:", res)

                if (Array.isArray(res)) {
                    setItems(res)
                } else if (res && Array.isArray(res.items)) {
                    setItems(res.items)
                } else {
                    console.error("[DriveExplorer] Unexpected response format:", res)
                    setItems([])
                    setError("Received invalid data from Google Drive.")
                }

            } catch (e) {
                console.error("[DriveExplorer] Failed to list items", e)
                setError("Failed to load files. Please try again.")
            } finally {
                setIsLoading(false)
            }
        }
        fetchItems()
    }, [currentPath])

    const handleNavigate = (folderId: string, folderName: string) => {
        setCurrentPath(prev => [...prev, { id: folderId, name: folderName }])
        setSelection(new Set())
    }

    const handleBreadcrumbClick = (index: number) => {
        setCurrentPath(prev => prev.slice(0, index + 1))
        setSelection(new Set())
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
            await authFetch.post('/integrations/google_drive/ingest', { item_ids: Array.from(selection) })
            alert("Ingestion Queued Successfully!")
            setSelection(new Set())
        } catch (e) {
            console.error("Ingest failed", e)
            alert("Ingestion failed")
        } finally {
            setIngesting(false)
        }
    }

    // Filter out folders from selection logic if we only want to ingest files? 
    // Actually BaseConnector supports recursive ingestion now so folders are OK to select if supported.
    // For now assuming we CAN select folders.

    return (
        <div className="flex flex-col h-[500px] border-t border-slate-100">
            {/* Toolbar */}
            <div className="flex items-center justify-between p-4 bg-slate-50/50 border-b border-slate-100">
                {/* Breadcrumbs */}
                <div className="flex items-center gap-1 text-sm text-slate-600 overflow-x-auto no-scrollbar mask-linear-fade">
                    {currentPath.map((item, idx) => (
                        <div key={idx} className="flex items-center whitespace-nowrap">
                            {idx > 0 && <ChevronRight className="h-4 w-4 mx-1 flex-shrink-0 text-slate-400" />}
                            <button
                                onClick={() => handleBreadcrumbClick(idx)}
                                className={`flex items-center hover:text-blue-600 transition-colors px-1 rounded hover:bg-slate-200/50 ${idx === currentPath.length - 1 ? "font-semibold text-slate-900" : ""}`}
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
                        <Button onClick={handleIngest} disabled={ingesting} size="sm" className="ml-4 shadow-sm animate-in fade-in zoom-in-95 bg-blue-600 hover:bg-blue-700 text-white">
                            {ingesting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                            Ingest {selection.size} Items
                        </Button>
                    )}
                </div>
            </div>

            {/* Error State */}
            {error && (
                <div className="p-4 bg-red-50 text-red-600 text-sm text-center border-b border-red-100">
                    {error}
                </div>
            )}

            {/* File List Table */}
            <div className="flex-1 overflow-y-auto bg-white">
                {isLoading ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-400">
                        <Loader2 className="h-8 w-8 animate-spin mb-2" />
                        <span className="text-sm">Loading contents...</span>
                    </div>
                ) : items.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-400">
                        <div className="p-4 bg-slate-50 rounded-full mb-3">
                            <Folder className="h-8 w-8 opacity-20" />
                        </div>
                        <span className="font-medium text-slate-600">This folder is empty</span>
                        <span className="text-xs mt-1">No files found in {currentPath[currentPath.length - 1].name}</span>
                    </div>
                ) : (
                    <table className="w-full text-sm text-left">
                        <thead className="bg-slate-50 sticky top-0 z-10 text-slate-500 font-medium border-b border-slate-100">
                            <tr>
                                <th className="p-3 w-10 text-center"></th>
                                <th className="p-3 w-10">Type</th>
                                <th className="p-3">Name</th>
                                <th className="p-3 text-right">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-50">
                            {items.map((item) => {
                                const isSelected = selection.has(item.id)
                                const isFolder = item.type === 'folder'
                                return (
                                    <tr
                                        key={item.id}
                                        className={`group transition-colors ${isSelected ? "bg-blue-50/50" : "hover:bg-slate-50"}`}
                                    >
                                        <td className="p-3 text-center">
                                            {!isFolder && (
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); toggleSelection(item.id) }}
                                                    className="focus:outline-none"
                                                >
                                                    {isSelected ? (
                                                        <CheckSquare className="h-5 w-5 text-blue-600" />
                                                    ) : (
                                                        <Square className="h-5 w-5 text-slate-300 group-hover:text-slate-400" />
                                                    )}
                                                </button>
                                            )}
                                        </td>
                                        <td className="p-3 text-slate-500">
                                            {isFolder ? (
                                                <Folder className="h-5 w-5 text-blue-500 fill-blue-50" />
                                            ) : (
                                                <div className="relative">
                                                    <FileText className="h-5 w-5 text-slate-400" />
                                                    {/* Attempt to show mime type hint */}
                                                </div>
                                            )}
                                        </td>
                                        <td className="p-3">
                                            {isFolder ? (
                                                <button
                                                    onClick={() => handleNavigate(item.id, item.name)}
                                                    className="font-medium text-slate-700 hover:text-blue-600 hover:underline truncate text-left w-full block"
                                                >
                                                    {item.name}
                                                </button>
                                            ) : (
                                                <div className="flex flex-col">
                                                    <span className="text-slate-700 font-medium truncate">{item.name}</span>
                                                    {item.mime_type && <span className="text-[10px] text-slate-400">{item.mime_type}</span>}
                                                </div>
                                            )}
                                        </td>
                                        <td className="p-3 text-right">
                                            {isFolder && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => handleNavigate(item.id, item.name)}
                                                    className="h-8 text-slate-400 hover:text-blue-600"
                                                >
                                                    Open
                                                </Button>
                                            )}
                                            {!isFolder && (
                                                <Button
                                                    variant="ghost"
                                                    size="sm"
                                                    onClick={() => toggleSelection(item.id)}
                                                    className={`h-8 ${isSelected ? "text-blue-600 bg-blue-100/50" : "text-slate-400 hover:text-blue-600"}`}
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
        </div>
    )
}
