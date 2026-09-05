"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { fetchEventMedia } from "@/lib/api/media";
import type { ContextualMediaResponse } from "@/types/media";

const mediaCache = new Map<string, ContextualMediaResponse>();

export interface UseEventMediaResult {
  media: ContextualMediaResponse | null;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useEventMedia(eventId: string | null | undefined): UseEventMediaResult {
  const [media, setMedia] = useState<ContextualMediaResponse | null>(() => {
    if (eventId && mediaCache.has(eventId)) {
      return mediaCache.get(eventId)!;
    }
    return null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const loadMedia = useCallback(async (id: string, force = false) => {
    if (!force && mediaCache.has(id)) {
      setMedia(mediaCache.get(id)!);
      setIsLoading(false);
      setIsError(false);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setIsError(false);
    setError(null);

    try {
      const res = await fetchEventMedia(id, controller.signal);
      mediaCache.set(id, res);
      setMedia(res);
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      setIsError(true);
      setError(err instanceof Error ? err : new Error("Failed to load contextual media"));
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!eventId) {
      setMedia(null);
      setIsLoading(false);
      setIsError(false);
      return;
    }

    loadMedia(eventId);

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [eventId, loadMedia]);

  const refetch = useCallback(async () => {
    if (eventId) {
      await loadMedia(eventId, true);
    }
  }, [eventId, loadMedia]);

  return {
    media,
    isLoading,
    isError,
    error,
    refetch,
  };
}
