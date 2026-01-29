import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ForgotPasswordForm } from '@/components/auth/ForgotPasswordForm';

// =============================================================================
// Mocks
// =============================================================================

const mockResetPasswordForEmail = vi.fn();
const mockToast = vi.fn();

vi.mock('@/lib/supabase', () => ({
    supabase: {
        auth: {
            resetPasswordForEmail: (...args: unknown[]) => mockResetPasswordForEmail(...args),
        },
    },
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({
        toast: mockToast,
    }),
}));

// =============================================================================
// Test Suite
// =============================================================================

describe('ForgotPasswordForm Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockResetPasswordForEmail.mockResolvedValue({ error: null });
    });

    // =========================================================================
    // Rendering Tests
    // =========================================================================

    describe('Rendering', () => {
        it('should render the reset password heading', () => {
            render(<ForgotPasswordForm />);

            expect(screen.getByRole('heading', { name: /reset password/i })).toBeInTheDocument();
        });

        it('should render email input field', () => {
            render(<ForgotPasswordForm />);

            expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
            expect(screen.getByPlaceholderText(/you@company.com/i)).toBeInTheDocument();
        });

        it('should render send reset link button', () => {
            render(<ForgotPasswordForm />);

            expect(screen.getByRole('button', { name: /send reset link/i })).toBeInTheDocument();
        });

        it('should render sign in link', () => {
            render(<ForgotPasswordForm />);

            expect(screen.getByText(/remember your password/i)).toBeInTheDocument();
            expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Form Validation Tests
    // =========================================================================

    describe('Form Validation', () => {
        it('should not call reset with invalid email', async () => {
            const user = userEvent.setup();
            render(<ForgotPasswordForm />);

            await user.type(screen.getByPlaceholderText(/you@company.com/i), 'invalid-email');
            await user.click(screen.getByRole('button', { name: /send reset link/i }));

            // Wait for validation
            await new Promise(resolve => setTimeout(resolve, 100));
            expect(mockResetPasswordForEmail).not.toHaveBeenCalled();
        });

        it('should not call reset for empty email', async () => {
            const user = userEvent.setup();
            render(<ForgotPasswordForm />);

            await user.click(screen.getByRole('button', { name: /send reset link/i }));

            // Wait for validation
            await new Promise(resolve => setTimeout(resolve, 100));
            expect(mockResetPasswordForEmail).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Reset Password Flow Tests
    // =========================================================================

    describe('Reset Password Flow', () => {
        it('should call resetPasswordForEmail with correct email', async () => {
            const user = userEvent.setup();
            render(<ForgotPasswordForm />);

            await user.type(screen.getByPlaceholderText(/you@company.com/i), 'test@example.com');
            await user.click(screen.getByRole('button', { name: /send reset link/i }));

            await waitFor(() => {
                expect(mockResetPasswordForEmail).toHaveBeenCalledWith(
                    'test@example.com',
                    expect.objectContaining({
                        redirectTo: expect.stringContaining('/auth/reset-password'),
                    })
                );
            });
        });

        it('should show success state after sending reset link', async () => {
            const user = userEvent.setup();
            render(<ForgotPasswordForm />);

            await user.type(screen.getByPlaceholderText(/you@company.com/i), 'test@example.com');
            await user.click(screen.getByRole('button', { name: /send reset link/i }));

            await waitFor(() => {
                expect(screen.getByRole('heading', { name: /check your email/i })).toBeInTheDocument();
            });
        });

        it('should show success toast after sending reset link', async () => {
            const user = userEvent.setup();
            render(<ForgotPasswordForm />);

            await user.type(screen.getByPlaceholderText(/you@company.com/i), 'test@example.com');
            await user.click(screen.getByRole('button', { name: /send reset link/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Reset link sent!',
                        description: 'Check your email for the password reset link.',
                    })
                );
            });
        });

        it('should allow sending another link from success state', async () => {
            const user = userEvent.setup();
            render(<ForgotPasswordForm />);

            // Send first link
            await user.type(screen.getByPlaceholderText(/you@company.com/i), 'test@example.com');
            await user.click(screen.getByRole('button', { name: /send reset link/i }));

            await waitFor(() => {
                expect(screen.getByRole('heading', { name: /check your email/i })).toBeInTheDocument();
            });

            // Click "Send another link"
            await user.click(screen.getByRole('button', { name: /send another link/i }));

            // Should show form again
            await waitFor(() => {
                expect(screen.getByPlaceholderText(/you@company.com/i)).toBeInTheDocument();
                expect(screen.getByRole('button', { name: /send reset link/i })).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // Error Handling Tests
    // =========================================================================

    describe('Error Handling', () => {
        it('should show error toast when reset fails', async () => {
            // The component throws the error object, and checks instanceof Error
            // Plain objects use fallback message
            mockResetPasswordForEmail.mockResolvedValue({
                error: { message: 'Email not found' },
            });

            const user = userEvent.setup();
            render(<ForgotPasswordForm />);

            await user.type(screen.getByPlaceholderText(/you@company.com/i), 'test@example.com');
            await user.click(screen.getByRole('button', { name: /send reset link/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Error',
                        variant: 'destructive',
                    })
                );
            });
        });

        it('should not show success state when reset fails', async () => {
            mockResetPasswordForEmail.mockResolvedValue({
                error: { message: 'Rate limit exceeded' },
            });

            const user = userEvent.setup();
            render(<ForgotPasswordForm />);

            await user.type(screen.getByPlaceholderText(/you@company.com/i), 'test@example.com');
            await user.click(screen.getByRole('button', { name: /send reset link/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalled();
            });

            // Should still show form, not success state
            expect(screen.queryByRole('heading', { name: /check your email/i })).not.toBeInTheDocument();
            expect(screen.getByPlaceholderText(/you@company.com/i)).toBeInTheDocument();
        });

        it('should handle unexpected errors gracefully', async () => {
            mockResetPasswordForEmail.mockRejectedValue(new Error('Network error'));

            const user = userEvent.setup();
            render(<ForgotPasswordForm />);

            await user.type(screen.getByPlaceholderText(/you@company.com/i), 'test@example.com');
            await user.click(screen.getByRole('button', { name: /send reset link/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Error',
                        variant: 'destructive',
                    })
                );
            });
        });
    });

    // =========================================================================
    // Loading State Tests
    // =========================================================================

    describe('Loading State', () => {
        it('should show loading spinner while sending reset link', async () => {
            // Keep reset pending indefinitely
            mockResetPasswordForEmail.mockImplementation(() => new Promise(() => {}));

            const user = userEvent.setup();
            render(<ForgotPasswordForm />);

            await user.type(screen.getByPlaceholderText(/you@company.com/i), 'test@example.com');
            fireEvent.click(screen.getByRole('button', { name: /send reset link/i }));

            await waitFor(() => {
                expect(document.querySelector('.animate-spin')).toBeInTheDocument();
            });
        });

        it('should disable submit button while loading', async () => {
            mockResetPasswordForEmail.mockImplementation(() => new Promise(() => {}));

            const user = userEvent.setup();
            render(<ForgotPasswordForm />);

            await user.type(screen.getByPlaceholderText(/you@company.com/i), 'test@example.com');
            fireEvent.click(screen.getByRole('button', { name: /send reset link/i }));

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /send reset link/i })).toBeDisabled();
            });
        });
    });
});
