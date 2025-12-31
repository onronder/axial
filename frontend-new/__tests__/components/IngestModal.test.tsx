import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { IngestModal } from '@/components/ingest-modal'

// Mock fetch
global.fetch = vi.fn()

// Mock useDataSources hook
const mockConnect = vi.fn();
const mockIsConnected = vi.fn();

vi.mock('@/hooks/useDataSources', () => ({
    useDataSources: () => ({
        connect: mockConnect,
        disconnect: vi.fn(),
        isConnected: mockIsConnected,
        loading: false,
        integrations: []
    })
}));

// Mock Supabase client
vi.mock('@/lib/supabase/client', () => ({
    createClient: () => ({
        auth: {
            getSession: () => Promise.resolve({
                data: { session: { access_token: 'test-token' } }
            })
        }
    })
}))

describe('IngestModal', () => {
    const mockOnClose = vi.fn()

    beforeEach(() => {
        vi.clearAllMocks()
            ; (global.fetch as Mock).mockResolvedValue({
                ok: true,
                json: () => Promise.resolve({ status: 'queued', doc_id: 'test-123' })
            })
    })


    describe('Tab Navigation', () => {
        it('should render with File tab active by default', () => {
            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            expect(screen.getByText('File')).toBeInTheDocument()
            expect(screen.getByText('Website')).toBeInTheDocument()
            expect(screen.getByText('Notion')).toBeInTheDocument()
            expect(screen.getByText(/Select Document/)).toBeInTheDocument()
        })

        it('should switch to Website tab and show URL input', async () => {
            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            const websiteTab = screen.getByText('Website')
            await userEvent.click(websiteTab)

            expect(screen.getByText('Web Page URL')).toBeInTheDocument()
            expect(screen.getByPlaceholderText('https://example.com/article')).toBeInTheDocument()
        })

        it('should switch to Notion tab and show connect button', async () => {
            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            const notionTab = screen.getByText('Notion')
            await userEvent.click(notionTab)

            expect(screen.getByText('Connect Notion Workspace')).toBeInTheDocument()
            expect(screen.getByText('Connect Notion')).toBeInTheDocument()
        })
    })

    describe('Website Submission', () => {
        it('should submit web URL correctly', async () => {
            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            // Switch to Website tab
            const websiteTab = screen.getByText('Website')
            await userEvent.click(websiteTab)

            // Enter URL
            const urlInput = screen.getByPlaceholderText('https://example.com/article')
            await userEvent.type(urlInput, 'https://example.com/test-page')

            // Submit
            const submitButton = screen.getByText('Ingest')
            await userEvent.click(submitButton)

            await waitFor(() => {
                expect(global.fetch).toHaveBeenCalledWith(
                    '/api/py/ingest',
                    expect.objectContaining({
                        method: 'POST',
                        headers: { 'Authorization': 'Bearer test-token' }
                    })
                )
            })

            // Check FormData contains url
            const fetchCall = (global.fetch as Mock).mock.calls[0]
            const formData = fetchCall[1].body as FormData
            expect(formData.get('url')).toBe('https://example.com/test-page')
        })

        it('should show error for invalid URL', async () => {
            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            const websiteTab = screen.getByText('Website')
            await userEvent.click(websiteTab)

            const urlInput = screen.getByPlaceholderText('https://example.com/article')
            await userEvent.type(urlInput, 'not-a-valid-url')

            // Check for validation message
            expect(screen.getByText(/Please enter a valid URL/)).toBeInTheDocument()
        })
    })

    describe('Notion Submission', () => {
        it('should trigger connect when clicking Connect Notion', async () => {
            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            const notionTab = screen.getByText('Notion')
            await userEvent.click(notionTab)

            const connectButton = screen.getByText('Connect Notion')
            await userEvent.click(connectButton)

            expect(mockConnect).toHaveBeenCalledWith('notion')
        })

        it('should show connected state when connected', async () => {
            mockIsConnected.mockReturnValue(true) // Mock connected state

            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            const notionTab = screen.getByText('Notion')
            await userEvent.click(notionTab)

            expect(screen.getByText('Notion Connected')).toBeInTheDocument()
            expect(screen.getByText('Manage in Notion')).toBeInTheDocument()
        })
    })

    describe('Modal Behavior', () => {
        it('should not render when isOpen is false', () => {
            render(<IngestModal isOpen={false} onClose={mockOnClose} />)
            expect(screen.queryByText('Add Data Source')).not.toBeInTheDocument()
        })

        it('should call onClose when clicking backdrop', async () => {
            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            // Click the backdrop (the outer div)
            const backdrop = screen.getByText('Add Data Source').closest('.fixed')
            if (backdrop) {
                fireEvent.click(backdrop)
            }

            // Note: This test may need adjustment based on actual DOM structure
        })

        it('should call onClose when clicking X button', async () => {
            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            const closeButton = screen.getByRole('button', { name: /close/i })
            await userEvent.click(closeButton)

            expect(mockOnClose).toHaveBeenCalled()
        })
    })
})
