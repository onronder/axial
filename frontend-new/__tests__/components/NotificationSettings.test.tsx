/**
 * Unit Tests for NotificationSettings Component
 * 
 * Tests the NotificationSettings component including:
 * - Rendering of settings grouped by category
 * - Toggle interactions
 * - Loading and error states
 * - Email ingestion setting visibility
 */

import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { NotificationSettings } from '@/components/settings/NotificationSettings';

// Mock the hook
const mockToggleSetting = vi.fn();
const mockSettings = {
    emailSettings: [
        {
            id: '1',
            setting_key: 'email_on_ingestion_complete',
            setting_label: 'Ingestion Complete Emails',
            setting_description: 'Receive email when processing finishes',
            category: 'email' as const,
            enabled: true,
        },
        {
            id: '2',
            setting_key: 'weekly-digest',
            setting_label: 'Weekly Digest',
            setting_description: 'Receive weekly summary',
            category: 'email' as const,
            enabled: false,
        },
    ],
    systemSettings: [
        {
            id: '3',
            setting_key: 'ingestion-completed',
            setting_label: 'Ingestion Completed',
            setting_description: 'System notification when file finishes',
            category: 'system' as const,
            enabled: true,
        },
    ],
    isLoading: false,
    toggleSetting: mockToggleSetting,
};

vi.mock('@/hooks/useNotificationSettings', () => ({
    useNotificationSettings: vi.fn(() => mockSettings),
}));

import { useNotificationSettings } from '@/hooks/useNotificationSettings';
const mockUseNotificationSettings = useNotificationSettings as ReturnType<typeof vi.fn>;

describe('NotificationSettings Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockUseNotificationSettings.mockReturnValue(mockSettings);
    });

    describe('Rendering', () => {
        it('should render page title', () => {
            render(<NotificationSettings />);
            expect(screen.getByText('Notifications')).toBeInTheDocument();
        });

        it('should render page description', () => {
            render(<NotificationSettings />);
            expect(screen.getByText(/Manage how Axio Hub communicates with you/i)).toBeInTheDocument();
        });

        it('should render Email Notifications section', () => {
            render(<NotificationSettings />);
            expect(screen.getByText('Email Notifications')).toBeInTheDocument();
        });

        it('should render System Alerts section', () => {
            render(<NotificationSettings />);
            expect(screen.getByText('System Alerts')).toBeInTheDocument();
        });
    });

    describe('Email Ingestion Setting', () => {
        it('should display email_on_ingestion_complete setting', () => {
            render(<NotificationSettings />);
            expect(screen.getByText('Ingestion Complete Emails')).toBeInTheDocument();
        });

        it('should display email ingestion setting description', () => {
            render(<NotificationSettings />);
            expect(screen.getByText('Receive email when processing finishes')).toBeInTheDocument();
        });

        it('should have a toggle switch for email ingestion setting', () => {
            render(<NotificationSettings />);
            const toggle = screen.getByRole('switch', { name: /ingestion complete emails/i });
            expect(toggle).toBeInTheDocument();
        });

        it('should show email ingestion setting as enabled', () => {
            render(<NotificationSettings />);
            const toggle = screen.getByRole('switch', { name: /ingestion complete emails/i });
            expect(toggle).toBeChecked();
        });
    });

    describe('Toggle Interactions', () => {
        it('should call toggleSetting when switch is clicked', () => {
            render(<NotificationSettings />);
            const toggle = screen.getByRole('switch', { name: /ingestion complete emails/i });

            fireEvent.click(toggle);

            expect(mockToggleSetting).toHaveBeenCalledWith('email_on_ingestion_complete');
        });

        it('should call toggleSetting with correct key for other settings', () => {
            render(<NotificationSettings />);
            const toggle = screen.getByRole('switch', { name: /weekly digest/i });

            fireEvent.click(toggle);

            expect(mockToggleSetting).toHaveBeenCalledWith('weekly-digest');
        });

        it('should call toggleSetting for system settings', () => {
            render(<NotificationSettings />);
            const toggle = screen.getByRole('switch', { name: /ingestion completed/i });

            fireEvent.click(toggle);

            expect(mockToggleSetting).toHaveBeenCalledWith('ingestion-completed');
        });
    });

    describe('Loading State', () => {
        it('should show loading spinner when loading', () => {
            mockUseNotificationSettings.mockReturnValue({
                ...mockSettings,
                isLoading: true,
            });

            render(<NotificationSettings />);
            // Loader2 from lucide-react renders as an SVG with animate-spin class
            const loader = document.querySelector('.animate-spin');
            expect(loader).toBeInTheDocument();
        });

        it('should not show settings when loading', () => {
            mockUseNotificationSettings.mockReturnValue({
                ...mockSettings,
                isLoading: true,
            });

            render(<NotificationSettings />);
            expect(screen.queryByText('Email Notifications')).not.toBeInTheDocument();
        });
    });

    describe('Empty States', () => {
        it('should show empty message when no email settings', () => {
            mockUseNotificationSettings.mockReturnValue({
                ...mockSettings,
                emailSettings: [],
            });

            render(<NotificationSettings />);
            expect(screen.getByText(/No email notification settings available/i)).toBeInTheDocument();
        });

        it('should show empty message when no system settings', () => {
            mockUseNotificationSettings.mockReturnValue({
                ...mockSettings,
                systemSettings: [],
            });

            render(<NotificationSettings />);
            expect(screen.getByText(/No system alert settings available/i)).toBeInTheDocument();
        });
    });

    describe('Settings Display', () => {
        it('should display all email settings', () => {
            render(<NotificationSettings />);
            expect(screen.getByText('Ingestion Complete Emails')).toBeInTheDocument();
            expect(screen.getByText('Weekly Digest')).toBeInTheDocument();
        });

        it('should display all system settings', () => {
            render(<NotificationSettings />);
            expect(screen.getByText('Ingestion Completed')).toBeInTheDocument();
        });

        it('should display setting descriptions', () => {
            render(<NotificationSettings />);
            expect(screen.getByText('Receive email when processing finishes')).toBeInTheDocument();
            expect(screen.getByText('Receive weekly summary')).toBeInTheDocument();
            expect(screen.getByText('System notification when file finishes')).toBeInTheDocument();
        });

        it('should correctly show enabled state for each setting', () => {
            render(<NotificationSettings />);

            const ingestionToggle = screen.getByRole('switch', { name: /ingestion complete emails/i });
            const weeklyToggle = screen.getByRole('switch', { name: /weekly digest/i });

            expect(ingestionToggle).toBeChecked();
            expect(weeklyToggle).not.toBeChecked();
        });
    });

    describe('Accessibility', () => {
        it('should have accessible labels for all switches', () => {
            render(<NotificationSettings />);

            expect(screen.getByRole('switch', { name: /ingestion complete emails/i })).toBeInTheDocument();
            expect(screen.getByRole('switch', { name: /weekly digest/i })).toBeInTheDocument();
            expect(screen.getByRole('switch', { name: /ingestion completed/i })).toBeInTheDocument();
        });

        it('should use correct heading hierarchy', () => {
            render(<NotificationSettings />);

            const heading = screen.getByRole('heading', { name: 'Notifications' });
            expect(heading).toBeInTheDocument();
        });
    });
});
