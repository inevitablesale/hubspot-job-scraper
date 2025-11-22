/**
 * Production-grade React hook for SSE event streaming
 * 
 * Features:
 * - Automatic connection management
 * - Auto-reconnect with exponential backoff
 * - Proper cleanup
 * - Connection state tracking
 * - Event buffering with size limits
 * - Type-safe event handling
 */

import { useEffect, useState, useRef, useCallback } from 'react';
import { createSSEClient, SSEClient } from '../api/client';
import { CrawlEvent, LogLine } from '../types/api';

export interface UseCrawlerEventsOptions {
  maxEvents?: number;
  maxLogs?: number;
  enabled?: boolean;
  onConnected?: () => void;
  onDisconnected?: () => void;
  onError?: (error: Event) => void;
}

export interface UseCrawlerEventsResult {
  events: CrawlEvent[];
  logs: LogLine[];
  connected: boolean;
  clearEvents: () => void;
  clearLogs: () => void;
}

export function useCrawlerEvents(
  options: UseCrawlerEventsOptions = {}
): UseCrawlerEventsResult {
  const {
    maxEvents = 500,
    maxLogs = 1000,
    enabled = true,
    onConnected,
    onDisconnected,
    onError,
  } = options;

  const [events, setEvents] = useState<CrawlEvent[]>([]);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [connected, setConnected] = useState(false);

  const clientRef = useRef<SSEClient | null>(null);
  const isMountedRef = useRef(true);

  const handleConnected = useCallback(() => {
    if (isMountedRef.current) {
      setConnected(true);
      onConnected?.();
    }
  }, [onConnected]);

  const handleDisconnected = useCallback(() => {
    if (isMountedRef.current) {
      setConnected(false);
      onDisconnected?.();
    }
  }, [onDisconnected]);

  const handleError = useCallback((error: Event) => {
    onError?.(error);
  }, [onError]);

  const clearEvents = useCallback(() => {
    setEvents([]);
  }, []);

  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  useEffect(() => {
    isMountedRef.current = true;

    if (!enabled) {
      return;
    }

    // Create SSE client
    const client = createSSEClient('/events/stream', {
      onConnected: handleConnected,
      onDisconnected: handleDisconnected,
      onError: handleError,
    });

    clientRef.current = client;

    // Subscribe to event messages
    const unsubscribeEvent = client.on('event', (data: CrawlEvent) => {
      if (isMountedRef.current) {
        setEvents(prev => {
          const updated = [...prev, data];
          // Keep only last maxEvents
          return updated.slice(-maxEvents);
        });
      }
    });

    // Subscribe to log messages
    const unsubscribeLog = client.on('log', (data: LogLine) => {
      if (isMountedRef.current) {
        setLogs(prev => {
          const updated = [...prev, data];
          // Keep only last maxLogs
          return updated.slice(-maxLogs);
        });
      }
    });

    // Connect
    client.connect();

    return () => {
      isMountedRef.current = false;
      unsubscribeEvent();
      unsubscribeLog();
      client.disconnect();
    };
  }, [
    enabled,
    maxEvents,
    maxLogs,
    handleConnected,
    handleDisconnected,
    handleError,
  ]);

  return {
    events,
    logs,
    connected,
    clearEvents,
    clearLogs,
  };
}
