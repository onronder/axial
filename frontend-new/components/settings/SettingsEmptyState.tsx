"use client";

import { cn } from "@/lib/utils";

interface SettingsEmptyStateProps {
  icon: React.ElementType;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function SettingsEmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: SettingsEmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-12 text-center",
        className
      )}
    >
      <Icon className="h-12 w-12 text-muted-foreground/50 mb-4" />
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-md mt-1">
        {description}
      </p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
