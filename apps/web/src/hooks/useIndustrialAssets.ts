"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  fetchIndustrialAssetsGeoJson,
  IndustrialAssetFeatureCollection,
  EMPTY_INDUSTRIAL_COLLECTION,
  FetchIndustrialAssetsParams,
} from "@/lib/api/industrial";

export interface UseIndustrialAssetsResult {
  data: IndustrialAssetFeatureCollection;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

/**
 * React hook to fetch and manage industrial asset GeoJSON data asynchronously.
 * Does not block initial map rendering and fails gracefully if the API is offline.
 */
export function useIndustrialAssets(
  params?: FetchIndustrialAssetsParams
): UseIndustrialAssetsResult {
  const [data, setData] = useState<IndustrialAssetFeatureCollection>(
    EMPTY_INDUSTRIAL_COLLECTION
  );
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const paramsRef = useRef(params);
  paramsRef.current = params;

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await fetchIndustrialAssetsGeoJson(paramsRef.current);
      setData(result);
    } catch (err) {
      const e = err instanceof Error ? err : new Error(String(err));
      setError(e);
      setData(EMPTY_INDUSTRIAL_COLLECTION);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;

    fetchIndustrialAssetsGeoJson(paramsRef.current)
      .then((result) => {
        if (isMounted) {
          setData(result);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          const e = err instanceof Error ? err : new Error(String(err));
          setError(e);
          setData(EMPTY_INDUSTRIAL_COLLECTION);
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return {
    data,
    isLoading,
    error,
    refetch: loadData,
  };
}
