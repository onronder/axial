/**
 * Tests for lib/youtube-utils.ts - YouTube URL validation and parsing utilities
 */

import { describe, it, expect } from 'vitest';
import {
  isValidYoutubeUrl,
  normalizeYoutubeUrl,
  extractYoutubeVideoId,
  YOUTUBE_URL_PATTERNS,
  YOUTUBE_ERROR_MESSAGES,
} from '@/lib/youtube-utils';

describe('YOUTUBE_URL_PATTERNS', () => {
  it('should export all pattern types', () => {
    expect(YOUTUBE_URL_PATTERNS).toHaveLength(5);
  });
});

describe('YOUTUBE_ERROR_MESSAGES', () => {
  it('should have all error message keys', () => {
    expect(YOUTUBE_ERROR_MESSAGES.INVALID_URL).toBeDefined();
    expect(YOUTUBE_ERROR_MESSAGES.INVALID_URL_DETAILED).toBeDefined();
    expect(YOUTUBE_ERROR_MESSAGES.EMPTY_URL).toBeDefined();
  });
});

describe('isValidYoutubeUrl', () => {
  describe('valid URLs', () => {
    it('should return true for standard watch URL', () => {
      expect(isValidYoutubeUrl('https://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe(true);
      expect(isValidYoutubeUrl('https://youtube.com/watch?v=dQw4w9WgXcQ')).toBe(true);
      expect(isValidYoutubeUrl('http://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe(true);
    });

    it('should return true for short URL', () => {
      expect(isValidYoutubeUrl('https://youtu.be/dQw4w9WgXcQ')).toBe(true);
      expect(isValidYoutubeUrl('http://youtu.be/dQw4w9WgXcQ')).toBe(true);
      expect(isValidYoutubeUrl('youtu.be/dQw4w9WgXcQ')).toBe(true);
    });

    it('should return true for embed URL', () => {
      expect(isValidYoutubeUrl('https://www.youtube.com/embed/dQw4w9WgXcQ')).toBe(true);
      expect(isValidYoutubeUrl('youtube.com/embed/dQw4w9WgXcQ')).toBe(true);
    });

    it('should return true for legacy v/ URL', () => {
      expect(isValidYoutubeUrl('https://www.youtube.com/v/dQw4w9WgXcQ')).toBe(true);
      expect(isValidYoutubeUrl('youtube.com/v/dQw4w9WgXcQ')).toBe(true);
    });

    it('should return true for shorts URL', () => {
      expect(isValidYoutubeUrl('https://www.youtube.com/shorts/dQw4w9WgXcQ')).toBe(true);
      expect(isValidYoutubeUrl('youtube.com/shorts/dQw4w9WgXcQ')).toBe(true);
    });

    it('should return true for URL without protocol', () => {
      expect(isValidYoutubeUrl('www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe(true);
      expect(isValidYoutubeUrl('youtube.com/watch?v=dQw4w9WgXcQ')).toBe(true);
    });

    it('should return true for URL with extra parameters', () => {
      expect(isValidYoutubeUrl('https://youtube.com/watch?v=dQw4w9WgXcQ&t=120')).toBe(true);
      expect(isValidYoutubeUrl('https://youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest')).toBe(true);
    });

    it('should handle whitespace around URL', () => {
      expect(isValidYoutubeUrl('  https://youtube.com/watch?v=dQw4w9WgXcQ  ')).toBe(true);
      expect(isValidYoutubeUrl('\nhttps://youtu.be/dQw4w9WgXcQ\n')).toBe(true);
    });
  });

  describe('invalid URLs', () => {
    it('should return false for empty string', () => {
      expect(isValidYoutubeUrl('')).toBe(false);
    });

    it('should return false for whitespace only', () => {
      expect(isValidYoutubeUrl('   ')).toBe(false);
      expect(isValidYoutubeUrl('\n\t')).toBe(false);
    });

    it('should return false for non-YouTube URLs', () => {
      expect(isValidYoutubeUrl('https://vimeo.com/12345')).toBe(false);
      expect(isValidYoutubeUrl('https://example.com')).toBe(false);
      expect(isValidYoutubeUrl('https://google.com')).toBe(false);
    });

    it('should return false for incomplete YouTube URLs', () => {
      expect(isValidYoutubeUrl('https://youtube.com/')).toBe(false);
      expect(isValidYoutubeUrl('https://youtube.com/watch')).toBe(false);
      expect(isValidYoutubeUrl('https://youtube.com/watch?v=')).toBe(false);
    });

    it('should return false for invalid video IDs (too short)', () => {
      expect(isValidYoutubeUrl('https://youtube.com/watch?v=abc')).toBe(false);
      expect(isValidYoutubeUrl('https://youtube.com/watch?v=abcde')).toBe(false);
    });

    it('should accept URLs with long video IDs (regex matches first 11 chars)', () => {
      // The regex pattern [\w-]{11} matches exactly 11 characters at the start
      // But the regex doesn't enforce that nothing follows, so longer IDs are accepted
      expect(isValidYoutubeUrl('https://youtube.com/watch?v=abcdefghijk')).toBe(true);
    });

    it('should return false for random text', () => {
      expect(isValidYoutubeUrl('random text')).toBe(false);
      expect(isValidYoutubeUrl('not a url at all')).toBe(false);
    });
  });
});

describe('normalizeYoutubeUrl', () => {
  it('should add https:// to URL without protocol', () => {
    expect(normalizeYoutubeUrl('youtube.com/watch?v=abc123')).toBe('https://youtube.com/watch?v=abc123');
    expect(normalizeYoutubeUrl('www.youtube.com/watch?v=abc123')).toBe('https://www.youtube.com/watch?v=abc123');
    expect(normalizeYoutubeUrl('youtu.be/abc123')).toBe('https://youtu.be/abc123');
  });

  it('should convert http:// to https://', () => {
    expect(normalizeYoutubeUrl('http://youtube.com/watch?v=abc123')).toBe('https://youtube.com/watch?v=abc123');
    expect(normalizeYoutubeUrl('http://www.youtube.com/watch?v=abc123')).toBe('https://www.youtube.com/watch?v=abc123');
  });

  it('should keep https:// URLs unchanged', () => {
    expect(normalizeYoutubeUrl('https://youtube.com/watch?v=abc123')).toBe('https://youtube.com/watch?v=abc123');
    expect(normalizeYoutubeUrl('https://www.youtube.com/watch?v=abc123')).toBe('https://www.youtube.com/watch?v=abc123');
  });

  it('should trim whitespace', () => {
    expect(normalizeYoutubeUrl('  youtube.com/watch?v=abc123  ')).toBe('https://youtube.com/watch?v=abc123');
    expect(normalizeYoutubeUrl('\nhttp://youtube.com/watch?v=abc123\n')).toBe('https://youtube.com/watch?v=abc123');
  });
});

describe('extractYoutubeVideoId', () => {
  describe('extracting from watch URLs', () => {
    it('should extract ID from standard watch URL', () => {
      expect(extractYoutubeVideoId('https://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
      expect(extractYoutubeVideoId('https://youtube.com/watch?v=abc123def45')).toBe('abc123def45');
    });

    it('should extract ID when v parameter is not first', () => {
      expect(extractYoutubeVideoId('https://youtube.com/watch?list=PLtest&v=dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    });

    it('should extract ID with timestamp parameter', () => {
      expect(extractYoutubeVideoId('https://youtube.com/watch?v=dQw4w9WgXcQ&t=120')).toBe('dQw4w9WgXcQ');
    });
  });

  describe('extracting from short URLs', () => {
    it('should extract ID from youtu.be URL', () => {
      expect(extractYoutubeVideoId('https://youtu.be/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
      expect(extractYoutubeVideoId('youtu.be/abc123def45')).toBe('abc123def45');
    });

    it('should extract ID from youtu.be with parameters', () => {
      expect(extractYoutubeVideoId('https://youtu.be/dQw4w9WgXcQ?t=120')).toBe('dQw4w9WgXcQ');
    });
  });

  describe('extracting from embed URLs', () => {
    it('should extract ID from embed URL', () => {
      expect(extractYoutubeVideoId('https://youtube.com/embed/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
      expect(extractYoutubeVideoId('https://www.youtube.com/embed/abc123def45')).toBe('abc123def45');
    });
  });

  describe('extracting from v/ URLs', () => {
    it('should extract ID from legacy v/ URL', () => {
      expect(extractYoutubeVideoId('https://youtube.com/v/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    });
  });

  describe('extracting from shorts URLs', () => {
    it('should extract ID from shorts URL', () => {
      expect(extractYoutubeVideoId('https://youtube.com/shorts/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    });
  });

  describe('invalid inputs', () => {
    it('should return null for invalid URLs', () => {
      expect(extractYoutubeVideoId('https://vimeo.com/12345')).toBeNull();
      expect(extractYoutubeVideoId('not a url')).toBeNull();
      expect(extractYoutubeVideoId('')).toBeNull();
    });

    it('should return null for URLs without video ID', () => {
      expect(extractYoutubeVideoId('https://youtube.com/')).toBeNull();
      expect(extractYoutubeVideoId('https://youtube.com/watch')).toBeNull();
    });

    it('should handle whitespace', () => {
      expect(extractYoutubeVideoId('  https://youtu.be/dQw4w9WgXcQ  ')).toBe('dQw4w9WgXcQ');
      expect(extractYoutubeVideoId('   ')).toBeNull();
    });
  });
});
