"""Tests for API-012 (Map Layers)."""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_api_012_get_events_layer_success() -> None:
    """API-012: Test successful retrieval of events GeoJSON layer."""
    response = client.get("/layers/events")
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert isinstance(data["features"], list)
    assert len(data["features"]) > 0

    # Inspect first feature for GeoJSON compliance (RFC 7946)
    feat = data["features"][0]
    assert feat["type"] == "Feature"
    assert "id" in feat
    assert "geometry" in feat
    assert feat["geometry"]["type"] == "Point"
    assert len(feat["geometry"]["coordinates"]) == 2

    # Coordinate order MUST be [longitude, latitude] in EPSG:4326
    lon, lat = feat["geometry"]["coordinates"]
    assert -180.0 <= lon <= 180.0
    assert -90.0 <= lat <= 90.0

    # Check properties
    props = feat["properties"]
    assert "event_id" in props
    assert "started_at" in props
    assert "ended_at" in props
    assert "detection_count" in props

    # Check bounding box
    if data["bbox"] is not None:
        assert len(data["bbox"]) == 4
        min_lon, min_lat, max_lon, max_lat = data["bbox"]
        assert min_lon <= max_lon
        assert min_lat <= max_lat

    # Verify no secrets leakage
    assert "FIRMS_MAP_KEY" not in str(data)
    assert "credentials" not in str(data)


def test_api_012_get_events_layer_spatial_and_temporal_filter() -> None:
    """API-012: Test spatial and temporal filtering on events layer."""
    # Test valid bounding box
    url = "/layers/events?min_lat=22.0&max_lat=23.0&min_lon=70.0&max_lon=71.0"
    res = client.get(url)
    assert res.status_code == 200
    features = res.json()["features"]
    for f in features:
        lon, lat = f["geometry"]["coordinates"]
        assert 22.0 <= lat <= 23.0
        assert 70.0 <= lon <= 71.0

    # Test pagination
    paged_res = client.get("/layers/events?limit=1&offset=0")
    assert paged_res.status_code == 200
    assert len(paged_res.json()["features"]) <= 1


def test_api_012_get_persistent_sources_layer_success() -> None:
    """API-012: Test successful retrieval of persistent sources GeoJSON layer."""
    response = client.get("/layers/persistent-sources")
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert isinstance(data["features"], list)
    assert len(data["features"]) > 0

    feat = data["features"][0]
    assert feat["type"] == "Feature"
    assert "id" in feat
    assert feat["geometry"]["type"] == "Point"
    assert len(feat["geometry"]["coordinates"]) == 2

    props = feat["properties"]
    assert "source_id" in props
    assert "persistence_state" in props
    assert "total_event_count" in props
    assert "linked_event_ids" in props


def test_api_012_get_industrial_layer_success() -> None:
    """API-012: Test successful retrieval of industrial GeoJSON layer."""
    response = client.get("/layers/industrial")
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert isinstance(data["features"], list)
    assert len(data["features"]) > 0

    feat = data["features"][0]
    assert feat["type"] == "Feature"
    assert feat["geometry"]["type"] == "Point"
    props = feat["properties"]
    assert "feature_id" in props
    assert "context_type" in props
    assert props["context_type"] in ["industrial", "oil_gas", "power", "mining"]

    # Test filtering by specific context_type
    oil_gas_res = client.get("/layers/industrial?context_type=oil_gas")
    assert oil_gas_res.status_code == 200
    for f in oil_gas_res.json()["features"]:
        assert f["properties"]["context_type"] == "oil_gas"


def test_api_012_get_land_cover_layer_success() -> None:
    """API-012: Test successful retrieval of land-cover context GeoJSON layer."""
    response = client.get("/layers/land-cover")
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert isinstance(data["features"], list)
    assert len(data["features"]) > 0

    feat = data["features"][0]
    assert feat["type"] == "Feature"
    props = feat["properties"]
    assert "feature_id" in props
    assert "context_type" in props
    assert props["context_type"] not in ["industrial", "oil_gas", "power", "mining"]


def test_api_012_invalid_bounding_box_error() -> None:
    """API-012: Test invalid bbox parameters returns validation error."""
    response = client.get("/layers/events?min_lat=25.0&max_lat=20.0")
    assert response.status_code == 422
    err = response.json()
    assert err["code"] == "VALIDATION_ERROR"
    assert "min_lat" in err["message"]
