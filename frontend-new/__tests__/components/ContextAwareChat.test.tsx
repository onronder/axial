/**
 * Universal Context - ClarificationCard Tests
 * 
 * Tests the clarification UI component in isolation.
 * Integration tests for full ChatPage flow should use Playwright E2E.
 */

import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ClarificationCard } from "@/components/chat/ClarificationCard";

describe("ClarificationCard", () => {
  it("renders message and candidates correctly", () => {
    render(
      <ClarificationCard
        message="I found info in multiple sources"
        candidates={[
          { id: "github://org/repo@main", summary: "Backend API", type: "github_repo" },
          { id: "s3://bucket/docs", summary: "Documentation", type: "s3_bucket" },
        ]}
        onSelectScope={vi.fn()}
      />
    );

    // Header text is always "Multiple contexts found"
    expect(screen.getByText("Multiple contexts found")).toBeInTheDocument();
    // Message text is passed as prop
    expect(screen.getByText(/I found info in multiple sources/i)).toBeInTheDocument();
    // Should have two candidate buttons
    const buttons = screen.getAllByRole("button");
    // 2 candidates + 1 "search all" link-button = at least 2 buttons
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });

  it("calls onSelectScope when a candidate is clicked", async () => {
    const user = userEvent.setup();
    const onSelectScope = vi.fn();

    render(
      <ClarificationCard
        message="Pick a scope"
        candidates={[
          { id: "github://org/repo@main", summary: "Backend", type: "github_repo" },
        ]}
        onSelectScope={onSelectScope}
      />
    );

    // Find the candidate button (not the "search all" button)
    const candidateButtons = screen.getAllByRole("button");
    const candidateButton = candidateButtons.find(btn => 
      btn.textContent?.includes("GitHub Repository")
    );
    expect(candidateButton).toBeDefined();
    
    await user.click(candidateButton!);
    expect(onSelectScope).toHaveBeenCalledWith("github://org/repo@main");
  });

  it("shows loading state and disables buttons when isLoading is true", () => {
    render(
      <ClarificationCard
        message="Pick a scope"
        candidates={[
          { id: "github://org/repo@main", summary: "Backend", type: "github_repo" },
        ]}
        onSelectScope={vi.fn()}
        isLoading={true}
      />
    );

    // Candidate buttons should be disabled when loading
    const buttons = screen.getAllByRole("button");
    buttons.forEach(btn => {
      expect(btn).toBeDisabled();
    });
  });

  it("renders multiple candidates with correct types", () => {
    render(
      <ClarificationCard
        message="Select a source"
        candidates={[
          { id: "github://org/repo@main", summary: "Code repo", type: "github_repo" },
          { id: "s3://bucket/docs/", summary: "S3 docs", type: "s3_bucket" },
          { id: "box://folder/123:Marketing", summary: "Marketing files", type: "box_folder" },
        ]}
        onSelectScope={vi.fn()}
      />
    );

    // All three candidates should be rendered with their type labels
    expect(screen.getByText("GitHub Repository")).toBeInTheDocument();
    expect(screen.getByText("S3 Bucket")).toBeInTheDocument();
    expect(screen.getByText("Box Folder")).toBeInTheDocument();
  });

  it("shows 'search all sources' option", () => {
    render(
      <ClarificationCard
        message="Pick a scope"
        candidates={[
          { id: "github://org/repo@main", summary: "Backend", type: "github_repo" },
        ]}
        onSelectScope={vi.fn()}
      />
    );

    expect(screen.getByText(/search all sources/i)).toBeInTheDocument();
  });

  it("calls onSelectScope with __all__ when 'search all' is clicked", async () => {
    const user = userEvent.setup();
    const onSelectScope = vi.fn();

    render(
      <ClarificationCard
        message="Pick a scope"
        candidates={[
          { id: "github://org/repo@main", summary: "Backend", type: "github_repo" },
        ]}
        onSelectScope={onSelectScope}
      />
    );

    await user.click(screen.getByText(/search all sources/i));
    expect(onSelectScope).toHaveBeenCalledWith("__all__");
  });

  it("displays candidate summaries when provided", () => {
    render(
      <ClarificationCard
        message="Select a source"
        candidates={[
          { id: "github://org/repo@main", summary: "This is the backend API codebase", type: "github_repo" },
        ]}
        onSelectScope={vi.fn()}
      />
    );

    expect(screen.getByText(/This is the backend API codebase/i)).toBeInTheDocument();
  });
});
