import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { LoginForm } from '@/components/auth/LoginForm';

// =============================================================================
// Mocks
// =============================================================================

const mockLogin = vi.fn();
const mockSignInWithOAuth = vi.fn();
const mockPush = vi.fn();
const mockToast = vi.fn();
const mockSearchParamsGet = vi.fn();

vi.mock('@/hooks/useAuth', () => ({
    useAuth: () => ({
        login: mockLogin,
        signInWithOAuth: mockSignInWithOAuth,
    }),
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({
        toast: mockToast,
    }),
}));

vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: mockPush,
    }),
    useSearchParams: () => ({
        get: mockSearchParamsGet,
    }),
}));

vi.mock('@/lib/storage', () => ({
    safeLocalStorage: {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
    },
}));

// =============================================================================
// Test Suite
// =============================================================================

describe('LoginForm Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockSearchParamsGet.mockReturnValue(null);
        mockLogin.mockResolvedValue(undefined);
        mockSignInWithOAuth.mockResolvedValue(undefined);
    });

    // =========================================================================
    // Rendering Tests
    // =========================================================================

    describe('Rendering', () => {
        it('should render email and password fields', () => {
            render(<LoginForm />);

            expect(screen.getByPlaceholderText('you@company.com')).toBeInTheDocument();
            expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
        });

        it('should render sign in button', () => {
            render(<LoginForm />);

            expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
        });

        it('should render Google OAuth button', () => {
            render(<LoginForm />);

            expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument();
        });

        it('should render remember me checkbox', () => {
            render(<LoginForm />);

            expect(screen.getByRole('checkbox')).toBeInTheDocument();
            expect(screen.getByText(/remember me/i)).toBeInTheDocument();
        });

        it('should render forgot password link', () => {
            render(<LoginForm />);

            expect(screen.getByText(/forgot password/i)).toBeInTheDocument();
        });

        it('should render sign up link', () => {
            render(<LoginForm />);

            expect(screen.getByText(/don't have an account/i)).toBeInTheDocument();
            expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Form Validation Tests
    // =========================================================================

    describe('Form Validation', () => {
        it('should not call login with invalid email', async () => {
            const user = userEvent.setup();
            render(<LoginForm />);

            await user.type(screen.getByPlaceholderText('you@company.com'), 'invalid-email');
            await user.type(screen.getByPlaceholderText('••••••••'), 'password123');
            await user.click(screen.getByRole('button', { name: /sign in/i }));

            // Wait a bit for any async validation
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Login should not be called with invalid email (form validation prevents it)
            expect(mockLogin).not.toHaveBeenCalled();
        });

        it('should not call login with short password', async () => {
            const user = userEvent.setup();
            render(<LoginForm />);

            await user.type(screen.getByPlaceholderText('you@company.com'), 'test@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), '12345');
            await user.click(screen.getByRole('button', { name: /sign in/i }));

            // Wait a bit for any async validation
            await new Promise(resolve => setTimeout(resolve, 100));
            
            // Login should not be called with short password
            expect(mockLogin).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Login Flow Tests
    // =========================================================================

    describe('Login Flow', () => {
        it('should call login with email and password on valid submit', async () => {
            const user = userEvent.setup();
            render(<LoginForm />);

            await user.type(screen.getByPlaceholderText('you@company.com'), 'test@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), 'password123');
            await user.click(screen.getByRole('button', { name: /sign in/i }));

            await waitFor(() => {
                expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
            });
        });

        it('should show success toast and redirect on successful login', async () => {
            const user = userEvent.setup();
            render(<LoginForm />);

            await user.type(screen.getByPlaceholderText('you@company.com'), 'test@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), 'password123');
            await user.click(screen.getByRole('button', { name: /sign in/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Welcome back!',
                    })
                );
                expect(mockPush).toHaveBeenCalledWith('/dashboard');
            });
        });

        it('should redirect to custom URL if redirectTo param is set', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'redirectTo') return '/custom-page';
                return null;
            });

            const user = userEvent.setup();
            render(<LoginForm />);

            await user.type(screen.getByPlaceholderText('you@company.com'), 'test@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), 'password123');
            await user.click(screen.getByRole('button', { name: /sign in/i }));

            await waitFor(() => {
                expect(mockPush).toHaveBeenCalledWith('/custom-page');
            });
        });

        it('should show error toast on login failure', async () => {
            mockLogin.mockRejectedValue(new Error('Invalid credentials'));

            const user = userEvent.setup();
            render(<LoginForm />);

            await user.type(screen.getByPlaceholderText('you@company.com'), 'test@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), 'password123');
            await user.click(screen.getByRole('button', { name: /sign in/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Login failed',
                        description: 'Invalid credentials',
                        variant: 'destructive',
                    })
                );
            });
        });

        it('should show loading spinner while logging in', async () => {
            // Keep login pending indefinitely
            mockLogin.mockImplementation(() => new Promise(() => {}));

            const user = userEvent.setup();
            render(<LoginForm />);

            await user.type(screen.getByPlaceholderText('you@company.com'), 'test@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), 'password123');
            
            // Click submit and immediately check for spinner
            fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

            await waitFor(() => {
                expect(document.querySelector('.animate-spin')).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // Google OAuth Tests
    // =========================================================================

    describe('Google OAuth', () => {
        it('should call signInWithOAuth when Google button is clicked', async () => {
            const user = userEvent.setup();
            render(<LoginForm />);

            await user.click(screen.getByRole('button', { name: /continue with google/i }));

            await waitFor(() => {
                expect(mockSignInWithOAuth).toHaveBeenCalledWith('google', expect.any(Object));
            });
        });

        it('should show error toast if Google OAuth fails', async () => {
            mockSignInWithOAuth.mockRejectedValue(new Error('Google connection failed'));

            const user = userEvent.setup();
            render(<LoginForm />);

            await user.click(screen.getByRole('button', { name: /continue with google/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Google Sign-in Failed',
                        description: 'Google connection failed',
                        variant: 'destructive',
                    })
                );
            });
        });

        it('should disable form inputs while OAuth is loading', async () => {
            // Keep OAuth pending
            mockSignInWithOAuth.mockImplementation(() => new Promise(() => {}));

            const user = userEvent.setup();
            render(<LoginForm />);

            await user.click(screen.getByRole('button', { name: /continue with google/i }));

            await waitFor(() => {
                expect(screen.getByPlaceholderText('you@company.com')).toBeDisabled();
                expect(screen.getByPlaceholderText('••••••••')).toBeDisabled();
            });
        });
    });

    // =========================================================================
    // Password Visibility Tests
    // =========================================================================

    describe('Password Visibility Toggle', () => {
        it('should toggle password visibility', async () => {
            const user = userEvent.setup();
            render(<LoginForm />);

            // Get the password input by placeholder since label matches the toggle button too
            const passwordInput = screen.getByPlaceholderText('••••••••');
            expect(passwordInput).toHaveAttribute('type', 'password');

            // Click show password button
            const toggleButton = screen.getByRole('button', { name: /show password/i });
            await user.click(toggleButton);

            expect(passwordInput).toHaveAttribute('type', 'text');

            // Click hide password button (now the aria-label changed)
            const hideButton = screen.getByRole('button', { name: /hide password/i });
            await user.click(hideButton);

            expect(passwordInput).toHaveAttribute('type', 'password');
        });
    });

    // =========================================================================
    // Session Error Tests
    // =========================================================================

    describe('Session Error Display', () => {
        it('should display session expired error from URL params', () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'error') return 'session_expired';
                return null;
            });

            render(<LoginForm />);

            expect(screen.getByText(/session expired/i)).toBeInTheDocument();
            expect(screen.getByText(/your session has expired/i)).toBeInTheDocument();
        });

        it('should display auth required error from URL params', () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'error') return 'auth_required';
                return null;
            });

            render(<LoginForm />);

            expect(screen.getByText(/authentication required/i)).toBeInTheDocument();
        });

        it('should allow dismissing session error', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'error') return 'session_expired';
                return null;
            });

            const user = userEvent.setup();
            render(<LoginForm />);

            expect(screen.getByText(/session expired/i)).toBeInTheDocument();

            // Click dismiss button
            const dismissButton = screen.getByRole('button', { name: /dismiss/i });
            await user.click(dismissButton);

            expect(screen.queryByText(/session expired/i)).not.toBeInTheDocument();
        });
    });
});
