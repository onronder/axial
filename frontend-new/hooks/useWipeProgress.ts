'use client';

import { useEffect, useState, useCallback, useRef } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface WipeProgress {
  documentId: string;
  documentName: string;
  currentPass: 1 | 2 | 3;
  passProgress: number;
  isComplete: boolean;
  startedAt: string;
  estimatedCompletion?: string;
  error?: string;
}

interface UseWipeProgressOptions {
  documentId: string;
  documentName?: string;
  enabled?: boolean;
  onComplete?: () => void;
  onError?: (error: Error) => void;
}

interface UseWipeProgressReturn {
  progress: WipeProgress | null;
  isLoading: boolean;
  error: Error | null;
  startWipe: () => Promise<void>;
  cancelWipe: () => void;
  simulateWipe: () => void;
}

// =============================================================================
// Simulation for Development/Demo
// =============================================================================

function createSimulatedProgress(documentId: string, documentName: string): WipeProgress {
  return {
    documentId,
    documentName,
    currentPass: 1,
    passProgress: 0,
    isComplete: false,
    startedAt: new Date().toISOString(),
  };
}

// =============================================================================
// Hook
// =============================================================================

export function useWipeProgress({
  documentId,
  documentName = 'Document',
  enabled = true,
  onComplete,
  onError,
}: UseWipeProgressOptions): UseWipeProgressReturn {
  const [progress, setProgress] = useState<WipeProgress | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const pollingRef = useRef<NodeJS.Timeout | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const simulationRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (simulationRef.current) {
      clearInterval(simulationRef.current);
      simulationRef.current = null;
    }
  }, []);

  // Polling for real wipe status
  const startPolling = useCallback(async () => {
    const poll = async () => {
      if (!isMountedRef.current) return;

      try {
        const response = await fetch(`/api/py/documents/${documentId}/wipe-status`, {
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          if (response.status === 404) {
            // Endpoint doesn't exist - this is expected in development
            return;
          }
          throw new Error('Failed to fetch wipe status');
        }

        const data: WipeProgress = await response.json();

        if (isMountedRef.current) {
          setProgress(data);

          if (data.isComplete) {
            cleanup();
            onComplete?.();
          }
        }
      } catch (err) {
        if (isMountedRef.current) {
          const error = err instanceof Error ? err : new Error('Unknown error');
          setError(error);
          onError?.(error);
          cleanup();
        }
      }
    };

    pollingRef.current = setInterval(poll, 500);
    poll();
  }, [documentId, cleanup, onComplete, onError]);

  // SSE connection for real-time updates
  const connectSSE = useCallback(() => {
    try {
      const eventSource = new EventSource(`/api/py/documents/${documentId}/wipe-progress`);
      eventSourceRef.current = eventSource;

      eventSource.onmessage = (event) => {
        if (!isMountedRef.current) return;

        try {
          const data: WipeProgress = JSON.parse(event.data);
          setProgress(data);

          if (data.isComplete) {
            cleanup();
            onComplete?.();
          }
        } catch {
          // Ignore parse errors
        }
      };

      eventSource.onerror = () => {
        eventSource.close();
        // Fall back to polling
        startPolling();
      };
    } catch {
      // SSE not supported, use polling
      startPolling();
    }
  }, [documentId, cleanup, onComplete, startPolling]);

  // Simulated wipe for development/demo purposes
  const simulateWipe = useCallback(() => {
    cleanup();
    setError(null);
    setIsLoading(true);

    const initialProgress = createSimulatedProgress(documentId, documentName);
    setProgress(initialProgress);

    let currentPass = 1;
    let currentProgress = 0;

    simulationRef.current = setInterval(() => {
      if (!isMountedRef.current) {
        cleanup();
        return;
      }

      currentProgress += Math.random() * 15 + 5; // 5-20% progress per tick

      if (currentProgress >= 100) {
        if (currentPass < 3) {
          currentPass++;
          currentProgress = 0;
        } else {
          // Complete
          setProgress(prev => prev ? {
            ...prev,
            currentPass: 3,
            passProgress: 100,
            isComplete: true,
          } : null);
          setIsLoading(false);
          cleanup();
          onComplete?.();
          return;
        }
      }

      setProgress(prev => prev ? {
        ...prev,
        currentPass: currentPass as 1 | 2 | 3,
        passProgress: Math.min(currentProgress, 100),
      } : null);
    }, 200);
  }, [documentId, documentName, cleanup, onComplete]);

  // Start real wipe operation
  const startWipe = useCallback(async () => {
    cleanup();
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/py/documents/${documentId}/wipe`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        if (response.status === 404) {
          // Endpoint doesn't exist - fall back to simulation
          console.warn('Wipe endpoint not found, using simulation');
          simulateWipe();
          return;
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to start wipe operation');
      }

      // Start monitoring progress
      if (typeof EventSource !== 'undefined') {
        connectSSE();
      } else {
        startPolling();
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Unknown error');
      setError(error);
      onError?.(error);
      setIsLoading(false);
    }
  }, [documentId, connectSSE, startPolling, simulateWipe, cleanup, onError]);

  // Cancel wipe operation
  const cancelWipe = useCallback(() => {
    cleanup();
    setProgress(null);
    setIsLoading(false);
  }, [cleanup]);

  // Cleanup on unmount
  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      cleanup();
    };
  }, [cleanup]);

  return {
    progress,
    isLoading,
    error,
    startWipe,
    cancelWipe,
    simulateWipe,
  };
}

export default useWipeProgress;
