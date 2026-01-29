import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RegisterForm } from '@/components/auth/RegisterForm';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';

// =============================================================================
// Mocks
// =============================================================================

const mockRegister = vi.fn();
const mockSignInWithOAuth = vi.fn();
const mockPush = vi.fn();
const mockToast = vi.fn();

vi.mock('@/hooks/useAuth', () => ({
    useAuth: () => ({
        register: mockRegister,
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
}));

// =============================================================================
// Test Suite
// =============================================================================

describe('RegisterForm Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockRegister.mockResolvedValue(undefined);
        mockSignInWithOAuth.mockResolvedValue(undefined);
    });

    // =========================================================================
    // Rendering Tests
    // =========================================================================

    describe('Rendering', () => {
        it('should render registration fields and consent checkbox', () => {
            render(<RegisterForm />);

            expect(screen.getByPlaceholderText('John')).toBeInTheDocument();
            expect(screen.getByPlaceholderText('Doe')).toBeInTheDocument();
            expect(screen.getByPlaceholderText('you@company.com')).toBeInTheDocument();
            expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();

            expect(screen.getByText(/I agree to the/i)).toBeInTheDocument();
            expect(screen.getByRole('checkbox')).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();
        });

        it('should render Google OAuth button', () => {
            render(<RegisterForm />);

            expect(screen.getByRole('button', { name: /Continue with Google/i })).toBeInTheDocument();
        });

        it('should render sign in link', () => {
            render(<RegisterForm />);

            expect(screen.getByText(/Already have an account/i)).toBeInTheDocument();
            expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Form Validation Tests
    // =========================================================================

    describe('Form Validation', () => {
        it('should show validation error if terms are not accepted', async () => {
            const user = userEvent.setup();
            render(<RegisterForm />);

            // Fill other fields with valid data
            await user.type(screen.getByPlaceholderText('John'), 'John');
            await user.type(screen.getByPlaceholderText('Doe'), 'Doe');
            await user.type(screen.getByPlaceholderText('you@company.com'), 'john@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), 'Password123');

            // Submit without checking box
            await user.click(screen.getByRole('button', { name: /Create Account/i }));

            // Check for validation error
            expect(await screen.findByText("You must accept the Terms and Privacy Policy")).toBeInTheDocument();
            expect(mockRegister).not.toHaveBeenCalled();
        });

        it('should not submit with password missing uppercase', async () => {
            const user = userEvent.setup();
            render(<RegisterForm />);

            await user.type(screen.getByPlaceholderText('John'), 'John');
            await user.type(screen.getByPlaceholderText('Doe'), 'Doe');
            await user.type(screen.getByPlaceholderText('you@company.com'), 'john@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), 'password123'); // no uppercase

            const checkbox = screen.getByRole('checkbox');
            await user.click(checkbox);

            await user.click(screen.getByRole('button', { name: /Create Account/i }));

            // Wait a bit
            await new Promise(resolve => setTimeout(resolve, 100));
            expect(mockRegister).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Registration Flow Tests
    // =========================================================================

    describe('Registration Flow', () => {
        it('should submit successfully when all fields valid and terms accepted', async () => {
            const user = userEvent.setup();
            render(<RegisterForm />);

            // Fill fields with valid password (has uppercase, lowercase, number, 8+ chars)
            await user.type(screen.getByPlaceholderText('John'), 'John');
            await user.type(screen.getByPlaceholderText('Doe'), 'Doe');
            await user.type(screen.getByPlaceholderText('you@company.com'), 'john@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), 'Password123');

            // Check the terms checkbox
            const checkbox = screen.getByRole('checkbox');
            await user.click(checkbox);

            // Submit
            await user.click(screen.getByRole('button', { name: /Create Account/i }));

            await waitFor(() => {
                expect(mockRegister).toHaveBeenCalledWith('John', 'Doe', 'john@example.com', 'Password123');
            });

            await waitFor(() => {
                expect(mockPush).toHaveBeenCalledWith('/dashboard');
            });
        });

        it('should show error message from Error instance on failure', async () => {
            mockRegister.mockRejectedValue(new Error('Registration blocked'));

            const user = userEvent.setup();
            render(<RegisterForm />);

            await user.type(screen.getByPlaceholderText('John'), 'Jane');
            await user.type(screen.getByPlaceholderText('Doe'), 'Smith');
            await user.type(screen.getByPlaceholderText('you@company.com'), 'jane@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), 'Password123');

            const checkbox = screen.getByRole('checkbox');
            await user.click(checkbox);

            await user.click(screen.getByRole('button', { name: /Create Account/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Registration failed',
                        description: 'Registration blocked',
                        variant: 'destructive',
                    })
                );
            });
        });

        it('should show fallback error toast when registration fails with non-Error', async () => {
            mockRegister.mockRejectedValue('oops');

            const user = userEvent.setup();
            render(<RegisterForm />);

            await user.type(screen.getByPlaceholderText('John'), 'John');
            await user.type(screen.getByPlaceholderText('Doe'), 'Doe');
            await user.type(screen.getByPlaceholderText('you@company.com'), 'john@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), 'Password123');

            const checkbox = screen.getByRole('checkbox');
            await user.click(checkbox);

            await user.click(screen.getByRole('button', { name: /Create Account/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Registration failed',
                        description: 'Please try again later.',
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
        it('should show loading indicator while submitting', async () => {
            mockRegister.mockImplementation(() => new Promise(() => {}));

            const user = userEvent.setup();
            render(<RegisterForm />);

            await user.type(screen.getByPlaceholderText('John'), 'John');
            await user.type(screen.getByPlaceholderText('Doe'), 'Doe');
            await user.type(screen.getByPlaceholderText('you@company.com'), 'john@example.com');
            await user.type(screen.getByPlaceholderText('••••••••'), 'Password123');

            const checkbox = screen.getByRole('checkbox');
            await user.click(checkbox);

            fireEvent.click(screen.getByRole('button', { name: /Create Account/i }));

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
            render(<RegisterForm />);

            await user.click(screen.getByRole('button', { name: /Continue with Google/i }));

            await waitFor(() => {
                expect(mockSignInWithOAuth).toHaveBeenCalledWith('google');
            });
        });

        it('should show error toast if Google OAuth fails', async () => {
            mockSignInWithOAuth.mockRejectedValue(new Error('Google connection failed'));

            const user = userEvent.setup();
            render(<RegisterForm />);

            await user.click(screen.getByRole('button', { name: /Continue with Google/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Google Sign-up Failed',
                        description: 'Google connection failed',
                        variant: 'destructive',
                    })
                );
            });
        });
    });
});
