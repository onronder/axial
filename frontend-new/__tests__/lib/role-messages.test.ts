/**
 * Tests for lib/role-messages.ts - Role-based Access Messages
 */

import { describe, it, expect } from 'vitest';
import {
    ROLE_TOAST_TITLES,
    ROLE_MESSAGES,
    hasEditPermission,
    isViewerRole,
} from '@/lib/role-messages';

describe('ROLE_TOAST_TITLES', () => {
    it('has VIEW_ONLY title', () => {
        expect(ROLE_TOAST_TITLES.VIEW_ONLY).toBe('View only');
    });

    it('has ACTION_LOCKED title', () => {
        expect(ROLE_TOAST_TITLES.ACTION_LOCKED).toBe('Action locked');
    });

    it('has UPGRADE_REQUIRED title', () => {
        expect(ROLE_TOAST_TITLES.UPGRADE_REQUIRED).toBe('Upgrade required');
    });
});

describe('ROLE_MESSAGES', () => {
    it('has generic editor access message', () => {
        expect(ROLE_MESSAGES.NEED_EDITOR_ACCESS).toBe('You need editor or admin access to perform this action.');
    });

    it('has specific action messages', () => {
        expect(ROLE_MESSAGES.NEED_EDITOR_UPLOAD).toBe('You need editor or admin access to upload files.');
        expect(ROLE_MESSAGES.NEED_EDITOR_INGEST).toBe('You need editor or admin access to ingest data.');
        expect(ROLE_MESSAGES.NEED_EDITOR_CONNECT).toBe('You need editor or admin access to connect data sources.');
        expect(ROLE_MESSAGES.NEED_EDITOR_DISCONNECT).toBe('You need editor or admin access to manage connections.');
        expect(ROLE_MESSAGES.NEED_EDITOR_SYNC).toBe('You need editor or admin access to sync data.');
        expect(ROLE_MESSAGES.NEED_EDITOR_DELETE).toBe('You need editor or admin access to delete documents.');
        expect(ROLE_MESSAGES.NEED_EDITOR_CRAWL).toBe('You need editor or admin access to run crawls.');
        expect(ROLE_MESSAGES.NEED_EDITOR_INGEST_VIDEOS).toBe('You need editor or admin access to ingest videos.');
        expect(ROLE_MESSAGES.NEED_EDITOR_BROWSE).toBe('You need editor or admin access to browse files.');
    });

    it('has plan upgrade messages', () => {
        expect(ROLE_MESSAGES.WEB_CRAWL_UPGRADE).toBe('Web crawling is available on Starter and above plans.');
        expect(ROLE_MESSAGES.YOUTUBE_UPGRADE).toBe('YouTube ingestion requires Starter or Pro plan.');
    });
});

describe('hasEditPermission', () => {
    it('returns true for editor role', () => {
        expect(hasEditPermission('editor')).toBe(true);
    });

    it('returns true for admin role', () => {
        expect(hasEditPermission('admin')).toBe(true);
    });

    it('returns true for owner role', () => {
        expect(hasEditPermission('owner')).toBe(true);
    });

    it('returns false for viewer role', () => {
        expect(hasEditPermission('viewer')).toBe(false);
    });

    it('returns false for undefined', () => {
        expect(hasEditPermission(undefined)).toBe(false);
    });

    it('returns false for null', () => {
        expect(hasEditPermission(null)).toBe(false);
    });

    it('returns false for empty string', () => {
        expect(hasEditPermission('')).toBe(false);
    });

    it('handles case-insensitive role names', () => {
        expect(hasEditPermission('EDITOR')).toBe(true);
        expect(hasEditPermission('Admin')).toBe(true);
        expect(hasEditPermission('OWNER')).toBe(true);
        expect(hasEditPermission('VIEWER')).toBe(false);
    });

    it('returns false for unknown roles', () => {
        expect(hasEditPermission('guest')).toBe(false);
        expect(hasEditPermission('member')).toBe(false);
        expect(hasEditPermission('user')).toBe(false);
    });
});

describe('isViewerRole', () => {
    it('returns true for viewer role', () => {
        expect(isViewerRole('viewer')).toBe(true);
    });

    it('returns false for editor role', () => {
        expect(isViewerRole('editor')).toBe(false);
    });

    it('returns false for admin role', () => {
        expect(isViewerRole('admin')).toBe(false);
    });

    it('returns false for owner role', () => {
        expect(isViewerRole('owner')).toBe(false);
    });

    it('returns false for undefined', () => {
        expect(isViewerRole(undefined)).toBe(false);
    });

    it('returns false for null', () => {
        expect(isViewerRole(null)).toBe(false);
    });

    it('handles case-insensitive viewer', () => {
        expect(isViewerRole('VIEWER')).toBe(true);
        expect(isViewerRole('Viewer')).toBe(true);
    });
});
