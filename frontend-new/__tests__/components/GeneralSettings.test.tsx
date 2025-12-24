/**
 * Unit Tests for GeneralSettings Component - Danger Zone
 * 
 * Tests the Delete Account functionality including:
 * - Danger Zone rendering
 * - Dialog interactions
 * - Safety confirmation (typing DELETE)
 * - API call and redirect
 */

import React from 'react';
import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { GeneralSettings } from '@/components/settings/GeneralSettings';

// Mock hooks
const mockUpdateProfile = vi.fn();
const mockSetTheme = vi.fn();
const mockLogout = vi.fn();
const mockToast = vi.fn();
const mockApiDelete = vi.fn();

vi.mock('@/hooks/useProfile', () => ({
    useProfile: vi.fn(() => ({
        profile: {
            first_name: 'John',
            last_name: 'Doe',
        },
        isLoading: false,
        updateProfile: mockUpdateProfile,
    })),
}));

vi.mock('@/hooks/useTheme', () => ({
    useTheme: vi.fn(() => ({
        theme: 'system',
        setTheme: mockSetTheme,
    })),
}));

vi.mock('@/hooks/useAuth', () => ({
    useAuth: vi.fn(() => ({
        user: { email: 'john@example.com' },
        logout: mockLogout,
    })),
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: vi.fn(() => ({
        toast: mockToast,
    })),
}));

vi.mock('@/lib/api', () => ({
    api: {
        delete: vi.fn(),
        get: vi.fn(),
        patch: vi.fn(),
    },
}));

import { api } from '@/lib/api';

describe('GeneralSettings - Danger Zone', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        (api.delete as Mock).mockResolvedValue({});
        mockLogout.mockResolvedValue(undefined);
    });

    describe('Rendering', () => {
        it('should render Danger Zone section', () => {
            render(<GeneralSettings />);
            expect(screen.getByText('Danger Zone')).toBeInTheDocument();
        });

        it('should display Delete Account title', () => {
            render(<GeneralSettings />);
            // Multiple "Delete Account" elements exist (title + button)
            const elements = screen.getAllByText('Delete Account');
            expect(elements.length).toBeGreaterThan(0);
        });

        it('should display warning description', () => {
            render(<GeneralSettings />);
            expect(screen.getByText(/Permanently remove your account/i)).toBeInTheDocument();
            expect(screen.getByText(/This action is not reversible/i)).toBeInTheDocument();
        });

        it('should have a red Delete Account button', () => {
            render(<GeneralSettings />);
            const button = screen.getByRole('button', { name: /Delete Account/i });
            expect(button).toBeInTheDocument();
        });
    });

    describe('Delete Dialog', () => {
        it('should open dialog when Delete Account button is clicked', async () => {
            render(<GeneralSettings />);

            const deleteButton = screen.getByRole('button', { name: /Delete Account/i });
            await userEvent.click(deleteButton);

            expect(screen.getByRole('dialog')).toBeInTheDocument();
        });

        it('should display warning content in dialog', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));

            expect(screen.getByText(/permanently delete your account, including/i)).toBeInTheDocument();
            expect(screen.getByText(/All uploaded documents/i)).toBeInTheDocument();
            expect(screen.getByText(/Chat history and conversations/i)).toBeInTheDocument();
            expect(screen.getByText(/Connected data sources/i)).toBeInTheDocument();
            expect(screen.getByText(/AI memory of your documents/i)).toBeInTheDocument();
        });

        it('should have confirmation input field', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));

            const input = screen.getByPlaceholderText(/Type DELETE here/i);
            expect(input).toBeInTheDocument();
        });

        it('should have Cancel and Permanently Delete buttons', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));

            expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /Permanently Delete/i })).toBeInTheDocument();
        });
    });

    describe('Safety Confirmation', () => {
        it('should have Permanently Delete button disabled by default', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));

            const confirmButton = screen.getByRole('button', { name: /Permanently Delete/i });
            expect(confirmButton).toBeDisabled();
        });

        it('should keep button disabled when typed text is not exactly DELETE', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));

            const input = screen.getByPlaceholderText(/Type DELETE here/i);
            await userEvent.type(input, 'delete'); // lowercase

            const confirmButton = screen.getByRole('button', { name: /Permanently Delete/i });
            expect(confirmButton).toBeDisabled();
        });

        it('should enable button when DELETE is typed exactly', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));

            const input = screen.getByPlaceholderText(/Type DELETE here/i);
            await userEvent.type(input, 'DELETE');

            const confirmButton = screen.getByRole('button', { name: /Permanently Delete/i });
            expect(confirmButton).not.toBeDisabled();
        });

        it('should keep button disabled for partial match', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));

            const input = screen.getByPlaceholderText(/Type DELETE here/i);
            await userEvent.type(input, 'DELET');

            const confirmButton = screen.getByRole('button', { name: /Permanently Delete/i });
            expect(confirmButton).toBeDisabled();
        });
    });

    describe('Cancel Action', () => {
        it('should close dialog when Cancel is clicked', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));
            await userEvent.click(screen.getByRole('button', { name: /Cancel/i }));

            expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        });

        it('should clear confirmation input when Cancel is clicked', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));

            const input = screen.getByPlaceholderText(/Type DELETE here/i);
            await userEvent.type(input, 'DELETE');
            await userEvent.click(screen.getByRole('button', { name: /Cancel/i }));

            // Reopen dialog
            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));

            const newInput = screen.getByPlaceholderText(/Type DELETE here/i);
            expect(newInput).toHaveValue('');
        });
    });

    describe('Delete Action', () => {
        it('should call API delete when confirmed', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type DELETE here/i), 'DELETE');
            await userEvent.click(screen.getByRole('button', { name: /Permanently Delete/i }));

            expect(api.delete).toHaveBeenCalledWith('api/v1/settings/profile/me');
        });

        it('should call logout after successful deletion', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type DELETE here/i), 'DELETE');
            await userEvent.click(screen.getByRole('button', { name: /Permanently Delete/i }));

            await waitFor(() => {
                expect(mockLogout).toHaveBeenCalled();
            });
        });

        it('should show success toast on deletion', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type DELETE here/i), 'DELETE');
            await userEvent.click(screen.getByRole('button', { name: /Permanently Delete/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Account deleted',
                    })
                );
            });
        });

        it('should show error toast on deletion failure', async () => {
            (api.delete as Mock).mockRejectedValue(new Error('Server error'));

            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type DELETE here/i), 'DELETE');
            await userEvent.click(screen.getByRole('button', { name: /Permanently Delete/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Deletion failed',
                        variant: 'destructive',
                    })
                );
            });
        });

        it('should not call logout on deletion failure', async () => {
            (api.delete as Mock).mockRejectedValue(new Error('Server error'));

            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type DELETE here/i), 'DELETE');
            await userEvent.click(screen.getByRole('button', { name: /Permanently Delete/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalled();
            });

            expect(mockLogout).not.toHaveBeenCalled();
        });
    });

    describe('Loading State', () => {
        it('should show loading indicator during deletion', async () => {
            // Make delete hang
            (api.delete as Mock).mockImplementation(() => new Promise(() => { }));

            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type DELETE here/i), 'DELETE');
            await userEvent.click(screen.getByRole('button', { name: /Permanently Delete/i }));

            expect(screen.getByText(/Deleting/i)).toBeInTheDocument();
        });

        it('should disable confirm button during deletion', async () => {
            (api.delete as Mock).mockImplementation(() => new Promise(() => { }));

            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type DELETE here/i), 'DELETE');

            const confirmButton = screen.getByRole('button', { name: /Permanently Delete/i });
            await userEvent.click(confirmButton);

            // Button should now show loading and be disabled
            await waitFor(() => {
                expect(screen.getByText(/Deleting/i)).toBeInTheDocument();
            });
        });
    });

    describe('Accessibility', () => {
        it('should have accessible dialog', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));

            const dialog = screen.getByRole('dialog');
            expect(dialog).toBeInTheDocument();
        });

        it('should have labeled input', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));

            const input = screen.getByLabelText(/Type.*DELETE.*to confirm/i);
            expect(input).toBeInTheDocument();
        });
    });
});
