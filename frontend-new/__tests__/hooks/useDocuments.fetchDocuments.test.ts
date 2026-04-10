import { describe, expect, it, vi, beforeEach } from "vitest";

const mockGet = vi.fn();

vi.mock("@/lib/api", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}));

import { fetchDocuments } from "@/hooks/useDocuments";

describe("fetchDocuments", () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it("parses the new object response shape with separate failed files", async () => {
    mockGet.mockResolvedValue({
      data: {
        documents: [
          {
            id: "doc-1",
            title: "Indexed Doc",
            source_type: "google_drive",
            status: "indexed",
            indexing_status: "completed",
            created_at: "2026-04-10T10:00:00Z",
          },
        ],
        failed_files: [
          {
            id: "fail-1",
            title: "Broken.pdf",
            source_type: "file_upload",
            status: "failed",
            indexing_status: "failed",
            created_at: "2026-04-10T09:00:00Z",
            metadata: { error: "Parse failed" },
          },
        ],
        total_documents: 42,
        failed_count: 3,
      },
      headers: {
        "x-total-count": "42",
        "x-failed-count": "3",
      },
    });

    const result = await fetchDocuments({ page: 1, pageSize: 10, search: "test" });

    expect(result.total).toBe(42);
    expect(result.failedCount).toBe(3);
    expect(result.documents).toHaveLength(1);
    expect(result.failedFiles).toHaveLength(1);
    expect(result.failedFiles[0].indexingStatus).toBe("failed");
    expect(result.failedFiles[0].errorMessage).toBe("Parse failed");
  });

  it("remains backward-compatible with legacy array responses", async () => {
    mockGet.mockResolvedValue({
      data: [
        {
          id: "doc-1",
          title: "Legacy Doc",
          source_type: "google_drive",
          status: "indexed",
          indexing_status: "completed",
          created_at: "2026-04-10T10:00:00Z",
        },
      ],
      headers: {
        "x-total-count": "1",
        "x-failed-count": "0",
      },
    });

    const result = await fetchDocuments({ page: 1, pageSize: 10 });

    expect(result.total).toBe(1);
    expect(result.failedCount).toBe(0);
    expect(result.documents).toHaveLength(1);
    expect(result.failedFiles).toEqual([]);
  });
});
