// React hook for jobs data
// Fetches and filters jobs from /api/jobs

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";
import { JobItem } from "../types/api";

interface UseJobsParams {
  q?: string;
  domain?: string;
  remoteOnly?: boolean;
}

export function useJobs(params?: UseJobsParams) {
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchJobs() {
      setLoading(true);
      try {
        // Build query string
        const query = new URLSearchParams();
        if (params?.q) query.set("q", params.q);
        if (params?.domain) query.set("domain", params.domain);
        if (params?.remoteOnly) query.set("remote_only", "true");

        const queryString = query.toString();
        const path = queryString ? `/jobs?${queryString}` : "/jobs";

        const res = await apiGet<JobItem[]>(path);
        
        if (!cancelled) {
          setJobs(res);
          setLoading(false);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          console.error("Failed to fetch jobs:", e);
          setError(e instanceof Error ? e.message : "Unknown error");
          setLoading(false);
        }
      }
    }

    fetchJobs();

    // Optional: Re-fetch on interval if you want live updates
    // const id = setInterval(fetchJobs, 15000);
    // return () => {
    //   cancelled = true;
    //   clearInterval(id);
    // };

    return () => {
      cancelled = true;
    };
  }, [params?.q, params?.domain, params?.remoteOnly]);

  return { jobs, loading, error };
}
