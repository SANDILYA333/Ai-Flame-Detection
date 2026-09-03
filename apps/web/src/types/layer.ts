/**
 * Layer & GIS taxonomy contracts matching backend routes/layers.py and routes/gis_layers.py
 */

export type LayerCategory =
  | "thermal"
  | "classification"
  | "context"
  | "infrastructure"
  | "hazard"
  | "benchmark"
  | "responders"
  | "geospatial"
  | "environment";

export interface GisLayerItem {
  id: string;
  label: string;
  category: LayerCategory;
  description: string;
  icon: string;
  count?: number;
  enabled: boolean;
  color?: string;
}
