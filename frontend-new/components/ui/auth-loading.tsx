
import { Spinner } from "@/components/ui/spinner";

export function AuthLoading() {
    return (
        <div className="flex min-h-screen w-full items-center justify-center bg-background">
            <Spinner className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
    );
}
