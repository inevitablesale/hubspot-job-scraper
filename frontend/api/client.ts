/**
 * API Client for HubSpot Job Scraper
 * 
 * Provides production-grade HTTP and SSE utilities with:
 * - Error handling and retry logic
 * - Request/response interceptors
 * - Type safety
 * - Cancellation support
 */

const API_BASE = '/api';

interface RequestConfig extends RequestInit {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

/**
 * Create an AbortController with timeout
 */
function createTimeoutController(timeout: number): AbortController {
  const controller = new AbortController();
  setTimeout(() => controller.abort(), timeout);
  return controller;
}

/**
 * Retry helper with exponential backoff
 */
async function retryRequest<T>(
  fn: () => Promise<T>,
  retries: number,
  delay: number
): Promise<T> {
  try {
    return await fn();
  } catch (error) {
    if (retries <= 0) throw error;
    
    // Don't retry client errors (4xx) except 408, 429
    if (error instanceof APIError && error.status) {
      if (error.status >= 400 && error.status < 500 && 
          error.status !== 408 && error.status !== 429) {
        throw error;
      }
    }
    
    await new Promise(resolve => setTimeout(resolve, delay));
    return retryRequest(fn, retries - 1, delay * 2);
  }
}

/**
 * Generic request handler
 */
async function request<T>(
  path: string,
  config: RequestConfig = {}
): Promise<T> {
  const {
    timeout = 30000,
    retries = 2,
    retryDelay = 1000,
    ...fetchConfig
  } = config;

  const makeRequest = async () => {
    const controller = timeout > 0 
      ? createTimeoutController(timeout)
      : undefined;

    const response = await fetch(`${API_BASE}${path}`, {
      ...fetchConfig,
      signal: controller?.signal,
      headers: {
        'Content-Type': 'application/json',
        ...fetchConfig.headers,
      },
    });

    if (!response.ok) {
      const errorBody = await response.text().catch(() => '');
      throw new APIError(
        `Request failed: ${response.statusText}`,
        response.status,
        errorBody
      );
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type');
    if (!contentType?.includes('application/json')) {
      return {} as T;
    }

    return response.json();
  };

  return retryRequest(makeRequest, retries, retryDelay);
}

/**
 * GET request
 */
export async function apiGet<T>(
  path: string,
  config?: RequestConfig
): Promise<T> {
  return request<T>(path, { ...config, method: 'GET' });
}

/**
 * POST request
 */
export async function apiPost<T>(
  path: string,
  body?: any,
  config?: RequestConfig
): Promise<T> {
  return request<T>(path, {
    ...config,
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * PUT request
 */
export async function apiPut<T>(
  path: string,
  body: any,
  config?: RequestConfig
): Promise<T> {
  return request<T>(path, {
    ...config,
    method: 'PUT',
    body: JSON.stringify(body),
  });
}

/**
 * DELETE request
 */
export async function apiDelete<T>(
  path: string,
  config?: RequestConfig
): Promise<T> {
  return request<T>(path, { ...config, method: 'DELETE' });
}

/**
 * Server-Sent Events client with auto-reconnect
 */
export class SSEClient {
  private eventSource: EventSource | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private isManualClose = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;

  constructor(
    private path: string,
    private onConnected?: () => void,
    private onDisconnected?: () => void,
    private onError?: (error: Event) => void
  ) {}

  /**
   * Connect to SSE endpoint
   */
  connect(): void {
    this.isManualClose = false;
    this.createEventSource();
  }

  /**
   * Disconnect from SSE endpoint
   */
  disconnect(): void {
    this.isManualClose = true;
    this.cleanup();
  }

  /**
   * Subscribe to an event type
   */
  on(event: string, handler: (data: any) => void): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.listeners.get(event);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.listeners.delete(event);
        }
      }
    };
  }

  /**
   * Get connection state
   */
  isConnected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }

  private createEventSource(): void {
    try {
      this.eventSource = new EventSource(`${API_BASE}${this.path}`);

      this.eventSource.onopen = () => {
        this.reconnectAttempts = 0;
        this.onConnected?.();
      };

      this.eventSource.onerror = (error) => {
        this.onDisconnected?.();
        this.onError?.(error);

        // Auto-reconnect unless manually closed
        if (!this.isManualClose) {
          this.scheduleReconnect();
        }
      };

      // Register listeners for all event types
      this.listeners.forEach((handlers, event) => {
        this.eventSource!.addEventListener(event, (e: MessageEvent) => {
          try {
            const data = JSON.parse(e.data);
            handlers.forEach(handler => handler(data));
          } catch (error) {
            console.error(`Failed to parse SSE event ${event}:`, error);
          }
        });
      });

    } catch (error) {
      console.error('Failed to create EventSource:', error);
      if (!this.isManualClose) {
        this.scheduleReconnect();
      }
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts),
      this.maxReconnectDelay
    );

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.cleanup();
      this.createEventSource();
    }, delay);
  }

  private cleanup(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

/**
 * Create and manage an SSE connection
 */
export function createSSEClient(
  path: string,
  options?: {
    onConnected?: () => void;
    onDisconnected?: () => void;
    onError?: (error: Event) => void;
  }
): SSEClient {
  return new SSEClient(
    path,
    options?.onConnected,
    options?.onDisconnected,
    options?.onError
  );
}

export { APIError };
