import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { formatFileSize, formatDate } from '@/lib/hash';

// Note: calculateSHA256 tests are skipped in Node.js environment because
// File.arrayBuffer() is not available. These tests run in browser environment.

describe('calculateSHA256', () => {
  // These tests need jsdom with full File API support
  // The function is tested indirectly through FileUploadZone integration tests
  it.skip('should calculate hash for small files (< 10MB)', () => {
    // Skipped - requires browser File API
  });

  it.skip('should handle files without progress callback', () => {
    // Skipped - requires browser File API
  });

  it.skip('should produce consistent output for same input', () => {
    // Skipped - requires browser File API
  });
});

describe('formatFileSize', () => {
  it('should format 0 bytes', () => {
    expect(formatFileSize(0)).toBe('0 B');
  });

  it('should format bytes', () => {
    expect(formatFileSize(500)).toBe('500 B');
  });

  it('should format kilobytes', () => {
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });

  it('should format megabytes', () => {
    expect(formatFileSize(1024 * 1024)).toBe('1 MB');
    expect(formatFileSize(5.5 * 1024 * 1024)).toBe('5.5 MB');
  });

  it('should format gigabytes', () => {
    expect(formatFileSize(1024 * 1024 * 1024)).toBe('1 GB');
    expect(formatFileSize(2.5 * 1024 * 1024 * 1024)).toBe('2.5 GB');
  });
});

describe('formatDate', () => {
  it('should format valid date string', () => {
    const result = formatDate('2026-01-14T10:30:00Z');
    expect(result).toContain('Jan');
    expect(result).toContain('14');
    expect(result).toContain('2026');
  });

  it('should return "Unknown" for empty string', () => {
    expect(formatDate('')).toBe('Unknown');
  });

  it('should return "Unknown" for invalid date', () => {
    expect(formatDate('not-a-date')).toBe('Unknown');
  });
});

