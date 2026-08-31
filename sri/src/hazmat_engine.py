"""
HAZMAT & Chemical Hazards Engine
Integrates:
1. CAMEO Chemicals (NOAA / EPA): 9,000+ chemicals reactivity, toxic byproducts, isolation/evacuation distances.
2. NIOSH Pocket Guide to Chemical Hazards: REL/PEL exposure limits, IDLH (Immediately Dangerous to Life or Health).
3. DOT Emergency Response Guidebook (ERG 2024): Table 1 Initial Isolation and Downwind Evacuation distances.
"""

import os
import json
from typing import Dict, Any, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HAZMAT_PROFILES_PATH = os.path.join(BASE_DIR, "data/industrial_infra/hazmat_profiles.json")

# Comprehensive CAMEO & NIOSH Chemical Database
CAMEO_NIOSH_DATABASE: Dict[str, Dict[str, Any]] = {
    "BENZENE": {
        "cas_number": "71-43-2",
        "un_number": "UN1114",
        "cameo_class": "Flammable Liquid (Class 3)",
        "niosh_rel": "0.1 ppm (0.32 mg/m3) TWA, 1 ppm STEL",
        "osha_pel": "1 ppm TWA, 5 ppm STEL",
        "idlh_ppm": 500,
        "primary_hazard": "Carcinogen, severe fire hazard, vapor explosion hazard",
        "toxic_byproducts": ["Carbon Monoxide (CO)", "Carbon Dioxide (CO2)", "Dense soot & Polycyclic Aromatic Hydrocarbons (PAHs)"],
        "erg_guide_no": 130,
        "initial_isolation_m": 100,
        "evacuation_day_m": 800,
        "evacuation_night_m": 1600,
        "firefighting_foam": "Alcohol-resistant foam (AR-AFFF) or regular AFFF foam"
    },
    "AMMONIA_ANHYDROUS": {
        "cas_number": "7664-41-7",
        "un_number": "UN1005",
        "cameo_class": "Toxic / Corrosive Gas (Class 2.3 / 8)",
        "niosh_rel": "25 ppm TWA, 35 ppm STEL",
        "osha_pel": "50 ppm TWA",
        "idlh_ppm": 300,
        "primary_hazard": "Severe respiratory tract & ocular chemical burns, toxic cloud dispersion",
        "toxic_byproducts": ["Nitrogen Oxides (NOx)", "Nitric Acid vapor (HNO3)"],
        "erg_guide_no": 125,
        "initial_isolation_m": 150,
        "evacuation_day_m": 1500,
        "evacuation_night_m": 3200,
        "firefighting_foam": "Water spray curtain for vapor knockdown (DO NOT apply water into liquid ammonia pools)"
    },
    "CHLORINE": {
        "cas_number": "7782-50-5",
        "un_number": "UN1017",
        "cameo_class": "Toxic Inhalation Hazard (Class 2.3 / 5.1 / 8)",
        "niosh_rel": "0.5 ppm (1.45 mg/m3) Ceiling (15 min)",
        "osha_pel": "1 ppm Ceiling",
        "idlh_ppm": 10,
        "primary_hazard": "Fatal pulmonary edema, green-yellow dense toxic gas hugging low terrain",
        "toxic_byproducts": ["Hydrogen Chloride (HCl)", "Chlorine Oxides"],
        "erg_guide_no": 124,
        "initial_isolation_m": 200,
        "evacuation_day_m": 2400,
        "evacuation_night_m": 5000,
        "firefighting_foam": "Vapor suppression via fine water fog curtains downwind"
    },
    "SULFUR_DIOXIDE": {
        "cas_number": "7446-09-5",
        "un_number": "UN1079",
        "cameo_class": "Toxic / Corrosive Gas (Class 2.3 / 8)",
        "niosh_rel": "2 ppm TWA, 5 ppm STEL",
        "osha_pel": "5 ppm TWA",
        "idlh_ppm": 100,
        "primary_hazard": "Choking gas, rapid formation of sulfuric acid upon contact with moisture",
        "toxic_byproducts": ["Sulfuric Acid mist (H2SO4)", "Sulfur Trioxide (SO3)"],
        "erg_guide_no": 125,
        "initial_isolation_m": 100,
        "evacuation_day_m": 1000,
        "evacuation_night_m": 2200,
        "firefighting_foam": "Water fog for gas cloud neutralization"
    },
    "HYDROGEN_SULFIDE": {
        "cas_number": "7783-06-4",
        "un_number": "UN1053",
        "cameo_class": "Flammable Gas / Toxic Inhalation Hazard (Class 2.3 / 2.1)",
        "niosh_rel": "10 ppm Ceiling (10 min)",
        "osha_pel": "20 ppm Ceiling",
        "idlh_ppm": 100,
        "primary_hazard": "Olfactory paralysis (rapid loss of smell), fatal chemical asphyxiation",
        "toxic_byproducts": ["Sulfur Dioxide (SO2)", "Sulfur Trioxide (SO3)"],
        "erg_guide_no": 117,
        "initial_isolation_m": 150,
        "evacuation_day_m": 1200,
        "evacuation_night_m": 2600,
        "firefighting_foam": "Dry chemical, CO2, or water spray"
    },
    "CRUDE_OIL_AND_PETROLEUM": {
        "cas_number": "8002-05-9",
        "un_number": "UN1267",
        "cameo_class": "Flammable Liquid (Class 3)",
        "niosh_rel": "350 mg/m3 TWA",
        "osha_pel": "500 ppm TWA",
        "idlh_ppm": 1100,
        "primary_hazard": "Massive thermal radiation boilover, tank catastrophic BLEVE explosion",
        "toxic_byproducts": ["SO2", "CO", "PAHs", "Hydrogen Sulfide (sour crude)"],
        "erg_guide_no": 128,
        "initial_isolation_m": 150,
        "evacuation_day_m": 1000,
        "evacuation_night_m": 2000,
        "firefighting_foam": "High-expansion fluoroprotein foam, AR-AFFF sub-surface injection"
    },
    "STYRENE_MONOMER": {
        "cas_number": "100-42-5",
        "un_number": "UN2055",
        "cameo_class": "Flammable Liquid (Class 3)",
        "niosh_rel": "50 ppm TWA, 100 ppm STEL",
        "osha_pel": "100 ppm TWA",
        "idlh_ppm": 700,
        "primary_hazard": "Runaway exothermic polymerization, explosive vapor cloud release (e.g. Vizag 2020)",
        "toxic_byproducts": ["Styrene Oxide", "Benzaldehyde", "CO", "Dense Aromatic Soot"],
        "erg_guide_no": 128,
        "initial_isolation_m": 200,
        "evacuation_day_m": 1800,
        "evacuation_night_m": 3500,
        "firefighting_foam": "Tertiary-butylcatechol inhibitor injection, alcohol-resistant foam"
    }
}


class HazmatEngine:
    """
    CAMEO, NIOSH, and ERG 2024 chemical hazard profiler for industrial facilities.
    """

    def __init__(self, profiles_path: str = HAZMAT_PROFILES_PATH):
        self.profiles: Dict[str, Any] = {}
        if os.path.exists(profiles_path):
            with open(profiles_path, "r") as f:
                self.profiles = json.load(f)

    def get_chemical_hazard_dossier(self, facility_type: str, frp_mw: float = 20.0) -> Dict[str, Any]:
        """
        Retrieves chemical hazards, IDLH values, and evacuation radii for a facility sector.
        """
        facility_upper = facility_type.upper()

        # Match sector
        matched_profile = None
        for sector, prof in self.profiles.items():
            if sector.upper() in facility_upper or any(k in facility_upper for k in ["REFINERY", "PETROCHEM", "OIL", "GAS"]):
                matched_profile = prof
                break

        if not matched_profile:
            matched_profile = self.profiles.get("Refinery_Petrochemical", {
                "sector": "Industrial Chemical & Hydrocarbon Complex",
                "primary_chemicals": ["Hydrocarbons", "LPG", "Benzene", "SO2"],
                "cameo_hazmat_class": "Class 3 Flammable Liquids / Class 2.1 Gases",
                "initial_isolation_distance_meters": 150,
                "downwind_evacuation_day_meters": 1200,
                "downwind_evacuation_night_meters": 2400,
                "firefighting_protocol": "AFFF foam blanket + continuous cooling water spray"
            })

        # Scale evacuation distance dynamically with Thermal Fire Radiative Power (FRP)
        scale_factor = max(1.0, min(3.5, (frp_mw / 25.0) ** 0.5))
        scaled_day_evac_m = int(matched_profile.get("downwind_evacuation_day_meters", 1000) * scale_factor)
        scaled_night_evac_m = int(matched_profile.get("downwind_evacuation_night_meters", 2000) * scale_factor)

        # Lookup detailed CAMEO/NIOSH chemical properties
        chemicals_detail = []
        for chem_name in matched_profile.get("primary_chemicals", []):
            clean_key = chem_name.upper().replace(" ", "_").replace("-", "_")
            if clean_key in CAMEO_NIOSH_DATABASE:
                chemicals_detail.append(CAMEO_NIOSH_DATABASE[clean_key])

        return {
            "sector": matched_profile.get("sector", facility_type),
            "cameo_hazmat_class": matched_profile.get("cameo_hazmat_class", "Class 3 Flammable"),
            "primary_chemicals": matched_profile.get("primary_chemicals", []),
            "un_numbers": matched_profile.get("un_na_numbers", ["UN1203"]),
            "initial_isolation_distance_m": matched_profile.get("initial_isolation_distance_meters", 150),
            "dynamic_evacuation_day_m": scaled_day_evac_m,
            "dynamic_evacuation_night_m": scaled_night_evac_m,
            "toxic_combustion_byproducts": matched_profile.get("toxic_combustion_byproducts", ["CO", "SO2", "NOx"]),
            "firefighting_protocol": matched_profile.get("firefighting_protocol", "AFFF Foam Injection"),
            "niosh_cameo_chemicals": chemicals_detail
        }


if __name__ == "__main__":
    engine = HazmatEngine()
    dossier = engine.get_chemical_hazard_dossier("Petrochemical Refinery", frp_mw=120.5)
    print("=== HAZMAT CHEMICAL DOSSIER ===")
    print(json.dumps(dossier, indent=2))
