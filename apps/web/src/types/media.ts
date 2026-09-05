/**
 * Contextual External Intelligence, News & Video briefing types (API-007)
 */

export type CorroborationType =
  | "OFFICIAL_DISPATCH"
  | "REGIONAL_COVERAGE"
  | "POTENTIALLY_RELEVANT"
  | "UNVERIFIED";

export interface ContextualNewsItem {
  id: string;
  title: string;
  source: string;
  published_at: string;
  url: string;
  snippet: string;
  relevance_score: number;
  corroboration_type: CorroborationType;
}

export interface ContextualVideoItem {
  id: string;
  youtube_id: string;
  title: string;
  channel_title: string;
  published_at: string;
  thumbnail_url: string;
  description: string;
}

export interface QueryContext {
  location_query: string;
  classification: string;
  facility_name?: string | null;
  temporal_window: string;
}

export interface ContextualMediaResponse {
  event_id: string;
  query_context: QueryContext;
  news: ContextualNewsItem[];
  videos: ContextualVideoItem[];
  disclaimer: string;
  is_live_service: boolean;
}
