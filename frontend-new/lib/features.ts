function parseBooleanEnv(value: string | undefined): boolean | null {
  if (value == null) return null;

  const normalized = value.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "off"].includes(normalized)) return false;
  return null;
}

export function isYoutubeIngestionEnabled(): boolean {
  const configured = parseBooleanEnv(process.env.NEXT_PUBLIC_YOUTUBE_INGEST_ENABLED);
  if (configured !== null) {
    return configured;
  }

  return process.env.NODE_ENV !== "production";
}
