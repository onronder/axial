import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useAuth } from "@/hooks/useAuth";

const mockSignInWithPassword = vi.fn();
const mockSignUp = vi.fn();
const mockSignOut = vi.fn();
const mockSignInWithOAuth = vi.fn();
const mockResetPasswordForEmail = vi.fn();
const mockUpdateUser = vi.fn();
const mockUseSession = vi.fn();

vi.mock("@/lib/supabase", () => ({
    supabase: {
        auth: {
            signInWithPassword: (...args: unknown[]) => mockSignInWithPassword(...args),
            signUp: (...args: unknown[]) => mockSignUp(...args),
            signInWithOAuth: (...args: unknown[]) => mockSignInWithOAuth(...args),
            resetPasswordForEmail: (...args: unknown[]) => mockResetPasswordForEmail(...args),
            updateUser: (...args: unknown[]) => mockUpdateUser(...args),
            signOut: (...args: unknown[]) => mockSignOut(...args),
        },
    },
}));

vi.mock("@/components/providers/SessionProvider", () => ({
    useSession: () => mockUseSession(),
}));

describe("useAuth", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseSession.mockReturnValue({
            session: null,
            user: null,
            loading: false,
            signOut: mockSignOut,
        });
    });

    it("maps the session user into the app-specific auth shape", () => {
        mockUseSession.mockReturnValue({
            session: { access_token: "token" },
            user: {
                id: "user-123",
                email: "jane@example.com",
                user_metadata: {
                    given_name: "Jane",
                    family_name: "Doe",
                    picture: "https://example.com/avatar.png",
                },
                app_metadata: {
                    provider: "google",
                },
            },
            loading: false,
            signOut: mockSignOut,
        });

        const { result } = renderHook(() => useAuth());

        expect(result.current.user).toEqual({
            id: "user-123",
            email: "jane@example.com",
            name: "Jane Doe",
            firstName: "Jane",
            lastName: "Doe",
            avatarUrl: "https://example.com/avatar.png",
            provider: "google",
            plan: "Free",
        });
        expect(result.current.isAuthenticated).toBe(true);
        expect(result.current.loading).toBe(false);
    });

    it("returns the session from context without fetching auth state again", async () => {
        const session = { access_token: "token-123" };
        mockUseSession.mockReturnValue({
            session,
            user: null,
            loading: false,
            signOut: mockSignOut,
        });

        const { result } = renderHook(() => useAuth());

        await expect(result.current.getSession()).resolves.toBe(session);
    });

    it("delegates logout to SessionProvider signOut", async () => {
        const { result } = renderHook(() => useAuth());

        await act(async () => {
            await result.current.logout();
        });

        expect(mockSignOut).toHaveBeenCalledTimes(1);
    });

    it("signs in with email and password", async () => {
        mockSignInWithPassword.mockResolvedValue({ error: null });
        const { result } = renderHook(() => useAuth());

        await act(async () => {
            await result.current.login("test@example.com", "secret");
        });

        expect(mockSignInWithPassword).toHaveBeenCalledWith({
            email: "test@example.com",
            password: "secret",
        });
    });

    it("registers users with name metadata", async () => {
        mockSignUp.mockResolvedValue({ error: null });
        const { result } = renderHook(() => useAuth());

        await act(async () => {
            await result.current.register("Ada", "Lovelace", "ada@example.com", "secret");
        });

        expect(mockSignUp).toHaveBeenCalledWith({
            email: "ada@example.com",
            password: "secret",
            options: {
                data: {
                    full_name: "Ada Lovelace",
                    first_name: "Ada",
                    last_name: "Lovelace",
                },
            },
        });
    });

    it("requests Google OAuth with offline access defaults", async () => {
        mockSignInWithOAuth.mockResolvedValue({ error: null });
        vi.stubGlobal("window", {
            location: { origin: "https://app.example.com" },
        });

        const { result } = renderHook(() => useAuth());

        await act(async () => {
            await result.current.signInWithOAuth("google");
        });

        expect(mockSignInWithOAuth).toHaveBeenCalledWith({
            provider: "google",
            options: {
                redirectTo: "https://app.example.com/auth/callback",
                queryParams: {
                    access_type: "offline",
                    prompt: "consent",
                },
                scopes: "openid email profile",
            },
        });
        vi.unstubAllGlobals();
    });

    it("sends password reset emails with app redirect", async () => {
        mockResetPasswordForEmail.mockResolvedValue({ error: null });
        vi.stubGlobal("window", {
            location: { origin: "https://app.example.com" },
        });

        const { result } = renderHook(() => useAuth());

        await act(async () => {
            await result.current.resetPassword("reset@example.com");
        });

        expect(mockResetPasswordForEmail).toHaveBeenCalledWith(
            "reset@example.com",
            { redirectTo: "https://app.example.com/auth/reset-password" }
        );
        vi.unstubAllGlobals();
    });

    it("updates the current password", async () => {
        mockUpdateUser.mockResolvedValue({ error: null });
        const { result } = renderHook(() => useAuth());

        await act(async () => {
            await result.current.updatePassword("new-password");
        });

        expect(mockUpdateUser).toHaveBeenCalledWith({ password: "new-password" });
    });

    it("surfaces friendly auth errors", async () => {
        mockSignInWithPassword.mockResolvedValue({
            error: { message: "Invalid login credentials" },
        });
        const { result } = renderHook(() => useAuth());

        await expect(
            result.current.login("test@example.com", "wrong")
        ).rejects.toThrow("Invalid email or password. Please try again.");
    });
});
