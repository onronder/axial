/**
 * Unit Tests for BillingSettings Component
 * 
 * Comprehensive tests covering:
 * - Loading state
 * - Current plan display
 * - Plan inheritance badge
 * - Pricing cards rendering
 * - Upgrade button behavior
 * - Feature lists
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BillingSettings } from '@/components/settings/BillingSettings';

// Mock dependencies
const mockProfile = vi.fn();
const mockUseUsage = vi.fn();

vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => mockProfile(),
}));

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => mockUseUsage(),
}));

vi.mock('@/components/branding/AxioLogo', () => ({
    AxioLogo: () => <div data-testid="axio-logo">Logo</div>,
}));

// Mock window.open
const mockWindowOpen = vi.fn();
Object.defineProperty(window, 'open', {
    value: mockWindowOpen,
    writable: true,
});

describe('BillingSettings Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockWindowOpen.mockClear();

        mockProfile.mockReturnValue({
            profile: { plan: 'pro' },
            isLoading: false,
        });

        mockUseUsage.mockReturnValue({
            plan: 'pro',
            isPlanInherited: false,
        });
    });

    describe('Loading State', () => {
        it('should show loading spinner when loading', () => {
            mockProfile.mockReturnValue({
                profile: null,
                isLoading: true,
            });

            render(<BillingSettings />);

            // Look for the Loader2 spinner (animate-spin class)
            const spinner = document.querySelector('.animate-spin');
            expect(spinner).toBeInTheDocument();
        });

        it('should not show content when loading', () => {
            mockProfile.mockReturnValue({
                profile: null,
                isLoading: true,
            });

            render(<BillingSettings />);

            expect(screen.queryByText('Billing & Plans')).not.toBeInTheDocument();
        });
    });

    describe('Page Header', () => {
        it('should render page title', () => {
            render(<BillingSettings />);

            expect(screen.getByText('Billing & Plans')).toBeInTheDocument();
        });

        it('should render page description', () => {
            render(<BillingSettings />);

            expect(screen.getByText('Manage your subscription and upgrade your plan')).toBeInTheDocument();
        });
    });

    describe('Current Plan Card', () => {
        it('should display current plan section', () => {
            render(<BillingSettings />);

            // Current Plan appears in header and on button for current plan
            const currentPlanElements = screen.getAllByText('Current Plan');
            expect(currentPlanElements.length).toBeGreaterThan(0);
        });

        it('should show Pro badge for pro plan', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'pro',
                isPlanInherited: false,
            });

            render(<BillingSettings />);

            // Pro appears in badge and card
            const proElements = screen.getAllByText('Pro');
            expect(proElements.length).toBeGreaterThan(0);
        });

        it('should show Free badge for free plan', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'free' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'free',
                isPlanInherited: false,
            });

            render(<BillingSettings />);

            expect(screen.getByText('Free')).toBeInTheDocument();
        });

        it('should show Enterprise badge for enterprise plan', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'enterprise' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'enterprise',
                isPlanInherited: false,
            });

            render(<BillingSettings />);

            // Enterprise appears in badge and card
            const enterpriseElements = screen.getAllByText('Enterprise');
            expect(enterpriseElements.length).toBeGreaterThan(0);
        });
    });

    describe('Plan Inheritance', () => {
        it('should show Team badge when plan is inherited', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'enterprise',
                isPlanInherited: true,
            });

            render(<BillingSettings />);

            expect(screen.getByText('Team')).toBeInTheDocument();
        });

        it('should show inheritance message when plan is inherited', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'enterprise',
                isPlanInherited: true,
            });

            render(<BillingSettings />);

            expect(screen.getByText("You're using your team owner's plan")).toBeInTheDocument();
        });

        it('should not show Team badge when not inherited', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'pro',
                isPlanInherited: false,
            });

            render(<BillingSettings />);

            expect(screen.queryByText('Team')).not.toBeInTheDocument();
        });
    });

    describe('Pricing Cards', () => {
        it('should render Available Plans section', () => {
            render(<BillingSettings />);

            expect(screen.getByText('Available Plans')).toBeInTheDocument();
        });

        it('should render Starter plan card', () => {
            render(<BillingSettings />);

            expect(screen.getByText('Starter')).toBeInTheDocument();
            expect(screen.getByText('$9')).toBeInTheDocument();
        });

        it('should render Pro plan card', () => {
            render(<BillingSettings />);

            // Pro appears multiple times (badge + card)
            const proElements = screen.getAllByText('Pro');
            expect(proElements.length).toBeGreaterThan(0);
            expect(screen.getByText('$29')).toBeInTheDocument();
        });

        it('should render Enterprise plan card', () => {
            render(<BillingSettings />);

            expect(screen.getByText('$99')).toBeInTheDocument();
        });

        it('should show "Most Popular" badge on Pro plan', () => {
            render(<BillingSettings />);

            expect(screen.getByText('Most Popular')).toBeInTheDocument();
        });

        it('should show "Current Plan" for active plan', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'starter' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'starter',
                isPlanInherited: false,
            });

            render(<BillingSettings />);

            // Current Plan appears in header and button
            const currentPlanElements = screen.getAllByText('Current Plan');
            expect(currentPlanElements.length).toBeGreaterThan(0);
        });
    });

    describe('Feature Lists', () => {
        it('should show Starter features', () => {
            render(<BillingSettings />);

            expect(screen.getByText('50 documents')).toBeInTheDocument();
            expect(screen.getByText('500 MB storage')).toBeInTheDocument();
        });

        it('should show Pro features', () => {
            render(<BillingSettings />);

            expect(screen.getByText('500 documents')).toBeInTheDocument();
            expect(screen.getByText('5 GB storage')).toBeInTheDocument();
            expect(screen.getByText('Web crawling')).toBeInTheDocument();
        });

        it('should show Enterprise features', () => {
            render(<BillingSettings />);

            expect(screen.getByText('Unlimited documents')).toBeInTheDocument();
            expect(screen.getByText('Unlimited storage')).toBeInTheDocument();
            expect(screen.getByText('Team access (20 seats)')).toBeInTheDocument();
        });

        it('should show crossed out features for lower plans', () => {
            render(<BillingSettings />);

            // Team access is crossed out for starter
            const crossedOut = document.querySelectorAll('.line-through');
            expect(crossedOut.length).toBeGreaterThan(0);
        });
    });

    describe('Upgrade Buttons', () => {
        it('should show Upgrade button for non-current plans', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'free' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'free',
                isPlanInherited: false,
            });

            render(<BillingSettings />);

            const upgradeButtons = screen.getAllByText('Upgrade');
            expect(upgradeButtons.length).toBe(3); // All 3 plans
        });

        it('should disable button for current plan', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'pro',
                isPlanInherited: false,
            });

            render(<BillingSettings />);

            // Find the disabled button with "Current Plan" text
            const currentPlanButtons = screen.getAllByText('Current Plan');
            const buttonElement = currentPlanButtons.find(el => el.closest('button'));
            expect(buttonElement?.closest('button')).toBeDisabled();
        });

        it('should open checkout URL on upgrade click', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'free' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'free',
                isPlanInherited: false,
            });

            render(<BillingSettings />);

            const upgradeButtons = screen.getAllByText('Upgrade');
            fireEvent.click(upgradeButtons[0]); // Click first upgrade button (Starter)

            expect(mockWindowOpen).toHaveBeenCalledWith(
                expect.stringContaining('polar.sh'),
                '_blank'
            );
        });
    });

    describe('Payment Methods Section', () => {
        it('should render Payment Methods section', () => {
            render(<BillingSettings />);

            expect(screen.getByText('Payment Methods')).toBeInTheDocument();
        });

        it('should show no payment method message', () => {
            render(<BillingSettings />);

            expect(screen.getByText('No payment method on file')).toBeInTheDocument();
        });

        it('should show Add Payment Method button', () => {
            render(<BillingSettings />);

            expect(screen.getByText('Add Payment Method')).toBeInTheDocument();
        });
    });

    describe('Billing History Section', () => {
        it('should render Billing History section', () => {
            render(<BillingSettings />);

            expect(screen.getByText('Billing History')).toBeInTheDocument();
        });

        it('should show no history message', () => {
            render(<BillingSettings />);

            expect(screen.getByText('No billing history available')).toBeInTheDocument();
        });
    });

    describe('Manage Subscription Button', () => {
        it('should show Manage button for paid plans', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'pro' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'pro',
                isPlanInherited: false,
            });

            render(<BillingSettings />);

            expect(screen.getByText('Manage Subscription')).toBeInTheDocument();
        });

        it('should not show Manage button for free plan', () => {
            mockProfile.mockReturnValue({
                profile: { plan: 'free' },
                isLoading: false,
            });
            mockUseUsage.mockReturnValue({
                plan: 'free',
                isPlanInherited: false,
            });

            render(<BillingSettings />);

            expect(screen.queryByText('Manage Subscription')).not.toBeInTheDocument();
        });
    });
});
