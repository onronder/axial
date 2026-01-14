"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { getMicrosoftRedirectUri, getMicrosoftTenantId } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type Provider = "google" | "notion" | "onedrive" | "sharepoint" | "dropbox";

type ApiError = {
    response?: {
        data?: {
            detail?: string;
        };
    };
    message?: string;
};

type DebugInfo = {
    provider: Provider;
    tenantId: string;
    redirectUri: string;
    pkcePresent: boolean;
    pkceLength: number;
};

function OAuthCallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
    const [error, setError] = useState<string | null>(null);
    const [provider, setProvider] = useState<Provider>("google");
    const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null);
    const [showDebug, setShowDebug] = useState(false);

    useEffect(() => {
        const code = searchParams.get("code");
        const errorParam = searchParams.get("error");
        const errorDescription = searchParams.get("error_description");
        const errorCodes = searchParams.get("error_codes");
        const stateParam = searchParams.get("state");

        // Detect provider from state parameter (set during OAuth init)
        const detectedProvider: Provider =
            stateParam === "notion"
                ? "notion"
                : stateParam === "onedrive"
                    ? "onedrive"
                    : stateParam === "sharepoint"
                        ? "sharepoint"
                        : stateParam === "dropbox"
                            ? "dropbox"
                            : "google";
        setProvider(detectedProvider);

        if (typeof window !== "undefined") {
            const isMicrosoft = detectedProvider === "onedrive" || detectedProvider === "sharepoint";
            const seenDebug = sessionStorage.getItem("oauth_debug_seen") === "1";
            if (isMicrosoft && !seenDebug) {
                const pkceKey = `microsoft_pkce_${detectedProvider}`;
                const codeVerifier = sessionStorage.getItem(pkceKey);
                const redirectUri = getMicrosoftRedirectUri() || "unknown";
                const tenantId = getMicrosoftTenantId();
                setDebugInfo({
                    provider: detectedProvider,
                    tenantId,
                    redirectUri,
                    pkcePresent: !!codeVerifier,
                    pkceLength: codeVerifier?.length || 0,
                });
                setShowDebug(true);
                sessionStorage.setItem("oauth_debug_seen", "1");
            }
        }

        console.log("🔐 [OAuth Callback] Starting...");
        console.log("🔐 [OAuth Callback] Provider:", detectedProvider);
        console.log("🔐 [OAuth Callback] Code:", code ? `${code.substring(0, 20)}...` : null);
        console.log("🔐 [OAuth Callback] Error:", errorParam);
        console.log("🔐 [OAuth Callback] Error Description:", errorDescription);
        console.log("🔐 [OAuth Callback] Error Codes:", errorCodes);

        if (errorParam) {
            setStatus("error");
            const friendly =
                errorParam === "access_denied"
                    ? "Access was denied"
                    : errorDescription || errorParam;
            setError(friendly);
            return;
        }

        if (!code) {
            setStatus("error");
            setError("No authorization code received");
            return;
        }

        // Exchange the code for tokens
        const exchangeCode = async () => {
            try {
                console.log(`🔐 [OAuth Callback] Sending code to backend for ${detectedProvider}...`);

                // Call the appropriate endpoint based on provider
                let response;
                if (detectedProvider === "notion") {
                    response = await api.post("/integrations/notion/exchange", { code });
                } else if (detectedProvider === "onedrive" || detectedProvider === "sharepoint") {
                    const pkceKey = `microsoft_pkce_${detectedProvider}`;
                    const codeVerifier = sessionStorage.getItem(pkceKey);
                    if (!codeVerifier) {
                        setStatus("error");
                        setError("Missing PKCE verifier. Please retry the connection.");
                        return;
                    }
                    response = await api.post("/integrations/microsoft/exchange", {
                        code,
                        target_type: detectedProvider,
                        code_verifier: codeVerifier,
                    });
                    sessionStorage.removeItem(pkceKey);
                } else if (detectedProvider === "dropbox") {
                    response = await api.post("/integrations/dropbox/exchange", { code });
                } else {
                    response = await api.post("/integrations/google/exchange", { code });
                }
                console.log("🔐 [OAuth Callback] ✅ Success:", response.data);
                setStatus("success");

                // Redirect to data sources after short delay
                setTimeout(() => {
                    router.push("/dashboard/settings/data-sources");
                }, 2000);
            } catch (err: unknown) {
                const apiError = err as ApiError;
                console.error("🔐 [OAuth Callback] ❌ Token exchange failed:", apiError.response?.data || apiError.message);
                setStatus("error");
                let providerName = "Google Drive";
                if (detectedProvider === "notion") {
                    providerName = "Notion";
                } else if (detectedProvider === "onedrive") {
                    providerName = "OneDrive";
                } else if (detectedProvider === "sharepoint") {
                    providerName = "SharePoint";
                } else if (detectedProvider === "dropbox") {
                    providerName = "Dropbox";
                }
                setError(apiError.response?.data?.detail || `Failed to connect ${providerName}`);
            }
        };

        exchangeCode();
    }, [searchParams, router]);

    let providerName = "Google Drive";
    if (provider === "notion") {
        providerName = "Notion";
    } else if (provider === "onedrive") {
        providerName = "OneDrive";
    } else if (provider === "sharepoint") {
        providerName = "SharePoint";
    } else if (provider === "dropbox") {
        providerName = "Dropbox";
    }

    return (
        <div className="flex min-h-screen items-center justify-center p-4 bg-background">
            <div className="w-full max-w-md space-y-4">
                {showDebug && debugInfo && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
                        <div className="flex items-center justify-between">
                            <span className="font-semibold">OAuth Debug (One-Time)</span>
                            <button
                                className="text-xs font-medium underline underline-offset-2"
                                onClick={() => setShowDebug(false)}
                                type="button"
                            >
                                Dismiss
                            </button>
                        </div>
                        <div className="mt-2 space-y-1">
                            <div>
                                <span className="font-medium">Provider:</span> {debugInfo.provider}
                            </div>
                            <div>
                                <span className="font-medium">Tenant:</span> {debugInfo.tenantId}
                            </div>
                            <div>
                                <span className="font-medium">Redirect URI:</span> {debugInfo.redirectUri}
                            </div>
                            <div>
                                <span className="font-medium">PKCE:</span>{" "}
                                {debugInfo.pkcePresent ? "present" : "missing"} (len {debugInfo.pkceLength})
                            </div>
                        </div>
                    </div>
                )}

                <Card>
                <CardHeader className="text-center">
                    <div className="mx-auto mb-4">
                        {status === "loading" && (
                            <Loader2 className="h-12 w-12 animate-spin text-primary" />
                        )}
                        {status === "success" && (
                            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
                                <CheckCircle className="h-8 w-8 text-green-600" />
                            </div>
                        )}
                        {status === "error" && (
                            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
                                <XCircle className="h-8 w-8 text-red-600" />
                            </div>
                        )}
                    </div>
                    <CardTitle>
                        {status === "loading" && `Connecting ${providerName}...`}
                        {status === "success" && `${providerName} Connected!`}
                        {status === "error" && "Connection Failed"}
                    </CardTitle>
                    <CardDescription>
                        {status === "loading" && "Please wait while we complete the connection."}
                        {status === "success" && "Redirecting to Data Sources..."}
                        {status === "error" && error}
                    </CardDescription>
                </CardHeader>
                {status === "error" && (
                    <CardContent className="flex justify-center gap-4">
                        <Button variant="outline" onClick={() => router.push("/dashboard/settings/data-sources")}>
                            Go Back
                        </Button>
                        <Button onClick={() => router.push("/dashboard/settings/data-sources")}>
                            Try Again
                        </Button>
                    </CardContent>
                )}
                </Card>
            </div>
        </div>
    );
}

export default function OAuthCallbackPage() {
    return (
        <Suspense fallback={
            <div className="flex min-h-screen items-center justify-center p-4 bg-background">
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
            </div>
        }>
            <OAuthCallbackContent />
        </Suspense>
    );
}
