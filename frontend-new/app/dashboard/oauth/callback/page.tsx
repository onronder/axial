"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function OAuthCallbackPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const code = searchParams.get("code");
        const errorParam = searchParams.get("error");

        console.log("🔐 [OAuth Callback] Starting...");
        console.log("🔐 [OAuth Callback] Code:", code ? `${code.substring(0, 20)}...` : null);
        console.log("🔐 [OAuth Callback] Error:", errorParam);

        if (errorParam) {
            setStatus("error");
            setError(errorParam === "access_denied" ? "Access was denied" : errorParam);
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
                console.log("🔐 [OAuth Callback] Sending code to backend...");
                const response = await api.post("/api/v1/integrations/google/exchange", { code });
                console.log("🔐 [OAuth Callback] ✅ Success:", response.data);
                setStatus("success");
                // Redirect to data sources after short delay
                setTimeout(() => {
                    router.push("/dashboard/settings/data-sources");
                }, 2000);
            } catch (err: any) {
                console.error("🔐 [OAuth Callback] ❌ Token exchange failed:", err.response?.data || err.message);
                setStatus("error");
                setError(err.response?.data?.detail || "Failed to connect Google Drive");
            }
        };

        exchangeCode();
    }, [searchParams, router]);

    return (
        <div className="flex min-h-[80vh] items-center justify-center p-4">
            <Card className="w-full max-w-md">
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
                        {status === "loading" && "Connecting Google Drive..."}
                        {status === "success" && "Connected Successfully!"}
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
    );
}
