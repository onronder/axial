'use client'

import { useState, useEffect } from "react"
import { authFetch } from "@/lib/api"
import { GoogleConnectButton } from "@/components/google-connect-button"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2, Folder, FileText, ChevronRight, Home, Globe, Upload, Trash2, RefreshCw, Eye, Database, Link as LinkIcon, HardDrive } from "lucide-react"

type ConnectorItem = {
    id: string
    name: string
    type: 'file' | 'folder'
    mime_type?: string
    icon?: string
    parent_id?: string
}

type DocumentDTO = {
    id: string
    title: string
    source_type: string
    created_at: string
    status: string
}

export default function SettingsPage() {
    const [activeTab, setActiveTab] = useState("sources")
    const [integrations, setIntegrations] = useState<{ [key: string]: boolean }>({})
    const [loadingStatus, setLoadingStatus] = useState(true)

    const fetchStatus = async () => {
        try {
            const res = await authFetch('/integrations/status')
            setIntegrations(res)
        } catch (e) {
            console.error("Failed to fetch statuses", e)
        } finally {
            setLoadingStatus(false)
        }
    }

    useEffect(() => {
        fetchStatus()
    }, [])

    const handleDisconnect = async (provider: string) => {
        if (!confirm(`Are you sure you want to disconnect ${provider}?`)) return
        try {
            await authFetch(`/integrations/${provider}`, { method: 'DELETE' })
            fetchStatus() // Refresh status
        } catch (e) {
            console.error("Disconnect failed", e)
            alert("Failed to disconnect")
        }
    }

    return (
        <div className="container mx-auto max-w-6xl py-8 px-4">
            <div className="mb-8">
                <h1 className="text-3xl font-bold tracking-tight text-slate-900">Settings</h1>
                <p className="text-slate-500 mt-2">Manage your data sources and knowledge base.</p>
            </div>

            <Tabs defaultValue="sources" value={activeTab} onValueChange={setActiveTab} className="w-full">
                <TabsList className="grid w-full max-w-md grid-cols-2 mb-8 bg-slate-100 p-1 rounded-xl">
                    <TabsTrigger value="sources" className="rounded-lg">
                        <Database className="w-4 h-4 mr-2" />
                        Data Sources
                    </TabsTrigger>
                    <TabsTrigger value="knowledge" className="rounded-lg">
                        <HardDrive className="w-4 h-4 mr-2" />
                        Knowledge Base
                    </TabsTrigger>
                </TabsList>

                <TabsContent value="sources" className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">

                    {/* Google Drive Section */}
                    <div className="grid gap-6">
                        <Card className="border-slate-200 shadow-sm overflow-hidden">
                            <CardHeader className="bg-slate-50/50 border-b border-slate-100 pb-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="bg-white p-2 rounded-lg border shadow-sm">
                                            <img src="https://www.gstatic.com/images/branding/product/1x/drive_2020q4_48dp.png" className="w-6 h-6" alt="Drive" />
                                        </div>
                                        <div>
                                            <CardTitle className="text-lg">Google Drive</CardTitle>
                                            <CardDescription>Connect to browse and ingest files</CardDescription>
                                        </div>
                                    </div>
                                    {integrations['google_drive'] && (
                                        <Button variant="outline" size="sm" onClick={() => handleDisconnect('google_drive')} className="text-red-500 hover:text-red-600 hover:bg-red-50 border-red-100">
                                            Disconnect
                                        </Button>
                                    )}
                                </div>
                            </CardHeader>
                            <CardContent className="p-0">
                                {loadingStatus ? (
                                    <div className="p-12 flex justify-center"><Loader2 className="animate-spin text-slate-400" /></div>
                                ) : integrations['google_drive'] ? (
                                    <DriveExplorer />
                                ) : (
                                    <div className="p-12 flex flex-col items-center justify-center text-center space-y-4 bg-slate-50/30">
                                        <div className="bg-blue-100 p-4 rounded-full mb-2">
                                            <img src="https://www.gstatic.com/images/branding/product/1x/drive_2020q4_48dp.png" className="w-8 h-8 opacity-50 grayscale hover:grayscale-0 transition-all cursor-pointer" alt="Drive" />
                                        </div>
                                        <div>
                                            <h3 className="font-medium text-slate-900">Not Connected</h3>
                                            <p className="text-slate-500 text-sm max-w-sm mx-auto mt-1">Connect your Google Drive account to access and sync your documents with Axial.</p>
                                        </div>
                                        <GoogleConnectButton />
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        <div className="grid md:grid-cols-2 gap-6">
                            {/* Web Source */}
                            <Card className="border-slate-200 shadow-sm">
                                <CardHeader>
                                    <div className="flex items-center gap-2">
                                        <Globe className="w-5 h-5 text-blue-500" />
                                        <CardTitle className="text-lg">Web Source</CardTitle>
                                    </div>
                                    <CardDescription>Crawl a webpage to extract content</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <WebIngest />
                                </CardContent>
                            </Card>

                            {/* File Upload Placeholder */}
                            <Card className="border-slate-200 shadow-sm opacity-60">
                                <CardHeader>
                                    <div className="flex items-center gap-2">
                                        <Upload className="w-5 h-5 text-slate-500" />
                                        <CardTitle className="text-lg">File Upload</CardTitle>
                                    </div>
                                    <CardDescription>Drag & Drop files (Coming Soon)</CardDescription>
                                </CardHeader>
                                <CardContent>
                                    <div className="border-2 border-dashed border-slate-200 rounded-lg h-32 flex items-center justify-center text-slate-400 bg-slate-50">
                                        <span className="text-sm">Upload disabled in simplified view</span>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </div>
                </TabsContent>

                <TabsContent value="knowledge" className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                    <KnowledgeBaseTable />
                </TabsContent>
            </Tabs>
        </div>
    )
}

// --- Sub-Components ---

function DriveExplorer() {
    const [isLoading, setIsLoading] = useState(true)
    const [items, setItems] = useState<ConnectorItem[]>([])
    const [currentPath, setCurrentPath] = useState<{ id: string | null, name: string }[]>([{ id: null, name: 'Home' }])
    const [selection, setSelection] = useState<Set<string>>(new Set())
    const [ingesting, setIngesting] = useState(false)

    // Load Items for Current Folder
    useEffect(() => {
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

    return (
        <div className="flex flex-col h-[500px]">
            {/* Toolbar */}
            <div className="flex items-center justify-between p-4 border-b bg-white">
                {/* Breadcrumbs */}
                <div className="flex items-center gap-1 text-sm text-slate-500 overflow-x-auto no-scrollbar">
                    {currentPath.map((item, idx) => (
                        <div key={idx} className="flex items-center whitespace-nowrap">
                            {idx > 0 && <ChevronRight className="h-4 w-4 mx-1 flex-shrink-0" />}
                            <button
                                onClick={() => handleBreadcrumbClick(idx)}
                                className={`hover:text-blue-600 font-medium transition-colors ${idx === currentPath.length - 1 ? "text-slate-900" : ""}`}
                            >
                                {item.id === null ? <div className="flex items-center gap-1"><Home className="h-4 w-4" /> Drive</div> : item.name}
                            </button>
                        </div>
                    ))}
                </div>

                {/* Actions */}
                {selection.size > 0 && (
                    <Button onClick={handleIngest} disabled={ingesting} size="sm" className="ml-4 animate-in fade-in zoom-in-95">
                        {ingesting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}
                        Ingest {selection.size} Items
                    </Button>
                )}
            </div>

            {/* File List */}
            <div className="flex-1 overflow-y-auto bg-white p-2">
                {isLoading ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-400">
                        <Loader2 className="h-8 w-8 animate-spin mb-2" />
                        <span className="text-sm">Loading contents...</span>
                    </div>
                ) : items.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-slate-400">
                        <Folder className="h-12 w-12 opacity-20 mb-2" />
                        <span className="text-sm">This folder is empty</span>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-1">
                        {items.map((item) => (
                            <div key={item.id} className={`flex items-center justify-between p-3 rounded-lg transition-all group ${selection.has(item.id) ? "bg-blue-50 border border-blue-100" : "hover:bg-slate-50 border border-transparent"}`}>
                                <div className="flex items-center gap-3 flex-1 min-w-0">
                                    {/* Icon */}
                                    {item.type === 'folder' ? (
                                        <div className="bg-blue-100 p-2 rounded-md">
                                            <Folder className="h-5 w-5 text-blue-600" />
                                        </div>
                                    ) : (
                                        <div className="bg-slate-100 p-2 rounded-md">
                                            <FileText className="h-5 w-5 text-slate-500" />
                                        </div>
                                    )}

                                    {/* Name */}
                                    <div className="flex flex-col min-w-0">
                                        {item.type === 'folder' ? (
                                            <button
                                                onClick={() => handleNavigate(item.id, item.name)}
                                                className="font-medium text-slate-700 hover:text-blue-600 truncate text-left"
                                            >
                                                {item.name}
                                            </button>
                                        ) : (
                                            <span className="text-slate-700 truncate font-medium">{item.name}</span>
                                        )}
                                        {item.mime_type && <span className="text-xs text-slate-400 truncate">{item.mime_type}</span>}
                                    </div>
                                </div>

                                {/* Checkbox / Action */}
                                {item.type !== 'folder' && (
                                    <div onClick={() => toggleSelection(item.id)} className="p-2 cursor-pointer">
                                        <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${selection.has(item.id) ? "bg-blue-600 border-blue-600" : "border-slate-300 bg-white group-hover:border-blue-400"}`}>
                                            {selection.has(item.id) && <div className="w-2.5 h-1.5 border-b-2 border-l-2 border-white -rotate-45 mb-0.5" />}
                                        </div>
                                    </div>
                                )}
                                {item.type === 'folder' && (
                                    <Button variant="ghost" size="icon" onClick={() => handleNavigate(item.id, item.name)} className="text-slate-400 hover:text-blue-600">
                                        <ChevronRight className="h-4 w-4" />
                                    </Button>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
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
        <form onSubmit={handleSubmit} className="flex gap-2">
            <div className="relative flex-1">
                <LinkIcon className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
                <Input
                    placeholder="https://example.com/article"
                    value={url}
                    onChange={e => setUrl(e.target.value)}
                    className="pl-9"
                />
            </div>
            <Button type="submit" disabled={loading || !url}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Add
            </Button>
        </form>
    )
}

function KnowledgeBaseTable() {
    const [docs, setDocs] = useState<DocumentDTO[]>([])
    const [isLoading, setIsLoading] = useState(true)

    const fetchDocs = async () => {
        setIsLoading(true)
        try {
            const res = await authFetch('/documents')
            setDocs(res)
        } catch (e) {
            console.error("Fetch docs failed", e)
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        fetchDocs()
    }, [])

    const handleDelete = async (id: string, title: string) => {
        if (!confirm(`Delete "${title}"? This cannot be undone.`)) return
        try {
            await authFetch(`/documents/${id}`, { method: 'DELETE' })
            setDocs(prev => prev.filter(d => d.id !== id))
        } catch (e) {
            console.error("Delete failed", e)
            alert("Failed to delete document")
        }
    }

    return (
        <Card className="border-slate-200 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between">
                <div>
                    <CardTitle>Ingested Documents</CardTitle>
                    <CardDescription>Manage the files and links your AI has processed.</CardDescription>
                </div>
                <Button variant="outline" size="icon" onClick={fetchDocs} disabled={isLoading}>
                    <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                </Button>
            </CardHeader>
            <CardContent>
                {isLoading ? (
                    <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-slate-400" /></div>
                ) : docs.length === 0 ? (
                    <div className="text-center py-12 text-slate-500">
                        <Database className="h-12 w-12 mx-auto mb-3 opacity-20" />
                        <p>No documents found.</p>
                        <p className="text-xs">Go to "Data Sources" to add some knowledge.</p>
                    </div>
                ) : (
                    <div className="rounded-md border">
                        <table className="w-full text-sm text-left">
                            <thead className="bg-slate-50 border-b text-slate-500 font-medium">
                                <tr>
                                    <th className="p-3 pl-4">Title</th>
                                    <th className="p-3">Source</th>
                                    <th className="p-3">Status</th>
                                    <th className="p-3">Created</th>
                                    <th className="p-3 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y">
                                {docs.map(doc => (
                                    <tr key={doc.id} className="hover:bg-slate-50 transition-colors group">
                                        <td className="p-3 pl-4 font-medium text-slate-700">
                                            <div className="flex items-center gap-2">
                                                <div className="p-1.5 bg-slate-100 rounded text-slate-500">
                                                    <FileText className="h-4 w-4" />
                                                </div>
                                                {doc.title || "Untitled"}
                                            </div>
                                        </td>
                                        <td className="p-3">
                                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
                                                {doc.source_type}
                                            </span>
                                        </td>
                                        <td className="p-3">
                                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${doc.status === 'indexed'
                                                ? 'bg-green-100 text-green-700'
                                                : 'bg-yellow-100 text-yellow-700'
                                                }`}>
                                                {doc.status || 'Indexed'}
                                            </span>
                                        </td>
                                        <td className="p-3 text-slate-500">
                                            {new Date(doc.created_at).toLocaleDateString()}
                                        </td>
                                        <td className="p-3 text-right">
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 text-slate-400 hover:text-red-500 hover:bg-red-50"
                                                onClick={() => handleDelete(doc.id, doc.title)}
                                            >
                                                <Trash2 className="h-4 w-4" />
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
