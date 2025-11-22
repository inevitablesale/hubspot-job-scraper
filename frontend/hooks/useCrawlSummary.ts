/**
 * Production-grade React hook for crawl summary
 * 
 * Features:
 * - Automatic polling with configurable interval
 * - Error handling and retry logic
 * - Loading and error states
 * - Cleanup on unmount
 * - Request deduplication
 */

import { useEffect, useState, useRef, useCallback } from 'react';
import { apiGet } from '../api/client';
import { CrawlSummary } from '../types/api';

export interface UseCrawlSummaryOptions {
  pollInterval?: number;
  enabled?: boolean;
  onError?: (error: Error) => void;
}

export interface UseCrawlSummaryResult {
  data: CrawlSummary | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useCrawlSummary(
  options: UseCrawlSummaryOptions = {}
): UseCrawlSummaryResult {
  const {
    pollInterval = 5000,
    enabled = true,
    onError,
  } = options;

  const [data, setData] = useState<CrawlSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const isMountedRef = useRef(true);
  const fetchInProgressRef = useRef(false);

  const fetchSummary = useCallback(async () => {
    // Prevent duplicate requests
    if (fetchInProgressRef.current) {
      return;
    }

    fetchInProgressRef.current = true;

    try {
      const summary = await apiGet<CrawlSummary>('/system/summary');

      if (isMountedRef.current) {
        setData(summary);
        setError(null);
        setLoading(false);
      }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch summary');

      if (isMountedRef.current) {
        setError(error);
        setLoading(false);
        onError?.(error);
      }
    } finally {
      fetchInProgressRef.current = false;
    }
  }, [onError]);

  useEffect(() => {
    isMountedRef.current = true;

    if (!enabled) {
      return;
    }

    // Initial fetch
    fetchSummary();

    // Set up polling
    const intervalId = setInterval(fetchSummary, pollInterval);

    return () => {
      isMountedRef.current = false;
      clearInterval(intervalId);
    };
  }, [enabled, pollInterval, fetchSummary]);

  return {
    data,
    loading,
    error,
    refetch: fetchSummary,
  };
}
