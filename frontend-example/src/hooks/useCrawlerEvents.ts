// React hook for real-time crawler events via SSE
// Connects to /api/events/stream for live updates

import { useEffect, useRef, useState } from "react";
import { createEventSource } from "../api/client";
import { CrawlEvent, LogLine } from "../types/api";

export function useCrawlerEvents() {
  const [events, setEvents] = useState<CrawlEvent[]>([]);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [connected, setConnected] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = createEventSource("/events/stream");
    sourceRef.current = es;

    es.onopen = () => {
      console.log("SSE connection opened");
      setConnected(true);
    };

    es.onerror = (error) => {
      console.error("SSE error:", error);
      setConnected(false);
    };

    // Listen for event messages (CrawlEvent)
    es.addEventListener("event", (evt) => {
      try {
        const data = JSON.parse((evt as MessageEvent).data) as CrawlEvent;
        setEvents((prev) => [...prev, data].slice(-500)); // Keep last 500
      } catch (e) {
        console.error("Failed to parse event:", e);
      }
    });

    // Listen for log messages (LogLine)
    es.addEventListener("log", (evt) => {
      try {
        const data = JSON.parse((evt as MessageEvent).data) as LogLine;
        setLogs((prev) => [...prev, data].slice(-1000)); // Keep last 1000
      } catch (e) {
        console.error("Failed to parse log:", e);
      }
    });

    // Listen for heartbeat (optional)
    es.addEventListener("heartbeat", () => {
      // Just to keep connection alive
    });

    // Listen for connected confirmation
    es.addEventListener("connected", () => {
      console.log("SSE connected confirmation received");
    });

    return () => {
      console.log("Closing SSE connection");
      es.close();
      setConnected(false);
    };
  }, []);

  return { events, logs, connected };
}
