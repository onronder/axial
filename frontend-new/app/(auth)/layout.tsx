"use client";

import { LayoutDashboard } from "lucide-react"
import Link from "next/link" // Keep imports if needed, though Link is unused in snippet
import { useAuth } from "@/hooks/useAuth"
import { useRouter } from "next/navigation"
import { useEffect } from "react"
import { AuthLoading } from "@/components/ui/auth-loading" // Assuming we can use it here too for consistency or a smaller spinner

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
        return <AuthLoading />
    }

    // Only render children (login/register forms) if NOT authenticated
    if (isAuthenticated) {
        return null
    }

    return (
        <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="w-full max-w-md space-y-8">
                <div className="flex flex-col items-center justify-center text-center">
                    <div className="flex items-center gap-2 mb-4">
                        <LayoutDashboard className="h-8 w-8 text-slate-900" />
                        <span className="text-xl font-bold">Axial Newton</span>
                    </div>
                </div>
                {children}
            </div>
        </div>
    )
}
