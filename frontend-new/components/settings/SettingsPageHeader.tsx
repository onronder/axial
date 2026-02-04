"use client";

import { cn } from "@/lib/utils";

interface SettingsPageHeaderProps {
  icon: React.ElementType;
  title: string;
  description: string;
  actions?: React.ReactNode;
  badge?: React.ReactNode;
  autoSaveNote?: boolean;
}

export function SettingsPageHeader({
  icon: Icon,
  title,
  description,
  actions,
  badge,
  autoSaveNote,
}: SettingsPageHeaderProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-white shadow-lg shadow-primary/20">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-display text-2xl font-bold text-foreground">
              {title}
            </h1>
            {badge}
          </div>
          <p className="mt-1 text-muted-foreground">{description}</p>
          {autoSaveNote && (
            <p className="mt-0.5 text-xs text-muted-foreground/70">
              Changes are saved automatically
            </p>
          )}
        </div>
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      )}
    </div>
  );
}
