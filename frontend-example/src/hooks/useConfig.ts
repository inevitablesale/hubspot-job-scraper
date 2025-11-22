// React hook for configuration
// Fetches and updates config from /api/config

import { useEffect, useState } from "react";
import { apiGet, apiPut } from "../api/client";
import { ConfigSettings } from "../types/api";

export function useConfig() {
  const [config, setConfig] = useState<ConfigSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchConfig() {
      try {
        const res = await apiGet<ConfigSettings>("/config");
        if (!cancelled) {
          setConfig(res);
          setLoading(false);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) {
          console.error("Failed to fetch config:", e);
          setError(e instanceof Error ? e.message : "Unknown error");
          setLoading(false);
        }
      }
    }

    fetchConfig();

    return () => {
      cancelled = true;
    };
  }, []);

  async function updateConfig(nextConfig: ConfigSettings) {
    setUpdating(true);
    try {
      const res = await apiPut<ConfigSettings>("/config", nextConfig);
      setConfig(res);
      setError(null);
    } catch (e) {
      console.error("Failed to update config:", e);
      setError(e instanceof Error ? e.message : "Failed to update config");
      throw e;
    } finally {
      setUpdating(false);
    }
  }

  return { config, loading, error, updating, updateConfig };
}
