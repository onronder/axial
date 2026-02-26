"use client"

import { useEffect, useState } from "react"
import { BookOpen, CheckCircle, Globe, Upload, X, Youtube, AlertCircle } from "lucide-react"

// NotionInput removed - using OAuth flow now
import { WebInput, validateUrl } from "@/components/ingest/WebInput"
import { useDataSources } from "@/hooks/useDataSources"
import { useIngestionProgress } from "@/hooks/useIngestionProgress"
import { useToast } from "@/hooks/use-toast"
import { useProfile } from "@/hooks/useProfile"
import { useUsage } from "@/hooks/useUsage"
import { authFetch, getUploadUrl, ingestFileReference, uploadToStorage } from "@/lib/api"
import { extractErrorMessage } from "@/lib/error-handling"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { 
    isValidYoutubeUrl, 
    normalizeYoutubeUrl, 
    YOUTUBE_ERROR_MESSAGES 
} from "@/lib/youtube-utils"
import { ROLE_TOAST_TITLES, ROLE_MESSAGES } from "@/lib/role-messages"

import { Spinner } from "@/components/ui/spinner";
type TabType = 'file' | 'url' | 'website' | 'notion' | 'youtube'

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

    // YouTube tab state
    const [youtubeUrl, setYoutubeUrl] = useState<string>("")
    const [youtubeValidationError, setYoutubeValidationError] = useState<string | null>(null)

    // Hook for Data Sources (OAuth)
    const { connect, isConnected, loading: dsLoading } = useDataSources()
    const isNotionConnected = isConnected('notion')
    const { toast } = useToast()
    const { profile } = useProfile()
    const { canWebCrawl } = useUsage()
    const isWebCrawlLocked = !canWebCrawl
    const isViewer = profile?.role === "viewer"

    const [loading, setLoading] = useState(false)
    
    // Use centralized ingestion progress context - GlobalProgress renders the UI
    const { registerJob } = useIngestionProgress()

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
                title: ROLE_TOAST_TITLES.VIEW_ONLY,
                description: ROLE_MESSAGES.NEED_EDITOR_CONNECT,
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
                title: ROLE_TOAST_TITLES.VIEW_ONLY,
                description: ROLE_MESSAGES.NEED_EDITOR_INGEST,
                variant: "destructive",
            })
            return
        }

        if ((activeTab === 'website' || activeTab === 'url') && isWebCrawlLocked) {
            toast({
                title: ROLE_TOAST_TITLES.UPGRADE_REQUIRED,
                description: ROLE_MESSAGES.WEB_CRAWL_UPGRADE,
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
            } else if (activeTab === 'youtube') {
                if (!youtubeUrl) {
                    return
                }

                // Validate YouTube URL specifically
                if (!isValidYoutubeUrl(youtubeUrl)) {
                    setYoutubeValidationError(YOUTUBE_ERROR_MESSAGES.INVALID_URL)
                    throw new Error(YOUTUBE_ERROR_MESSAGES.INVALID_URL_DETAILED)
                }

                // Normalize and send to web backend (backend detects YouTube and fetches transcript)
                const normalizedUrl = normalizeYoutubeUrl(youtubeUrl)
                const { data } = await authFetch.post('/integrations/web/crawl', {
                    url: normalizedUrl,
                    crawl_type: 'single',
                    max_depth: 1,
                    respect_robots: true,
                    allow_subdomains: false
                })

                ingestionJobId = data?.job_id || data?.crawl_id || null
            }

            if (ingestionJobId) {
                // Register job with centralized context - GlobalProgress will show UI
                registerJob(ingestionJobId)
            }

            // Robust error handling: Check content type
            // Axios-based calls throw on non-2xx; fetch path removed for web crawl.

            // Show appropriate success message based on tab
            const toastDescriptions: Record<string, string> = {
                file: "Your file is being processed.",
                youtube: "Fetching transcript and processing video content...",
                website: "The website has been added to the crawl queue.",
                url: "The URL has been added to the crawl queue.",
            }
            
            toast({
                title: "Ingestion Queued",
                description: toastDescriptions[activeTab] || "Your content is being processed.",
                variant: "default",
                className: "bg-green-50 border-green-200 text-green-900",
            })

            // Reset form but keep modal open so progress modal can display
            setFile(null)
            setUrl("")
            setWebsiteUrl("")
            setYoutubeUrl("")
            setYoutubeValidationError(null)

        } catch (err) {
            const message = extractErrorMessage(err, "Something went wrong. Please try again.")
            if (process.env.NODE_ENV !== 'production') {
                console.error(message)
            }
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
        { id: 'youtube' as const, label: 'YouTube', icon: Youtube },
        { id: 'website' as const, label: 'Website', icon: Globe },
        { id: 'notion' as const, label: 'Notion', icon: BookOpen },
    ]
    const isActionDisabled = loading || isViewer || ((activeTab === 'website' || activeTab === 'youtube') && isWebCrawlLocked)

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" onClick={handleBackdropClick}>
            <Card className="w-full max-w-md relative animate-in fade-in zoom-in-95 duration-200">
                <button onClick={onClose} className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 cursor-pointer">
                    <X className="h-4 w-4" />
                    <span className="sr-only">Close</span>
                </button>
                <CardHeader>
                    <CardTitle>Add Data Source</CardTitle>
                </CardHeader>
                <CardContent>
                    {/* Tabs */}
                    <div className="flex w-full rounded-md border p-1 mb-6 bg-muted">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={cn(
                                    "flex-1 rounded-sm px-3 py-1.5 text-sm font-medium transition-all cursor-pointer",
                                    activeTab === tab.id
                                        ? "bg-background text-foreground shadow-sm"
                                        : "text-muted-foreground hover:text-foreground"
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
                                {file && <p className="text-xs text-muted-foreground">Selected: {file.name}</p>}
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

                        {activeTab === 'youtube' && (
                            <div className="space-y-3">
                                <div className="flex items-center gap-3 p-3 rounded-lg bg-red-50 dark:bg-red-500/10 border border-red-100 dark:border-red-500/20">
                                    <Youtube className="h-5 w-5 text-red-500 shrink-0" />
                                    <div className="text-sm text-muted-foreground">
                                        Paste a YouTube video URL to transcribe and chat with the content.
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <label className="text-sm font-medium leading-none">YouTube Video URL</label>
                                    <div className="relative">
                                        <Input
                                            key="youtube-input"
                                            type="url"
                                            placeholder="https://youtube.com/watch?v=..."
                                            value={youtubeUrl}
                                            onChange={(e) => {
                                                setYoutubeUrl(e.target.value)
                                                if (youtubeValidationError) setYoutubeValidationError(null)
                                            }}
                                            disabled={isWebCrawlLocked || loading}
                                            className={cn(youtubeValidationError && "border-destructive")}
                                            aria-invalid={!!youtubeValidationError}
                                        />
                                        {youtubeValidationError && (
                                            <AlertCircle className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-destructive" />
                                        )}
                                    </div>
                                    {youtubeValidationError && (
                                        <p className="text-xs text-destructive flex items-center gap-1">
                                            <AlertCircle className="h-3 w-3" />
                                            {youtubeValidationError}
                                        </p>
                                    )}
                                    <p className="text-xs text-muted-foreground">
                                        Supports youtube.com/watch, youtu.be, and shorts URLs.
                                    </p>
                                </div>
                                {isWebCrawlLocked && (
                                    <p className="text-xs text-amber-500">
                                        YouTube ingestion requires Starter or Pro plan.
                                    </p>
                                )}
                            </div>
                        )}

                        {activeTab === 'notion' && (
                            <div className="flex flex-col items-center justify-center py-6 space-y-4 text-center border rounded-lg bg-muted/50">
                                <BookOpen className={cn("h-12 w-12", isNotionConnected ? "text-green-500" : "text-muted-foreground/50")} />

                                {isNotionConnected ? (
                                    <div className="space-y-2">
                                        <h3 className="font-semibold text-foreground flex items-center justify-center gap-2">
                                            <CheckCircle className="h-4 w-4 text-green-500" />
                                            Notion Connected
                                        </h3>
                                        <p className="text-sm text-muted-foreground max-w-[260px] mx-auto">
                                            Your Notion workspace is synced. All accessible pages will be automatically ingested.
                                        </p>
                                        <div className="pt-2">
                                            <Button variant="outline" size="sm" onClick={() => window.open('https://notion.so/my-integrations', '_blank', 'noopener,noreferrer')} className="text-xs">
                                                Manage in Notion
                                            </Button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        <h3 className="font-medium text-foreground">Connect Notion Workspace</h3>
                                        <p className="text-sm text-muted-foreground max-w-[280px] mx-auto">
                                            Connect your workspace to automatically import and sync pages.
                                        </p>
                                        <Button
                                            type="button"
                                            onClick={handleNotionConnect}
                                            disabled={dsLoading || isViewer}
                                            className="bg-foreground text-background hover:bg-foreground/90"
                                        >
                                            {dsLoading && <Spinner className="mr-2 h-4 w-4 animate-spin" />}
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
            {/* Progress UI is now rendered by GlobalProgress - single source of truth */}
        </div>
    )
}
