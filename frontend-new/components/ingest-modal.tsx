'use client'

import { useState } from "react"
import { X, Upload, Link as LinkIcon, FileText, CheckCircle, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { authFetch } from "@/lib/api"
import { cn } from "@/lib/utils"

interface IngestModalProps {
    isOpen: boolean
    onClose: () => void
}

export function IngestModal({ isOpen, onClose }: IngestModalProps) {
    const [activeTab, setActiveTab] = useState<'file' | 'url'>('file')
    const [file, setFile] = useState<File | null>(null)
    const [url, setUrl] = useState<string>("") // Explicit type for hygiene
    const [loading, setLoading] = useState(false)
    const [status, setStatus] = useState<{ type: 'success' | 'error' | null, message: string }>({ type: null, message: "" })

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
            if (activeTab === 'file') {
                if (!file) {
                    setLoading(false)
                    return
                }
                const formData = new FormData()
                formData.append("file", file)
                formData.append("metadata", JSON.stringify({ client_id: "frontend_user" }))

                // Note: authFetch is mainly for JSON. FormData requires special handling (no Content-Type header so browser sets boundary).
                // We'll use specific fetch here or adapt authFetch. 
                // Adapting logic here to ensure headers are correct.

                // Re-implementing simplified auth fetch for FormData to avoid header conflict
                // TODO: ideally refactor api.ts to handle FormData
                // switch to SSR client to ensure we get the correct cookie-based session
                const { createClient } = await import("@/lib/supabase/client")
                const supabase = createClient()
                const { data: { session } } = await supabase.auth.getSession()
                const token = session?.access_token

                if (!token) {
                    console.error("No token found in session")
                    throw new Error("Not authenticated")
                }

                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/ingest`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                        // Details: Do NOT set Content-Type for FormData
                    },
                    body: formData
                })

                if (!res.ok) {
                    const err = await res.json()
                    throw new Error(err.detail || "Upload failed")
                }

            } else {
                if (!url) {
                    setLoading(false)
                    return
                }

                // Using URLSearchParams to match backend 'Form' expectation for 'url' field.
                // Note: The user prompt asked for JSON, but the existing backend (ingest_document) 
                // uses `url: Optional[str] = Form(None)`, which requires application/x-www-form-urlencoded or multipart/form-data.
                // Sending JSON would result in 422. We stick to this for compatibility.
                // Using FormData even for URL to match backend Multipart expectation
                const formData = new FormData()
                formData.append("url", url)
                formData.append("metadata", JSON.stringify({ client_id: "frontend_user", source: "web_crawl" }))

                await authFetch('/ingest', {
                    method: 'POST',
                    body: formData
                    // No headers needed, api.ts detects FormData and removes Content-Type
                })
            }

            setStatus({ type: 'success', message: "Ingestion queued successfully!" })
            setFile(null)
            setUrl("")
            if (activeTab === 'file') {
                // Reset file input visually if needed
            }

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

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4" onClick={handleBackdropClick}>
            <Card className="w-full max-w-md relative animate-in fade-in zoom-in-95 duration-200">
                <button
                    onClick={onClose}
                    className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                    <X className="h-4 w-4" />
                    <span className="sr-only">Close</span>
                </button>
                <CardHeader>
                    <CardTitle>Add Data Source</CardTitle>
                </CardHeader>
                <CardContent>
                    {/* Tabs */}
                    <div className="flex w-full rounded-md border p-1 mb-6 bg-slate-100">
                        <button
                            onClick={() => setActiveTab('file')}
                            className={cn(
                                "flex-1 rounded-sm px-3 py-1.5 text-sm font-medium transition-all",
                                activeTab === 'file' ? "bg-white text-slate-950 shadow-sm" : "text-slate-500 hover:text-slate-900"
                            )}
                        >
                            <div className="flex items-center justify-center gap-2">
                                <Upload className="h-4 w-4" />
                                <span>Upload File</span>
                            </div>
                        </button>
                        <button
                            onClick={() => setActiveTab('url')}
                            className={cn(
                                "flex-1 rounded-sm px-3 py-1.5 text-sm font-medium transition-all",
                                activeTab === 'url' ? "bg-white text-slate-950 shadow-sm" : "text-slate-500 hover:text-slate-900"
                            )}
                        >
                            <div className="flex items-center justify-center gap-2">
                                <LinkIcon className="h-4 w-4" />
                                <span>Add URL</span>
                            </div>
                        </button>
                    </div>

                    {/* Content */}
                    <form onSubmit={handleSubmit} className="space-y-4">
                        {activeTab === 'file' ? (
                            <div className="grid w-full items-center gap-1.5">
                                <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                                    Select Document (PDF, TXT, MD)
                                </label>
                                <Input key="file-input" type="file" onChange={handleFileChange} />
                                {file && <p className="text-xs text-slate-500">Selected: {file.name}</p>}
                            </div>
                        ) : (
                            <div className="space-y-2">
                                <label className="text-sm font-medium leading-none">
                                    Web Page URL
                                </label>
                                <Input
                                    key="url-input"
                                    placeholder="https://example.com"
                                    value={url}
                                    onChange={(e) => setUrl(e.target.value)}
                                />
                            </div>
                        )}

                        {status.message && (
                            <div className={cn(
                                "flex items-center gap-2 p-3 rounded-md text-sm",
                                status.type === 'success' ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
                            )}>
                                {status.type === 'success' ? <CheckCircle className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                                {status.message}
                            </div>
                        )}

                        <div className="flex justify-end gap-2 pt-2">
                            <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
                            <Button type="submit" disabled={loading}>
                                {loading ? "Processing..." : "Ingest"}
                            </Button>
                        </div>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
