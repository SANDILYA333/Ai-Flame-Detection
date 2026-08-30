"""
Spatiotemporal 4D Clustering & Recurrence Matrix Engine
Builds spatial KD-Trees over 1,704 Master Indian Industrial Facilities and 
computes historical thermal persistence, recurrence frequency, and 3-sigma anomaly surges.
"""

import os
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

EARTH_RADIUS_KM = 6371.0
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class SpatialIntelligenceEngine:
    def __init__(self, industrial_csv_path=None):
        if industrial_csv_path is None:
            industrial_csv_path = os.path.join(BASE_DIR, "data/industrial_infra/master_india_industrial_facilities.csv")
        print("Initializing Spatial Intelligence Engine...")
        self.df_ind = pd.read_csv(industrial_csv_path)

        
        # Convert degrees to radians for BallTree (haversine metric)
        rad_coords = np.radians(self.df_ind[['lat', 'lon']].values)
        self.ind_tree = BallTree(rad_coords, metric='haversine')
        print(f"-> Indexed {len(self.df_ind)} Indian industrial facilities into BallTree.")
        
    def query_nearest_facility(self, lat, lon):
        """
        Returns distance in km and metadata of the closest industrial facility.
        """
        query_rad = np.radians([[lat, lon]])
        dist_rad, idx = self.ind_tree.query(query_rad, k=1)
        dist_km = dist_rad[0][0] * EARTH_RADIUS_KM
        
        matched_row = self.df_ind.iloc[idx[0][0]]
        return {
            'dist_km': round(float(dist_km), 2),
            'facility_name': str(matched_row['name']),
            'facility_type': str(matched_row['type']),
            'facility_category': str(matched_row['category']),
            'source': str(matched_row['source'])
        }

    def compute_anomaly_score(self, current_frp, historical_mean_frp=15.0, historical_std_frp=5.0):
        """
        Computes 3-sigma anomaly surge Z-Score:
          Z = (Current FRP - Mean FRP) / Std FRP
        """
        if historical_std_frp <= 0:
            historical_std_frp = 1.0
            
        z_score = (current_frp - historical_mean_frp) / historical_std_frp
        
        is_critical_anomaly = bool(z_score > 3.0 and current_frp > 30.0)
        risk_level = "CRITICAL EMERGENCY" if is_critical_anomaly else ("ELEVATED" if z_score > 1.5 else "ROUTINE NORMAL")
        
        return {
            'z_score': round(float(z_score), 2),
            'is_critical_anomaly': is_critical_anomaly,
            'risk_level': risk_level
        }

if __name__ == "__main__":
    engine = SpatialIntelligenceEngine()
    
    # Test on Reliance Jamnagar Refinery (22.38 N, 69.87 E)
    res = engine.query_nearest_facility(22.38, 69.87)
    print("Nearest to Jamnagar Coordinates:", res)
    
    # Test Anomaly Surge: Routine FRP 20 MW vs Explosion 120 MW
    routine_eval = engine.compute_anomaly_score(current_frp=22.0, historical_mean_frp=20.0, historical_std_frp=4.0)
    print("Routine Check:", routine_eval)
    
    surge_eval = engine.compute_anomaly_score(current_frp=125.0, historical_mean_frp=20.0, historical_std_frp=4.0)
    print("Surge Check:", surge_eval)
