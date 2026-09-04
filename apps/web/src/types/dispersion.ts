/**
 * Canonical TypeScript types for Atmospheric Dispersion & Downwind Hazard Intelligence (Phase 3 & 4).
 */

import type { Coordinate, DataQuality, WindVector } from "./weather";

export type PasquillStabilityClass = "A" | "B" | "C" | "D" | "E" | "F";

export interface DispersionSamplePoint {
  downwind_distance_km: number;
  centerline_point: Coordinate;
  left_boundary_point: Coordinate;
  right_boundary_point: Coordinate;
  sigma_y_m: number;
  sigma_z_m: number;
  lateral_width_km: number;
  relative_concentration: number;
}

export interface DispersionSummary {
  model_name: string;
  is_engineering_approximation: boolean;
  stability_class: PasquillStabilityClass;
  stability_rationale: string;
  effective_release_height_m: number;
  source_strength_proxy: number;
  max_hazard_distance_km: number;
  max_hazard_width_km: number;
  plume_angle_deg: number;
  calm_stagnation_flag: boolean;
}

export interface AtmosphericDispersionResult {
  source_location: Coordinate;
  event_id: string | null;
  evaluated_at: string;
  wind: WindVector;
  dispersion: DispersionSummary;
  trajectory: DispersionSamplePoint[];
  data_quality: DataQuality;
  model_confidence: string;
}

export type DispersionCalculationResponse = AtmosphericDispersionResult;

export interface PlumeHazardFeatureProperties {
  label: string;
  hazard_level?: string;
  max_distance_km?: number;
  max_width_km?: number;
  bearing_deg?: number;
  stability_class?: string;
  is_calm?: boolean;
  data_quality?: DataQuality;
  model_confidence?: string;
}

export interface PlumeHazardGeoJson {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    id?: string;
    geometry: {
      type: "Polygon" | "LineString" | "Point";
      coordinates: any;
    };
    properties: PlumeHazardFeatureProperties;
  }>;
}
