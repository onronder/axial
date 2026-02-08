'use client'

import { Button } from "@/components/ui/button"
import { DataSourceIcon } from "@/components/data-sources/DataSourceIcon"
import { getGoogleRedirectUri, getGoogleClientId } from "@/lib/utils"
import { toast } from "@/lib/toast"

export function GoogleConnectButton() {
    const handleConnect = () => {
        const clientId = getGoogleClientId();
        const redirectUri = getGoogleRedirectUri();

        if (process.env.NODE_ENV === 'development') {
            console.log('🔐 [Connect Button] Client ID:', clientId ? `${clientId.substring(0, 20)}...` : 'NOT SET');
            console.log('🔐 [Connect Button] Redirect URI:', redirectUri);
        }

        if (!clientId) {
            if (process.env.NODE_ENV !== 'production') {
                console.error('🔐 [Connect Button] ❌ NEXT_PUBLIC_GOOGLE_CLIENT_ID not configured');
            }
            toast({ title: "Configuration Error", description: "Google Client ID is not configured.", variant: "destructive" });
            return;
        }

        if (!redirectUri) {
            if (process.env.NODE_ENV !== 'production') {
                console.error('🔐 [Connect Button] ❌ Redirect URI not available');
            }
            toast({ title: "Configuration Error", description: "OAuth redirect URI is not configured.", variant: "destructive" });
            return;
        }

        const scope = 'https://www.googleapis.com/auth/drive.readonly';
        const params = new URLSearchParams({
            client_id: clientId,
            redirect_uri: redirectUri,
            response_type: 'code',
            scope: scope,
            access_type: 'offline',
            prompt: 'consent',
            include_granted_scopes: 'true'
        });

        const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
        if (process.env.NODE_ENV !== 'production') {
            console.log('🔐 [Connect Button] Redirecting to:', authUrl);
        }

        window.location.href = authUrl;
    }

    return (
        <Button onClick={handleConnect} variant="outline" className="w-full gap-2">
            <DataSourceIcon sourceId="google-drive" size="sm" />
            Connect Google Drive
        </Button>
    )
}
