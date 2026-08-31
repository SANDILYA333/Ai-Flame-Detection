# 🏛️ PyroSat-AI — System Architecture & Technical Specification

## 1. System Overview & Invariants

PyroSat-AI is engineered as a modular, high-throughput geospatial intelligence system designed to ingest, process, classify, and visualize satellite thermal telemetry in real time.

### Core Architectural Invariants:
1. **Zero Unclassified Raw Telemetry**: No thermal detection reaches the end-user interface without being evaluated through physical pyrometry and multi-modal feature classification.
2. **Deterministic Physical Grounding**: Pure AI predictions are strictly validated against Planck radiation constraints and historical facility baselines.
3. **Sub-Second Real-Time Latency**: End-to-end processing (from raw VIIRS CSV string to spatial matching, inference, and plume generation) executes in $<350\text{ ms}$.
4. **Resilient Offline Fallback**: In case of network interruptions, pre-seeded deterministic historical scenarios provide zero-latency continuity.

---

## 2. Multi-Tier Architecture Blueprint

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PRESENTATION LAYER                                     │
│  React 19 + TypeScript + Leaflet GIS + Tailwind CSS (Port 5175)                        │
│  • Multi-Layer Basemap Switcher (Dark Canvas, OSM, High-Res Satellite)                 │
│  • Dynamic Downwind Plume Overlay & Evacuation Perimeter Circle                        │
│  • 30-Day Spatiotemporal Timeline Scrubber & Automated Playback Engine                 │
│  • Interactive Category Pills, Multi-Criteria Filters, Real-Time Search                │
│  • Tactical First Responder HAZMAT Dossier Modal & 1-Click PDF Exporter                │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTP / REST API (JSON & GeoJSON)
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                             FASTAPI APPLICATION GATEWAY                                │
│  Uvicorn REST Server (Port 8000) — backend/server.py                                   │
│  • GET  /api/thermal-events       ── In-Memory Precomputed Telemetry Cache             │
│  • GET  /api/live-firms           ── Real-Time NASA VIIRS 375m NRT Stream Ingestion    │
│  • POST /api/classify             ── Ad-Hoc On-Demand Coordinate Inference             │
│  • GET  /api/incident-dossier/:id ── Dynamic ReportLab PDF Action Dossier Generator    │
│  • GET  /api/emergency-services   ── Spatial Nearest Emergency Provider Locator        │
│  • GET  /api/historical-scenarios ── Ground-Truth Evaluator Benchmark Cases            │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
        ┌───────────────────────────────────┼───────────────────────────────────┐
        ▼                                   ▼                                   ▼
┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────────┐
│   GEOSPATIAL ENGINES  │   │  PHYSICAL PYROMETRY   │   │  MACHINE LEARNING &   │
│                       │   │                       │   │    EXPLAINABILITY     │
│ • Spatial BallTree    │   │ • Dozier Subpixel     │   │ • 6-Class Random      │
│   1,704 Indian Plants │   │   Planck Inversion    │   │   Forest Ensemble     │
│ • 10m LULC Land-Cover │   │ • Flame Temp (K) &    │   │ • 91.4% F1-Score      │
│   Fraction Aggregator │   │   Fire Area (m²)      │   │ • Feature SHAP /      │
│ • OSM Emergency Index │   │ • 90-Day Baseline &   │   │   Physics Evidence    │
│   Fire/Hospitals/NDRF │   │   FRP Z-Score Surges  │   │   Extraction          │
└───────────────────────┘   └───────────────────────┘   └───────────────────────┘
        │                                   │                                   │
        └───────────────────────────────────┼───────────────────────────────────┘
                                            │
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                            METEOROLOGICAL & HAZMAT LAYER                               │
│  • Open-Meteo REST API: Live 10m Wind Speed (km/h) & Compass Bearing (Deg)             │
│  • Gaussian Toxic Plume Model: Dynamic Downwind Dispersion Polygon Geometry            │
│  • CAMEO Chemicals & NIOSH Database: UN Number, Reactivity, Toxic Byproducts          │
│  • ERG 2024 Emergency Response Guidebook: Initial Isolation & Evacuation Radii         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow & Execution Sequence

1. **Ingestion**: Raw thermal points $(lat, lon, MWIR, LWIR, FRP, DayNight)$ are ingested via live NASA FIRMS VIIRS stream or precomputed benchmark datasets.
2. **Spatial Attribution**: `SpatialIntelligenceEngine` performs a $k$-d tree query against 1,704 geocoded Indian facilities to calculate exact distance ($\text{km}$) to the nearest industrial asset.
3. **LULC Environmental Footprint**: `LULCEngine` extracts land-cover fractions (Built-up %, Forest %, Cropland %, Water %).
4. **Physical Pyrometry Inversion**: `planck_pyrometry.py` solves non-linear dual-band radiance equations to calculate $T_{\text{flame}} (\text{K})$ and $A_{\text{flame}} (\text{m}^2)$.
5. **Temporal Baseline Surge**: `spatiotemporal_engine.py` checks historical recurrence and calculates the FRP surge multiplier ($z$-score).
6. **Hierarchical AI Classification**: `HierarchicalThermalClassifier` generates calibrated class probabilities and confidence bands.
7. **Downwind Dispersion**: For accidental blazes, `weather_plume_engine.py` calls Open-Meteo and projects the toxic plume polygon.
8. **Emergency Routing & Dossier**: `SpatialEmergencyMatcher` queries nearest Fire Commands and ICU Trauma Centers, ready for 1-click PDF export.
