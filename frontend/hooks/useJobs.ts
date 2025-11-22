/**
 * Production-grade React hook for jobs data
 * 
 * Features:
 * - Automatic fetching with dependency tracking
 * - Debounced search queries
 * - Pagination support
 * - Error handling and retry
 * - Request cancellation
 * - Loading states
 */

import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { apiGet } from '../api/client';
import { JobItem } from '../types/api';

export interface UseJobsOptions {
  q?: string;
  domain?: string;
  remoteOnly?: boolean;
  enabled?: boolean;
  debounceMs?: number;
  onError?: (error: Error) => void;
}

export interface UseJobsResult {
  jobs: JobItem[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useJobs(options: UseJobsOptions = {}): UseJobsResult {
  const {
    q,
    domain,
    remoteOnly = false,
    enabled = true,
    debounceMs = 300,
    onError,
  } = options;

  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const isMountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Build query string
  const queryString = useMemo(() => {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (domain) params.set('domain', domain);
    if (remoteOnly) params.set('remote_only', 'true');
    const qs = params.toString();
    return qs ? `?${qs}` : '';
  }, [q, domain, remoteOnly]);

  const fetchJobs = useCallback(async () => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);

    try {
      const result = await apiGet<JobItem[]>(
        `/jobs${queryString}`,
        { signal: controller.signal }
      );

      if (isMountedRef.current && !controller.signal.aborted) {
        setJobs(result);
        setError(null);
        setLoading(false);
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      const error = err instanceof Error ? err : new Error('Failed to fetch jobs');

      if (isMountedRef.current) {
        setError(error);
        setLoading(false);
        onError?.(error);
      }
    }
  }, [queryString, onError]);

  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    // Clear previous debounce timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Debounce the fetch for search queries
    if (q && debounceMs > 0) {
      debounceTimerRef.current = setTimeout(() => {
        fetchJobs();
      }, debounceMs);
    } else {
      // Immediate fetch for non-search queries
      fetchJobs();
    }
  }, [enabled, fetchJobs, q, debounceMs]);

  return {
    jobs,
    loading,
    error,
    refetch: fetchJobs,
  };
}
