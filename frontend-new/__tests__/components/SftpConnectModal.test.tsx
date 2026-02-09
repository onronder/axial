import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SftpConnectModal } from '@/components/data-sources/SftpConnectModal';

// =============================================================================
// Mocks
// =============================================================================

const mockToast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

const mockApiPost = vi.fn();
vi.mock('@/lib/api', () => ({
    api: {
        post: (...args: unknown[]) => mockApiPost(...args),
    },
    clearAuthCache: vi.fn(),
}));

// =============================================================================
// Test Suite
// =============================================================================

describe('SftpConnectModal Component', () => {
    const mockOnOpenChange = vi.fn();
    const mockOnConnected = vi.fn();

    const defaultProps = {
        open: true,
        onOpenChange: mockOnOpenChange,
        onConnected: mockOnConnected,
    };

    beforeEach(() => {
        vi.clearAllMocks();
        mockApiPost.mockResolvedValue({ data: { success: true } });
    });

    // =========================================================================
    // Rendering Tests
    // =========================================================================

    describe('Rendering', () => {
        it('should render the modal when open', () => {
            render(<SftpConnectModal {...defaultProps} />);

            expect(screen.getByText('Connect SFTP')).toBeInTheDocument();
            expect(screen.getByText(/Securely connect your SFTP server/i)).toBeInTheDocument();
        });

        it('should not render when closed', () => {
            render(<SftpConnectModal {...defaultProps} open={false} />);

            expect(screen.queryByText('Connect SFTP')).not.toBeInTheDocument();
        });

        it('should render all form fields', () => {
            render(<SftpConnectModal {...defaultProps} />);

            expect(screen.getByText('Host')).toBeInTheDocument();
            expect(screen.getByText('Port')).toBeInTheDocument();
            expect(screen.getByText('Username')).toBeInTheDocument();
            expect(screen.getByText('Password (optional)')).toBeInTheDocument();
            expect(screen.getByText('Private Key (optional, PEM)')).toBeInTheDocument();
            expect(screen.getByText('Root Path')).toBeInTheDocument();
        });

        it('should render Connect and Cancel buttons', () => {
            render(<SftpConnectModal {...defaultProps} />);

            expect(screen.getByRole('button', { name: /connect/i })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
        });

        it('should have default port value of 22', () => {
            render(<SftpConnectModal {...defaultProps} />);

            const portInput = screen.getByDisplayValue('22');
            expect(portInput).toBeInTheDocument();
        });

        it('should have default root path of /', () => {
            render(<SftpConnectModal {...defaultProps} />);

            const rootPathInput = screen.getByDisplayValue('/');
            expect(rootPathInput).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Input Handling Tests
    // =========================================================================

    describe('Input Handling', () => {
        it('should update host input value', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            expect(hostInput).toHaveValue('my-server.com');
        });

        it('should update port input value', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            const portInput = screen.getByDisplayValue('22');
            await user.clear(portInput);
            await user.type(portInput, '2222');

            expect(portInput).toHaveValue('2222');
        });

        it('should update username input value', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            const usernameInputs = screen.getAllByRole('textbox');
            const usernameInput = usernameInputs[2]; // Username is 3rd textbox
            await user.type(usernameInput, 'testuser');

            expect(usernameInput).toHaveValue('testuser');
        });

        it('should update password input value', async () => {
            render(<SftpConnectModal {...defaultProps} />);

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'secret123' } });

            expect(passwordInput).toHaveValue('secret123');
        });

        it('should update private key input value', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            const privateKeyInput = screen.getByPlaceholderText('-----BEGIN PRIVATE KEY-----');
            await user.type(privateKeyInput, '-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----');

            expect(privateKeyInput).toHaveValue('-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----');
        });

        it('should update root path input value', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            const rootPathInput = screen.getByDisplayValue('/');
            await user.clear(rootPathInput);
            await user.type(rootPathInput, '/home/user/data');

            expect(rootPathInput).toHaveValue('/home/user/data');
        });
    });

    // =========================================================================
    // Validation Tests
    // =========================================================================

    describe('Validation', () => {
        it('should show error when host is empty', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill username but not host
            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            // Fill password
            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            expect(screen.getByText('Host and username are required.')).toBeInTheDocument();
        });

        it('should show error when username is empty', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill host but not username
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            // Fill password
            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            expect(screen.getByText('Host and username are required.')).toBeInTheDocument();
        });

        it('should show error when neither password nor private key is provided', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill host and username
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            // Submit without password or key
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            expect(screen.getByText('Provide either a password or a private key.')).toBeInTheDocument();
        });

        it('should show error for invalid port - zero', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill required fields
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Set invalid port
            const portInput = screen.getByDisplayValue('22');
            await user.clear(portInput);
            await user.type(portInput, '0');

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            expect(screen.getByText('Port must be a valid integer between 1 and 65535.')).toBeInTheDocument();
        });

        it('should show error for invalid port - too high', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill required fields
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Set invalid port
            const portInput = screen.getByDisplayValue('22');
            await user.clear(portInput);
            await user.type(portInput, '99999');

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            expect(screen.getByText('Port must be a valid integer between 1 and 65535.')).toBeInTheDocument();
        });

        it('should show error for non-numeric port', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill required fields
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Set invalid port
            const portInput = screen.getByDisplayValue('22');
            await user.clear(portInput);
            await user.type(portInput, 'abc');

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            expect(screen.getByText('Port must be a valid integer between 1 and 65535.')).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Successful Submission Tests
    // =========================================================================

    describe('Successful Submission', () => {
        it('should submit form with password authentication', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'secret123' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalledWith('/integrations/sftp/connect', {
                    host: 'my-server.com',
                    port: 22,
                    username: 'testuser',
                    password: 'secret123',
                    private_key: null,
                    root_path: '/',
                });
            });
        });

        it('should submit form with private key authentication', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const privateKeyInput = screen.getByPlaceholderText('-----BEGIN PRIVATE KEY-----');
            await user.type(privateKeyInput, 'my-private-key');

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalledWith('/integrations/sftp/connect', {
                    host: 'my-server.com',
                    port: 22,
                    username: 'testuser',
                    password: null,
                    private_key: 'my-private-key',
                    root_path: '/',
                });
            });
        });

        it('should submit form with custom port and root path', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const portInput = screen.getByDisplayValue('22');
            await user.clear(portInput);
            await user.type(portInput, '2222');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            const rootPathInput = screen.getByDisplayValue('/');
            await user.clear(rootPathInput);
            await user.type(rootPathInput, '/home/data');

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalledWith('/integrations/sftp/connect', {
                    host: 'my-server.com',
                    port: 2222,
                    username: 'testuser',
                    password: 'password',
                    private_key: null,
                    root_path: '/home/data',
                });
            });
        });

        it('should show success toast on successful connection', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith({
                    title: 'SFTP connected',
                    description: 'Connection verified and saved.',
                });
            });
        });

        it('should call onConnected callback on success', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockOnConnected).toHaveBeenCalled();
            });
        });

        it('should close modal on successful connection', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockOnOpenChange).toHaveBeenCalledWith(false);
            });
        });
    });

    // =========================================================================
    // Error Handling Tests
    // =========================================================================

    describe('Error Handling', () => {
        it('should show API error message on failure', async () => {
            mockApiPost.mockRejectedValueOnce({
                response: { data: { detail: 'Connection refused' } },
            });

            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(screen.getByText('Connection refused')).toBeInTheDocument();
            });
        });

        it('should show default error message when API error has no detail', async () => {
            mockApiPost.mockRejectedValueOnce(new Error('Network error'));

            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(screen.getByText('Failed to connect to SFTP. Please verify the details.')).toBeInTheDocument();
            });
        });

        it('should not call onConnected on error', async () => {
            mockApiPost.mockRejectedValueOnce(new Error('Network error'));

            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(screen.getByText('Failed to connect to SFTP. Please verify the details.')).toBeInTheDocument();
            });

            expect(mockOnConnected).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Loading State Tests
    // =========================================================================

    describe('Loading State', () => {
        it('should show "Connecting..." while submitting', async () => {
            // Slow down the API call
            mockApiPost.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 500)));

            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await act(async () => {
                fireEvent.click(submitBtn);
            });

            // Check loading state
            await waitFor(() => {
                expect(screen.getByText('Connecting...')).toBeInTheDocument();
            });
        });

        it('should disable buttons while submitting', async () => {
            mockApiPost.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 500)));

            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await act(async () => {
                fireEvent.click(submitBtn);
            });

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled();
            });
        });
    });

    // =========================================================================
    // Modal Close Tests
    // =========================================================================

    describe('Modal Close', () => {
        it('should call onOpenChange with false when Cancel is clicked', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            const cancelBtn = screen.getByRole('button', { name: /cancel/i });
            await user.click(cancelBtn);

            expect(mockOnOpenChange).toHaveBeenCalledWith(false);
        });

        it('should reset form fields when modal is closed', async () => {
            const user = userEvent.setup();
            const { rerender } = render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            // Close modal
            const cancelBtn = screen.getByRole('button', { name: /cancel/i });
            await user.click(cancelBtn);

            // Reopen
            rerender(<SftpConnectModal {...defaultProps} open={true} />);

            // Form should be reset
            expect(screen.getByPlaceholderText('sftp.example.com')).toHaveValue('');
        });

        it('should clear error message when modal is closed', async () => {
            const user = userEvent.setup();
            const { rerender } = render(<SftpConnectModal {...defaultProps} />);

            // Trigger validation error
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            expect(screen.getByText('Host and username are required.')).toBeInTheDocument();

            // Close modal
            const cancelBtn = screen.getByRole('button', { name: /cancel/i });
            await user.click(cancelBtn);

            // Reopen
            rerender(<SftpConnectModal {...defaultProps} open={true} />);

            // Error should be cleared
            expect(screen.queryByText('Host and username are required.')).not.toBeInTheDocument();
        });
    });

    // =========================================================================
    // Form Prevention Tests
    // =========================================================================

    describe('Form Prevention', () => {
        it('should prevent default form submission', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit form via form element
            const form = hostInput.closest('form');
            if (form) {
                fireEvent.submit(form);
            }

            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalled();
            });
        });
    });

    // =========================================================================
    // Edge Cases
    // =========================================================================

    describe('Edge Cases', () => {
        it('should trim whitespace from host', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form with whitespace
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, '  my-server.com  ');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalledWith('/integrations/sftp/connect', expect.objectContaining({
                    host: 'my-server.com',
                }));
            });
        });

        it('should trim whitespace from username', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], '  testuser  ');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalledWith('/integrations/sftp/connect', expect.objectContaining({
                    username: 'testuser',
                }));
            });
        });

        it('should handle empty root path as default', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal {...defaultProps} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Clear root path
            const rootPathInput = screen.getByDisplayValue('/');
            await user.clear(rootPathInput);

            // Submit
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalledWith('/integrations/sftp/connect', expect.objectContaining({
                    root_path: '/',
                }));
            });
        });

        it('should work without onConnected callback', async () => {
            const user = userEvent.setup();
            render(<SftpConnectModal open={true} onOpenChange={mockOnOpenChange} />);

            // Fill form
            const hostInput = screen.getByPlaceholderText('sftp.example.com');
            await user.type(hostInput, 'my-server.com');

            const usernameInputs = screen.getAllByRole('textbox');
            await user.type(usernameInputs[2], 'testuser');

            const passwordInput = screen.getByPlaceholderText('••••••••');
            fireEvent.change(passwordInput, { target: { value: 'password' } });

            // Submit - should not throw
            const submitBtn = screen.getByRole('button', { name: /^connect$/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalled();
            });
        });
    });
});
