'use client';

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

type LogoSize = "xs" | "sm" | "md" | "lg" | "xl";
type LogoVariant = "icon" | "full";

interface AxioLogoProps {
  size?: LogoSize;
  variant?: LogoVariant;
  forceDark?: boolean;
  className?: string;
}

const sizeMap: Record<LogoVariant, Record<LogoSize, { width: number; height: number }>> = {
  icon: {
    xs: { width: 20, height: 20 },
    sm: { width: 24, height: 24 },
    md: { width: 32, height: 32 },
    lg: { width: 48, height: 48 },
    xl: { width: 64, height: 64 },
  },
  full: {
    xs: { width: 100, height: 40 },
    sm: { width: 140, height: 56 },
    md: { width: 180, height: 72 },
    lg: { width: 220, height: 88 },
    xl: { width: 280, height: 112 },
  },
};

export function AxioLogo({
  size = "md",
  variant = "icon",
  forceDark = false,
  className = ""
}: AxioLogoProps) {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Avoid hydration mismatch by waiting for mount
  if (!mounted) {
    return <div style={{ width: sizeMap[variant][size].width, height: sizeMap[variant][size].height }} />;
  }

  // Determine which theme to use
  const effectiveTheme = forceDark ? "dark" : resolvedTheme;

  // Icon works for both themes, full logo needs theme switching
  const logoSrc = variant === "icon"
    ? "/assets/axio-hub-logo.png"
    : (effectiveTheme === "dark" ? "/assets/axio-hub-full-dark.png" : "/assets/axio-hub-full-light.png");

  const dimensions = sizeMap[variant][size];

  return (
    <img
      src={logoSrc}
      alt="Axio Hub"
      width={dimensions.width}
      height={dimensions.height}
      className={`object-contain ${className}`}
    />
  );
}
