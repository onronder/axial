/**
 * File Validation Constants & Utilities
 * 
 * Production-grade file validation for client-side upload security.
 * These validations complement server-side checks - never trust client alone.
 * 
 * @see https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload
 */

// =============================================================================
// SIZE LIMITS
// =============================================================================

/**
 * Maximum file size in bytes (50MB)
 * Matches backend limit to prevent unnecessary upload attempts
 */
export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

/**
 * Human-readable max file size
 */
export const MAX_FILE_SIZE_LABEL = "50MB";

/**
 * Minimum file size (1 byte) - prevents empty file uploads
 */
export const MIN_FILE_SIZE = 1;

// =============================================================================
// ACCEPTED FILE TYPES
// =============================================================================

/**
 * Comprehensive accepted file types for dropzone
 * Keys are MIME types, values are file extensions
 */
export const ACCEPTED_FILE_TYPES: Record<string, string[]> = {
  // Documents
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/msword": [".doc"],
  "application/rtf": [".rtf"],

  // Spreadsheets
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
  "application/vnd.ms-excel": [".xls"],
  "text/csv": [".csv"],
  "text/tab-separated-values": [".tsv"],

  // Presentations
  "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
  "application/vnd.ms-powerpoint": [".ppt"],

  // Email
  "message/rfc822": [".eml"],
  "application/vnd.ms-outlook": [".msg"],

  // Text & Code
  "text/plain": [
    ".txt",
    ".srt",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".cpp",
    ".c",
    ".cs",
    ".rb",
    ".php",
    ".rs",
    ".scala",
    ".swift",
    ".kt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".conf",
    ".config",
    ".xml",
    ".css",
    ".sql",
    ".env",
    ".sh",
    ".dockerfile",
    ".log",
  ],
  "text/vtt": [".vtt"],
  "application/x-subrip": [".srt"],
  "text/markdown": [".md", ".markdown"],
  "text/html": [".html", ".htm"],
  "application/json": [".json"],
  "application/xml": [".xml"],
  "text/xml": [".xml"],

  // Images (OCR via LlamaParse)
  "image/jpeg": [".jpg", ".jpeg"],
  "image/png": [".png"],
  "image/tiff": [".tiff", ".tif"],
  "image/bmp": [".bmp"],
};

/**
 * Simplified accepted file types for chat empty state
 * (Most common types for quick upload)
 */
export const SIMPLE_ACCEPTED_FILE_TYPES: Record<string, string[]> = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
};

// =============================================================================
// VALIDATION UTILITIES
// =============================================================================

export interface FileValidationError {
  file: File;
  errors: string[];
}

/**
 * Validate a single file against size and type constraints
 */
export function validateFile(file: File): string[] {
  const errors: string[] = [];

  // Size validation
  if (file.size > MAX_FILE_SIZE) {
    errors.push(`File exceeds ${MAX_FILE_SIZE_LABEL} limit (${formatFileSize(file.size)})`);
  }

  if (file.size < MIN_FILE_SIZE) {
    errors.push("File is empty");
  }

  // Type validation (MIME type)
  const acceptedMimeTypes = Object.keys(ACCEPTED_FILE_TYPES);
  const isAcceptedMime = acceptedMimeTypes.includes(file.type);
  
  // Extension validation (fallback for when MIME type is not set)
  const extension = getFileExtension(file.name);
  const isAcceptedExtension = Object.values(ACCEPTED_FILE_TYPES)
    .flat()
    .includes(extension.toLowerCase());

  if (!isAcceptedMime && !isAcceptedExtension) {
    errors.push(`File type not supported (${file.type || extension})`);
  }

  return errors;
}

/**
 * Validate multiple files
 */
export function validateFiles(files: File[]): FileValidationError[] {
  return files
    .map((file) => ({ file, errors: validateFile(file) }))
    .filter(({ errors }) => errors.length > 0);
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Get file extension from filename
 */
export function getFileExtension(filename: string): string {
  const lastDot = filename.lastIndexOf(".");
  return lastDot !== -1 ? filename.slice(lastDot) : "";
}

/**
 * Resolve a safe upload MIME type.
 * Prefers explicit browser MIME types, but normalizes subtitle uploads and
 * falls back to extension-derived MIME for empty browser values.
 */
export function getUploadMimeType(file: Pick<File, "name" | "type">): string {
  const extension = getFileExtension(file.name).toLowerCase();

  if (extension === ".srt" || extension === ".vtt") {
    return "text/plain";
  }

  if (file.type) {
    return file.type;
  }

  for (const [mimeType, extensions] of Object.entries(ACCEPTED_FILE_TYPES)) {
    if (extensions.includes(extension)) {
      return mimeType;
    }
  }

  return "application/octet-stream";
}

/**
 * Create user-friendly error message for rejected files
 * Uses readonly arrays to be compatible with react-dropzone's FileRejection type
 */
export function getDropRejectionMessage(
  rejections: ReadonlyArray<{ file: File; errors: ReadonlyArray<{ code: string; message: string }> }>
): string {
  if (rejections.length === 0) return "";

  const messages: string[] = [];

  for (const rejection of rejections) {
    const fileErrors: string[] = [];
    
    for (const error of rejection.errors) {
      switch (error.code) {
        case "file-too-large":
          fileErrors.push(`exceeds ${MAX_FILE_SIZE_LABEL}`);
          break;
        case "file-too-small":
          fileErrors.push("is empty");
          break;
        case "file-invalid-type":
          fileErrors.push("type not supported");
          break;
        default:
          fileErrors.push(error.message);
      }
    }
    
    messages.push(`${rejection.file.name}: ${fileErrors.join(", ")}`);
  }

  // Limit to first 3 errors to avoid overwhelming UI
  const displayMessages = messages.slice(0, 3);
  const remaining = messages.length - 3;
  
  if (remaining > 0) {
    displayMessages.push(`...and ${remaining} more`);
  }

  return displayMessages.join("\n");
}
