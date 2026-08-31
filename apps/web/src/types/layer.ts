/**
 * Layer & GIS taxonomy contracts matching backend routes/layers.py
 */

export type LayerCategory = "thermal" | "classification" | "context" | "infrastructure";

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
