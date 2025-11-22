// React hook for domains data
// Fetches domains list from /api/domains

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import { DomainItem } from "../types/api";

export function useDomains() {
  const [domains, setDomains] = useState<DomainItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchDomains() {
      try {
        const res = await apiGet<DomainItem[]>("/domains");
        if (!cancelled) {
          setDomains(res);
          setLoading(false);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          console.error("Failed to fetch domains:", e);
          setError(e instanceof Error ? e.message : "Unknown error");
          setLoading(false);
        }
      }
    }

    fetchDomains();

    return () => {
      cancelled = true;
    };
  }, []);

  return { domains, loading, error };
}
