/**
 * Unit Tests for useTheme Hook
 * 
 * Tests covering:
 * - Theme state management
 * - Theme toggle
 * - Resolved theme
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock next-themes
const mockSetTheme = vi.fn();
const mockUseThemeReturn = {
    theme: 'system',
    setTheme: mockSetTheme,
    resolvedTheme: 'dark',
    systemTheme: 'dark',
};

vi.mock('next-themes', () => ({
    useTheme: () => mockUseThemeReturn,
}));

import { useTheme } from '@/hooks/useTheme';

describe('useTheme Hook', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseThemeReturn.theme = 'system';
        mockUseThemeReturn.resolvedTheme = 'dark';
    });

    describe('Theme State', () => {
        it('should return current theme', () => {
            const result = useTheme();
            expect(result.theme).toBe('system');
        });

        it('should return resolved theme', () => {
            const result = useTheme();
            expect(result.resolvedTheme).toBe('dark');
        });

        it('should return setTheme function', () => {
            const result = useTheme();
            expect(typeof result.setTheme).toBe('function');
        });
    });

    describe('Theme Values', () => {
        it('should handle dark theme', () => {
            mockUseThemeReturn.theme = 'dark';
            mockUseThemeReturn.resolvedTheme = 'dark';

            const result = useTheme();
            expect(result.theme).toBe('dark');
            expect(result.resolvedTheme).toBe('dark');
        });

        it('should handle light theme', () => {
            mockUseThemeReturn.theme = 'light';
            mockUseThemeReturn.resolvedTheme = 'light';

            const result = useTheme();
            expect(result.theme).toBe('light');
            expect(result.resolvedTheme).toBe('light');
        });

        it('should handle system theme with light preference', () => {
            mockUseThemeReturn.theme = 'system';
            mockUseThemeReturn.resolvedTheme = 'light';
            mockUseThemeReturn.systemTheme = 'light';

            const result = useTheme();
            expect(result.theme).toBe('system');
            expect(result.resolvedTheme).toBe('light');
        });
    });

    describe('setTheme', () => {
        it('should call setTheme with new value', () => {
            const result = useTheme();
            result.setTheme('dark');

            expect(mockSetTheme).toHaveBeenCalledWith('dark');
        });

        it('should accept light theme', () => {
            const result = useTheme();
            result.setTheme('light');

            expect(mockSetTheme).toHaveBeenCalledWith('light');
        });

        it('should accept system theme', () => {
            const result = useTheme();
            result.setTheme('system');

            expect(mockSetTheme).toHaveBeenCalledWith('system');
        });
    });
});
