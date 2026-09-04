"""Unit and integration tests for industrial asset backend API endpoints."""

import pytest
from fastapi.testclient import TestClient

from services.api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _ensure_cache_ready() -> None:
    """Ensure in-memory cache is warmed up cleanly."""
    pass


class TestIndustrialAssetsApi:
    """Tests for GET /api/industrial-assets, /summary, and /{asset_id}."""

    def test_get_industrial_assets_success(self) -> None:
        """API: Test successful retrieval of industrial assets GeoJSON layer."""
        response = client.get("/api/industrial-assets")
        assert response.status_code == 200

        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data
        assert isinstance(data["features"], list)
        assert len(data["features"]) == 1704  # Phase 1 primary baseline

        # Verify Bounding Box [min_lon, min_lat, max_lon, max_lat]
        assert "bbox" in data
        assert data["bbox"] is not None
        assert len(data["bbox"]) == 4
        min_lon, min_lat, max_lon, max_lat = data["bbox"]
        assert min_lon <= max_lon
        assert min_lat <= max_lat
        assert 68.0 <= min_lon <= 98.0
        assert 6.0 <= min_lat <= 38.0

    def test_geojson_feature_contract(self) -> None:
        """API: Verify RFC 7946 compliance on features and properties."""
        response = client.get("/api/industrial-assets?limit=20")
        assert response.status_code == 200
        features = response.json()["features"]
        assert len(features) == 20

        for feat in features:
            assert feat["type"] == "Feature"
            assert "id" in feat
            assert feat["id"].startswith("ind_asset_")

            # Geometry must be Point with [lon, lat] in EPSG:4326
            geo = feat["geometry"]
            assert geo["type"] == "Point"
            coords = geo["coordinates"]
            assert len(coords) == 2
            lon, lat = coords
            assert 68.0 <= lon <= 98.0
            assert 6.0 <= lat <= 38.0

            # Properties contract
            props = feat["properties"]
            assert "id" in props
            assert "name" in props
            assert len(props["name"]) > 0
            assert "asset_type" in props
            assert "industry" in props
            assert "status" in props
            assert "country" in props
            assert props["country"] == "India"
            assert "source" in props
            assert "source_id" in props
            assert "linked_source_ids" in props
            assert isinstance(props["linked_source_ids"], list)
            assert "is_map_eligible" in props
            assert props["is_map_eligible"] is True

    def test_include_expansion_steel_facilities(self) -> None:
        """API: Verify include_expansion adds steel metallurgy plants."""
        response = client.get("/api/industrial-assets?include_expansion=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data["features"]) == 1817  # 1704 primary + 113 steel plants

        # Verify steel metallurgy plants are present
        steel_plants = [
            f for f in data["features"] if f["properties"]["industry"] == "metallurgy"
        ]
        assert len(steel_plants) == 113

    def test_spatial_bounding_box_filtering(self) -> None:
        """API: Verify spatial bbox filtering correctly restricts coordinates."""
        # Query bounding box around Western India / Gujarat (lat 21-24, lon 69-74)
        url = (
            "/api/industrial-assets?min_lat=21.0&max_lat=24.0&min_lon=69.0&max_lon=74.0"
        )
        response = client.get(url)
        assert response.status_code == 200

        features = response.json()["features"]
        assert len(features) > 0
        for f in features:
            lon, lat = f["geometry"]["coordinates"]
            assert 21.0 <= lat <= 24.0
            assert 69.0 <= lon <= 74.0

    def test_bbox_string_query_parameter(self) -> None:
        """API: Verify standard 'bbox' string query parameter."""
        url = "/api/industrial-assets?bbox=69.0,21.0,74.0,24.0"
        response = client.get(url)
        assert response.status_code == 200

        features = response.json()["features"]
        assert len(features) > 0
        for f in features:
            lon, lat = f["geometry"]["coordinates"]
            assert 21.0 <= lat <= 24.0
            assert 69.0 <= lon <= 74.0

    def test_invalid_bounding_box_returns_422(self) -> None:
        """API: Verify invalid min/max latitude coordinates return 422."""
        response = client.get("/api/industrial-assets?min_lat=25.0&max_lat=20.0")
        assert response.status_code == 422
        data = response.json()
        assert "min_lat" in data["message"] or "INVALID_PARAMETER" in str(data)

    def test_invalid_bbox_string_returns_422(self) -> None:
        """API: Verify malformed bbox string returns 422."""
        response = client.get("/api/industrial-assets?bbox=not,a,valid,box")
        assert response.status_code == 422

    def test_industry_filtering(self) -> None:
        """API: Verify industry sector filter."""
        response = client.get("/api/industrial-assets?industry=power")
        assert response.status_code == 200
        features = response.json()["features"]
        assert len(features) == 1589
        for f in features:
            assert f["properties"]["industry"] == "power"

    def test_status_filtering(self) -> None:
        """API: Verify operational status filter."""
        response = client.get("/api/industrial-assets?status=operating")
        assert response.status_code == 200
        features = response.json()["features"]
        assert len(features) > 1500
        for f in features:
            assert f["properties"]["status"] == "operating"

    def test_state_filtering(self) -> None:
        """API: Verify state administrative filter."""
        response = client.get("/api/industrial-assets?state=Gujarat")
        assert response.status_code == 200
        features = response.json()["features"]
        assert len(features) > 0
        for f in features:
            assert f["properties"]["state"] == "Gujarat"

    def test_pagination_limit_and_offset(self) -> None:
        """API: Verify pagination limit and offset."""
        res_page1 = client.get("/api/industrial-assets?limit=15&offset=0")
        assert res_page1.status_code == 200
        features_p1 = res_page1.json()["features"]
        assert len(features_p1) == 15

        res_page2 = client.get("/api/industrial-assets?limit=15&offset=15")
        assert res_page2.status_code == 200
        features_p2 = res_page2.json()["features"]
        assert len(features_p2) == 15

        # Ensure pagination offsets contain disjoint records
        ids_p1 = {f["id"] for f in features_p1}
        ids_p2 = {f["id"] for f in features_p2}
        assert ids_p1.isdisjoint(ids_p2)

    def test_get_single_asset_success(self) -> None:
        """API: Test retrieval of single asset by canonical ID."""
        # Get first asset id
        list_res = client.get("/api/industrial-assets?limit=1")
        assert list_res.status_code == 200
        first_id = list_res.json()["features"][0]["id"]

        detail_res = client.get(f"/api/industrial-assets/{first_id}")
        assert detail_res.status_code == 200
        asset = detail_res.json()
        assert asset["id"] == first_id
        assert "name" in asset
        assert "latitude" in asset
        assert "longitude" in asset
        assert "industry" in asset
        assert "status" in asset

    def test_get_single_asset_not_found(self) -> None:
        """API: Test 404 for non-existent asset ID."""
        response = client.get("/api/industrial-assets/ind_asset_non_existent_123")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["message"].lower()

    def test_summary_endpoint(self) -> None:
        """API: Verify GET /api/industrial-assets/summary."""
        response = client.get("/api/industrial-assets/summary")
        assert response.status_code == 200
        summary = response.json()
        assert summary["total_count"] == 1704
        assert summary["map_eligible_count"] == 1704
        assert "sources_summary" in summary
        assert "industries_summary" in summary
        assert summary["sources_summary"]["WRI Power Database"] == 1589
        assert summary["sources_summary"]["GEM Oil & Gas Tracker"] == 115
        assert summary["duplicate_candidates_count"] == 237

        # Test with expansion
        res_exp = client.get("/api/industrial-assets/summary?include_expansion=true")
        assert res_exp.status_code == 200
        summary_exp = res_exp.json()
        assert summary_exp["total_count"] == 1817

    def test_route_alias_without_api_prefix(self) -> None:
        """API: Verify /industrial-assets works identically to /api."""
        res_alias = client.get("/industrial-assets?limit=5")
        assert res_alias.status_code == 200
        assert res_alias.json()["type"] == "FeatureCollection"
        assert len(res_alias.json()["features"]) == 5

        res_sum_alias = client.get("/industrial-assets/summary")
        assert res_sum_alias.status_code == 200
        assert res_sum_alias.json()["total_count"] == 1704

    def test_no_secrets_leakage(self) -> None:
        """API: Verify no credentials or internal file paths are leaked in responses."""
        res = client.get("/api/industrial-assets?limit=5")
        body = res.text
        assert "password" not in body.lower()
        assert "secret" not in body.lower()
        assert "token" not in body.lower()
        assert "/home/kafka" not in body
