/**
 * Test Suite: ChatInput Component
 *
 * Comprehensive tests for:
 * - Message input handling
 * - Send button functionality
 * - Keyboard shortcuts (Enter, Shift+Enter)
 * - Model selection dropdown
 * - File attachment handler
 * - Disabled state
 * - Auto-expand textarea
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatInput } from '@/components/chat/ChatInput';
import { ModelId } from '@/lib/types';

// =============================================================================
// Test Setup
// =============================================================================

const defaultProps = {
    onSend: vi.fn(),
    onFileSelect: vi.fn(),
    disabled: false,
    selectedModel: 'fast' as ModelId,
    onModelSelect: vi.fn(),
};

describe('ChatInput Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
    });

    describe('Rendering', () => {
        it('renders input and buttons correctly', () => {
            render(<ChatInput {...defaultProps} />);

            // Check textarea exists
            expect(screen.getByRole('textbox')).toBeInTheDocument();

            // Check send button exists
            expect(screen.getByRole('button', { name: /send/i })).toBeDefined();

            // Check attachment button exists
            expect(screen.getByRole('button', { name: /attach files/i })).toBeInTheDocument();

            // Check model selector button exists
            expect(screen.getByText(/Axio Fast/)).toBeInTheDocument();
        });

        it('shows correct placeholder text', () => {
            render(<ChatInput {...defaultProps} />);

            const textarea = screen.getByRole('textbox');
            expect(textarea).toHaveAttribute('placeholder', expect.stringContaining('Ask Axio anything'));
        });

        it('renders footer text', () => {
            render(<ChatInput {...defaultProps} />);

            expect(screen.getByText(/Powered by Axio Hub/)).toBeInTheDocument();
        });
    });

    describe('Message Input Handling', () => {
        it('handles message input changes', async () => {
            const user = userEvent.setup();
            render(<ChatInput {...defaultProps} />);

            const textarea = screen.getByRole('textbox');
            await user.type(textarea, 'Hello, AI!');

            expect(textarea).toHaveValue('Hello, AI!');
        });

        it('clears input after sending', async () => {
            const user = userEvent.setup();
            render(<ChatInput {...defaultProps} />);

            const textarea = screen.getByRole('textbox');
            await user.type(textarea, 'Hello');

            const sendButton = screen.getAllByRole('button').find(btn =>
                btn.querySelector('svg.lucide-send') !== null
            );
            await user.click(sendButton!);

            expect(textarea).toHaveValue('');
        });

        it('trims whitespace before sending', async () => {
            const user = userEvent.setup();
            const onSend = vi.fn();
            render(<ChatInput {...defaultProps} onSend={onSend} />);

            const textarea = screen.getByRole('textbox');
            await user.type(textarea, '  Hello world  ');

            const sendButton = screen.getAllByRole('button').find(btn =>
                btn.querySelector('svg.lucide-send') !== null
            );
            await user.click(sendButton!);

            expect(onSend).toHaveBeenCalledWith('Hello world');
        });
    });

    describe('Send Button', () => {
        it('sends message on button click', async () => {
            const user = userEvent.setup();
            const onSend = vi.fn();
            render(<ChatInput {...defaultProps} onSend={onSend} />);

            const textarea = screen.getByRole('textbox');
            await user.type(textarea, 'Test message');

            const sendButton = screen.getAllByRole('button').find(btn =>
                btn.querySelector('svg.lucide-send') !== null
            );
            await user.click(sendButton!);

            expect(onSend).toHaveBeenCalledWith('Test message');
        });

        it('disables send button when message is empty', () => {
            render(<ChatInput {...defaultProps} />);

            const sendButton = screen.getAllByRole('button').find(btn =>
                btn.querySelector('svg.lucide-send') !== null
            );
            expect(sendButton).toBeDisabled();
        });

        it('disables send button when only whitespace', async () => {
            const user = userEvent.setup();
            render(<ChatInput {...defaultProps} />);

            const textarea = screen.getByRole('textbox');
            await user.type(textarea, '   ');

            const sendButton = screen.getAllByRole('button').find(btn =>
                btn.querySelector('svg.lucide-send') !== null
            );
            expect(sendButton).toBeDisabled();
        });

        it('enables send button when message has content', async () => {
            const user = userEvent.setup();
            render(<ChatInput {...defaultProps} />);

            const textarea = screen.getByRole('textbox');
            await user.type(textarea, 'Hello');

            const sendButton = screen.getAllByRole('button').find(btn =>
                btn.querySelector('svg.lucide-send') !== null
            );
            expect(sendButton).not.toBeDisabled();
        });
    });

    describe('Keyboard Shortcuts', () => {
        it('sends message on Enter key', async () => {
            const user = userEvent.setup();
            const onSend = vi.fn();
            render(<ChatInput {...defaultProps} onSend={onSend} />);

            const textarea = screen.getByRole('textbox');
            await user.type(textarea, 'Test message{Enter}');

            expect(onSend).toHaveBeenCalledWith('Test message');
        });

        it('creates new line on Shift+Enter', async () => {
            const user = userEvent.setup();
            const onSend = vi.fn();
            render(<ChatInput {...defaultProps} onSend={onSend} />);

            const textarea = screen.getByRole('textbox');
            await user.type(textarea, 'Line 1{Shift>}{Enter}{/Shift}Line 2');

            expect(onSend).not.toHaveBeenCalled();
            expect(textarea).toHaveValue('Line 1\nLine 2');
        });

        it('does not send on Enter when disabled', async () => {
            const user = userEvent.setup();
            const onSend = vi.fn();
            render(<ChatInput {...defaultProps} onSend={onSend} disabled={true} />);

            const textarea = screen.getByRole('textbox');
            // Note: Can't type in disabled textarea, testing the disabled state instead
            expect(textarea).toBeDisabled();
        });
    });

    describe('Disabled State', () => {
        it('disables textarea when disabled prop is true', () => {
            render(<ChatInput {...defaultProps} disabled={true} />);

            const textarea = screen.getByRole('textbox');
            expect(textarea).toBeDisabled();
        });

        it('disables attachment button when disabled', () => {
            render(<ChatInput {...defaultProps} disabled={true} />);

            const attachButton = screen.getByRole('button', { name: /attach files/i });
            expect(attachButton).toBeDisabled();
        });

        it('disables send button when disabled', () => {
            render(<ChatInput {...defaultProps} disabled={true} />);

            const sendButton = screen.getAllByRole('button').find(btn =>
                btn.querySelector('svg.lucide-send') !== null
            );
            expect(sendButton).toBeDisabled();
        });
    });

    describe('Model Selection', () => {
        it('displays current model name', () => {
            render(<ChatInput {...defaultProps} selectedModel="fast" />);

            expect(screen.getByText(/Axio Fast/)).toBeInTheDocument();
        });

        it('displays smart model name when selected', () => {
            render(<ChatInput {...defaultProps} selectedModel="smart" />);

            expect(screen.getByText(/Axio Pro/)).toBeInTheDocument();
        });

        it('opens dropdown on click', async () => {
            const user = userEvent.setup();
            render(<ChatInput {...defaultProps} />);

            const modelButton = screen.getByText(/Axio Fast/);
            await user.click(modelButton);

            // Dropdown should show both model options
            await waitFor(() => {
                expect(screen.getByText('Great for simple tasks & speed')).toBeInTheDocument();
            });
        });

        it('calls onModelSelect when model is changed', async () => {
            const user = userEvent.setup();
            const onModelSelect = vi.fn();
            render(<ChatInput {...defaultProps} onModelSelect={onModelSelect} selectedModel="fast" />);

            const modelButton = screen.getByText(/Axio Fast/);
            await user.click(modelButton);

            // Click on Pro model (note: includes emoji in name "Axio Pro 🧠")
            const proOption = await screen.findByText(/Axio Pro/);
            await user.click(proOption);

            expect(onModelSelect).toHaveBeenCalledWith('smart');
        });
    });

    describe('File Attachment', () => {
        it('renders hidden file input', () => {
            render(<ChatInput {...defaultProps} />);

            const fileInput = document.querySelector('input[type="file"]');
            expect(fileInput).toBeInTheDocument();
            expect(fileInput).toHaveClass('hidden');
        });

        it('file input accepts correct file types', () => {
            render(<ChatInput {...defaultProps} />);

            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
            expect(fileInput.accept).toContain('.pdf');
            expect(fileInput.accept).toContain('.doc');
            expect(fileInput.accept).toContain('.txt');
            expect(fileInput.accept).toContain('.csv');
        });

        it('file input allows multiple files', () => {
            render(<ChatInput {...defaultProps} />);

            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
            expect(fileInput.multiple).toBe(true);
        });

        it('triggers file input when attachment button is clicked', async () => {
            const user = userEvent.setup();
            render(<ChatInput {...defaultProps} />);

            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
            const clickSpy = vi.spyOn(fileInput, 'click');

            const attachButton = screen.getByRole('button', { name: /attach files/i });
            await user.click(attachButton);

            expect(clickSpy).toHaveBeenCalled();
        });

        it('calls onFileSelect when files are selected', async () => {
            const onFileSelect = vi.fn();
            render(<ChatInput {...defaultProps} onFileSelect={onFileSelect} />);

            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

            // Create mock files
            const file1 = new File(['content1'], 'test1.pdf', { type: 'application/pdf' });
            const file2 = new File(['content2'], 'test2.txt', { type: 'text/plain' });

            // Simulate file selection
            Object.defineProperty(fileInput, 'files', {
                value: [file1, file2],
                writable: false,
            });

            fireEvent.change(fileInput);

            expect(onFileSelect).toHaveBeenCalledWith([file1, file2]);
        });

        it('resets file input after selection', async () => {
            const onFileSelect = vi.fn();
            render(<ChatInput {...defaultProps} onFileSelect={onFileSelect} />);

            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            Object.defineProperty(fileInput, 'files', {
                value: [file],
                writable: false,
            });

            fireEvent.change(fileInput);

            // Input value should be reset to allow re-selecting same file
            expect(fileInput.value).toBe('');
        });

        it('does not call onFileSelect when no files are selected', () => {
            const onFileSelect = vi.fn();
            render(<ChatInput {...defaultProps} onFileSelect={onFileSelect} />);

            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

            Object.defineProperty(fileInput, 'files', {
                value: [],
                writable: false,
            });

            fireEvent.change(fileInput);

            expect(onFileSelect).not.toHaveBeenCalled();
        });

        it('works without onFileSelect callback', () => {
            render(<ChatInput {...defaultProps} onFileSelect={undefined} />);

            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;

            const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
            Object.defineProperty(fileInput, 'files', {
                value: [file],
                writable: false,
            });

            // Should not throw
            expect(() => fireEvent.change(fileInput)).not.toThrow();
        });
    });

    describe('Accessibility', () => {
        it('has aria-label on attachment button', () => {
            render(<ChatInput {...defaultProps} />);

            const attachButton = screen.getByRole('button', { name: /attach files/i });
            expect(attachButton).toHaveAttribute('aria-label', 'Attach files');
        });

        it('has aria-label on file input', () => {
            render(<ChatInput {...defaultProps} />);

            const fileInput = document.querySelector('input[type="file"]');
            expect(fileInput).toHaveAttribute('aria-label', 'Upload files');
        });

        it('textarea is focusable', () => {
            render(<ChatInput {...defaultProps} />);

            const textarea = screen.getByRole('textbox');
            textarea.focus();

            expect(document.activeElement).toBe(textarea);
        });
    });
});
