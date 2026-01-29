import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { FileUploadZone } from '@/components/data-sources/FileUploadZone';
import type { DataSource } from '@/lib/mockData';

// Mock all dependencies
const mockToast = vi.fn();
const mockRefresh = vi.fn();
const mockCheckDuplicates = vi.fn();
const mockGetUploadUrl = vi.fn();
const mockUploadToStorage = vi.fn();
const mockIngestFileReference = vi.fn();
const mockCalculateSHA256 = vi.fn();

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast }),
}));

vi.mock('@/hooks/useUsage', () => ({
  useUsage: () => ({
    filesUsed: 5,
    filesLimit: 100,
    refresh: mockRefresh,
  }),
}));

vi.mock('@/hooks/useFileStatus', () => ({
  useFileStatus: () => ({
    files: [],
  }),
}));

vi.mock('@/lib/api', () => ({
  checkDuplicates: (...args: unknown[]) => mockCheckDuplicates(...args),
  getUploadUrl: (...args: unknown[]) => mockGetUploadUrl(...args),
  uploadToStorage: (...args: unknown[]) => mockUploadToStorage(...args),
  ingestFileReference: (...args: unknown[]) => mockIngestFileReference(...args),
}));

vi.mock('@/lib/hash', async (importOriginal) => {
  const actual = await importOriginal() as Record<string, unknown>;
  return {
    ...actual,
    calculateSHA256: (...args: unknown[]) => mockCalculateSHA256(...args),
  };
});

vi.mock('@/components/ingestion/IngestionProgressModal', () => ({
  IngestionProgressModal: () => null,
}));

vi.mock('@/hooks/useIngestionProgress', () => ({
  useIngestionProgress: () => ({
    registerJob: vi.fn(),
    unregisterJob: vi.fn(),
    updateJobProgress: vi.fn(),
    markJobCompleted: vi.fn(),
    hasJobCompleted: vi.fn().mockReturnValue(false),
    currentJobId: null,
    overallProgress: 0,
    jobFiles: [],
    isComplete: false,
    hasAnyIngestion: false,
    globalToastMessage: null,
    setGlobalToastMessage: vi.fn(),
    clearGlobalToast: vi.fn(),
  }),
  IngestionProgressProvider: ({ children }: { children: React.ReactNode }) => children,
}));

const mockSource: DataSource = {
  id: 'file-upload',
  name: 'File Upload',
  description: 'Upload files from your computer',
  icon: 'file',
  status: 'active',
  type: 'file_upload',
  lastSync: '',
  category: 'files',
};

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  
  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>
  );
}

describe('FileUploadZone', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock implementations
    mockCalculateSHA256.mockResolvedValue('a'.repeat(64));
    mockCheckDuplicates.mockResolvedValue({
      is_duplicate: false,
      existing_document: null,
      action_required: 'none',
    });
    mockGetUploadUrl.mockResolvedValue({
      upload_url: 'https://storage.example.com/upload',
      storage_path: 'uploads/user-1/abc123/file.pdf',
      expires_in: 3600,
    });
    mockUploadToStorage.mockResolvedValue(true);
    mockIngestFileReference.mockResolvedValue({
      status: 'queued',
      doc_id: 'doc-123',
      job_id: 'job-123',
    });
  });

  it('should render upload zone', () => {
    renderWithProviders(<FileUploadZone source={mockSource} />);
    
    expect(screen.getByText('File Upload')).toBeInTheDocument();
    expect(screen.getByText('Upload files from your computer')).toBeInTheDocument();
  });

  it('should show disabled state when disabled prop is true', () => {
    renderWithProviders(<FileUploadZone source={mockSource} disabled />);
    
    expect(screen.getByText('View only')).toBeInTheDocument();
  });

  it('should calculate SHA-256 hash before checking duplicates', async () => {
    const user = userEvent.setup();
    renderWithProviders(<FileUploadZone source={mockSource} />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);
    
    await waitFor(() => {
      expect(mockCalculateSHA256).toHaveBeenCalledWith(file, expect.any(Function));
    });
  });

  it('should check for duplicates after calculating hash', async () => {
    const user = userEvent.setup();
    renderWithProviders(<FileUploadZone source={mockSource} />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);
    
    await waitFor(() => {
      expect(mockCheckDuplicates).toHaveBeenCalledWith(
        'a'.repeat(64),  // The hash
        'test.pdf',       // The filename
        12                // The file size
      );
    });
  });

  it('should show duplicate modal when duplicate is detected', async () => {
    mockCheckDuplicates.mockResolvedValue({
      is_duplicate: true,
      existing_document: {
        id: 'doc-existing',
        title: 'existing.pdf',
        created_at: '2026-01-01T00:00:00Z',
        file_size_bytes: 1234567,
      },
      action_required: 'confirm_overwrite',
    });
    
    const user = userEvent.setup();
    renderWithProviders(<FileUploadZone source={mockSource} />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);
    
    await waitFor(() => {
      expect(screen.getByText('File Already Exists')).toBeInTheDocument();
    });
  });

  it('should proceed with upload when no duplicate found', async () => {
    const user = userEvent.setup();
    renderWithProviders(<FileUploadZone source={mockSource} />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);
    
    await waitFor(() => {
      expect(mockGetUploadUrl).toHaveBeenCalledWith(
        'test.pdf',
        'application/pdf',
        12,
        'a'.repeat(64),  // Content hash
        false             // forceOverwrite
      );
    });
  });

  it('should upload with force_overwrite when user confirms', async () => {
    mockCheckDuplicates.mockResolvedValue({
      is_duplicate: true,
      existing_document: {
        id: 'doc-existing',
        title: 'existing.pdf',
        created_at: '2026-01-01T00:00:00Z',
      },
      action_required: 'confirm_overwrite',
    });
    
    const user = userEvent.setup();
    renderWithProviders(<FileUploadZone source={mockSource} />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);
    
    // Wait for modal to appear
    await waitFor(() => {
      expect(screen.getByText('File Already Exists')).toBeInTheDocument();
    });
    
    // Click overwrite
    fireEvent.click(screen.getByRole('button', { name: /overwrite/i }));
    
    await waitFor(() => {
      expect(mockGetUploadUrl).toHaveBeenCalledWith(
        'test.pdf',
        'application/pdf',
        12,
        'a'.repeat(64),
        true  // forceOverwrite = true
      );
    });
  });

  it('should skip upload when user cancels duplicate', async () => {
    mockCheckDuplicates.mockResolvedValue({
      is_duplicate: true,
      existing_document: {
        id: 'doc-existing',
        title: 'existing.pdf',
        created_at: '2026-01-01T00:00:00Z',
      },
      action_required: 'confirm_overwrite',
    });
    
    const user = userEvent.setup();
    renderWithProviders(<FileUploadZone source={mockSource} />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);
    
    // Wait for modal to appear
    await waitFor(() => {
      expect(screen.getByText('File Already Exists')).toBeInTheDocument();
    });
    
    // Click cancel
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    
    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Upload Cancelled',
        })
      );
    });
    
    // Upload should NOT have been called
    expect(mockGetUploadUrl).not.toHaveBeenCalled();
  });

  it('should show toast on successful upload', async () => {
    const user = userEvent.setup();
    renderWithProviders(<FileUploadZone source={mockSource} />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);
    
    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Files Uploaded',
        })
      );
    });
  });

  it('should refresh usage after upload', async () => {
    const user = userEvent.setup();
    renderWithProviders(<FileUploadZone source={mockSource} />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);
    
    await waitFor(() => {
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  it('should handle upload failure gracefully', async () => {
    mockUploadToStorage.mockResolvedValue(false);
    
    const user = userEvent.setup();
    renderWithProviders(<FileUploadZone source={mockSource} />);
    
    const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    
    await user.upload(input, file);
    
    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith(
        expect.objectContaining({
          title: 'Upload Failed',
          variant: 'destructive',
        })
      );
    });
  });
});

