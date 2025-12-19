"use client";

import {
  HardDrive,
  Cloud,
  FolderSync,
  Box,
  Server,
  FileText,
  MessageSquare,
  Users,
  Globe,
  Upload,
  Database,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface DataSourceIconProps {
  sourceId: string;
  className?: string;
}

const iconConfig: Record<string, { icon: typeof HardDrive; color: string }> = {
  "google_drive": { icon: HardDrive, color: "text-yellow-500" }, // Updated ID key
  "onedrive": { icon: Cloud, color: "text-blue-500" },
  "dropbox": { icon: FolderSync, color: "text-blue-400" },
  "box": { icon: Box, color: "text-blue-600" },
  "sftp": { icon: Server, color: "text-gray-500" },
  "notion": { icon: FileText, color: "text-foreground" },
  "confluence": { icon: Database, color: "text-blue-500" },
  "coda": { icon: FileText, color: "text-orange-500" },
  "airtable": { icon: Database, color: "text-blue-400" },
  "slack": { icon: MessageSquare, color: "text-purple-500" },
  "teams": { icon: Users, color: "text-blue-600" },
  "discord": { icon: MessageSquare, color: "text-indigo-500" },
  "crawler": { icon: Globe, color: "text-green-500" }, // Updated ID key
  "local": { icon: Upload, color: "text-primary" }, // Updated ID key
};

export function DataSourceIcon({ sourceId, className }: DataSourceIconProps) {
  const config = iconConfig[sourceId] || { icon: Cloud, color: "text-muted-foreground" };
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-lg bg-muted p-2",
        className
      )}
    >
      <Icon className={cn("h-5 w-5", config.color)} />
    </div>
  );
}
