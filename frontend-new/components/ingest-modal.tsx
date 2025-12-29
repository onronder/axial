'use client'

import { useState, useEffect } from "react"
import { X, Upload, Link as LinkIcon, FileText, CheckCircle, AlertCircle, Globe, BookOpen, Loader2, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { authFetch } from "@/lib/api"
import { cn } from "@/lib/utils"
// NotionInput removed - using OAuth flow now
import { WebInput, validateUrl } from "@/components/ingest/WebInput"
import { useDataSources } from "@/hooks/useDataSources"
import { useToast } from "@/hooks/use-toast"
import { motion, AnimatePresence } from "framer-motion"

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

    // Hook for Data Sources (OAuth)
    const { connect, isConnected, loading: dsLoading } = useDataSources()
    const isNotionConnected = isConnected('notion')
    const { toast } = useToast()

    const [loading, setLoading] = useState(false)
    const [progress, setProgress] = useState(0)

    // Sync activeTab when initialTab changes
    useEffect(() => {
        setActiveTab(initialTab)
    }, [initialTab])

    // Reset progress when tab changes
    useEffect(() => {
        setProgress(0)
    }, [activeTab])

    if (!isOpen) return null

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0])
            setProgress(0)
        }
    }

    const handleNotionConnect = () => {
        connect('notion')
        // OAuth redirect will happen, no need to set loading here managed by hook
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        // If Notion tab, we don't submit via this form anymore
        if (activeTab === 'notion') {
            return
        }

        setLoading(true)
        setProgress(10) // Start progress

        // Fake progress animation for better UX during queueing
        const interval = setInterval(() => {
            setProgress(prev => Math.min(prev + 5, 90))
        }, 300)

        try {
            const { createClient } = await import("@/lib/supabase/client")
            const supabase = createClient()
            const { data: { session } } = await supabase.auth.getSession()
            const token = session?.access_token

            if (!token) throw new Error("Not authenticated")

            const endpoint = '/api/py/ingest'
            let body: FormData | null = null

            if (activeTab === 'file') {
                if (!file) {
                    setLoading(false)
                    clearInterval(interval)
                    return
                }
                const formData = new FormData()
                formData.append("file", file)
                formData.append("metadata", JSON.stringify({ client_id: "frontend_user" }))
                body = formData

            } else if (activeTab === 'url' || activeTab === 'website') {
                const targetUrl = activeTab === 'website' ? websiteUrl : url
                if (!targetUrl) {
                    setLoading(false)
                    clearInterval(interval)
                    return
                }

                // Validate URL
                if (!validateUrl(targetUrl)) {
                    throw new Error("Please enter a valid URL starting with http:// or https://")
                }

                const formData = new FormData()
                formData.append("url", targetUrl)
                formData.append("metadata", JSON.stringify({ client_id: "frontend_user", source: "web_crawl" }))
                body = formData
            }

            if (!body) {
                // Should not happen
                setLoading(false)
                clearInterval(interval)
                return
            }

            const res = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: body
            })

            clearInterval(interval)
            setProgress(100)

            // Robust error handling: Check content type
            const contentType = res.headers.get("content-type")
            if (!res.ok) {
                if (contentType && contentType.includes("application/json")) {
                    const err = await res.json()
                    throw new Error(err.detail || "Ingestion failed")
                } else {
                    const text = await res.text()
                    console.error("Non-JSON API Error:", text)
                    if (res.status === 503) {
                        throw new Error("Service unavailable. The document queue is currently down.")
                    } else if (res.status === 500) {
                        throw new Error("Internal server error. Please try again later.")
                    } else if (res.status === 413) {
                        throw new Error("File too large.")
                    }
                    throw new Error(`Server error (${res.status})`)
                }
            }

            toast({
                title: "Ingestion Queued",
                description: activeTab === 'file' ? "Your file is being processed." : "The URL has been added to the crawl queue.",
                variant: "default",
                className: "bg-green-50 border-green-200 text-green-900",
            })

            // Close modal after short delay to show 100% progress
            setTimeout(() => {
                onClose()
                // Reset form
                setFile(null)
                setUrl("")
                setWebsiteUrl("")
                setProgress(0)
            }, 800)

        } catch (err: any) {
            clearInterval(interval)
            setProgress(0)
            console.error(err)
            toast({
                title: "Ingestion Failed",
                description: err.message || "Something went wrong. Please try again.",
                variant: "destructive",
            })
        } finally {
            // Only unset loading if we errored, otherwise we wait for the timeout close
            // This prevents the button from becoming enabled while modal is closing
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
                            <div className="flex flex-col items-center justify-center py-6 space-y-4 text-center border rounded-lg bg-slate-50/50">
                                <BookOpen className={cn("h-12 w-12", isNotionConnected ? "text-green-500" : "text-slate-300")} />

                                {isNotionConnected ? (
                                    <div className="space-y-2">
                                        <h3 className="font-semibold text-slate-900 flex items-center justify-center gap-2">
                                            <CheckCircle className="h-4 w-4 text-green-500" />
                                            Notion Connected
                                        </h3>
                                        <p className="text-sm text-slate-500 max-w-[260px] mx-auto">
                                            Your Notion workspace is synced. All accessible pages will be automatically ingested.
                                        </p>
                                        <div className="pt-2">
                                            <Button variant="outline" size="sm" onClick={() => window.open('https://notion.so/my-integrations', '_blank')} className="text-xs">
                                                Manage in Notion
                                            </Button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        <h3 className="font-medium text-slate-900">Connect Notion Workspace</h3>
                                        <p className="text-sm text-slate-500 max-w-[280px] mx-auto">
                                            Connect your workspace to automatically import and sync pages.
                                        </p>
                                        <Button
                                            type="button"
                                            onClick={handleNotionConnect}
                                            disabled={dsLoading}
                                            className="bg-slate-900 text-white hover:bg-slate-800"
                                        >
                                            {dsLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                            Connect Notion
                                        </Button>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Legacy URL tab - hidden but kept for backward compat */}
                        {activeTab === 'url' && (
                            <div className="space-y-2">
                                <label className="text-sm font-medium leading-none">Web Page URL</label>
                                <Input key="url-input" placeholder="https://example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
                            </div>
                        )}

                        <AnimatePresence>
                            {loading && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="pt-2"
                                >
                                    <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                                        <motion.div
                                            className="h-full bg-slate-900"
                                            initial={{ width: 0 }}
                                            animate={{ width: `${progress}%` }}
                                            transition={{ duration: 0.3 }}
                                        />
                                    </div>
                                    <p className="text-xs text-center text-slate-500 mt-1">
                                        {progress < 100 ? "Queueing ingestion..." : "Done!"}
                                    </p>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {activeTab !== 'notion' && (
                            <div className="flex justify-end gap-2 pt-2">
                                <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
                                <Button type="submit" disabled={loading}>{loading ? "Processing..." : "Ingest"}</Button>
                            </div>
                        )}

                        {/* Notion Close Button */}
                        {activeTab === 'notion' && (
                            <div className="flex justify-end gap-2 pt-2">
                                <Button type="button" variant="ghost" onClick={onClose}>Close</Button>
                            </div>
                        )}
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
