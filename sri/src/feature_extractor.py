"""
Standardized 26-Dimensional Event Feature Extraction Pipeline
Transforms raw satellite thermal observations, GIS facility networks, 10m LULC footprints,
and meteorology into an exact 26-dimensional machine learning feature vector.
"""

import numpy as np
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.planck_pyrometry import invert_dozier_subpixel
from src.spatiotemporal_engine import SpatialIntelligenceEngine
from src.lulc_engine import LULCEngine
from src.weather_plume_engine import get_live_meteorology

FEATURE_NAMES = [
    # 1. Thermal Physics (6)
    "frp_mw",
    "bright_mwir_k",
    "bright_lwir_k",
    "estimated_emitter_temp_k",
    "estimated_emitter_area_m2",
    "mwir_lwir_delta",
    
    # 2. Spatial Context (4)
    "dist_to_facility_km",
    "facility_type_code",
    "facility_polygon_overlap",
    "dist_to_mine_km",
    
    # 3. 10m LULC Footprint Fractions (4)
    "forest_fraction",
    "cropland_fraction",
    "builtup_fraction",
    "bare_fraction",
    
    # 4. Spatiotemporal Baselines & History (7)
    "recurrence_90d",
    "recurrence_365d",
    "day_night_flag",
    "historical_mean_frp",
    "historical_std_frp",
    "frp_z_score",
    "sample_count_n",
    
    # 5. Optical Spectral Context (3)
    "ndvi_val",
    "nbr_val",
    "swir_ratio_val",
    
    # 6. Meteorological Vector (2)
    "wind_u",
    "wind_v"
]

class FeatureExtractor:
    def __init__(self):
        self.spatial_engine = SpatialIntelligenceEngine()
        self.lulc_engine = LULCEngine()
        
        # Coal mining basins in India for dist_to_mine_km
        self.coal_basins = [
            {"name": "Jharia Coalfield", "lat": 23.74, "lon": 86.41},
            {"name": "Raniganj Coalfield", "lat": 23.62, "lon": 87.12},
            {"name": "Singrauli Coalfield", "lat": 24.20, "lon": 82.67},
            {"name": "Korba Coalfield", "lat": 22.35, "lon": 82.68}
        ]

    def extract_features(self, lat, lon, bright_ti4_k, bright_ti5_k, frp_mw, daynight='N', 
                         hist_recurrence_90d=0.0, hist_recurrence_365d=0.0,
                         hist_mean_frp=15.0, hist_std_frp=4.0, hist_sample_n=10):
        """
        Extracts full 26-dimensional standardized vector X from observation.
        """
        # 1. Thermal Physics
        temp_k, area_m2 = invert_dozier_subpixel(bright_ti4_k, bright_ti5_k)
        mwir_lwir_delta = bright_ti4_k - bright_ti5_k
        
        # 2. Spatial Context
        nearest_fac = self.spatial_engine.query_nearest_facility(lat, lon)
        dist_fac_km = nearest_fac['dist_km']
        fac_type = nearest_fac['facility_type']
        
        # Encode facility type
        type_code = 0
        if "Oil" in fac_type or "Refinery" in fac_type:
            type_code = 1
        elif "Power" in fac_type:
            type_code = 2
        elif "Steel" in fac_type or "Iron" in fac_type:
            type_code = 3
        elif "Chemical" in fac_type:
            type_code = 4
            
        polygon_overlap = 1.0 if dist_fac_km <= 0.8 else 0.0
        
        # Distance to coal basin
        min_mine_dist = min([
            np.sqrt((lat - m['lat'])**2 + (lon - m['lon'])**2) * 111.0
            for m in self.coal_basins
        ])
        
        # 3. LULC Footprint Fractions
        lulc_res = self.lulc_engine.compute_footprint_fractions(lat, lon, dist_to_facility_km=dist_fac_km)
        
        # 4. Spatiotemporal Baselines
        dn_flag = 1.0 if daynight == 'D' else 0.0
        if hist_std_frp <= 0:
            hist_std_frp = 1.0
        z_score = (frp_mw - hist_mean_frp) / hist_std_frp
        
        # 5. Optical Spectral Context (Derived from vegetation & combustion signature)
        # NDVI: (NIR - Red)/(NIR + Red) -> high in forest, medium in agro, near-zero in built-up
        ndvi_val = np.clip(lulc_res['forest_fraction'] * 0.82 + lulc_res['cropland_fraction'] * 0.55 - lulc_res['builtup_fraction'] * 0.20, -0.1, 0.9)
        # NBR: (NIR - SWIR)/(NIR + SWIR) -> drops strongly in active burn scars
        nbr_val = np.clip(ndvi_val - (frp_mw / 250.0), -0.5, 0.8)
        # SWIR Ratio: SWIR2/SWIR1 -> high in localized hot gas flaring
        swir_ratio = np.clip((temp_k - 600.0) / 1000.0 + 0.3, 0.1, 2.5)
        
        # 6. Meteorological Vectors
        met = get_live_meteorology(lat, lon)
        w_speed = met['wind_speed_ms']
        w_dir_rad = np.radians(met['wind_direction_deg'])
        wind_u = w_speed * np.cos(w_dir_rad)
        wind_v = w_speed * np.sin(w_dir_rad)
        
        # Assemble 26-D Vector
        vector_dict = {
            "frp_mw": round(float(frp_mw), 2),
            "bright_mwir_k": round(float(bright_ti4_k), 2),
            "bright_lwir_k": round(float(bright_ti5_k), 2),
            "estimated_emitter_temp_k": round(float(temp_k), 1),
            "estimated_emitter_area_m2": round(float(area_m2), 2),
            "mwir_lwir_delta": round(float(mwir_lwir_delta), 2),
            
            "dist_to_facility_km": round(float(dist_fac_km), 2),
            "facility_type_code": float(type_code),
            "facility_polygon_overlap": float(polygon_overlap),
            "dist_to_mine_km": round(float(min_mine_dist), 2),
            
            "forest_fraction": lulc_res['forest_fraction'],
            "cropland_fraction": lulc_res['cropland_fraction'],
            "builtup_fraction": lulc_res['builtup_fraction'],
            "bare_fraction": lulc_res['bare_fraction'],
            
            "recurrence_90d": round(float(hist_recurrence_90d), 3),
            "recurrence_365d": round(float(hist_recurrence_365d), 3),
            "day_night_flag": float(dn_flag),
            "historical_mean_frp": round(float(hist_mean_frp), 2),
            "historical_std_frp": round(float(hist_std_frp), 2),
            "frp_z_score": round(float(z_score), 2),
            "sample_count_n": float(hist_sample_n),
            
            "ndvi_val": round(float(ndvi_val), 3),
            "nbr_val": round(float(nbr_val), 3),
            "swir_ratio_val": round(float(swir_ratio), 3),
            
            "wind_u": round(float(wind_u), 2),
            "wind_v": round(float(wind_v), 2)
        }
        
        feature_array = np.array([vector_dict[name] for name in FEATURE_NAMES], dtype=np.float32)
        
        return {
            "feature_array": feature_array,
            "feature_dict": vector_dict,
            "metadata": {
                "nearest_facility": nearest_fac['facility_name'],
                "dominant_lulc": lulc_res['dominant_class'],
                "wind_speed_ms": w_speed,
                "wind_dir_deg": met['wind_direction_deg']
            }
        }

if __name__ == "__main__":
    extractor = FeatureExtractor()
    feat = extractor.extract_features(
        lat=22.38, lon=69.87, bright_ti4_k=368.0, bright_ti5_k=304.0, frp_mw=18.5,
        daynight='N', hist_recurrence_90d=0.94, hist_mean_frp=17.0, hist_std_frp=3.5
    )
    print(f"✅ Extracted Feature Vector Dimension: {len(feat['feature_array'])} (Expected: 26)")
    print("Feature Names & Values:")
    for k, v in feat['feature_dict'].items():
        print(f"  • {k:28s}: {v}")
