import { apiFetch } from "./client.ts";

export interface IndustrialAssetProperties {
  id: string;
  name: string;
  asset_type: string;
  industry: string;
  context_type: string;
  country: string;
  state?: string | null;
  district?: string | null;
  city?: string | null;
  operator?: string | null;
  owner?: string | null;
  status: string;
  capacity?: number | null;
  capacity_unit?: string | null;
  primary_fuel?: string | null;
  commissioning_year?: number | null;
  source: string;
  source_id?: string | null;
  linked_source_ids: string[];
  is_map_eligible: boolean;
  metadata?: Record<string, unknown>;
}

export interface IndustrialAssetFeature {
  type: "Feature";
  id: string;
  geometry: {
    type: "Point";
    coordinates: [number, number]; // [longitude, latitude] in EPSG:4326
  };
  properties: IndustrialAssetProperties;
}

export interface IndustrialAssetFeatureCollection {
  type: "FeatureCollection";
  features: IndustrialAssetFeature[];
  bbox?: [number, number, number, number];
}

export interface FetchIndustrialAssetsParams {
  min_lat?: number;
  max_lat?: number;
  min_lon?: number;
  max_lon?: number;
  bbox?: string;
  industry?: string;
  status?: string;
  state?: string;
  include_expansion?: boolean;
  limit?: number;
  offset?: number;
}

export const EMPTY_INDUSTRIAL_COLLECTION: IndustrialAssetFeatureCollection = {
  type: "FeatureCollection",
  features: [],
};

// In-memory response cache and inflight promise map to eliminate duplicate API requests
const assetCache = new Map<string, IndustrialAssetFeatureCollection>();
const inflightRequests = new Map<string, Promise<IndustrialAssetFeatureCollection>>();

/**
 * Clear the in-memory cache of industrial assets (useful for testing or manual refresh).
 */
export function clearIndustrialAssetsCache(): void {
  assetCache.clear();
  inflightRequests.clear();
}

/**
 * Validates and sanitizes an individual GeoJSON Feature to guarantee
 * that invalid coordinates, NaNs, or non-finite values never crash MapLibre or GlobeGL.
 */
export function isValidIndustrialFeature(feature: any): feature is IndustrialAssetFeature {
  if (!feature || feature.type !== "Feature" || !feature.geometry) {
    return false;
  }
  const coords = feature.geometry.coordinates;
  if (!Array.isArray(coords) || coords.length < 2) {
    return false;
  }
  const [lon, lat] = coords;
  if (
    typeof lon !== "number" ||
    typeof lat !== "number" ||
    Number.isNaN(lon) ||
    Number.isNaN(lat) ||
    !Number.isFinite(lon) ||
    !Number.isFinite(lat)
  ) {
    return false;
  }
  if (lon < -180 || lon > 180 || lat < -90 || lat > 90) {
    return false;
  }
  return true;
}

/**
 * Fetch normalized industrial assets as RFC 7946 GeoJSON FeatureCollection.
 * Deduplicates concurrent in-flight calls and caches responses in-memory.
 * Handles API failures gracefully by returning an empty collection with a safe warning.
 */
export async function fetchIndustrialAssetsGeoJson(
  params: FetchIndustrialAssetsParams = {}
): Promise<IndustrialAssetFeatureCollection> {
  const cacheKey = JSON.stringify({
    min_lat: params.min_lat,
    max_lat: params.max_lat,
    min_lon: params.min_lon,
    max_lon: params.max_lon,
    bbox: params.bbox,
    industry: params.industry,
    status: params.status,
    state: params.state,
    include_expansion: params.include_expansion ?? true,
    limit: params.limit ?? 2500,
    offset: params.offset ?? 0,
  });

  if (assetCache.has(cacheKey)) {
    return assetCache.get(cacheKey)!;
  }

  if (inflightRequests.has(cacheKey)) {
    return inflightRequests.get(cacheKey)!;
  }

  const fetchPromise = (async () => {
    try {
      const data = await apiFetch<IndustrialAssetFeatureCollection>(
        "/api/industrial-assets",
        {
          params: {
            min_lat: params.min_lat,
            max_lat: params.max_lat,
            min_lon: params.min_lon,
            max_lon: params.max_lon,
            bbox: params.bbox,
            industry: params.industry,
            status: params.status,
            state: params.state,
            include_expansion: params.include_expansion ?? true,
            limit: params.limit ?? 2500,
            offset: params.offset ?? 0,
          },
          timeoutMs: 10000,
        }
      );

      if (data && Array.isArray(data.features)) {
        // Defensive sanitization: reject malformed or out-of-range coordinates
        const sanitizedFeatures = data.features.filter(isValidIndustrialFeature);
        const result: IndustrialAssetFeatureCollection = {
          ...data,
          features: sanitizedFeatures,
        };
        assetCache.set(cacheKey, result);
        return result;
      }
      return EMPTY_INDUSTRIAL_COLLECTION;
    } catch (err) {
      console.warn(
        "fetchIndustrialAssetsGeoJson: API unavailable or failed. Returning empty collection gracefully:",
        err
      );
      return EMPTY_INDUSTRIAL_COLLECTION;
    } finally {
      inflightRequests.delete(cacheKey);
    }
  })();

  inflightRequests.set(cacheKey, fetchPromise);
  return fetchPromise;
}

export type IndustrialLayerId =
  | "global-power-plants"
  | "global-oil-gas-tracker"
  | "global-iron-steel-tracker"
  | "india-industrial-facilities";

/**
 * Maps an individual industrial asset feature to its authoritative GIS layer identifier.
 */
export function getIndustrialAssetLayerId(
  feature: IndustrialAssetFeature
): IndustrialLayerId {
  const p = feature.properties || {};
  const industry = p.industry?.toLowerCase() || "";
  const source = p.source?.toLowerCase() || "";
  const name = p.name?.toLowerCase() || "";

  // 1. Thermal & renewable power plants (WRI Power Database)
  if (
    industry === "power" ||
    source.includes("power") ||
    source.includes("wri")
  ) {
    return "global-power-plants";
  }

  // 2. Blast furnaces & metallurgy smelting facilities (GEM Iron & Steel Tracker)
  if (
    industry === "metallurgy" ||
    source.includes("steel") ||
    source.includes("iron")
  ) {
    return "global-iron-steel-tracker";
  }

  // 3. Heavy chemical facilities, refineries, and petrochemical parks (Master India Facilities)
  if (
    industry === "chemical" ||
    name.includes("refin") ||
    name.includes("petro") ||
    name.includes("chemical") ||
    name.includes("caustic") ||
    name.includes("bcpl") ||
    name.includes("ioc") ||
    name.includes("bpcl") ||
    name.includes("hpcl") ||
    name.includes("ongc") ||
    name.includes("gail") ||
    name.includes("reliance")
  ) {
    return "india-industrial-facilities";
  }

  // 4. Hydrocarbon extraction, gas terminals, and pipeline infrastructure (GEM Oil & Gas Tracker)
  return "global-oil-gas-tracker";
}

/**
 * Returns true if the given industrial asset should be rendered according to the active GIS layers.
 */
export function isIndustrialAssetVisible(
  feature: IndustrialAssetFeature,
  activeLayers?: Record<string, boolean>
): boolean {
  if (!activeLayers) return true;

  // Legacy master toggle fallback if explicitly disabled
  if (activeLayers["industrial"] === false) {
    return false;
  }

  const layerId = getIndustrialAssetLayerId(feature);
  // Independent layer visibility: if explicitly in activeLayers, check state; default to true
  return activeLayers[layerId] ?? true;
}

/**
 * Pure, in-memory filter that yields an updated GeoJSON FeatureCollection containing only
 * features whose corresponding industrial GIS layer is currently enabled.
 * Zero network round-trips, zero DOM thrashing.
 */
export function filterIndustrialAssetsByLayers(
  collection: IndustrialAssetFeatureCollection,
  activeLayers?: Record<string, boolean>
): IndustrialAssetFeatureCollection {
  if (!collection || !Array.isArray(collection.features)) {
    return EMPTY_INDUSTRIAL_COLLECTION;
  }
  if (!activeLayers) {
    return collection;
  }

  const filtered = collection.features.filter((f) =>
    isIndustrialAssetVisible(f, activeLayers)
  );

  return {
    ...collection,
    features: filtered,
  };
}
