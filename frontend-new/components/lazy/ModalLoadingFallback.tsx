"use client";
import { Spinner } from "@/components/ui/spinner";

export function ModalLoadingFallback() {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="flex items-center gap-3 rounded-lg bg-background px-6 py-4 shadow-lg">
        <Spinner label="Loading modal" />
        <span className="text-sm text-foreground">Loading...</span>
      </div>
    </div>
  );
}
