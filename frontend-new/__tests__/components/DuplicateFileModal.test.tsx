import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { DuplicateFileModal } from '@/components/data-sources/DuplicateFileModal';
import type { ExistingDocument } from '@/lib/api';

describe('DuplicateFileModal', () => {
  const mockOnAction = vi.fn();

  const defaultProps = {
    open: true,
    filename: 'new-report.pdf',
    existingDocument: {
      id: 'doc-123',
      title: 'existing-report.pdf',
      created_at: '2026-01-10T10:00:00Z',
      file_size_bytes: 1234567,
    } as ExistingDocument,
    onAction: mockOnAction,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render modal when open is true', () => {
    render(<DuplicateFileModal {...defaultProps} />);
    
    expect(screen.getByText('File Already Exists')).toBeInTheDocument();
    expect(screen.getByText(/identical content already exists/)).toBeInTheDocument();
  });

  it('should not render modal when open is false', () => {
    render(<DuplicateFileModal {...defaultProps} open={false} />);
    
    expect(screen.queryByText('File Already Exists')).not.toBeInTheDocument();
  });

  it('should display the uploading filename', () => {
    render(<DuplicateFileModal {...defaultProps} />);
    
    expect(screen.getByText('new-report.pdf')).toBeInTheDocument();
  });

  it('should display the existing document title', () => {
    render(<DuplicateFileModal {...defaultProps} />);
    
    expect(screen.getByText('existing-report.pdf')).toBeInTheDocument();
  });

  it('should display formatted date', () => {
    render(<DuplicateFileModal {...defaultProps} />);
    
    // Date should be formatted (Jan 10, 2026 or similar depending on locale)
    expect(screen.getByText(/Jan/)).toBeInTheDocument();
    expect(screen.getByText(/2026/)).toBeInTheDocument();
  });

  it('should display formatted file size', () => {
    render(<DuplicateFileModal {...defaultProps} />);
    
    // 1234567 bytes ≈ 1.2 MB
    expect(screen.getByText(/1\.2 MB/)).toBeInTheDocument();
  });

  it('should call onAction with "cancel" when Cancel is clicked', () => {
    render(<DuplicateFileModal {...defaultProps} />);
    
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    
    expect(mockOnAction).toHaveBeenCalledWith('cancel');
    expect(mockOnAction).toHaveBeenCalledTimes(1);
  });

  it('should call onAction with "overwrite" when Overwrite is clicked', () => {
    render(<DuplicateFileModal {...defaultProps} />);
    
    fireEvent.click(screen.getByRole('button', { name: /overwrite/i }));
    
    expect(mockOnAction).toHaveBeenCalledWith('overwrite');
    expect(mockOnAction).toHaveBeenCalledTimes(1);
  });

  it('should handle missing existingDocument gracefully', () => {
    render(
      <DuplicateFileModal
        {...defaultProps}
        existingDocument={undefined}
      />
    );
    
    // Should still render without crashing
    expect(screen.getByText('File Already Exists')).toBeInTheDocument();
    // Should fall back to the new filename
    expect(screen.getAllByText('new-report.pdf').length).toBeGreaterThanOrEqual(1);
  });

  it('should handle missing file_size_bytes gracefully', () => {
    render(
      <DuplicateFileModal
        {...defaultProps}
        existingDocument={{
          id: 'doc-123',
          title: 'test.pdf',
          created_at: '2026-01-10T10:00:00Z',
          file_size_bytes: undefined,
        }}
      />
    );
    
    // Should render without file size
    expect(screen.getByText('File Already Exists')).toBeInTheDocument();
    expect(screen.queryByText(/MB/)).not.toBeInTheDocument();
  });

  it('should have accessible button labels', () => {
    render(<DuplicateFileModal {...defaultProps} />);
    
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    const overwriteButton = screen.getByRole('button', { name: /overwrite/i });
    
    expect(cancelButton).toBeInTheDocument();
    expect(overwriteButton).toBeInTheDocument();
  });

  it('should display warning text about overwriting', () => {
    render(<DuplicateFileModal {...defaultProps} />);
    
    expect(screen.getByText(/Overwriting will replace/)).toBeInTheDocument();
  });
});

