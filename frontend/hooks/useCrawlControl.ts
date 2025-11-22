/**
 * Production-grade React hook for crawl control actions
 * 
 * Features:
 * - Start and stop crawl operations
 * - Loading states
 * - Error handling
 * - Automatic status refresh after actions
 */

import { useState, useCallback } from 'react';
import { apiPost } from '../api/client';
import { StartCrawlRequest, StartCrawlResponse } from '../types/api';

export interface UseCrawlControlOptions {
  onStart?: () => void;
  onStop?: () => void;
  onError?: (error: Error) => void;
}

export interface UseCrawlControlResult {
  starting: boolean;
  stopping: boolean;
  error: Error | null;
  startCrawl: (params?: StartCrawlRequest) => Promise<void>;
  stopCrawl: () => Promise<void>;
}

export function useCrawlControl(
  options: UseCrawlControlOptions = {}
): UseCrawlControlResult {
  const { onStart, onStop, onError } = options;

  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const startCrawl = useCallback(
    async (params?: StartCrawlRequest) => {
      setStarting(true);
      setError(null);

      try {
        const response = await apiPost<StartCrawlResponse>(
          '/crawl/start',
          params
        );

        if (!response.ok) {
          throw new Error(response.reason || 'Failed to start crawl');
        }

        onStart?.();
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to start crawl');
        setError(error);
        onError?.(error);
        throw error;
      } finally {
        setStarting(false);
      }
    },
    [onStart, onError]
  );

  const stopCrawl = useCallback(async () => {
    setStopping(true);
    setError(null);

    try {
      const response = await apiPost<StartCrawlResponse>('/crawl/stop');

      if (!response.ok) {
        throw new Error(response.reason || 'Failed to stop crawl');
      }

      onStop?.();
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to stop crawl');
      setError(error);
      onError?.(error);
      throw error;
    } finally {
      setStopping(false);
    }
  }, [onStop, onError]);

  return {
    starting,
    stopping,
    error,
    startCrawl,
    stopCrawl,
  };
}
