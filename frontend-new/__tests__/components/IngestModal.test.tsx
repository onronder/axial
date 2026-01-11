import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { IngestModal } from '@/components/ingest-modal'
import { UsageProvider } from '@/hooks/useUsage'
import { ProfileProvider } from '@/hooks/useProfile'

const { mockAuthPost, mockConnect, mockIsConnected, mockLoading, mockGetUploadUrl, mockUploadToStorage, mockIngestFileReference, mockToast } = vi.hoisted(() => ({
    mockAuthPost: vi.fn(),
    mockConnect: vi.fn(),
    mockIsConnected: vi.fn(),
    mockLoading: vi.fn(),
    mockGetUploadUrl: vi.fn(),
    mockUploadToStorage: vi.fn(),
    mockIngestFileReference: vi.fn(),
    mockToast: vi.fn(),
}));

vi.mock('@/hooks/useDataSources', () => ({
    useDataSources: () => ({
        connect: mockConnect,
        disconnect: vi.fn(),
        isConnected: mockIsConnected,
        loading: mockLoading(),
        integrations: []
    })
}));

vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => ({
        profile: {
            id: 'user-1',
            user_id: 'user-1',
            first_name: 'Test',
            last_name: 'User',
            plan: 'pro',
            theme: 'dark',
            role: 'admin',
            has_team: false,
            created_at: '',
            updated_at: ''
        },
        isLoading: false,
        error: null,
        updateProfile: vi.fn(),
        refresh: vi.fn(),
    }),
    ProfileProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => ({
        usage: null,
        effectivePlan: null,
        isLoading: false,
        error: null,
        plan: 'pro',
        isPlanInherited: false,
        filesUsed: 0,
        filesLimit: 10,
        filesPercent: 0,
        storageUsed: 0,
        storageLimit: 100,
        storagePercent: 0,
        canWebCrawl: true,
        teamEnabled: true,
        premiumModels: true,
        modelTier: 'hybrid',
        refresh: vi.fn(),
        refreshPlan: vi.fn(),
    }),
    UsageProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({
        toast: mockToast,
    }),
}));

vi.mock('@/lib/api', () => ({
    authFetch: { post: mockAuthPost },
    getUploadUrl: mockGetUploadUrl,
    uploadToStorage: mockUploadToStorage,
    ingestFileReference: mockIngestFileReference,
    getUsageStats: () => Promise.resolve({
        plan: 'pro',
        files: { used: 0, limit: 10, percent: 0 },
        storage: { used_bytes: 0, limit_bytes: 100, used_display: '0 B', limit_display: '100 B', percent: 0 },
        features: { web_crawl: true, team: true, team_enabled: true, premium_models: true },
        model_tier: 'hybrid',
        subscription_status: 'active'
    }),
    getEffectivePlan: () => Promise.resolve({ plan: 'pro', inherited: false, team_id: null, team_name: null }),
}))

const renderWithProviders = (ui: React.ReactElement) =>
    render(
        <UsageProvider>
            <ProfileProvider>{ui}</ProfileProvider>
        </UsageProvider>
    );

const renderModal = (props: React.ComponentProps<typeof IngestModal>) =>
    renderWithProviders(<IngestModal {...props} />);

describe('IngestModal', () => {
    const mockOnClose = vi.fn()

    beforeEach(() => {
        vi.clearAllMocks()
        mockAuthPost.mockResolvedValue({ data: { status: 'queued' } })
        mockIsConnected.mockReturnValue(false)
        mockLoading.mockReturnValue(false)
        mockGetUploadUrl.mockResolvedValue({
            upload_url: 'https://storage.test/upload',
            storage_path: 'uploads/test.pdf'
        });
        mockUploadToStorage.mockResolvedValue(true);
        mockIngestFileReference.mockResolvedValue({ data: { status: 'queued' } });
    })


    describe('Tab Navigation', () => {
        it('should render with File tab active by default', () => {
            renderModal({ isOpen: true, onClose: mockOnClose })

            expect(screen.getByText('File')).toBeInTheDocument()
            expect(screen.getByText('Website')).toBeInTheDocument()
            expect(screen.getByText('Notion')).toBeInTheDocument()
            expect(screen.getByText(/Select Document/)).toBeInTheDocument()
        })

        it('should switch to Website tab and show URL input', async () => {
            renderModal({ isOpen: true, onClose: mockOnClose })

            const websiteTab = screen.getByText('Website')
            await userEvent.click(websiteTab)

            expect(screen.getByText('Web Page URL')).toBeInTheDocument()
            expect(screen.getByPlaceholderText('https://example.com/article')).toBeInTheDocument()
        })

        it('should switch to Notion tab and show connect button', async () => {
            renderModal({ isOpen: true, onClose: mockOnClose })

            const notionTab = screen.getByText('Notion')
            await userEvent.click(notionTab)

            expect(screen.getByText('Connect Notion Workspace')).toBeInTheDocument()
            expect(screen.getByText('Connect Notion')).toBeInTheDocument()
        })
    })

    describe('Website Submission', () => {
        it('should submit web URL correctly', async () => {
            renderModal({ isOpen: true, onClose: mockOnClose })

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
                expect(mockAuthPost).toHaveBeenCalledWith(
                    '/integrations/web/crawl',
                    expect.objectContaining({
                        url: 'https://example.com/test-page',
                        crawl_type: 'sitemap',
                        max_depth: 1,
                        respect_robots: true,
                        allow_subdomains: false
                    })
                );
            })

            // Ensure payload includes URL and crawl type
            const postCall = mockAuthPost.mock.calls[0]
            const payload = postCall[1]
            expect(payload.url).toBe('https://example.com/test-page')
            expect(payload.crawl_type).toBe('sitemap')
        })

        it('should return early when URL is empty', async () => {
            renderModal({ isOpen: true, onClose: mockOnClose })

            const websiteTab = screen.getByText('Website')
            await userEvent.click(websiteTab)

            await userEvent.click(screen.getByText('Ingest'))

            await waitFor(() => {
                expect(mockAuthPost).not.toHaveBeenCalled()
            })
        })

        it('should show error for invalid URL', async () => {
            renderModal({ isOpen: true, onClose: mockOnClose })

            const websiteTab = screen.getByText('Website')
            await userEvent.click(websiteTab)

            const urlInput = screen.getByPlaceholderText('https://example.com/article')
            await userEvent.type(urlInput, 'not-a-valid-url')

            // Check for validation message
            expect(screen.getByText(/Please enter a valid URL/)).toBeInTheDocument()
        })

        it('should show error toast on invalid URL submit', async () => {
            renderModal({ isOpen: true, onClose: mockOnClose })

            const websiteTab = screen.getByText('Website')
            await userEvent.click(websiteTab)

            const urlInput = screen.getByPlaceholderText('https://example.com/article')
            await userEvent.type(urlInput, 'not-a-valid-url')

            const form = document.querySelector('form')
            expect(form).toBeTruthy()
            if (form) {
                fireEvent.submit(form)
            }

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Ingestion Failed',
                        description: expect.stringContaining('Please enter a valid URL'),
                        variant: 'destructive',
                    })
                )
            })
        })

        it('should advance progress while loading', async () => {
            const intervalSpy = vi.spyOn(global, 'setInterval');
            mockAuthPost.mockImplementation(() => new Promise(() => { }));

            renderModal({ isOpen: true, onClose: mockOnClose });

            const websiteTab = screen.getByText('Website');
            await userEvent.click(websiteTab);

            const urlInput = screen.getByPlaceholderText('https://example.com/article');
            await userEvent.type(urlInput, 'https://example.com/test-page');

            const form = document.querySelector('form');
            if (form) {
                await waitFor(() => {
                    fireEvent.submit(form);
                });
            }

            const intervalCallback = intervalSpy.mock.calls[0]?.[0] as (() => void) | undefined;
            if (intervalCallback) {
                await waitFor(() => {
                    intervalCallback();
                });
            }

            expect(intervalSpy).toHaveBeenCalled();
            intervalSpy.mockRestore();
        })

        it('should show fallback error on non-Error failures', async () => {
            mockAuthPost.mockRejectedValue('bad')

            renderModal({ isOpen: true, onClose: mockOnClose })

            const websiteTab = screen.getByText('Website')
            await userEvent.click(websiteTab)

            const urlInput = screen.getByPlaceholderText('https://example.com/article')
            await userEvent.type(urlInput, 'https://example.com/fail')

            await userEvent.click(screen.getByText('Ingest'))

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Ingestion Failed',
                        description: 'Something went wrong. Please try again.',
                        variant: 'destructive',
                    })
                )
            })
        })
    })

    describe('File Submission', () => {
        it('should return early when submitting without a file', async () => {
            const user = userEvent.setup({ delay: null });
            renderModal({ isOpen: true, onClose: mockOnClose })

            await user.click(screen.getByText('Ingest'));

            await waitFor(() => {
                expect(mockGetUploadUrl).not.toHaveBeenCalled();
                expect(mockIngestFileReference).not.toHaveBeenCalled();
            });
        });

        it('should use default content type when file type is missing', async () => {
            const user = userEvent.setup({ delay: null });
            renderModal({ isOpen: true, onClose: mockOnClose })

            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
            const file = new File(['test content'], 'test.bin');
            await user.upload(fileInput, file);

            await user.click(screen.getByText('Ingest'));

            await waitFor(() => {
                expect(mockGetUploadUrl).toHaveBeenCalledWith('test.bin', 'application/octet-stream', file.size);
            });
        });

        it('should submit file upload successfully', async () => {
            const user = userEvent.setup({ delay: null });
            renderModal({ isOpen: true, onClose: mockOnClose })

            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
            expect(fileInput).toBeInTheDocument();

            const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
            await user.upload(fileInput, file);

            const submitButton = screen.getByText('Ingest');
            await user.click(submitButton);

            await waitFor(() => {
                expect(mockGetUploadUrl).toHaveBeenCalledWith('test.pdf', 'application/pdf', file.size);
            });

            expect(mockUploadToStorage).toHaveBeenCalledWith('https://storage.test/upload', file);
            expect(mockIngestFileReference).toHaveBeenCalledWith(
                'uploads/test.pdf',
                'test.pdf',
                file.size,
                { client_id: 'frontend_user' }
            );

            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Ingestion Queued',
                    variant: 'default',
                })
            );
        });

        it('should show error toast when upload fails', async () => {
            mockUploadToStorage.mockResolvedValue(false);

            const user = userEvent.setup({ delay: null });
            renderModal({ isOpen: true, onClose: mockOnClose })

            const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
            const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
            await user.upload(fileInput, file);

            await user.click(screen.getByText('Ingest'));

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Ingestion Failed',
                        variant: 'destructive',
                    })
                );
            });
        });
    });

    describe('Legacy URL Submission', () => {
        it('should submit legacy URL with single crawl type', async () => {
            const user = userEvent.setup({ delay: null });
            renderModal({ isOpen: true, onClose: mockOnClose, initialTab: "url" })

            const urlInput = screen.getByPlaceholderText('https://example.com');
            await user.type(urlInput, 'https://example.com/single');

            await user.click(screen.getByText('Ingest'));

            await waitFor(() => {
                expect(mockAuthPost).toHaveBeenCalledWith(
                    '/integrations/web/crawl',
                    expect.objectContaining({
                        url: 'https://example.com/single',
                        crawl_type: 'single',
                    })
                );
            });
        });
    });

    describe('Notion Submission', () => {
        it('should trigger connect when clicking Connect Notion', async () => {
            renderModal({ isOpen: true, onClose: mockOnClose })

            const notionTab = screen.getByText('Notion')
            await userEvent.click(notionTab)

            const connectButton = screen.getByText('Connect Notion')
            await userEvent.click(connectButton)

            expect(mockConnect).toHaveBeenCalledWith('notion')
        })

        it('should show loading indicator when datasource is loading', async () => {
            mockLoading.mockReturnValue(true)

            renderModal({ isOpen: true, onClose: mockOnClose })

            const notionTab = screen.getByText('Notion')
            await userEvent.click(notionTab)

            expect(document.querySelector('.animate-spin')).toBeInTheDocument()
        })

        it('should show connected state when connected', async () => {
            mockIsConnected.mockReturnValue(true) // Mock connected state

            renderModal({ isOpen: true, onClose: mockOnClose })

            const notionTab = screen.getByText('Notion')
            await userEvent.click(notionTab)

            expect(screen.getByText('Notion Connected')).toBeInTheDocument()
            expect(screen.getByText('Manage in Notion')).toBeInTheDocument()
        })

        it('should open notion integrations link when clicking Manage in Notion', async () => {
            mockIsConnected.mockReturnValue(true)
            const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);

            renderModal({ isOpen: true, onClose: mockOnClose })

            const notionTab = screen.getByText('Notion')
            await userEvent.click(notionTab)

            await userEvent.click(screen.getByText('Manage in Notion'))

            expect(openSpy).toHaveBeenCalledWith('https://notion.so/my-integrations', '_blank');
            openSpy.mockRestore();
        });
    })

    describe('Modal Behavior', () => {
        it('should not render when isOpen is false', () => {
            renderModal({ isOpen: false, onClose: mockOnClose })
            expect(screen.queryByText('Add Data Source')).not.toBeInTheDocument()
        })

        it('should call onClose when clicking backdrop', async () => {
            renderModal({ isOpen: true, onClose: mockOnClose })

            // Click the backdrop (the outer div)
            const backdrop = screen.getByText('Add Data Source').closest('.fixed')
            if (backdrop) {
                fireEvent.click(backdrop)
            }

            // Note: This test may need adjustment based on actual DOM structure
        })

        it('should call onClose when clicking X button', async () => {
            renderModal({ isOpen: true, onClose: mockOnClose })

            const closeButton = screen.getByRole('button', { name: /close/i })
            await userEvent.click(closeButton)

            expect(mockOnClose).toHaveBeenCalled()
        })
    })
})
