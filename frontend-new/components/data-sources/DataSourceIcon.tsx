"use client";

import { Upload, Server } from "lucide-react";
import { cn } from "@/lib/utils";

interface DataSourceIconProps {
  sourceId: string;
  className?: string;
  size?: "sm" | "md" | "lg";
}

// Google Drive Logo SVG
const GoogleDriveIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 87.3 78" xmlns="http://www.w3.org/2000/svg">
    <path d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z" fill="#0066da" />
    <path d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z" fill="#00ac47" />
    <path d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z" fill="#ea4335" />
    <path d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z" fill="#00832d" />
    <path d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z" fill="#2684fc" />
    <path d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z" fill="#ffba00" />
  </svg>
);

// Notion Logo SVG (Standard N Logo)
const NotionIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
    <path d="M4.128 0.5C2.108 0.5 0.5 2.108 0.5 4.128V19.872C0.5 21.892 2.108 23.5 4.128 23.5H8.641C10.661 23.5 12.269 21.892 12.269 19.872V10.165L18.066 19.682C18.665 20.665 19.333 21.165 20.128 21.165H20.128C21.892 21.165 23.5 19.557 23.5 17.793V4.128C23.5 2.108 21.892 0.5 19.872 0.5H15.359C13.339 0.5 11.731 2.108 11.731 4.128V13.885L5.934 4.318C5.335 3.335 4.667 2.835 3.872 2.835C2.108 2.835 0.5 4.443 0.5 6.207V19.872C0.5 21.892 2.108 23.5 4.128 23.5H8.641" fill="currentColor" />
    <path d="M19.872 0.5H15.359C13.339 0.5 11.731 2.108 11.731 4.128V15.75L18.683 4.318C19.282 3.335 19.95 2.835 20.745 2.835H23.5V4.128C23.5 2.108 21.892 0.5 19.872 0.5Z" fill="currentColor" />
    <path d="M4.128 23.5H8.641C10.661 23.5 12.269 21.892 12.269 19.872V8.25L5.317 19.682C4.718 20.665 4.05 21.165 3.255 21.165H0.5V19.872C0.5 21.892 2.108 23.5 4.128 23.5Z" fill="currentColor" />
  </svg>
);

// OneDrive Logo SVG
const OneDriveIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M10.619 8.267c.378-.162.79-.252 1.22-.252a3.08 3.08 0 0 1 2.933 2.135l.225.68.713.043a2.46 2.46 0 0 1 2.29 2.46 2.46 2.46 0 0 1-.686 1.705l-.01.01-.027.028-.002.002-.016.015-.003.003-.022.02H8.073a2.46 2.46 0 0 1-2.46-2.46c0-.59.209-1.132.556-1.555l.022-.027a2.46 2.46 0 0 1 1.822-.88l.446-.025.24-.375a2.96 2.96 0 0 1 1.92-1.527z" fill="#0364B8" />
    <path d="M10.619 8.267a2.96 2.96 0 0 0-1.92 1.527l-.24.375-.446.025a2.46 2.46 0 0 0-1.822.88l-.022.027a2.461 2.461 0 0 0-.556 1.555 2.46 2.46 0 0 0 2.46 2.46h.518V10.55a2.284 2.284 0 0 1 2.028-2.283z" fill="#0078D4" />
    <path d="M17.286 13.087l-.713-.043-.225-.68a3.08 3.08 0 0 0-2.933-2.135c-.43 0-.842.09-1.22.252l-.034.015a2.284 2.284 0 0 0-2.028 2.283v4.566h7.903l.003-.003.022-.02.002-.002.016-.015.003-.003.027-.027.01-.011a2.46 2.46 0 0 0 .455-3.464 2.46 2.46 0 0 0-1.288-.713z" fill="#1490DF" />
    <path d="M8.591 15.316H6.533a2.46 2.46 0 0 1-2.46-2.46c0-.59.209-1.132.556-1.555l.022-.027A2.46 2.46 0 0 1 6.473 10.4l.446-.025.24-.375a2.96 2.96 0 0 1 1.92-1.527A2.96 2.96 0 0 0 6.31 9.717a2.46 2.46 0 0 0-2.237 2.94 2.46 2.46 0 0 0 2.457 1.98l.004-.002h2.057v.681z" fill="#28A8EA" />
  </svg>
);

// Dropbox Logo SVG
const DropboxIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 256 218" xmlns="http://www.w3.org/2000/svg">
    <path d="M63.995 0L0 40.771l63.995 40.772L128 40.771zM192.005 0l-64 40.771 64 40.772L256 40.771zM0 122.321l63.995 40.772L128 122.321 63.995 81.55zM192.005 81.55l-64 40.772 64 40.772 64-40.772zM64 176.771l64.005 40.772L192 176.771l-63.995-40.772z" fill="#0061FF" />
  </svg>
);

// Slack Logo SVG
const SlackIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 127 127" xmlns="http://www.w3.org/2000/svg">
    <path d="M27.2 80c0 7.3-5.9 13.2-13.2 13.2S.8 87.3.8 80s5.9-13.2 13.2-13.2h13.2V80zm6.6 0c0-7.3 5.9-13.2 13.2-13.2s13.2 5.9 13.2 13.2v33c0 7.3-5.9 13.2-13.2 13.2s-13.2-5.9-13.2-13.2V80z" fill="#E01E5A" />
    <path d="M47 27c-7.3 0-13.2-5.9-13.2-13.2S39.7.6 47 .6s13.2 5.9 13.2 13.2V27H47zm0 6.7c7.3 0 13.2 5.9 13.2 13.2s-5.9 13.2-13.2 13.2H14c-7.3 0-13.2-5.9-13.2-13.2S6.7 33.7 14 33.7h33z" fill="#36C5F0" />
    <path d="M99.9 46.9c0-7.3 5.9-13.2 13.2-13.2s13.2 5.9 13.2 13.2-5.9 13.2-13.2 13.2H99.9V46.9zm-6.6 0c0 7.3-5.9 13.2-13.2 13.2S66.9 54.2 66.9 46.9V14c0-7.3 5.9-13.2 13.2-13.2s13.2 5.9 13.2 13.2v32.9z" fill="#2EB67D" />
    <path d="M80.1 99.8c7.3 0 13.2 5.9 13.2 13.2s-5.9 13.2-13.2 13.2-13.2-5.9-13.2-13.2V99.8h13.2zm0-6.6c-7.3 0-13.2-5.9-13.2-13.2s5.9-13.2 13.2-13.2h33c7.3 0 13.2 5.9 13.2 13.2s-5.9 13.2-13.2 13.2h-33z" fill="#ECB22E" />
  </svg>
);

// Microsoft Teams Logo
const TeamsIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M20.625 6.75h-5.25c-.621 0-1.125.504-1.125 1.125v5.25c0 .621.504 1.125 1.125 1.125h5.25c.621 0 1.125-.504 1.125-1.125v-5.25c0-.621-.504-1.125-1.125-1.125z" fill="#5059C9" />
    <circle cx="18" cy="4.5" r="1.5" fill="#5059C9" />
    <path d="M15.375 5.25a3.375 3.375 0 1 0 0-6.75 3.375 3.375 0 0 0 0 6.75z" fill="#7B83EB" />
    <path d="M13.5 7.5H3a1.5 1.5 0 0 0-1.5 1.5v6.75a5.25 5.25 0 0 0 10.5 0V9a1.5 1.5 0 0 0-1.5-1.5z" fill="#7B83EB" />
  </svg>
);

// Globe/Web Icon (custom design)
const GlobeIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" stroke="url(#globeGradient)" strokeWidth="2" />
    <ellipse cx="12" cy="12" rx="4" ry="10" stroke="url(#globeGradient)" strokeWidth="2" />
    <path d="M2 12h20" stroke="url(#globeGradient)" strokeWidth="2" />
    <path d="M12 2c2.5 3.5 2.5 14.5 0 20" stroke="url(#globeGradient)" strokeWidth="2" />
    <defs>
      <linearGradient id="globeGradient" x1="2" y1="2" x2="22" y2="22">
        <stop stopColor="#10B981" />
        <stop offset="1" stopColor="#3B82F6" />
      </linearGradient>
    </defs>
  </svg>
);

// Confluence Logo
const ConfluenceIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 256 246" xmlns="http://www.w3.org/2000/svg">
    <path d="M9.26 187.86c-3.11 5.12-6.63 11.06-9.26 15.66a7.46 7.46 0 0 0 2.68 10.2l54.19 33.46a7.46 7.46 0 0 0 10.2-2.45c2.26-3.76 5.23-8.5 8.43-13.6 22.93-36.67 45.86-32.64 87.88-13.6l57.69 26.14a7.46 7.46 0 0 0 9.89-3.69l25.37-55.64a7.46 7.46 0 0 0-3.58-9.8c-17.7-8.28-52.95-24.76-78.55-36.68-73.2-34.04-127.8-33.37-164.94 49.99z" fill="#2684FF" />
    <path d="M246.74 57.94c3.11-5.12 6.63-11.06 9.26-15.66a7.46 7.46 0 0 0-2.68-10.2L199.13-1.38a7.46 7.46 0 0 0-10.2 2.45c-2.26 3.76-5.23 8.5-8.43 13.6-22.93 36.67-45.86 32.64-87.88 13.6L35.05 2.25a7.46 7.46 0 0 0-9.89 3.69L-.21 61.58a7.46 7.46 0 0 0 3.58 9.8c17.7 8.28 52.95 24.76 78.55 36.68 73.2 33.95 127.8 33.28 164.82-50.12z" fill="#0052CC" />
  </svg>
);

// Discord Logo
const DiscordIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 256 199" xmlns="http://www.w3.org/2000/svg">
    <path d="M216.856 16.597A208.502 208.502 0 0 0 164.042 0c-2.275 4.113-4.933 9.645-6.766 14.046-19.692-2.961-39.203-2.961-58.533 0-1.832-4.4-4.55-9.933-6.846-14.046a207.809 207.809 0 0 0-52.855 16.638C5.618 67.147-3.443 116.4 1.087 164.956c22.169 16.555 43.653 26.612 64.775 33.193A161.094 161.094 0 0 0 79.735 175.3a136.413 136.413 0 0 1-21.846-10.632 108.636 108.636 0 0 0 5.356-4.237c42.122 19.702 87.89 19.702 129.51 0a131.66 131.66 0 0 0 5.355 4.237 136.07 136.07 0 0 1-21.886 10.653c4.006 8.02 8.638 15.67 13.873 22.848 21.142-6.58 42.646-16.637 64.815-33.213 5.316-56.288-9.08-105.09-38.056-148.36zM85.474 135.095c-12.645 0-23.015-11.805-23.015-26.18s10.149-26.2 23.015-26.2c12.867 0 23.236 11.804 23.015 26.2.02 14.375-10.148 26.18-23.015 26.18zm85.051 0c-12.645 0-23.014-11.805-23.014-26.18s10.148-26.2 23.014-26.2c12.867 0 23.236 11.804 23.015 26.2 0 14.375-10.148 26.18-23.015 26.18z" fill="#5865F2" />
  </svg>
);

// Box Logo
const BoxIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 256 135" xmlns="http://www.w3.org/2000/svg">
    <path d="M50.408 0C33.727 0 20.6 13.127 20.6 29.808v61.07c0 16.681 13.127 29.808 29.808 29.808h155.184c16.681 0 29.808-13.127 29.808-29.808v-61.07C235.4 13.127 222.273 0 205.592 0H50.408z" fill="#0061D5" />
  </svg>
);

// Airtable Logo
const AirtableIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 200 170" xmlns="http://www.w3.org/2000/svg">
    <path d="M90.04 8.51L8.17 36.18C-.27 39.05-.47 50.79 7.85 53.93l82.03 31.31c6.05 2.31 12.8 2.31 18.85 0l82.03-31.31c8.32-3.14 8.11-14.87-.11-17.75L108.89 8.51A31.1 31.1 0 0 0 90.04 8.51z" fill="#FCB400" />
    <path d="M105.97 92.54v69.52c0 5.26 5.33 8.87 10.2 6.92l80.78-32.46c3.09-1.24 5.13-4.23 5.13-7.64V59.36c0-5.26-5.33-8.87-10.2-6.92l-80.78 32.46A8.152 8.152 0 0 0 105.97 92.54z" fill="#18BFFF" />
    <path d="M92.09 97.6L26.6 52.32c-4.63-3.2-10.85.56-10.85 6.23v67.52c0 3.11 1.69 5.97 4.4 7.47l64.49 45.28c4.63 3.2 10.85-.56 10.85-6.23V104.86A8.51 8.51 0 0 0 92.09 97.6z" fill="#F82B60" />
  </svg>
);

// Coda Logo
const CodaIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M22.5 12c0-5.799-4.701-10.5-10.5-10.5S1.5 6.201 1.5 12s4.701 10.5 10.5 10.5c2.898 0 5.523-1.175 7.425-3.075l-3.75-3.75A5.959 5.959 0 0 1 12 17.25c-2.898 0-5.25-2.352-5.25-5.25S9.102 6.75 12 6.75s5.25 2.352 5.25 5.25c0 1.2-.402 2.304-1.08 3.187l3.75 3.75A10.43 10.43 0 0 0 22.5 12z" fill="#F46A54" />
  </svg>
);

// Size configurations
const sizeConfig = {
  sm: "h-4 w-4",
  md: "h-5 w-5",
  lg: "h-6 w-6",
};

const containerSizeConfig = {
  sm: "p-1.5",
  md: "p-2",
  lg: "p-2.5",
};

// Map source IDs to their custom icons
// Support both hyphen and underscore formats for compatibility
const customIconMap: Record<string, React.FC<{ className?: string }>> = {
  "google-drive": GoogleDriveIcon,
  "google_drive": GoogleDriveIcon, // Backend uses underscore format
  "notion": NotionIcon,
  "onedrive": OneDriveIcon,
  "one_drive": OneDriveIcon,
  "dropbox": DropboxIcon,
  "slack": SlackIcon,
  "teams": TeamsIcon,
  "url-crawler": GlobeIcon,
  "url_crawler": GlobeIcon,
  "confluence": ConfluenceIcon,
  "discord": DiscordIcon,
  "box": BoxIcon,
  "airtable": AirtableIcon,
  "coda": CodaIcon,
};

// Fallback icons with colors for sources without custom SVGs
const fallbackConfig: Record<string, { icon: typeof Upload; color: string }> = {
  "sftp": { icon: Server, color: "text-gray-500" },
  "file-upload": { icon: Upload, color: "text-primary" },
};

export function DataSourceIcon({ sourceId, className, size = "md" }: DataSourceIconProps) {
  const CustomIcon = customIconMap[sourceId];
  const iconSize = sizeConfig[size];

  // If we have a custom brand icon, use it directly (no wrapper)
  if (CustomIcon) {
    return <CustomIcon className={cn(iconSize, className)} />;
  }

  // Fallback to Lucide icons
  const fallback = fallbackConfig[sourceId] || { icon: Upload, color: "text-muted-foreground" };
  const FallbackIcon = fallback.icon;

  return <FallbackIcon className={cn(iconSize, fallback.color, className)} />;
}
