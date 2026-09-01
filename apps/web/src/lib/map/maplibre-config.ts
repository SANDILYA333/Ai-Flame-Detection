/**
 * 2D MapLibre GL Basemap Configuration
 * Keyless, watermark-free dark intelligence styles with environment variable adaptability.
 */

function resolveStyleUrl(): string {
  if (typeof process !== "undefined" && process.env) {
    if (process.env.NEXT_PUBLIC_MAP_STYLE_URL) {
      return process.env.NEXT_PUBLIC_MAP_STYLE_URL;
    }
    if (process.env.NEXT_PUBLIC_MAPTILER_KEY) {
      return `https://api.maptiler.com/maps/dataviz-dark/style.json?key=${process.env.NEXT_PUBLIC_MAPTILER_KEY}`;
    }
  }
  // Default: CARTO Dark Matter Vector - 100% Free, Keyless, Open Source, High-DPI Vector Cartography
  return "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
}

export const MAPLIBRE_CONFIG = {
  // Primary Dark Vector Basemap (CARTO Dark Matter)
  style: resolveStyleUrl(),

  // Secondary Dark Vector Basemap (OpenFreeMap)
  openFreeMapStyle: "https://tiles.openfreemap.org/styles/dark",

  // Fallback Raster Basemap (ESRI World Dark Gray Canvas - 100% Keyless)
  fallbackStyle: {
    version: 8 as const,
    name: "ESRI Dark Gray Canvas",
    sources: {
      "esri-dark": {
        type: "raster" as const,
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        attribution: "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ",
      },
      "esri-dark-ref": {
        type: "raster" as const,
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
      },
    },
    layers: [
      {
        id: "esri-dark-base",
        type: "raster" as const,
        source: "esri-dark",
        minzoom: 0,
        maxzoom: 19,
      },
      {
        id: "esri-dark-labels",
        type: "raster" as const,
        source: "esri-dark-ref",
        minzoom: 0,
        maxzoom: 19,
        paint: {
          "raster-opacity": 0.65,
        },
      },
    ],
  },

  // Initial geographic center: Global Overview / Jamnagar Anchor
  initialCenter: [70.0577, 22.4707] as [number, number], // [lng, lat]
  initialZoom: 4.5,
  minZoom: 1.5,
  maxZoom: 18,
};
