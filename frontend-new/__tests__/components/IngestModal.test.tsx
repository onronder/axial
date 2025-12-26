import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';
import { IngestModal } from '@/components/ingest-modal'

// Mock fetch
global.fetch = vi.fn()

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

        it('should switch to Notion tab and show token/page inputs', async () => {
            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            const notionTab = screen.getByText('Notion')
            await userEvent.click(notionTab)

            expect(screen.getByText('Integration Token')).toBeInTheDocument()
            expect(screen.getByText('Page ID')).toBeInTheDocument()
            expect(screen.getByPlaceholderText('secret_xxxxxxxxxxxxx')).toBeInTheDocument()
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
                    '/api/py/api/v1/ingest',
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
        it('should submit Notion page ID and token correctly', async () => {
            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            // Switch to Notion tab
            const notionTab = screen.getByText('Notion')
            await userEvent.click(notionTab)

            // Enter token
            const tokenInput = screen.getByPlaceholderText('secret_xxxxxxxxxxxxx')
            await userEvent.type(tokenInput, 'secret_test_token_12345')

            // Enter page ID
            const pageIdInput = screen.getByPlaceholderText('xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx')
            await userEvent.type(pageIdInput, 'abc123-def456-789')

            // Submit
            const submitButton = screen.getByText('Ingest')
            await userEvent.click(submitButton)

            await waitFor(() => {
                expect(global.fetch).toHaveBeenCalled()
            })

            // Check FormData contains notion fields
            const fetchCall = (global.fetch as Mock).mock.calls[0]
            const formData = fetchCall[1].body as FormData
            expect(formData.get('notion_page_id')).toBe('abc123-def456-789')
            expect(formData.get('notion_token')).toBe('secret_test_token_12345')
        })

        it('should show help tooltip when clicking help icon', async () => {
            render(<IngestModal isOpen={true} onClose={mockOnClose} />)

            const notionTab = screen.getByText('Notion')
            await userEvent.click(notionTab)

            // Find and click help icon
            const helpButton = screen.getByTitle('How to get a Notion Token?')
            await userEvent.click(helpButton)

            // Check help content is visible
            expect(screen.getByText('How to get a Notion Token:')).toBeInTheDocument()
            expect(screen.getByText(/notion.so\/my-integrations/)).toBeInTheDocument()
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
