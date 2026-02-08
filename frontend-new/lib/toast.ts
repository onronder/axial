/**
 * Unified toast wrapper using sonner.
 *
 * Provides a useToast()-compatible API surface for gradual migration.
 * After full migration, consumers can import { toast } from "sonner" directly.
 */
import { toast as sonnerToast } from "sonner";

interface ToastOptions {
  title?: string;
  description?: string;
  variant?: "default" | "destructive";
  duration?: number;
  className?: string;
  [key: string]: unknown;
}

export function toast(opts: ToastOptions) {
  const sonnerOpts: Record<string, unknown> = {
    description: opts.description,
    duration: opts.duration,
  };
  if (opts.className) {
    sonnerOpts.className = opts.className;
  }

  if (opts.variant === "destructive") {
    sonnerToast.error(opts.title ?? "Error", sonnerOpts);
  } else {
    sonnerToast.success(opts.title ?? "Success", sonnerOpts);
  }
}

export function useToast() {
  return { toast };
}
