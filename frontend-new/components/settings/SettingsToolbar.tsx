"use client";

import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface SettingsToolbarProps {
  searchPlaceholder: string;
  searchValue: string;
  onSearchChange: (value: string) => void;
  children?: React.ReactNode;
  actions?: React.ReactNode;
}

export function SettingsToolbar({
  searchPlaceholder,
  searchValue,
  onSearchChange,
  children,
  actions,
}: SettingsToolbarProps) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center flex-1">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder={searchPlaceholder}
            value={searchValue}
            onChange={(e) => onSearchChange(e.target.value)}
            className="pl-9"
            aria-label="Search"
          />
        </div>
        {children}
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      )}
    </div>
  );
}
