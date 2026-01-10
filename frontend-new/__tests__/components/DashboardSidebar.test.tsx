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
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const mockPush = vi.fn();
const mockLogout = vi.fn();
const mockSetTheme = vi.fn();
const mockUsePathname = vi.fn();
const mockUseUsage = vi.fn();
const mockUseProfile = vi.fn();
const mockUseAuth = vi.fn();
const mockUseTheme = vi.fn();

// Mock all dependencies
vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: mockPush,
    }),
    usePathname: () => mockUsePathname(),
}));

vi.mock('next/link', () => ({
    __esModule: true,
    default: ({ href, onClick, children, ...props }: any) => (
        <a
            href={href}
            onClick={(event) => {
                event.preventDefault();
                onClick?.(event);
            }}
            {...props}
        >
            {children}
        </a>
    ),
}));

vi.mock('@/hooks/useAuth', () => ({
    useAuth: () => mockUseAuth(),
}));

vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => mockUseProfile(),
}));

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => mockUseUsage(),
}));

vi.mock('@/hooks/useTheme', () => ({
    useTheme: () => mockUseTheme(),
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
        mockUsePathname.mockReturnValue('/dashboard');
        mockUseAuth.mockReturnValue({
            user: { email: 'test@example.com', plan: 'pro', name: 'Test User' },
            logout: mockLogout,
        });
        mockUseProfile.mockReturnValue({
            profile: { first_name: 'Test', last_name: 'User' },
        });
        mockUseUsage.mockReturnValue({
            plan: 'pro',
            isLoading: false,
        });
        mockUseTheme.mockReturnValue({
            theme: 'system',
            setTheme: mockSetTheme,
            resolvedTheme: 'dark',
        });
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

        it('should navigate to new chat on click', async () => {
            const user = userEvent.setup();
            render(<DashboardSidebar />);

            await user.click(screen.getByText('New Chat'));

            expect(mockPush).toHaveBeenCalledWith('/dashboard/chat/new');
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

        it('should mark settings as active when on settings page', () => {
            mockUsePathname.mockReturnValue('/dashboard/settings/general');

            render(<DashboardSidebar />);

            const link = screen.getByText('Settings').closest('a');
            expect(link?.className).toContain('bg-sidebar-accent');
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

        it('should fall back to first name when last name is missing', () => {
            mockUseProfile.mockReturnValue({
                profile: { first_name: 'Solo', last_name: '' },
            });

            render(<DashboardSidebar />);

            expect(screen.getByText('Solo')).toBeInTheDocument();
        });

        it('should fall back to email prefix when profile is missing', () => {
            mockUseProfile.mockReturnValue({ profile: null });
            mockUseAuth.mockReturnValue({
                user: { email: 'fallback@example.com', name: null },
                logout: mockLogout,
            });

            render(<DashboardSidebar />);

            expect(screen.getByText('fallback')).toBeInTheDocument();
        });

        it('should fall back to default User label when no profile or user data', () => {
            mockUseProfile.mockReturnValue({ profile: null });
            mockUseAuth.mockReturnValue({
                user: null,
                logout: mockLogout,
            });

            render(<DashboardSidebar />);

            expect(screen.getByText('User')).toBeInTheDocument();
        });

        it('should render user plan badge', () => {
            render(<DashboardSidebar />);
            expect(screen.getByText('Pro')).toBeInTheDocument();
        });

        it('should not open the user menu when clicking the plan badge', async () => {
            const user = userEvent.setup();
            render(<DashboardSidebar />);

            const badgeLink = screen.getByText('Pro').closest('a');
            expect(badgeLink).toBeInTheDocument();

            if (badgeLink) {
                await user.click(badgeLink);
            }

            expect(mockPush).not.toHaveBeenCalled();
        });

        it('should show loading placeholder for missing plan', () => {
            mockUseUsage.mockReturnValue({
                plan: null,
                isLoading: false,
            });

            render(<DashboardSidebar />);

            expect(screen.getByText('···')).toBeInTheDocument();
        });

        it('should toggle theme from dropdown menu', async () => {
            const user = userEvent.setup();
            render(<DashboardSidebar />);

            const triggerButton = screen.getByText('Test User').closest('button');
            expect(triggerButton).toBeInTheDocument();

            if (triggerButton) {
                await user.click(triggerButton);
            }

            await user.click(screen.getByText('Light Mode'));

            expect(mockSetTheme).toHaveBeenCalledWith('light');
        });

        it('should toggle theme to dark when current theme is light', async () => {
            mockUseTheme.mockReturnValue({
                theme: 'system',
                setTheme: mockSetTheme,
                resolvedTheme: 'light',
            });

            const user = userEvent.setup();
            render(<DashboardSidebar />);

            const triggerButton = screen.getByText('Test User').closest('button');
            if (triggerButton) {
                await user.click(triggerButton);
            }

            await user.click(screen.getByText('Dark Mode'));

            expect(mockSetTheme).toHaveBeenCalledWith('dark');
        });

        it('should navigate to profile settings from the dropdown menu', async () => {
            const user = userEvent.setup();
            render(<DashboardSidebar />);

            const triggerButton = screen.getByText('Test User').closest('button');
            if (triggerButton) {
                await user.click(triggerButton);
            }

            await user.click(screen.getByText('Profile'));

            expect(mockPush).toHaveBeenCalledWith('/dashboard/settings/general');
        });

        it('should call logout from dropdown menu', async () => {
            const user = userEvent.setup();
            render(<DashboardSidebar />);

            const triggerButton = screen.getByText('Test User').closest('button');
            if (triggerButton) {
                await user.click(triggerButton);
            }

            await user.click(screen.getByText('Logout'));
            expect(mockLogout).toHaveBeenCalled();
        });
    });
});
