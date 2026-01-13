export type CanonicalSourceType =
  | "file_upload"
  | "google_drive"
  | "web"
  | "notion"
  | "slack"
  | "onedrive"
  | "sharepoint"
  | "dropbox"
  | "local";

const SOURCE_TYPE_ALIASES: Record<string, string> = {
  "file-upload": "file_upload",
  file_upload: "file_upload",
  "google-drive": "google_drive",
  google_drive: "google_drive",
  notion: "notion",
  web: "web",
  slack: "slack",
  onedrive: "onedrive",
  "one_drive": "onedrive",
  sharepoint: "sharepoint",
  "share_point": "sharepoint",
  dropbox: "dropbox",
  local: "local",
};

export function normalizeSourceType(value?: string | null): string | undefined {
  if (!value) return undefined;
  const normalized = value.trim().toLowerCase().replace(/[\s-]+/g, "_");
  return SOURCE_TYPE_ALIASES[normalized] ?? normalized;
}

const SOURCE_TYPE_LABELS: Record<string, string> = {
  file_upload: "File Upload",
  google_drive: "Google Drive",
  web: "Web Crawl",
  notion: "Notion",
  slack: "Slack",
  onedrive: "OneDrive",
  sharepoint: "SharePoint",
  dropbox: "Dropbox",
  local: "Local",
};

export function formatSourceTypeLabel(value?: string | null): string {
  const normalized = normalizeSourceType(value) ?? value;
  if (!normalized) return "Unknown";
  return SOURCE_TYPE_LABELS[normalized] || normalized;
}
