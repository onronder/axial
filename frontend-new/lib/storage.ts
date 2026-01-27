export const safeLocalStorage = {
  getItem: (key: string): string | null => {
    try {
      return localStorage.getItem(key);
    } catch (error) {
      console.warn(`[safeLocalStorage] Failed to read "${key}"`, error);
      return null;
    }
  },
  setItem: (key: string, value: string): boolean => {
    try {
      localStorage.setItem(key, value);
      return true;
    } catch (error) {
      console.warn(`[safeLocalStorage] Failed to write "${key}"`, error);
      return false;
    }
  },
  removeItem: (key: string): void => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.warn(`[safeLocalStorage] Failed to remove "${key}"`, error);
    }
  },
  getJson: <T>(key: string, fallback: T): T => {
    try {
      const raw = localStorage.getItem(key);
      if (!raw) return fallback;
      return JSON.parse(raw) as T;
    } catch (error) {
      console.warn(`[safeLocalStorage] Failed to parse "${key}"`, error);
      return fallback;
    }
  },
  setJson: (key: string, value: unknown): boolean => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      console.warn(`[safeLocalStorage] Failed to stringify "${key}"`, error);
      return false;
    }
  },
};
