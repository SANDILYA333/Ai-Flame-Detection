"""
NASA FIRMS Active Thermal Anomaly Stream Engine
Integrates:
1. NASA FIRMS Country Archive Download: VIIRS (NOAA-20 / Suomi-NPP 375m) & MODIS (1km) historical CSVs.
2. NASA FIRMS Near-Real-Time REST API: Live 24-48h streaming of thermal fire pixels with MAP_KEY support.
"""

import os
import requests
import pandas as pd
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_THERMAL_DIR = os.path.join(BASE_DIR, "data/raw_thermal")


class FirmsStreamEngine:
    """
    Downloader and parser for NASA FIRMS satellite thermal anomalies.
    """

    def __init__(self, map_key: Optional[str] = None):
        self.map_key = map_key or os.environ.get("FIRMS_MAP_KEY", "DEMO_KEY")
        self.base_api_url = "https://firms.modaps.eosdis.nasa.gov/api/country/csv"

    def fetch_nrt_feed_india(self, source: str = "VIIRS_NOAA20_NRT", days: int = 1) -> pd.DataFrame:
        """
        Fetches live Near-Real-Time thermal detections for India from NASA FIRMS API.
        Sources: VIIRS_NOAA20_NRT, VIIRS_SNPP_NRT, MODIS_NRT
        """
        url = f"{self.base_api_url}/{self.map_key}/{source}/IND/{days}"
        try:
            resp = requests.get(url, timeout=12)
            if resp.status_code == 200 and "latitude" in resp.text:
                from io import StringIO
                df = pd.read_csv(StringIO(resp.text))
                return df
        except Exception as e:
            print(f"Warning: Live FIRMS API fetch failed ({e}). Falling back to local offline archive.")

        # Fallback: Load latest local NRT slice from data/raw_thermal
        fallback_file = os.path.join(RAW_THERMAL_DIR, "fire_nrt_J1V-C2_792517.csv")
        if os.path.exists(fallback_file):
            return pd.read_csv(fallback_file, nrows=1000)

        return pd.DataFrame()

    def parse_archive_stream(self, max_records: int = 50000) -> pd.DataFrame:
        """
        Loads and standardizes multi-year archive CSVs from data/raw_thermal/.
        """
        archive_files = [
            os.path.join(RAW_THERMAL_DIR, "fire_archive_J1V-C2_792517.csv"),
            os.path.join(RAW_THERMAL_DIR, "fire_archive_SV-C2_792518.csv")
        ]

        dfs = []
        for file_path in archive_files:
            if os.path.exists(file_path):
                print(f"Ingesting NASA FIRMS Archive: {os.path.basename(file_path)}...")
                chunk = pd.read_csv(file_path, nrows=max_records)
                
                # Standardize column names
                rename_map = {}
                if "brightness" in chunk.columns:
                    rename_map["brightness"] = "brightness_mid_ir_k"
                elif "bright_ti4" in chunk.columns:
                    rename_map["bright_ti4"] = "brightness_mid_ir_k"
                    
                if "bright_t31" in chunk.columns:
                    rename_map["bright_t31"] = "brightness_thermal_ir_k"
                elif "bright_ti5" in chunk.columns:
                    rename_map["bright_ti5"] = "brightness_thermal_ir_k"
                    
                if "frp" in chunk.columns:
                    rename_map["frp"] = "frp_mw"
                    
                chunk.rename(columns=rename_map, inplace=True)
                dfs.append(chunk)

        if not dfs:
            return pd.DataFrame()

        combined = pd.concat(dfs, ignore_index=True)
        print(f"✅ Successfully loaded {len(combined):,} raw NASA FIRMS detections.")
        return combined


if __name__ == "__main__":
    engine = FirmsStreamEngine()
    df = engine.parse_archive_stream(max_records=1000)
    print("=== NASA FIRMS THERMAL STREAM SAMPLE ===")
    print(df.head(5))
