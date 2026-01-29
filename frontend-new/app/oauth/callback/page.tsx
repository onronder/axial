
"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { getMicrosoftRedirectUri, getMicrosoftTenantId } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { GitHubRepoSelector } from "@/components/data-sources/GitHubRepoSelector";
import { Spinner } from "@/components/ui/spinner";

// =============================================================================
// Types & Constants
// =============================================================================

type Provider = "google" | "notion" | "onedrive" | "sharepoint" | "dropbox" | "github" | "box";
type Status = "loading" | "success" | "error";

interface ApiError {
    response?: {
        data?: {
            detail?: string;
        };
    };
    message?: string;
}

interface DebugInfo {
    provider: Provider;
    tenantId: string;
    redirectUri: string;
    pkcePresent: boolean;
    pkceLength: number;
}

/**
 * Provider configuration mapping
 * Maps state parameter to provider type and display name
 */
const PROVIDER_CONFIG: Record<string, { type: Provider; name: string; endpoint: string }> = {
    notion: { type: "notion", name: "Notion", endpoint: "/integrations/notion/exchange" },
    onedrive: { type: "onedrive", name: "OneDrive", endpoint: "/integrations/microsoft/exchange" },
    sharepoint: { type: "sharepoint", name: "SharePoint", endpoint: "/integrations/microsoft/exchange" },
    dropbox: { type: "dropbox", name: "Dropbox", endpoint: "/integrations/dropbox/exchange" },
    github: { type: "github", name: "GitHub", endpoint: "/integrations/github/exchange" },
    box: { type: "box", name: "Box", endpoint: "/integrations/box/exchange" },
    google: { type: "google", name: "Google Drive", endpoint: "/integrations/google/exchange" },
};

const DEFAULT_PROVIDER = PROVIDER_CONFIG.google;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Detect provider from state parameter
 */
function detectProvider(stateParam: string | null): { type: Provider; name: string; endpoint: string } {
    if (!stateParam) return DEFAULT_PROVIDER;
    return PROVIDER_CONFIG[stateParam] || DEFAULT_PROVIDER;
}

/**
 * Check if provider requires PKCE (Microsoft providers)
 */
function requiresPkce(provider: Provider): boolean {
    return provider === "onedrive" || provider === "sharepoint";
}

// =============================================================================
// Main Component
// =============================================================================

function OAuthCallbackContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [status, setStatus] = useState<Status>("loading");
    const [error, setError] = useState<string | null>(null);
    const [providerConfig, setProviderConfig] = useState(DEFAULT_PROVIDER);
    const [debugInfo, setDebugInfo] = useState<DebugInfo | null>(null);
    const [showDebug, setShowDebug] = useState(false);
    const [showGitHubRepoSelector, setShowGitHubRepoSelector] = useState(false);

    useEffect(() => {
        const code = searchParams.get("code");
        const errorParam = searchParams.get("error");
        const errorDescription = searchParams.get("error_description");
        const stateParam = searchParams.get("state");

        // Detect provider from state parameter
        const config = detectProvider(stateParam);
        setProviderConfig(config);

        // Setup debug info for Microsoft providers (one-time display)
        if (typeof window !== "undefined" && requiresPkce(config.type)) {
            const seenDebug = sessionStorage.getItem("oauth_debug_seen") === "1";
            if (!seenDebug) {
                const pkceKey = `microsoft_pkce_${config.type}`;
                const codeVerifier = sessionStorage.getItem(pkceKey);
                setDebugInfo({
                    provider: config.type,
                    tenantId: getMicrosoftTenantId(),
                    redirectUri: getMicrosoftRedirectUri() || "unknown",
                    pkcePresent: !!codeVerifier,
                    pkceLength: codeVerifier?.length || 0,
                });
                setShowDebug(true);
                sessionStorage.setItem("oauth_debug_seen", "1");
            }
        }

        console.log("🔐 [OAuth Callback] Starting...");
        console.log("🔐 [OAuth Callback] Provider:", config.name);
        console.log("🔐 [OAuth Callback] Code:", code ? `${code.substring(0, 20)}...` : null);

        // Handle OAuth error from provider
        if (errorParam) {
            console.error("🔐 [OAuth Callback] Error from provider:", errorParam, errorDescription);
            setStatus("error");
            const friendly = errorParam === "access_denied"
                ? "Access was denied"
                : errorDescription || errorParam;
            setError(friendly);
            return;
        }

        // Validate authorization code
        if (!code) {
            setStatus("error");
            setError("No authorization code received");
            return;
        }

        // Exchange the code for tokens
        const exchangeCode = async () => {
            try {
                console.log(`🔐 [OAuth Callback] Exchanging code for ${config.name}...`);

                let payload: Record<string, string> = { code };

                // Handle PKCE for Microsoft providers
                if (requiresPkce(config.type)) {
                    const pkceKey = `microsoft_pkce_${config.type}`;
                    const codeVerifier = sessionStorage.getItem(pkceKey);
                    
                    if (!codeVerifier) {
                        setStatus("error");
                        setError("Missing PKCE verifier. Please retry the connection.");
                        return;
                    }
                    
                    payload = {
                        ...payload,
                        target_type: config.type,
                        code_verifier: codeVerifier,
                    };
                    
                    // Clean up PKCE verifier
                    sessionStorage.removeItem(pkceKey);
                }

                const response = await api.post(config.endpoint, payload);
                console.log("🔐 [OAuth Callback] ✅ Success:", response.data);
                setStatus("success");

                // Special handling for GitHub - show repo selector
                if (config.type === "github") {
                    console.log("🔐 [OAuth Callback] GitHub connected - showing repo selector");
                    setTimeout(() => {
                        setShowGitHubRepoSelector(true);
                    }, 1500);
                    return;
                }

                // Redirect to data sources after short delay
                setTimeout(() => {
                    router.push("/dashboard/settings/data-sources");
                }, 2000);

            } catch (err: unknown) {
                const apiError = err as ApiError;
                console.error("🔐 [OAuth Callback] ❌ Token exchange failed:", apiError.response?.data || apiError.message);
                setStatus("error");
                setError(apiError.response?.data?.detail || `Failed to connect ${config.name}`);
            }
        };

        exchangeCode();
    }, [searchParams, router]);

    return (
        <div className="flex min-h-screen items-center justify-center p-4 bg-background">
            <div className="w-full max-w-md space-y-4">
                {/* Debug Info Panel (Microsoft providers only, one-time) */}
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
                            <div><span className="font-medium">Provider:</span> {debugInfo.provider}</div>
                            <div><span className="font-medium">Tenant:</span> {debugInfo.tenantId}</div>
                            <div><span className="font-medium">Redirect URI:</span> {debugInfo.redirectUri}</div>
                            <div>
                                <span className="font-medium">PKCE:</span>{" "}
                                {debugInfo.pkcePresent ? "present" : "missing"} (len {debugInfo.pkceLength})
                            </div>
                        </div>
                    </div>
                )}

                {/* Main Status Card */}
                <Card>
                    <CardHeader className="text-center">
                        <div className="mx-auto mb-4">
                            {status === "loading" && (
                                <Spinner className="h-12 w-12 animate-spin text-primary" />
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
                            {status === "loading" && `Connecting ${providerConfig.name}...`}
                            {status === "success" && `${providerConfig.name} Connected!`}
                            {status === "error" && "Connection Failed"}
                        </CardTitle>
                        <CardDescription>
                            {status === "loading" && "Please wait while we complete the connection."}
                            {status === "success" && providerConfig.type === "github" && !showGitHubRepoSelector && "Loading repository selector..."}
                            {status === "success" && providerConfig.type !== "github" && "Redirecting to Data Sources..."}
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

                {/* GitHub Repository Selector Modal */}
                <GitHubRepoSelector
                    open={showGitHubRepoSelector}
                    onOpenChange={(open) => {
                        setShowGitHubRepoSelector(open);
                        if (!open) {
                            // If user closes modal without saving, redirect anyway
                            router.push("/dashboard/settings/data-sources");
                        }
                    }}
                    onComplete={() => {
                        setShowGitHubRepoSelector(false);
                        router.push("/dashboard/settings/data-sources");
                    }}
                />
            </div>
        </div>
    );
}

export default function OAuthCallbackPage() {
    return (
        <Suspense fallback={
            <div className="flex min-h-screen items-center justify-center p-4 bg-background">
                <Spinner className="h-12 w-12 animate-spin text-primary" />
            </div>
        }>
            <OAuthCallbackContent />
        </Suspense>
    );
}
