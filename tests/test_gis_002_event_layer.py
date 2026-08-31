"""Tests for GIS-002 (Event Layer: bounded map queries and event geometries)."""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_gis_002_event_layer_point_geometry_success() -> None:
    """GIS-002: Verify bounded event query renders standard Point centroid geometry."""
    response = client.get("/layers/events?geometry_type=point")
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert len(data["features"]) > 0

    for feat in data["features"]:
        assert feat["type"] == "Feature"
        assert "id" in feat
        assert feat["geometry"]["type"] == "Point"
        assert len(feat["geometry"]["coordinates"]) == 2
        lon, lat = feat["geometry"]["coordinates"]
        assert -180.0 <= lon <= 180.0
        assert -90.0 <= lat <= 90.0

        props = feat["properties"]
        assert "event_id" in props
        assert "detection_count" in props
        assert "started_at" in props
        assert "ended_at" in props


def test_gis_002_event_layer_envelope_geometry_success() -> None:
    """GIS-002: Verify bounded event query renders closed Polygon envelope geometry."""
    response = client.get("/layers/events?geometry_type=envelope")
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0

    # At least one event with bounding box should render as Polygon
    polygon_found = False
    for feat in data["features"]:
        geom = feat["geometry"]
        if geom["type"] == "Polygon":
            polygon_found = True
            coords = geom["coordinates"]
            assert len(coords) == 1
            ring = coords[0]
            assert len(ring) == 5
            # Closed ring check
            assert ring[0] == ring[4]
            # Check coordinate bounds
            for lon, lat in ring:
                assert -180.0 <= lon <= 180.0
                assert -90.0 <= lat <= 90.0

    assert polygon_found, "Expected at least one event to render as Polygon envelope"


def test_gis_002_event_layer_spatial_bbox_filtering() -> None:
    """GIS-002: Verify bounded map query strictly filters by spatial envelope."""
    url = "/layers/events?min_lat=22.44&max_lat=22.46&min_lon=70.04&max_lon=70.06"
    res = client.get(url)
    assert res.status_code == 200

    features = res.json()["features"]
    for f in features:
        lon, lat = f["geometry"]["coordinates"]
        assert 22.44 <= lat <= 22.46
        assert 70.04 <= lon <= 70.06


def test_gis_002_event_layer_temporal_and_frp_filtering() -> None:
    """GIS-002: Verify temporal, classification, and FRP threshold filters."""
    # FRP filter
    res_frp = client.get("/layers/events?min_frp_mw=10.0")
    assert res_frp.status_code == 200
    for f in res_frp.json()["features"]:
        props = f["properties"]
        max_frp = props.get("max_frp_mw") or 0.0
        mean_frp = props.get("mean_frp_mw") or 0.0
        assert max_frp >= 10.0 or mean_frp >= 10.0

    # Classification filter
    res_cls = client.get("/layers/events?classification_state=industrial")
    assert res_cls.status_code == 200
    for f in res_cls.json()["features"]:
        assert f["properties"]["classification_state"] == "industrial"


def test_gis_002_event_layer_invalid_bbox_error() -> None:
    """GIS-002: Verify inverted bounding box returns 422 VALIDATION_ERROR."""
    res_lat = client.get("/layers/events?min_lat=30.0&max_lat=20.0")
    assert res_lat.status_code == 422
    assert res_lat.json()["code"] == "VALIDATION_ERROR"

    res_lon = client.get("/layers/events?min_lon=80.0&max_lon=70.0")
    assert res_lon.status_code == 422
    assert res_lon.json()["code"] == "VALIDATION_ERROR"


def test_gis_002_event_layer_no_secrets() -> None:
    """GIS-002: Verify zero sensitive tokens or secrets in response payload."""
    res = client.get("/layers/events")
    assert res.status_code == 200
    body = str(res.json())
    assert "FIRMS_MAP_KEY" not in body
    assert "POSTGRES_PASSWORD" not in body
    assert "credentials" not in body
