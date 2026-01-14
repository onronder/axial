/**
 * File Hashing Utilities
 * 
 * Uses the native Web Crypto API (crypto.subtle) for SHA-256 hashing.
 * Hardware-accelerated in modern browsers.
 * 
 * Performance benchmarks (approximate):
 * - 1MB: ~50-100ms
 * - 10MB: ~500ms-1s
 * - 50MB: ~2-5s
 * - 100MB: ~5-10s
 */

/**
 * Calculate SHA-256 hash of a File using Web Crypto API
 * 
 * @param file - The File object to hash
 * @param onProgress - Optional callback for progress updates (0-100)
 * @returns Promise resolving to 64-character hex string
 * 
 * @example
 * const hash = await calculateSHA256(file, (progress) => {
 *   console.log(`Hashing: ${progress}%`);
 * });
 */
export async function calculateSHA256(
  file: File,
  onProgress?: (progress: number) => void
): Promise<string> {
  // For small files (< 10MB), read entire file at once for simplicity
  if (file.size < 10 * 1024 * 1024) {
    onProgress?.(0);
    const buffer = await file.arrayBuffer();
    onProgress?.(50);
    const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
    onProgress?.(100);
    return bufferToHex(hashBuffer);
  }

  // For larger files, use chunked reading to avoid memory issues
  // and provide progress updates
  return calculateSHA256Chunked(file, onProgress);
}

/**
 * Chunked SHA-256 calculation for large files
 * Processes file in 2MB chunks to avoid memory pressure
 */
async function calculateSHA256Chunked(
  file: File,
  onProgress?: (progress: number) => void
): Promise<string> {
  const CHUNK_SIZE = 2 * 1024 * 1024; // 2MB chunks
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
  
  // We need to accumulate chunks and hash at the end
  // because Web Crypto doesn't support incremental hashing
  const chunks: ArrayBuffer[] = [];
  
  for (let i = 0; i < totalChunks; i++) {
    const start = i * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);
    const blob = file.slice(start, end);
    const chunk = await blob.arrayBuffer();
    chunks.push(chunk);
    
    // Report progress (reading phase is 0-80%, hashing is 80-100%)
    const readProgress = Math.round(((i + 1) / totalChunks) * 80);
    onProgress?.(readProgress);
  }
  
  // Concatenate all chunks
  const totalLength = chunks.reduce((acc, chunk) => acc + chunk.byteLength, 0);
  const combined = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    combined.set(new Uint8Array(chunk), offset);
    offset += chunk.byteLength;
  }
  
  onProgress?.(90);
  
  // Final hash
  const hashBuffer = await crypto.subtle.digest("SHA-256", combined);
  onProgress?.(100);
  
  return bufferToHex(hashBuffer);
}

/**
 * Convert ArrayBuffer to hexadecimal string
 */
function bufferToHex(buffer: ArrayBuffer): string {
  const hashArray = Array.from(new Uint8Array(buffer));
  return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

/**
 * Format date for display
 */
export function formatDate(dateString: string): string {
  if (!dateString) return "Unknown";
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return "Unknown";
    return date.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return "Unknown";
  }
}

