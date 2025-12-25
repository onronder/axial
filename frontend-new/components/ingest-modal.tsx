'use client'

import { useState, useEffect } from "react"
import { X, Upload, Link as LinkIcon, FileText, CheckCircle, AlertCircle, Globe, BookOpen } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { authFetch } from "@/lib/api"
import { cn } from "@/lib/utils"
import { NotionInput } from "@/components/ingest/NotionInput"
import { WebInput, validateUrl } from "@/components/ingest/WebInput"

type TabType = 'file' | 'url' | 'website' | 'notion'

interface IngestModalProps {
    isOpen: boolean
    onClose: () => void
    initialTab?: TabType
}

export function IngestModal({ isOpen, onClose, initialTab = 'file' }: IngestModalProps) {
    const [activeTab, setActiveTab] = useState<TabType>(initialTab)
    const [file, setFile] = useState<File | null>(null)
    const [url, setUrl] = useState<string>("")

    // Website tab state
    const [websiteUrl, setWebsiteUrl] = useState<string>("")

    // Notion tab state
    const [notionToken, setNotionToken] = useState<string>("")
    const [notionPageId, setNotionPageId] = useState<string>("")

    const [loading, setLoading] = useState(false)
    const [status, setStatus] = useState<{ type: 'success' | 'error' | null, message: string }>({ type: null, message: "" })

    // Sync activeTab when initialTab changes
    useEffect(() => {
        setActiveTab(initialTab)
    }, [initialTab])

    if (!isOpen) return null

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0])
            setStatus({ type: null, message: "" })
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setLoading(true)
        setStatus({ type: null, message: "" })

        try {
            const { createClient } = await import("@/lib/supabase/client")
            const supabase = createClient()
            const { data: { session } } = await supabase.auth.getSession()
            const token = session?.access_token

            if (!token) throw new Error("Not authenticated")

            if (activeTab === 'file') {
                if (!file) {
                    setLoading(false)
                    return
                }
                const formData = new FormData()
                formData.append("file", file)
                formData.append("metadata", JSON.stringify({ client_id: "frontend_user" }))

                const res = await fetch('/api/py/api/v1/ingest', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` },
                    body: formData
                })

                if (!res.ok) {
                    const err = await res.json()
                    throw new Error(err.detail || "Upload failed")
                }

            } else if (activeTab === 'url' || activeTab === 'website') {
                const targetUrl = activeTab === 'website' ? websiteUrl : url
                if (!targetUrl) {
                    setLoading(false)
                    return
                }

                // Validate URL
                if (!validateUrl(targetUrl)) {
                    throw new Error("Please enter a valid URL starting with http:// or https://")
                }

                const formData = new FormData()
                formData.append("url", targetUrl)
                formData.append("metadata", JSON.stringify({ client_id: "frontend_user", source: "web_crawl" }))

                const res = await fetch('/api/py/api/v1/ingest', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` },
                    body: formData
                })

                if (!res.ok) {
                    const err = await res.json()
                    throw new Error(err.detail || "URL ingestion failed")
                }

            } else if (activeTab === 'notion') {
                if (!notionPageId) {
                    throw new Error("Please enter a Notion Page ID")
                }

                const formData = new FormData()
                formData.append("notion_page_id", notionPageId)
                if (notionToken) {
                    formData.append("notion_token", notionToken)
                }
                formData.append("metadata", JSON.stringify({ client_id: "frontend_user", source: "notion" }))

                const res = await fetch('/api/py/api/v1/ingest', {
                    method: 'POST',
                    headers: { 'Authorization': `Bearer ${token}` },
                    body: formData
                })

                if (!res.ok) {
                    const err = await res.json()
                    throw new Error(err.detail || "Notion ingestion failed")
                }
            }

            setStatus({ type: 'success', message: "Ingestion queued successfully!" })
            // Reset form
            setFile(null)
            setUrl("")
            setWebsiteUrl("")
            setNotionToken("")
            setNotionPageId("")


        } catch (err: any) {
            console.error(err)
            setStatus({ type: 'error', message: err.message || "Something went wrong" })
        } finally {
            setLoading(false)
        }
    }

    // Close when clicking backdrop
    const handleBackdropClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) {
            onClose()
        }
    }

    const tabs = [
        { id: 'file' as const, label: 'File', icon: Upload },
        { id: 'website' as const, label: 'Website', icon: Globe },
        { id: 'notion' as const, label: 'Notion', icon: BookOpen },
    ]

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" onClick={handleBackdropClick}>
            <Card className="w-full max-w-md relative animate-in fade-in zoom-in-95 duration-200">
                <button onClick={onClose} className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2">
                    <X className="h-4 w-4" />
                    <span className="sr-only">Close</span>
                </button>
                <CardHeader>
                    <CardTitle>Add Data Source</CardTitle>
                </CardHeader>
                <CardContent>
                    {/* Tabs */}
                    <div className="flex w-full rounded-md border p-1 mb-6 bg-slate-100">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={cn(
                                    "flex-1 rounded-sm px-3 py-1.5 text-sm font-medium transition-all",
                                    activeTab === tab.id
                                        ? "bg-white text-slate-950 shadow-sm"
                                        : "text-slate-500 hover:text-slate-900"
                                )}
                            >
                                <div className="flex items-center justify-center gap-2">
                                    <tab.icon className="h-4 w-4" />
                                    <span>{tab.label}</span>
                                </div>
                            </button>
                        ))}
                    </div>

                    {/* Content */}
                    <form onSubmit={handleSubmit} className="space-y-4">
                        {activeTab === 'file' && (
                            <div className="grid w-full items-center gap-1.5">
                                <label className="text-sm font-medium leading-none">Select Document (PDF, TXT, MD)</label>
                                <Input key="file-input" type="file" onChange={handleFileChange} />
                                {file && <p className="text-xs text-slate-500">Selected: {file.name}</p>}
                            </div>
                        )}

                        {activeTab === 'website' && (
                            <WebInput
                                url={websiteUrl}
                                onUrlChange={setWebsiteUrl}
                            />
                        )}

                        {activeTab === 'notion' && (
                            <NotionInput
                                token={notionToken}
                                pageId={notionPageId}
                                onTokenChange={setNotionToken}
                                onPageIdChange={setNotionPageId}
                            />
                        )}

                        {/* Legacy URL tab - hidden but kept for backward compat */}
                        {activeTab === 'url' && (
                            <div className="space-y-2">
                                <label className="text-sm font-medium leading-none">Web Page URL</label>
                                <Input key="url-input" placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
                            </div>
                        )}

                        {status.message && (
                            <div className={cn("flex items-center gap-2 p-3 rounded-md text-sm", status.type === 'success' ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700")}>
                                {status.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                                {status.message}
                            </div>
                        )}

                        <div className="flex justify-end gap-2 pt-2">
                            <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
                            <Button type="submit" disabled={loading}>{loading ? "Processing..." : "Ingest"}</Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
