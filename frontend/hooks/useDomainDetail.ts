/**
 * Production-grade React hook for domain details
 * 
 * Features:
 * - Fetch single domain with navigation flow and screenshots
 * - Error handling and retry
 * - Loading states
 * - Request cancellation
 */

import { useEffect, useState, useRef, useCallback } from 'react';
import { apiGet } from '../api/client';
import { DomainItem, NavigationFlowStep, ScreenshotInfo } from '../types/api';

export interface UseDomainDetailOptions {
  domain: string | null;
  enabled?: boolean;
  includeFlow?: boolean;
  includeScreenshots?: boolean;
  onError?: (error: Error) => void;
}

export interface UseDomainDetailResult {
  domainInfo: DomainItem | null;
  navigationFlow: NavigationFlowStep[];
  screenshots: ScreenshotInfo[];
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useDomainDetail(
  options: UseDomainDetailOptions
): UseDomainDetailResult {
  const {
    domain,
    enabled = true,
    includeFlow = true,
    includeScreenshots = true,
    onError,
  } = options;

  const [domainInfo, setDomainInfo] = useState<DomainItem | null>(null);
  const [navigationFlow, setNavigationFlow] = useState<NavigationFlowStep[]>([]);
  const [screenshots, setScreenshots] = useState<ScreenshotInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const isMountedRef = useRef(true);
  const abortControllersRef = useRef<AbortController[]>([]);

  const fetchDomainData = useCallback(async () => {
    if (!domain) {
      setDomainInfo(null);
      setNavigationFlow([]);
      setScreenshots([]);
      setLoading(false);
      return;
    }

    // Abort previous requests
    abortControllersRef.current.forEach(controller => controller.abort());
    abortControllersRef.current = [];

    setLoading(true);
    setError(null);

    try {
      const requests: Promise<any>[] = [];

      // Fetch domain info
      const domainController = new AbortController();
      abortControllersRef.current.push(domainController);
      requests.push(
        apiGet<DomainItem>(`/domains/${encodeURIComponent(domain)}`, {
          signal: domainController.signal,
        })
      );

      // Fetch navigation flow if requested
      if (includeFlow) {
        const flowController = new AbortController();
        abortControllersRef.current.push(flowController);
        requests.push(
          apiGet<NavigationFlowStep[]>(
            `/domains/${encodeURIComponent(domain)}/flow`,
            { signal: flowController.signal }
          )
        );
      } else {
        requests.push(Promise.resolve([]));
      }

      // Fetch screenshots if requested
      if (includeScreenshots) {
        const screenshotsController = new AbortController();
        abortControllersRef.current.push(screenshotsController);
        requests.push(
          apiGet<ScreenshotInfo[]>(
            `/domains/${encodeURIComponent(domain)}/screenshots`,
            { signal: screenshotsController.signal }
          )
        );
      } else {
        requests.push(Promise.resolve([]));
      }

      const [info, flow, shots] = await Promise.all(requests);

      if (isMountedRef.current) {
        setDomainInfo(info);
        setNavigationFlow(flow || []);
        setScreenshots(shots || []);
        setLoading(false);
      }
    } catch (err) {
      // Ignore abort errors
      if (err instanceof Error && err.name === 'AbortError') {
        return;
      }

      const error = err instanceof Error ? err : new Error('Failed to fetch domain details');

      if (isMountedRef.current) {
        setError(error);
        setLoading(false);
        onError?.(error);
      }
    }
  }, [domain, includeFlow, includeScreenshots, onError]);

  useEffect(() => {
    isMountedRef.current = true;

    return () => {
      isMountedRef.current = false;
      abortControllersRef.current.forEach(controller => controller.abort());
    };
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    fetchDomainData();
  }, [enabled, fetchDomainData]);

  return {
    domainInfo,
    navigationFlow,
    screenshots,
    loading,
    error,
    refetch: fetchDomainData,
  };
}
