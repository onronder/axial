"use client";

import { Loader2 } from "lucide-react"
import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { AxioLogo } from "@/components/branding/AxioLogo"
import { ParticleBackground } from "@/components/ui/ParticleBackground"

export default function AuthLayout({
    children,
}: {
    children: React.ReactNode
}) {
    const { isAuthenticated, loading } = useAuth()
    const router = useRouter()

    useEffect(() => {
        if (!loading && isAuthenticated) {
            router.push("/dashboard")
        }
    }, [isAuthenticated, loading, router])

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center bg-background">
                <Loader2 className="animate-spin h-8 w-8 text-primary" />
            </div>
        )
    }

    // Only render children (login/register forms) if NOT authenticated
    if (isAuthenticated) {
        return null
    }

    return (
        <div className="void-background min-h-screen flex flex-col items-center justify-center p-4 overflow-hidden relative">
            <ParticleBackground />
            <div className="w-full max-w-md space-y-8 animate-fade-in relative z-10">
                {/* Centered Logo */}
                <div className="flex flex-col items-center justify-center space-y-2">
                    <AxioLogo variant="full" size="lg" />
                </div>

                {/* Auth Form Content */}
                <div className="animate-slide-up">
                    {children}
                </div>
            </div>
        </div>
    )
}
