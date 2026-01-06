/**
 * Accessibility Utilities
 * 
 * Provides utilities for screen reader announcements and keyboard navigation.
 */

/**
 * Announce a message to screen readers
 * 
 * Creates a live region that screen readers will announce,
 * then removes it after a short delay.
 */
export function announceToScreenReader(message: string, priority: 'polite' | 'assertive' = 'polite') {
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', priority);
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;

    document.body.appendChild(announcement);

    // Remove after announcement
    setTimeout(() => {
        document.body.removeChild(announcement);
    }, 1000);
}

/**
 * Keyboard shortcuts manager
 */
export class KeyboardShortcuts {
    private shortcuts: Map<string, () => void> = new Map();

    constructor() {
        this.handleKeyPress = this.handleKeyPress.bind(this);
    }

    /**
     * Register a keyboard shortcut
     * 
     * @param key - Key combination (e.g., 'Escape', 'Ctrl+E', 'Shift+?')
     * @param handler - Function to call when shortcut is pressed
     */
    register(key: string, handler: () => void) {
        this.shortcuts.set(key.toLowerCase(), handler);
    }

    /**
     * Unregister a keyboard shortcut
     */
    unregister(key: string) {
        this.shortcuts.delete(key.toLowerCase());
    }

    /**
     * Start listening for keyboard events
     */
    start() {
        window.addEventListener('keydown', this.handleKeyPress);
    }

    /**
     * Stop listening for keyboard events
     */
    stop() {
        window.removeEventListener('keydown', this.handleKeyPress);
    }

    private handleKeyPress(event: KeyboardEvent) {
        const key = this.getKeyString(event);
        const handler = this.shortcuts.get(key);

        if (handler) {
            event.preventDefault();
            handler();
        }
    }

    private getKeyString(event: KeyboardEvent): string {
        const parts: string[] = [];

        if (event.ctrlKey) parts.push('ctrl');
        if (event.altKey) parts.push('alt');
        if (event.shiftKey) parts.push('shift');
        if (event.metaKey) parts.push('meta');

        parts.push(event.key.toLowerCase());

        return parts.join('+');
    }
}

/**
 * Focus trap for modals
 * 
 * Keeps focus within a container element
 */
export class FocusTrap {
    private container: HTMLElement;
    private previousFocus: HTMLElement | null = null;

    constructor(container: HTMLElement) {
        this.container = container;
    }

    /**
     * Activate the focus trap
     */
    activate() {
        // Save current focus
        this.previousFocus = document.activeElement as HTMLElement;

        // Focus first focusable element
        const firstFocusable = this.getFocusableElements()[0];
        if (firstFocusable) {
            firstFocusable.focus();
        }

        // Add event listener
        this.container.addEventListener('keydown', this.handleKeyDown);
    }

    /**
     * Deactivate the focus trap
     */
    deactivate() {
        this.container.removeEventListener('keydown', this.handleKeyDown);

        // Restore previous focus
        if (this.previousFocus) {
            this.previousFocus.focus();
        }
    }

    private handleKeyDown = (event: KeyboardEvent) => {
        if (event.key !== 'Tab') return;

        const focusableElements = this.getFocusableElements();
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey) {
            // Shift + Tab
            if (document.activeElement === firstElement) {
                event.preventDefault();
                lastElement?.focus();
            }
        } else {
            // Tab
            if (document.activeElement === lastElement) {
                event.preventDefault();
                firstElement?.focus();
            }
        }
    };

    private getFocusableElements(): HTMLElement[] {
        const selector = [
            'a[href]',
            'button:not([disabled])',
            'textarea:not([disabled])',
            'input:not([disabled])',
            'select:not([disabled])',
            '[tabindex]:not([tabindex="-1"])',
        ].join(', ');

        return Array.from(this.container.querySelectorAll(selector));
    }
}

/**
 * Get ARIA label for progress percentage
 */
export function getProgressLabel(percentage: number, context: string): string {
    if (percentage === 0) {
        return `${context} not started`;
    } else if (percentage === 100) {
        return `${context} complete`;
    } else {
        return `${context} ${percentage} percent complete`;
    }
}

/**
 * Get ARIA label for file status
 */
export function getFileStatusLabel(status: string, filename: string): string {
    const statusLabels: Record<string, string> = {
        pending: 'queued',
        uploading: 'downloading',
        processing: 'processing',
        embedding: 'generating embeddings',
        indexing: 'indexing',
        completed: 'completed successfully',
        failed: 'failed',
        cancelled: 'cancelled',
    };

    const label = statusLabels[status] || status;
    return `${filename} ${label}`;
}
