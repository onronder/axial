"use client"

import { useEffect, useState, useCallback } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { BookOpen, CheckCircle, Globe, Loader2, Upload, X } from "lucide-react"

import { IngestionProgressModal } from "@/components/ingestion/IngestionProgressModal"
// NotionInput removed - using OAuth flow now
import { WebInput, validateUrl } from "@/components/ingest/WebInput"
import { useDataSources } from "@/hooks/useDataSources"
import { useFileStatus } from "@/hooks/useFileStatus"
import { useToast } from "@/hooks/use-toast"
import { useProfile } from "@/hooks/useProfile"
import { useUsage } from "@/hooks/useUsage"
import { authFetch, getUploadUrl, ingestFileReference, uploadToStorage } from "@/lib/api"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

type TabType = 'file' | 'url' | 'website' | 'notion'

interface IngestModalProps {
    isOpen: boolean
    onClose: () => void
    initialTab?: TabType
}

export function IngestModal({ isOpen, onClose, initialTab = 'file' }: IngestModalProps) {
    const queryClient = useQueryClient()
    const [activeTab, setActiveTab] = useState<TabType>(initialTab)
    const [file, setFile] = useState<File | null>(null)
    const [url, setUrl] = useState<string>("")

    // Website tab state
    const [websiteUrl, setWebsiteUrl] = useState<string>("")

    // Hook for Data Sources (OAuth)
    const { connect, isConnected, loading: dsLoading } = useDataSources()
    const isNotionConnected = isConnected('notion')
    const { toast } = useToast()
    const { profile } = useProfile()
    const { canWebCrawl, refresh } = useUsage()
    const isWebCrawlLocked = !canWebCrawl
    const isViewer = profile?.role === "viewer"

    const [loading, setLoading] = useState(false)
    const [currentJobId, setCurrentJobId] = useState<string | null>(null)

    // Track job status for unified ingestion progress
    const { files: fileStatuses } = useFileStatus(currentJobId)

    /**
     * Called when all files in the ingestion job have finished processing.
     * Refreshes usage stats and invalidates document cache to update UI.
     */
    const handleIngestionComplete = useCallback(() => {
        console.log("📊 [IngestModal] Ingestion complete - refreshing data...")
        
        // Refresh usage stats (file count, storage) in sidebar
        refresh(true)
        
        // Invalidate documents cache so Knowledge Base table updates
        queryClient.invalidateQueries({ queryKey: ["documents"] })
        queryClient.invalidateQueries({ queryKey: ["documentCount"] })
    }, [refresh, queryClient])

    // Sync activeTab when initialTab changes
    useEffect(() => {
        setActiveTab(initialTab)
    }, [initialTab])

    if (!isOpen) return null

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0])
        }
    }

    const handleNotionConnect = () => {
        if (isViewer) {
            toast({
                title: "View only",
                description: "You need editor or admin access to connect data sources.",
                variant: "destructive",
            })
            return
        }
        connect('notion')
        // OAuth redirect will happen, no need to set loading here managed by hook
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (isViewer) {
            toast({
                title: "View only",
                description: "You need editor or admin access to ingest data.",
                variant: "destructive",
            })
            return
        }

        if ((activeTab === 'website' || activeTab === 'url') && isWebCrawlLocked) {
            toast({
                title: "Upgrade required",
                description: "Web crawling is available on Starter and above plans.",
                variant: "destructive",
            })
            return
        }

        // If Notion tab, we don't submit via this form anymore
        if (activeTab === 'notion') {
            return
        }

        setLoading(true)

        try {
            let ingestionJobId: string | null = null

            if (activeTab === 'file') {
                if (!file) {
                    return
                }
                const uploadUrl = await getUploadUrl(file.name, file.type || "application/octet-stream", file.size)
                const uploaded = await uploadToStorage(uploadUrl.upload_url, file)
                if (!uploaded) {
                    throw new Error("Failed to upload file to storage")
                }
                const ingestionResponse = await ingestFileReference(
                    uploadUrl.storage_path,
                    file.name,
                    file.size,
                    { client_id: "frontend_user" }
                )
                ingestionJobId = ingestionResponse?.job_id ?? null
            } else if (activeTab === 'url' || activeTab === 'website') {
                const targetUrl = activeTab === 'website' ? websiteUrl : url
                if (!targetUrl) {
                    return
                }

                // Validate URL
                if (!validateUrl(targetUrl)) {
                    throw new Error("Please enter a valid URL starting with http:// or https://")
                }
                const crawlType = activeTab === 'website' ? 'sitemap' : 'single'
                const { data } = await authFetch.post('/integrations/web/crawl', {
                    url: targetUrl,
                    crawl_type: crawlType,
                    max_depth: 1,
                    respect_robots: true,
                    allow_subdomains: false
                })

                ingestionJobId = data?.job_id || data?.crawl_id || null
            }

            if (ingestionJobId) {
                setCurrentJobId(ingestionJobId)
            }

            // Robust error handling: Check content type
            // Axios-based calls throw on non-2xx; fetch path removed for web crawl.

            toast({
                title: "Ingestion Queued",
                description: activeTab === 'file' ? "Your file is being processed." : "The URL has been added to the crawl queue.",
                variant: "default",
                className: "bg-green-50 border-green-200 text-green-900",
            })

            // Reset form but keep modal open so progress modal can display
            setFile(null)
            setUrl("")
            setWebsiteUrl("")

        } catch (err) {
            const message = err instanceof Error ? err.message : "Something went wrong. Please try again."
            console.error(message)
            toast({
                title: "Ingestion Failed",
                description: message,
                variant: "destructive",
            })
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
    const isActionDisabled = loading || isViewer || (activeTab === 'website' && isWebCrawlLocked)

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
                                <Input key="file-input" type="file" onChange={handleFileChange} disabled={isViewer} />
                                {file && <p className="text-xs text-slate-500">Selected: {file.name}</p>}
                            </div>
                        )}

                        {activeTab === 'website' && (
                            <div className="space-y-2">
                                <WebInput
                                    url={websiteUrl}
                                    onUrlChange={setWebsiteUrl}
                                    disabled={isWebCrawlLocked || loading}
                                />
                                {isWebCrawlLocked && (
                                    <p className="text-xs text-amber-500">
                                        Web crawling is locked on your current plan. Upgrade to Starter or Pro to enable site ingestion.
                                    </p>
                                )}
                            </div>
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
                                            disabled={dsLoading || isViewer}
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

                        {activeTab !== 'notion' && (
                            <div className="flex justify-end gap-2 pt-2">
                                <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
                                <Button type="submit" disabled={isActionDisabled}>
                                    {loading ? "Processing..." : isWebCrawlLocked && activeTab === 'website' ? "Upgrade to unlock" : "Ingest"}
                                </Button>
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

            {/* Unified Ingestion Progress */}
            {currentJobId && (
                <IngestionProgressModal
                    jobId={currentJobId}
                    files={fileStatuses}
                    totalFiles={fileStatuses.length}
                    overallProgress={
                        fileStatuses.length > 0
                            ? (fileStatuses.filter((f) => f.status === "completed").length / fileStatuses.length) * 100
                            : 0
                    }
                    onClose={() => setCurrentJobId(null)}
                    onComplete={handleIngestionComplete}
                />
            )}
        </div>
    )
}
