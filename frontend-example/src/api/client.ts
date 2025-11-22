// API Client for HubSpot Job Scraper
// Provides HTTP and SSE utilities for frontend integration

export const API_BASE = "/api";

/**
 * Generic GET request
 */
export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Generic POST request
 */
export async function apiPost<T>(path: string, body?: any): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    throw new Error(`POST ${path} failed: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Generic PUT request
 */
export async function apiPut<T>(path: string, body: any): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`PUT ${path} failed: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Create an EventSource for SSE
 */
export function createEventSource(path: string): EventSource {
  return new EventSource(`${API_BASE}${path}`);
}
