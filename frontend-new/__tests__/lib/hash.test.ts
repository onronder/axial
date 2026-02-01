import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { formatFileSize, formatDate, calculateSHA256 } from '@/lib/hash';

// Mock crypto.subtle for Node.js/jsdom environment
const mockDigest = vi.fn();

// Setup global crypto mock before tests
beforeEach(() => {
  // Mock crypto.subtle.digest to return a predictable hash
  mockDigest.mockImplementation(async (_algorithm: string, _data: ArrayBuffer) => {
    // Return a 32-byte (256-bit) ArrayBuffer representing a fake hash
    const hash = new Uint8Array(32);
    for (let i = 0; i < 32; i++) {
      hash[i] = i; // Predictable bytes: 00, 01, 02, ..., 1f
    }
    return hash.buffer;
  });

  // Define crypto.subtle if it doesn't exist
  if (!globalThis.crypto) {
    Object.defineProperty(globalThis, 'crypto', {
      value: {
        subtle: {
          digest: mockDigest,
        },
      },
      configurable: true,
    });
  } else if (!globalThis.crypto.subtle) {
    Object.defineProperty(globalThis.crypto, 'subtle', {
      value: {
        digest: mockDigest,
      },
      configurable: true,
    });
  } else {
    vi.spyOn(globalThis.crypto.subtle, 'digest').mockImplementation(mockDigest);
  }
});

afterEach(() => {
  vi.restoreAllMocks();
});

// Helper to create a mock File with arrayBuffer support for jsdom
function createMockFile(content: string, name: string = 'test.txt'): File {
  const encoder = new TextEncoder();
  const buffer = encoder.encode(content).buffer;
  
  // Create a File-like object that works in jsdom
  const file = {
    name,
    type: 'text/plain',
    size: content.length,
    lastModified: Date.now(),
    arrayBuffer: vi.fn().mockResolvedValue(buffer),
    slice: vi.fn(),
    stream: vi.fn(),
    text: vi.fn().mockResolvedValue(content),
  } as unknown as File;
  
  return file;
}

describe('calculateSHA256', () => {
  it('should calculate hash for small files (< 10MB)', async () => {
    const file = createMockFile('Hello, World!');
    
    const hash = await calculateSHA256(file);
    
    // Expected hash from our mock: 000102...1e1f (32 bytes as hex)
    expect(hash).toBe('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f');
    expect(hash).toHaveLength(64); // SHA-256 produces 64 hex characters
  });

  it('should handle files without progress callback', async () => {
    const file = createMockFile('Test content without progress');
    
    // Should not throw when called without progress callback
    const hash = await calculateSHA256(file);
    
    expect(hash).toBeDefined();
    expect(typeof hash).toBe('string');
    expect(hash).toHaveLength(64);
  });

  it('should produce consistent output for same input', async () => {
    const content = 'Consistent content for hashing';
    const file1 = createMockFile(content);
    const file2 = createMockFile(content);
    
    const hash1 = await calculateSHA256(file1);
    const hash2 = await calculateSHA256(file2);
    
    // Same input should produce same hash (with our mock)
    expect(hash1).toBe(hash2);
  });

  it('should call progress callback with correct values', async () => {
    const file = createMockFile('Test file');
    const progressCallback = vi.fn();
    
    await calculateSHA256(file, progressCallback);
    
    // For small files: 0 -> 50 -> 100
    expect(progressCallback).toHaveBeenCalledWith(0);
    expect(progressCallback).toHaveBeenCalledWith(50);
    expect(progressCallback).toHaveBeenCalledWith(100);
  });

  it('should return hex string format', async () => {
    const file = createMockFile('Some data');
    
    const hash = await calculateSHA256(file);
    
    // Verify it's a valid hex string
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('should use chunked hashing for large files (>= 10MB)', async () => {
    // Create a large file mock (11MB)
    const largeSize = 11 * 1024 * 1024;
    const chunkSize = 2 * 1024 * 1024;
    const totalChunks = Math.ceil(largeSize / chunkSize);
    
    // Mock the Blob.slice().arrayBuffer() chain
    const mockChunkBuffer = new ArrayBuffer(chunkSize);
    const mockSlice = vi.fn().mockReturnValue({
      arrayBuffer: vi.fn().mockResolvedValue(mockChunkBuffer),
    });

    const largeFile = {
      name: 'large-file.bin',
      type: 'application/octet-stream',
      size: largeSize,
      lastModified: Date.now(),
      arrayBuffer: vi.fn(), // Not called for large files
      slice: mockSlice,
      stream: vi.fn(),
      text: vi.fn(),
    } as unknown as File;

    const progressCallback = vi.fn();
    
    const hash = await calculateSHA256(largeFile, progressCallback);
    
    // Verify chunked processing
    expect(mockSlice).toHaveBeenCalledTimes(totalChunks);
    expect(largeFile.arrayBuffer).not.toHaveBeenCalled(); // Should not use direct arrayBuffer
    
    // Verify progress updates
    expect(progressCallback).toHaveBeenCalledWith(expect.any(Number));
    
    // Should have final progress values for chunked processing
    // Reading is 0-80%, hashing is 80-100%
    const calls = progressCallback.mock.calls.map(c => c[0]);
    expect(calls.some(p => p <= 80)).toBe(true); // Reading progress
    expect(calls).toContain(90); // Before final hash
    expect(calls).toContain(100); // After hash
    
    // Result should still be a valid hash
    expect(hash).toHaveLength(64);
    expect(hash).toMatch(/^[0-9a-f]{64}$/);
  });

  it('should calculate correct slice ranges for chunked files', async () => {
    const fileSize = 5 * 1024 * 1024; // 5MB chunks would need 3 slices at 2MB each
    const actualSize = 11 * 1024 * 1024; // 11MB file = 6 chunks at 2MB each
    
    const sliceCalls: Array<{ start: number; end: number }> = [];
    
    const mockSlice = vi.fn((start: number, end: number) => {
      sliceCalls.push({ start, end });
      return {
        arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(end - start)),
      };
    });

    const file = {
      name: 'chunked-file.bin',
      type: 'application/octet-stream',
      size: actualSize,
      lastModified: Date.now(),
      arrayBuffer: vi.fn(),
      slice: mockSlice,
      stream: vi.fn(),
      text: vi.fn(),
    } as unknown as File;

    await calculateSHA256(file);

    // Verify all chunks were sliced correctly
    const chunkSize = 2 * 1024 * 1024;
    const expectedChunks = Math.ceil(actualSize / chunkSize);
    expect(sliceCalls).toHaveLength(expectedChunks);
    
    // First chunk
    expect(sliceCalls[0]).toEqual({ start: 0, end: chunkSize });
    
    // Last chunk should end at file size
    const lastCall = sliceCalls[sliceCalls.length - 1];
    expect(lastCall.end).toBe(actualSize);
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

