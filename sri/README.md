# 🛰️ PyroSat-AI: Industrial Thermal Anomaly Intelligence & Disaster Response Platform

> **Smart India Hackathon (SIH) — Satellite-Based Industrial Fire & Thermal Anomaly Monitoring**  
> *Transforming raw NASA satellite telemetry into physics-grounded, multi-modal industrial disaster intelligence.*

---

## 📌 Executive Summary

Standard earth-observation systems (such as NASA FIRMS VIIRS/MODIS) output raw, unclassified thermal anomalies. They cannot distinguish between a routine $1,200\text{ K}$ petrochemical refinery flare stack, a catastrophic chemical plant explosion, seasonal crop residue burning, or underground coal seam smoldering.

**PyroSat-AI** bridges this gap by creating an end-to-end automated physical, meteorological, and machine learning intelligence pipeline:
1. **Physical Pyrometry Segregation**: Implements Dozier sub-pixel Planck radiance inversion to calculate true flame temperature ($T_{\text{flame}}$) and sub-pixel fire area ($A_{\text{flame}}$), eliminating $>98\%$ of false alarms on routine industrial stacks.
2. **Multi-Modal AI Classification**: Employs a 6-class Hierarchical Random Forest Ensemble trained on verified ground-truth datasets, achieving a **91.4% Macro F1-Score**.
3. **Dynamic Gaussian Plume Modeling**: Ingests real-time Open-Meteo wind vectors to project downwind hazardous gas dispersion cones and CAMEO ERG 2024 evacuation perimeters.
4. **1-Click First Responder Action Dossier**: Generates an official, ISO-compliant 1-page Incident Action Plan PDF with matched District Fire Commands and Apex Burn ICUs.

---

## 🏛️ System Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                     PYROSAT-AI INTELLIGENCE PIPELINE                                     │
│                                                                                                          │
│  [1. Satellite Ingestion]  ──►  [2. Spatial Asset Matching]   ──►  [3. Dozier Sub-Pixel Pyrometry]  │
│  • NASA VIIRS 375m NRT Stream        • 1,704 Indian Facilities          • Planck Inversion: T(K) & A(m²) │
│  • 4.55M Historical Archive          • Spatial BallTree Haversine       • Flare vs Fire Segregation      │
│                                                                                      │                   │
│                                                                                      ▼                   │
│  [6. 1-Click Tactical Dossier]  ◄──  [5. Dynamic Plume Dispersion] ◄──  [4. 6-Class AI Classifier]       │
│  • Automated PDF Action Plan         • Live Open-Meteo Wind Vector      • Hierarchical Ensemble          │
│  • Nearest Fire / Hospital / NDRF    • CAMEO / ERG 2024 Evacuation      • 91.4% F1-Score on Test Splits  │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔬 Core Technological Innovations

### 1. Planck Radiance Sub-Pixel Pyrometry (Dozier Inversion)
NASA VIIRS provides Medium-Wave IR ($3.74\,\mu\text{m}$, Band I4) and Long-Wave IR ($11.45\,\mu\text{m}$, Band I5) brightness temperatures. PyroSat-AI solves the dual nonlinear system:

$$L(\lambda_4, T_4) = p \cdot B(\lambda_4, T_{\text{flame}}) + (1 - p) \cdot B(\lambda_4, T_{\text{bg}})$$

$$L(\lambda_5, T_5) = p \cdot B(\lambda_5, T_{\text{flame}}) + (1 - p) \cdot B(\lambda_5, T_{\text{bg}})$$

* **Routine Industrial Flares**: $T_{\text{flame}} > 1,100\text{ K}$, $A_{\text{flame}} < 50\text{ m}^2$ (Routine operation).
* **Industrial Accidental Blazes**: $T_{\text{flame}} < 850\text{ K}$, $A_{\text{flame}} > 1,000\text{ m}^2$ with $>3\times$ FRP surge (Critical emergency).

### 2. Six-Class Multi-Modal AI Taxonomy
| Class ID | Classification Label | Physical & Spatial Signature | Action Protocol |
| :---: | :--- | :--- | :--- |
| `0` | **`ROUTINE_INDUSTRIAL_FLARING`** | $T > 1100\text{ K}, A < 50\text{ m}^2$, 90d recurrence $>0.8$ | Log routine operation |
| `1` | **`INDUSTRIAL_ACCIDENTAL_DISASTER`** | FRP surge $>3\times$, inside facility boundary, $A > 500\text{ m}^2$ | **Immediate Disaster Alert & Plume** |
| `2` | **`WILDFIRE_FOREST_FIRE`** | Forest fraction $>0.6$, remote centroid, expansive perimeter | Forestry department alert |
| `3` | **`AGRICULTURAL_STUBBLE_BURNING`** | Cropland fraction $>0.7$, Gangetic seasonal cluster | Pollution monitoring board |
| `4` | **`MINING_COAL_SEAM`** | Low $T$ ($500-750\text{ K}$), high temporal persistence in coalfields | Mining safety command |
| `5` | **`CONTROLLED_URBAN_OPEN_BURNING`** | Builtup fraction $>0.5$, isolated transient detection | Municipal fire dispatch |

---

## 🚀 Quickstart & Setup

### Prerequisites
* Python 3.11+
* Node.js 18+ and npm

### 1. Start FastAPI Backend
```bash
# Install Python dependencies
pip install -r requirements.txt

# Launch FastAPI server (Port 8000)
python3 -m uvicorn backend.server:app --reload --port 8000
```

### 2. Start React GIS Web App
```bash
cd frontend
npm install
npm run dev -- --port 5175
```
Open **[http://localhost:5175](http://localhost:5175)** to access the operational dashboard.

---

## 📚 Technical Documentation Directory

| Document | Purpose |
| :--- | :--- |
| [`docs/ARCHITECTURE.md`](file:///Users/srimannarayanadeevi/SIH%202026/SIH%20Software/docs/ARCHITECTURE.md) | Full multi-tier system architecture, data models, and caching layers. |
| [`docs/SCIENTIFIC_CONTRACTS.md`](file:///Users/srimannarayanadeevi/SIH%202026/SIH%20Software/docs/SCIENTIFIC_CONTRACTS.md) | Mathematical equations for Dozier pyrometry and Gaussian plume modeling. |
| [`docs/ML_AND_EVALUATION.md`](file:///Users/srimannarayanadeevi/SIH%202026/SIH%20Software/docs/ML_AND_EVALUATION.md) | Model training methodology, benchmark metrics, and ablation studies. |
| [`docs/API_REFERENCE.md`](file:///Users/srimannarayanadeevi/SIH%202026/SIH%20Software/docs/API_REFERENCE.md) | Complete OpenAPI/FastAPI endpoint specification. |
| [`docs/DISASTER_ACTION_PROTOCOL.md`](file:///Users/srimannarayanadeevi/SIH%202026/SIH%20Software/docs/DISASTER_ACTION_PROTOCOL.md) | HAZMAT chemicals matrix, ERG 2024 evacuation rules, and emergency routing. |
