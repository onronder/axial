import { afterEach, describe, expect, it, vi } from "vitest";

import { isYoutubeIngestionEnabled } from "@/lib/features";

describe("feature flags", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("disables youtube ingestion when the public env flag is false", () => {
    vi.stubEnv("NEXT_PUBLIC_YOUTUBE_INGEST_ENABLED", "false");
    expect(isYoutubeIngestionEnabled()).toBe(false);
  });

  it("enables youtube ingestion in non-production builds when the env flag is unset", () => {
    vi.stubEnv("NEXT_PUBLIC_YOUTUBE_INGEST_ENABLED", "");
    const originalNodeEnv = process.env.NODE_ENV;
    vi.stubEnv("NODE_ENV", "test");

    expect(isYoutubeIngestionEnabled()).toBe(true);

    vi.stubEnv("NODE_ENV", originalNodeEnv || "test");
  });
});
