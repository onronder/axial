import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { WebInput } from '@/components/ingest/WebInput';

describe('WebInput', () => {
    it('shows helper text by default', () => {
        render(<WebInput url="" onUrlChange={() => { }} />);

        expect(screen.getByText('Enter the full URL of the web page you want to ingest.')).toBeInTheDocument();
    });

    it('shows validation error for invalid URL', () => {
        render(<WebInput url="invalid" onUrlChange={() => { }} />);

        expect(screen.getByText(/Please enter a valid URL/)).toBeInTheDocument();
    });

    it('shows custom error message when provided', () => {
        render(<WebInput url="https://example.com" onUrlChange={() => { }} error="Custom error" />);

        expect(screen.getByText('Custom error')).toBeInTheDocument();
    });
});
