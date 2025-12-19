import { Loader2 } from "lucide-react";

export function AuthLoading() {
    return (
        <div className="flex min-h-screen w-full items-center justify-center bg-slate-950">
            <Loader2 className="h-8 w-8 animate-spin text-white/50" />
        </div>
    );
}
