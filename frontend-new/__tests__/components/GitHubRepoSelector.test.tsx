import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor, fireEvent, within } from "@testing-library/react";
import { GitHubRepoSelector, type GitHubRepo } from "@/components/data-sources/GitHubRepoSelector";
import { api } from "@/lib/api";

// Mock the API
vi.mock("@/lib/api", () => ({
    api: {
        get: vi.fn(),
        post: vi.fn(),
    },
    clearAuthCache: vi.fn(),
}));

const mockRepos: GitHubRepo[] = [
    {
        id: 1,
        name: "frontend",
        full_name: "onronder/frontend",
        description: "React frontend application",
        private: false,
        fork: false,
        archived: false,
        default_branch: "main",
        owner: "onronder",
        owner_type: "User",
        updated_at: "2026-01-15T10:00:00Z",
        language: "TypeScript",
        stargazers_count: 42,
    },
    {
        id: 2,
        name: "backend",
        full_name: "onronder/backend",
        description: "Python FastAPI backend",
        private: true,
        fork: false,
        archived: false,
        default_branch: "main",
        owner: "onronder",
        owner_type: "User",
        updated_at: "2026-01-14T10:00:00Z",
        language: "Python",
        stargazers_count: 10,
    },
    {
        id: 3,
        name: "org-repo",
        full_name: "my-org/org-repo",
        description: "Organization repository",
        private: true,
        fork: false,
        archived: false,
        default_branch: "develop",
        owner: "my-org",
        owner_type: "Organization",
        updated_at: "2026-01-13T10:00:00Z",
        language: "Go",
        stargazers_count: 5,
    },
    {
        id: 4,
        name: "archived-project",
        full_name: "onronder/archived-project",
        description: "Old archived project",
        private: false,
        fork: false,
        archived: true,
        default_branch: "master",
        owner: "onronder",
        owner_type: "User",
        language: "JavaScript",
        stargazers_count: 0,
    },
    {
        id: 5,
        name: "forked-lib",
        full_name: "onronder/forked-lib",
        description: "A forked library",
        private: false,
        fork: true,
        archived: false,
        default_branch: "main",
        owner: "onronder",
        owner_type: "User",
        language: "Rust",
        stargazers_count: 100,
    },
];

describe("GitHubRepoSelector", () => {
    const mockOnComplete = vi.fn();
    const mockOnOpenChange = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        vi.mocked(api.get).mockResolvedValue({ data: { repositories: mockRepos } });
        vi.mocked(api.post).mockResolvedValue({ data: { success: true } });
    });

    it("renders loading state initially", () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        expect(screen.getByText("Loading repositories...")).toBeInTheDocument();
    });

    it("fetches and displays repositories", async () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(api.get).toHaveBeenCalledWith("/integrations/github/repos");
        });

        // Check repos are displayed
        expect(await screen.findByText("frontend")).toBeInTheDocument();
        expect(screen.getByText("backend")).toBeInTheDocument();
        expect(screen.getByText("org-repo")).toBeInTheDocument();
    });

    it("groups repos by owner", async () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("frontend")).toBeInTheDocument();
        });

        // Check owner headers are displayed
        expect(screen.getByText("onronder")).toBeInTheDocument();
        expect(screen.getByText("my-org")).toBeInTheDocument();
    });

    it("shows repo badges correctly", async () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("frontend")).toBeInTheDocument();
        });

        // Check for badges
        expect(screen.getAllByText("Private").length).toBeGreaterThan(0);
        expect(screen.getAllByText("Public").length).toBeGreaterThan(0);
        expect(screen.getByText("Archived")).toBeInTheDocument();
        expect(screen.getByText("Fork")).toBeInTheDocument();
    });

    it("allows selecting individual repos", async () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("frontend")).toBeInTheDocument();
        });

        // Click on a repo to select it
        const frontendItem = screen.getByText("frontend").closest("[role='button']");
        expect(frontendItem).toBeInTheDocument();
        fireEvent.click(frontendItem!);

        // Check selection count
        expect(screen.getByText(/1 of \d+ selected/)).toBeInTheDocument();
    });

    it("allows selecting all repos", async () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("frontend")).toBeInTheDocument();
        });

        // Click select all
        const selectAllButton = screen.getByText("Select all");
        fireEvent.click(selectAllButton);

        // Check all are selected
        expect(screen.getByText("5 of 5 selected")).toBeInTheDocument();
        expect(screen.getByText("Deselect all")).toBeInTheDocument();
    });

    it("filters repos by search query", async () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("frontend")).toBeInTheDocument();
        });

        // Search for "Python"
        const searchInput = screen.getByPlaceholderText("Search repositories...");
        fireEvent.change(searchInput, { target: { value: "Python" } });

        // Only backend should be visible (has Python language)
        expect(screen.getByText("backend")).toBeInTheDocument();
        expect(screen.queryByText("frontend")).not.toBeInTheDocument();
    });

    it("saves selected repos on complete", async () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("frontend")).toBeInTheDocument();
        });

        // Select a repo
        const frontendItem = screen.getByText("frontend").closest("[role='button']");
        fireEvent.click(frontendItem!);

        // Click save
        const saveButton = screen.getByRole("button", { name: /Save Selection/ });
        fireEvent.click(saveButton);

        // Check API was called
        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith("/integrations/github/repos/select", {
                selected_repositories: [
                    {
                        full_name: "onronder/frontend",
                        branch: "main",
                        enabled: true,
                    },
                ],
            });
        });

        // Check complete callback
        await waitFor(() => {
            expect(mockOnComplete).toHaveBeenCalled();
        });
    });

    it("shows error when trying to save with no selection", async () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("frontend")).toBeInTheDocument();
        });

        // Save button should be disabled when no repos selected
        const saveButton = screen.getByRole("button", { name: /Save Selection/ });
        expect(saveButton).toBeDisabled();
    });

    it("closes modal on cancel", async () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("frontend")).toBeInTheDocument();
        });

        // Click cancel
        const cancelButton = screen.getByRole("button", { name: "Cancel" });
        fireEvent.click(cancelButton);

        // Check onOpenChange was called with false
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it("shows error state when API fails", async () => {
        vi.mocked(api.get).mockRejectedValueOnce(new Error("Network error"));

        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("Failed to load repositories. Please try again.")).toBeInTheDocument();
        });

        // Should show retry button
        expect(screen.getByRole("button", { name: "Try Again" })).toBeInTheDocument();
    });

    it("shows empty state when no repos found", async () => {
        vi.mocked(api.get).mockResolvedValueOnce({ data: { repositories: [] } });

        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("No repositories found.")).toBeInTheDocument();
        });
    });

    it("shows no match state when search has no results", async () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("frontend")).toBeInTheDocument();
        });

        // Search for something that doesn't exist
        const searchInput = screen.getByPlaceholderText("Search repositories...");
        fireEvent.change(searchInput, { target: { value: "nonexistent-repo-xyz" } });

        expect(screen.getByText("No repositories match your search.")).toBeInTheDocument();
    });

    it("does not fetch repos when modal is closed", () => {
        render(
            <GitHubRepoSelector
                open={false}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        expect(api.get).not.toHaveBeenCalled();
    });

    it("displays repo metadata correctly", async () => {
        render(
            <GitHubRepoSelector
                open={true}
                onOpenChange={mockOnOpenChange}
                onComplete={mockOnComplete}
            />
        );

        await waitFor(() => {
            expect(screen.getByText("frontend")).toBeInTheDocument();
        });

        // Check language
        expect(screen.getByText("TypeScript")).toBeInTheDocument();
        expect(screen.getByText("Python")).toBeInTheDocument();

        // Check stars (42 stars for frontend)
        expect(screen.getByText("42")).toBeInTheDocument();

        // Check branch
        expect(screen.getAllByText("main").length).toBeGreaterThan(0);
        expect(screen.getByText("develop")).toBeInTheDocument();
    });
});
