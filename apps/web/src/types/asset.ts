export type AssetType =
  | "REFINERY"
  | "POWER_PLANT"
  | "PETROCHEMICAL"
  | "METALLURGICAL"
  | "PIPELINE"
  | "STORAGE_FACILITY"
  | "INDUSTRIAL_ZONE"
  | "AGRICULTURAL_PARCEL"
  | "OTHER";

export type ExposureLevel = "HIGH" | "MEDIUM" | "LOW" | "NO_ASSETS_DETECTED";

export interface IndustrialAsset {
  id: string;
  name: string;
  type: AssetType;
  distanceMeters: number | null;
  formattedDistance: string;
  exposureLevel: "HIGH" | "MEDIUM" | "LOW" | "NONE";
  sourceType: string;
  coordinates?: [number, number]; // [lat, lon]
}

export interface IndustrialContextSummary {
  eventId: string;
  assets: IndustrialAsset[];
  overallExposure: ExposureLevel;
  summary: string;
  hasAssetData: boolean;
  sourceAttribution: string;
}
