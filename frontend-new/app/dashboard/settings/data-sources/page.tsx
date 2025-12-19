'use client'

import { useState, useEffect } from "react"
import { authFetch } from "@/lib/api"
import { GoogleConnectButton } from "@/components/google-connect-button"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, Folder, FileText, ChevronRight, Home, Globe, Upload } from "lucide-react"

type ConnectorItem = {
    id: string
    name: string
    type: 'file' | 'folder'
    mime_type?: string
    icon?: string
    parent_id?: string
}

export default function DataSourcesPage() {
    const [activeTab, setActiveTab] = useState("drive")

    return (
        <div className="container mx-auto max-w-5xl py-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold tracking-tight text-slate-900">Data Sources</h1>
                <p className="text-slate-500 mt-2">Manage your knowledge base integrations and connections.</p>
            </div>

            <Tabs defaultValue="drive" className="w-full" onValueChange={setActiveTab}>
                <TabsList className="grid w-full max-w-md grid-cols-3 mb-8">
                    <TabsTrigger value="drive" className="flex items-center gap-2">
                        <img src="https://www.gstatic.com/images/branding/product/1x/drive_2020q4_48dp.png" className="w-4 h-4" alt="Drive" />
                        Google Drive
                    </TabsTrigger>
                    <TabsTrigger value="web" className="flex items-center gap-2">
                        <Globe className="w-4 h-4" />
                        Web Link
                    </TabsTrigger>
                    {/* Placeholder for future expansion */}
                    <TabsTrigger value="files" className="flex items-center gap-2">
                        <Upload className="w-4 h-4" />
                        Files
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="drive" className="space-y-4">
                    <DriveExplorer />
                </TabsContent>

                <TabsContent value="web" className="space-y-4">
                    <WebIngest />
                </TabsContent>

                <TabsContent value="files" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>File Upload</CardTitle>
                            <CardDescription>Drag and drop files here to add them to your knowledge base.</CardDescription>
                        </CardHeader>
                        <CardContent>
                            <div className="border-2 border-dashed border-slate-200 rounded-lg p-12 text-center text-slate-500">
                                <Upload className="mx-auto h-12 w-12 mb-4 opacity-50" />
                                <p>File upload feature coming soon to this unified view.</p>
                                <p className="text-xs mt-2">Please use the "Add Data Source" button in the sidebar for now.</p>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    )
}

function DriveExplorer() {
    const [isConnected, setIsConnected] = useState(false)
    const [isLoading, setIsLoading] = useState(true)
    const [items, setItems] = useState<ConnectorItem[]>([])
    const [currentPath, setCurrentPath] = useState<{ id: string | null, name: string }[]>([{ id: null, name: 'Home' }])
    const [selection, setSelection] = useState<Set<string>>(new Set())
    const [ingesting, setIngesting] = useState(false)

    // Check Connection Status
    useEffect(() => {
        const checkStatus = async () => {
            try {
                const res = await authFetch('/integrations/google_drive/status')
                setIsConnected(res.connected)
            } catch (e) {
                console.error("Status check failed", e)
            } finally {
                setIsLoading(false)
            }
        }
        checkStatus()
    }, [])

    // Load Items for Current Folder
    useEffect(() => {
        if (!isConnected) return

        const fetchItems = async () => {
            setIsLoading(true)
            try {
                const currentFolder = currentPath[currentPath.length - 1]
                const query = currentFolder.id ? `?parent_id=${currentFolder.id}` : ''
                const res = await authFetch(`/integrations/google_drive/items${query}`)
                setItems(res)
            } catch (e) {
                console.error("Failed to list items", e)
            } finally {
                setIsLoading(false)
            }
        }
        fetchItems()
    }, [isConnected, currentPath])

    const handleNavigate = (folderId: string, folderName: string) => {
        setCurrentPath(prev => [...prev, { id: folderId, name: folderName }])
        setSelection(new Set()) // Clear selection on nav
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
            await authFetch('/integrations/google_drive/ingest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_ids: Array.from(selection) })
            })
            alert("Ingestion Queued Successfully!")
            setSelection(new Set())
        } catch (e) {
            console.error("Ingest failed", e)
            alert("Ingestion failed")
        } finally {
            setIngesting(false)
        }
    }

    if (isLoading && !isConnected) {
        return <div className="flex justify-center p-12"><Loader2 className="animate-spin h-8 w-8 text-blue-500" /></div>
    }

    if (!isConnected) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Connect Google Drive</CardTitle>
                    <CardDescription>Connect your account to browse and ingest files.</CardDescription>
                </CardHeader>
                <CardContent className="flex justify-center py-8">
                    <GoogleConnectButton />
                </CardContent>
            </Card>
        )
    }

    return (
        <Card>
            <CardHeader className="pb-4">
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle>File Explorer</CardTitle>
                        <CardDescription>Browse folders and select files to add to your knowledge base.</CardDescription>
                    </div>
                    {selection.size > 0 && (
                        <div className="flex items-center gap-4 animate-in fade-in">
                            <span className="text-sm font-medium text-slate-600">{selection.size} selected</span>
                            <Button onClick={handleIngest} disabled={ingesting}>
                                {ingesting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                                Ingest Selected
                            </Button>
                        </div>
                    )}
                </div>
            </CardHeader>
            <CardContent>
                {/* Breadcrumbs */}
                <div className="flex items-center gap-1 text-sm text-slate-500 mb-4 p-2 bg-slate-50 rounded-md">
                    {currentPath.map((item, idx) => (
                        <div key={idx} className="flex items-center">
                            {idx > 0 && <ChevronRight className="h-4 w-4 mx-1" />}
                            <button
                                onClick={() => handleBreadcrumbClick(idx)}
                                className={`hover:text-blue-600 font-medium ${idx === currentPath.length - 1 ? "text-slate-900" : ""}`}
                            >
                                {item.id === null ? <Home className="h-4 w-4" /> : item.name}
                            </button>
                        </div>
                    ))}
                </div>

                {/* File List */}
                <div className="border rounded-md divide-y">
                    {isLoading ? (
                        <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-slate-400" /></div>
                    ) : items.length === 0 ? (
                        <div className="p-8 text-center text-slate-500">Folder is empty</div>
                    ) : (
                        items.map((item) => (
                            <div key={item.id} className="flex items-center justify-between p-3 hover:bg-slate-50 transition-colors group">
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                    {/* Icon */}
                                    {item.type === 'folder' ? (
                                        <Folder className="h-5 w-5 text-blue-500 fill-blue-500/20" />
                                    ) : (
                                        <FileText className="h-5 w-5 text-slate-400" />
                                    )}

                                    {/* Name */}
                                    {item.type === 'folder' ? (
                                        <button
                                            onClick={() => handleNavigate(item.id, item.name)}
                                            className="font-medium text-slate-700 hover:text-blue-600 truncate"
                                        >
                                            {item.name}
                                        </button>
                                    ) : (
                                        <span className="text-slate-700 truncate">{item.name}</span>
                                    )}
                                </div>

                                {/* Checkbox / Action */}
                                {item.type !== 'folder' && (
                                    <input
                                        type="checkbox"
                                        className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                        checked={selection.has(item.id)}
                                        onChange={() => toggleSelection(item.id)}
                                    />
                                )}
                            </div>
                        ))
                    )}
                </div>
            </CardContent>
        </Card>
    )
}

function WebIngest() {
    const [url, setUrl] = useState("")
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!url) return
        setLoading(true)
        try {
            await authFetch('/integrations/web/ingest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_ids: [url] })
            })
            alert("URL Ingested Successfully!")
            setUrl("")
        } catch (e) {
            console.error("Ingest failed", e)
            alert("Failed to ingest URL")
        } finally {
            setLoading(false)
        }
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Add Web Source</CardTitle>
                <CardDescription>Crawl a specific webpage and add it to your knowledge base.</CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="flex gap-4">
                    <Input
                        placeholder="https://example.com/article"
                        value={url}
                        onChange={e => setUrl(e.target.value)}
                        className="flex-1"
                    />
                    <Button type="submit" disabled={loading || !url}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Add to Knowledge Base
                    </Button>
                </form>
            </CardContent>
        </Card>
    )
}
