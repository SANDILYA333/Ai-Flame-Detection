"""Comprehensive tests for Pyrometry, Plume, Tactical Dossier, Simulation, and GIS metadata."""

from fastapi.testclient import TestClient

from packages.physics.plume import GaussianPlumeEngine
from packages.physics.pyrometry import DozierPyrometrySolver
from services.api.main import app

client = TestClient(app)


def get_valid_event_id() -> str:
    """Helper to fetch a valid event ID from /events endpoint."""
    response = client.get("/events?limit=1")
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) > 0
    return str(events[0]["event_id"])


def test_dozier_pyrometry_solver():
    """Verify Dozier dual-band radiance solver physics."""
    result = DozierPyrometrySolver.solve(
        bright_mwir_k=365.0,
        bright_lwir_k=302.0,
        background_temp_k=295.0,
    )
    assert result.is_valid is True
    assert result.emitter_temp_k > 500.0
    assert result.emitter_area_m2 > 0.0
    assert result.convergence_status == "CONVERGED"


def test_gaussian_plume_engine():
    """Verify Gaussian plume downwind dispersion geometry generation."""
    plume = GaussianPlumeEngine.compute_plume(
        latitude=22.4707,
        longitude=70.0577,
        frp_mw=85.0,
        wind_speed_ms=4.0,
        wind_direction_deg=225.0,
    )
    assert plume.downwind_azimuth_deg == 45.0
    assert plume.plume_length_km > 1.0
    assert plume.evacuation_radius_km > 0.3
    assert plume.plume_polygon_geojson["type"] == "Feature"
    assert len(plume.plume_polygon_geojson["geometry"]["coordinates"][0]) > 5


def test_tactical_dossier_endpoint():
    """Verify Tactical Dossier generation endpoint."""
    event_id = get_valid_event_id()
    resp = client.get(f"/events/{event_id}/dossier")
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_id"] == event_id
    assert "pyrometry" in data
    assert "plume" in data
    assert "recommended_responders" in data
    assert len(data["recommended_responders"]) > 0


def test_tactical_dossier_html_endpoint():
    """Verify printable HTML briefing endpoint."""
    event_id = get_valid_event_id()
    resp = client.get(f"/events/{event_id}/dossier/html")
    assert resp.status_code == 200
    assert "PyroSat-AI Tactical Briefing" in resp.text
    assert event_id in resp.text


def test_ai_simulation_classify_endpoint():
    """Verify AI Simulation Lab custom prediction endpoint."""
    payload = {
        "latitude": 22.4707,
        "longitude": 70.0577,
        "frp_mw": 95.0,
        "bright_mwir_k": 365.0,
        "bright_lwir_k": 300.0,
        "dist_to_facility_km": 0.25,
        "recurrence_90d": 12,
        "forest_fraction": 0.02,
        "cropland_fraction": 0.05,
        "wind_speed_ms": 3.5,
        "wind_direction_deg": 240.0,
    }
    resp = client.post("/api/classify", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "predicted_class" in data
    assert "confidence" in data
    assert "pyrometry" in data
    assert "plume" in data
    assert "xai_signals" in data


def test_historical_curve_endpoint():
    """Verify 90-day historical curve endpoint."""
    event_id = get_valid_event_id()
    resp = client.get(f"/api/historical-curve/{event_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["event_id"] == event_id
    assert len(data["data_points"]) == 90
    assert data["baseline_mean_frp"] > 0


def test_gis_layers_metadata_endpoint():
    """Verify 12 GIS layers metadata catalog endpoint."""
    resp = client.get("/api/gis-layers/metadata")
    assert resp.status_code == 200
    layers = resp.json()
    assert len(layers) == 12
    layer_ids = [layer["id"] for layer in layers]
    assert "nasa-firms-viirs" in layer_ids
    assert "cameo-niosh-hazmat" in layer_ids
    assert "india-emergency-services" in layer_ids


def test_hazmat_profiles_endpoint():
    """Verify CAMEO-NIOSH hazmat registry endpoint."""
    resp = client.get("/api/hazmat-profiles")
    assert resp.status_code == 200
    data = resp.json()
    assert "Oil Refinery" in data
