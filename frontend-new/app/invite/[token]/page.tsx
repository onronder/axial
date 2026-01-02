"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { api } from "@/lib/api";
import { useSession } from "@/components/providers/SessionProvider";
import { Loader2, CheckCircle2, XCircle, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

type InviteState = "loading" | "success" | "error" | "unauthenticated";

interface AcceptResult {
    success: boolean;
    team_name?: string;
    team_id?: string;
    error?: string;
}

export default function AcceptInvitePage() {
    const router = useRouter();
    const params = useParams();
    const token = params.token as string;
    const { session, loading: sessionLoading } = useSession();

    const [state, setState] = useState<InviteState>("loading");
    const [teamName, setTeamName] = useState<string>("");
    const [errorMessage, setErrorMessage] = useState<string>("");

    useEffect(() => {
        // Wait for session to load
        if (sessionLoading) return;

        // If not authenticated, redirect to login with return URL
        if (!session) {
            setState("unauthenticated");
            const returnUrl = encodeURIComponent(`/invite/${token}`);
            router.push(`/login?redirect=${returnUrl}`);
            return;
        }

        // Accept the invite
        const acceptInvite = async () => {
            try {
                const { data } = await api.post<AcceptResult>("/team/accept", {
                    token: token,
                });

                if (data.success) {
                    setTeamName(data.team_name || "the team");
                    setState("success");

                    // Redirect to dashboard after a short delay
                    setTimeout(() => {
                        router.push("/dashboard");
                    }, 2500);
                } else {
                    setErrorMessage(data.error || "Failed to accept invitation");
                    setState("error");
                }
            } catch (error: any) {
                console.error("Failed to accept invite:", error);
                const message = error.response?.data?.detail || "Invalid or expired invite link";
                setErrorMessage(message);
                setState("error");
            }
        };

        acceptInvite();
    }, [session, sessionLoading, token, router]);

    // Loading state
    if (state === "loading" || state === "unauthenticated") {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <Card className="w-full max-w-md mx-4">
                    <CardContent className="flex flex-col items-center justify-center py-12">
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mb-6">
                            <Loader2 className="h-8 w-8 text-primary animate-spin" />
                        </div>
                        <h2 className="text-xl font-semibold text-foreground mb-2">
                            {state === "unauthenticated" ? "Redirecting to login..." : "Accepting invitation..."}
                        </h2>
                        <p className="text-muted-foreground text-center">
                            {state === "unauthenticated"
                                ? "Please sign in to accept this team invitation"
                                : "Please wait while we process your invitation"}
                        </p>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Success state
    if (state === "success") {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background">
                <Card className="w-full max-w-md mx-4">
                    <CardContent className="flex flex-col items-center justify-center py-12">
                        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-success/10 mb-6">
                            <CheckCircle2 className="h-8 w-8 text-success" />
                        </div>
                        <h2 className="text-xl font-semibold text-foreground mb-2">
                            Welcome to {teamName}! 🎉
                        </h2>
                        <p className="text-muted-foreground text-center mb-6">
                            You've successfully joined the team. Redirecting to dashboard...
                        </p>
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Users className="h-4 w-4" />
                            <span>You can now collaborate with your team</span>
                        </div>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Error state
    return (
        <div className="min-h-screen flex items-center justify-center bg-background">
            <Card className="w-full max-w-md mx-4">
                <CardContent className="flex flex-col items-center justify-center py-12">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-destructive/10 mb-6">
                        <XCircle className="h-8 w-8 text-destructive" />
                    </div>
                    <h2 className="text-xl font-semibold text-foreground mb-2">
                        Invitation Error
                    </h2>
                    <p className="text-muted-foreground text-center mb-6">
                        {errorMessage}
                    </p>
                    <div className="flex gap-3">
                        <Button variant="outline" onClick={() => router.push("/")}>
                            Go Home
                        </Button>
                        <Button onClick={() => router.push("/dashboard")}>
                            Go to Dashboard
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
