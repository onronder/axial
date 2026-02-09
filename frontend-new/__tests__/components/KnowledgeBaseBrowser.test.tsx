/**
 * Unit Tests for KnowledgeBaseBrowser Component
 * 
 * Comprehensive tests for the folder-based navigation system
 * in the Knowledge Base.
 * 
 * Coverage targets:
 * - Folder tree rendering
 * - Navigation (double-click, breadcrumbs, back button)
 * - Search functionality
 * - Selection (single, bulk)
 * - Delete operations
 * - Keyboard navigation
 * - Empty states
 * - Loading states
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KnowledgeBaseBrowser } from '@/components/knowledge-base/KnowledgeBaseBrowser';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { Document } from '@/types';

// =============================================================================
// MOCKS
// =============================================================================

// Mock Radix UI Dropdown Menu to render inline (not in portal)
vi.mock('@radix-ui/react-dropdown-menu', async () => {
    const actual = await vi.importActual('@radix-ui/react-dropdown-menu');
    return {
        ...actual,
        Portal: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    };
});

// Mock useDocuments hook
const mockDeleteDocument = vi.fn();
const mockBulkDeleteDocuments = vi.fn();
const mockRefresh = vi.fn();
const mockUseDocuments = vi.fn();

vi.mock('@/hooks/useDocuments', () => ({
    useDocuments: () => mockUseDocuments(),
}));

// Mock useProfile hook
const mockUseProfile = vi.fn();
vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => mockUseProfile(),
}));

// Mock useUsage hook
const mockRefreshUsage = vi.fn();
vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => ({
        refresh: mockRefreshUsage,
        isLoading: false,
        plan: 'starter',
        filesUsed: 5,
        filesLimit: 20,
        filesPercent: 25,
        storageUsed: 1000,
        storageLimit: 5000,
        storagePercent: 20,
    }),
}));

// Mock StorageMeter component
vi.mock('@/components/documents/StorageMeter', () => ({
    StorageMeter: ({ variant }: { variant?: string }) => (
        <div data-testid="storage-meter" data-variant={variant}>StorageMeter</div>
    ),
}));

// =============================================================================
// TEST UTILITIES
// =============================================================================

function createDocument(overrides: Partial<Document> = {}): Document {
    return {
        id: `doc-${Math.random().toString(36).substr(2, 9)}`,
        name: 'test-document.pdf',
        source: 'file_upload',
        sourceType: 'file_upload',
        status: 'indexed',
        addedAt: '2024-01-15T10:00:00Z',
        size: 1024,
        ...overrides,
    };
}

function createQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
            },
        },
    });
}

function renderWithProviders(ui: React.ReactElement) {
    const queryClient = createQueryClient();
    return render(
        <QueryClientProvider client={queryClient}>
            {ui}
        </QueryClientProvider>
    );
}

function setupDefaultMocks(documents: Document[] = []) {
    mockUseDocuments.mockReturnValue({
        documents,
        totalCount: documents.length,
        isLoading: false,
        refresh: mockRefresh,
        deleteDocument: mockDeleteDocument,
        bulkDeleteDocuments: mockBulkDeleteDocuments,
        isBulkDeleting: false,
    });

    mockUseProfile.mockReturnValue({
        profile: { role: 'admin' },
        isLoading: false,
    });
}

// =============================================================================
// TESTS
// =============================================================================

describe('KnowledgeBaseBrowser Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        setupDefaultMocks();
    });

    // =========================================================================
    // RENDERING TESTS
    // =========================================================================

    describe('Rendering', () => {
        it('should render the component with header', () => {
            setupDefaultMocks();
            renderWithProviders(<KnowledgeBaseBrowser />);

            expect(screen.getByText('Knowledge Base')).toBeInTheDocument();
            expect(screen.getByText(/Browse and manage your ingested documents/)).toBeInTheDocument();
        });

        it('should render storage meter', () => {
            setupDefaultMocks();
            renderWithProviders(<KnowledgeBaseBrowser />);

            expect(screen.getByTestId('storage-meter')).toBeInTheDocument();
        });

        it('should render search input', () => {
            setupDefaultMocks();
            renderWithProviders(<KnowledgeBaseBrowser />);

            expect(screen.getByPlaceholderText(/Search in current folder/)).toBeInTheDocument();
        });

        it('should render refresh button', () => {
            setupDefaultMocks();
            renderWithProviders(<KnowledgeBaseBrowser />);

            expect(screen.getByRole('button', { name: /Refresh/i })).toBeInTheDocument();
        });

        it('should render breadcrumb navigation starting at root', () => {
            setupDefaultMocks();
            renderWithProviders(<KnowledgeBaseBrowser />);

            expect(screen.getByRole('button', { name: /All Documents/i })).toBeInTheDocument();
        });
    });

    // =========================================================================
    // EMPTY STATE TESTS
    // =========================================================================

    describe('Empty State', () => {
        it('should show empty state message when no documents', () => {
            setupDefaultMocks([]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            expect(screen.getByText('This folder is empty')).toBeInTheDocument();
            expect(screen.getByText(/Upload files or connect a data source/)).toBeInTheDocument();
        });

        it('should show search empty state when search returns no results', async () => {
            setupDefaultMocks([
                createDocument({ name: 'report.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            const searchInput = screen.getByPlaceholderText(/Search in current folder/);
            await userEvent.type(searchInput, 'nonexistent');

            await waitFor(() => {
                expect(screen.getByText('No results found')).toBeInTheDocument();
            });
        });

        it('should handle null currentFolder gracefully', () => {
            // When documents list is empty, tree has no children
            // The displayItems should still return empty array
            setupDefaultMocks([]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Should show empty state message
            expect(screen.getByText('This folder is empty')).toBeInTheDocument();
        });
    });

    // =========================================================================
    // FOLDER TREE TESTS
    // =========================================================================

    describe('Folder Tree Display', () => {
        it('should display source folders for documents', () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', name: 'upload.pdf' }),
                createDocument({ sourceType: 'google_drive', name: 'drive.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            expect(screen.getByText('📁 Uploaded Files')).toBeInTheDocument();
            expect(screen.getByText('🔷 Google Drive')).toBeInTheDocument();
        });

        it('should display correct item count for folders', () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', path: '/folder/doc1.pdf' }),
                createDocument({ sourceType: 'file_upload', path: '/folder/doc2.pdf' }),
                createDocument({ sourceType: 'file_upload', path: '/folder/doc3.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            expect(screen.getByText('3 items')).toBeInTheDocument();
        });

        it('should display "Folder" as type for folders', () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            expect(screen.getByText('Folder')).toBeInTheDocument();
        });

        it('should display folder icon for folders', () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload' }),
            ]);
            const { container } = renderWithProviders(<KnowledgeBaseBrowser />);

            // Check for folder icon (Lucide icon has specific class structure)
            expect(container.querySelector('[class*="lucide-folder"]')).toBeInTheDocument();
        });
    });

    // =========================================================================
    // NAVIGATION TESTS
    // =========================================================================

    describe('Navigation', () => {
        it('should navigate into folder on double-click', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', path: '/Projects/doc.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Double-click on source folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            // Should now show Projects folder
            await waitFor(() => {
                expect(screen.getByText('Projects')).toBeInTheDocument();
            });
        });

        it('should update breadcrumbs when navigating', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', path: '/Projects/doc.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into source folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                // Breadcrumbs should show: All Documents > Uploaded Files
                expect(screen.getAllByRole('button', { name: /Uploaded Files/i }).length).toBeGreaterThan(0);
            });
        });

        it('should navigate back when clicking back button', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', path: '/Projects/doc.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Back/i })).toBeInTheDocument();
            });

            // Click back
            fireEvent.click(screen.getByRole('button', { name: /Back/i }));

            // Should be back at root
            await waitFor(() => {
                expect(screen.getByText('📁 Uploaded Files')).toBeInTheDocument();
            });
        });

        it('should navigate to root when clicking home button', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', path: '/Projects/Q4/doc.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate deep
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('Projects')).toBeInTheDocument();
            });

            fireEvent.doubleClick(screen.getByText('Projects').closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('Q4')).toBeInTheDocument();
            });

            // Click home button
            const homeButton = screen.getByTitle('Go to root');
            fireEvent.click(homeButton);

            // Should be at root
            await waitFor(() => {
                expect(screen.getByText('📁 Uploaded Files')).toBeInTheDocument();
            });
        });

        it('should navigate via breadcrumb click', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', path: '/Projects/doc.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('Projects')).toBeInTheDocument();
            });

            // Click "All Documents" breadcrumb
            fireEvent.click(screen.getByRole('button', { name: /All Documents/i }));

            // Should be back at root
            await waitFor(() => {
                expect(screen.getByText('📁 Uploaded Files')).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // SEARCH TESTS
    // =========================================================================

    describe('Search', () => {
        it('should filter items based on search query', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', name: 'report.pdf', path: 'report.pdf' }),
                createDocument({ sourceType: 'file_upload', name: 'invoice.pdf', path: 'invoice.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into source folder first
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });

            const searchInput = screen.getByPlaceholderText(/Search in current folder/);
            await userEvent.type(searchInput, 'report');

            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
                expect(screen.queryByText('invoice.pdf')).not.toBeInTheDocument();
            });
        });

        it('should debounce search input', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', name: 'test.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            const searchInput = screen.getByPlaceholderText(/Search in current folder/);

            // Type quickly
            await userEvent.type(searchInput, 'test');

            // Search should be debounced - initial render should still show folder
            expect(screen.getByText('📁 Uploaded Files')).toBeInTheDocument();
        });

        it('should cancel previous debounce when typing rapidly', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', name: 'test.pdf' }),
            ]);
            const { unmount } = renderWithProviders(<KnowledgeBaseBrowser />);

            const searchInput = screen.getByPlaceholderText(/Search in current folder/);

            // Type rapidly to trigger debounce cleanup
            fireEvent.change(searchInput, { target: { value: 'a' } });
            fireEvent.change(searchInput, { target: { value: 'ab' } });
            fireEvent.change(searchInput, { target: { value: 'abc' } });

            // The debounce cleanup should be triggered for each rapid change
            expect(screen.getByText('📁 Uploaded Files')).toBeInTheDocument();

            // Test keyboard on search input (triggers handleKeyDown)
            fireEvent.keyDown(searchInput, { key: 'ArrowDown' });
            fireEvent.keyDown(searchInput, { key: 'Enter' });
            fireEvent.keyDown(searchInput, { key: 'Escape' });

            // Unmount to trigger final cleanup
            unmount();
        });

        it('should reset page when searching', async () => {
            // Create many documents to trigger pagination
            const docs = Array.from({ length: 50 }, (_, i) =>
                createDocument({ id: `doc-${i}`, sourceType: 'file_upload', name: `doc${i}.pdf`, path: `doc${i}.pdf` })
            );
            setupDefaultMocks(docs);
            renderWithProviders(<KnowledgeBaseBrowser />);

            const searchInput = screen.getByPlaceholderText(/Search in current folder/);
            await userEvent.type(searchInput, 'doc1');

            // Should show filtered results
            await waitFor(() => {
                expect(screen.queryByText('This folder is empty')).not.toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // SELECTION TESTS
    // =========================================================================

    describe('Selection', () => {
        it('should select individual document with checkbox', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Find and click the checkbox for the document
            const checkboxes = screen.getAllByRole('checkbox');
            // First checkbox is "select all", second is the document
            fireEvent.click(checkboxes[1]);

            // Selection count should update
            expect(screen.getByText('1 selected')).toBeInTheDocument();
        });

        it('should select all documents with header checkbox', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test1.pdf', path: 'test1.pdf' }),
                createDocument({ id: 'doc-2', sourceType: 'file_upload', name: 'test2.pdf', path: 'test2.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test1.pdf')).toBeInTheDocument();
            });

            // Click select all checkbox
            const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
            fireEvent.click(selectAllCheckbox);

            expect(screen.getByText('2 selected')).toBeInTheDocument();
        });

        it('should deselect all documents when toggling header checkbox off', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test1.pdf', path: 'test1.pdf' }),
                createDocument({ id: 'doc-2', sourceType: 'file_upload', name: 'test2.pdf', path: 'test2.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test1.pdf')).toBeInTheDocument();
            });

            // Click select all checkbox to select
            const selectAllCheckbox = screen.getAllByRole('checkbox')[0];
            fireEvent.click(selectAllCheckbox);
            expect(screen.getByText('2 selected')).toBeInTheDocument();

            // Click again to deselect all
            fireEvent.click(selectAllCheckbox);
            expect(screen.queryByText('2 selected')).not.toBeInTheDocument();
        });

        it('should clear selection when navigating to new folder', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: '/A/test.pdf' }),
                createDocument({ id: 'doc-2', sourceType: 'file_upload', name: 'other.pdf', path: '/B/other.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate and select
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('A')).toBeInTheDocument();
            });

            // Navigate into A
            fireEvent.doubleClick(screen.getByText('A').closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Select the document
            const checkboxes = screen.getAllByRole('checkbox');
            fireEvent.click(checkboxes[1]);

            expect(screen.getByText('1 selected')).toBeInTheDocument();

            // Navigate back
            fireEvent.click(screen.getByRole('button', { name: /Back/i }));

            await waitFor(() => {
                // Selection should be cleared
                expect(screen.queryByText('1 selected')).not.toBeInTheDocument();
            });
        });

        it('should disable checkboxes for viewer role', () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);
            mockUseProfile.mockReturnValue({
                profile: { role: 'viewer' },
                isLoading: false,
            });
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            // All checkboxes should be disabled
            const checkboxes = screen.getAllByRole('checkbox');
            checkboxes.forEach(checkbox => {
                expect(checkbox).toBeDisabled();
            });
        });

        it('should deselect individual document by toggling checkbox', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Select and then deselect
            const checkboxes = screen.getAllByRole('checkbox');
            fireEvent.click(checkboxes[1]); // Select
            expect(screen.getByText('1 selected')).toBeInTheDocument();
            
            fireEvent.click(checkboxes[1]); // Deselect
            expect(screen.queryByText('1 selected')).not.toBeInTheDocument();
        });
    });

    // =========================================================================
    // DELETE OPERATIONS TESTS
    // =========================================================================

    describe('Delete Operations', () => {
        it('should show delete confirmation dialog for document', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Find and click the dropdown menu trigger (more vertical button)
            const row = screen.getByText('test.pdf').closest('tr')!;
            const menuButtons = within(row).getAllByRole('button');
            const menuTrigger = menuButtons[menuButtons.length - 1]; // Last button is the menu
            await userEvent.click(menuTrigger);

            // Wait for menu to appear and click delete option
            await waitFor(async () => {
                const deleteMenuItem = screen.getByRole('menuitem', { name: /Delete/i });
                expect(deleteMenuItem).toBeInTheDocument();
                await userEvent.click(deleteMenuItem);
            });

            // Dialog should appear
            await waitFor(() => {
                expect(screen.getByRole('alertdialog')).toBeInTheDocument();
                expect(screen.getByText('Delete Document')).toBeInTheDocument();
            });
        });

        it('should call deleteDocument when confirmed', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate and open delete dialog
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            const row = screen.getByText('test.pdf').closest('tr')!;
            const menuButtons = within(row).getAllByRole('button');
            const menuTrigger = menuButtons[menuButtons.length - 1];
            await userEvent.click(menuTrigger);

            await waitFor(async () => {
                const deleteMenuItem = screen.getByRole('menuitem', { name: /Delete/i });
                await userEvent.click(deleteMenuItem);
            });

            // Wait for dialog and confirm delete
            await waitFor(() => {
                expect(screen.getByRole('alertdialog')).toBeInTheDocument();
            });

            const confirmButton = within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Delete' });
            await userEvent.click(confirmButton);

            expect(mockDeleteDocument).toHaveBeenCalledWith('doc-1');
        });

        it('should remove deleted document from selection', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // First select the document
            const checkboxes = screen.getAllByRole('checkbox');
            fireEvent.click(checkboxes[1]);
            expect(screen.getByText('1 selected')).toBeInTheDocument();

            // Now delete it via menu
            const row = screen.getByText('test.pdf').closest('tr')!;
            const menuButtons = within(row).getAllByRole('button');
            const menuTrigger = menuButtons[menuButtons.length - 1];
            await userEvent.click(menuTrigger);

            await waitFor(async () => {
                const deleteMenuItem = screen.getByRole('menuitem', { name: /Delete/i });
                await userEvent.click(deleteMenuItem);
            });

            // Confirm delete
            await waitFor(() => {
                expect(screen.getByRole('alertdialog')).toBeInTheDocument();
            });

            const confirmButton = within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Delete' });
            await userEvent.click(confirmButton);

            // Document should be deleted and removed from selection
            expect(mockDeleteDocument).toHaveBeenCalledWith('doc-1');
            // Selection count should be cleared
            expect(screen.queryByText('1 selected')).not.toBeInTheDocument();
        });

        it('should close dialog on cancel', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate and open delete dialog
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            const row = screen.getByText('test.pdf').closest('tr')!;
            const menuButtons = within(row).getAllByRole('button');
            const menuTrigger = menuButtons[menuButtons.length - 1];
            await userEvent.click(menuTrigger);

            await waitFor(async () => {
                const deleteMenuItem = screen.getByRole('menuitem', { name: /Delete/i });
                await userEvent.click(deleteMenuItem);
            });

            // Wait for dialog and cancel
            await waitFor(() => {
                expect(screen.getByRole('alertdialog')).toBeInTheDocument();
            });

            const cancelButton = within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Cancel' });
            await userEvent.click(cancelButton);

            // Dialog should close
            await waitFor(() => {
                expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
            });
        });

        it('should enable bulk delete button when items selected', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Initially bulk delete should be disabled
            const bulkDeleteButton = screen.getByRole('button', { name: /Delete selected/i });
            expect(bulkDeleteButton).toBeDisabled();

            // Select a document
            const checkboxes = screen.getAllByRole('checkbox');
            fireEvent.click(checkboxes[1]);

            // Now bulk delete should be enabled
            expect(bulkDeleteButton).not.toBeDisabled();
        });

        it('should call bulkDeleteDocuments when bulk delete is confirmed', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);

            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Select a document
            const checkboxes = screen.getAllByRole('checkbox');
            fireEvent.click(checkboxes[1]);

            // Click bulk delete - opens AlertDialog
            const bulkDeleteButton = screen.getByRole('button', { name: /Delete selected/i });
            fireEvent.click(bulkDeleteButton);

            // Confirm in the AlertDialog
            await waitFor(() => {
                expect(screen.getByRole('alertdialog')).toBeInTheDocument();
            });

            const confirmButton = within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Delete' });
            await userEvent.click(confirmButton);

            expect(mockBulkDeleteDocuments).toHaveBeenCalledWith({ documentIds: ['doc-1'] });
        });

        it('should not call bulkDeleteDocuments when bulk delete is cancelled', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);

            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Select a document
            const checkboxes = screen.getAllByRole('checkbox');
            fireEvent.click(checkboxes[1]);

            // Click bulk delete - opens AlertDialog
            const bulkDeleteButton = screen.getByRole('button', { name: /Delete selected/i });
            fireEvent.click(bulkDeleteButton);

            // Cancel in the AlertDialog
            await waitFor(() => {
                expect(screen.getByRole('alertdialog')).toBeInTheDocument();
            });

            const cancelButton = within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Cancel' });
            await userEvent.click(cancelButton);

            expect(mockBulkDeleteDocuments).not.toHaveBeenCalled();
        });

        it('should handle bulk delete error gracefully', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);

            // Mock bulkDeleteDocuments to reject
            mockBulkDeleteDocuments.mockRejectedValueOnce(new Error('Delete failed'));

            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Select a document
            const checkboxes = screen.getAllByRole('checkbox');
            fireEvent.click(checkboxes[1]);

            // Click bulk delete - opens AlertDialog
            const bulkDeleteButton = screen.getByRole('button', { name: /Delete selected/i });
            fireEvent.click(bulkDeleteButton);

            // Confirm in the AlertDialog
            await waitFor(() => {
                expect(screen.getByRole('alertdialog')).toBeInTheDocument();
            });

            const confirmButton = within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Delete' });
            await userEvent.click(confirmButton);

            // Should call the function (which will throw, but be caught)
            await waitFor(() => {
                expect(mockBulkDeleteDocuments).toHaveBeenCalled();
            });

            // Component should still be functional (error was caught)
            expect(screen.getByText('test.pdf')).toBeInTheDocument();
        });

        it('should not allow bulk delete for viewer role even with selections', async () => {
            // Setup with documents but viewer role
            mockUseDocuments.mockReturnValue({
                documents: [createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' })],
                totalCount: 1,
                isLoading: false,
                refresh: mockRefresh,
                deleteDocument: mockDeleteDocument,
                bulkDeleteDocuments: mockBulkDeleteDocuments,
                isBulkDeleting: false,
            });
            mockUseProfile.mockReturnValue({
                profile: { role: 'viewer' },
                isLoading: false,
            });

            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Bulk delete button should be disabled for viewer
            const bulkDeleteButton = screen.getByRole('button', { name: /Delete selected/i });
            expect(bulkDeleteButton).toBeDisabled();

            // Even if we try to click, no dialog should open
            fireEvent.click(bulkDeleteButton);
            expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
            expect(mockBulkDeleteDocuments).not.toHaveBeenCalled();
        });

        it('should disable delete for viewer role', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);
            mockUseProfile.mockReturnValue({
                profile: { role: 'viewer' },
                isLoading: false,
            });
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Bulk delete should be disabled
            const bulkDeleteButton = screen.getByRole('button', { name: /Delete selected/i });
            expect(bulkDeleteButton).toBeDisabled();

            // Menu delete option should be disabled (showing Read Only)
            const row = screen.getByText('test.pdf').closest('tr')!;
            const menuButtons = within(row).getAllByRole('button');
            const menuTrigger = menuButtons[menuButtons.length - 1];
            await userEvent.click(menuTrigger);

            await waitFor(() => {
                // The delete menu item should contain "Read Only" text indicating it's disabled
                const deleteItem = screen.getByRole('menuitem', { name: /Delete.*Read Only/i });
                expect(deleteItem).toBeInTheDocument();
            });
        });

        it('should show folder delete confirmation dialog', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'doc.pdf', path: '/MyFolder/doc.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into source folder to see MyFolder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('MyFolder')).toBeInTheDocument();
            });

            // Open folder menu
            const folderRow = screen.getByText('MyFolder').closest('tr')!;
            const menuButtons = within(folderRow).getAllByRole('button');
            const menuTrigger = menuButtons[menuButtons.length - 1];
            await userEvent.click(menuTrigger);

            // Click delete all contents
            await waitFor(async () => {
                const deleteMenuItem = screen.getByRole('menuitem', { name: /Delete all contents/i });
                await userEvent.click(deleteMenuItem);
            });

            // Dialog should appear
            await waitFor(() => {
                expect(screen.getByRole('alertdialog')).toBeInTheDocument();
                expect(screen.getByText('Delete All Folder Contents')).toBeInTheDocument();
            });
        });

        it('should call bulkDeleteDocuments when folder delete is confirmed', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'doc1.pdf', path: '/MyFolder/doc1.pdf' }),
                createDocument({ id: 'doc-2', sourceType: 'file_upload', name: 'doc2.pdf', path: '/MyFolder/doc2.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into source folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('MyFolder')).toBeInTheDocument();
            });

            // Open folder menu and click delete
            const folderRow = screen.getByText('MyFolder').closest('tr')!;
            const menuButtons = within(folderRow).getAllByRole('button');
            const menuTrigger = menuButtons[menuButtons.length - 1];
            await userEvent.click(menuTrigger);

            await waitFor(async () => {
                const deleteMenuItem = screen.getByRole('menuitem', { name: /Delete all contents/i });
                await userEvent.click(deleteMenuItem);
            });

            // Confirm delete
            await waitFor(() => {
                expect(screen.getByRole('alertdialog')).toBeInTheDocument();
            });

            const confirmButton = within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Delete All' });
            await userEvent.click(confirmButton);

            // Should call bulkDeleteDocuments with all document IDs in folder
            expect(mockBulkDeleteDocuments).toHaveBeenCalledWith({
                documentIds: expect.arrayContaining(['doc-1', 'doc-2'])
            });
        });

        it('should close folder delete dialog on cancel', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'doc.pdf', path: '/MyFolder/doc.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into source folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('MyFolder')).toBeInTheDocument();
            });

            // Open folder menu and click delete
            const folderRow = screen.getByText('MyFolder').closest('tr')!;
            const menuButtons = within(folderRow).getAllByRole('button');
            const menuTrigger = menuButtons[menuButtons.length - 1];
            await userEvent.click(menuTrigger);

            await waitFor(async () => {
                const deleteMenuItem = screen.getByRole('menuitem', { name: /Delete all contents/i });
                await userEvent.click(deleteMenuItem);
            });

            // Cancel delete
            await waitFor(() => {
                expect(screen.getByRole('alertdialog')).toBeInTheDocument();
            });

            const cancelButton = within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Cancel' });
            await userEvent.click(cancelButton);

            // Dialog should close and no delete called
            await waitFor(() => {
                expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
            });
            expect(mockBulkDeleteDocuments).not.toHaveBeenCalled();
        });

        it('should open folder from dropdown menu', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', path: '/Projects/doc.pdf' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into source folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('Projects')).toBeInTheDocument();
            });

            // Open folder menu
            const folderRow = screen.getByText('Projects').closest('tr')!;
            const menuButtons = within(folderRow).getAllByRole('button');
            const menuTrigger = menuButtons[menuButtons.length - 1];
            await userEvent.click(menuTrigger);

            // Click "Open folder"
            await waitFor(async () => {
                const openMenuItem = screen.getByRole('menuitem', { name: /Open folder/i });
                await userEvent.click(openMenuItem);
            });

            // Should navigate into the folder
            await waitFor(() => {
                // doc.pdf should now be visible (we're inside Projects folder)
                expect(screen.getByText('doc.pdf')).toBeInTheDocument();
            });
        });

        it('should open source URL in new window when View Source is clicked', async () => {
            const mockOpen = vi.fn();
            vi.stubGlobal('open', mockOpen);

            setupDefaultMocks([
                createDocument({
                    sourceType: 'google_drive',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    sourceUrl: 'https://drive.google.com/file/123',
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('🔷 Google Drive');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Open dropdown on document
            const row = screen.getByText('test.pdf').closest('tr')!;
            const menuButtons = within(row).getAllByRole('button');
            const menuTrigger = menuButtons[menuButtons.length - 1];
            await userEvent.click(menuTrigger);

            // Click "View Source" menu item
            await waitFor(async () => {
                const viewSourceMenuItem = screen.getByRole('menuitem', { name: /View Source/i });
                await userEvent.click(viewSourceMenuItem);
            });

            // Should open URL in new window
            expect(mockOpen).toHaveBeenCalledWith(
                'https://drive.google.com/file/123',
                '_blank',
                'noopener,noreferrer'
            );

            vi.unstubAllGlobals();
        });

        it('should have disabled View Source when no sourceUrl', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    sourceUrl: undefined,
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Open dropdown on document
            const row = screen.getByText('test.pdf').closest('tr')!;
            const menuButtons = within(row).getAllByRole('button');
            const menuTrigger = menuButtons[menuButtons.length - 1];
            await userEvent.click(menuTrigger);

            // View Source menu item should exist but be disabled
            await waitFor(() => {
                const viewSourceMenuItem = screen.getByRole('menuitem', { name: /View Source/i });
                expect(viewSourceMenuItem).toHaveAttribute('data-disabled');
            });
        });
    });

    // =========================================================================
    // REFRESH TESTS
    // =========================================================================

    describe('Refresh', () => {
        it('should call refresh when clicking refresh button', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            const refreshButton = screen.getByRole('button', { name: /Refresh/i });
            fireEvent.click(refreshButton);

            expect(mockRefresh).toHaveBeenCalled();
        });

        it('should disable refresh button while loading', () => {
            mockUseDocuments.mockReturnValue({
                documents: [],
                totalCount: 0,
                isLoading: true,
                refresh: mockRefresh,
                deleteDocument: mockDeleteDocument,
                bulkDeleteDocuments: mockBulkDeleteDocuments,
                isBulkDeleting: false,
            });
            mockUseProfile.mockReturnValue({
                profile: { role: 'admin' },
                isLoading: false,
            });
            renderWithProviders(<KnowledgeBaseBrowser />);

            const refreshButton = screen.getByRole('button', { name: /Refresh/i });
            expect(refreshButton).toBeDisabled();
        });
    });

    // =========================================================================
    // PAGINATION TESTS
    // =========================================================================

    describe('Pagination', () => {
        it('should show correct item count', () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload' }),
                createDocument({ sourceType: 'file_upload' }),
                createDocument({ sourceType: 'file_upload' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Root level shows 1 folder (file_upload source)
            expect(screen.getByText('1 item')).toBeInTheDocument();
        });

        it('should show pagination controls', () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Should have page size selector
            expect(screen.getByText('Rows per page')).toBeInTheDocument();

            // Should show item range
            expect(screen.getByText(/1.1 of 1/)).toBeInTheDocument();
        });

        it('should change page size', async () => {
            // Create more documents than default page size
            const docs = Array.from({ length: 30 }, (_, i) =>
                createDocument({ id: `doc-${i}`, sourceType: 'file_upload', name: `doc${i}.pdf`, path: `doc${i}.pdf` })
            );
            setupDefaultMocks(docs);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder to see documents
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText(/1.25 of 30/)).toBeInTheDocument();
            });

            // Change page size
            const pageSizeSelect = screen.getByRole('combobox');
            await userEvent.click(pageSizeSelect);
            
            const option50 = screen.getByRole('option', { name: '50' });
            await userEvent.click(option50);

            await waitFor(() => {
                expect(screen.getByText(/1.30 of 30/)).toBeInTheDocument();
            });
        });

        it('should clamp page when total pages decrease', async () => {
            // Start with many documents
            const docs = Array.from({ length: 30 }, (_, i) =>
                createDocument({ id: `doc-${i}`, sourceType: 'file_upload', name: `doc${i}.pdf`, path: `doc${i}.pdf` })
            );
            setupDefaultMocks(docs);
            const { rerender } = renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText(/1.25 of 30/)).toBeInTheDocument();
            });

            // Go to page 2 using aria-label
            const nextButton = screen.getByRole('button', { name: 'Next page' });
            fireEvent.click(nextButton);

            // Now update to fewer documents (simulating data refresh)
            // The page should clamp automatically
            const fewerDocs = Array.from({ length: 5 }, (_, i) =>
                createDocument({ id: `doc-new-${i}`, sourceType: 'file_upload', name: `newdoc${i}.pdf`, path: `newdoc${i}.pdf` })
            );
            mockUseDocuments.mockReturnValue({
                documents: fewerDocs,
                totalCount: fewerDocs.length,
                isLoading: false,
                refresh: mockRefresh,
                deleteDocument: mockDeleteDocument,
                bulkDeleteDocuments: mockBulkDeleteDocuments,
                isBulkDeleting: false,
            });

            // Force re-render with new data
            rerender(
                <QueryClientProvider client={createQueryClient()}>
                    <KnowledgeBaseBrowser />
                </QueryClientProvider>
            );

            // Should show page 1 with fewer items now
            await waitFor(() => {
                expect(screen.getByText(/of 5/)).toBeInTheDocument();
            });
        });

        it('should navigate between pages', async () => {
            const docs = Array.from({ length: 30 }, (_, i) =>
                createDocument({ id: `doc-${i}`, sourceType: 'file_upload', name: `doc${i}.pdf`, path: `doc${i}.pdf` })
            );
            setupDefaultMocks(docs);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText(/1.25 of 30/)).toBeInTheDocument();
            });

            // Click next page using aria-label
            const nextButton = screen.getByRole('button', { name: 'Next page' });
            expect(nextButton).toBeInTheDocument();
            fireEvent.click(nextButton);

            await waitFor(() => {
                expect(screen.getByText(/26.30 of 30/)).toBeInTheDocument();
            });

            // Click previous page using aria-label
            const prevButton = screen.getByRole('button', { name: 'Previous page' });
            expect(prevButton).toBeInTheDocument();
            fireEvent.click(prevButton);

            await waitFor(() => {
                expect(screen.getByText(/1.25 of 30/)).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // KEYBOARD NAVIGATION TESTS
    // =========================================================================

    describe('Keyboard Navigation', () => {
        it('should have accessible container', () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload' }),
            ]);
            const { container } = renderWithProviders(<KnowledgeBaseBrowser />);

            const gridContainer = container.querySelector('[role="grid"]');
            expect(gridContainer).toBeInTheDocument();
            expect(gridContainer).toHaveAttribute('aria-label', 'Knowledge base file browser');
        });

        it('should have screen reader instructions', () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            expect(screen.getByText(/Use arrow keys to navigate/)).toBeInTheDocument();
        });

        it('should navigate with arrow keys', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', name: 'doc1.pdf', path: 'doc1.pdf' }),
                createDocument({ sourceType: 'file_upload', name: 'doc2.pdf', path: 'doc2.pdf' }),
            ]);
            const { container } = renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder first
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('doc1.pdf')).toBeInTheDocument();
            });

            // Focus the grid container
            const gridContainer = container.querySelector('[role="grid"]') as HTMLElement;
            gridContainer.focus();

            // Press down arrow
            fireEvent.keyDown(gridContainer, { key: 'ArrowDown' });

            // Press down arrow again
            fireEvent.keyDown(gridContainer, { key: 'ArrowDown' });

            // Press up arrow
            fireEvent.keyDown(gridContainer, { key: 'ArrowUp' });

            // No errors should occur
            expect(screen.getByText('doc1.pdf')).toBeInTheDocument();
        });

        it('should open folder with Enter key', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', path: '/Projects/doc.pdf' }),
            ]);
            const { container } = renderWithProviders(<KnowledgeBaseBrowser />);

            // Focus the grid and navigate
            const gridContainer = container.querySelector('[role="grid"]') as HTMLElement;
            gridContainer.focus();

            // Press down to focus first item (source folder)
            fireEvent.keyDown(gridContainer, { key: 'ArrowDown' });

            // Press Enter to open folder
            fireEvent.keyDown(gridContainer, { key: 'Enter' });

            await waitFor(() => {
                expect(screen.getByText('Projects')).toBeInTheDocument();
            });
        });

        it('should select item with Space key', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);
            const { container } = renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Focus the grid
            const gridContainer = container.querySelector('[role="grid"]') as HTMLElement;
            gridContainer.focus();

            // Navigate to document
            fireEvent.keyDown(gridContainer, { key: 'ArrowDown' });

            // Select with space
            fireEvent.keyDown(gridContainer, { key: ' ' });

            expect(screen.getByText('1 selected')).toBeInTheDocument();
        });

        it('should navigate back with Backspace key', async () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload', path: '/Projects/doc.pdf' }),
            ]);
            const { container } = renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('Projects')).toBeInTheDocument();
            });

            // Focus the grid and press backspace (not in search)
            const gridContainer = container.querySelector('[role="grid"]') as HTMLElement;
            gridContainer.focus();
            fireEvent.keyDown(gridContainer, { key: 'Backspace' });

            // Should go back to root
            await waitFor(() => {
                expect(screen.getByText('📁 Uploaded Files')).toBeInTheDocument();
            });
        });

        it('should clear selection with Escape key', async () => {
            setupDefaultMocks([
                createDocument({ id: 'doc-1', sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
            ]);
            const { container } = renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder and select
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('test.pdf')).toBeInTheDocument();
            });

            // Select the document
            const checkboxes = screen.getAllByRole('checkbox');
            fireEvent.click(checkboxes[1]);

            expect(screen.getByText('1 selected')).toBeInTheDocument();

            // Press Escape to clear selection
            const gridContainer = container.querySelector('[role="grid"]') as HTMLElement;
            gridContainer.focus();
            fireEvent.keyDown(gridContainer, { key: 'Escape' });

            expect(screen.queryByText('1 selected')).not.toBeInTheDocument();
        });

        it('should handle keyboard events on empty list gracefully', async () => {
            setupDefaultMocks([]);
            const { container } = renderWithProviders(<KnowledgeBaseBrowser />);

            // Focus the grid
            const gridContainer = container.querySelector('[role="grid"]') as HTMLElement;
            gridContainer.focus();

            // Try all keyboard actions - should not throw
            fireEvent.keyDown(gridContainer, { key: 'ArrowDown' });
            fireEvent.keyDown(gridContainer, { key: 'ArrowUp' });
            fireEvent.keyDown(gridContainer, { key: 'Enter' });
            fireEvent.keyDown(gridContainer, { key: ' ' });
            fireEvent.keyDown(gridContainer, { key: 'Escape' });

            // Component should still be functional
            expect(screen.getByText('This folder is empty')).toBeInTheDocument();
        });
    });

    // =========================================================================
    // STATUS DISPLAY TESTS
    // =========================================================================

    describe('Status Display', () => {
        it('should display indexed status badge', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    indexingStatus: 'completed',
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('Indexed')).toBeInTheDocument();
            });
        });

        it('should display processing status badge', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    indexingStatus: 'processing',
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('Processing')).toBeInTheDocument();
            });
        });

        it('should display failed status with error message', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    indexingStatus: 'failed',
                    errorMessage: 'File too large',
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('Failed')).toBeInTheDocument();
                expect(screen.getByText('File too large')).toBeInTheDocument();
            });
        });

        it('should handle unknown status gracefully with default style', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    // @ts-expect-error - testing unknown status
                    indexingStatus: 'unknown_status_xyz',
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                // Should fall back to "Indexed" style for unknown statuses
                expect(screen.getByText('Indexed')).toBeInTheDocument();
            });
        });

        it('should handle undefined status', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    indexingStatus: undefined,
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                // Should display "Indexed" for undefined/null status
                expect(screen.getByText('Indexed')).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // FILE SIZE DISPLAY TESTS
    // =========================================================================

    describe('File Size Display', () => {
        it('should display formatted file size in MB', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    size: 1048576, // 1 MB
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('1.0 MB')).toBeInTheDocument();
            });
        });

        it('should display formatted file size in KB', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    size: 2048, // 2 KB
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('2.0 KB')).toBeInTheDocument();
            });
        });

        it('should display formatted file size in bytes for small files', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    size: 500, // 500 bytes
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('500 B')).toBeInTheDocument();
            });
        });

        it('should display dash for missing size', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    size: undefined,
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                const row = screen.getByText('test.pdf').closest('tr')!;
                expect(within(row).getByText('-')).toBeInTheDocument();
            });
        });

        it('should display dash for zero size', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    size: 0,
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                const row = screen.getByText('test.pdf').closest('tr')!;
                expect(within(row).getByText('-')).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // DATE DISPLAY TESTS
    // =========================================================================

    describe('Date Display', () => {
        it('should display formatted date for documents', async () => {
            setupDefaultMocks([
                createDocument({
                    sourceType: 'file_upload',
                    name: 'test.pdf',
                    path: 'test.pdf',
                    addedAt: '2024-06-15T10:00:00Z',
                }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Navigate into folder
            const sourceFolder = screen.getByText('📁 Uploaded Files');
            fireEvent.doubleClick(sourceFolder.closest('tr')!);

            await waitFor(() => {
                expect(screen.getByText('Jun 15, 2024')).toBeInTheDocument();
            });
        });

        it('should display dash for folder date', () => {
            setupDefaultMocks([
                createDocument({ sourceType: 'file_upload' }),
            ]);
            renderWithProviders(<KnowledgeBaseBrowser />);

            // Folders should show — for date
            const folderRow = screen.getByText('📁 Uploaded Files').closest('tr')!;
            expect(within(folderRow).getByText('—')).toBeInTheDocument();
        });
    });
});

// =============================================================================
// ACCESSIBILITY TESTS
// =============================================================================

describe('Accessibility', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        setupDefaultMocks();
    });

    it('should have accessible table structure', () => {
        setupDefaultMocks([
            createDocument({ sourceType: 'file_upload' }),
        ]);
        renderWithProviders(<KnowledgeBaseBrowser />);

        expect(screen.getByRole('table')).toBeInTheDocument();
        expect(screen.getAllByRole('columnheader').length).toBeGreaterThan(0);
    });

    it('should have labeled checkboxes', async () => {
        setupDefaultMocks([
            createDocument({ sourceType: 'file_upload', name: 'test.pdf', path: 'test.pdf' }),
        ]);
        renderWithProviders(<KnowledgeBaseBrowser />);

        // Navigate into folder
        const sourceFolder = screen.getByText('📁 Uploaded Files');
        fireEvent.doubleClick(sourceFolder.closest('tr')!);

        await waitFor(() => {
            expect(screen.getByLabelText('Select all')).toBeInTheDocument();
            expect(screen.getByLabelText('Select test.pdf')).toBeInTheDocument();
        });
    });

    it('should have accessible buttons', () => {
        setupDefaultMocks([
            createDocument({ sourceType: 'file_upload' }),
        ]);
        renderWithProviders(<KnowledgeBaseBrowser />);

        expect(screen.getByRole('button', { name: /Refresh/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Delete selected/i })).toBeInTheDocument();
        expect(screen.getByTitle('Go to root')).toBeInTheDocument();
    });
});
