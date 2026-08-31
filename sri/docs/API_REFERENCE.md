# 📡 REST API Reference & Data Contracts

The PyroSat-AI backend exposes a high-performance REST API built with FastAPI and Uvicorn on **`http://localhost:8000`**. Interactive OpenAPI Swagger documentation is available at **`/docs`**.

---

## Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/thermal-events` | Retrieve precomputed, classified thermal events with filtering |
| `GET` | `/api/live-firms` | Ingest real-time NASA VIIRS NRT telemetry across India and classify |
| `POST` | `/api/classify` | Ad-hoc on-demand classification of a custom thermal coordinate |
| `GET` | `/api/incident-dossier/{case_id}` | Generate and download official 1-page Incident Action Plan PDF |
| `GET` | `/api/emergency-services` | Query nearest emergency facilities (Fire Commands, Burn ICUs, NDRF) |
| `GET` | `/api/historical-scenarios` | Retrieve benchmark ground-truth validation cases |
| `GET` | `/api/hazmat-profiles` | Query chemical sector hazard index and CAMEO ERG profiles |

---

## Detailed Endpoint Specifications

### 1. `GET /api/thermal-events`
Retrieve classified thermal detections across India.

**Query Parameters:**
* `limit` (integer, default: 1400, max: 1500): Number of records.
* `class_filter` (string, default: "ALL"): Filter by label (`ROUTINE_INDUSTRIAL_FLARING`, `INDUSTRIAL_ACCIDENTAL_DISASTER`, etc.).
* `region_split` (string, default: "ALL"): Filter by geographic sector.

**Response Schema (`GeoJSON FeatureCollection`):**
```json
{
  "type": "FeatureCollection",
  "total_count": 1400,
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [83.2185, 17.7607] },
      "properties": {
        "event_id": "EVT_001",
        "nearest_facility": "LG Polymers / HPCL Visakhapatnam Petrochem SEZ",
        "predicted_class_id": 1,
        "predicted_class_name": "INDUSTRIAL_ACCIDENTAL_DISASTER",
        "confidence_score": 94.2,
        "frp_mw": 142.5,
        "estimated_emitter_temp_k": 820.0,
        "estimated_emitter_area_m2": 4500.0,
        "dist_to_facility_km": 0.4,
        "hazard_dispersion": {
          "type": "Polygon",
          "coordinates": [[[83.218, 17.760], [83.225, 17.780], ...]]
        }
      }
    }
  ]
}
```

---

### 2. `POST /api/classify`
Executes multi-modal feature extraction and hierarchical classification on custom telemetry.

**Request Body (`application/json`):**
```json
{
  "latitude": 17.7607,
  "longitude": 83.2185,
  "bright_ti4": 384.2,
  "bright_ti5": 310.5,
  "frp": 142.5,
  "daynight": "D",
  "recurrence_90d": 0.05,
  "historical_mean_frp": 12.4,
  "historical_std_frp": 4.1,
  "sample_count_n": 48
}
```

**Response (`application/json`):**
```json
{
  "event_coordinates": [83.2185, 17.7607],
  "classification": {
    "predicted_class_id": 1,
    "predicted_class_name": "INDUSTRIAL_ACCIDENTAL_DISASTER",
    "color": "#EF4444",
    "confidence_score": 94.2,
    "confidence_band": "HIGH"
  },
  "physical_characterization": {
    "estimated_emitter_temp_k": 820.0,
    "estimated_emitter_area_m2": 4500.0,
    "frp_mw": 142.5
  },
  "spatial_attribution": {
    "nearest_facility": "LG Polymers / HPCL Visakhapatnam Petrochem SEZ",
    "dist_km": 0.4,
    "dominant_lulc": "BUILTUP"
  },
  "downwind_hazard": {
    "type": "Polygon",
    "coordinates": [...]
  }
}
```

---

### 3. `GET /api/incident-dossier/{case_id}`
Generates and downloads an official tactical PDF Incident Action Plan.

**Path Parameters:**
* `case_id` (string, e.g. `HIST_DISASTER_VIZAG_2020` or `INC-001`)

**Response:**
* Direct binary stream with `Content-Type: application/pdf` and `Content-Disposition: attachment; filename=...`.
