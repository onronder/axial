import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import ResetPasswordPage from '@/app/auth/reset-password/page';

// =============================================================================
// Mocks
// =============================================================================

const mockGetSession = vi.fn();
const mockUpdateUser = vi.fn();
const mockPush = vi.fn();
const mockToast = vi.fn();

vi.mock('@/lib/supabase', () => ({
    supabase: {
        auth: {
            getSession: () => mockGetSession(),
            updateUser: (...args: unknown[]) => mockUpdateUser(...args),
        },
    },
}));

vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: mockPush,
    }),
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({
        toast: mockToast,
    }),
}));

// =============================================================================
// Test Suite
// =============================================================================

describe('ResetPasswordPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Default: valid session exists
        mockGetSession.mockResolvedValue({
            data: { session: { user: { id: 'test-user' } } },
        });
        mockUpdateUser.mockResolvedValue({ error: null });
    });

    // =========================================================================
    // Session Validation Tests
    // =========================================================================

    describe('Session Validation', () => {
        it('should show loading spinner while checking session', () => {
            // Keep session check pending
            mockGetSession.mockReturnValue(new Promise(() => {}));

            render(<ResetPasswordPage />);

            expect(document.querySelector('.animate-spin')).toBeInTheDocument();
        });

        it('should redirect to forgot-password if no valid session', async () => {
            mockGetSession.mockResolvedValue({
                data: { session: null },
            });

            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Invalid or expired link',
                        variant: 'destructive',
                    })
                );
                expect(mockPush).toHaveBeenCalledWith('/forgot-password');
            });
        });

        it('should show form when valid session exists', async () => {
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByText(/set new password/i)).toBeInTheDocument();
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
                expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // Rendering Tests
    // =========================================================================

    describe('Rendering', () => {
        it('should render password requirements list', async () => {
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
                expect(screen.getByText(/one uppercase letter/i)).toBeInTheDocument();
                expect(screen.getByText(/one lowercase letter/i)).toBeInTheDocument();
                expect(screen.getByText(/one number/i)).toBeInTheDocument();
            });
        });

        it('should render update password button', async () => {
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /update password/i })).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // Form Validation Tests
    // =========================================================================

    describe('Form Validation', () => {
        it('should show error for password less than 8 characters', async () => {
            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'Pass1');
            await user.type(screen.getByLabelText(/confirm password/i), 'Pass1');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            await waitFor(() => {
                expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument();
            });
            expect(mockUpdateUser).not.toHaveBeenCalled();
        });

        it('should show error for password without uppercase', async () => {
            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'password123');
            await user.type(screen.getByLabelText(/confirm password/i), 'password123');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            await waitFor(() => {
                expect(screen.getByText(/password must contain at least one uppercase letter/i)).toBeInTheDocument();
            });
            expect(mockUpdateUser).not.toHaveBeenCalled();
        });

        it('should show error for password without lowercase', async () => {
            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'PASSWORD123');
            await user.type(screen.getByLabelText(/confirm password/i), 'PASSWORD123');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            await waitFor(() => {
                expect(screen.getByText(/password must contain at least one lowercase letter/i)).toBeInTheDocument();
            });
            expect(mockUpdateUser).not.toHaveBeenCalled();
        });

        it('should show error for password without number', async () => {
            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'PasswordABC');
            await user.type(screen.getByLabelText(/confirm password/i), 'PasswordABC');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            await waitFor(() => {
                expect(screen.getByText(/password must contain at least one number/i)).toBeInTheDocument();
            });
            expect(mockUpdateUser).not.toHaveBeenCalled();
        });

        it('should show error for mismatched passwords', async () => {
            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'Password123');
            await user.type(screen.getByLabelText(/confirm password/i), 'Password456');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            await waitFor(() => {
                expect(screen.getByText(/passwords don't match/i)).toBeInTheDocument();
            });
            expect(mockUpdateUser).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Password Update Flow Tests
    // =========================================================================

    describe('Password Update Flow', () => {
        it('should call updateUser with valid password', async () => {
            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'NewPassword123');
            await user.type(screen.getByLabelText(/confirm password/i), 'NewPassword123');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            await waitFor(() => {
                expect(mockUpdateUser).toHaveBeenCalledWith({
                    password: 'NewPassword123',
                });
            });
        });

        it('should show success state after password update', async () => {
            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'NewPassword123');
            await user.type(screen.getByLabelText(/confirm password/i), 'NewPassword123');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            await waitFor(() => {
                expect(screen.getByText(/password updated!/i)).toBeInTheDocument();
                expect(screen.getByText(/redirecting you to login/i)).toBeInTheDocument();
            });
        });

        it('should show success toast after password update', async () => {
            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'NewPassword123');
            await user.type(screen.getByLabelText(/confirm password/i), 'NewPassword123');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Password updated!',
                    })
                );
            });
        });
    });

    // =========================================================================
    // Error Handling Tests
    // =========================================================================

    describe('Error Handling', () => {
        it('should show error toast when update fails', async () => {
            mockUpdateUser.mockResolvedValue({
                error: { message: 'Password too weak' },
            });

            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'NewPassword123');
            await user.type(screen.getByLabelText(/confirm password/i), 'NewPassword123');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            // The component checks instanceof Error for the error message
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Error',
                        variant: 'destructive',
                    })
                );
            });
        });

        it('should not show success state when update fails', async () => {
            mockUpdateUser.mockResolvedValue({
                error: { message: 'Update failed' },
            });

            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'NewPassword123');
            await user.type(screen.getByLabelText(/confirm password/i), 'NewPassword123');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalled();
            });

            // Should still show form
            expect(screen.queryByText(/redirecting you to login/i)).not.toBeInTheDocument();
            expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Loading State Tests
    // =========================================================================

    describe('Loading State', () => {
        it('should show loading spinner while updating password', async () => {
            // Keep update pending
            const pendingUpdate = new Promise(() => {});
            mockUpdateUser.mockReturnValue(pendingUpdate);

            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'NewPassword123');
            await user.type(screen.getByLabelText(/confirm password/i), 'NewPassword123');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            expect(document.querySelector('.animate-spin')).toBeInTheDocument();
        });

        it('should disable submit button while loading', async () => {
            const pendingUpdate = new Promise(() => {});
            mockUpdateUser.mockReturnValue(pendingUpdate);

            const user = userEvent.setup();
            render(<ResetPasswordPage />);

            await waitFor(() => {
                expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
            });

            await user.type(screen.getByLabelText(/new password/i), 'NewPassword123');
            await user.type(screen.getByLabelText(/confirm password/i), 'NewPassword123');
            await user.click(screen.getByRole('button', { name: /update password/i }));

            expect(screen.getByRole('button', { name: /update password/i })).toBeDisabled();
        });
    });
});
