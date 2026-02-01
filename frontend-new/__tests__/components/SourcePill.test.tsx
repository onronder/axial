import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SourcePill, SourcePillList } from '@/components/chat/SourcePill';
import { SourceMetadata } from '@/components/chat/SourceCard';

// =============================================================================
// Test Data
// =============================================================================

const createMockSource = (overrides: Partial<SourceMetadata> = {}): SourceMetadata => ({
  label: 'Test Document',
  type: 'pdf',
  url: 'https://example.com/doc.pdf',
  ...overrides,
});

// =============================================================================
// SourcePill Component Tests
// =============================================================================

describe('SourcePill', () => {
  describe('Rendering', () => {
    it('should render with label', () => {
      render(<SourcePill source={createMockSource({ label: 'My Document' })} />);
      expect(screen.getByText(/My Document/i)).toBeInTheDocument();
    });

    it('should render with bullet point', () => {
      render(<SourcePill source={createMockSource()} />);
      expect(screen.getByText('•')).toBeInTheDocument();
    });

    it('should render as link when URL is provided', () => {
      render(<SourcePill source={createMockSource({ url: 'https://example.com' })} />);
      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', 'https://example.com');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('should render as span when no URL', () => {
      render(<SourcePill source={createMockSource({ url: undefined })} />);
      expect(screen.queryByRole('link')).not.toBeInTheDocument();
      expect(screen.getByText(/Test Document/)).toBeInTheDocument();
    });

    it('should render external icon when showExternalIcon is true and has URL', () => {
      const { container } = render(
        <SourcePill 
          source={createMockSource({ url: 'https://example.com' })} 
          showExternalIcon={true} 
        />
      );
      // ExternalLink icon should be rendered
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('should not render external icon when no URL', () => {
      const { container } = render(
        <SourcePill 
          source={createMockSource({ url: undefined })} 
          showExternalIcon={true} 
        />
      );
      // ExternalLink icon should not be rendered
      const icon = container.querySelector('svg');
      expect(icon).not.toBeInTheDocument();
    });

    it('should not render external icon when showExternalIcon is false', () => {
      const { container } = render(
        <SourcePill 
          source={createMockSource({ url: 'https://example.com' })} 
          showExternalIcon={false} 
        />
      );
      // ExternalLink icon should not be rendered
      const icon = container.querySelector('svg');
      expect(icon).not.toBeInTheDocument();
    });
  });

  describe('Display Label', () => {
    it('should show label with type when different', () => {
      render(<SourcePill source={createMockSource({ label: 'Report', type: 'pdf' })} />);
      expect(screen.getByText(/Report \(PDF\)/i)).toBeInTheDocument();
    });

    it('should use title as fallback when no label', () => {
      render(<SourcePill source={createMockSource({ label: undefined, title: 'My Title' })} />);
      expect(screen.getByText(/My Title/i)).toBeInTheDocument();
    });

    it('should use source as fallback when no label or title', () => {
      render(<SourcePill source={createMockSource({ label: undefined, title: undefined, source: 'my-source' })} />);
      expect(screen.getByText(/my-source/i)).toBeInTheDocument();
    });

    it('should show "Source" as default label', () => {
      render(<SourcePill source={createMockSource({ label: undefined, title: undefined, source: undefined })} />);
      expect(screen.getByText(/Source/)).toBeInTheDocument();
    });

    it('should handle source_type field', () => {
      render(<SourcePill source={createMockSource({ type: undefined, source_type: 'google_drive' })} />);
      expect(screen.getByText(/Google Drive/i)).toBeInTheDocument();
    });

    it('should handle source_url field', () => {
      render(<SourcePill source={createMockSource({ url: undefined, source_url: 'https://drive.google.com' })} />);
      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', 'https://drive.google.com');
    });
  });

  describe('Highlighted State', () => {
    it('should apply highlighted styles when isHighlighted is true', () => {
      const { container } = render(
        <SourcePill source={createMockSource()} isHighlighted={true} />
      );
      const pill = container.querySelector('a');
      expect(pill).toHaveClass('ring-2');
      expect(pill).toHaveClass('scale-[1.02]');
    });

    it('should not apply highlighted styles when isHighlighted is false', () => {
      const { container } = render(
        <SourcePill source={createMockSource()} isHighlighted={false} />
      );
      const pill = container.querySelector('a');
      expect(pill).not.toHaveClass('scale-[1.02]');
    });
  });

  describe('Citation Badges', () => {
    it('should render citation badges when citationIndices provided', () => {
      render(<SourcePill source={createMockSource()} citationIndices={[1, 2, 3]} />);
      
      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });

    it('should not render citation badges when citationIndices is empty', () => {
      render(<SourcePill source={createMockSource()} citationIndices={[]} />);
      
      // No citation numbers should be present
      expect(screen.queryByText('1')).not.toBeInTheDocument();
    });

    it('should not render citation badges when citationIndices is undefined', () => {
      render(<SourcePill source={createMockSource()} citationIndices={undefined} />);
      
      // Check for aria-label that would only exist with badges
      expect(screen.queryByLabelText(/Citations:/)).not.toBeInTheDocument();
    });

    it('should have proper aria-label for citation badges', () => {
      render(<SourcePill source={createMockSource()} citationIndices={[6, 10]} />);
      
      expect(screen.getByLabelText('Citations: 6, 10')).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper title attribute for links', () => {
      render(<SourcePill source={createMockSource({ label: 'My Doc' })} />);
      
      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('title', 'View: My Doc');
    });

    it('should have proper title attribute for spans', () => {
      render(<SourcePill source={createMockSource({ label: 'My Doc', url: undefined })} />);
      
      // For span, title is just the label
      expect(screen.getByTitle('My Doc')).toBeInTheDocument();
    });

    it('should hide bullet point from screen readers', () => {
      render(<SourcePill source={createMockSource()} />);
      
      const bullet = screen.getByText('•');
      expect(bullet).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('Event Handlers', () => {
    it('should pass through onClick handler', () => {
      const onClick = vi.fn();
      render(<SourcePill source={createMockSource()} onClick={onClick} />);
      
      fireEvent.click(screen.getByRole('link'));
      expect(onClick).toHaveBeenCalled();
    });

    it('should pass through onMouseEnter handler', () => {
      const onMouseEnter = vi.fn();
      render(<SourcePill source={createMockSource()} onMouseEnter={onMouseEnter} />);
      
      fireEvent.mouseEnter(screen.getByRole('link'));
      expect(onMouseEnter).toHaveBeenCalled();
    });

    it('should pass through onMouseLeave handler', () => {
      const onMouseLeave = vi.fn();
      render(<SourcePill source={createMockSource()} onMouseLeave={onMouseLeave} />);
      
      fireEvent.mouseLeave(screen.getByRole('link'));
      expect(onMouseLeave).toHaveBeenCalled();
    });
  });

  describe('Custom className', () => {
    it('should merge custom className', () => {
      const { container } = render(
        <SourcePill source={createMockSource()} className="custom-class" />
      );
      
      const pill = container.querySelector('a');
      expect(pill).toHaveClass('custom-class');
      // Should still have base classes
      expect(pill).toHaveClass('inline-flex');
    });
  });
});

// =============================================================================
// SourcePillList Component Tests
// =============================================================================

describe('SourcePillList', () => {
  describe('Rendering', () => {
    it('should return null when sources is empty', () => {
      const { container } = render(<SourcePillList sources={[]} />);
      expect(container.firstChild).toBeNull();
    });

    it('should return null when sources is undefined', () => {
      const { container } = render(<SourcePillList sources={undefined as unknown as SourceMetadata[]} />);
      expect(container.firstChild).toBeNull();
    });

    it('should render sources as pills', () => {
      const sources = [
        createMockSource({ label: 'Doc 1' }),
        createMockSource({ label: 'Doc 2' }),
      ];
      
      render(<SourcePillList sources={sources} />);
      
      expect(screen.getByText(/Doc 1/)).toBeInTheDocument();
      expect(screen.getByText(/Doc 2/)).toBeInTheDocument();
    });

    it('should have proper aria-label', () => {
      const sources = [createMockSource({ label: 'Test' })];
      
      render(<SourcePillList sources={sources} />);
      
      expect(screen.getByRole('navigation', { name: 'Source citations' })).toBeInTheDocument();
    });
  });

  describe('Deduplication', () => {
    it('should deduplicate sources with same label', () => {
      const sources = [
        createMockSource({ label: 'Same Doc', index: 1 }),
        createMockSource({ label: 'Same Doc', index: 2 }),
        createMockSource({ label: 'Different Doc', index: 3 }),
      ];
      
      render(<SourcePillList sources={sources} />);
      
      // Should only show 2 pills (deduplicated)
      const pills = screen.getAllByText(/Doc/);
      expect(pills.length).toBe(2);
    });

    it('should show multiple citation indices for deduplicated sources', () => {
      const sources = [
        createMockSource({ label: 'Repeated Doc', index: 1 }),
        createMockSource({ label: 'Repeated Doc', index: 5 }),
      ];
      
      render(<SourcePillList sources={sources} />);
      
      // Both citation numbers should be shown
      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('should deduplicate case-insensitively', () => {
      const sources = [
        createMockSource({ label: 'Document' }),
        createMockSource({ label: 'document' }),
        createMockSource({ label: 'DOCUMENT' }),
      ];
      
      render(<SourcePillList sources={sources} />);
      
      // Should only show 1 pill (all same label case-insensitively)
      // Query for links only (pills are rendered as links when they have URLs)
      const links = screen.getAllByRole('link');
      expect(links.length).toBe(1);
    });
  });

  describe('Overflow', () => {
    it('should limit visible sources to 5', () => {
      const sources = Array.from({ length: 8 }, (_, i) => 
        createMockSource({ label: `Doc ${i + 1}` })
      );
      
      render(<SourcePillList sources={sources} />);
      
      // Should show first 5
      expect(screen.getByText(/Doc 1/)).toBeInTheDocument();
      expect(screen.getByText(/Doc 5/)).toBeInTheDocument();
      
      // Should not show 6th
      expect(screen.queryByText(/Doc 6/)).not.toBeInTheDocument();
    });

    it('should show overflow indicator', () => {
      const sources = Array.from({ length: 8 }, (_, i) => 
        createMockSource({ label: `Doc ${i + 1}` })
      );
      
      render(<SourcePillList sources={sources} />);
      
      expect(screen.getByText('+3 more')).toBeInTheDocument();
    });

    it('should not show overflow indicator when exactly 5 sources', () => {
      const sources = Array.from({ length: 5 }, (_, i) => 
        createMockSource({ label: `Doc ${i + 1}` })
      );
      
      render(<SourcePillList sources={sources} />);
      
      expect(screen.queryByText(/more/)).not.toBeInTheDocument();
    });

    it('should have title on overflow indicator', () => {
      const sources = Array.from({ length: 7 }, (_, i) => 
        createMockSource({ label: `Doc ${i + 1}` })
      );
      
      render(<SourcePillList sources={sources} />);
      
      expect(screen.getByTitle('2 more sources not shown')).toBeInTheDocument();
    });
  });

  describe('Highlighting', () => {
    it('should highlight pill when its index matches highlightedIndex', () => {
      const sources = [
        createMockSource({ label: 'Doc 1', index: 1 }),
        createMockSource({ label: 'Doc 2', index: 2 }),
      ];
      
      const { container } = render(
        <SourcePillList sources={sources} highlightedIndex={1} />
      );
      
      // First pill should be highlighted
      const links = container.querySelectorAll('a');
      expect(links[0]).toHaveClass('ring-2');
      expect(links[1]).not.toHaveClass('ring-2');
    });

    it('should highlight deduplicated pill when any of its indices matches', () => {
      const sources = [
        createMockSource({ label: 'Same Doc', index: 1 }),
        createMockSource({ label: 'Same Doc', index: 5 }),
      ];
      
      const { container } = render(
        <SourcePillList sources={sources} highlightedIndex={5} />
      );
      
      // The deduplicated pill should be highlighted
      const link = container.querySelector('a');
      expect(link).toHaveClass('ring-2');
    });
  });

  describe('Hover Events', () => {
    it('should call onSourceHover with index on mouse enter', () => {
      const onSourceHover = vi.fn();
      const sources = [createMockSource({ label: 'Doc 1', index: 3 })];
      
      render(<SourcePillList sources={sources} onSourceHover={onSourceHover} />);
      
      fireEvent.mouseEnter(screen.getByRole('link'));
      expect(onSourceHover).toHaveBeenCalledWith(3);
    });

    it('should call onSourceHover with null on mouse leave', () => {
      const onSourceHover = vi.fn();
      const sources = [createMockSource({ label: 'Doc 1' })];
      
      render(<SourcePillList sources={sources} onSourceHover={onSourceHover} />);
      
      fireEvent.mouseLeave(screen.getByRole('link'));
      expect(onSourceHover).toHaveBeenCalledWith(null);
    });

    it('should call onSourceHover with index on focus', () => {
      const onSourceHover = vi.fn();
      const sources = [createMockSource({ label: 'Doc 1', index: 7 })];
      
      render(<SourcePillList sources={sources} onSourceHover={onSourceHover} />);
      
      fireEvent.focus(screen.getByRole('link'));
      expect(onSourceHover).toHaveBeenCalledWith(7);
    });

    it('should call onSourceHover with null on blur', () => {
      const onSourceHover = vi.fn();
      const sources = [createMockSource({ label: 'Doc 1' })];
      
      render(<SourcePillList sources={sources} onSourceHover={onSourceHover} />);
      
      fireEvent.blur(screen.getByRole('link'));
      expect(onSourceHover).toHaveBeenCalledWith(null);
    });
  });

  describe('Custom className', () => {
    it('should merge custom className on container', () => {
      const sources = [createMockSource({ label: 'Test' })];
      
      render(<SourcePillList sources={sources} className="custom-list-class" />);
      
      const nav = screen.getByRole('navigation');
      expect(nav).toHaveClass('custom-list-class');
      expect(nav).toHaveClass('flex'); // Should still have base classes
    });
  });

  describe('Index Fallback', () => {
    it('should use 1-based index when source.index is undefined', () => {
      const sources = [
        createMockSource({ label: 'Doc 1', index: undefined }),
        createMockSource({ label: 'Doc 2', index: undefined }),
      ];
      
      render(<SourcePillList sources={sources} />);
      
      // First source should have index 1, second should have index 2
      expect(screen.getByText('1')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });
});
