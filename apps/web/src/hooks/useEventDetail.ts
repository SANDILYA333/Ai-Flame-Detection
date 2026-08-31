"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchEventDetail,
  fetchEventTimeline,
  fetchEventEvidence,
  fetchEventIntelligence,
} from "@/lib/api/events";
import { ApiClientError } from "@/lib/api/client";
import type {
  EventDetailResponse,
  EventTimelineResponse,
  EventEvidenceResponse,
} from "@/types/event";
import type { IntelligenceResult } from "@/types/intelligence";

export interface UseEventDetailResult {
  detail: EventDetailResponse | null;
  timeline: EventTimelineResponse | null;
  evidence: EventEvidenceResponse | null;
  intelligence: IntelligenceResult | null;
  isLoading: boolean;
  isError: boolean;
  error: ApiClientError | null;
  refetch: () => Promise<void>;
}

export function useEventDetail(eventId: string | null | undefined): UseEventDetailResult {
  const [detail, setDetail] = useState<EventDetailResponse | null>(null);
  const [timeline, setTimeline] = useState<EventTimelineResponse | null>(null);
  const [evidence, setEvidence] = useState<EventEvidenceResponse | null>(null);
  const [intelligence, setIntelligence] = useState<IntelligenceResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isError, setIsError] = useState<boolean>(false);
  const [error, setError] = useState<ApiClientError | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const loadData = useCallback(async (id: string) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setIsError(false);
    setError(null);

    try {
      const [detailRes, timelineRes, evidenceRes, intelligenceRes] = await Promise.allSettled([
        fetchEventDetail(id, controller.signal),
        fetchEventTimeline(id, controller.signal),
        fetchEventEvidence(id, controller.signal),
        fetchEventIntelligence(id, controller.signal),
      ]);

      if (detailRes.status === "fulfilled") setDetail(detailRes.value);
      if (timelineRes.status === "fulfilled") setTimeline(timelineRes.value);
      if (evidenceRes.status === "fulfilled") setEvidence(evidenceRes.value);
      if (intelligenceRes.status === "fulfilled") setIntelligence(intelligenceRes.value);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      const clientError =
        err instanceof ApiClientError
          ? err
          : new ApiClientError({
              message: err instanceof Error ? err.message : "Failed to load event intelligence",
              status: 0,
              statusText: "Unknown Error",
            });
      setIsError(true);
      setError(clientError);
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!eventId) {
      setDetail(null);
      setTimeline(null);
      setEvidence(null);
      setIntelligence(null);
      setIsLoading(false);
      setIsError(false);
      return;
    }

    loadData(eventId);

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [eventId, loadData]);

  const refetch = useCallback(async () => {
    if (eventId) {
      await loadData(eventId);
    }
  }, [eventId, loadData]);

  return {
    detail,
    timeline,
    evidence,
    intelligence,
    isLoading,
    isError,
    error,
    refetch,
  };
}
