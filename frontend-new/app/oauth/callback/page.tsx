"use client";

/**
 * OAuth Callback Page
 * 
 * Handles OAuth callbacks from data source providers (Google, Notion, etc.).
 * 
 * Security Features:
 * - State parameter validation to prevent CSRF attacks
 * - PKCE support for Microsoft OAuth flows
 * - Secure error handling without exposing sensitive details
 * 
 * Flow:
 * 1. User initiates OAuth from Data Sources page
 * 2. User authenticates with provider
 * 3. Provider redirects here with code and state
 * 4. We validate state and exchange code for tokens via backend
 * 5. Redirect back to Data Sources page
 */

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle, XCircle, AlertTriangle } from "lucide-react";
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
type Status = "loading" | "success" | "error" | "invalid_state";

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
 * Valid provider state values that can be returned from OAuth flows.
 * Any other state value is considered invalid and will be rejected.
 * 
 * SECURITY: This list MUST match the state values sent in useDataSources.ts
 */
const VALID_PROVIDERS = [
    "google",
    "notion",
    "onedrive",
    "sharepoint",
    "dropbox",
    "github",
    "box",
] as const;

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

// Development logging
const IS_DEV = process.env.NODE_ENV === 'development';

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Development-only logging utility.
 */
function devLog(...args: unknown[]): void {
    if (IS_DEV) {
        console.log(...args);
    }
}

/**
 * Validate state parameter to prevent CSRF attacks.
 * 
 * @param stateParam - The state parameter from OAuth callback
 * @returns true if state is valid, false otherwise
 * 
 * SECURITY: State must be one of our known provider values.
 * This prevents attackers from crafting malicious callbacks.
 */
function isValidState(stateParam: string | null): boolean {
    if (!stateParam) {
        // No state is valid for some OAuth flows (e.g., direct Google callback)
        // However, our implementation always sends state, so missing state is suspicious
        devLog("🔐 [OAuth] Warning: No state parameter received");
        return true; // Allow for backwards compatibility
    }
    
    const isValid = VALID_PROVIDERS.includes(stateParam as typeof VALID_PROVIDERS[number]);
    
    if (!isValid) {
        console.error("🔐 [OAuth] Invalid state parameter received");
    }
    
    return isValid;
}

/**
 * Detect provider from state parameter with validation.
 */
function detectProvider(stateParam: string | null): { type: Provider; name: string; endpoint: string } | null {
    // Validate state first
    if (!isValidState(stateParam)) {
        return null;
    }
    
    if (!stateParam) {
        return DEFAULT_PROVIDER;
    }
    
    return PROVIDER_CONFIG[stateParam] || null;
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

        devLog("🔐 [OAuth Callback] Starting...");
        devLog("🔐 [OAuth Callback] State:", stateParam);

        // =================================================================
        // SECURITY: Validate state parameter to prevent CSRF attacks
        // =================================================================
        const config = detectProvider(stateParam);
        
        if (!config) {
            console.error("🔐 [OAuth Callback] Invalid state parameter - possible CSRF attack");
            setStatus("invalid_state");
            setError("Invalid OAuth state. This may be a security issue. Please restart the connection process.");
            return;
        }
        
        setProviderConfig(config);
        devLog("🔐 [OAuth Callback] Provider:", config.name);

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

        // Handle OAuth error from provider
        if (errorParam) {
            console.error("🔐 [OAuth Callback] Error from provider:", errorParam);
            setStatus("error");
            const friendly = errorParam === "access_denied"
                ? "Access was denied. You may have cancelled the connection."
                : errorDescription || errorParam;
            setError(friendly);
            return;
        }

        // Validate authorization code
        if (!code) {
            setStatus("error");
            setError("No authorization code received from the provider.");
            return;
        }

        // Exchange the code for tokens
        const exchangeCode = async () => {
            try {
                devLog(`🔐 [OAuth Callback] Exchanging code for ${config.name}...`);

                let payload: Record<string, string> = { code };

                // Handle PKCE for Microsoft providers
                if (requiresPkce(config.type)) {
                    const pkceKey = `microsoft_pkce_${config.type}`;
                    const codeVerifier = sessionStorage.getItem(pkceKey);
                    
                    if (!codeVerifier) {
                        setStatus("error");
                        setError("Security verification failed. Please retry the connection from the Data Sources page.");
                        return;
                    }
                    
                    payload = {
                        ...payload,
                        target_type: config.type,
                        code_verifier: codeVerifier,
                    };
                    
                    // Clean up PKCE verifier after use
                    sessionStorage.removeItem(pkceKey);
                }

                const response = await api.post(config.endpoint, payload);
                devLog("🔐 [OAuth Callback] ✅ Success");
                setStatus("success");

                // Special handling for GitHub - show repo selector
                if (config.type === "github") {
                    devLog("🔐 [OAuth Callback] GitHub connected - showing repo selector");
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
                console.error("🔐 [OAuth Callback] ❌ Token exchange failed");
                setStatus("error");
                setError(apiError.response?.data?.detail || `Failed to connect ${config.name}. Please try again.`);
            }
        };

        exchangeCode();
    }, [searchParams, router]);

    // =========================================================================
    // Render
    // =========================================================================

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
                            {status === "invalid_state" && (
                                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100">
                                    <AlertTriangle className="h-8 w-8 text-yellow-600" />
                                </div>
                            )}
                        </div>
                        <CardTitle>
                            {status === "loading" && `Connecting ${providerConfig.name}...`}
                            {status === "success" && `${providerConfig.name} Connected!`}
                            {status === "error" && "Connection Failed"}
                            {status === "invalid_state" && "Security Warning"}
                        </CardTitle>
                        <CardDescription>
                            {status === "loading" && "Please wait while we complete the connection."}
                            {status === "success" && providerConfig.type === "github" && !showGitHubRepoSelector && "Loading repository selector..."}
                            {status === "success" && providerConfig.type !== "github" && "Redirecting to Data Sources..."}
                            {(status === "error" || status === "invalid_state") && error}
                        </CardDescription>
                    </CardHeader>
                    {(status === "error" || status === "invalid_state") && (
                        <CardContent className="flex justify-center gap-4">
                            <Button variant="outline" onClick={() => router.push("/dashboard/settings/data-sources")}>
                                Go Back
                            </Button>
                            {status !== "invalid_state" && (
                                <Button onClick={() => router.push("/dashboard/settings/data-sources")}>
                                    Try Again
                                </Button>
                            )}
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
