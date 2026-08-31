import { GisLayerItem } from "@/types/layer";

export const APP_CONFIG = {
  name: "FLAME INTELLIGENCE",
  shortName: "SIH26",
  tagline: "Satellite Thermal Anomaly & Industrial Fire Intelligence",
  version: "v1.0.0",
  modelName: "production-classifier-b4",
  featureSchema: "feat_v1.0.0",
  defaultCenter: {
    lat: 22.4707,
    lon: 70.0577, // Jamnagar Industrial Cluster, India
    zoom: 6,
  },
};

export const INITIAL_LAYERS: GisLayerItem[] = [
  {
    id: "all_thermal",
    label: "All Thermal Events",
    category: "thermal",
    description: "Active clustered thermal anomalies from NASA FIRMS",
    icon: "Flame",
    enabled: true,
    color: "var(--thermal-primary)",
  },
  {
    id: "industrial",
    label: "Industrial Combustion",
    category: "classification",
    description: "Refinery flares, furnace stacks & industrial processes",
    icon: "Factory",
    enabled: true,
    color: "var(--accent-primary)",
  },
  {
    id: "non_industrial",
    label: "Vegetation / Agricultural",
    category: "classification",
    description: "Crop residue burning & wildland thermal events",
    icon: "Trees",
    enabled: true,
    color: "var(--state-warning)",
  },
  {
    id: "persistent_sources",
    label: "Persistent Sources",
    category: "thermal",
    description: "Longitudinal facilities with recurring thermal activity",
    icon: "RotateCw",
    enabled: false,
    color: "var(--accent-cyan)",
  },
  {
    id: "review_required",
    label: "Review Required",
    category: "classification",
    description: "Events with conflicting or low-confidence evidence",
    icon: "AlertTriangle",
    enabled: false,
    color: "var(--state-error)",
  },
  {
    id: "osm_infrastructure",
    label: "OSM Industrial Context",
    category: "context",
    description: "OpenStreetMap power plants, refineries & heavy industry",
    icon: "Building2",
    enabled: false,
    color: "var(--text-muted)",
  },
];
