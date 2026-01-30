/**
 * Safe localStorage Wrapper
 * 
 * Provides SSR-safe access to browser localStorage with:
 * - Server-side rendering (SSR) guards to prevent build failures
 * - Error handling for quota exceeded, private browsing, etc.
 * - JSON serialization helpers
 * - TypeScript type safety
 * 
 * @example
 * ```typescript
 * // Simple key-value
 * safeLocalStorage.setItem('theme', 'dark');
 * const theme = safeLocalStorage.getItem('theme');
 * 
 * // JSON objects
 * safeLocalStorage.setJson('user', { id: 1, name: 'John' });
 * const user = safeLocalStorage.getJson('user', { id: 0, name: '' });
 * ```
 */

/**
 * Check if we're running in a browser environment.
 * This prevents errors during server-side rendering.
 */
const isBrowser = typeof window !== 'undefined';

/**
 * Safe localStorage wrapper with SSR compatibility.
 */
export const safeLocalStorage = {
    /**
     * Get an item from localStorage.
     * 
     * @param key - The storage key
     * @returns The stored value, or null if not found or in SSR
     */
    getItem: (key: string): string | null => {
        if (!isBrowser) {
            return null;
        }

        try {
            return localStorage.getItem(key);
        } catch (error) {
            console.warn(`[safeLocalStorage] Failed to read "${key}"`, error);
            return null;
        }
    },

    /**
     * Set an item in localStorage.
     * 
     * @param key - The storage key
     * @param value - The value to store
     * @returns true if successful, false otherwise
     */
    setItem: (key: string, value: string): boolean => {
        if (!isBrowser) {
            return false;
        }

        try {
            localStorage.setItem(key, value);
            return true;
        } catch (error) {
            // Common errors:
            // - QuotaExceededError: Storage is full
            // - SecurityError: Private browsing mode
            console.warn(`[safeLocalStorage] Failed to write "${key}"`, error);
            return false;
        }
    },

    /**
     * Remove an item from localStorage.
     * 
     * @param key - The storage key to remove
     */
    removeItem: (key: string): void => {
        if (!isBrowser) {
            return;
        }

        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.warn(`[safeLocalStorage] Failed to remove "${key}"`, error);
        }
    },

    /**
     * Get a JSON-parsed value from localStorage.
     * 
     * @param key - The storage key
     * @param fallback - Default value if key doesn't exist or parsing fails
     * @returns The parsed value, or fallback
     */
    getJson: <T>(key: string, fallback: T): T => {
        if (!isBrowser) {
            return fallback;
        }

        try {
            const raw = localStorage.getItem(key);
            if (!raw) {
                return fallback;
            }
            return JSON.parse(raw) as T;
        } catch (error) {
            console.warn(`[safeLocalStorage] Failed to parse "${key}"`, error);
            return fallback;
        }
    },

    /**
     * Set a JSON-stringified value in localStorage.
     * 
     * @param key - The storage key
     * @param value - The value to store (will be JSON stringified)
     * @returns true if successful, false otherwise
     */
    setJson: (key: string, value: unknown): boolean => {
        if (!isBrowser) {
            return false;
        }

        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.warn(`[safeLocalStorage] Failed to stringify "${key}"`, error);
            return false;
        }
    },

    /**
     * Check if a key exists in localStorage.
     * 
     * @param key - The storage key to check
     * @returns true if the key exists, false otherwise
     */
    hasItem: (key: string): boolean => {
        if (!isBrowser) {
            return false;
        }

        try {
            return localStorage.getItem(key) !== null;
        } catch {
            return false;
        }
    },

    /**
     * Clear all items from localStorage.
     * Use with caution - this removes ALL stored data.
     */
    clear: (): void => {
        if (!isBrowser) {
            return;
        }

        try {
            localStorage.clear();
        } catch (error) {
            console.warn('[safeLocalStorage] Failed to clear storage', error);
        }
    },

    /**
     * Get all keys in localStorage.
     * 
     * @returns Array of all storage keys, or empty array in SSR
     */
    keys: (): string[] => {
        if (!isBrowser) {
            return [];
        }

        try {
            return Object.keys(localStorage);
        } catch {
            return [];
        }
    },
};

/**
 * Safe sessionStorage Wrapper
 * 
 * Same API as safeLocalStorage but for session storage.
 * Data persists only for the browser session.
 */
export const safeSessionStorage = {
    getItem: (key: string): string | null => {
        if (!isBrowser) {
            return null;
        }

        try {
            return sessionStorage.getItem(key);
        } catch (error) {
            console.warn(`[safeSessionStorage] Failed to read "${key}"`, error);
            return null;
        }
    },

    setItem: (key: string, value: string): boolean => {
        if (!isBrowser) {
            return false;
        }

        try {
            sessionStorage.setItem(key, value);
            return true;
        } catch (error) {
            console.warn(`[safeSessionStorage] Failed to write "${key}"`, error);
            return false;
        }
    },

    removeItem: (key: string): void => {
        if (!isBrowser) {
            return;
        }

        try {
            sessionStorage.removeItem(key);
        } catch (error) {
            console.warn(`[safeSessionStorage] Failed to remove "${key}"`, error);
        }
    },

    getJson: <T>(key: string, fallback: T): T => {
        if (!isBrowser) {
            return fallback;
        }

        try {
            const raw = sessionStorage.getItem(key);
            if (!raw) {
                return fallback;
            }
            return JSON.parse(raw) as T;
        } catch (error) {
            console.warn(`[safeSessionStorage] Failed to parse "${key}"`, error);
            return fallback;
        }
    },

    setJson: (key: string, value: unknown): boolean => {
        if (!isBrowser) {
            return false;
        }

        try {
            sessionStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.warn(`[safeSessionStorage] Failed to stringify "${key}"`, error);
            return false;
        }
    },
};
