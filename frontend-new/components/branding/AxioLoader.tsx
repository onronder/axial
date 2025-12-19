'use client';

import { cn } from "@/lib/utils";

// Use static path instead of import
const logoIcon = "/assets/axio-hub-logo.png";

type LoaderSize = "sm" | "md" | "lg";

interface AxioLoaderProps {
  size?: LoaderSize;
  text?: string;
  className?: string;
}

const sizeMap: Record<LoaderSize, { logo: number; text: string }> = {
  sm: { logo: 24, text: "text-xs" },
  md: { logo: 40, text: "text-sm" },
  lg: { logo: 64, text: "text-base" },
};

export function AxioLoader({
  size = "md",
  text,
  className
}: AxioLoaderProps) {
  const dimensions = sizeMap[size];

  return (
    <div className={cn("flex flex-col items-center justify-center gap-3", className)}>
      <div className="relative">
        {/* Pulsing ring */}
        <div
          className="absolute inset-0 rounded-full animate-ping opacity-20 bg-primary"
          style={{
            width: dimensions.logo + 16,
            height: dimensions.logo + 16,
            top: -8,
            left: -8
          }}
        />
        {/* Spinning glow */}
        <div
          className="absolute inset-0 rounded-full animate-spin opacity-30"
          style={{
            width: dimensions.logo + 8,
            height: dimensions.logo + 8,
            top: -4,
            left: -4,
            background: "conic-gradient(from 0deg, transparent, hsl(var(--primary)), transparent)"
          }}
        />
        {/* Logo */}
        <img
          src={logoIcon}
          alt="Loading..."
          width={dimensions.logo}
          height={dimensions.logo}
          className="object-contain relative z-10 animate-pulse"
        />
      </div>
      {text && (
        <p className={cn("text-muted-foreground animate-pulse", dimensions.text)}>
          {text}
        </p>
      )}
    </div>
  );
}
