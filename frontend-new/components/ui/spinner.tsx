import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface SpinnerProps {
  className?: string;
  label?: string;
  size?: "sm" | "md" | "lg";
}

const sizes: Record<NonNullable<SpinnerProps["size"]>, string> = {
  sm: "h-4 w-4",
  md: "h-5 w-5",
  lg: "h-8 w-8",
};

export function Spinner({ className, label = "Loading", size = "md" }: SpinnerProps) {
  return (
    <Loader2
      className={cn("animate-spin", sizes[size], className)}
      aria-label={label}
      role="status"
    />
  );
}
