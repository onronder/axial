import { describe, it, expect } from 'vitest';
import {
    MAX_FILE_SIZE,
    MAX_FILE_SIZE_LABEL,
    MIN_FILE_SIZE,
    ACCEPTED_FILE_TYPES,
    SIMPLE_ACCEPTED_FILE_TYPES,
    validateFile,
    validateFiles,
    formatFileSize,
    getFileExtension,
    getUploadMimeType,
    getDropRejectionMessage,
    type FileValidationError,
} from '@/lib/file-validation';

// =============================================================================
// Helper to create mock File objects
// =============================================================================

function createMockFile(
    name: string,
    size: number,
    type: string = 'application/pdf'
): File {
    const content = new Array(size).fill('a').join('');
    const blob = new Blob([content], { type });
    return new File([blob], name, { type });
}

// =============================================================================
// Constants Tests
// =============================================================================

describe('File Validation Constants', () => {
    describe('Size Limits', () => {
        it('should have MAX_FILE_SIZE as 50MB', () => {
            expect(MAX_FILE_SIZE).toBe(50 * 1024 * 1024);
        });

        it('should have MAX_FILE_SIZE_LABEL as "50MB"', () => {
            expect(MAX_FILE_SIZE_LABEL).toBe('50MB');
        });

        it('should have MIN_FILE_SIZE as 1', () => {
            expect(MIN_FILE_SIZE).toBe(1);
        });
    });

    describe('ACCEPTED_FILE_TYPES', () => {
        it('should include PDF files', () => {
            expect(ACCEPTED_FILE_TYPES['application/pdf']).toEqual(['.pdf']);
        });

        it('should include Word documents', () => {
            expect(ACCEPTED_FILE_TYPES['application/vnd.openxmlformats-officedocument.wordprocessingml.document']).toEqual(['.docx']);
            expect(ACCEPTED_FILE_TYPES['application/msword']).toEqual(['.doc']);
        });

        it('should include Excel files', () => {
            expect(ACCEPTED_FILE_TYPES['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']).toEqual(['.xlsx']);
            expect(ACCEPTED_FILE_TYPES['text/csv']).toEqual(['.csv']);
        });

        it('should include PowerPoint files', () => {
            expect(ACCEPTED_FILE_TYPES['application/vnd.openxmlformats-officedocument.presentationml.presentation']).toEqual(['.pptx']);
        });

        it('should include text and code files', () => {
            expect(ACCEPTED_FILE_TYPES['text/plain']).toContain('.txt');
            expect(ACCEPTED_FILE_TYPES['text/plain']).toContain('.py');
            expect(ACCEPTED_FILE_TYPES['text/plain']).toContain('.js');
            expect(ACCEPTED_FILE_TYPES['text/plain']).toContain('.ts');
            expect(ACCEPTED_FILE_TYPES['text/plain']).toContain('.json');
        });

        it('should include markdown files', () => {
            expect(ACCEPTED_FILE_TYPES['text/markdown']).toEqual(['.md', '.markdown']);
        });

        it('should include subtitle files', () => {
            expect(ACCEPTED_FILE_TYPES['text/plain']).toContain('.srt');
            expect(ACCEPTED_FILE_TYPES['text/vtt']).toContain('.vtt');
        });

        it('should include image files', () => {
            expect(ACCEPTED_FILE_TYPES['image/jpeg']).toEqual(['.jpg', '.jpeg']);
            expect(ACCEPTED_FILE_TYPES['image/png']).toEqual(['.png']);
            expect(ACCEPTED_FILE_TYPES['image/tiff']).toEqual(['.tiff', '.tif']);
        });

        it('should include email files', () => {
            expect(ACCEPTED_FILE_TYPES['message/rfc822']).toEqual(['.eml']);
            expect(ACCEPTED_FILE_TYPES['application/vnd.ms-outlook']).toEqual(['.msg']);
        });
    });

    describe('SIMPLE_ACCEPTED_FILE_TYPES', () => {
        it('should only include common file types', () => {
            expect(Object.keys(SIMPLE_ACCEPTED_FILE_TYPES)).toHaveLength(4);
            expect(SIMPLE_ACCEPTED_FILE_TYPES['application/pdf']).toEqual(['.pdf']);
            expect(SIMPLE_ACCEPTED_FILE_TYPES['text/plain']).toEqual(['.txt']);
            expect(SIMPLE_ACCEPTED_FILE_TYPES['text/markdown']).toEqual(['.md']);
        });
    });
});

// =============================================================================
// validateFile Tests
// =============================================================================

describe('validateFile', () => {
    describe('Size Validation', () => {
        it('should return no errors for valid file size', () => {
            const file = createMockFile('test.pdf', 1024);
            const errors = validateFile(file);
            expect(errors).toHaveLength(0);
        });

        it('should return error for file exceeding max size', () => {
            const file = createMockFile('test.pdf', MAX_FILE_SIZE + 1);
            const errors = validateFile(file);
            expect(errors.some(e => e.includes('exceeds'))).toBe(true);
        });

        it('should return error for empty file', () => {
            const file = createMockFile('test.pdf', 0);
            const errors = validateFile(file);
            expect(errors).toContain('File is empty');
        });
    });

    describe('Type Validation', () => {
        it('should accept valid MIME type', () => {
            const file = createMockFile('test.pdf', 100, 'application/pdf');
            const errors = validateFile(file);
            expect(errors).toHaveLength(0);
        });

        it('should accept valid extension even without MIME type', () => {
            const file = createMockFile('test.pdf', 100, '');
            const errors = validateFile(file);
            expect(errors).toHaveLength(0);
        });

        it('should reject unsupported file type', () => {
            const file = createMockFile('test.exe', 100, 'application/x-executable');
            const errors = validateFile(file);
            expect(errors.some(e => e.includes('not supported'))).toBe(true);
        });

        it('should accept Word documents', () => {
            const docx = createMockFile('doc.docx', 100, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document');
            expect(validateFile(docx)).toHaveLength(0);
        });

        it('should accept CSV files', () => {
            const csv = createMockFile('data.csv', 100, 'text/csv');
            expect(validateFile(csv)).toHaveLength(0);
        });

        it('should accept image files', () => {
            const jpg = createMockFile('image.jpg', 100, 'image/jpeg');
            expect(validateFile(jpg)).toHaveLength(0);

            const png = createMockFile('image.png', 100, 'image/png');
            expect(validateFile(png)).toHaveLength(0);
        });

        it('should accept code files by extension', () => {
            const py = createMockFile('script.py', 100, 'text/plain');
            expect(validateFile(py)).toHaveLength(0);

            const ts = createMockFile('app.ts', 100, 'text/plain');
            expect(validateFile(ts)).toHaveLength(0);
        });
    });

    describe('Multiple Errors', () => {
        it('should return multiple errors for multiple issues', () => {
            const file = createMockFile('test.exe', 0, 'application/x-executable');
            const errors = validateFile(file);
            expect(errors.length).toBeGreaterThanOrEqual(2);
        });
    });
});

// =============================================================================
// validateFiles Tests
// =============================================================================

describe('validateFiles', () => {
    it('should return empty array for valid files', () => {
        const files = [
            createMockFile('test1.pdf', 100),
            createMockFile('test2.txt', 200, 'text/plain'),
        ];
        const errors = validateFiles(files);
        expect(errors).toHaveLength(0);
    });

    it('should return errors only for invalid files', () => {
        const files = [
            createMockFile('valid.pdf', 100),
            createMockFile('invalid.exe', 100, 'application/x-executable'),
        ];
        const errors = validateFiles(files);
        expect(errors).toHaveLength(1);
        expect(errors[0].file.name).toBe('invalid.exe');
    });

    it('should return validation errors for each invalid file', () => {
        const files = [
            createMockFile('empty.pdf', 0),
            createMockFile('bad.exe', 100, 'application/x-executable'),
        ];
        const errors = validateFiles(files);
        expect(errors).toHaveLength(2);
    });

    it('should include file reference in error objects', () => {
        const files = [createMockFile('bad.exe', 100, 'application/x-executable')];
        const errors = validateFiles(files);
        expect(errors[0].file).toBeDefined();
        expect(errors[0].file.name).toBe('bad.exe');
    });

    it('should handle empty array', () => {
        const errors = validateFiles([]);
        expect(errors).toHaveLength(0);
    });
});

// =============================================================================
// formatFileSize Tests
// =============================================================================

describe('formatFileSize', () => {
    it('should return "0 B" for 0 bytes', () => {
        expect(formatFileSize(0)).toBe('0 B');
    });

    it('should format bytes', () => {
        expect(formatFileSize(500)).toBe('500 B');
    });

    it('should format kilobytes', () => {
        expect(formatFileSize(1024)).toBe('1 KB');
        expect(formatFileSize(2048)).toBe('2 KB');
    });

    it('should format megabytes', () => {
        expect(formatFileSize(1024 * 1024)).toBe('1 MB');
        expect(formatFileSize(5 * 1024 * 1024)).toBe('5 MB');
    });

    it('should format gigabytes', () => {
        expect(formatFileSize(1024 * 1024 * 1024)).toBe('1 GB');
    });

    it('should handle decimal values', () => {
        expect(formatFileSize(1536)).toBe('1.5 KB'); // 1.5 KB
        expect(formatFileSize(2560 * 1024)).toBe('2.5 MB'); // 2.5 MB
    });
});

describe('getUploadMimeType', () => {
    it('should normalize subtitle uploads to text/plain', () => {
        expect(getUploadMimeType({ name: 'captions.srt', type: '' } as File)).toBe('text/plain');
        expect(getUploadMimeType({ name: 'captions.vtt', type: 'text/vtt' } as File)).toBe('text/plain');
    });

    it('should preserve explicit MIME types for normal files', () => {
        expect(getUploadMimeType({ name: 'doc.pdf', type: 'application/pdf' } as File)).toBe('application/pdf');
    });
});

// =============================================================================
// getFileExtension Tests
// =============================================================================

describe('getFileExtension', () => {
    it('should extract extension from filename', () => {
        expect(getFileExtension('document.pdf')).toBe('.pdf');
        expect(getFileExtension('image.jpg')).toBe('.jpg');
        expect(getFileExtension('script.py')).toBe('.py');
    });

    it('should handle multiple dots in filename', () => {
        expect(getFileExtension('my.document.pdf')).toBe('.pdf');
        expect(getFileExtension('file.test.backup.txt')).toBe('.txt');
    });

    it('should return empty string for no extension', () => {
        expect(getFileExtension('README')).toBe('');
        expect(getFileExtension('Makefile')).toBe('');
    });

    it('should handle hidden files', () => {
        expect(getFileExtension('.gitignore')).toBe('.gitignore');
        expect(getFileExtension('.env')).toBe('.env');
    });

    it('should preserve extension case', () => {
        expect(getFileExtension('Document.PDF')).toBe('.PDF');
        expect(getFileExtension('Image.JPG')).toBe('.JPG');
    });
});

// =============================================================================
// getDropRejectionMessage Tests
// =============================================================================

describe('getDropRejectionMessage', () => {
    it('should return empty string for no rejections', () => {
        expect(getDropRejectionMessage([])).toBe('');
    });

    it('should handle file-too-large error', () => {
        const rejections = [{
            file: createMockFile('big.pdf', MAX_FILE_SIZE + 1),
            errors: [{ code: 'file-too-large', message: 'File is too large' }],
        }];
        const message = getDropRejectionMessage(rejections);
        expect(message).toContain('exceeds 50MB');
    });

    it('should handle file-too-small error', () => {
        const rejections = [{
            file: createMockFile('empty.pdf', 0),
            errors: [{ code: 'file-too-small', message: 'File is too small' }],
        }];
        const message = getDropRejectionMessage(rejections);
        expect(message).toContain('is empty');
    });

    it('should handle file-invalid-type error', () => {
        const rejections = [{
            file: createMockFile('bad.exe', 100, 'application/x-executable'),
            errors: [{ code: 'file-invalid-type', message: 'File type not accepted' }],
        }];
        const message = getDropRejectionMessage(rejections);
        expect(message).toContain('type not supported');
    });

    it('should handle unknown error codes', () => {
        const rejections = [{
            file: createMockFile('file.pdf', 100),
            errors: [{ code: 'unknown-error', message: 'Some unknown error' }],
        }];
        const message = getDropRejectionMessage(rejections);
        expect(message).toContain('Some unknown error');
    });

    it('should combine multiple errors for same file', () => {
        const rejections = [{
            file: createMockFile('bad.exe', MAX_FILE_SIZE + 1, 'application/x-executable'),
            errors: [
                { code: 'file-too-large', message: '' },
                { code: 'file-invalid-type', message: '' },
            ],
        }];
        const message = getDropRejectionMessage(rejections);
        expect(message).toContain('exceeds 50MB');
        expect(message).toContain('type not supported');
    });

    it('should handle multiple file rejections', () => {
        const rejections = [
            {
                file: createMockFile('file1.exe', 100),
                errors: [{ code: 'file-invalid-type', message: '' }],
            },
            {
                file: createMockFile('file2.exe', 100),
                errors: [{ code: 'file-invalid-type', message: '' }],
            },
        ];
        const message = getDropRejectionMessage(rejections);
        expect(message).toContain('file1.exe');
        expect(message).toContain('file2.exe');
    });

    it('should limit to first 3 errors and show count', () => {
        const rejections = [
            { file: createMockFile('f1.exe', 100), errors: [{ code: 'file-invalid-type', message: '' }] },
            { file: createMockFile('f2.exe', 100), errors: [{ code: 'file-invalid-type', message: '' }] },
            { file: createMockFile('f3.exe', 100), errors: [{ code: 'file-invalid-type', message: '' }] },
            { file: createMockFile('f4.exe', 100), errors: [{ code: 'file-invalid-type', message: '' }] },
            { file: createMockFile('f5.exe', 100), errors: [{ code: 'file-invalid-type', message: '' }] },
        ];
        const message = getDropRejectionMessage(rejections);
        expect(message).toContain('...and 2 more');
    });

    it('should not show "and more" for exactly 3 rejections', () => {
        const rejections = [
            { file: createMockFile('f1.exe', 100), errors: [{ code: 'file-invalid-type', message: '' }] },
            { file: createMockFile('f2.exe', 100), errors: [{ code: 'file-invalid-type', message: '' }] },
            { file: createMockFile('f3.exe', 100), errors: [{ code: 'file-invalid-type', message: '' }] },
        ];
        const message = getDropRejectionMessage(rejections);
        expect(message).not.toContain('more');
    });

    it('should include filename in error message', () => {
        const rejections = [{
            file: createMockFile('my-document.exe', 100),
            errors: [{ code: 'file-invalid-type', message: '' }],
        }];
        const message = getDropRejectionMessage(rejections);
        expect(message).toContain('my-document.exe');
    });
});
