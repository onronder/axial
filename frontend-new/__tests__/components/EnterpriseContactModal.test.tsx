import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { EnterpriseContactModal } from '@/components/billing/EnterpriseContactModal';

const mockApiPost = vi.fn();
const mockOnOpenChange = vi.fn();
const mockUseProfile = vi.fn();
const { mockToast } = vi.hoisted(() => ({
    mockToast: { success: vi.fn(), error: vi.fn() },
}));

vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => mockUseProfile(),
}));

vi.mock('@/lib/api', () => ({
    api: {
        post: (...args: unknown[]) => mockApiPost(...args),
    },
    clearAuthCache: vi.fn(),
}));

vi.mock('sonner', () => ({
    toast: mockToast,
}));

describe('EnterpriseContactModal', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiPost.mockResolvedValue({ data: { message: 'Thanks!' } });
        mockUseProfile.mockReturnValue({
            profile: { first_name: 'Jane', last_name: 'Doe' },
            isLoading: false,
            error: null,
            updateProfile: vi.fn(),
            refresh: vi.fn(),
        });
    });

    it('validates required fields before submit', async () => {
        render(<EnterpriseContactModal open={true} onOpenChange={mockOnOpenChange} />);

        const form = document.querySelector('form');
        expect(form).toBeTruthy();

        if (form) {
            fireEvent.submit(form);
        }

        expect(mockToast.error).toHaveBeenCalledWith('Please fill in all required fields');
        expect(mockApiPost).not.toHaveBeenCalled();
    });

    it('submits successfully and resets form', async () => {
        const user = userEvent.setup();
        render(<EnterpriseContactModal open={true} onOpenChange={mockOnOpenChange} />);

        await user.type(screen.getByLabelText(/Work Email/i), 'jane@company.com');
        await user.type(screen.getByLabelText(/Company/i), 'Acme Inc');

        await user.click(screen.getByRole('button', { name: /Send Inquiry/i }));

        await waitFor(() => {
            expect(mockApiPost).toHaveBeenCalledWith(
                '/billing/enterprise-inquiry',
                expect.objectContaining({
                    name: 'Jane Doe',
                    email: 'jane@company.com',
                    company: 'Acme Inc',
                })
            );
        });

        expect(mockToast.success).toHaveBeenCalledWith('Thanks!');
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);

        expect(screen.getByLabelText(/Work Email/i)).toHaveValue('');
        expect(screen.getByLabelText(/Company/i)).toHaveValue('');
    });

    it('allows editing name, message, and team size', async () => {
        const user = userEvent.setup();
        render(<EnterpriseContactModal open={true} onOpenChange={mockOnOpenChange} />);

        const nameInput = screen.getByLabelText(/Name/i);
        await user.clear(nameInput);
        await user.type(nameInput, 'Jane Smith');

        const teamSizeTrigger = screen.getByLabelText(/Team Size/i);
        await user.click(teamSizeTrigger);
        const listbox = await screen.findByRole('listbox');
        const teamSizeOption = within(listbox).getByText('11-50 people');
        await user.click(teamSizeOption);

        const messageInput = screen.getByLabelText(/How can we help/i);
        await user.type(messageInput, 'We need SSO');

        expect(nameInput).toHaveValue('Jane Smith');
        expect(teamSizeTrigger).toHaveTextContent('11-50 people');
        expect(messageInput).toHaveValue('We need SSO');
    });

    it('closes when cancel is clicked', async () => {
        const user = userEvent.setup();
        render(<EnterpriseContactModal open={true} onOpenChange={mockOnOpenChange} />);

        await user.click(screen.getByRole('button', { name: /Cancel/i }));

        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });

    it('starts with empty name when profile is missing', () => {
        mockUseProfile.mockReturnValue({
            profile: null,
            isLoading: false,
            error: null,
            updateProfile: vi.fn(),
            refresh: vi.fn(),
        });

        render(<EnterpriseContactModal open={true} onOpenChange={mockOnOpenChange} />);

        expect(screen.getByLabelText(/Name/i)).toHaveValue('');
    });

    it('uses first name only when last name is missing', async () => {
        mockUseProfile.mockReturnValue({
            profile: { first_name: 'Solo' },
            isLoading: false,
            error: null,
            updateProfile: vi.fn(),
            refresh: vi.fn(),
        });

        const user = userEvent.setup();
        render(<EnterpriseContactModal open={true} onOpenChange={mockOnOpenChange} />);

        const nameInput = screen.getByLabelText(/Name/i);
        expect(nameInput).toHaveValue('Solo');

        await user.type(screen.getByLabelText(/Work Email/i), 'solo@company.com');
        await user.type(screen.getByLabelText(/Company/i), 'Solo LLC');
        await user.click(screen.getByRole('button', { name: /Send Inquiry/i }));

        await waitFor(() => {
            expect(mockToast.success).toHaveBeenCalled();
        });

        expect(screen.getByLabelText(/Name/i)).toHaveValue('Solo');
    });

    it('resets name to empty when profile is missing after submit', async () => {
        mockUseProfile.mockReturnValue({
            profile: null,
            isLoading: false,
            error: null,
            updateProfile: vi.fn(),
            refresh: vi.fn(),
        });

        const user = userEvent.setup();
        render(<EnterpriseContactModal open={true} onOpenChange={mockOnOpenChange} />);

        await user.type(screen.getByLabelText(/Name/i), 'Temp Name');
        await user.type(screen.getByLabelText(/Work Email/i), 'temp@company.com');
        await user.type(screen.getByLabelText(/Company/i), 'Temp Co');

        await user.click(screen.getByRole('button', { name: /Send Inquiry/i }));

        await waitFor(() => {
            expect(mockToast.success).toHaveBeenCalled();
        });

        expect(screen.getByLabelText(/Name/i)).toHaveValue('');
    });

    it('uses default success message when none provided', async () => {
        mockApiPost.mockResolvedValue({ data: {} });

        const user = userEvent.setup();
        render(<EnterpriseContactModal open={true} onOpenChange={mockOnOpenChange} />);

        await user.type(screen.getByLabelText(/Work Email/i), 'jane@company.com');
        await user.type(screen.getByLabelText(/Company/i), 'Acme Inc');

        await user.click(screen.getByRole('button', { name: /Send Inquiry/i }));

        await waitFor(() => {
            expect(mockToast.success).toHaveBeenCalledWith("Thank you! We'll be in touch soon.");
        });
    });

    it('shows error toast on submit failure', async () => {
        mockApiPost.mockRejectedValue(new Error('Bad request'));

        const user = userEvent.setup();
        render(<EnterpriseContactModal open={true} onOpenChange={mockOnOpenChange} />);

        await user.type(screen.getByLabelText(/Work Email/i), 'jane@company.com');
        await user.type(screen.getByLabelText(/Company/i), 'Acme Inc');

        await user.click(screen.getByRole('button', { name: /Send Inquiry/i }));

        await waitFor(() => {
            expect(mockToast.error).toHaveBeenCalledWith('Failed to submit inquiry. Please try again.');
        });
    });

    it('shows loading state while submitting', async () => {
        mockApiPost.mockImplementation(() => new Promise(() => { }));

        const user = userEvent.setup();
        render(<EnterpriseContactModal open={true} onOpenChange={mockOnOpenChange} />);

        await user.type(screen.getByLabelText(/Work Email/i), 'jane@company.com');
        await user.type(screen.getByLabelText(/Company/i), 'Acme Inc');

        await user.click(screen.getByRole('button', { name: /Send Inquiry/i }));

        expect(document.querySelector('.animate-spin')).toBeInTheDocument();
    });
});
