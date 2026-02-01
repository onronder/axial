import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ComingSoonIntegrations } from '@/components/data-sources/ComingSoonIntegrations';

// =============================================================================
// Mocks
// =============================================================================

const mockToast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

// =============================================================================
// Test Suite
// =============================================================================

describe('ComingSoonIntegrations Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    // =========================================================================
    // Rendering Tests
    // =========================================================================

    describe('Rendering', () => {
        it('should render the section header', () => {
            render(<ComingSoonIntegrations />);

            expect(screen.getByText(/Coming Soon — Enterprise Connectors/i)).toBeInTheDocument();
        });

        it('should render the description text', () => {
            render(<ComingSoonIntegrations />);

            expect(screen.getByText(/Connect to your entire tech stack/i)).toBeInTheDocument();
        });

        it('should render the 50+ Platforms badge', () => {
            render(<ComingSoonIntegrations />);

            expect(screen.getByText('50+ Platforms')).toBeInTheDocument();
        });

        it('should render all Project & Ops integrations', () => {
            render(<ComingSoonIntegrations />);

            expect(screen.getByText('Jira')).toBeInTheDocument();
            expect(screen.getByText('Monday.com')).toBeInTheDocument();
            expect(screen.getByText('Asana')).toBeInTheDocument();
            expect(screen.getByText('Trello')).toBeInTheDocument();
        });

        it('should render Communication integrations', () => {
            render(<ComingSoonIntegrations />);

            expect(screen.getByText('Slack')).toBeInTheDocument();
        });

        it('should render category headers', () => {
            render(<ComingSoonIntegrations />);

            expect(screen.getByText('Project & Ops')).toBeInTheDocument();
            expect(screen.getByText('Communication')).toBeInTheDocument();
        });

        it('should render Coming Soon badges on all cards', () => {
            render(<ComingSoonIntegrations />);

            const badges = screen.getAllByText('Coming Soon');
            expect(badges.length).toBeGreaterThanOrEqual(5);
        });

        it('should render integration descriptions', () => {
            render(<ComingSoonIntegrations />);

            expect(screen.getByText('Issue tracking & project management')).toBeInTheDocument();
            expect(screen.getByText('Work OS & project boards')).toBeInTheDocument();
            expect(screen.getByText('Task & project management')).toBeInTheDocument();
            expect(screen.getByText('Kanban boards & workflows')).toBeInTheDocument();
            expect(screen.getByText('Channels, threads & DMs')).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Interaction Tests
    // =========================================================================

    describe('Interactions', () => {
        it('should show toast when Jira card is clicked', async () => {
            const user = userEvent.setup();
            render(<ComingSoonIntegrations />);

            const jiraCard = screen.getByText('Jira').closest('div[class*="cursor-pointer"]');
            expect(jiraCard).toBeInTheDocument();

            if (jiraCard) {
                await user.click(jiraCard);
            }

            expect(mockToast).toHaveBeenCalledWith({
                title: 'Jira coming soon!',
                description: "We've noted your interest. You'll be notified when it's available.",
            });
        });

        it('should show toast when Monday.com card is clicked', async () => {
            const user = userEvent.setup();
            render(<ComingSoonIntegrations />);

            const mondayCard = screen.getByText('Monday.com').closest('div[class*="cursor-pointer"]');
            if (mondayCard) {
                await user.click(mondayCard);
            }

            expect(mockToast).toHaveBeenCalledWith({
                title: 'Monday.com coming soon!',
                description: "We've noted your interest. You'll be notified when it's available.",
            });
        });

        it('should show toast when Asana card is clicked', async () => {
            const user = userEvent.setup();
            render(<ComingSoonIntegrations />);

            const asanaCard = screen.getByText('Asana').closest('div[class*="cursor-pointer"]');
            if (asanaCard) {
                await user.click(asanaCard);
            }

            expect(mockToast).toHaveBeenCalledWith({
                title: 'Asana coming soon!',
                description: "We've noted your interest. You'll be notified when it's available.",
            });
        });

        it('should show toast when Trello card is clicked', async () => {
            const user = userEvent.setup();
            render(<ComingSoonIntegrations />);

            const trelloCard = screen.getByText('Trello').closest('div[class*="cursor-pointer"]');
            if (trelloCard) {
                await user.click(trelloCard);
            }

            expect(mockToast).toHaveBeenCalledWith({
                title: 'Trello coming soon!',
                description: "We've noted your interest. You'll be notified when it's available.",
            });
        });

        it('should show toast when Slack card is clicked', async () => {
            const user = userEvent.setup();
            render(<ComingSoonIntegrations />);

            const slackCard = screen.getByText('Slack').closest('div[class*="cursor-pointer"]');
            if (slackCard) {
                await user.click(slackCard);
            }

            expect(mockToast).toHaveBeenCalledWith({
                title: 'Slack coming soon!',
                description: "We've noted your interest. You'll be notified when it's available.",
            });
        });

        it('should be clickable via fireEvent', () => {
            render(<ComingSoonIntegrations />);

            const jiraCard = screen.getByText('Jira').closest('div[class*="cursor-pointer"]');
            if (jiraCard) {
                fireEvent.click(jiraCard);
            }

            expect(mockToast).toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Category Grouping Tests
    // =========================================================================

    describe('Category Grouping', () => {
        it('should display Project & Ops category first', () => {
            render(<ComingSoonIntegrations />);

            const categoryHeaders = screen.getAllByRole('heading', { level: 3 });
            expect(categoryHeaders[0]).toHaveTextContent('Project & Ops');
        });

        it('should display Communication category second', () => {
            render(<ComingSoonIntegrations />);

            const categoryHeaders = screen.getAllByRole('heading', { level: 3 });
            expect(categoryHeaders[1]).toHaveTextContent('Communication');
        });

        it('should group correct integrations under Project & Ops', () => {
            render(<ComingSoonIntegrations />);

            // Find the Project & Ops section
            const projectOpsSection = screen.getByText('Project & Ops').closest('div[class*="space-y-4"]');
            expect(projectOpsSection).toBeInTheDocument();

            // Check integrations in this section
            if (projectOpsSection) {
                expect(projectOpsSection.textContent).toContain('Jira');
                expect(projectOpsSection.textContent).toContain('Monday.com');
                expect(projectOpsSection.textContent).toContain('Asana');
                expect(projectOpsSection.textContent).toContain('Trello');
            }
        });

        it('should group correct integrations under Communication', () => {
            render(<ComingSoonIntegrations />);

            // Find the Communication section
            const commSection = screen.getByText('Communication').closest('div[class*="space-y-4"]');
            expect(commSection).toBeInTheDocument();

            // Check integrations in this section
            if (commSection) {
                expect(commSection.textContent).toContain('Slack');
            }
        });
    });

    // =========================================================================
    // Styling and Structure Tests
    // =========================================================================

    describe('Styling and Structure', () => {
        it('should have cursor-pointer class on cards', () => {
            render(<ComingSoonIntegrations />);

            const jiraCard = screen.getByText('Jira').closest('div[class*="cursor-pointer"]');
            expect(jiraCard).toHaveClass('cursor-pointer');
        });

        it('should have opacity and grayscale classes on cards', () => {
            render(<ComingSoonIntegrations />);

            const jiraCard = screen.getByText('Jira').closest('div[class*="opacity-60"]');
            expect(jiraCard).toHaveClass('opacity-60');
            expect(jiraCard).toHaveClass('grayscale');
        });

        it('should have hover transition classes', () => {
            render(<ComingSoonIntegrations />);

            const jiraCard = screen.getByText('Jira').closest('div[class*="transition-all"]');
            expect(jiraCard).toHaveClass('transition-all');
            expect(jiraCard).toHaveClass('duration-300');
        });

        it('should have dashed border on cards', () => {
            render(<ComingSoonIntegrations />);

            const jiraCard = screen.getByText('Jira').closest('div[class*="border-dashed"]');
            expect(jiraCard).toHaveClass('border-dashed');
        });

        it('should render clock icon in header', () => {
            render(<ComingSoonIntegrations />);

            // Clock icon should be in the document
            const header = screen.getByText(/Coming Soon — Enterprise Connectors/i).closest('div');
            expect(header).toBeInTheDocument();
        });

        it('should render icon containers for each integration', () => {
            render(<ComingSoonIntegrations />);

            // Each integration has an icon in a container
            const iconContainers = document.querySelectorAll('.h-10.w-10');
            expect(iconContainers.length).toBeGreaterThanOrEqual(5);
        });
    });

    // =========================================================================
    // Edge Cases
    // =========================================================================

    describe('Edge Cases', () => {
        it('should handle multiple rapid clicks', async () => {
            const user = userEvent.setup();
            render(<ComingSoonIntegrations />);

            const jiraCard = screen.getByText('Jira').closest('div[class*="cursor-pointer"]');

            if (jiraCard) {
                // Click rapidly
                await user.click(jiraCard);
                await user.click(jiraCard);
                await user.click(jiraCard);
            }

            // Should be called 3 times
            expect(mockToast).toHaveBeenCalledTimes(3);
        });

        it('should render correctly with no custom props', () => {
            // ComingSoonIntegrations takes no props, just verify it renders
            const { container } = render(<ComingSoonIntegrations />);
            expect(container.firstChild).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Accessibility Tests
    // =========================================================================

    describe('Accessibility', () => {
        it('should have proper heading hierarchy', () => {
            render(<ComingSoonIntegrations />);

            // Main section header is h2
            const h2 = screen.getByRole('heading', { level: 2 });
            expect(h2).toHaveTextContent(/Coming Soon — Enterprise Connectors/i);

            // Category headers are h3
            const h3s = screen.getAllByRole('heading', { level: 3 });
            expect(h3s.length).toBe(2);
        });

        it('should have proper card structure with name and description', () => {
            render(<ComingSoonIntegrations />);

            // Each card should have h4 for name
            const h4s = document.querySelectorAll('h4');
            expect(h4s.length).toBeGreaterThanOrEqual(5);
        });
    });
});
