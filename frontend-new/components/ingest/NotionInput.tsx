'use client'

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { HelpCircle } from "lucide-react"

interface NotionInputProps {
    token: string
    pageId: string
    onTokenChange: (value: string) => void
    onPageIdChange: (value: string) => void
}

export function NotionInput({ token, pageId, onTokenChange, onPageIdChange }: NotionInputProps) {
    const [showTokenHelp, setShowTokenHelp] = useState(false)

    return (
        <div className="space-y-4">
            {/* Integration Token */}
            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <label className="text-sm font-medium leading-none">
                        Integration Token
                    </label>
                    <button
                        type="button"
                        onClick={() => setShowTokenHelp(!showTokenHelp)}
                        className="text-slate-400 hover:text-slate-600 transition-colors"
                        title="How to get a Notion Token?"
                    >
                        <HelpCircle className="h-4 w-4" />
                    </button>
                </div>
                <Input
                    type="password"
                    placeholder="secret_xxxxxxxxxxxxx"
                    value={token}
                    onChange={(e) => onTokenChange(e.target.value)}
                    autoComplete="off"
                />
                {showTokenHelp && (
                    <div className="text-xs text-slate-500 bg-slate-50 p-3 rounded-md space-y-1">
                        <p className="font-medium">How to get a Notion Token:</p>
                        <ol className="list-decimal list-inside space-y-1 ml-1">
                            <li>Go to <a href="https://www.notion.so/my-integrations" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">notion.so/my-integrations</a></li>
                            <li>Click &quot;New integration&quot;</li>
                            <li>Give it a name and select a workspace</li>
                            <li>Copy the &quot;Internal Integration Token&quot;</li>
                            <li>Share the page with your integration</li>
                        </ol>
                    </div>
                )}
            </div>

            {/* Page ID */}
            <div className="space-y-2">
                <label className="text-sm font-medium leading-none">
                    Page ID
                </label>
                <Input
                    type="text"
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    value={pageId}
                    onChange={(e) => onPageIdChange(e.target.value)}
                />
                <p className="text-xs text-slate-500">
                    Find it in the page URL: notion.so/Your-Page-<span className="font-mono bg-slate-100 px-1 rounded">PageID</span>
                </p>
            </div>
        </div>
    )
}
