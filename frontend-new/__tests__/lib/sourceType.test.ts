import { describe, it, expect } from 'vitest';
import { normalizeSourceType, formatSourceTypeLabel } from '@/lib/sourceType';

describe('sourceType', () => {
    it('normalizes aliases and casing', () => {
        expect(normalizeSourceType('Google Drive')).toBe('google_drive');
        expect(normalizeSourceType('one-drive')).toBe('onedrive');
    });

    it('returns undefined for empty values', () => {
        expect(normalizeSourceType(null)).toBeUndefined();
        expect(normalizeSourceType('')).toBeUndefined();
    });

    it('formats labels for known types', () => {
        expect(formatSourceTypeLabel('google_drive')).toBe('Google Drive');
        expect(formatSourceTypeLabel('one_drive')).toBe('OneDrive');
    });

    it('returns fallback label for unknown types', () => {
        expect(formatSourceTypeLabel('Custom Source')).toBe('custom_source');
        expect(formatSourceTypeLabel(null)).toBe('Unknown');
    });
});
