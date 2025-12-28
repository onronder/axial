import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RegisterForm } from '@/components/auth/RegisterForm';
import userEvent from '@testing-library/user-event';

// Mock hooks
const mockRegister = vi.fn();
const mockPush = vi.fn();
const mockToast = vi.fn();

vi.mock('@/hooks/useAuth', () => ({
    useAuth: () => ({
        register: mockRegister,
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

describe('RegisterForm Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should render registration fields and consent checkbox', () => {
        render(<RegisterForm />);

        expect(screen.getByLabelText(/First Name/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Last Name/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Email/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();

        // Consent checkbox might not have a label linked via 'for' in the standard way for library-based checks sometimes, 
        // but it has text "I agree to the Terms..."
        expect(screen.getByText(/I agree to the/i)).toBeInTheDocument();
        expect(screen.getByText(/Terms of Service/i)).toBeInTheDocument();
        expect(screen.getByText(/Privacy Policy/i)).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Create Account/i })).toBeInTheDocument();
    });

    it('should show validation error if terms are not accepted', async () => {
        const user = userEvent.setup();
        render(<RegisterForm />);

        // Fill other fields
        await user.type(screen.getByLabelText(/First Name/i), 'John');
        await user.type(screen.getByLabelText(/Last Name/i), 'Doe');
        await user.type(screen.getByLabelText(/Email/i), 'john@example.com');
        await user.type(screen.getByLabelText(/Password/i), 'password123');

        // Submit without checking box
        await user.click(screen.getByRole('button', { name: /Create Account/i }));

        // Check for validation error
        expect(await screen.findByText("You must accept the Terms and Privacy Policy")).toBeInTheDocument();
        expect(mockRegister).not.toHaveBeenCalled();
    });

    it('should submit successfully when all fields valid and terms accepted', async () => {
        const user = userEvent.setup();
        render(<RegisterForm />);

        // Fill fields
        await user.type(screen.getByLabelText(/First Name/i), 'John');
        await user.type(screen.getByLabelText(/Last Name/i), 'Doe');
        await user.type(screen.getByLabelText(/Email/i), 'john@example.com');
        await user.type(screen.getByLabelText(/Password/i), 'password123');

        // Check the box
        // The checkbox from shadcn/ui (radix) might need specific handling or just click label
        // Finding the checkbox role might be tricky if hidden input, but clicking the label works usually
        // The label text contains links, but "I agree to the..." is part of it
        // Or find by role 'checkbox'
        const checkbox = screen.getByRole('checkbox');
        await user.click(checkbox);

        // Submit
        await user.click(screen.getByRole('button', { name: /Create Account/i }));

        await waitFor(() => {
            expect(mockRegister).toHaveBeenCalledWith('John', 'Doe', 'john@example.com', 'password123');
        });

        expect(mockPush).toHaveBeenCalledWith('/dashboard');
    });
});
