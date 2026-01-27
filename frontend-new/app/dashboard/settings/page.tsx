
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@/components/ui/spinner";

export default function SettingsPage() {
    const router = useRouter();

    useEffect(() => {
        router.replace("/dashboard/settings/general");
    }, [router]);

    return (
        <div className="flex h-[50vh] items-center justify-center">
            <Spinner className="h-8 w-8 animate-spin text-primary" />
        </div>
    );
}