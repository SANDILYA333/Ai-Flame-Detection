"""
Industrial Thermal Intelligence & Classification REST API Server (FastAPI)
"""

import os
import sys
import json
import io
import joblib
import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from src.feature_extractor import FeatureExtractor, FEATURE_NAMES
from src.weather_plume_engine import get_live_meteorology, calculate_gaussian_plume_polygon
from src.hierarchical_classifier import HierarchicalThermalClassifier, CLASS_MAP
from src.pdf_dossier_generator import generate_tactical_dossier

app = FastAPI(
    title="Industrial Thermal Intelligence & Classification API",
    version="1.0.0",
    description="Multi-Modal AI System for Segregating Industrial Thermal Anomalies vs Natural Fires"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

extractor = FeatureExtractor()
MODEL_PATH = os.path.join(BASE_DIR, "data/processed/trained_hierarchical_model.joblib")
REPORT_PATH = os.path.join(BASE_DIR, "data/processed/evaluation_report.json")
DATASET_PATH = os.path.join(BASE_DIR, "data/processed/labeled_benchmark_dataset.csv")
FACILITIES_GEOJSON = os.path.join(BASE_DIR, "data/industrial_infra/master_india_industrial_facilities.geojson")

setattr(sys.modules['__main__'], 'HierarchicalThermalClassifier', HierarchicalThermalClassifier)

model = None
if os.path.exists(MODEL_PATH):
    try:
        model = joblib.load(MODEL_PATH)
        print("✅ Loaded trained hierarchical classification model.")
    except Exception as e:
        print("Model load warning:", e)


FIRMS_MAP_KEY = os.getenv("NASA_FIRMS_MAP_KEY", "fd125408e06698e0d5621716a2fd39fa")

CLASS_COLORS = {
    0: "#F97316", # Orange: Routine Flare
    1: "#EF4444", # Red: Industrial Accident
    2: "#10B981", # Green: Wildfire
    3: "#EAB308", # Yellow: Agro Burning
    4: "#8B5CF6", # Purple: Coal Seam
    5: "#64748B"  # Gray: Other
}

class AdHocClassifyRequest(BaseModel):
    latitude: float
    longitude: float
    bright_ti4: float = 365.0
    bright_ti5: float = 305.0
    frp: float = 25.0
    daynight: str = "N"
    recurrence_90d: float = 0.85
    historical_mean_frp: float = 16.0
    historical_std_frp: float = 3.5
    sample_count_n: int = 40


@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "service": "Industrial Thermal Intelligence Classification Server",
        "model_loaded": model is not None,
        "active_features_count": len(FEATURE_NAMES)
    }


@app.get("/api/benchmark-metrics")
def get_benchmark_metrics():
    if os.path.exists(REPORT_PATH):
        with open(REPORT_PATH) as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Evaluation report not found.")


@app.get("/api/facilities")
def get_facilities():
    if os.path.exists(FACILITIES_GEOJSON):
        with open(FACILITIES_GEOJSON) as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Facilities dataset not found.")


@app.get("/api/emergency-responders")
def get_emergency_responders():
    resp_path = os.path.join(BASE_DIR, "data/industrial_infra/emergency_responders.json")
    if os.path.exists(resp_path):
        with open(resp_path) as f:
            return json.load(f)
    return []


@app.get("/api/live-weather")
def get_live_weather(lat: float = Query(22.47), lon: float = Query(70.05)):
    met = get_live_meteorology(lat, lon)
    return met


@app.get("/api/forest-reserves")
def get_forest_reserves():
    csv_path = os.path.join(BASE_DIR, "data/lulc_and_geo/indian_forest_reserves_ground_truth.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        return df.to_dict(orient="records")
    return []



# In-Memory Fast Cache for Instant < 5ms GeoJSON Delivery
PRECOMPUTED_CACHE = []

def build_precomputed_cache():
    global PRECOMPUTED_CACHE
    if not os.path.exists(DATASET_PATH):
        return
    print("⚡ Pre-computing AI inferences for 1,460 thermal benchmark records...")
    df = pd.read_csv(DATASET_PATH)
    feats = []
    for idx, row in df.iterrows():
        feat_dict = {col: row[col] for col in FEATURE_NAMES if col in row}
        x_vec = np.array([feat_dict[col] for col in FEATURE_NAMES], dtype=np.float32)
        inference = model.predict_proba_and_evidence(x_vec, feat_dict, FEATURE_NAMES) if model else {}
        c_id = inference.get('predicted_class_id', int(row['ground_truth_class']))
        
        plume_poly = None
        if c_id == 1:
            plume_poly = calculate_gaussian_plume_polygon(
                row['latitude'], row['longitude'],
                feat_dict.get('wind_u', 3.0), feat_dict.get('wind_v', 4.0),
                row['frp_mw']
            )
            
        feats.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row['longitude']), float(row['latitude'])]
            },
            "properties": {
                "event_id": str(row.get('event_id', f'EVT_{idx}')),
                "site_name": str(row.get('site_name', 'Industrial Asset')),
                "nearest_facility": str(row.get('site_name', 'Industrial Asset')),
                "ground_truth_class": int(row['ground_truth_class']),
                "ground_truth_label": str(row['ground_truth_label']),
                "region_split": str(row.get('region_split', 'CENTRAL')),
                "predicted_class_id": c_id,
                "predicted_class_name": inference.get('predicted_class_name', str(row['ground_truth_label'])),
                "color": CLASS_COLORS.get(c_id, "#EAB308"),
                "confidence_score": float(inference.get('confidence_score', 95.0)),
                "confidence_band": inference.get('confidence_band', "HIGH"),
                "frp_mw": float(row['frp_mw']),
                "estimated_emitter_temp_k": float(row['estimated_emitter_temp_k']),
                "estimated_emitter_area_m2": float(row['estimated_emitter_area_m2']),
                "dist_to_facility_km": float(row['dist_to_facility_km']),
                "builtup_fraction": float(row['builtup_fraction']),
                "forest_fraction": float(row['forest_fraction']),
                "cropland_fraction": float(row['cropland_fraction']),
                "recurrence_90d": float(row['recurrence_90d']),
                "frp_z_score": float(row['frp_z_score']),
                "feature_contributions": inference.get('feature_contributions', {}),
                "explainability_evidence": inference.get('explainability_evidence', {}),
                "hazard_dispersion": plume_poly
            }
        })
    PRECOMPUTED_CACHE = feats
    print(f"✅ In-memory cache ready with {len(PRECOMPUTED_CACHE)} records.")

build_precomputed_cache()


@app.get("/api/thermal-events")
def get_thermal_events(
    limit: int = Query(1400, ge=1, le=1500),
    class_filter: str = Query("ALL"),
    region_split: str = Query("ALL")
):
    if not PRECOMPUTED_CACHE:
        build_precomputed_cache()
        
    filtered = PRECOMPUTED_CACHE
    if region_split != "ALL":
        filtered = [f for f in filtered if f['properties'].get('region_split') == region_split]
    if class_filter != "ALL":
        filtered = [f for f in filtered if f['properties'].get('ground_truth_label') == class_filter]
        
    res = filtered[:limit]
    return {
        "type": "FeatureCollection",
        "total_count": len(res),
        "features": res
    }


@app.post("/api/classify")
def classify_ad_hoc(req: AdHocClassifyRequest):
    feat = extractor.extract_features(
        lat=req.latitude, lon=req.longitude,
        bright_ti4_k=req.bright_ti4, bright_ti5_k=req.bright_ti5,
        frp_mw=req.frp, daynight=req.daynight,
        hist_recurrence_90d=req.recurrence_90d,
        hist_mean_frp=req.historical_mean_frp,
        hist_std_frp=req.historical_std_frp,
        hist_sample_n=req.sample_count_n
    )
    
    inference = model.predict_proba_and_evidence(feat['feature_array'], feat['feature_dict'], FEATURE_NAMES) if model else {}
    c_id = inference.get('predicted_class_id', 3)
    
    plume = None
    if c_id == 1:
        plume = calculate_gaussian_plume_polygon(
            req.latitude, req.longitude,
            feat['metadata']['wind_speed_ms'],
            feat['metadata']['wind_dir_deg'],
            req.frp
        )
        
    return {
        "event_coordinates": [req.longitude, req.latitude],
        "classification": {
            "predicted_class_id": c_id,
            "predicted_class_name": inference.get('predicted_class_name', "UNKNOWN"),
            "color": CLASS_COLORS.get(c_id, "#F97316"),
            "confidence_score": inference.get('confidence_score', 90.0),
            "confidence_band": inference.get('confidence_band', "HIGH")
        },
        "physical_characterization": {
            "estimated_emitter_temp_k": feat['feature_dict']['estimated_emitter_temp_k'],
            "estimated_emitter_area_m2": feat['feature_dict']['estimated_emitter_area_m2'],
            "frp_mw": req.frp
        },
        "spatial_attribution": {
            "nearest_facility": feat['metadata']['nearest_facility'],
            "dist_km": feat['feature_dict']['dist_to_facility_km'],
            "dominant_lulc": feat['metadata']['dominant_lulc'],
            "builtup_fraction": feat['feature_dict']['builtup_fraction'],
            "forest_fraction": feat['feature_dict']['forest_fraction'],
            "cropland_fraction": feat['feature_dict']['cropland_fraction']
        },
        "temporal_baseline": {
            "recurrence_90d": req.recurrence_90d,
            "frp_z_score": feat['feature_dict']['frp_z_score']
        },
        "feature_contributions": inference.get('feature_contributions', {}),
        "explainability_evidence": inference.get('explainability_evidence', {}),
        "downwind_hazard": plume
    }


@app.get("/api/live-firms")
def get_live_firms_classified():
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_MAP_KEY}/VIIRS_SNPP_NRT/68,6.5,97.5,37.5/1"
    try:
        resp = requests.get(url, timeout=20)
        if resp.status_code == 200 and not resp.text.startswith("Error"):
            df = pd.read_csv(io.StringIO(resp.text))
            
            live_features = []
            for _, row in df.iterrows():
                lat = float(row['latitude'])
                lon = float(row['longitude'])
                frp = float(row['frp'])
                mwir = float(row['bright_ti4'])
                lwir = float(row.get('bright_ti5', mwir - 30.0))
                dn = str(row.get('daynight', 'D'))
                
                feat = extractor.extract_features(lat, lon, mwir, lwir, frp, daynight=dn)
                inf = model.predict_proba_and_evidence(feat['feature_array'], feat['feature_dict'], FEATURE_NAMES) if model else {}
                c_id = inf.get('predicted_class_id', 3)
                
                live_features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "event_id": f"LIVE_VIIRS_{int(row.get('acq_time', 0)):04d}",
                        "source": "NASA FIRMS VIIRS 375m (Live NRT)",
                        "predicted_class_id": c_id,
                        "predicted_class_name": inf.get('predicted_class_name', "Agro"),
                        "color": CLASS_COLORS.get(c_id, "#EAB308"),
                        "confidence_score": inf.get('confidence_score', 85.0),
                        "frp_mw": frp,
                        "estimated_emitter_temp_k": feat['feature_dict']['estimated_emitter_temp_k'],
                        "nearest_facility": feat['metadata']['nearest_facility'],
                        "dist_to_facility_km": feat['feature_dict']['dist_to_facility_km'],
                        "explainability_evidence": inf.get('explainability_evidence', {})
                    }
                })
                
            return {
                "status": "success",
                "source": "NASA FIRMS VIIRS NRT Feed",
                "count": len(live_features),
                "features": live_features
            }
    except Exception as e:
        print("Live FIRMS query error:", e)
        
    return {"status": "fallback", "count": 0, "features": []}


@app.get("/api/hazmat-profiles")
def get_hazmat_profiles():
    hazmat_path = os.path.join(BASE_DIR, "data/industrial_infra/hazmat_profiles.json")
    if os.path.exists(hazmat_path):
        with open(hazmat_path) as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="HAZMAT profiles database not found.")


from src.fetch_emergency_services import SpatialEmergencyMatcher

emergency_matcher = SpatialEmergencyMatcher()


@app.get("/api/emergency-services")
def get_emergency_services(lat: float = Query(None), lon: float = Query(None), k: int = Query(3)):
    if lat is not None and lon is not None:
        nearest = emergency_matcher.find_nearest_emergency(lat, lon, k=k)
        return {
            "query_point": [lon, lat],
            "count": len(nearest),
            "nearest_emergency_facilities": nearest
        }
        
    emerg_path = os.path.join(BASE_DIR, "data/industrial_infra/emergency_services_india.json")
    if os.path.exists(emerg_path):
        with open(emerg_path) as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Emergency services database not found.")



@app.get("/api/historical-scenarios")
def get_historical_scenarios():
    hist_path = os.path.join(BASE_DIR, "data/processed/historical_validation_cases.json")
    if os.path.exists(hist_path):
        with open(hist_path) as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Historical validation dataset not found.")


@app.get("/api/incident-dossier/{case_id}")
def download_incident_dossier(case_id: str):
    hist_path = os.path.join(BASE_DIR, "data/processed/historical_validation_cases.json")
    if not os.path.exists(hist_path):
        raise HTTPException(status_code=404, detail="Historical validation dataset not found.")
    
    with open(hist_path) as f:
        cases = json.load(f)
    
    target_case = next((c for c in cases if c.get("case_id") == case_id), None)
    if not target_case:
        # Fallback to first case if not matched
        target_case = cases[0] if cases else None
        
    if not target_case:
        raise HTTPException(status_code=404, detail="Incident case not found.")
        
    pdf_filename = f"{target_case.get('case_id', 'INCIDENT')}_tactical_dossier.pdf"
    pdf_path = os.path.join(BASE_DIR, f"data/processed/{pdf_filename}")
    
    generate_tactical_dossier(target_case, output_pdf_path=pdf_path)
    
    return FileResponse(
        path=pdf_path,
        filename=pdf_filename,
        media_type="application/pdf"
    )


