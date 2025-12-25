'use client'

import { Input } from "@/components/ui/input"

interface WebInputProps {
    url: string
    onUrlChange: (value: string) => void
    error?: string
}

// Simple URL validation regex
const URL_REGEX = /^https?:\/\/.+\..+/

export function validateUrl(url: string): boolean {
    return URL_REGEX.test(url)
}

export function WebInput({ url, onUrlChange, error }: WebInputProps) {
    const isValid = url === '' || validateUrl(url)

    return (
        <div className="space-y-2">
            <label className="text-sm font-medium leading-none">
                Web Page URL
            </label>
            <Input
                type="url"
                placeholder="https://example.com/article"
                value={url}
                onChange={(e) => onUrlChange(e.target.value)}
                className={!isValid ? 'border-red-500 focus-visible:ring-red-500' : ''}
            />
            {!isValid && (
                <p className="text-xs text-red-500">
                    Please enter a valid URL starting with http:// or https://
                </p>
            )}
            {error && (
                <p className="text-xs text-red-500">{error}</p>
            )}
            <p className="text-xs text-slate-500">
                Enter the full URL of the web page you want to ingest.
            </p>
        </div>
    )
}
