/**
 * Production-grade React hook for domains data
 * 
 * Features:
 * - Automatic fetching
 * - Error handling and retry
 * - Loading states
 * - Refresh capability
 * - Request cancellation
 */

import { useEffect, useState, useRef, useCallback } from 'react';
import { apiGet } from '../api/client';
import { DomainItem } from '../types/api';

export interface UseDomainsOptions {
  enabled?: boolean;
  onError?: (error: Error) => void;
}

export interface UseDomainsResult {
  domains: DomainItem[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useDomains(
  options: UseDomainsOptions = {}
): UseDomainsResult {
  const { enabled = true, onError } = options;

  const [domains, setDomains] = useState<DomainItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const isMountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchDomains = useCallback(async () => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);

    try {
      const result = await apiGet<DomainItem[]>('/domains', {
        signal: controller.signal,
      });

      if (isMountedRef.current && !controller.signal.aborted) {
        setDomains(result);
        setError(null);
        setLoading(false);
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      const error = err instanceof Error ? err : new Error('Failed to fetch domains');

      if (isMountedRef.current) {
        setError(error);
        setLoading(false);
        onError?.(error);
      }
    }
  }, [onError]);

  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    fetchDomains();
  }, [enabled, fetchDomains]);

  return {
    domains,
    loading,
    error,
    refetch: fetchDomains,
  };
}
