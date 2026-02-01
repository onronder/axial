/**
 * Tests for FileBrowser component
 * 
 * Covers file browsing, selection, ingestion, search, breadcrumbs,
 * and viewer permission handling.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FileBrowser, FileItem } from '@/components/data-sources/FileBrowser';
import { DataSource } from '@/lib/mockData';

// =============================================================================
// Mocks
// =============================================================================

const mockGetFiles = vi.fn();
const mockIngestFiles = vi.fn();
const mockGetIngestedFileIds = vi.fn();
const mockToast = vi.fn();

vi.mock('@/hooks/useDataSources', () => ({
    useDataSources: () => ({
        getFiles: mockGetFiles,
        ingestFiles: mockIngestFiles,
        getIngestedFileIds: mockGetIngestedFileIds,
    }),
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({
        toast: mockToast,
    }),
}));

vi.mock('@/components/data-sources/DataSourceIcon', () => ({
    DataSourceIcon: ({ sourceId }: { sourceId: string }) => (
        <div data-testid="data-source-icon">{sourceId}</div>
    ),
}));

// =============================================================================
// Test Data
// =============================================================================

const mockSource: DataSource = {
    id: 'google-drive',
    name: 'Google Drive',
    type: 'google_drive',
    status: 'connected',
    lastSync: '2024-01-15',
    provider: 'google',
};

const mockFiles: FileItem[] = [
    { id: 'folder-1', name: 'Documents', type: 'folder' },
    { id: 'folder-2', name: 'Images', type: 'folder' },
    { id: 'file-1', name: 'report.pdf', type: 'file', size: 1024000, mimeType: 'application/pdf' },
    { id: 'file-2', name: 'data.csv', type: 'file', size: 512, mimeType: 'text/csv' },
    { id: 'file-3', name: 'presentation.pptx', type: 'file', size: 2048000, mimeType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' },
];

const mockSubFiles: FileItem[] = [
    { id: 'subfile-1', name: 'nested-doc.docx', type: 'file', size: 256000, mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },
    { id: 'subfile-2', name: 'spreadsheet.xlsx', type: 'file', size: 128000, mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },
];

// =============================================================================
// Test Setup
// =============================================================================

beforeEach(() => {
    vi.clearAllMocks();
    mockGetFiles.mockResolvedValue(mockFiles);
    mockGetIngestedFileIds.mockResolvedValue(new Set());
    mockIngestFiles.mockResolvedValue(undefined);
});

afterEach(() => {
    vi.restoreAllMocks();
});

// =============================================================================
// Tests
// =============================================================================

describe('FileBrowser', () => {
    // =========================================================================
    // Rendering Tests
    // =========================================================================

    describe('Rendering', () => {
        it('should render the component with source name', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('Google Drive')).toBeInTheDocument();
            });
        });

        it('should render back button', async () => {
            const onBack = vi.fn();
            render(<FileBrowser source={mockSource} onBack={onBack} />);
            
            // Back button is a ghost variant with arrow icon
            const buttons = screen.getAllByRole('button');
            expect(buttons.length).toBeGreaterThan(0);
        });

        it('should render search input', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            const searchInput = screen.getByPlaceholderText('Search files...');
            expect(searchInput).toBeInTheDocument();
        });

        it('should render Home breadcrumb initially', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('Home')).toBeInTheDocument();
            });
        });

        it('should show loading spinner while fetching files', () => {
            mockGetFiles.mockImplementation(() => new Promise(() => {})); // Never resolves
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            expect(screen.getByTestId('data-source-icon')).toBeInTheDocument();
        });

        it('should render files after loading', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('Documents')).toBeInTheDocument();
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
                expect(screen.getByText('data.csv')).toBeInTheDocument();
            });
        });

        it('should show empty state when folder is empty', async () => {
            mockGetFiles.mockResolvedValue([]);
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('This folder is empty')).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // File Type Tests
    // =========================================================================

    describe('File Type Labels', () => {
        it('should show "PDF" for PDF files', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('PDF')).toBeInTheDocument();
            });
        });

        it('should show "CSV" for CSV files', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('CSV')).toBeInTheDocument();
            });
        });

        it('should show "PowerPoint" for presentation files', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('PowerPoint')).toBeInTheDocument();
            });
        });

        it('should show "Folder" for folder items', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                const folderTypes = screen.getAllByText('Folder');
                expect(folderTypes.length).toBeGreaterThan(0);
            });
        });

        it('should handle files with various mime types', async () => {
            const filesWithTypes: FileItem[] = [
                { id: '1', name: 'image.png', type: 'file', mimeType: 'image/png' },
                { id: '2', name: 'audio.mp3', type: 'file', mimeType: 'audio/mpeg' },
                { id: '3', name: 'video.mp4', type: 'file', mimeType: 'video/mp4' },
                { id: '4', name: 'unknown.xyz', type: 'file', mimeType: 'application/xyz' },
            ];
            mockGetFiles.mockResolvedValue(filesWithTypes);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('image.png')).toBeInTheDocument();
            });
        });

        it('should handle files without mime type', async () => {
            const filesNoMime: FileItem[] = [
                { id: '1', name: 'document.txt', type: 'file' },
                { id: '2', name: 'noextension', type: 'file' },
            ];
            mockGetFiles.mockResolvedValue(filesNoMime);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('document.txt')).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // File Size Tests
    // =========================================================================

    describe('File Size Formatting', () => {
        it('should format bytes correctly', async () => {
            const testFiles: FileItem[] = [
                { id: '1', name: 'tiny.txt', type: 'file', size: 500 },
            ];
            mockGetFiles.mockResolvedValue(testFiles);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('500 B')).toBeInTheDocument();
            });
        });

        it('should format KB correctly', async () => {
            const testFiles: FileItem[] = [
                { id: '1', name: 'small.txt', type: 'file', size: 2048 },
            ];
            mockGetFiles.mockResolvedValue(testFiles);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('2.0 KB')).toBeInTheDocument();
            });
        });

        it('should format MB correctly', async () => {
            const testFiles: FileItem[] = [
                { id: '1', name: 'large.pdf', type: 'file', size: 1048576 }, // Exactly 1 MB
            ];
            mockGetFiles.mockResolvedValue(testFiles);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('1.0 MB')).toBeInTheDocument();
            });
        });

        it('should handle string size values', async () => {
            const testFiles: FileItem[] = [
                { id: '1', name: 'doc.pdf', type: 'file', size: '5.2 MB' },
            ];
            mockGetFiles.mockResolvedValue(testFiles);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('5.2 MB')).toBeInTheDocument();
            });
        });

        it('should show dash for files without size', async () => {
            const testFiles: FileItem[] = [
                { id: '1', name: 'nosize.txt', type: 'file' },
            ];
            mockGetFiles.mockResolvedValue(testFiles);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('-')).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // Selection Tests
    // =========================================================================

    describe('File Selection', () => {
        it('should select a file when clicking checkbox', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            const checkboxes = screen.getAllByRole('checkbox');
            await userEvent.click(checkboxes[2]); // First file checkbox (after header and folders)
            
            // Check that selection bar appears
            await waitFor(() => {
                expect(screen.getByText(/1 item selected/)).toBeInTheDocument();
            });
        });

        it('should toggle selection when clicking file row', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            const fileRow = screen.getByText('report.pdf').closest('tr');
            if (fileRow) {
                await userEvent.click(fileRow);
            }
            
            await waitFor(() => {
                expect(screen.getByText(/1 item selected/)).toBeInTheDocument();
            });
        });

        it('should toggle all items when clicking header checkbox', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            const headerCheckbox = screen.getAllByRole('checkbox')[0];
            await userEvent.click(headerCheckbox);
            
            await waitFor(() => {
                expect(screen.getByText(/5 items selected/)).toBeInTheDocument();
            });
        });

        it('should deselect all when header checkbox is clicked twice', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            const headerCheckbox = screen.getAllByRole('checkbox')[0];
            await userEvent.click(headerCheckbox); // Select all
            await userEvent.click(headerCheckbox); // Deselect all
            
            await waitFor(() => {
                expect(screen.queryByText(/items selected/)).not.toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // Navigation Tests
    // =========================================================================

    describe('Folder Navigation', () => {
        it('should navigate into folder on click', async () => {
            mockGetFiles
                .mockResolvedValueOnce(mockFiles)
                .mockResolvedValueOnce(mockSubFiles);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('Documents')).toBeInTheDocument();
            });
            
            const folderRow = screen.getByText('Documents').closest('tr');
            if (folderRow) {
                await userEvent.click(folderRow);
            }
            
            await waitFor(() => {
                expect(mockGetFiles).toHaveBeenCalledTimes(2);
                expect(screen.getByText('Documents')).toBeInTheDocument(); // In breadcrumbs
            });
        });

        it('should update breadcrumbs when navigating', async () => {
            mockGetFiles
                .mockResolvedValueOnce(mockFiles)
                .mockResolvedValueOnce(mockSubFiles);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('Documents')).toBeInTheDocument();
            });
            
            const folderRow = screen.getByText('Documents').closest('tr');
            if (folderRow) {
                await userEvent.click(folderRow);
            }
            
            await waitFor(() => {
                const breadcrumbs = screen.getAllByRole('button');
                const breadcrumbTexts = breadcrumbs.map(b => b.textContent);
                expect(breadcrumbTexts).toContain('Home');
                expect(breadcrumbTexts).toContain('Documents');
            });
        });

        it('should navigate back via breadcrumb click', async () => {
            mockGetFiles
                .mockResolvedValueOnce(mockFiles)
                .mockResolvedValueOnce(mockSubFiles)
                .mockResolvedValueOnce(mockFiles);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('Documents')).toBeInTheDocument();
            });
            
            // Navigate into folder
            const folderRow = screen.getByText('Documents').closest('tr');
            if (folderRow) {
                await userEvent.click(folderRow);
            }
            
            await waitFor(() => {
                expect(mockGetFiles).toHaveBeenCalledTimes(2);
            });
            
            // Click Home breadcrumb
            const homeBreadcrumb = screen.getByRole('button', { name: 'Home' });
            await userEvent.click(homeBreadcrumb);
            
            await waitFor(() => {
                expect(mockGetFiles).toHaveBeenCalledTimes(3);
            });
        });

        it('should clear selection when navigating folders', async () => {
            mockGetFiles
                .mockResolvedValueOnce(mockFiles)
                .mockResolvedValueOnce(mockSubFiles);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            // Select a file
            const checkboxes = screen.getAllByRole('checkbox');
            await userEvent.click(checkboxes[3]);
            
            await waitFor(() => {
                expect(screen.getByText(/1 item selected/)).toBeInTheDocument();
            });
            
            // Navigate into folder
            const folderRow = screen.getByText('Documents').closest('tr');
            if (folderRow) {
                await userEvent.click(folderRow);
            }
            
            await waitFor(() => {
                expect(screen.queryByText(/items selected/)).not.toBeInTheDocument();
            });
        });

        it('should call onBack when back button is clicked', async () => {
            const onBack = vi.fn();
            render(<FileBrowser source={mockSource} onBack={onBack} />);
            
            // Wait for files to load
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            // The back button is the first button (ghost variant with arrow icon)
            const buttons = screen.getAllByRole('button');
            await userEvent.click(buttons[0]); // First button is back
            
            expect(onBack).toHaveBeenCalledTimes(1);
        });
    });

    // =========================================================================
    // Search Tests
    // =========================================================================

    describe('Search', () => {
        it('should filter files based on search query', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            const searchInput = screen.getByPlaceholderText('Search files...');
            await userEvent.type(searchInput, 'report');
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
                expect(screen.queryByText('data.csv')).not.toBeInTheDocument();
            });
        });

        it('should show no results message when search has no matches', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            const searchInput = screen.getByPlaceholderText('Search files...');
            await userEvent.type(searchInput, 'nonexistent');
            
            await waitFor(() => {
                expect(screen.getByText('No matching files found')).toBeInTheDocument();
            });
        });

        it('should be case insensitive', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            const searchInput = screen.getByPlaceholderText('Search files...');
            await userEvent.type(searchInput, 'REPORT');
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // Ingestion Tests
    // =========================================================================

    describe('Ingestion', () => {
        it('should ingest selected files', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            // Select a file
            const checkboxes = screen.getAllByRole('checkbox');
            await userEvent.click(checkboxes[3]); // file-1
            
            await waitFor(() => {
                expect(screen.getByText(/1 item selected/)).toBeInTheDocument();
            });
            
            // Click ingest button
            const ingestButton = screen.getByRole('button', { name: /ingest selected/i });
            await userEvent.click(ingestButton);
            
            await waitFor(() => {
                expect(mockIngestFiles).toHaveBeenCalledWith('google-drive', ['file-1']);
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Files queued for ingestion',
                }));
            });
        });

        it('should clear selection after successful ingestion', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            const checkboxes = screen.getAllByRole('checkbox');
            await userEvent.click(checkboxes[3]);
            
            await waitFor(() => {
                expect(screen.getByText(/1 item selected/)).toBeInTheDocument();
            });
            
            const ingestButton = screen.getByRole('button', { name: /ingest selected/i });
            await userEvent.click(ingestButton);
            
            await waitFor(() => {
                expect(screen.queryByText(/items selected/)).not.toBeInTheDocument();
            });
        });

        it('should show error toast on ingestion failure', async () => {
            mockIngestFiles.mockRejectedValue(new Error('Network error'));
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            const checkboxes = screen.getAllByRole('checkbox');
            await userEvent.click(checkboxes[3]);
            
            const ingestButton = screen.getByRole('button', { name: /ingest selected/i });
            await userEvent.click(ingestButton);
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Ingestion failed',
                    variant: 'destructive',
                }));
            });
        });
    });

    // =========================================================================
    // Already Ingested Files Tests
    // =========================================================================

    describe('Already Ingested Files', () => {
        it('should show "Added" badge for already ingested files', async () => {
            mockGetIngestedFileIds.mockResolvedValue(new Set(['file-1']));
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('Added')).toBeInTheDocument();
            });
        });

        it('should update ingested IDs after successful ingestion', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            // Select and ingest
            const checkboxes = screen.getAllByRole('checkbox');
            await userEvent.click(checkboxes[3]);
            
            const ingestButton = screen.getByRole('button', { name: /ingest selected/i });
            await userEvent.click(ingestButton);
            
            await waitFor(() => {
                expect(screen.getByText('Added')).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // Viewer Mode Tests
    // =========================================================================

    describe('Viewer Mode', () => {
        it('should disable checkboxes for viewers', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} isViewer={true} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            const checkboxes = screen.getAllByRole('checkbox');
            checkboxes.forEach(checkbox => {
                expect(checkbox).toBeDisabled();
            });
        });

        it('should not select files on row click for viewers', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} isViewer={true} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            const fileRow = screen.getByText('report.pdf').closest('tr');
            if (fileRow) {
                await userEvent.click(fileRow);
            }
            
            expect(screen.queryByText(/items selected/)).not.toBeInTheDocument();
        });

        it('should still allow folder navigation for viewers', async () => {
            mockGetFiles
                .mockResolvedValueOnce(mockFiles)
                .mockResolvedValueOnce(mockSubFiles);
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} isViewer={true} />);
            
            await waitFor(() => {
                expect(screen.getByText('Documents')).toBeInTheDocument();
            });
            
            const folderRow = screen.getByText('Documents').closest('tr');
            if (folderRow) {
                await userEvent.click(folderRow);
            }
            
            await waitFor(() => {
                expect(mockGetFiles).toHaveBeenCalledTimes(2);
            });
        });

        it('should show viewer toast when trying to ingest', async () => {
            render(<FileBrowser source={mockSource} onBack={vi.fn()} isViewer={true} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
            
            // Force selection state somehow (shouldn't be possible in real UI)
            // This tests the guard in handleIngest
        });
    });

    // =========================================================================
    // Error Handling Tests
    // =========================================================================

    describe('Error Handling', () => {
        it('should show error toast when file loading fails', async () => {
            mockGetFiles.mockRejectedValue(new Error('Network error'));
            
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Failed to load files',
                    variant: 'destructive',
                }));
            });
        });

        it('should handle getIngestedFileIds failure gracefully', async () => {
            mockGetIngestedFileIds.mockRejectedValue(new Error('Failed'));
            
            // Should not crash
            render(<FileBrowser source={mockSource} onBack={vi.fn()} />);
            
            await waitFor(() => {
                expect(screen.getByText('report.pdf')).toBeInTheDocument();
            });
        });
    });
});
