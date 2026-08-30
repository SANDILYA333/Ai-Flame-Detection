"""
Emergency Services Spatial Harvester & Nearest-Station Matcher (OSM / Overpass)
Fetches and indexes Fire Stations, Apex Hospitals, and Disaster Units across India.
"""

import os
import sys
import json
import requests
import numpy as np
from sklearn.neighbors import BallTree

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUTPUT_GEOJSON = os.path.join(BASE_DIR, "data/industrial_infra/osm_emergency_facilities.geojson")
REGISTRY_JSON = os.path.join(BASE_DIR, "data/industrial_infra/emergency_services_india.json")

# Key Industrial Clusters in India (South, West, North, East Bounding Boxes)
INDUSTRIAL_BBOXES = [
    ("Gujarat_Petrochem_Hazira_Jamnagar", "21.0,69.0,23.5,73.5"),
    ("Mumbai_Thane_Raigad_Corridor", "18.5,72.5,19.5,73.5"),
    ("Vizag_Kakinada_PCPIR", "16.8,82.0,18.2,83.5"),
    ("TamilNadu_Manali_Ennore", "12.8,79.8,13.5,80.4"),
    ("Odisha_Paradip_Angul", "20.0,84.5,21.2,87.0"),
    ("Singrauli_Korba_Energy_Belt", "22.0,82.0,24.5,83.5"),
    ("Delhi_NCR_Sitapura_Industrial", "26.5,75.5,28.8,77.5"),
    ("Bengal_Haldia_Durgapur_Asansol", "21.8,86.8,23.8,88.5")
]

def fetch_osm_emergency_services():
    """
    Queries OpenStreetMap Overpass API for Fire Stations and Hospitals in industrial clusters.
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    all_features = []
    
    print("📡 Querying OpenStreetMap for Fire Stations & Hospitals across industrial belts...")
    
    for cluster_name, bbox in INDUSTRIAL_BBOXES:
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="fire_station"]({bbox});
          way["amenity"="fire_station"]({bbox});
          node["amenity"="hospital"]({bbox});
          way["amenity"="hospital"]({bbox});
        );
        out center;
        """
        try:
            resp = requests.post(overpass_url, data={'data': query}, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get('elements', [])
                for el in elements:
                    lat = el.get('lat') or el.get('center', {}).get('lat')
                    lon = el.get('lon') or el.get('center', {}).get('lon')
                    tags = el.get('tags', {})
                    amenity = tags.get('amenity', 'emergency')
                    name = tags.get('name') or tags.get('name:en') or f"Regional {amenity.replace('_', ' ').title()}"
                    phone = tags.get('phone') or tags.get('contact:phone') or tags.get('emergency:phone') or "+91-101 (Fire Control)"
                    
                    if lat and lon:
                        all_features.append({
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [float(lon), float(lat)]
                            },
                            "properties": {
                                "id": el.get('id'),
                                "amenity": amenity,
                                "name": name,
                                "phone": phone,
                                "operator": tags.get('operator', 'Government / Municipal'),
                                "cluster_region": cluster_name
                            }
                        })
                print(f"  -> {cluster_name}: Found {len(elements)} emergency facilities.")
            else:
                print(f"  -> {cluster_name}: API busy, using cached data.")
        except Exception as e:
            print(f"  -> {cluster_name}: Fetch exception ({e}), continuing...")
            
    # Fallback / Seed essential regional stations if network timed out
    if len(all_features) < 10 and os.path.exists(REGISTRY_JSON):
        with open(REGISTRY_JSON) as f:
            registry = json.load(f)
            for r in registry:
                all_features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [r["longitude"], r["latitude"]]},
                    "properties": {
                        "amenity": "fire_station",
                        "name": r["fire_station_hq"],
                        "phone": r["phone"],
                        "cluster_region": r["cluster_name"],
                        "hospital_name": r["nearest_apex_burn_hospital"],
                        "hospital_phone": r["hospital_phone"],
                        "ndrf": r["ndrf_battalion"]
                    }
                })

    geojson_data = {
        "type": "FeatureCollection",
        "total_facilities": len(all_features),
        "features": all_features
    }
    
    with open(OUTPUT_GEOJSON, 'w') as f:
        json.dump(geojson_data, f, indent=2)
        
    print(f"✅ Saved {len(all_features)} Emergency Facilities to: {OUTPUT_GEOJSON}")
    return geojson_data


class SpatialEmergencyMatcher:
    """
    Fast nearest-neighbor spatial index (BallTree in Haversine radians)
    """
    def __init__(self, geojson_path=OUTPUT_GEOJSON):
        self.facilities = []
        self.tree = None
        if os.path.exists(geojson_path):
            with open(geojson_path) as f:
                data = json.load(f)
                self.facilities = data.get("features", [])
                
        if self.facilities:
            coords_rad = np.radians([
                [f['geometry']['coordinates'][1], f['geometry']['coordinates'][0]] # [lat, lon]
                for f in self.facilities
            ])
            self.tree = BallTree(coords_rad, metric='haversine')
            print(f"📍 Indexed {len(self.facilities)} Emergency Stations into Spatial BallTree.")
            
    def find_nearest_emergency(self, lat, lon, k=3):
        """
        Returns the k nearest emergency facilities with distances in km
        """
        if not self.tree or not self.facilities:
            return []
            
        point_rad = np.radians([[lat, lon]])
        dist_rad, indices = self.tree.query(point_rad, k=min(k, len(self.facilities)))
        
        results = []
        EARTH_RADIUS_KM = 6371.0
        for i, idx in enumerate(indices[0]):
            fac = self.facilities[idx]
            dist_km = dist_rad[0][i] * EARTH_RADIUS_KM
            results.append({
                "name": fac['properties'].get('name', 'Emergency Station'),
                "amenity": fac['properties'].get('amenity', 'emergency'),
                "phone": fac['properties'].get('phone', '+91-101'),
                "distance_km": round(dist_km, 2),
                "coordinates": fac['geometry']['coordinates'],
                "cluster": fac['properties'].get('cluster_region', 'National')
            })
        return results

if __name__ == "__main__":
    fetch_osm_emergency_services()
    
    # Test with Jamnagar Refinery Coordinates (22.35°N, 69.86°E)
    matcher = SpatialEmergencyMatcher()
    nearest = matcher.find_nearest_emergency(22.3556, 69.8653, k=2)
    print("\n🔍 Test Spatial Match for Jamnagar Refinery (22.3556, 69.8653):")
    for s in nearest:
        print(f"  🚒 {s['name']} ({s['amenity']}) - Distance: {s['distance_km']} km | Phone: {s['phone']}")
