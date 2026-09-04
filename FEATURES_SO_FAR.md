# Comprehensive Project Feature Inventory (`FEATURES_SO_FAR.md`)

> **Authoritative, Grounded Record of All Implemented Features & System Capabilities**  
> **Repository:** `SANDILYA333/Ai-Flame-Detection` (SIH26162)  
> **Date:** September 2026  
> **Target Audience:** Developers, Evaluators, Judges, Technical Teammates, and AI Coding Agents  

---

## Executive Overview

The **Satellite Thermal Anomaly & Flame Intelligence System (SIH26162)** is an end-to-end, multi-sensor geospatial and artificial intelligence platform designed to ingest satellite thermal detections (NASA FIRMS VIIRS/MODIS), perform physics-grounded pyrometry and atmospheric dispersion modeling, run calibrated machine learning inference to segregate industrial flaring from non-industrial wildfires/agricultural burns, assess proximity risks to forests and industrial assets, and orchestrate multi-channel emergency responder dispatches.

This document serves as the **single source of truth** for all capabilities implemented in the active codebase. Every feature listed here is verified against actual source code, endpoints, database migrations, mathematical formulations, and user interface components.

---

## High-Level Feature Inventory Summary

| # | Feature Name | Primary Category | Implementation Status | User Facing? | Key Evidence |
|---|---|---|---|---|---|
| **1** | [NASA FIRMS Thermal Observation Ingestion](#feature-1-nasa-firms-thermal-observation-ingestion) | Data & Satellite | `Implemented` | Yes (via API & Feed) | `packages/data/firms/parser.py`, `services/api/routes/detections.py` |
| **2** | [Industrial Asset & Ground Truth Cataloging](#feature-2-industrial-asset--ground-truth-cataloging) | Data & Context | `Implemented` | Yes (GIS Overlay) | `packages/context/ground_truth.py`, `packages/schemas/source.py` |
| **3** | [Global Forest & Protected Area Spatial Ingestion](#feature-3-global-forest--protected-area-spatial-ingestion) | Data & Forests | `Implemented` | Yes (Forest Hub) | `packages/data/forests/service.py`, `alembic/versions/0009_forest_areas.py` |
| **4** | [Automated Ingestion Quality Auditing & Quarantine](#feature-4-automated-ingestion-quality-auditing--quarantine) | Data Quality | `Implemented` | Internal / Backend Only | `packages/data/quality/auditor.py`, `packages/data/quality/rules.py` |
| **5** | [Point-in-Time Supervised Feature Engineering](#feature-5-point-in-time-supervised-feature-engineering) | AI / ML Intelligence | `Implemented` | Internal / Backend Only | `services/ml/features/extractor.py`, `services/ml/features/standard_set.py` |
| **6** | [Multi-Model Machine Learning Classification Engine](#feature-6-multi-model-machine-learning-classification-engine) | AI / ML Intelligence | `Implemented` | Yes (Prediction API) | `services/ml/models/tree.py`, `services/ml/training/real_trainer.py` |
| **7** | [Calibrated Abstention & Operating Mode Policy](#feature-7-calibrated-abstention--operating-mode-policy) | AI / ML Intelligence | `Implemented` | Yes (Runtime API) | `services/ml/deployment/policy.py`, `services/ml/calibration/abstention.py` |
| **8** | [SHAP Explainability & Feature Attribution Engine](#feature-8-shap-explainability--feature-attribution-engine) | AI / ML Intelligence | `Implemented` | Yes (XAI Panel) | `services/ml/explainability/shap_explainer.py`, `apps/web/src/lib/xai/explainer.ts` |
| **9** | [Spatiotemporal DBSCAN Event Clustering](#feature-9-spatiotemporal-dbscan-event-clustering) | Fire / Thermal | `Implemented` | Yes (Map & Feeds) | `packages/events/clustering.py`, `packages/events/pipeline.py` |
| **10** | [Planck / Dozier Dual-Band Pyrometry Solver](#feature-10-planck--dozier-dual-band-pyrometry-solver) | Physics & Thermal | `Implemented` | Yes (Pyrometry Card) | `packages/physics/pyrometry.py`, `apps/web/src/components/events/PlanckPyrometrySection.tsx` |
| **11** | [Temporal Persistence & Recurrence Intelligence](#feature-11-temporal-persistence--recurrence-intelligence) | Fire / Thermal | `Implemented` | Yes (Historical Curve) | `packages/sources/tracking.py`, `services/api/routes/historical.py` |
| **12** | [Dual-Engine 2D/3D Geospatial Mission Canvas](#feature-12-dual-engine-2d3d-geospatial-mission-canvas) | GIS / Mapping | `Implemented` | Yes (Core UI) | `apps/web/src/components/map/MapWorkspace.tsx`, `FlatMapView.tsx`, `GlobeView.tsx` |
| **13** | [12 GIS Layer Catalog & GeoJSON Streaming](#feature-13-12-gis-layer-catalog--geojson-streaming) | GIS / Mapping | `Implemented` | Yes (Layer Panel) | `services/api/routes/layers.py`, `apps/web/src/components/map/LayerPanel.tsx` |
| **14** | [Interactive Temporal Playback & Scrubbing](#feature-14-interactive-temporal-playback--scrubbing) | GIS / Timeline | `Implemented` | Yes (Bottom Bar) | `apps/web/src/components/playback/TimelinePlaybackBar.tsx`, `EventContext.tsx` |
| **15** | [Real-Time Open-Meteo Weather & Wind Engine](#feature-15-real-time-open-meteo-weather--wind-engine) | Weather / Wind | `Implemented` | Yes (Weather API) | `packages/data/weather/open_meteo.py`, `packages/physics/wind.py` |
| **16** | [Wind Vector Compass & Threat Analysis](#feature-16-wind-vector-compass--threat-analysis) | Weather / Wind | `Implemented` | Yes (Wind Card) | `apps/web/src/components/events/WindVectorCard.tsx`, `services/api/routes/weather.py` |
| **17** | [Gaussian Plume Atmospheric Dispersion Modeling](#feature-17-gaussian-plume-atmospheric-dispersion-modeling) | Atmospheric Hazard | `Implemented` | Yes (Plume Map Layer) | `packages/physics/dispersion.py`, `services/api/routes/dispersion.py` |
| **18** | [CAMEO-NIOSH Toxic Hazmat Chemical Profiling](#feature-18-cameo-niosh-toxic-hazmat-chemical-profiling) | Hazmat Intelligence | `Implemented` | Yes (Hazmat Card) | `services/api/routes/hazmat.py`, `apps/web/src/components/events/HazmatRiskCard.tsx` |
| **19** | [PostGIS Geodesic Forest Threat Assessment](#feature-19-postgis-geodesic-forest-threat-assessment) | Forest Intelligence | `Implemented` | Yes (Forest Card) | `packages/data/forests/threat_service.py`, `packages/geospatial/polygon_distance.py` |
| **20** | [Global Forest Monitoring Hub & Threat Drawer](#feature-20-global-forest-monitoring-hub--threat-drawer) | Forest Intelligence | `Implemented` | Yes (Dedicated Hub) | `apps/web/src/components/events/GlobalForestMonitoringHub.tsx`, `ForestThreatDetailDrawer.tsx` |
| **21** | [Multi-Agency Emergency Responder Discovery](#feature-21-multi-agency-emergency-responder-discovery) | Emergency Response | `Implemented` | Yes (Response Modal) | `services/api/services/responders.py`, `EmergencyResponseSection.tsx` |
| **22** | [Deterministic Escalation Policy Engine](#feature-22-deterministic-escalation-policy-engine) | Emergency Response | `Implemented` | Yes (Escalation API) | `services/api/services/escalation.py`, `packages/schemas/responders.py` |
| **23** | [Multi-Channel SMS & WhatsApp Dispatch Gateway](#feature-23-multi-channel-sms--whatsapp-dispatch-gateway) | Notifications | `Implemented` | Yes (Confirm Modal) | `services/api/services/notifications.py`, `fast2sms.py`, `richautomate.py` |
| **24** | [Tactical Incident Dossier PDF Generator](#feature-24-tactical-incident-dossier-pdf-generator) | Incident Dossier | `Implemented` | Yes (Dossier Modal) | `services/api/services/dossier.py`, `apps/web/src/components/dossier/TacticalDossierModal.tsx` |
| **25** | [AI Simulation Lab & What-If Sandbox](#feature-25-ai-simulation-lab--what-if-sandbox) | Simulation / ML | `Implemented` | Yes (Sim Lab Modal) | `services/api/routes/simulation.py`, `apps/web/src/components/simulation/AiSimulationLabModal.tsx` |
| **26** | [Comprehensive Event Intelligence Side-Panel](#feature-26-comprehensive-event-intelligence-side-panel) | Frontend UX | `Implemented` | Yes (Event Panel) | `apps/web/src/components/events/EventIntelligencePanel.tsx`, `useEventDetail.ts` |
| **27** | [Global Command Bar & Telemetry HUD](#feature-27-global-command-bar--telemetry-hud) | Frontend UX | `Implemented` | Yes (TopBar & HUD) | `apps/web/src/components/app-shell/TopBar.tsx`, `StatusBar.tsx` |
| **28** | [Modular FastAPI REST Architecture (17 Routers)](#feature-28-modular-fastapi-rest-architecture-17-routers) | Backend / API | `Implemented` | Yes (OpenAPI / Docs) | `services/api/app.py`, `services/api/routes/__init__.py` |
| **29** | [System Health & Dependency Readiness Probes](#feature-29-system-health--dependency-readiness-probes) | Backend / Reliability | `Implemented` | Yes (`/health`, `/ready`) | `services/api/routes/health.py`, `services/api/routes/readiness.py` |
| **30** | [PostGIS Spatial Relational Architecture (9 Migrations)](#feature-30-postgis-spatial-relational-architecture-9-migrations) | Database / Storage | `Implemented` | Internal / Backend Only | `alembic/versions/0001_baseline_infrastructure.py` to `0009_forest_areas.py` |
| **31** | [Asynchronous Background Job & Queue Engine](#feature-31-asynchronous-background-job--queue-engine) | Infrastructure | `Implemented` | Internal / Backend Only | `services/worker/jobs/runner.py`, `services/worker/jobs/queue.py` |

---

# Detailed Feature Specifications

---

## Category 1: Data & Satellite Intelligence

### Feature 1: NASA FIRMS Thermal Observation Ingestion

#### What it is
Ingests active fire and thermal anomaly data from NASA LANCE / FIRMS across multiple satellite sensor streams: VIIRS (Suomi-NPP, NOAA-20, NOAA-21 at 375m spatial resolution) and MODIS (Terra, Aqua at 1km resolution). Ingests raw CSV and JSON streams, validates coordinate boundaries, parses brightness temperatures (MWIR / LWIR), scan/track angles, confidence ratings, and Fire Radiative Power (FRP in MW).

#### Why is it useful?
Thermal anomalies provide the foundational near-real-time sensor telemetry for detecting combustion. Standardizing disparate satellite formats into a single canonical schema prevents downstream sensor mismatch and enables unified clustering.

#### How did we implement it?
- Implemented robust CSV and dict parsers with strict type casting and null-safe coordinate conversion.
- Created the canonical Pydantic model `Detection` representing individual satellite observations.
- Built bulk acquisition and real-time fetch routines that link observations to tracking snapshot IDs.

#### Implementation Status
`Implemented`

#### Evidence
- [`packages/data/firms/parser.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/firms/parser.py)
- [`packages/data/firms/normalizer.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/firms/normalizer.py)
- [`packages/data/firms/client.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/firms/client.py)
- [`packages/schemas/detection.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/schemas/detection.py)
- [`services/api/routes/detections.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/detections.py)

---

### Feature 2: Industrial Asset & Ground Truth Cataloging

#### What it is
Maintains a spatial catalog of industrial facilities (petroleum refineries, steel plants, chemical manufacturing hubs, thermal power plants, gas flare stacks) extracted from Global Energy Monitor (Global Iron & Steel Tracker, Global Oil & Gas Tracker, Global Power Plants) and OpenStreetMap. Each asset is stored as a `PersistentSource` with validated WGS-84 coordinates, facility type, capacity, and operational status.

#### Why is it useful?
Differentiating routine industrial gas flaring from emergency wildfires requires knowing where stationary thermal assets exist. Proximity to known flare stacks is a key feature for ML segregation.

#### How did we implement it?
- Ground truth parsers ingest Excel/CSV datasets into `PersistentSource` records.
- Spatial index trees (KD-Tree / BallTree / PostGIS `ST_DWithin`) compute distance to nearest facility in milliseconds.

#### Implementation Status
`Implemented`

#### Evidence
- [`packages/context/ground_truth.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/context/ground_truth.py)
- [`packages/context/pipeline.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/context/pipeline.py)
- [`packages/data/context/parser.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/context/parser.py)
- [`packages/schemas/source.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/schemas/source.py)
- [`services/api/routes/sources.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/sources.py)

---

### Feature 3: Global Forest & Protected Area Spatial Ingestion

#### What it is
Automated client and ingestion pipeline that queries OpenStreetMap Overpass API and World Database on Protected Areas (WDPA) to ingest forest reserves, national parks, and wildlife sanctuaries as GeoJSON MultiPolygons.

#### Why is it useful?
Fires near or within forest reserves pose catastrophic environmental and ecological destruction risks. Ingesting high-precision polygon boundaries allows geodesic containment testing.

#### How did we implement it?
- Overpass API query client with retry logic, backoff, and XML/GeoJSON parsing.
- Forest repository backed by PostGIS spatial queries (`ST_GeomFromGeoJSON`, `ST_Intersects`, `ST_Distance`).
- Database migration `0009_forest_areas.py` creating spatial indexes on forest polygons.

#### Implementation Status
`Implemented`

#### Evidence
- [`packages/data/forests/client.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/forests/client.py)
- [`packages/data/forests/parser.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/forests/parser.py)
- [`packages/data/forests/repository.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/forests/repository.py)
- [`packages/data/forests/service.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/forests/service.py)
- [`alembic/versions/0009_forest_areas.py`](file:///home/kafka/Coding/SIH-Hackathon/alembic/versions/0009_forest_areas.py)

---

### Feature 4: Automated Ingestion Quality Auditing & Quarantine

#### What it is
Validation gate that intercepts satellite and contextual data payloads before database persistence. Checks coordinate bounding boxes ($[-90, 90], [-180, 180]$), physical radiance bounds ($T_{MWIR} > T_{LWIR}$ for genuine thermal emission), non-negative FRP, temporal monotonically increasing timestamps, and non-empty satellite identifiers. Violations are flagged and quarantined with structured error codes.

#### Why is it useful?
Prevents sensor glitches, cloud-reflection artifacts, and corrupt data rows from polluting training sets, clustering pipelines, or emergency dispatch systems.

#### How did we implement it?
- Rule-based evaluation engine implementing `QualityRule` protocols.
- Structured validation report generation with error codes defined in `packages/data/quality/errors.py`.

#### Implementation Status
`Implemented`

#### Evidence
- [`packages/data/quality/auditor.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/quality/auditor.py)
- [`packages/data/quality/rules.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/quality/rules.py)
- [`packages/data/quality/schemas.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/quality/schemas.py)
- [`tests/test_data_quality.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_data_quality.py)

---

## Category 2: AI / ML Intelligence

### Feature 5: Point-in-Time Supervised Feature Engineering

#### What it is
Extracts 26+ deterministic physical, thermal, spatial, temporal, and contextual features per event according to canonical schema `feat_v1.0.0`. Features include max/mean FRP, MWIR/LWIR brightness temperatures, brightness ratio, day/night flag, distance to nearest industrial facility, observation count, spatial density, temporal duration, and 30-day recurrence count. Enforces strict point-in-time isolation to prevent data leakage.

#### Why is it useful?
High-performing ML models require leak-free feature vectors that reflect only information available at the exact observation timestamp.

#### How did we implement it?
- Feature registry pattern with strict schema versioning (`feat_v1.0.0`).
- Feature extractor with automated leakage verification tests.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/ml/features/extractor.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/features/extractor.py)
- [`services/ml/features/builder.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/features/builder.py)
- [`services/ml/features/leakage.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/features/leakage.py)
- [`services/ml/features/standard_set.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/features/standard_set.py)

---

### Feature 6: Multi-Model Machine Learning Classification Engine

#### What it is
Supervised classification engine deploying gradient-boosted decision trees (XGBoost, LightGBM), Random Forests, and Calibrated Logistic Regression models. Classifies thermal events into `INDUSTRIAL` (refinery flaring, steel manufacturing, chemical plants) and `NON_INDUSTRIAL` (wildfires, forest fires, agricultural residue burning). Outputs calibrated class probabilities $[0.0, 1.0]$.

#### Why is it useful?
Manual inspection of thousands of daily satellite detections is impossible. Machine learning automates real-time classification so operators can focus on dangerous uncontained wildfires rather than routine permitted industrial flares.

#### How did we implement it?
- Standard model interface `BaseMLModel` with serialization/deserialization.
- Stratified spatial-temporal cross-validation and evaluation harness.
- Production model registry selecting top-performing models meeting F1, Precision, and Recall gates.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/ml/models/tree.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/tree.py)
- [`services/ml/models/linear.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/linear.py)
- [`services/ml/models/registry.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/models/registry.py)
- [`services/ml/training/real_trainer.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/training/real_trainer.py)
- [`services/ml/evaluation/real_evaluator.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/evaluation/real_evaluator.py)

---

### Feature 7: Calibrated Abstention & Operating Mode Policy

#### What it is
Production deployment runtime governing model inference under three distinct operational modes: `HIGH_PRECISION` (threshold $\ge 0.85$, minimizes false alarms), `HIGH_RECALL` (threshold $\ge 0.50$, captures all potential wildfires), and `SELECTIVE` (requires high confidence; otherwise abstains). When confidence falls in the uncertainty band or input features are out-of-distribution, the engine flags the event as `REVIEW_REQUIRED` with an explicit `AbstentionReason`. Enforces the mathematical invariant: `UNKNOWN != NON_INDUSTRIAL`.

#### Why is it useful?
In mission-critical disaster management, an uncertain prediction must never be silently misclassified as safe. Abstention prompts human operator review for edge cases.

#### How did we implement it?
- `OperatingModePolicy` service integrated into the inference execution path.
- Returns structured `ProductionPredictionResponse` containing confidence, thresholds, abstention status, review triggers, and inference latency.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/ml/deployment/policy.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/deployment/policy.py)
- [`services/ml/calibration/abstention.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/calibration/abstention.py)
- [`services/ml/inference/production_runtime.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/inference/production_runtime.py)
- [`services/api/routes/inference.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/inference.py)

---

### Feature 8: SHAP Explainability & Feature Attribution Engine

#### What it is
Explainable AI (XAI) engine generating local feature attribution scores (Shapley values) for each classification decision. Identifies top positive drivers (e.g., proximity to refinery $< 300\text{m}$, high recurrence count) and negative drivers (e.g., inside forest boundary, zero historical persistence). Synthesizes human-readable natural language justification strings for operators.

#### Why is it useful?
Black-box ML predictions cannot be trusted blindly during emergency escalations. Operators need clear, grounded explanations of *why* an event was classified as industrial or wildfire.

#### How did we implement it?
- TreeSHAP and KernelSHAP backend explainer in `services/ml/explainability/shap_explainer.py`.
- Grounded TypeScript XAI generator in `apps/web/src/lib/xai/explainer.ts`.
- Interactive frontend visualization with visual attribution bars and confidence indicators in `ExplainableAiSection.tsx`.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/ml/explainability/shap_explainer.py`](file:///home/kafka/Coding/SIH-Hackathon/services/ml/explainability/shap_explainer.py)
- [`apps/web/src/lib/xai/explainer.ts`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/lib/xai/explainer.ts)
- [`apps/web/src/components/events/ExplainableAiSection.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/ExplainableAiSection.tsx)

---

## Category 3: Fire / Thermal & Physical Intelligence

### Feature 9: Spatiotemporal DBSCAN Event Clustering

#### What it is
Spatiotemporal clustering algorithm that groups individual raw satellite detection pixels into unified `ThermalEvent` clusters. Employs geodesic haversine spatial distance ($\le 2.5\text{km}$) and temporal windowing ($\le 12\text{hours}$). Computes aggregate cluster properties: centroid coordinates, convex hull bounding envelope, total FRP, peak FRP, observation count, and temporal duration.

#### Why is it useful?
A single industrial flare stack or wildfire flank generates dozens of satellite detection pixels across multiple satellite passes. Clustering consolidates these into single actionable incidents.

#### How did we implement it?
- DBSCAN clustering service with custom spatial-temporal distance metric.
- Event builder constructing standardized `ThermalEvent` models with full provenance tracking.

#### Implementation Status
`Implemented`

#### Evidence
- [`packages/events/clustering.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/events/clustering.py)
- [`packages/events/builder.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/events/builder.py)
- [`packages/events/pipeline.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/events/pipeline.py)
- [`packages/schemas/event.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/schemas/event.py)
- [`services/api/routes/events.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/events.py)

---

### Feature 10: Planck / Dozier Dual-Band Pyrometry Solver

#### What it is
Physical radiative transfer inversion solver based on Dozier (1981) dual-band infrared pyrometry. Utilizes simultaneous Medium-Wave Infrared ($\lambda \approx 3.74\,\mu\text{m}$, VIIRS I4) and Long-Wave Infrared ($\lambda \approx 11.45\,\mu\text{m}$, VIIRS I5) blackbody radiances to solve the nonlinear system:
$$L_{\text{obs}}(\lambda) = p \cdot B(\lambda, T_{\text{flame}}) + (1 - p) \cdot B(\lambda, T_{\text{background}})$$
Inverts for sub-pixel flame temperature $T_{\text{flame}}$ (in Kelvin/Celsius), background temperature $T_{\text{background}}$, fractional fire pixel coverage $p$, and exact subpixel combustion area $A_{\text{flame}}$ in square meters.

#### Why is it useful?
Satellite pixels are $375\text{m} \times 375\text{m}$ ($140,625\,\text{m}^2$). Pixel brightness temperature is an average over the entire footprint. Dozier pyrometry reveals the *true* sub-pixel flame temperature ($> 1200\text{K}$ for gas flares vs $600\text{–}900\text{K}$ for biomass burning) and actual flame area ($< 50\,\text{m}^2$ for flare tips vs thousands of $\text{m}^2$ for forest fires).

#### How did we implement it?
- Numerical optimization solver with Planck spectral radiance integration and bounds checking ($450\text{K} \le T_f \le 2200\text{K}$).
- Interactive frontend telemetry card displaying emitter temperature, background temperature, flame area, and convergence residuals.

#### Implementation Status
`Implemented`

#### Evidence
- [`packages/physics/pyrometry.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/physics/pyrometry.py)
- [`tests/test_planck_pyrometry.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_planck_pyrometry.py)
- [`apps/web/src/components/events/PlanckPyrometrySection.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/PlanckPyrometrySection.tsx)

---

### Feature 11: Temporal Persistence & Recurrence Intelligence

#### What it is
Multi-temporal tracking system analyzing 30, 60, and 90-day observation curves for geographic coordinates. Tracks observation multiplicity, day/night detection ratio, and recurrence frequency.

#### Why is it useful?
Stationary industrial flares exhibit steady, persistent thermal signatures over months, whereas wildfires and stubble burns are transient, single-epoch events. Historical curve analysis provides unmistakable validation of stationary flaring.

#### How did we implement it?
- Source tracking service computing temporal baselines in `packages/sources/tracking.py` and `packages/intelligence/baseline.py`.
- Historical curve route `/api/historical/scenarios` and `/events/{event_id}/timeline`.
- Interactive SVG time-series charts rendering 90-day FRP curves and anomaly markers in `HistoricalCurveSection.tsx`.

#### Implementation Status
`Implemented`

#### Evidence
- [`packages/sources/tracking.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/sources/tracking.py)
- [`packages/intelligence/baseline.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/intelligence/baseline.py)
- [`services/api/routes/historical.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/historical.py)
- [`apps/web/src/components/events/HistoricalCurveSection.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/HistoricalCurveSection.tsx)

---

## Category 4: GIS / Mapping & Cartography

### Feature 12: Dual-Engine 2D/3D Geospatial Mission Canvas

#### What it is
High-performance dual-engine cartographic interface supporting instant, synchronized switching between **MapLibre GL 2D Mercator flat map** and **3D Orthographic Orbital Globe**. Features hardware-accelerated WebGL rendering, custom animated thermal flame markers with pulsing radial glow, dynamic camera fly-to transitions, zoom/pan controls, and datum annotation (`WGS-84 · EPSG:4326`).

#### Why is it useful?
Provides operators both macro-scale orbital situational awareness (global/national scale) and micro-scale tactical inspection (facility/forest boundary level).

#### How did we implement it?
- React component architecture with dynamic SSR-safe lazy loading in `MapWorkspace.tsx`.
- MapLibre GL instance in `FlatMapView.tsx` and 3D globe renderer in `GlobeView.tsx`.
- Custom DOM / canvas fire markers in `FireMarkerElement.ts`.

#### Implementation Status
`Implemented`

#### Evidence
- [`apps/web/src/components/map/MapWorkspace.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/map/MapWorkspace.tsx)
- [`apps/web/src/components/map/FlatMapView.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/map/FlatMapView.tsx)
- [`apps/web/src/components/map/GlobeView.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/map/GlobeView.tsx)
- [`apps/web/src/components/map/FireMarkerElement.ts`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/map/FireMarkerElement.ts)
- [`apps/web/src/components/map/ViewModeToggle.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/map/ViewModeToggle.tsx)

---

### Feature 13: 12 GIS Layer Catalog & GeoJSON Streaming

#### What it is
Comprehensive 12-layer GIS management panel streaming RFC 7946 GeoJSON FeatureCollections:
1. NASA FIRMS VIIRS Thermal Detections
2. NASA FIRMS Live API Stream
3. India Industrial Facilities (Refineries, Chemical Plants)
4. Global Power Plants Database
5. Global Oil & Gas Infrastructure Tracker
6. Global Iron & Steel Plant Tracker
7. CAMEO-NIOSH Hazmat Chemical Sites
8. Historical Industrial Incident Sites
9. Emergency Response Services (Fire, Hazmat, Hospitals)
10. Multimodal Benchmark Reference Zones
11. Administrative & State Boundaries
12. Indian Forest Reserves & Protected Wilderness

#### Why is it useful?
Enables multi-layer spatial correlation, allowing operators to overlay thermal anomalies directly on forest boundaries, industrial plant perimeters, and critical infrastructure.

#### How did we implement it?
- Backend endpoints `/layers/events`, `/layers/detections`, and `/api/gis-layers/catalog`.
- Interactive `LayerPanel.tsx` with search filtering, visibility toggles, category badges, and metadata inspection modal (`LayerMetadataModal.tsx`).

#### Implementation Status
`Implemented`

#### Evidence
- [`services/api/routes/layers.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/layers.py)
- [`services/api/routes/gis_layers.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/gis_layers.py)
- [`apps/web/src/components/map/LayerPanel.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/map/LayerPanel.tsx)
- [`apps/web/src/components/map/LayerMetadataModal.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/map/LayerMetadataModal.tsx)

---

### Feature 14: Interactive Temporal Playback & Scrubbing

#### What it is
Floating timeline playback bar allowing operators to scrub through observation history, filter events by temporal window, and play historical animations at variable speeds ($1\times, 2\times, 5\times, 10\times$).

#### Why is it useful?
Crucial for reconstructing fire propagation, identifying ignition timing, and visualizing seasonal industrial flaring trends over time.

#### How did we implement it?
- Temporal window manager in `apps/web/src/lib/playback/temporal.ts`.
- React state synchronization in `EventContext.tsx` and UI controls in `TimelinePlaybackBar.tsx`.

#### Implementation Status
`Implemented`

#### Evidence
- [`apps/web/src/components/playback/TimelinePlaybackBar.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/playback/TimelinePlaybackBar.tsx)
- [`apps/web/src/lib/playback/temporal.ts`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/lib/playback/temporal.ts)
- [`apps/web/src/context/EventContext.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/context/EventContext.tsx)

---

## Category 5: Weather & Wind Intelligence

### Feature 15: Real-Time Open-Meteo Weather & Wind Engine

#### What it is
Integrated meteorological service that queries Open-Meteo REST APIs for coordinate-specific weather conditions: 10m wind speed ($\text{m/s}$ and $\text{km/h}$), meteorological wind direction ($\text{degrees FROM}$), wind gusts, ambient temperature ($^\circ\text{C}$), relative humidity ($\%$), surface pressure, cloud cover, and boundary layer height. Features in-memory TTL caching (1-hour window) and coordinate rounding to minimize redundant external API calls.

#### Why is it useful?
Wind speed and direction govern fire spread rate and atmospheric smoke/gas plume dispersion. Accurate local weather is vital for hazard modeling.

#### How did we implement it?
- `OpenMeteoClient` with connection pooling, timeout safety, and fallback handling.
- `WeatherCache` in-memory key-value store with expiry enforcement.
- Meteorological coordinate and vector transformation service in `packages/data/weather/service.py`.

#### Implementation Status
`Implemented`

#### Evidence
- [`packages/data/weather/open_meteo.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/weather/open_meteo.py)
- [`packages/data/weather/cache.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/weather/cache.py)
- [`packages/data/weather/service.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/weather/service.py)
- [`packages/physics/wind.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/physics/wind.py)
- [`services/api/routes/weather.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/weather.py)

---

### Feature 16: Wind Vector Compass & Threat Analysis

#### What it is
Frontend meteorological intelligence card computing and rendering:
- Dynamic 16-point meteorological wind compass with rotating vector needle.
- Downwind propagation bearing ($\theta_{\text{downwind}} = (\theta_{\text{from}} + 180^\circ) \bmod 360^\circ$).
- Cartesian $u$ (eastward) and $v$ (northward) vector components.
- Fire spread risk multiplier based on wind velocity.

#### Why is it useful?
Gives incident commanders an immediate visual summary of where a fire or toxic cloud is moving and how rapidly it will expand.

#### How did we implement it?
- Math utilities in `packages/physics/wind.py` and frontend type contracts in `types/weather.ts`.
- Interactive SVG compass card with dynamic risk color coding in `WindVectorCard.tsx`.

#### Implementation Status
`Implemented`

#### Evidence
- [`packages/physics/wind.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/physics/wind.py)
- [`apps/web/src/components/events/WindVectorCard.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/WindVectorCard.tsx)
- [`apps/web/src/types/weather.ts`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/types/weather.ts)

---

## Category 6: Atmospheric / Hazard & Hazmat Intelligence

### Feature 17: Gaussian Plume Atmospheric Dispersion Modeling

#### What it is
Physics engine executing steady-state **Gaussian Plume atmospheric dispersion modeling** for combustion products and hazardous industrial gas releases. Formulates:
$$C(x, y, z) = \frac{Q}{2\pi u \sigma_y \sigma_z} \exp\left(-\frac{y^2}{2\sigma_y^2}\right) \left[ \exp\left(-\frac{(z - H)^2}{2\sigma_z^2}\right) + \exp\left(-\frac{(z + H)^2}{2\sigma_z^2}\right) \right]$$
Calculates Pasquill-Gifford atmospheric stability classes (A through F) based on wind speed and insolation, downwind/crosswind dispersion coefficients ($\sigma_y, \sigma_z$), Briggs plume rise from thermal buoyancy (FRP), and multi-zone isolation / protective action distance polygons.

#### Why is it useful?
Industrial fires and chemical leaks generate toxic downwind plumes. The model predicts hazardous ground concentrations to establish life-saving evacuation corridors.

#### How did we implement it?
- Core physics engine in `packages/physics/dispersion.py` and `packages/physics/plume.py`.
- Service integration in `packages/data/weather/dispersion_service.py` generating GeoJSON polygons for Red (Immediate Isolation Zone), Orange (Protective Action Zone), and Yellow (Downwind Awareness Zone).
- Map visualization with semi-transparent hazard overlays in `FlatMapView.tsx`.

#### Implementation Status
`Implemented`

#### Evidence
- [`packages/physics/dispersion.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/physics/dispersion.py)
- [`packages/physics/plume.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/physics/plume.py)
- [`packages/data/weather/dispersion_service.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/weather/dispersion_service.py)
- [`services/api/routes/dispersion.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/dispersion.py)
- [`apps/web/src/components/events/HazardDispersionCard.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/HazardDispersionCard.tsx)

---

### Feature 18: CAMEO-NIOSH Toxic Hazmat Chemical Profiling

#### What it is
Chemical safety intelligence database integrating CAMEO Chemicals and NIOSH Pocket Guide hazardous chemical profiles. Maps industrial facility types (refineries, polymer plants, fertilizer units) to associated chemicals: Sulfur Dioxide ($\text{SO}_2$), Hydrogen Sulfide ($\text{H}_2\text{S}$), Styrene monomer, Ammonia ($\text{NH}_3$), and Chlorine ($\text{Cl}_2$). Provides UN numbers, CAS numbers, IDLH limits, ERPG-1/2/3 thresholds, health hazard summaries, and recommended initial isolation distances.

#### Why is it useful?
Responders must know what toxic chemicals are present at an industrial fire before arriving on scene to wear proper PPE and establish correct standoff distances.

#### How did we implement it?
- Chemical registry and hazard synthesis in `services/api/services/dossier.py`.
- Dedicated endpoint `/api/hazmat-profiles` in `services/api/routes/hazmat.py`.
- Interactive hazard card in `apps/web/src/components/events/HazmatRiskCard.tsx`.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/api/routes/hazmat.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/hazmat.py)
- [`services/api/services/dossier.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/services/dossier.py)
- [`apps/web/src/components/events/HazmatRiskCard.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/HazmatRiskCard.tsx)

---

## Category 7: Forest Intelligence & Threat Analysis

### Feature 19: PostGIS Geodesic Forest Threat Assessment

#### What it is
Spatial intelligence service calculating geodesic boundary distances from thermal fire coordinates to all nearby OpenStreetMap forest polygons. Uses PostGIS spatial functions (`ST_Distance`, `ST_DWithin`, `ST_Intersects`, `ST_Contains`) and Shapely polygon geometries. Classifies threat into four standardized levels:
- `INSIDE_FOREST`: Distance $= 0.0\,\text{km}$ (Active forest wildfire)
- `IMMINENT_PERIL`: Distance $< 1.0\,\text{km}$
- `WARNING`: $1.0\,\text{km} \le \text{Distance} < 5.0\,\text{km}$
- `MONITORING`: $5.0\,\text{km} \le \text{Distance} < 20.0\,\text{km}$

#### Why is it useful?
Provides immediate automated warning when fires approach or ignite within protected forest reserves, enabling rapid ranger deployment before crown fire development.

#### How did we implement it?
- Point-to-polygon geodesic calculation algorithms in `packages/geospatial/polygon_distance.py`.
- `ForestThreatService` with candidate filtering, threat ranking, and thread-safe alert deduplication.

#### Implementation Status
`Implemented`

#### Evidence
- [`packages/data/forests/threat_service.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/forests/threat_service.py)
- [`packages/data/forests/repository.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/forests/repository.py)
- [`packages/geospatial/polygon_distance.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/geospatial/polygon_distance.py)
- [`services/api/routes/forests.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/forests.py)
- [`apps/web/src/components/events/ForestProximityCard.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/ForestProximityCard.tsx)

---

### Feature 20: Global Forest Monitoring Hub & Threat Drawer

#### What it is
Dedicated operational management hub providing national forest fire surveillance. Displays:
- Global KPI counters (Total Forests Monitored, Critical Active Threats, Warning Stances, Safe Reserves).
- Searchable, filterable forest threat list with live distance badges and fire event associations.
- Slide-out **Forest Threat Detail Drawer** with high-resolution map, boundary inspection, and ranger dispatch actions.
- Interactive end-to-end simulation runner for training and demonstrations.

#### Why is it useful?
Gives forest conservation officers and environmental protection agencies a centralized dashboard tailored specifically to wilderness fire mitigation.

#### How did we implement it?
- Backend endpoint `/api/forests/monitoring-dashboard` and `/api/forests/threat-detail/{forest_id}`.
- Complete React interface in `GlobalForestMonitoringHub.tsx` and `ForestThreatDetailDrawer.tsx`.

#### Implementation Status
`Implemented`

#### Evidence
- [`apps/web/src/components/events/GlobalForestMonitoringHub.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/GlobalForestMonitoringHub.tsx)
- [`apps/web/src/components/events/ForestThreatDetailDrawer.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/ForestThreatDetailDrawer.tsx)
- [`apps/web/src/lib/api/forests.ts`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/lib/api/forests.ts)
- [`services/api/routes/forests.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/forests.py)

---

## Category 8: Emergency Response & Notification Gateway

### Feature 21: Multi-Agency Emergency Responder Discovery

#### What it is
Spatial discovery engine identifying nearest emergency response units within a $50\text{km}$ radius of an incident:
- **Fire Stations & Industrial Fire Brigades** (Equipment, pump capacity, foam units)
- **Hazmat Emergency Response Teams** (Chemical neutralizers, breathing apparatus)
- **District Police Headquarters & PCR Units** (Perimeter cordon, traffic control)
- **District Hospitals & Trauma Centers** (Burn units, ICU beds, oxygen supply)
Calculates haversine geodesic distance, estimated road travel time (ETA in minutes), and flags units located in the downwind toxic plume path.

#### Why is it useful?
Eliminates delay in finding appropriate emergency resources during severe industrial flare escalations or wildfires.

#### How did we implement it?
- Domain service `ResponseRecommendationService` querying responder repositories.
- Ranking algorithm ordering responders by proximity and specialized capability.
- Interactive responder cards in `EmergencyResponseSection.tsx`.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/api/services/responders.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/services/responders.py)
- [`services/api/routes/responders.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/responders.py)
- [`apps/web/src/lib/responders/engine.ts`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/lib/responders/engine.ts)
- [`apps/web/src/components/events/EmergencyResponse/EmergencyResponseSection.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/EmergencyResponse/EmergencyResponseSection.tsx)

---

### Feature 22: Deterministic Escalation Policy Engine

#### What it is
Backend-authoritative decision engine governing incident escalation workflows. Evaluates model confidence and operational risk priority against configurable threshold invariants:
- $\text{Confidence} \le 0.94 \implies \text{NO\_ESCALATION}$
- $0.94 < \text{Confidence} \le 0.98 \implies \text{ADMIN\_REVIEW\_REQUIRED}$
- $\text{Confidence} > 0.98 \implies \text{AUTOMATIC\_ESCALATION}$ (if enabled)
- $\text{Priority} = \text{CRITICAL} \implies \text{MEDICAL\_ESCALATION} = \text{True}$

#### Why is it useful?
Prevents accidental false-alarm dispatches while guaranteeing that high-severity, high-confidence emergencies trigger immediate automated response protocols.

#### How did we implement it?
- `EscalationPolicyService` in `services/api/services/escalation.py`.
- Endpoint `GET /events/{event_id}/escalation` returning structured policy decisions and human-readable justification strings.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/api/services/escalation.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/services/escalation.py)
- [`packages/schemas/responders.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/schemas/responders.py)
- [`tests/test_escalation_engine.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_escalation_engine.py)

---

### Feature 23: Multi-Channel SMS & WhatsApp Dispatch Gateway

#### What it is
Notification engine supporting multi-channel emergency alert dispatches via:
- **Fast2SMS API** (High-priority Indian emergency SMS)
- **RichAutomate API** (WhatsApp Business interactive notification templates)
- **Simulated Provider** (Sandboxed mock provider for deterministic offline testing)
Features phone number configuration overrides, idempotent deduplication, delivery receipt tracking, and structured audit logging.

#### Why is it useful?
Ensures incident details and tactical instructions reach field commanders and first responders via reliable mobile messaging channels.

#### How did we implement it?
- Provider factory pattern in `services/api/services/providers/factory.py`.
- Dedicated endpoints `POST /events/{event_id}/notify` and `GET /events/{event_id}/response-activity`.
- Modal confirmation dialog `NotificationConfirmModal.tsx` and live audit feed `ResponseActivityFeed.tsx`.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/api/services/notifications.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/services/notifications.py)
- [`services/api/services/providers/fast2sms.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/services/providers/fast2sms.py)
- [`services/api/services/providers/richautomate.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/services/providers/richautomate.py)
- [`services/api/services/providers/simulated.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/services/providers/simulated.py)
- [`apps/web/src/components/events/EmergencyResponse/NotificationConfirmModal.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/EmergencyResponse/NotificationConfirmModal.tsx)

---

## Category 9: Incident Dossier & Simulation

### Feature 24: Tactical Incident Dossier PDF Generator

#### What it is
Comprehensive operational briefing package generator that consolidates:
- Event metadata & coordinates
- ML classification & class probabilities
- Planck pyrometry physical metrics ($T_{\text{flame}}$, flame area)
- CAMEO-NIOSH chemical hazard profile & IDLH limits
- Gaussian dispersion plume evacuation radii
- Dispatched emergency responders & contact numbers
Formats output into a clean, official, printable PDF / HTML briefing document.

#### Why is it useful?
Provides incident commanders and regulatory bodies with a complete, single-document situational briefing for briefings, press releases, or legal compliance.

#### How did we implement it?
- `TacticalDossierService` in `services/api/services/dossier.py`.
- Endpoints `GET /events/{event_id}/dossier` and `GET /events/{event_id}/dossier/html`.
- High-fidelity printable modal `TacticalDossierModal.tsx` with browser print integration.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/api/services/dossier.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/services/dossier.py)
- [`services/api/routes/dossier.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/dossier.py)
- [`apps/web/src/components/dossier/TacticalDossierModal.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/dossier/TacticalDossierModal.tsx)

---

### Feature 25: AI Simulation Lab & What-If Sandbox

#### What it is
Interactive simulation modal allowing operators to perturb environmental and thermal variables:
- Latitude & Longitude coordinates
- Fire Radiative Power (FRP from $0\text{ to }500\,\text{MW}$)
- MWIR / LWIR Brightness Temperatures
- Distance to nearest industrial facility ($0\text{ to }20\,\text{km}$)
- Historical Recurrence Count ($1\text{ to }30\text{ detections}$)
- Wind Speed & Direction
Executes real-time inference against the backend ML model and Gaussian Plume solver to observe classification shifts and plume expansion. Includes pre-loaded real-world benchmark presets (Jamnagar Refinery Flare, Vizag Polymer Leak, Punjab Stubble Burn, Jharia Coal Smolder).

#### Why is it useful?
Enables training, what-if risk modeling, and model sensitivity testing without waiting for live satellite passes.

#### How did we implement it?
- Backend simulation route `/api/simulation/custom-classify` in `services/api/routes/simulation.py`.
- Interactive frontend modal with live parameter sliders and preset selector in `AiSimulationLabModal.tsx`.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/api/routes/simulation.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/simulation.py)
- [`apps/web/src/components/simulation/AiSimulationLabModal.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/simulation/AiSimulationLabModal.tsx)

---

## Category 10: Frontend User Experience & Telemetry

### Feature 26: Comprehensive Event Intelligence Side-Panel

#### What it is
Collapsible, highly structured right-hand event intelligence panel that surfaces 10 specialized intelligence sections for any selected thermal event:
1. **Classification Header** (Status badge, confidence score, operational risk level)
2. **Class Probability Breakdown** (Industrial vs Non-Industrial probability distribution)
3. **Event Overview Grid** (FRP, observation count, day/night, duration, coordinates)
4. **Wind Vector Intelligence Card** (16-point compass, speed, direction, risk)
5. **Atmospheric Dispersion Card** (Plume length, isolation zone radius, evacuation radius)
6. **Industrial Asset Association** (Nearest facility, distance in km, facility type)
7. **Forest Proximity Threat Card** (Boundary distance, threat level, ranger alert dispatch)
8. **Explainable AI (XAI) Attribution** (Shapley feature drivers, natural language justification)
9. **Planck Pyrometry Physics Card** (Subpixel flame temperature, flame area in $\text{m}^2$)
10. **Historical 90-Day Curve** (FRP persistence timeline and recurrence anomaly flags)

#### Why is it useful?
Transforms raw satellite coordinates into a rich, multi-dimensional intelligence dossier on a single screen.

#### How did we implement it?
- Modular component hierarchy in `apps/web/src/components/events/`.
- Data hook `useEventDetail.ts` with SWR/fetch caching, loading skeletons, and error retry states.

#### Implementation Status
`Implemented`

#### Evidence
- [`apps/web/src/components/events/EventIntelligencePanel.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/EventIntelligencePanel.tsx)
- [`apps/web/src/hooks/useEventDetail.ts`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/hooks/useEventDetail.ts)
- [`apps/web/src/components/events/EventClassificationHeader.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/EventClassificationHeader.tsx)
- [`apps/web/src/components/events/EventOverviewGrid.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/events/EventOverviewGrid.tsx)

---

### Feature 27: Global Command Bar & Telemetry HUD

#### What it is
Top command header and bottom operational telemetry bar featuring:
- Global `⌘K` / `Ctrl+K` keyboard shortcut search focusing on event IDs, industrial facilities, and regions.
- Quick classification filter pills (`ALL`, `INDUSTRIAL`, `NON-IND`, `UNKNOWN`, `REVIEW`).
- Live UTC clock synchronized with WGS-84 coordinate HUD.
- Live backend connection status indicator (`LIVE FASTAPI` / `DEMO READY`).
- Keyboard navigation (Left/Right arrows for event navigation, Space for play/pause, Esc to dismiss).

#### Why is it useful?
Provides rapid, accessible keyboard-driven navigation for mission control operators.

#### How did we implement it?
- React components `TopBar.tsx`, `StatusBar.tsx`, and `MapOverlayContainer.tsx`.
- Centralized event state in `EventContext.tsx`.

#### Implementation Status
`Implemented`

#### Evidence
- [`apps/web/src/components/app-shell/TopBar.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/app-shell/TopBar.tsx)
- [`apps/web/src/components/app-shell/StatusBar.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/components/app-shell/StatusBar.tsx)
- [`apps/web/src/context/EventContext.tsx`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/context/EventContext.tsx)

---

## Category 11: Backend API Architecture

### Feature 28: Modular FastAPI REST Architecture (17 Routers)

#### What it is
Production-grade FastAPI asynchronous application structuring 17 modular route handlers:
- `/health`: Operational heartbeat probe
- `/ready`: Multi-dependency readiness check
- `/version`: Contract and semantic versioning
- `/sources`: Data source operational status
- `/detections`: Raw satellite detection querying and bounding box filtering
- `/events`: Clustered thermal events, evidence, timeline, and intelligence
- `/layers`: GeoJSON RFC 7946 map streaming layers
- `/inference`: Production ML runtime batch and single prediction endpoints
- `/events/{event_id}/responders` & `/events/{event_id}/notify`: Emergency responder discovery and notification dispatch
- `/events/{event_id}/dossier`: Tactical incident dossier generation
- `/api/simulation`: AI simulation lab custom classification
- `/api/historical`: 90-day persistence curves and scenarios
- `/api/hazmat-profiles`: CAMEO-NIOSH chemical database
- `/api/gis-layers`: 12-layer GIS catalog metadata
- `/api/forests`: Global forest monitoring, proximity assessments, and alert dispatch
- `/weather`: Open-Meteo live weather and wind vector endpoints
- `/dispersion`: Gaussian plume dispersion calculations

#### Why is it useful?
Ensures modular, decoupled, maintainable backend architecture with auto-generated interactive OpenAPI/Swagger documentation.

#### How did we implement it?
- Application factory `create_app()` in `services/api/app.py`.
- Strict Pydantic v2 schemas across all request/response models.
- Centralized RFC 7807 problem exception handling in `services/api/errors.py`.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/api/app.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/app.py)
- [`services/api/routes/__init__.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/__init__.py)
- [`services/api/errors.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/errors.py)

---

### Feature 29: System Health & Dependency Readiness Probes

#### What it is
Kubernetes-compatible `/health` and `/ready` probes evaluating system operational integrity:
- Database connectivity check
- Redis job queue responsiveness
- Production ML model artifact availability and feature schema validation
- Configuration consistency

#### Why is it useful?
Enables zero-downtime rolling deployments and automated traffic shedding when dependencies fail.

#### How did we implement it?
- `ReadinessCheckService` in `services/api/services/readiness.py`.
- Returns HTTP 200 when ready or HTTP 503 Service Unavailable with structured diagnostic json.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/api/routes/health.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/health.py)
- [`services/api/routes/readiness.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/routes/readiness.py)
- [`services/api/services/readiness.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/services/readiness.py)

---

## Category 12: Database & Infrastructure

### Feature 30: PostGIS Spatial Relational Architecture (9 Migrations)

#### What it is
PostgreSQL relational schema enhanced with PostGIS spatial extensions. Managed via 9 sequential Alembic migrations:
1. `0001_baseline_infrastructure.py`: PostGIS extension and baseline setup
2. `0002_scientific_contracts.py`: Scientific contract catalog
3. `0003_source_registry.py`: Data source provider registry
4. `0004_source_snapshots.py`: Immutable observation snapshot tracking
5. `0005_source_records.py`: Raw record storage
6. `0006_detections.py`: Canonical detection records with spatial GiST indexing
7. `0007_thermal_events.py`: Clustered thermal events and convex hulls
8. `0008_pipeline_runs_and_jobs.py`: Pipeline execution runs and background jobs
9. `0009_forest_areas.py`: Forest area boundaries with spatial geometry indexes

#### Why is it useful?
Provides transactional consistency, spatial indexing for sub-second bounding box queries, and auditability.

#### How did we implement it?
- Alembic migration versioning with reversible `upgrade()` and `downgrade()` scripts.
- PostGIS spatial indexes (`GIST(geometry)`) on all coordinate and polygon columns.

#### Implementation Status
`Implemented`

#### Evidence
- [`alembic/versions/0001_baseline_infrastructure.py`](file:///home/kafka/Coding/SIH-Hackathon/alembic/versions/0001_baseline_infrastructure.py) through [`alembic/versions/0009_forest_areas.py`](file:///home/kafka/Coding/SIH-Hackathon/alembic/versions/0009_forest_areas.py)
- [`docker/postgres/init-postgis.sh`](file:///home/kafka/Coding/SIH-Hackathon/docker/postgres/init-postgis.sh)

---

### Feature 31: Asynchronous Background Job & Queue Engine

#### What it is
Background job processing infrastructure supporting synchronous execution and Redis-backed queued task processing. Includes state machine management (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`), idempotent execution deduplication, progress reporting, and secret-sanitized error logging.

#### Why is it useful?
Long-running satellite CSV parsing, ML batch inference, and spatial clustering must run in the background without blocking API request threads.

#### How did we implement it?
- `SyncJobRunner` and `RedisJobQueue` in `services/worker/jobs/`.
- Domain job handlers: `FIRMSIngestJobHandler`, `EventClusteringJobHandler`, `ContextEnrichmentJobHandler`, `IntelligenceDerivationJobHandler`.

#### Implementation Status
`Implemented`

#### Evidence
- [`services/worker/jobs/runner.py`](file:///home/kafka/Coding/SIH-Hackathon/services/worker/jobs/runner.py)
- [`services/worker/jobs/queue.py`](file:///home/kafka/Coding/SIH-Hackathon/services/worker/jobs/queue.py)
- [`services/worker/jobs/handlers.py`](file:///home/kafka/Coding/SIH-Hackathon/services/worker/jobs/handlers.py)
- [`services/worker/jobs/state_machine.py`](file:///home/kafka/Coding/SIH-Hackathon/services/worker/jobs/state_machine.py)

---

# Planned / Partially Implemented Features

The following items are defined or partially implemented in the codebase, with specific missing pieces clearly noted:

### 1. Redis Distributed Queue in Default Local Standalone Mode
- **Current State:** Fully implemented in [`services/worker/jobs/queue.py`](file:///home/kafka/Coding/SIH-Hackathon/services/worker/jobs/queue.py) and [`tests/test_work_002_redis_queue.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_work_002_redis_queue.py).
- **Missing Pieces:** By default in local development mode, the system defaults to in-memory synchronous execution (`InMemoryJobRepository`) to allow running without requiring an active external Redis container.
- **Evidence:** [`services/worker/jobs/runner.py`](file:///home/kafka/Coding/SIH-Hackathon/services/worker/jobs/runner.py)

### 2. NASA FIRMS Continuous Live Polling Daemon
- **Current State:** FIRMS client ([`packages/data/firms/client.py`](file:///home/kafka/Coding/SIH-Hackathon/packages/data/firms/client.py)) and batch execution scripts ([`scripts/acquire_real_bulk_data.py`](file:///home/kafka/Coding/SIH-Hackathon/scripts/acquire_real_bulk_data.py), [`scripts/firms_ml_e2e_smoke_test.py`](file:///home/kafka/Coding/SIH-Hackathon/scripts/firms_ml_e2e_smoke_test.py)) are implemented.
- **Missing Pieces:** Continuous automated cron-based background polling daemon is run manually via CLI scripts rather than running as an automatic daemon service upon API startup.
- **Evidence:** [`scripts/acquire_real_bulk_data.py`](file:///home/kafka/Coding/SIH-Hackathon/scripts/acquire_real_bulk_data.py)

### 3. Live GPS Vehicle Tracking for Emergency Responders
- **Current State:** Nearest-neighbor responder identification, road distance/ETA estimation, downwind hazard exposure, and mobile notification dispatch are fully implemented.
- **Missing Pieces:** Real-time live GPS telemetry streaming from moving responder vehicles is not integrated; stations and units use authoritative static facility coordinates.
- **Evidence:** [`services/api/services/responders.py`](file:///home/kafka/Coding/SIH-Hackathon/services/api/services/responders.py)

---

# Overall System Capabilities

The current codebase delivers the following cohesive system capabilities:

```
+-----------------------------------------------------------------------------------------------+
|                                      SIH26162 PLATFORM                                        |
+-------------------------------+-------------------------------+-------------------------------+
| 1. DATA INGESTION             | 2. AI / ML CLASSIFICATION     | 3. PHYSICAL REASONING         |
| - NASA VIIRS/MODIS FIRMS      | - XGBoost, LightGBM, Trees    | - Dozier Dual-Band Pyrometry  |
| - Industrial Asset Catalogs   | - Calibrated Probabilities    | - Gaussian Plume Dispersion   |
| - OSM & WDPA Forest Polygons  | - Calibrated Abstention Bands | - Briggs Buoyancy Modeling    |
| - Open-Meteo Wind & Weather   | - SHAP Attribution & XAI      | - Pasquill-Gifford Stability  |
+-------------------------------+-------------------------------+-------------------------------+
| 4. GEOSPATIAL & GIS           | 5. EMERGENCY ESCALATION       | 6. INTERACTIVE MISSION UI     |
| - 2D MapLibre & 3D Globe WebGL| - Deterministic Policy Engine | - Collapsible Intel Panel     |
| - 12-Layer GeoJSON Streaming  | - Multi-Agency Responder Match| - Global Forest Monitoring    |
| - DBSCAN Cluster Aggregation  | - Fast2SMS & RichAutomate     | - AI Simulation Lab Sandbox   |
| - Temporal Timeline Scrubbing | - Tactical Incident Dossier   | - Global Command Bar (Cmd+K)  |
+-------------------------------+-------------------------------+-------------------------------+
```

1. **Multi-Source Data Ingestion:** Automated ingestion and normalization of satellite thermal anomalies, industrial ground truth datasets, forest reserves, and real-time weather streams.
2. **AI/ML Flame vs Fire Segregation:** Supervised ML classification backed by leak-free feature extraction, operating mode policies, and SHAP explainability.
3. **Rigorous Physics Modeling:** Sub-pixel Dozier pyrometry ($T_f, A_{\text{flame}}$) and Gaussian Plume atmospheric dispersion for toxic hazard corridor calculation.
4. **Forest & Asset Protection:** PostGIS geodesic spatial threat assessments identifying boundary proximities and deforestation risks.
5. **Emergency Escalation & Multi-Channel Dispatch:** Deterministic escalation evaluation, multi-agency responder discovery, and SMS/WhatsApp mobile notifications.
6. **Unified WebGL Mission Control:** Seamless 2D/3D geospatial visualization with temporal playback, tactical dossier generation, and what-if simulation capabilities.

---

# What Can Be Demonstrated Right Now?

The following user workflows and capabilities can be demonstrated directly in the running application:

### 1. Dual-Engine 2D / 3D Geospatial Map & Thermal Event Inspection
- **Where to access:** Navigate to `http://localhost:3000` (Main Mission Control).
- **Action:** Toggle between `2D` and `3D` buttons at the top of the map. Click on any pulsing fire marker on the map or in the live feed.
- **Expected Output:** Camera smoothly centers on the event; the 10-section **Event Intelligence Panel** opens displaying real-time classification, confidence, operational risk, and satellite telemetry.

### 2. Explainable AI (XAI) & Feature Attribution Review
- **Where to access:** Select any event in the main map to open the side panel, scroll to the **Explainable AI (XAI)** section.
- **Action:** Inspect the horizontal feature attribution bars and natural language justification text.
- **Expected Output:** Visual breakdown showing top positive drivers (e.g., proximity to refinery $< 0.4\text{km}$, high 30-day recurrence) and negative drivers with grounded explanations.

### 3. Planck / Dozier Sub-Pixel Pyrometry Telemetry
- **Where to access:** Select any event in the side panel, scroll to the **Planck Pyrometry** section.
- **Action:** View sub-pixel emitter temperature and area metrics.
- **Expected Output:** Solved flame temperature (e.g., $1120\text{K} / 847^\circ\text{C}$), background temperature ($298\text{K}$), subpixel combustion area ($18.5\,\text{m}^2$), and radiance inversion residuals.

### 4. Wind Vector Compass & Gaussian Dispersion Plume
- **Where to access:** Select any event in the side panel, scroll to **Wind Vector Intelligence** and **Hazard Dispersion**.
- **Action:** View the rotating 16-point meteorological compass and downwind corridor overlay on the map.
- **Expected Output:** Live wind speed/direction from Open-Meteo, downwind bearing, and colored multi-zone dispersion corridor (Red Isolation Zone, Orange Protective Action Zone, Yellow Plume Path).

### 5. Multi-Agency Emergency Responder Discovery & SMS/WhatsApp Dispatch
- **Where to access:** In the Event Intelligence Panel, scroll to **Emergency Response & Regulation**, click **Open Response Center**.
- **Action:** Enter a demo phone number, click **Notify via SMS** or **Notify via WhatsApp** on any discovered responder (Fire Station, Hazmat Unit, Police, Hospital).
- **Expected Output:** A structured confirmation modal appears with incident summary. Upon clicking **Confirm & Dispatch**, an instant notification is dispatched with delivery receipt and logged in the **Response Activity Feed**.

### 6. Tactical Incident Dossier Generation & PDF Export
- **Where to access:** In the Event Intelligence Panel, click the **Tactical Dossier** button (or header briefing button).
- **Action:** Click **Print / Export PDF** in the modal.
- **Expected Output:** An official, multi-agency Incident Briefing Document renders containing all incident metadata, chemical safety sheets, pyrometry metrics, and responder dispatches ready for immediate printing or PDF export.

### 7. AI Simulation Lab & What-If Scenario Sandbox
- **Where to access:** Click **AI Simulation Lab** in the top navigation bar.
- **Action:** Select a preset (e.g., *Jamnagar Refinery Flare*, *Vizag Polymer Gas Leak*, or *Punjab Stubble Burn*) or adjust sliders (FRP, Radiance, Distance to Facility, Wind Speed), then click **Run AI & Physics Simulation**.
- **Expected Output:** Instant real-time execution of the backend ML classification engine, Dozier pyrometry solver, and Gaussian plume model displaying predicted class, confidence, flame temperature, and plume length.

### 8. Global Forest Monitoring Hub & Threat Drawer
- **Where to access:** In the layer panel or top bar, navigate to the Forest Monitoring section / click **Forest Proximity** in any event card.
- **Action:** Select a forest reserve under threat, view boundary distance, and trigger a simulated ranger proximity alert.
- **Expected Output:** Global forest KPI cards update, geodesic boundary distance is calculated, and deduplicated ranger alerts are logged.

### 9. Interactive 12-Layer GIS Catalog & Metadata
- **Where to access:** Click **Layers** icon on the map control bar.
- **Action:** Search and toggle layers on/off (Thermal Detections, Industrial Facilities, Forest Reserves, Hazmat Sites). Click the **(i)** info icon on any layer.
- **Expected Output:** Map overlays toggle in real time, and the **Layer Metadata Modal** displays data provider, geometry type, update cadence, and scientific limitations.

---

# Known Gaps & Incomplete Integrations

1. **Continuous Live API Polling Daemon:** Ingestion scripts for NASA FIRMS and OpenStreetMap are executable via CLI scripts and API endpoints, but background continuous polling is not configured as an auto-started background daemon by default.
2. **Local Redis Requirement Bypass:** Background tasks run seamlessly using synchronous in-memory state machines by default to enable developer ease-of-use without forcing an active Redis service.
3. **Live GPS Vehicle Telemetry:** Emergency responder spatial discovery uses exact station/facility coordinates rather than real-time GPS feeds from mobile responder vehicles.

---

# Verification & Test Coverage Summary

The system is rigorously verified through an automated test suite comprising **60+ test suites** spanning all modules:

- **API Routes & Schemas:** [`tests/test_api_001_foundation.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_api_001_foundation.py) through [`test_api_012_layers.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_api_012_layers.py), [`test_schemas.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_schemas.py)
- **ML Training, Inference & Leakage:** [`tests/test_ml_leakage_safety.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_ml_leakage_safety.py), [`test_real_model_training.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_real_model_training.py), [`test_next_009_production_ml_runtime.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_next_009_production_ml_runtime.py)
- **Physics, Pyrometry & Plumes:** [`tests/test_planck_pyrometry.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_planck_pyrometry.py), [`test_dispersion_physics.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_dispersion_physics.py), [`test_dispersion_service_and_api.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_dispersion_service_and_api.py)
- **Weather & Wind Intelligence:** [`tests/test_weather_provider.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_weather_provider.py), [`test_weather_service_and_cache.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_weather_service_and_cache.py), [`test_weather_wind_math.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_weather_wind_math.py)
- **Forest Intelligence:** [`tests/test_forest_intelligence.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_forest_intelligence.py)
- **Emergency Escalation & Notifications:** [`tests/test_escalation_engine.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_escalation_engine.py), [`tests/test_emergency_responders.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_emergency_responders.py), [`tests/test_notification_engine.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_notification_engine.py)
- **Database & PostGIS:** [`tests/test_db_smoke.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_db_smoke.py), [`tests/test_migrations.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_migrations.py), [`tests/test_thermal_events_db.py`](file:///home/kafka/Coding/SIH-Hackathon/tests/test_thermal_events_db.py)
- **Frontend Unit & Integration Tests:** [`apps/web/src/__tests__/`](file:///home/kafka/Coding/SIH-Hackathon/apps/web/src/__tests__/) covering event feeds, XAI explanations, emergency response centers, and temporal playback.

---
*Document generated directly from active codebase inspection of repository `SANDILYA333/Ai-Flame-Detection`.*
