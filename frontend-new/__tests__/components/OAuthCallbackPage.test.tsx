import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

import OAuthCallbackPage from "@/app/oauth/callback/page";
import { api } from "@/lib/api";

let searchParams = new URLSearchParams();
const pushMock = vi.fn();

vi.mock("next/navigation", () => ({
    useRouter: () => ({
        push: pushMock,
        replace: vi.fn(),
        back: vi.fn(),
        forward: vi.fn(),
        refresh: vi.fn(),
        prefetch: vi.fn(),
    }),
    useSearchParams: () => searchParams,
}));

vi.mock("@/lib/api", () => ({
    api: {
        post: vi.fn(),
        get: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
    },
    clearAuthCache: vi.fn(),
}));

// Mock GitHubRepoSelector to simplify testing
vi.mock("@/components/data-sources/GitHubRepoSelector", () => ({
    GitHubRepoSelector: ({ open, onComplete, onOpenChange }: { 
        open: boolean; 
        onComplete: () => void;
        onOpenChange: (open: boolean) => void;
    }) => {
        if (!open) return null;
        return (
            <div data-testid="github-repo-selector">
                <button onClick={onComplete}>Complete Selection</button>
                <button onClick={() => onOpenChange(false)}>Cancel</button>
            </div>
        );
    },
}));

describe("OAuthCallbackPage", () => {
    beforeEach(() => {
        searchParams = new URLSearchParams();
        pushMock.mockClear();
        vi.mocked(api.post).mockClear();
        vi.mocked(api.post).mockResolvedValue({ data: {} });
        sessionStorage.clear();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("exchanges code with Microsoft endpoint for OneDrive", async () => {
        searchParams = new URLSearchParams("code=abc123&state=onedrive");
        sessionStorage.setItem("microsoft_pkce_onedrive", "verifier-123");

        render(<OAuthCallbackPage />);

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith("/integrations/microsoft/exchange", {
                code: "abc123",
                target_type: "onedrive",
                code_verifier: "verifier-123",
            });
        });

        // Wait for the redirect (setTimeout 1500ms in the component)
        await waitFor(() => {
            expect(pushMock).toHaveBeenCalledWith("/dashboard/settings/data-sources");
        }, { timeout: 3000 });
    });

    it("exchanges code with Microsoft endpoint for SharePoint", async () => {
        searchParams = new URLSearchParams("code=share123&state=sharepoint");
        sessionStorage.setItem("microsoft_pkce_sharepoint", "verifier-456");

        render(<OAuthCallbackPage />);

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith("/integrations/microsoft/exchange", {
                code: "share123",
                target_type: "sharepoint",
                code_verifier: "verifier-456",
            });
        });
    });

    it("shows error when access is denied", async () => {
        searchParams = new URLSearchParams("error=access_denied&state=onedrive");

        render(<OAuthCallbackPage />);

        // The error message includes additional context
        expect(await screen.findByText(/Access was denied/i)).toBeInTheDocument();
        expect(api.post).not.toHaveBeenCalled();
    });

    it("shows error when no code is provided", async () => {
        searchParams = new URLSearchParams("state=onedrive");

        render(<OAuthCallbackPage />);

        // The error message includes additional context
        expect(await screen.findByText(/No authorization code/i)).toBeInTheDocument();
        expect(api.post).not.toHaveBeenCalled();
    });

    // =========================================================================
    // GitHub OAuth Tests
    // =========================================================================

    it("exchanges code with GitHub endpoint", async () => {
        searchParams = new URLSearchParams("code=gh_code_123&state=github");

        render(<OAuthCallbackPage />);

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith("/integrations/github/exchange", {
                code: "gh_code_123",
            });
        });
    });

    it("shows repo selector after successful GitHub exchange", async () => {
        searchParams = new URLSearchParams("code=gh_success&state=github");

        render(<OAuthCallbackPage />);

        await waitFor(() => {
            expect(api.post).toHaveBeenCalledWith("/integrations/github/exchange", {
                code: "gh_success",
            });
        });

        // Wait for the repo selector to appear (setTimeout 1500ms in the component)
        await waitFor(() => {
            expect(screen.getByTestId("github-repo-selector")).toBeInTheDocument();
        }, { timeout: 3000 });
    });

    it("redirects after completing GitHub repo selection", async () => {
        searchParams = new URLSearchParams("code=gh_complete&state=github");

        render(<OAuthCallbackPage />);

        // Wait for repo selector
        await waitFor(() => {
            expect(screen.getByTestId("github-repo-selector")).toBeInTheDocument();
        }, { timeout: 3000 });

        // Complete selection
        fireEvent.click(screen.getByText("Complete Selection"));

        // Should redirect
        expect(pushMock).toHaveBeenCalledWith("/dashboard/settings/data-sources");
    });

    it("redirects when GitHub repo selector is cancelled", async () => {
        searchParams = new URLSearchParams("code=gh_cancel&state=github");

        render(<OAuthCallbackPage />);

        // Wait for repo selector
        await waitFor(() => {
            expect(screen.getByTestId("github-repo-selector")).toBeInTheDocument();
        }, { timeout: 3000 });

        // Cancel
        fireEvent.click(screen.getByText("Cancel"));

        // Should still redirect
        expect(pushMock).toHaveBeenCalledWith("/dashboard/settings/data-sources");
    });

    it("shows error when GitHub access is denied", async () => {
        searchParams = new URLSearchParams("error=access_denied&state=github");

        render(<OAuthCallbackPage />);

        // The error message includes additional context
        expect(await screen.findByText(/Access was denied/i)).toBeInTheDocument();
        expect(api.post).not.toHaveBeenCalled();
    });
});
