import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { S3ConnectModal } from '@/components/data-sources/S3ConnectModal';

// =============================================================================
// Mocks
// =============================================================================

const mockToast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast }),
}));

const mockPost = vi.fn();
vi.mock('@/lib/api', () => ({
  api: {
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

// Mock clipboard API with proper stubbing
const mockClipboardWrite = vi.fn().mockResolvedValue(undefined);
const originalNavigator = { ...navigator };
beforeAll(() => {
  Object.defineProperty(navigator, 'clipboard', {
    value: {
      writeText: mockClipboardWrite,
      readText: vi.fn(),
    },
    writable: true,
    configurable: true,
  });
});

afterAll(() => {
  Object.defineProperty(navigator, 'clipboard', {
    value: originalNavigator.clipboard,
    writable: true,
    configurable: true,
  });
});

describe('S3ConnectModal Component', () => {
  const defaultProps = {
    open: true,
    onOpenChange: vi.fn(),
    onConnected: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe('Rendering', () => {
    it('should render the modal when open', () => {
      render(<S3ConnectModal {...defaultProps} />);

      expect(screen.getByText('Connect Amazon S3')).toBeInTheDocument();
      expect(screen.getByText(/Enterprise Feature/i)).toBeInTheDocument();
    });

    it('should not render when closed', () => {
      render(<S3ConnectModal {...defaultProps} open={false} />);

      // Radix Dialog may keep content mounted but hidden - check for dialog role
      const dialog = screen.queryByRole('dialog');
      expect(dialog).not.toBeInTheDocument();
    });

    it('should render all form fields', () => {
      render(<S3ConnectModal {...defaultProps} />);

      expect(screen.getByLabelText(/Access Key ID/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Secret Access Key/i)).toBeInTheDocument();
      // Use getAllByText since there may be multiple matching elements (label + placeholder)
      const bucketNameElements = screen.getAllByText(/Bucket Name/i);
      expect(bucketNameElements.length).toBeGreaterThan(0);
      const folderPrefixElements = screen.getAllByText(/Folder Prefix/i);
      expect(folderPrefixElements.length).toBeGreaterThan(0);
    });

    it('should render the region dropdown with default value', () => {
      render(<S3ConnectModal {...defaultProps} />);

      // The Select component should have a trigger showing the default region
      const regionSelect = screen.getByRole('combobox', { name: /region/i });
      expect(regionSelect).toBeInTheDocument();
      // Default value is us-east-1 which displays as "US East (N. Virginia)"
      expect(regionSelect).toHaveTextContent(/US East.*Virginia/i);
    });

    it('should render security notice about encryption', () => {
      render(<S3ConnectModal {...defaultProps} />);

      expect(screen.getByText(/AES-256/i)).toBeInTheDocument();
      // Multiple elements contain "encrypted" - use getAllByText
      const encryptedElements = screen.getAllByText(/encrypted/i);
      expect(encryptedElements.length).toBeGreaterThan(0);
    });

    it('should render enterprise feature alert', () => {
      render(<S3ConnectModal {...defaultProps} />);

      expect(screen.getByText(/Enterprise Feature/i)).toBeInTheDocument();
      expect(screen.getByText(/Enterprise plans/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Form Validation Tests
  // ===========================================================================

  describe('Form Validation', () => {
    it('should show error when Access Key ID is empty', async () => {
      render(<S3ConnectModal {...defaultProps} />);

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText('Access Key ID is required')).toBeInTheDocument();
      });
    });

    it('should show error when Access Key ID is too short', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'SHORT');

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText(/at least 16 characters/i)).toBeInTheDocument();
      });
    });

    it('should show error when Access Key ID has invalid characters', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      // Input lowercase - the component converts to uppercase, so this will pass
      // Let's input special characters
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EX@MPL');

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText(/uppercase letters and numbers/i)).toBeInTheDocument();
      });
    });

    it('should show error when Secret Access Key is empty', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      // Fill in valid access key
      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EXAMPLE');

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText('Secret Access Key is required')).toBeInTheDocument();
      });
    });

    it('should show error when Secret Access Key is too short', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EXAMPLE');

      const secretKeyInput = screen.getByLabelText(/Secret Access Key/i);
      await user.type(secretKeyInput, 'short');

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText(/at least 20 characters/i)).toBeInTheDocument();
      });
    });

    it('should show error when bucket name is empty', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EXAMPLE');

      const secretKeyInput = screen.getByLabelText(/Secret Access Key/i);
      await user.type(secretKeyInput, 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY');

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText('Bucket name is required')).toBeInTheDocument();
      });
    });

    it('should show error when bucket name is too short', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EXAMPLE');

      const secretKeyInput = screen.getByLabelText(/Secret Access Key/i);
      await user.type(secretKeyInput, 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY');

      const bucketInput = screen.getByPlaceholderText('my-documents-bucket');
      await user.type(bucketInput, 'ab');

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText(/3-63 characters/i)).toBeInTheDocument();
      });
    });

    it('should show error when bucket name has invalid format', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EXAMPLE');

      const secretKeyInput = screen.getByLabelText(/Secret Access Key/i);
      await user.type(secretKeyInput, 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY');

      const bucketInput = screen.getByPlaceholderText('my-documents-bucket');
      // Bucket names with uppercase are invalid
      await user.type(bucketInput, '-invalid-bucket');

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText(/must start\/end with letter or number/i)).toBeInTheDocument();
      });
    });

    it('should show error when prefix is empty (cost protection)', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EXAMPLE');

      const secretKeyInput = screen.getByLabelText(/Secret Access Key/i);
      await user.type(secretKeyInput, 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY');

      const bucketInput = screen.getByPlaceholderText('my-documents-bucket');
      await user.type(bucketInput, 'my-valid-bucket');

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText(/Prefix is required/i)).toBeInTheDocument();
      });
    });

    it('should show error when prefix starts with forward slash', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EXAMPLE');

      const secretKeyInput = screen.getByLabelText(/Secret Access Key/i);
      await user.type(secretKeyInput, 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY');

      const bucketInput = screen.getByPlaceholderText('my-documents-bucket');
      await user.type(bucketInput, 'my-valid-bucket');

      const prefixInput = screen.getByPlaceholderText(/documents\/knowledge-base/i);
      await user.type(prefixInput, '/invalid-prefix');

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText(/should not start with a forward slash/i)).toBeInTheDocument();
      });
    });

    it('should clear field errors when user types', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      // Trigger validation error
      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText('Access Key ID is required')).toBeInTheDocument();
      });

      // Type in the field
      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'A');

      // Error should be cleared
      expect(screen.queryByText('Access Key ID is required')).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Form Submission Tests
  // ===========================================================================

  describe('Form Submission', () => {
    const fillValidForm = async () => {
      const user = userEvent.setup();

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EXAMPLE');

      const secretKeyInput = screen.getByLabelText(/Secret Access Key/i);
      await user.type(secretKeyInput, 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY');

      const bucketInput = screen.getByPlaceholderText('my-documents-bucket');
      await user.type(bucketInput, 'my-test-bucket');

      const prefixInput = screen.getByPlaceholderText(/documents\/knowledge-base/i);
      await user.type(prefixInput, 'documents/');
    };

    it('should submit form with correct data on success', async () => {
      mockPost.mockResolvedValueOnce({ data: { success: true } });

      render(<S3ConnectModal {...defaultProps} />);
      await fillValidForm();

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(mockPost).toHaveBeenCalledWith('/integrations/s3/connect', {
          access_key_id: 'AKIAIOSFODNN7EXAMPLE',
          secret_access_key: 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',
          region: 'us-east-1',
          bucket_name: 'my-test-bucket',
          prefix: 'documents/',
        });
      });
    });

    it('should show loading state while submitting', async () => {
      // Create a promise that won't resolve immediately
      let resolvePromise: () => void;
      const pendingPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });
      mockPost.mockImplementationOnce(() => pendingPromise);

      render(<S3ConnectModal {...defaultProps} />);
      await fillValidForm();

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText('Connecting...')).toBeInTheDocument();
      });

      // Cleanup
      resolvePromise!();
    });

    it('should call onConnected and onOpenChange on success', async () => {
      mockPost.mockResolvedValueOnce({ data: { success: true } });

      render(<S3ConnectModal {...defaultProps} />);
      await fillValidForm();

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(defaultProps.onConnected).toHaveBeenCalled();
        expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
      });
    });

    it('should show success toast on successful connection', async () => {
      mockPost.mockResolvedValueOnce({ data: { success: true } });

      render(<S3ConnectModal {...defaultProps} />);
      await fillValidForm();

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(mockToast).toHaveBeenCalledWith(
          expect.objectContaining({
            title: 'S3 Connected',
            description: expect.stringContaining('my-test-bucket'),
          })
        );
      });
    });
  });

  // ===========================================================================
  // Error Handling Tests
  // ===========================================================================

  describe('Error Handling', () => {
    const fillValidForm = async () => {
      const user = userEvent.setup();

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EXAMPLE');

      const secretKeyInput = screen.getByLabelText(/Secret Access Key/i);
      await user.type(secretKeyInput, 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY');

      const bucketInput = screen.getByPlaceholderText('my-documents-bucket');
      await user.type(bucketInput, 'my-test-bucket');

      const prefixInput = screen.getByPlaceholderText(/documents\/knowledge-base/i);
      await user.type(prefixInput, 'documents/');
    };

    it('should show enterprise error when 403 with ENTERPRISE_REQUIRED', async () => {
      mockPost.mockRejectedValueOnce({
        response: {
          status: 403,
          data: {
            detail: {
              error: 'ENTERPRISE_REQUIRED',
              current_plan: 'starter',
              message: 'Enterprise plan required',
            },
          },
        },
      });

      render(<S3ConnectModal {...defaultProps} />);
      await fillValidForm();

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText(/requires an Enterprise plan/i)).toBeInTheDocument();
        expect(screen.getByText(/starter/i)).toBeInTheDocument();
      });
    });

    it('should show generic 403 error for access denied', async () => {
      mockPost.mockRejectedValueOnce({
        response: {
          status: 403,
          data: { detail: 'Access denied' },
        },
      });

      render(<S3ConnectModal {...defaultProps} />);
      await fillValidForm();

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText(/Access denied.*Enterprise plans/i)).toBeInTheDocument();
      });
    });

    it('should show credential error on 401', async () => {
      mockPost.mockRejectedValueOnce({
        response: {
          status: 401,
          data: { detail: 'Invalid credentials' },
        },
      });

      render(<S3ConnectModal {...defaultProps} />);
      await fillValidForm();

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText(/Invalid AWS credentials/i)).toBeInTheDocument();
      });
    });

    it('should show validation error on 400', async () => {
      mockPost.mockRejectedValueOnce({
        response: {
          status: 400,
          data: { detail: 'Bucket does not exist' },
        },
      });

      render(<S3ConnectModal {...defaultProps} />);
      await fillValidForm();

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText('Bucket does not exist')).toBeInTheDocument();
      });
    });

    it('should show generic error for unknown errors', async () => {
      mockPost.mockRejectedValueOnce({
        response: {
          status: 500,
          data: { detail: 'Internal server error' },
        },
      });

      render(<S3ConnectModal {...defaultProps} />);
      await fillValidForm();

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText('Internal server error')).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // UI Interaction Tests
  // ===========================================================================

  describe('UI Interactions', () => {
    it('should toggle secret key visibility', async () => {
      render(<S3ConnectModal {...defaultProps} />);

      const secretKeyInput = screen.getByLabelText(/Secret Access Key/i);
      expect(secretKeyInput).toHaveAttribute('type', 'password');

      // Find and click the visibility toggle button
      const toggleButton = screen.getByRole('button', { name: '' });
      fireEvent.click(toggleButton);

      expect(secretKeyInput).toHaveAttribute('type', 'text');

      // Click again to hide
      fireEvent.click(toggleButton);
      expect(secretKeyInput).toHaveAttribute('type', 'password');
    });

    it('should have copy button for IAM policy', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      // Expand the accordion
      const accordionTrigger = screen.getByText(/Recommended IAM Policy/i);
      await user.click(accordionTrigger);

      // Wait for accordion content to show
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Copy/i })).toBeInTheDocument();
      });

      // Verify the IAM policy code block is visible
      expect(screen.getByText(/"Version":/)).toBeInTheDocument();
      
      // The copy button should exist and be clickable
      const copyButton = screen.getByRole('button', { name: /Copy/i });
      expect(copyButton).toBeEnabled();
    });

    it('should update IAM policy when bucket name changes', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      // Expand the accordion
      const accordionTrigger = screen.getByText(/Recommended IAM Policy/i);
      fireEvent.click(accordionTrigger);

      // Type a bucket name
      const bucketInput = screen.getByPlaceholderText('my-documents-bucket');
      await user.type(bucketInput, 'custom-bucket');

      // The IAM policy should update
      await waitFor(() => {
        expect(screen.getByText(/custom-bucket/i)).toBeInTheDocument();
      });
    });

    it('should reset form when modal is closed', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      // Fill in some data
      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIATEST');

      // Close the modal
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      fireEvent.click(cancelButton);

      // Verify onOpenChange was called with false
      expect(defaultProps.onOpenChange).toHaveBeenCalledWith(false);
    });

    it('should convert access key ID to uppercase', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'akiatest');

      expect(accessKeyInput).toHaveValue('AKIATEST');
    });

    it('should convert bucket name to lowercase', async () => {
      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      const bucketInput = screen.getByPlaceholderText('my-documents-bucket');
      await user.type(bucketInput, 'MyBucket');

      expect(bucketInput).toHaveValue('mybucket');
    });

    it('should disable buttons while submitting', async () => {
      let resolvePromise: () => void;
      const pendingPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });
      mockPost.mockImplementationOnce(() => pendingPromise);

      const user = userEvent.setup();
      render(<S3ConnectModal {...defaultProps} />);

      // Fill form
      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EXAMPLE');

      const secretKeyInput = screen.getByLabelText(/Secret Access Key/i);
      await user.type(secretKeyInput, 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY');

      const bucketInput = screen.getByPlaceholderText('my-documents-bucket');
      await user.type(bucketInput, 'my-test-bucket');

      const prefixInput = screen.getByPlaceholderText(/documents\/knowledge-base/i);
      await user.type(prefixInput, 'documents/');

      // Submit
      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /Connecting/i })).toBeDisabled();
        expect(screen.getByRole('button', { name: /Cancel/i })).toBeDisabled();
      });

      // Cleanup
      resolvePromise!();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe('Accessibility', () => {
    it('should have proper aria attributes for form fields', () => {
      render(<S3ConnectModal {...defaultProps} />);

      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      expect(accessKeyInput).toHaveAttribute('id');
    });

    it('should mark invalid fields with aria-invalid', async () => {
      render(<S3ConnectModal {...defaultProps} />);

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
        expect(accessKeyInput).toHaveAttribute('aria-invalid', 'true');
      });
    });

    it('should have aria-describedby for error messages', async () => {
      render(<S3ConnectModal {...defaultProps} />);

      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
        expect(accessKeyInput).toHaveAttribute('aria-describedby');
      });
    });
  });

  // ===========================================================================
  // Region Selection Tests
  // ===========================================================================

  describe('Region Selection', () => {
    it('should change region when selected', async () => {
      mockPost.mockResolvedValueOnce({ data: { success: true } });
      const user = userEvent.setup();

      render(<S3ConnectModal {...defaultProps} />);

      // Fill in required fields
      const accessKeyInput = screen.getByLabelText(/Access Key ID/i);
      await user.type(accessKeyInput, 'AKIAIOSFODNN7EXAMPLE');

      const secretKeyInput = screen.getByLabelText(/Secret Access Key/i);
      await user.type(secretKeyInput, 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY');

      const bucketInput = screen.getByPlaceholderText('my-documents-bucket');
      await user.type(bucketInput, 'my-test-bucket');

      const prefixInput = screen.getByPlaceholderText(/documents\/knowledge-base/i);
      await user.type(prefixInput, 'documents/');

      // Open region dropdown and select different region
      const regionTrigger = screen.getByRole('combobox', { name: /region/i });
      await user.click(regionTrigger);

      // Wait for dropdown to open and select Europe (Ireland)
      const euWestOption = await screen.findByRole('option', { name: /Europe.*Ireland/i });
      await user.click(euWestOption);

      // Submit and verify region is sent
      const connectButton = screen.getByRole('button', { name: /Connect/i });
      fireEvent.click(connectButton);

      await waitFor(() => {
        expect(mockPost).toHaveBeenCalledWith(
          '/integrations/s3/connect',
          expect.objectContaining({
            region: 'eu-west-1',
          })
        );
      });
    });
  });
});
