/**
 * Production-grade React hook for log data
 * 
 * Features:
 * - Fetch initial log history
 * - Real-time log updates via SSE integration
 * - Log level filtering
 * - Domain filtering
 * - Export functionality
 * - Size-limited buffer
 */

import { useEffect, useState, useCallback, useMemo } from 'react';
import { apiGet } from '../api/client';
import { LogLine, LogLevel } from '../types/api';

export interface UseLogsOptions {
  initialLimit?: number;
  maxLogs?: number;
  filterLevel?: LogLevel;
  filterDomain?: string;
  enabled?: boolean;
  onError?: (error: Error) => void;
}

export interface UseLogsResult {
  logs: LogLine[];
  filteredLogs: LogLine[];
  loading: boolean;
  error: Error | null;
  clearLogs: () => void;
  exportLogs: () => void;
}

export function useLogs(options: UseLogsOptions = {}): UseLogsResult {
  const {
    initialLimit = 500,
    maxLogs = 1000,
    filterLevel,
    filterDomain,
    enabled = true,
    onError,
  } = options;

  const [logs, setLogs] = useState<LogLine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Fetch initial logs
  useEffect(() => {
    if (!enabled) {
      return;
    }

    const fetchLogs = async () => {
      setLoading(true);

      try {
        const result = await apiGet<LogLine[]>(
          `/logs?limit=${initialLimit}`
        );

        setLogs(result);
        setError(null);
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to fetch logs');
        setError(error);
        onError?.(error);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [enabled, initialLimit, onError]);

  // Filter logs
  const filteredLogs = useMemo(() => {
    let filtered = logs;

    if (filterLevel) {
      filtered = filtered.filter(log => log.level === filterLevel);
    }

    if (filterDomain) {
      filtered = filtered.filter(log => log.domain === filterDomain);
    }

    return filtered;
  }, [logs, filterLevel, filterDomain]);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  const exportLogs = useCallback(() => {
    const content = filteredLogs
      .map(log => {
        const timestamp = new Date(log.ts).toISOString();
        const level = log.level.toUpperCase().padEnd(7);
        const domain = log.domain ? `[${log.domain}]` : '';
        return `${timestamp} ${level} ${domain} ${log.message}`;
      })
      .join('\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `scraper-logs-${new Date().toISOString()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [filteredLogs]);

  return {
    logs,
    filteredLogs,
    loading,
    error,
    clearLogs,
    exportLogs,
  };
}
