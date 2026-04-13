import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IngestionProgressModal } from '@/components/ingestion/IngestionProgressModal';

const mockMarkJobCompleted = vi.fn();

vi.mock('@/hooks/useIngestionProgress', () => ({
  useIngestionProgress: () => ({
    hasJobCompleted: () => false,
    markJobCompleted: mockMarkJobCompleted,
  }),
}));

vi.mock('@/hooks/useFailedTaskStatus', () => ({
  useFailedTaskStatus: () => ({
    failedTask: null,
    loading: false,
  }),
  getTimeUntilRetry: () => '0s',
  formatRetryTime: () => 'now',
}));

vi.mock('@/lib/accessibility', () => ({
  announceToScreenReader: vi.fn(),
  KeyboardShortcuts: class {
    register() {}
    start() {}
    stop() {}
  },
  FocusTrap: class {
    activate() {}
    deactivate() {}
  },
  getProgressLabel: (percentage: number, context: string) => `${context} ${percentage}%`,
  getFileStatusLabel: (status: string, filename: string) => `${filename} ${status}`,
}));

describe('IngestionProgressModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows failed job messaging even when file rows never arrive', async () => {
    const onClose = vi.fn();

    render(
      <IngestionProgressModal
        jobId="job-1"
        files={[]}
        totalFiles={1}
        overallProgress={0}
        jobStatus="failed"
        jobErrorMessage="Scope limit reached for your plan."
        onClose={onClose}
      />
    );

    expect(screen.getByText('Processing Failed')).toBeInTheDocument();
    expect(screen.getByText('The ingestion job failed.')).toBeInTheDocument();
    expect(screen.getAllByText('Scope limit reached for your plan.').length).toBeGreaterThan(0);
    expect(screen.queryByText('Preparing files...')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /close/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
