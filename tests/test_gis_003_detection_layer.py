"""Tests for GIS-003 (Detection Layer: raw observations and pixel footprints)."""

from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


def test_gis_003_detection_layer_point_geometry_success() -> None:
    """GIS-003: Verify raw detection layer renders standard Point centroid geometry."""
    response = client.get("/layers/detections?geometry_type=point")
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
        assert "detection_id" in props
        assert "satellite" in props
        assert "instrument" in props
        assert "acquired_at" in props
        assert "precision_note" in props


def test_gis_003_detection_layer_footprint_polygon_geometry_success() -> None:
    """GIS-003: Verify raw detection layer renders closed Polygon pixel footprints."""
    response = client.get("/layers/detections?geometry_type=footprint")
    assert response.status_code == 200

    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0

    for feat in data["features"]:
        geom = feat["geometry"]
        assert geom["type"] == "Polygon"
        coords = geom["coordinates"]
        assert len(coords) == 1
        ring = coords[0]
        assert len(ring) == 5
        # Closed ring check
        assert ring[0] == ring[4]
        # Coordinate validity
        for lon, lat in ring:
            assert -180.0 <= lon <= 180.0
            assert -90.0 <= lat <= 90.0

        props = feat["properties"]
        assert "precision_note" in props
        assert "not ground truth" in props["precision_note"]


def test_gis_003_detection_layer_spatial_bbox_filtering() -> None:
    """GIS-003: Verify bounded map query strictly filters detections by bbox."""
    url = "/layers/detections?min_lat=22.44&max_lat=22.46&min_lon=70.04&max_lon=70.06"
    res = client.get(url)
    assert res.status_code == 200

    features = res.json()["features"]
    for f in features:
        lon, lat = f["geometry"]["coordinates"]
        assert 22.44 <= lat <= 22.46
        assert 70.04 <= lon <= 70.06


def test_gis_003_detection_layer_satellite_instrument_frp_filtering() -> None:
    """GIS-003: Verify satellite, instrument, and FRP threshold filters."""
    # Satellite and instrument filter
    res = client.get("/layers/detections?satellite=NOAA-20&instrument=VIIRS")
    assert res.status_code == 200
    for f in res.json()["features"]:
        assert f["properties"]["satellite"].upper() == "NOAA-20"
        assert f["properties"]["instrument"].upper() == "VIIRS"

    # FRP threshold filter
    res_frp = client.get("/layers/detections?min_frp_mw=10.0")
    assert res_frp.status_code == 200
    for f in res_frp.json()["features"]:
        assert f["properties"]["frp_mw"] >= 10.0


def test_gis_003_detection_layer_invalid_bbox_error() -> None:
    """GIS-003: Verify inverted bounding box returns 422 VALIDATION_ERROR."""
    res_lat = client.get("/layers/detections?min_lat=30.0&max_lat=20.0")
    assert res_lat.status_code == 422
    assert res_lat.json()["code"] == "VALIDATION_ERROR"

    res_lon = client.get("/layers/detections?min_lon=80.0&max_lon=70.0")
    assert res_lon.status_code == 422
    assert res_lon.json()["code"] == "VALIDATION_ERROR"


def test_gis_003_detection_layer_no_secrets() -> None:
    """GIS-003: Verify zero sensitive tokens or credentials in response payload."""
    res = client.get("/layers/detections")
    assert res.status_code == 200
    body = str(res.json())
    assert "FIRMS_MAP_KEY" not in body
    assert "POSTGRES_PASSWORD" not in body
    assert "credentials" not in body
