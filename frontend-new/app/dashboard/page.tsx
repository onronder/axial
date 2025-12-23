"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

export default function DashboardPage() {
    const router = useRouter();

    // Redirect to new chat page
    useEffect(() => {
        router.replace("/dashboard/chat/new");
    }, [router]);

    // Show loading while redirecting
    return (
        <div className="flex h-full items-center justify-center">
            <Loader2 className="animate-spin h-8 w-8 text-primary" />
        </div>
    );
}
