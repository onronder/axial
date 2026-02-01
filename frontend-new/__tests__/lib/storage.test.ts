/**
 * Tests for lib/storage.ts - Safe localStorage/sessionStorage wrappers
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { safeLocalStorage, safeSessionStorage } from '@/lib/storage';

// Mock localStorage and sessionStorage
const createStorageMock = () => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null),
  };
};

describe('safeLocalStorage', () => {
  let localStorageMock: ReturnType<typeof createStorageMock>;

  beforeEach(() => {
    localStorageMock = createStorageMock();
    Object.defineProperty(globalThis, 'localStorage', {
      value: localStorageMock,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getItem', () => {
    it('should return value for existing key', () => {
      localStorageMock.getItem.mockReturnValueOnce('test-value');
      expect(safeLocalStorage.getItem('test-key')).toBe('test-value');
    });

    it('should return null for non-existing key', () => {
      localStorageMock.getItem.mockReturnValueOnce(null);
      expect(safeLocalStorage.getItem('non-existent')).toBeNull();
    });

    it('should return null and log warning on error', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      localStorageMock.getItem.mockImplementationOnce(() => {
        throw new Error('Storage error');
      });
      
      expect(safeLocalStorage.getItem('error-key')).toBeNull();
      expect(warnSpy).toHaveBeenCalledWith(
        '[safeLocalStorage] Failed to read "error-key"',
        expect.any(Error)
      );
    });
  });

  describe('setItem', () => {
    it('should set value and return true', () => {
      expect(safeLocalStorage.setItem('key', 'value')).toBe(true);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('key', 'value');
    });

    it('should return false and log warning on error', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      localStorageMock.setItem.mockImplementationOnce(() => {
        throw new Error('QuotaExceededError');
      });
      
      expect(safeLocalStorage.setItem('quota-key', 'large-value')).toBe(false);
      expect(warnSpy).toHaveBeenCalledWith(
        '[safeLocalStorage] Failed to write "quota-key"',
        expect.any(Error)
      );
    });
  });

  describe('removeItem', () => {
    it('should remove item from storage', () => {
      safeLocalStorage.removeItem('key-to-remove');
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('key-to-remove');
    });

    it('should log warning on error', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      localStorageMock.removeItem.mockImplementationOnce(() => {
        throw new Error('Remove error');
      });
      
      safeLocalStorage.removeItem('error-key');
      expect(warnSpy).toHaveBeenCalledWith(
        '[safeLocalStorage] Failed to remove "error-key"',
        expect.any(Error)
      );
    });
  });

  describe('getJson', () => {
    it('should return parsed JSON value', () => {
      localStorageMock.getItem.mockReturnValueOnce('{"name":"John","age":30}');
      
      const result = safeLocalStorage.getJson('user', { name: '', age: 0 });
      expect(result).toEqual({ name: 'John', age: 30 });
    });

    it('should return fallback for non-existing key', () => {
      localStorageMock.getItem.mockReturnValueOnce(null);
      
      const fallback = { defaultValue: true };
      expect(safeLocalStorage.getJson('missing', fallback)).toBe(fallback);
    });

    it('should return fallback for invalid JSON', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      localStorageMock.getItem.mockReturnValueOnce('invalid-json{');
      
      const fallback = { valid: false };
      expect(safeLocalStorage.getJson('invalid', fallback)).toBe(fallback);
      expect(warnSpy).toHaveBeenCalled();
    });

    it('should return fallback on read error', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      localStorageMock.getItem.mockImplementationOnce(() => {
        throw new Error('Read error');
      });
      
      const fallback = ['default'];
      expect(safeLocalStorage.getJson('error', fallback)).toBe(fallback);
      expect(warnSpy).toHaveBeenCalled();
    });
  });

  describe('setJson', () => {
    it('should stringify and store JSON value', () => {
      const data = { key: 'value', number: 42 };
      expect(safeLocalStorage.setJson('json-key', data)).toBe(true);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'json-key',
        JSON.stringify(data)
      );
    });

    it('should return false on stringify error', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      localStorageMock.setItem.mockImplementationOnce(() => {
        throw new Error('Stringify error');
      });
      
      expect(safeLocalStorage.setJson('error', { data: 'test' })).toBe(false);
      expect(warnSpy).toHaveBeenCalled();
    });
  });

  describe('hasItem', () => {
    it('should return true for existing key', () => {
      localStorageMock.getItem.mockReturnValueOnce('some-value');
      expect(safeLocalStorage.hasItem('existing')).toBe(true);
    });

    it('should return false for non-existing key', () => {
      localStorageMock.getItem.mockReturnValueOnce(null);
      expect(safeLocalStorage.hasItem('missing')).toBe(false);
    });

    it('should return false on error', () => {
      localStorageMock.getItem.mockImplementationOnce(() => {
        throw new Error('Error');
      });
      expect(safeLocalStorage.hasItem('error')).toBe(false);
    });
  });

  describe('clear', () => {
    it('should clear all storage', () => {
      safeLocalStorage.clear();
      expect(localStorageMock.clear).toHaveBeenCalled();
    });

    it('should log warning on error', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      localStorageMock.clear.mockImplementationOnce(() => {
        throw new Error('Clear error');
      });
      
      safeLocalStorage.clear();
      expect(warnSpy).toHaveBeenCalledWith(
        '[safeLocalStorage] Failed to clear storage',
        expect.any(Error)
      );
    });
  });

  describe('keys', () => {
    it('should return all storage keys', () => {
      // Set up mock storage with some keys
      Object.defineProperty(globalThis, 'localStorage', {
        value: {
          ...localStorageMock,
          key1: 'value1',
          key2: 'value2',
        },
        writable: true,
        configurable: true,
      });
      
      const keys = safeLocalStorage.keys();
      expect(Array.isArray(keys)).toBe(true);
    });

    it('should return empty array on error', () => {
      Object.defineProperty(globalThis, 'localStorage', {
        get() {
          throw new Error('Storage unavailable');
        },
        configurable: true,
      });
      
      // Re-mock localStorage to throw on Object.keys
      Object.defineProperty(globalThis, 'localStorage', {
        value: new Proxy({}, {
          ownKeys() {
            throw new Error('Keys error');
          }
        }),
        writable: true,
        configurable: true,
      });
      
      expect(safeLocalStorage.keys()).toEqual([]);
    });
  });
});

describe('safeSessionStorage', () => {
  let sessionStorageMock: ReturnType<typeof createStorageMock>;

  beforeEach(() => {
    sessionStorageMock = createStorageMock();
    Object.defineProperty(globalThis, 'sessionStorage', {
      value: sessionStorageMock,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('getItem', () => {
    it('should return value for existing key', () => {
      sessionStorageMock.getItem.mockReturnValueOnce('session-value');
      expect(safeSessionStorage.getItem('session-key')).toBe('session-value');
    });

    it('should return null for non-existing key', () => {
      sessionStorageMock.getItem.mockReturnValueOnce(null);
      expect(safeSessionStorage.getItem('missing')).toBeNull();
    });

    it('should return null and log warning on error', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      sessionStorageMock.getItem.mockImplementationOnce(() => {
        throw new Error('Session error');
      });
      
      expect(safeSessionStorage.getItem('error')).toBeNull();
      expect(warnSpy).toHaveBeenCalledWith(
        '[safeSessionStorage] Failed to read "error"',
        expect.any(Error)
      );
    });
  });

  describe('setItem', () => {
    it('should set value and return true', () => {
      expect(safeSessionStorage.setItem('key', 'value')).toBe(true);
      expect(sessionStorageMock.setItem).toHaveBeenCalledWith('key', 'value');
    });

    it('should return false and log warning on error', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      sessionStorageMock.setItem.mockImplementationOnce(() => {
        throw new Error('Write error');
      });
      
      expect(safeSessionStorage.setItem('key', 'value')).toBe(false);
      expect(warnSpy).toHaveBeenCalled();
    });
  });

  describe('removeItem', () => {
    it('should remove item from storage', () => {
      safeSessionStorage.removeItem('to-remove');
      expect(sessionStorageMock.removeItem).toHaveBeenCalledWith('to-remove');
    });

    it('should log warning on error', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      sessionStorageMock.removeItem.mockImplementationOnce(() => {
        throw new Error('Remove error');
      });
      
      safeSessionStorage.removeItem('error');
      expect(warnSpy).toHaveBeenCalled();
    });
  });

  describe('getJson', () => {
    it('should return parsed JSON value', () => {
      sessionStorageMock.getItem.mockReturnValueOnce('["item1","item2"]');
      
      const result = safeSessionStorage.getJson<string[]>('array', []);
      expect(result).toEqual(['item1', 'item2']);
    });

    it('should return fallback for non-existing key', () => {
      sessionStorageMock.getItem.mockReturnValueOnce(null);
      
      expect(safeSessionStorage.getJson('missing', 'default')).toBe('default');
    });

    it('should return fallback for invalid JSON', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      sessionStorageMock.getItem.mockReturnValueOnce('not-json');
      
      expect(safeSessionStorage.getJson('invalid', 123)).toBe(123);
      expect(warnSpy).toHaveBeenCalled();
    });
  });

  describe('setJson', () => {
    it('should stringify and store JSON value', () => {
      const data = [1, 2, 3];
      expect(safeSessionStorage.setJson('array', data)).toBe(true);
      expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
        'array',
        JSON.stringify(data)
      );
    });

    it('should return false on error', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      sessionStorageMock.setItem.mockImplementationOnce(() => {
        throw new Error('Error');
      });
      
      expect(safeSessionStorage.setJson('key', {})).toBe(false);
      expect(warnSpy).toHaveBeenCalled();
    });

    it('should handle nested objects', () => {
      const nested = { level1: { level2: { value: 'deep' } } };
      expect(safeSessionStorage.setJson('nested', nested)).toBe(true);
      expect(sessionStorageMock.setItem).toHaveBeenCalledWith(
        'nested',
        JSON.stringify(nested)
      );
    });
  });

  describe('getJson error paths', () => {
    it('should handle getItem throwing in getJson', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      sessionStorageMock.getItem.mockImplementationOnce(() => {
        throw new Error('Read failed');
      });
      
      const fallback = { default: true };
      expect(safeSessionStorage.getJson('error', fallback)).toBe(fallback);
      expect(warnSpy).toHaveBeenCalledWith(
        '[safeSessionStorage] Failed to parse "error"',
        expect.any(Error)
      );
    });
  });
});

// SSR-specific tests that require mocking window
describe('Storage SSR Behavior', () => {
  // Save original window
  const originalWindow = globalThis.window;

  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    // Restore window
    Object.defineProperty(globalThis, 'window', {
      value: originalWindow,
      writable: true,
      configurable: true,
    });
  });

  it('safeLocalStorage.keys should return empty array on error', async () => {
    // Create a proxy that throws on Object.keys
    const throwingStorage = new Proxy({} as Storage, {
      ownKeys() {
        throw new Error('Keys not available');
      }
    });
    
    Object.defineProperty(globalThis, 'localStorage', {
      value: throwingStorage,
      writable: true,
      configurable: true,
    });
    
    const { safeLocalStorage } = await import('@/lib/storage');
    expect(safeLocalStorage.keys()).toEqual([]);
  });
});

// =============================================================================
// SSR Path Tests (when window is undefined)
// =============================================================================

describe('Storage SSR paths - safeSessionStorage', () => {
  it('safeSessionStorage.getJson returns fallback when isBrowser is false', async () => {
    vi.resetModules();
    
    // Mock window as undefined to simulate SSR
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeSessionStorage } = await import('@/lib/storage');
    
    const fallback = { defaultValue: true };
    const result = safeSessionStorage.getJson('test-key', fallback);
    
    expect(result).toBe(fallback);
    
    // Restore window
    globalThis.window = originalWindow;
  });

  it('safeSessionStorage.setJson returns false when isBrowser is false', async () => {
    vi.resetModules();
    
    // Mock window as undefined to simulate SSR
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeSessionStorage } = await import('@/lib/storage');
    
    const result = safeSessionStorage.setJson('test-key', { value: 'test' });
    
    expect(result).toBe(false);
    
    // Restore window
    globalThis.window = originalWindow;
  });

  it('safeLocalStorage.getJson returns fallback when isBrowser is false', async () => {
    vi.resetModules();
    
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeLocalStorage } = await import('@/lib/storage');
    
    const fallback = ['default', 'array'];
    const result = safeLocalStorage.getJson('test-key', fallback);
    
    expect(result).toBe(fallback);
    
    globalThis.window = originalWindow;
  });

  it('safeLocalStorage.setJson returns false when isBrowser is false', async () => {
    vi.resetModules();
    
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeLocalStorage } = await import('@/lib/storage');
    
    const result = safeLocalStorage.setJson('test-key', { data: 123 });
    
    expect(result).toBe(false);
    
    globalThis.window = originalWindow;
  });

  it('safeLocalStorage.getItem returns null when isBrowser is false', async () => {
    vi.resetModules();
    
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeLocalStorage } = await import('@/lib/storage');
    
    const result = safeLocalStorage.getItem('any-key');
    
    expect(result).toBeNull();
    
    globalThis.window = originalWindow;
  });

  it('safeLocalStorage.setItem returns false when isBrowser is false', async () => {
    vi.resetModules();
    
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeLocalStorage } = await import('@/lib/storage');
    
    const result = safeLocalStorage.setItem('any-key', 'value');
    
    expect(result).toBe(false);
    
    globalThis.window = originalWindow;
  });

  it('safeLocalStorage.removeItem does nothing when isBrowser is false', async () => {
    vi.resetModules();
    
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeLocalStorage } = await import('@/lib/storage');
    
    // Should not throw
    safeLocalStorage.removeItem('any-key');
    
    globalThis.window = originalWindow;
  });

  it('safeLocalStorage.hasItem returns false when isBrowser is false', async () => {
    vi.resetModules();
    
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeLocalStorage } = await import('@/lib/storage');
    
    const result = safeLocalStorage.hasItem('any-key');
    
    expect(result).toBe(false);
    
    globalThis.window = originalWindow;
  });

  it('safeLocalStorage.clear does nothing when isBrowser is false', async () => {
    vi.resetModules();
    
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeLocalStorage } = await import('@/lib/storage');
    
    // Should not throw
    safeLocalStorage.clear();
    
    globalThis.window = originalWindow;
  });

  it('safeLocalStorage.keys returns empty array when isBrowser is false', async () => {
    vi.resetModules();
    
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeLocalStorage } = await import('@/lib/storage');
    
    const result = safeLocalStorage.keys();
    
    expect(result).toEqual([]);
    
    globalThis.window = originalWindow;
  });

  it('safeSessionStorage.getItem returns null when isBrowser is false', async () => {
    vi.resetModules();
    
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeSessionStorage } = await import('@/lib/storage');
    
    const result = safeSessionStorage.getItem('any-key');
    
    expect(result).toBeNull();
    
    globalThis.window = originalWindow;
  });

  it('safeSessionStorage.setItem returns false when isBrowser is false', async () => {
    vi.resetModules();
    
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeSessionStorage } = await import('@/lib/storage');
    
    const result = safeSessionStorage.setItem('any-key', 'value');
    
    expect(result).toBe(false);
    
    globalThis.window = originalWindow;
  });

  it('safeSessionStorage.removeItem does nothing when isBrowser is false', async () => {
    vi.resetModules();
    
    const originalWindow = globalThis.window;
    // @ts-expect-error - intentionally setting to undefined for SSR test
    delete globalThis.window;
    
    const { safeSessionStorage } = await import('@/lib/storage');
    
    // Should not throw
    safeSessionStorage.removeItem('any-key');
    
    globalThis.window = originalWindow;
  });
});

describe('Storage - Edge Cases', () => {
  let localStorageMock: ReturnType<typeof createStorageMock>;
  let sessionStorageMock: ReturnType<typeof createStorageMock>;

  beforeEach(() => {
    localStorageMock = createStorageMock();
    sessionStorageMock = createStorageMock();
    
    Object.defineProperty(globalThis, 'localStorage', {
      value: localStorageMock,
      writable: true,
      configurable: true,
    });
    
    Object.defineProperty(globalThis, 'sessionStorage', {
      value: sessionStorageMock,
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Empty String Values', () => {
    it('safeLocalStorage should store and retrieve empty string', () => {
      localStorageMock.getItem.mockReturnValueOnce('');
      expect(safeLocalStorage.getItem('empty')).toBe('');
    });

    it('safeSessionStorage should store and retrieve empty string', () => {
      sessionStorageMock.getItem.mockReturnValueOnce('');
      expect(safeSessionStorage.getItem('empty')).toBe('');
    });
  });

  describe('Special Characters', () => {
    it('should handle keys with special characters', () => {
      expect(safeLocalStorage.setItem('key:with:colons', 'value')).toBe(true);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('key:with:colons', 'value');
    });

    it('should handle values with unicode characters', () => {
      const unicodeValue = '日本語テスト 🎉';
      expect(safeLocalStorage.setItem('unicode', unicodeValue)).toBe(true);
      expect(localStorageMock.setItem).toHaveBeenCalledWith('unicode', unicodeValue);
    });
  });

  describe('JSON Edge Cases', () => {
    it('should handle null as JSON value', () => {
      localStorageMock.getItem.mockReturnValueOnce('null');
      expect(safeLocalStorage.getJson('null-key', 'default')).toBeNull();
    });

    it('should handle array as JSON fallback', () => {
      localStorageMock.getItem.mockReturnValueOnce(null);
      const fallback = [1, 2, 3];
      expect(safeLocalStorage.getJson('missing', fallback)).toBe(fallback);
    });

    it('should handle complex nested objects', () => {
      const complex = {
        nested: {
          array: [1, 2, { deep: true }],
          value: 'test',
        },
        date: '2026-01-01',
      };
      localStorageMock.getItem.mockReturnValueOnce(JSON.stringify(complex));
      expect(safeLocalStorage.getJson('complex', {})).toEqual(complex);
    });

    it('should set undefined as null in JSON', () => {
      const withUndefined = { a: 1, b: undefined };
      expect(safeLocalStorage.setJson('undef', withUndefined)).toBe(true);
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'undef',
        JSON.stringify(withUndefined) // undefined becomes omitted
      );
    });
  });

  describe('hasItem Edge Cases', () => {
    it('should handle empty string value as existing', () => {
      localStorageMock.getItem.mockReturnValueOnce('');
      expect(safeLocalStorage.hasItem('empty-value')).toBe(true);
    });
  });

  describe('Concurrent Access', () => {
    it('should handle multiple sequential reads', () => {
      localStorageMock.getItem
        .mockReturnValueOnce('value1')
        .mockReturnValueOnce('value2')
        .mockReturnValueOnce('value3');

      expect(safeLocalStorage.getItem('key1')).toBe('value1');
      expect(safeLocalStorage.getItem('key2')).toBe('value2');
      expect(safeLocalStorage.getItem('key3')).toBe('value3');
    });

    it('should handle read-write-read pattern', () => {
      localStorageMock.getItem.mockReturnValueOnce(null);
      expect(safeLocalStorage.getItem('new-key')).toBeNull();
      
      expect(safeLocalStorage.setItem('new-key', 'new-value')).toBe(true);
      
      localStorageMock.getItem.mockReturnValueOnce('new-value');
      expect(safeLocalStorage.getItem('new-key')).toBe('new-value');
    });
  });

  describe('Error Recovery', () => {
    it('should recover from errors on subsequent calls', () => {
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      // First call throws
      localStorageMock.getItem.mockImplementationOnce(() => {
        throw new Error('Temporary error');
      });
      expect(safeLocalStorage.getItem('key')).toBeNull();
      expect(warnSpy).toHaveBeenCalled();
      
      // Clear mock calls
      warnSpy.mockClear();
      
      // Second call succeeds
      localStorageMock.getItem.mockReturnValueOnce('recovered-value');
      expect(safeLocalStorage.getItem('key')).toBe('recovered-value');
      expect(warnSpy).not.toHaveBeenCalled();
    });
  });
});
