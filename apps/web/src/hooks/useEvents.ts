"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { fetchEvents } from "@/lib/api/events";
import { ApiClientError } from "@/lib/api/client";
import type {
  EventsQueryParams,
  EventsResponse,
  BackendEventItem,
  EventPagination,
} from "@/types/event";

export interface UseEventsOptions {
  enabled?: boolean;
  refetchInterval?: number; // In milliseconds
  initialData?: EventsResponse;
}

export interface UseEventsResult {
  data: EventsResponse | null;
  events: BackendEventItem[];
  pagination: EventPagination | null;
  isLoading: boolean; // Initial load when no data exists
  isFetching: boolean; // Background refresh / active request
  isError: boolean;
  error: ApiClientError | null;
  refetch: () => Promise<void>;
}

/**
 * Canonical React hook for retrieving and caching thermal events from the FastAPI backend
 */
export function useEvents(
  params: EventsQueryParams = {},
  options: UseEventsOptions = {}
): UseEventsResult {
  const { enabled = true, refetchInterval, initialData } = options;

  const [data, setData] = useState<EventsResponse | null>(initialData ?? null);
  const [isLoading, setIsLoading] = useState<boolean>(!initialData && enabled);
  const [isFetching, setIsFetching] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);
  const [error, setError] = useState<ApiClientError | null>(null);

  // Stable stringified query key to avoid unnecessary refetches
  const paramsKey = JSON.stringify(params);
  const activeAbortControllerRef = useRef<AbortController | null>(null);

  const executeFetch = useCallback(
    async (isBackground = false) => {
      if (!enabled) return;

      // Abort any ongoing request before starting a new one
      if (activeAbortControllerRef.current) {
        activeAbortControllerRef.current.abort();
      }

      const controller = new AbortController();
      activeAbortControllerRef.current = controller;

      if (!isBackground) {
        setIsLoading(true);
      }
      setIsFetching(true);

      try {
        const parsedParams: EventsQueryParams = JSON.parse(paramsKey);
        const result = await fetchEvents(parsedParams, controller.signal);

        setData(result);
        setIsError(false);
        setError(null);
      } catch (err) {
        // Ignore aborted requests
        if (err instanceof DOMException && err.name === "AbortError") {
          return;
        }

        const clientError =
          err instanceof ApiClientError
            ? err
            : new ApiClientError({
                message: err instanceof Error ? err.message : "Failed to fetch events",
                status: 0,
                statusText: "Unknown Error",
              });

        setIsError(true);
        setError(clientError);
      } finally {
        setIsLoading(false);
        setIsFetching(false);
        activeAbortControllerRef.current = null;
      }
    },
    [enabled, paramsKey]
  );

  // Initial fetch and param change listener
  useEffect(() => {
    executeFetch(false);

    return () => {
      if (activeAbortControllerRef.current) {
        activeAbortControllerRef.current.abort();
      }
    };
  }, [executeFetch]);

  // Periodic polling interval
  useEffect(() => {
    if (!enabled || !refetchInterval || refetchInterval <= 0) return;

    const intervalId = setInterval(() => {
      executeFetch(true);
    }, refetchInterval);

    return () => clearInterval(intervalId);
  }, [enabled, refetchInterval, executeFetch]);

  const refetch = useCallback(async () => {
    await executeFetch(true);
  }, [executeFetch]);

  return {
    data,
    events: data?.events ?? [],
    pagination: data?.pagination ?? null,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  };
}
