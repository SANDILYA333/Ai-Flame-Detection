# 🚒 HAZMAT Disaster Action Protocol & First Responder Integration

## 1. Sector-Specific Chemical Vulnerability Matrix

When an industrial anomaly is classified as `INDUSTRIAL_ACCIDENTAL_DISASTER`, PyroSat-AI cross-references the matched industrial sector with the **CAMEO Chemicals / NIOSH Pocket Guide database** (`data/industrial_infra/hazmat_profiles.json`):

| Industrial Sector | Primary Chemical Stored | UN Number | Hazard Class | Dangerous Byproducts | Initial Isolation (ERG 2024) |
| :--- | :--- | :---: | :---: | :--- | :---: |
| **Petrochemicals & Polymers** | Styrene Monomer | `UN 2055` | 3 (Flammable) | Phosgene, Carbon Monoxide, HCl | $1,000\text{ m}$ ($3.0\text{ km}$ Downwind) |
| **Oil Refinery & Bulk Fuels** | Gasoline / Kerosene | `UN 1268` | 3 (Flammable) | Dense Soot, Benzene, Polycyclic Aromatics | $1,500\text{ m}$ ($5.0\text{ km}$ Downwind) |
| **Chemical & Fertilizers** | Anhydrous Ammonia | `UN 1005` | 2.3 (Toxic Gas) | Toxic Nitrogen Oxides ($NO_x$) | $1,200\text{ m}$ ($4.0\text{ km}$ Downwind) |
| **Iron, Steel & Smelting** | Molten Pig Iron / BFG | `UN 1910` | 8 (Corrosive) | Carbon Monoxide, Sulfur Dioxide ($SO_2$) | $500\text{ m}$ ($1.5\text{ km}$ Downwind) |
| **Coal Mining & Stockpiles** | Bituminous Coal | `UN 1361` | 4.2 (Spontaneous) | Coal Tar Pitch Aerosols, $CH_4$ | $300\text{ m}$ ($1.2\text{ km}$ Downwind) |
| **Chlor-Alkali & Caustic** | Chlorine Liquefied | `UN 1017` | 2.3 (Poison Gas) | Corrosive Chlorine Acid Cloud | $1,600\text{ m}$ ($5.0\text{ km}$ Downwind) |

---

## 2. Dynamic Evacuation Corridor Generation

1. **Meteorological Vector Extraction**:
   * Open-Meteo REST API is queried for the exact coordinate $(\text{lat}, \text{lon})$.
   * Fetches $10\text{m}$ wind speed ($u\text{ in km/h}$) and wind direction angle ($\theta\text{ in deg}$).
2. **Plume Dispersion Geometry**:
   * Generates a 5-point GeoJSON downwind polygon wedge oriented along $\theta$.
   * Projects the ERG 2024 safety perimeter circle overlaying affected population zones.

---

## 3. Emergency Routing & Automated Tactical Dossier

The backend `SpatialEmergencyMatcher` queries indexed OpenStreetMap infrastructure to locate:
1. **Nearest District Fire Command & Industrial Chemical Brigades** (e.g. Foam tender capacity).
2. **Apex Burn Trauma Intensive Care Units** (Bed capacity, distance, and direct emergency dispatch phone numbers).
3. **Regional National Disaster Response Force (NDRF) Battalion Headquarters**.

### Tactical Action Dossier (1-Page PDF Export)
Exportable with 1-click directly from the web interface, containing:
* Official Disaster Alert Header with ISO Incident ID and timestamp.
* Satellite Telemetry & Physical Inversion ($T_{\text{flame}}$, FRP, Area).
* HAZMAT Inventory & Reactive Gas Warnings.
* Meteorological Wind Vector & Evacuation Radius ($km$).
* Key Emergency Contact Numbers for Immediate Tactical Dispatch.
