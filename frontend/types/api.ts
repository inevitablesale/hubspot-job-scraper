/**
 * TypeScript type definitions for the API
 * 
 * These types match the Pydantic models in the backend.
 */

export type CrawlState = 'idle' | 'running' | 'stopping' | 'error' | 'finished';

export interface CrawlSummary {
  state: CrawlState;
  last_run_started_at: string | null;
  last_run_finished_at: string | null;
  domains_total: number;
  domains_completed: number;
  jobs_found: number;
  errors_count: number;
}

export type EventLevel = 'info' | 'warning' | 'error';

export type EventType =
  | 'domain_started'
  | 'domain_finished'
  | 'career_page_found'
  | 'job_extracted'
  | 'error'
  | 'log';

export interface CrawlEvent {
  id: string;
  ts: string;
  level: EventLevel;
  type: EventType;
  domain?: string;
  message: string;
  metadata: Record<string, any>;
}

export type LogLevel = 'debug' | 'info' | 'warning' | 'error';

export interface LogLine {
  ts: string;
  level: LogLevel;
  message: string;
  domain?: string;
  source: 'crawler' | 'system';
}

export type RemoteType = 'remote' | 'hybrid' | 'office';

export interface JobItem {
  id: string;
  domain: string;
  title: string;
  location?: string;
  remote_type?: RemoteType;
  url: string;
  source_page: string;
  ats?: string;
  created_at: string;
}

export interface DomainItem {
  domain: string;
  category?: string;
  blacklisted: boolean;
  last_scraped_at?: string;
  career_page?: string;
  ats?: string;
  jobs_count: number;
  status?: string;
}

export interface ConfigSettings {
  dark_mode_default: 'system' | 'light' | 'dark';
  max_pages_per_domain: number;
  max_depth: number;
  blacklist_domains: string[];
  allowed_categories: string[];
  role_filters: string[];
  remote_only: boolean;
}

export interface NavigationFlowStep {
  step: number;
  url: string;
  type: string;
  timestamp?: string;
  screenshot?: string;
  jobs_found: number;
  metadata: Record<string, any>;
}

export interface ScreenshotInfo {
  filename: string;
  url: string;
  step: number;
  timestamp: string;
  description?: string;
}

export interface StartCrawlRequest {
  role_filter?: string;
  remote_only?: boolean;
}

export interface StartCrawlResponse {
  ok: boolean;
  reason?: string;
  message?: string;
}
