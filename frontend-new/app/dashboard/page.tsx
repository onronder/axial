
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@/components/ui/spinner";

export default function DashboardPage() {
    const router = useRouter();

    // Redirect to new chat page
    useEffect(() => {
        router.replace("/dashboard/chat/new");
    }, [router]);

    // Show loading while redirecting
    return (
        <div className="flex h-full items-center justify-center">
            <Spinner className="animate-spin h-8 w-8 text-primary" />
        </div>
    );
}