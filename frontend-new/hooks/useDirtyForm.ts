"use client";

import { useState, useCallback, useRef, useEffect } from "react";

export function useDirtyForm<T extends Record<string, unknown>>(initialValues: T) {
  const initialRef = useRef<T>(initialValues);
  const [initialSnapshot, setInitialSnapshot] = useState(() => JSON.stringify(initialValues));
  const [values, setValues] = useState<T>(initialValues);

  const setField = useCallback(<K extends keyof T>(key: K, value: T[K]) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  const isDirty = JSON.stringify(values) !== initialSnapshot;

  // Warn user before leaving page with unsaved changes
  useEffect(() => {
    if (!isDirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [isDirty]);

  const reset = useCallback((newInitial?: T) => {
    if (newInitial) {
      initialRef.current = newInitial;
      setInitialSnapshot(JSON.stringify(newInitial));
      setValues(newInitial);
    } else {
      setValues(initialRef.current);
    }
  }, []);

  return { values, setField, isDirty, reset };
}
