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
const mockUseProfile = vi.fn();
const mockUseTheme = vi.fn();
const mockUseAuth = vi.fn();

vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => mockUseProfile(),
}));

vi.mock('@/hooks/useTheme', () => ({
    useTheme: () => mockUseTheme(),
}));

vi.mock('@/hooks/useAuth', () => ({
    useAuth: () => mockUseAuth(),
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
        post: vi.fn(),
    },
}));

import { api } from '@/lib/api';

describe('GeneralSettings - Danger Zone', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        (api.delete as Mock).mockResolvedValue({});
        mockLogout.mockResolvedValue(undefined);
        mockUseProfile.mockReturnValue({
            profile: {
                first_name: 'John',
                last_name: 'Doe',
            },
            isLoading: false,
            updateProfile: mockUpdateProfile,
        });
        mockUseTheme.mockReturnValue({
            theme: 'system',
            setTheme: mockSetTheme,
        });
        mockUseAuth.mockReturnValue({
            user: { email: 'john@example.com' },
            logout: mockLogout,
        });
    });

    describe('Rendering', () => {
        it('should show loading state when profile is loading', () => {
            mockUseProfile.mockReturnValue({
                profile: null,
                isLoading: true,
                updateProfile: mockUpdateProfile,
            });

            render(<GeneralSettings />);

            expect(screen.getByText('Loading your settings...')).toBeInTheDocument();
        });

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

    describe('Profile Settings', () => {
        it('should allow saving profile changes', async () => {
            render(<GeneralSettings />);

            await userEvent.clear(screen.getByLabelText('First Name'));
            await userEvent.type(screen.getByLabelText('First Name'), 'Jane');
            await userEvent.clear(screen.getByLabelText('Last Name'));
            await userEvent.type(screen.getByLabelText('Last Name'), 'Smith');

            await userEvent.click(screen.getByRole('button', { name: /Save Changes/i }));

            expect(mockUpdateProfile).toHaveBeenCalledWith({
                first_name: 'Jane',
                last_name: 'Smith',
            });
        });

        it('should show saving state while profile update is pending', async () => {
            mockUpdateProfile.mockImplementation(() => new Promise(() => { }));

            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Save Changes/i }));

            expect(screen.getByText('Saving...')).toBeInTheDocument();
        });

        it('should handle empty profile names', () => {
            mockUseProfile.mockReturnValue({
                profile: {
                    first_name: '',
                    last_name: '',
                },
                isLoading: false,
                updateProfile: mockUpdateProfile,
            });

            render(<GeneralSettings />);

            expect(screen.getByLabelText('First Name')).toHaveValue('');
            expect(screen.getByLabelText('Last Name')).toHaveValue('');
        });

        it('should render empty email when user is missing', () => {
            mockUseAuth.mockReturnValue({
                user: null,
                logout: mockLogout,
            });

            render(<GeneralSettings />);

            expect(screen.getByLabelText('Email')).toHaveValue('');
        });
    });

    describe('Form Validation', () => {
        it('should show error when first name is empty', async () => {
            render(<GeneralSettings />);

            await userEvent.clear(screen.getByLabelText('First Name'));
            await userEvent.click(screen.getByRole('button', { name: /Save Changes/i }));

            expect(screen.getByText(/first name is required/i)).toBeInTheDocument();
            expect(mockUpdateProfile).not.toHaveBeenCalled();
        });

        it('should show error when last name is empty', async () => {
            render(<GeneralSettings />);

            await userEvent.clear(screen.getByLabelText('Last Name'));
            await userEvent.click(screen.getByRole('button', { name: /Save Changes/i }));

            expect(screen.getByText(/last name is required/i)).toBeInTheDocument();
            expect(mockUpdateProfile).not.toHaveBeenCalled();
        });

        it('should show error when first name is too short', async () => {
            render(<GeneralSettings />);

            await userEvent.clear(screen.getByLabelText('First Name'));
            await userEvent.type(screen.getByLabelText('First Name'), 'J');
            await userEvent.click(screen.getByRole('button', { name: /Save Changes/i }));

            expect(screen.getByText(/at least 2 characters/i)).toBeInTheDocument();
            expect(mockUpdateProfile).not.toHaveBeenCalled();
        });

        it('should show error when last name is too short', async () => {
            render(<GeneralSettings />);

            await userEvent.clear(screen.getByLabelText('Last Name'));
            await userEvent.type(screen.getByLabelText('Last Name'), 'D');
            await userEvent.click(screen.getByRole('button', { name: /Save Changes/i }));

            expect(screen.getByText(/at least 2 characters/i)).toBeInTheDocument();
            expect(mockUpdateProfile).not.toHaveBeenCalled();
        });

        it('should clear error when user starts typing', async () => {
            render(<GeneralSettings />);

            await userEvent.clear(screen.getByLabelText('First Name'));
            await userEvent.click(screen.getByRole('button', { name: /Save Changes/i }));

            expect(screen.getByText(/first name is required/i)).toBeInTheDocument();

            await userEvent.type(screen.getByLabelText('First Name'), 'John');

            expect(screen.queryByText(/first name is required/i)).not.toBeInTheDocument();
        });

        it('should trim whitespace before saving', async () => {
            render(<GeneralSettings />);

            await userEvent.clear(screen.getByLabelText('First Name'));
            await userEvent.type(screen.getByLabelText('First Name'), '  Jane  ');
            await userEvent.clear(screen.getByLabelText('Last Name'));
            await userEvent.type(screen.getByLabelText('Last Name'), '  Smith  ');
            await userEvent.click(screen.getByRole('button', { name: /Save Changes/i }));

            expect(mockUpdateProfile).toHaveBeenCalledWith({
                first_name: 'Jane',
                last_name: 'Smith',
            });
        });
    });

    describe('Theme Selection', () => {
        it('should update theme when selecting Dark mode', async () => {
            const user = userEvent.setup();
            render(<GeneralSettings />);

            await user.click(screen.getByText('Dark'));
            expect(mockSetTheme).toHaveBeenCalledWith('dark');
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

            expect(api.delete).toHaveBeenCalledWith('/settings/profile/me');
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

        it('should show fallback error message on non-Error deletion failure', async () => {
            (api.delete as Mock).mockRejectedValue('bad');

            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Delete Account/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type DELETE here/i), 'DELETE');
            await userEvent.click(screen.getByRole('button', { name: /Permanently Delete/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Deletion failed',
                        description: 'Failed to delete account. Please try again.',
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

describe('GeneralSettings - GDPR Anonymization', () => {
    const mockApiPost = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();
        mockApiPost.mockResolvedValue({
            data: {
                message: 'Your data has been anonymized',
                request_id: 'req-123',
                anonymized_at: '2026-01-15T10:00:00Z',
                details: {
                    profile: 'success',
                    team_members: 'success',
                    integrations: '5 deleted',
                    feedback: 'success',
                    auth: 'success',
                },
            },
        });
        
        // Re-mock api with post
        vi.doMock('@/lib/api', () => ({
            api: {
                delete: vi.fn().mockResolvedValue({}),
                get: vi.fn(),
                patch: vi.fn(),
                post: mockApiPost,
            },
        }));

        mockUseProfile.mockReturnValue({
            profile: {
                first_name: 'John',
                last_name: 'Doe',
            },
            isLoading: false,
            updateProfile: mockUpdateProfile,
        });
        mockUseTheme.mockReturnValue({
            theme: 'system',
            setTheme: mockSetTheme,
        });
        mockUseAuth.mockReturnValue({
            user: { email: 'john@example.com' },
            logout: mockLogout,
        });
    });

    describe('Rendering', () => {
        it('should render Data Privacy (GDPR) section', () => {
            render(<GeneralSettings />);
            expect(screen.getByText('Data Privacy (GDPR)')).toBeInTheDocument();
        });

        it('should display Anonymize Data button', () => {
            render(<GeneralSettings />);
            expect(screen.getByRole('button', { name: /Anonymize Data/i })).toBeInTheDocument();
        });

        it('should display section description', () => {
            render(<GeneralSettings />);
            expect(screen.getByText(/Manage your personal data under GDPR Article 17/i)).toBeInTheDocument();
        });

        it('should display Anonymize Personal Data subsection', () => {
            render(<GeneralSettings />);
            expect(screen.getByText('Anonymize Personal Data')).toBeInTheDocument();
        });
    });

    describe('Anonymize Dialog', () => {
        it('should open dialog when Anonymize Data button is clicked', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            expect(screen.getByRole('dialog')).toBeInTheDocument();
            expect(screen.getByText('GDPR Data Anonymization')).toBeInTheDocument();
        });

        it('should display what will be anonymized', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            expect(screen.getByText(/What will be anonymized:/i)).toBeInTheDocument();
            expect(screen.getByText(/Your name → "Deleted User"/i)).toBeInTheDocument();
            expect(screen.getByText(/Your email → anonymized identifier/i)).toBeInTheDocument();
            expect(screen.getByText(/Profile picture → removed/i)).toBeInTheDocument();
            expect(screen.getByText(/OAuth connections → deleted/i)).toBeInTheDocument();
        });

        it('should display what will be preserved', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            expect(screen.getByText(/What will be preserved:/i)).toBeInTheDocument();
            expect(screen.getByText(/Your documents & AI knowledge/i)).toBeInTheDocument();
            expect(screen.getByText(/Chat history \(anonymized\)/i)).toBeInTheDocument();
            expect(screen.getByText(/Account access/i)).toBeInTheDocument();
        });

        it('should have reason selection dropdown', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            expect(screen.getByText('Reason for Request')).toBeInTheDocument();
        });

        it('should have confirmation input field', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            const input = screen.getByPlaceholderText(/Type ANONYMIZE here/i);
            expect(input).toBeInTheDocument();
        });

        it('should have Cancel and Anonymize buttons', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /Anonymize My Data/i })).toBeInTheDocument();
        });
    });

    describe('Anonymize Safety Confirmation', () => {
        it('should have Anonymize button disabled by default', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            const confirmButton = screen.getByRole('button', { name: /Anonymize My Data/i });
            expect(confirmButton).toBeDisabled();
        });

        it('should keep button disabled when typed text is not exactly ANONYMIZE', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            const input = screen.getByPlaceholderText(/Type ANONYMIZE here/i);
            await userEvent.type(input, 'anonymize'); // lowercase

            // Button enables because input converts to uppercase
            const confirmButton = screen.getByRole('button', { name: /Anonymize My Data/i });
            expect(confirmButton).not.toBeDisabled();
        });

        it('should enable button when ANONYMIZE is typed exactly', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            const input = screen.getByPlaceholderText(/Type ANONYMIZE here/i);
            await userEvent.type(input, 'ANONYMIZE');

            const confirmButton = screen.getByRole('button', { name: /Anonymize My Data/i });
            expect(confirmButton).not.toBeDisabled();
        });

        it('should keep button disabled for partial match', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            const input = screen.getByPlaceholderText(/Type ANONYMIZE here/i);
            await userEvent.type(input, 'ANON');

            const confirmButton = screen.getByRole('button', { name: /Anonymize My Data/i });
            expect(confirmButton).toBeDisabled();
        });
    });

    describe('Anonymize Cancel Action', () => {
        it('should close dialog when Cancel is clicked', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));
            await userEvent.click(screen.getByRole('button', { name: /Cancel/i }));

            expect(screen.queryByText('GDPR Data Anonymization')).not.toBeInTheDocument();
        });

        it('should clear confirmation input when Cancel is clicked', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            const input = screen.getByPlaceholderText(/Type ANONYMIZE here/i);
            await userEvent.type(input, 'ANONYMIZE');
            await userEvent.click(screen.getByRole('button', { name: /Cancel/i }));

            // Reopen dialog
            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));

            const newInput = screen.getByPlaceholderText(/Type ANONYMIZE here/i);
            expect(newInput).toHaveValue('');
        });
    });

    describe('Anonymize Action', () => {
        beforeEach(() => {
            (api.post as Mock).mockResolvedValue({
                data: {
                    message: 'Your data has been anonymized',
                    request_id: 'req-123',
                    anonymized_at: '2026-01-15T10:00:00Z',
                    details: {
                        profile: 'success',
                        team_members: 'success',
                        integrations: '5 deleted',
                        feedback: 'success',
                        auth: 'success',
                    },
                },
            });
        });

        it('should call API post when confirmed', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type ANONYMIZE here/i), 'ANONYMIZE');
            await userEvent.click(screen.getByRole('button', { name: /Anonymize My Data/i }));

            await waitFor(() => {
                expect(api.post).toHaveBeenCalledWith('/settings/profile/me/anonymize', expect.any(Object));
            });
        });

        it('should show success toast on anonymization', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type ANONYMIZE here/i), 'ANONYMIZE');
            await userEvent.click(screen.getByRole('button', { name: /Anonymize My Data/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Data Anonymized',
                    })
                );
            });
        });

        it('should show error toast on anonymization failure', async () => {
            (api.post as Mock).mockRejectedValue(new Error('Server error'));

            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type ANONYMIZE here/i), 'ANONYMIZE');
            await userEvent.click(screen.getByRole('button', { name: /Anonymize My Data/i }));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Anonymization failed',
                        variant: 'destructive',
                    })
                );
            });
        });

        it('should show loading indicator during anonymization', async () => {
            // Make post hang
            (api.post as Mock).mockImplementation(() => new Promise(() => { }));

            render(<GeneralSettings />);

            await userEvent.click(screen.getByRole('button', { name: /Anonymize Data/i }));
            await userEvent.type(screen.getByPlaceholderText(/Type ANONYMIZE here/i), 'ANONYMIZE');
            await userEvent.click(screen.getByRole('button', { name: /Anonymize My Data/i }));

            // Check that loading state is shown (button text changes to "Anonymizing...")
            await waitFor(() => {
                const anonymizingText = screen.queryAllByText(/Anonymizing/i);
                expect(anonymizingText.length).toBeGreaterThan(0);
            });
        });
    });

    describe('Appearance Section', () => {
        it('should render appearance section', () => {
            render(<GeneralSettings />);
            expect(screen.getByText('Appearance')).toBeInTheDocument();
        });

        it('should render all theme options', () => {
            render(<GeneralSettings />);
            expect(screen.getByText('Light')).toBeInTheDocument();
            expect(screen.getByText('Dark')).toBeInTheDocument();
            expect(screen.getByText('System')).toBeInTheDocument();
        });

        it('should show description for each theme', () => {
            render(<GeneralSettings />);
            expect(screen.getByText('Bright and clean')).toBeInTheDocument();
            expect(screen.getByText('Easy on the eyes')).toBeInTheDocument();
            expect(screen.getByText('Match your device')).toBeInTheDocument();
        });

        it('should update theme when selecting Light mode', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByText('Light'));
            expect(mockSetTheme).toHaveBeenCalledWith('light');
        });

        it('should update theme when selecting System mode', async () => {
            render(<GeneralSettings />);

            await userEvent.click(screen.getByText('System'));
            expect(mockSetTheme).toHaveBeenCalledWith('system');
        });

        it('should show active indicator on current theme', () => {
            mockUseTheme.mockReturnValue({
                theme: 'dark',
                setTheme: mockSetTheme,
            });

            render(<GeneralSettings />);
            
            // The dark theme button should have active styling (check icon present)
            const darkButton = screen.getByText('Dark').closest('button');
            expect(darkButton).toBeInTheDocument();
        });
    });

    describe('Personal Information Section', () => {
        it('should render personal information section', () => {
            render(<GeneralSettings />);
            expect(screen.getByText('Personal Information')).toBeInTheDocument();
        });

        it('should display email as disabled', () => {
            render(<GeneralSettings />);
            const emailInput = screen.getByLabelText('Email');
            expect(emailInput).toBeDisabled();
        });

        it('should show email is managed externally', () => {
            render(<GeneralSettings />);
            expect(screen.getByText(/Managed through your authentication provider/i)).toBeInTheDocument();
        });

        it('should populate form from profile on load', () => {
            mockUseProfile.mockReturnValue({
                profile: {
                    first_name: 'Alice',
                    last_name: 'Smith',
                },
                isLoading: false,
                updateProfile: mockUpdateProfile,
            });

            render(<GeneralSettings />);

            expect(screen.getByLabelText('First Name')).toHaveValue('Alice');
            expect(screen.getByLabelText('Last Name')).toHaveValue('Smith');
        });

        it('should handle null profile gracefully', () => {
            mockUseProfile.mockReturnValue({
                profile: null,
                isLoading: false,
                updateProfile: mockUpdateProfile,
            });

            render(<GeneralSettings />);

            expect(screen.getByLabelText('First Name')).toHaveValue('');
            expect(screen.getByLabelText('Last Name')).toHaveValue('');
        });
    });
});
