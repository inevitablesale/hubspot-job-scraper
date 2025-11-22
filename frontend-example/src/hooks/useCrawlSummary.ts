// React hook for crawl summary (Dashboard + header)
// Polls the /api/system/summary endpoint at regular intervals

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import { CrawlSummary } from "../types/api";

export function useCrawlSummary(pollMs = 5000) {
  const [data, setData] = useState<CrawlSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchSummary() {
      try {
        const res = await apiGet<CrawlSummary>("/system/summary");
        if (!cancelled) {
          setData(res);
          setLoading(false);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          console.error("Failed to fetch summary:", e);
          setError(e instanceof Error ? e.message : "Unknown error");
          setLoading(false);
        }
      }
    }

    // Initial fetch
    fetchSummary();

    // Poll at interval
    const id = setInterval(fetchSummary, pollMs);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [pollMs]);

  return { data, loading, error };
}
