'use client'

import { Button } from "@/components/ui/button"
import { HardDrive } from "lucide-react"

export function GoogleConnectButton() {
    const handleConnect = () => {
        const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID
        const redirectUri = process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI || "http://localhost:3000/dashboard"
        const scope = 'https://www.googleapis.com/auth/drive.readonly'

        if (!clientId) {
            alert("Google Client ID is not configured.")
            return
        }

        const params = new URLSearchParams({
            client_id: clientId,
            redirect_uri: redirectUri,
            response_type: 'code',
            scope: scope,
            access_type: 'offline', // Critical for refresh token
            prompt: 'consent', // Critical to force refresh token
            include_granted_scopes: 'true'
        })

        window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`
    }

    return (
        <Button onClick={handleConnect} variant="outline" className="w-full gap-2">
            <HardDrive className="h-4 w-4" />
            Connect Google Drive
        </Button>
    )
}
