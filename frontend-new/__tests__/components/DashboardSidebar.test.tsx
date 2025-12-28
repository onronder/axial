/**
 * Unit Tests for DashboardSidebar Component
 * 
 * Tests covering:
 * - Logo and branding
 * - Navigation elements
 * - User menu
 * - Theme toggle
 * - Usage indicator integration
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock all dependencies
vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: vi.fn(),
    }),
    usePathname: () => '/dashboard',
}));

vi.mock('@/hooks/useAuth', () => ({
    useAuth: () => ({
        user: { email: 'test@example.com', plan: 'pro', name: 'Test User' },
        logout: vi.fn(),
    }),
}));

vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => ({
        profile: { first_name: 'Test', last_name: 'User' },
    }),
}));

vi.mock('@/hooks/useTheme', () => ({
    useTheme: () => ({
        theme: 'system',
        setTheme: vi.fn(),
        resolvedTheme: 'dark',
    }),
}));

vi.mock('@/hooks/useChatHistory', () => ({
    useChatHistory: () => ({
        conversations: [],
        isLoading: false,
    }),
    ChatHistoryProvider: ({ children }: { children: React.ReactNode }) => children,
}));

vi.mock('@/components/layout/ChatHistoryList', () => ({
    ChatHistoryList: () => <div data-testid="chat-history-list">Chat History</div>,
}));

vi.mock('@/components/layout/NotificationCenter', () => ({
    NotificationCenter: () => <div data-testid="notification-center">Notifications</div>,
}));

vi.mock('@/components/UsageIndicator', () => ({
    UsageIndicator: () => <div data-testid="usage-indicator">Usage</div>,
}));

vi.mock('@/components/branding/AxioLogo', () => ({
    AxioLogo: () => <div data-testid="axio-logo">Logo</div>,
}));

import { DashboardSidebar } from '@/components/layout/DashboardSidebar';

describe('DashboardSidebar Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Branding', () => {
        it('should render logo', () => {
            render(<DashboardSidebar />);
            expect(screen.getByTestId('axio-logo')).toBeInTheDocument();
        });

        it('should render app name', () => {
            render(<DashboardSidebar />);
            expect(screen.getByText('Axio Hub')).toBeInTheDocument();
        });
    });

    describe('New Chat Button', () => {
        it('should render new chat button', () => {
            render(<DashboardSidebar />);
            expect(screen.getByText('New Chat')).toBeInTheDocument();
        });

        it('should have gradient styling', () => {
            render(<DashboardSidebar />);
            const button = screen.getByText('New Chat').closest('button');
            expect(button?.className).toContain('bg-gradient');
        });
    });

    describe('Chat History', () => {
        it('should render chat history list', () => {
            render(<DashboardSidebar />);
            expect(screen.getByTestId('chat-history-list')).toBeInTheDocument();
        });
    });

    describe('Usage Indicator', () => {
        it('should render usage indicator', () => {
            render(<DashboardSidebar />);
            expect(screen.getByTestId('usage-indicator')).toBeInTheDocument();
        });
    });

    describe('Settings Link', () => {
        it('should render settings link', () => {
            render(<DashboardSidebar />);
            expect(screen.getByText('Settings')).toBeInTheDocument();
        });

        it('should link to settings page', () => {
            render(<DashboardSidebar />);
            const link = screen.getByText('Settings').closest('a');
            expect(link?.getAttribute('href')).toBe('/dashboard/settings');
        });
    });

    describe('Notifications', () => {
        it('should render notification center', () => {
            render(<DashboardSidebar />);
            expect(screen.getByTestId('notification-center')).toBeInTheDocument();
        });
    });

    describe('User Menu', () => {
        it('should render user display name', () => {
            render(<DashboardSidebar />);
            expect(screen.getByText('Test User')).toBeInTheDocument();
        });

        it('should render user plan badge', () => {
            render(<DashboardSidebar />);
            expect(screen.getByText('pro')).toBeInTheDocument();
        });
    });
});
