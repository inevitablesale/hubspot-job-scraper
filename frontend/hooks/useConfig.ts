/**
 * Production-grade React hook for configuration management
 * 
 * Features:
 * - Automatic config loading
 * - Optimistic updates
 * - Error handling with rollback
 * - Loading states for updates
 * - Request cancellation
 */

import { useEffect, useState, useRef, useCallback } from 'react';
import { apiGet, apiPut } from '../api/client';
import { ConfigSettings } from '../types/api';

export interface UseConfigOptions {
  enabled?: boolean;
  onError?: (error: Error) => void;
  onUpdate?: (config: ConfigSettings) => void;
}

export interface UseConfigResult {
  config: ConfigSettings | null;
  loading: boolean;
  updating: boolean;
  error: Error | null;
  updateConfig: (config: ConfigSettings) => Promise<void>;
  refetch: () => Promise<void>;
}

export function useConfig(
  options: UseConfigOptions = {}
): UseConfigResult {
  const { enabled = true, onError, onUpdate } = options;

  const [config, setConfig] = useState<ConfigSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const isMountedRef = useRef(true);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchConfig = useCallback(async () => {
    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoading(true);

    try {
      const result = await apiGet<ConfigSettings>('/config', {
        signal: controller.signal,
      });

      if (isMountedRef.current && !controller.signal.aborted) {
        setConfig(result);
        setError(null);
        setLoading(false);
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      const error = err instanceof Error ? err : new Error('Failed to fetch config');

      if (isMountedRef.current) {
        setError(error);
        setLoading(false);
        onError?.(error);
      }
    }
  }, [onError]);

  const updateConfig = useCallback(
    async (newConfig: ConfigSettings) => {
      if (!isMountedRef.current) return;

      // Store previous config for rollback
      const previousConfig = config;

      // Optimistic update
      setConfig(newConfig);
      setUpdating(true);
      setError(null);

      try {
        const result = await apiPut<ConfigSettings>('/config', newConfig);

        if (isMountedRef.current) {
          setConfig(result);
          setUpdating(false);
          onUpdate?.(result);
        }
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to update config');

        if (isMountedRef.current) {
          // Rollback on error
          setConfig(previousConfig);
          setError(error);
          setUpdating(false);
          onError?.(error);
        }

        throw error; // Re-throw for caller to handle
      }
    },
    [config, onError, onUpdate]
  );

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

    fetchConfig();
  }, [enabled, fetchConfig]);

  return {
    config,
    loading,
    updating,
    error,
    updateConfig,
    refetch: fetchConfig,
  };
}
