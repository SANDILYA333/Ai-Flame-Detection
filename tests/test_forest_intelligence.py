"""Comprehensive automated test suite for Forest Intelligence Foundation (Phase 1).

Tests cover:
1. OSM object -> normalized canonical forest record
2. Valid polygon acceptance
3. Invalid / self-intersecting polygon safe repair
4. Centroid coordinate calculation
5. Geodesic area calculation (km²)
6. Duplicate OSM object rejection & deduplication
7. Repeated ingestion idempotency
8. GET /forests GeoJSON FeatureCollection endpoint
9. GET /forests/{id} single forest detail endpoint
10. GET /forests/nearby geodesic proximity search & ordering
11. Bounding-box spatial filtering
12. RFC 7946 GeoJSON output conformance
13. Ingestion service dry-run telemetry
14. Overpass client query builders
"""

import pytest
from fastapi.testclient import TestClient

from packages.data.forests.client import ForestOverpassClient
from packages.data.forests.normalizer import (
    normalize_and_validate_geometry,
)
from packages.data.forests.parser import (
    candidate_to_forest_record,
    parse_osm_element,
)
from packages.data.forests.repository import InMemoryForestRepository
from packages.data.forests.service import ForestIngestionService
from packages.data.forests.threat_service import ForestThreatService
from packages.errors import InvalidCoordinateError
from packages.geospatial.polygon_distance import calculate_point_to_polygon_distance_km
from packages.schemas.common import Coordinate
from packages.schemas.forest import (
    ForestAreaRecord,
    ForestGeometry,
    ForestThreatAssessment,
    ForestThreatLevel,
    ForestType,
    NearbyForestThreatItem,
)
from services.api.app import create_app


@pytest.fixture
def mock_repo() -> InMemoryForestRepository:
    """Fixture providing an isolated in-memory forest repository."""
    repo = InMemoryForestRepository()
    return repo


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient fixture."""
    app = create_app()
    return TestClient(app)


class TestForestGeometryAndNormalization:
    """Tests for geometry validation, repair, centroid, and geodesic area."""

    def test_01_osm_object_to_normalized_forest_record(self) -> None:
        """Test 1: Normalizing raw OSM element to canonical ForestAreaRecord."""
        raw_element = {
            "type": "way",
            "id": 554433,
            "tags": {
                "name": "Deccan Dry Deciduous Forest",
                "natural": "wood",
                "leaf_type": "broadleaved",
                "leaf_cycle": "deciduous",
                "operator": "Forest Department",
                "addr:country": "IN",
            },
            "geometry": [
                {"lat": 18.50, "lon": 74.00},
                {"lat": 18.50, "lon": 74.20},
                {"lat": 18.70, "lon": 74.20},
                {"lat": 18.70, "lon": 74.00},
                {"lat": 18.50, "lon": 74.00},
            ],
        }

        candidate = parse_osm_element(raw_element, default_country_code="IN")
        assert candidate is not None
        assert candidate.osm_id == 554433
        assert candidate.osm_type == "way"
        assert candidate.osm_identity == "way:554433"
        assert candidate.name == "Deccan Dry Deciduous Forest"
        assert candidate.country_code == "IN"
        assert candidate.norm_result.is_valid is True

        record = candidate_to_forest_record(candidate)
        assert record is not None
        assert record.forest_id == "forest_way_554433"
        assert record.forest_type == ForestType.NATURAL_WOOD
        assert record.osm_tag == "natural=wood"
        assert record.area_km2 > 0.0
        assert record.metadata_tags.get("leaf_type") == "broadleaved"
        assert record.metadata_tags.get("operator") == "Forest Department"

    def test_02_valid_polygon_accepted(self) -> None:
        """Test 2: Valid polygon coordinates are accepted without errors."""
        coords = [
            [
                [75.0, 20.0],
                [75.5, 20.0],
                [75.5, 20.5],
                [75.0, 20.5],
                [75.0, 20.0],
            ]
        ]
        result = normalize_and_validate_geometry(coords, geometry_type="Polygon")
        assert result.is_valid is True
        assert result.is_repaired is False
        assert result.geometry is not None
        assert result.geometry.type == "Polygon"
        assert len(result.geometry.coordinates[0]) == 5

    def test_03_invalid_self_intersecting_polygon_repaired(self) -> None:
        """Test 3: Self-intersecting figure-8 polygon is safely repaired."""
        # Figure-8 polygon (self-intersecting bowtie)
        bowtie_coords = [
            [
                [0.0, 0.0],
                [2.0, 2.0],
                [2.0, 0.0],
                [0.0, 2.0],
                [0.0, 0.0],
            ]
        ]
        result = normalize_and_validate_geometry(bowtie_coords, geometry_type="Polygon")
        assert result.is_valid is True
        assert result.is_repaired is True
        assert result.geometry is not None
        assert result.area_km2 > 0.0

    def test_04_centroid_calculated_accurately(self) -> None:
        """Test 4: Representative centroid is calculated correctly for polygon."""
        coords = [
            [
                [70.0, 20.0],
                [72.0, 20.0],
                [72.0, 22.0],
                [70.0, 22.0],
                [70.0, 20.0],
            ]
        ]
        result = normalize_and_validate_geometry(coords, geometry_type="Polygon")
        assert result.centroid is not None
        assert pytest.approx(result.centroid.latitude, 0.01) == 21.0
        assert pytest.approx(result.centroid.longitude, 0.01) == 71.0

    def test_05_geodesic_area_calculated_correctly(self) -> None:
        """Test 5: Area is computed using spherical excess in km² (not flat degrees)."""
        # A 1-degree square near the equator is roughly 111 km x 111 km ~ 12,300 km²
        coords = [
            [
                [0.0, 0.0],
                [1.0, 0.0],
                [1.0, 1.0],
                [0.0, 1.0],
                [0.0, 0.0],
            ]
        ]
        result = normalize_and_validate_geometry(coords, geometry_type="Polygon")
        assert result.area_km2 > 12000.0
        assert result.area_km2 < 12500.0


class TestForestDeduplicationAndIdempotency:
    """Tests for duplicate rejection and repeated ingestion idempotency."""

    def test_06_duplicate_osm_object_does_not_create_duplicate(
        self, mock_repo: InMemoryForestRepository
    ) -> None:
        """Test 6: Duplicate OSM identity updates existing instead of duplicating."""
        element = {
            "type": "way",
            "id": 999111,
            "tags": {"name": "Saranda Forest", "natural": "wood"},
            "geometry": [
                {"lat": 22.0, "lon": 85.0},
                {"lat": 22.0, "lon": 85.3},
                {"lat": 22.3, "lon": 85.3},
                {"lat": 22.3, "lon": 85.0},
                {"lat": 22.0, "lon": 85.0},
            ],
        }

        service = ForestIngestionService(repository=mock_repo)
        stats1 = service.ingest_raw_elements([element], default_country="IN")
        assert stats1.inserted == 1
        assert stats1.updated == 0
        assert mock_repo.count() == 1

        # Second insertion of same identity
        stats2 = service.ingest_raw_elements([element], default_country="IN")
        assert stats2.inserted == 0
        assert stats2.updated == 1
        assert mock_repo.count() == 1  # Still exactly 1

    def test_07_repeated_ingestion_is_idempotent(
        self, mock_repo: InMemoryForestRepository
    ) -> None:
        """Test 7: Ingesting a batch multiple times creates 0 duplicate records."""
        elements = [
            {
                "type": "way",
                "id": 101,
                "tags": {"name": "Forest Alpha", "landuse": "forest"},
                "geometry": [
                    {"lat": 10.0, "lon": 76.0},
                    {"lat": 10.0, "lon": 76.1},
                    {"lat": 10.1, "lon": 76.1},
                    {"lat": 10.1, "lon": 76.0},
                    {"lat": 10.0, "lon": 76.0},
                ],
            },
            {
                "type": "way",
                "id": 102,
                "tags": {"name": "Forest Beta", "natural": "wood"},
                "geometry": [
                    {"lat": 10.2, "lon": 76.2},
                    {"lat": 10.2, "lon": 76.3},
                    {"lat": 10.3, "lon": 76.3},
                    {"lat": 10.3, "lon": 76.2},
                    {"lat": 10.2, "lon": 76.2},
                ],
            },
        ]

        service = ForestIngestionService(repository=mock_repo)

        # Run 1
        run1 = service.ingest_raw_elements(elements, default_country="IN")
        assert run1.inserted == 2
        assert run1.updated == 0
        assert mock_repo.count() == 2

        # Run 2
        run2 = service.ingest_raw_elements(elements, default_country="IN")
        assert run2.inserted == 0
        assert run2.updated == 2
        assert mock_repo.count() == 2


class TestForestApiEndpoints:
    """Tests for HTTP API endpoints (/forests, /forests/{id}, /forests/nearby)."""

    def test_08_get_forests_returns_valid_geojson(self, client: TestClient) -> None:
        """Test 8: GET /forests returns valid RFC 7946 GeoJSON FeatureCollection."""
        response = client.get("/forests")
        assert response.status_code == 200
        data = response.json()

        assert data["type"] == "FeatureCollection"
        assert "features" in data
        assert isinstance(data["features"], list)
        assert len(data["features"]) > 0

        first_feature = data["features"][0]
        assert first_feature["type"] == "Feature"
        assert "geometry" in first_feature
        assert first_feature["geometry"]["type"] in ("Polygon", "MultiPolygon")
        assert "properties" in first_feature
        props = first_feature["properties"]
        assert "forest_id" in props
        assert "name" in props
        assert "area_km2" in props
        assert "centroid" in props
        assert "country_code" in props

    def test_09_get_forest_detail_by_id(self, client: TestClient) -> None:
        """Test 9: GET /forests/{forest_id} returns single canonical forest entity."""
        # Query list first to get a real ID
        list_res = client.get("/forests?limit=1")
        assert list_res.status_code == 200
        first_id = list_res.json()["features"][0]["properties"]["forest_id"]

        detail_res = client.get(f"/forests/{first_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["id"] == first_id
        assert detail["country_code"] == "IN"
        assert detail["area_km2"] > 0.0
        assert "centroid" in detail
        assert "geometry" in detail
        assert detail["source"] == "openstreetmap"

    def test_09b_get_forest_detail_not_found(self, client: TestClient) -> None:
        """Test 9b: Non-existent forest returns 404."""
        res = client.get("/forests/forest_non_existent_999999")
        assert res.status_code == 404

    def test_10_get_nearby_forests_distance_ordering(self, client: TestClient) -> None:
        """Test 10: GET /forests/nearby returns ordered nearby forests."""
        # Query near Gir Forest centroid (lat: 21.15, lon: 70.75)
        response = client.get(
            "/forests/nearby?latitude=21.15&longitude=70.75&radius_km=300"
        )
        assert response.status_code == 200
        data = response.json()

        assert "forests" in data
        forests = data["forests"]
        assert len(forests) >= 1

        # Check distances are non-negative and monotonically ascending
        distances = [f["distance_km"] for f in forests]
        assert distances == sorted(distances)
        assert all(d >= 0.0 for d in distances)

    def test_11_bounding_box_filtering(self, client: TestClient) -> None:
        """Test 11: Bounding box query filters out forests outside viewport."""
        # Bbox covering only Gujarat (approx lon: 68-73, lat: 20-24)
        response = client.get(
            "/forests?min_lat=20.0&max_lat=24.0&min_lon=68.0&max_lon=73.0"
        )
        assert response.status_code == 200
        data = response.json()

        for feat in data["features"]:
            centroid = feat["properties"]["centroid"]
            assert 20.0 <= centroid["latitude"] <= 24.0
            assert 68.0 <= centroid["longitude"] <= 73.0

    def test_12_geojson_rfc7946_compliance(self, client: TestClient) -> None:
        """Test 12: Validate GeoJSON conforms to RFC 7946 standard structure."""
        response = client.get("/forests?limit=5")
        assert response.status_code == 200
        data = response.json()

        assert data["type"] == "FeatureCollection"
        for feature in data["features"]:
            assert feature["type"] == "Feature"
            geom = feature["geometry"]
            assert geom["type"] in ("Polygon", "MultiPolygon")
            # First coordinate in coordinates should be longitude, second latitude
            if geom["type"] == "Polygon":
                first_coord = geom["coordinates"][0][0]
                assert len(first_coord) == 2
                lon, lat = first_coord
                assert -180.0 <= lon <= 180.0
                assert -90.0 <= lat <= 90.0


class TestForestIngestionClientAndDryRun:
    """Tests for dry-run telemetry and Overpass QL query formatting."""

    def test_13_dry_run_mode_telemetry(
        self, mock_repo: InMemoryForestRepository
    ) -> None:
        """Test 13: Dry-run parses and validates data without modifying repository."""
        elements = [
            {
                "type": "way",
                "id": 777,
                "tags": {"name": "Dry Run Reserve", "natural": "wood"},
                "geometry": [
                    {"lat": 15.0, "lon": 75.0},
                    {"lat": 15.0, "lon": 75.2},
                    {"lat": 15.2, "lon": 75.2},
                    {"lat": 15.2, "lon": 75.0},
                    {"lat": 15.0, "lon": 75.0},
                ],
            }
        ]

        service = ForestIngestionService(repository=mock_repo)
        stats = service.ingest_raw_elements(
            elements, default_country="IN", dry_run=True
        )

        assert stats.is_dry_run is True
        assert stats.objects_received == 1
        assert stats.polygons_parsed == 1
        assert stats.inserted == 1
        assert mock_repo.count() == 0  # Dry run MUST NOT persist!

    def test_14_overpass_query_construction(self) -> None:
        """Test 14: Overpass query builder creates valid QL for country and bbox."""
        client = ForestOverpassClient()

        # Country query
        query_in = client.build_country_query("IN", limit=50, include_boundary=True)
        assert 'area["ISO3166-1"="IN"]' in query_in
        assert 'way["natural"="wood"]' in query_in
        assert 'way["landuse"="forest"]' in query_in
        assert 'way["boundary"="forest"]' in query_in
        assert "out geom 50;" in query_in

        # Bbox query
        query_bbox = client.build_bbox_query(20.0, 70.0, 22.0, 72.0, limit=100)
        assert "(20.0,70.0,22.0,72.0)" in query_bbox
        assert "out geom 100;" in query_bbox

    def test_15_multipolygon_normalization_with_holes(self) -> None:
        """Test 15: Relation with outer and inner rings is parsed into MultiPolygon."""
        raw_relation = {
            "type": "relation",
            "id": 998877,
            "tags": {
                "name": "Archipelago Mangrove Forest",
                "natural": "wood",
                "addr:country": "IN",
            },
            "members": [
                {
                    "type": "way",
                    "role": "outer",
                    "geometry": [
                        {"lat": 10.0, "lon": 80.0},
                        {"lat": 10.0, "lon": 80.5},
                        {"lat": 10.5, "lon": 80.5},
                        {"lat": 10.5, "lon": 80.0},
                        {"lat": 10.0, "lon": 80.0},
                    ],
                },
                {
                    "type": "way",
                    "role": "inner",
                    "geometry": [
                        {"lat": 10.2, "lon": 80.2},
                        {"lat": 10.2, "lon": 80.3},
                        {"lat": 10.3, "lon": 80.3},
                        {"lat": 10.3, "lon": 80.2},
                        {"lat": 10.2, "lon": 80.2},
                    ],
                },
            ],
        }

        candidate = parse_osm_element(raw_relation, default_country_code="IN")
        assert candidate is not None
        assert candidate.osm_type == "relation"
        assert candidate.norm_result.is_valid is True
        assert candidate.norm_result.geometry.type in ("Polygon", "MultiPolygon")
        assert candidate.norm_result.area_km2 > 0.0

        record = candidate_to_forest_record(candidate)
        assert record is not None
        assert record.forest_id == "forest_relation_998877"

    def test_16_missing_name_handling(self) -> None:
        """Test 16: Forest without a name tag is preserved safely with name=None."""
        raw_element = {
            "type": "way",
            "id": 112233,
            "tags": {"landuse": "forest", "addr:country": "IN"},
            "geometry": [
                {"lat": 12.0, "lon": 76.0},
                {"lat": 12.0, "lon": 76.1},
                {"lat": 12.1, "lon": 76.1},
                {"lat": 12.1, "lon": 76.0},
                {"lat": 12.0, "lon": 76.0},
            ],
        }

        candidate = parse_osm_element(raw_element)
        assert candidate is not None
        assert candidate.name is None

        record = candidate_to_forest_record(candidate)
        assert record is not None
        assert record.name is None
        assert record.forest_type == ForestType.LANDUSE_FOREST

    def test_17_invalid_geometry_rejection(self) -> None:
        """Test 17: Incomplete, malformed, or degenerate geometries are rejected."""
        # Less than 3 points
        raw_element_short = {
            "type": "way",
            "id": 101,
            "tags": {"natural": "wood"},
            "geometry": [
                {"lat": 12.0, "lon": 76.0},
                {"lat": 12.0, "lon": 76.1},
            ],
        }
        candidate = parse_osm_element(raw_element_short)
        assert candidate is None

        # NaN coordinate
        invalid_coords = [
            [
                [76.0, float("nan")],
                [76.1, 12.0],
                [76.1, 12.1],
                [76.0, 12.0],
            ]
        ]
        norm_result = normalize_and_validate_geometry(invalid_coords)
        assert norm_result.is_valid is False

    def test_18_idempotent_reingestion_updates_record(
        self, mock_repo: InMemoryForestRepository
    ) -> None:
        """Test 18: Re-ingesting OSM identity updates record without duplicates."""
        element = {
            "type": "way",
            "id": 4040,
            "tags": {"name": "Initial Forest Name", "natural": "wood"},
            "geometry": [
                {"lat": 22.0, "lon": 77.0},
                {"lat": 22.0, "lon": 77.2},
                {"lat": 22.2, "lon": 77.2},
                {"lat": 22.2, "lon": 77.0},
                {"lat": 22.0, "lon": 77.0},
            ],
        }

        service = ForestIngestionService(repository=mock_repo)

        # First run: 1 inserted
        stats1 = service.ingest_raw_elements([element])
        assert stats1.inserted == 1
        assert stats1.updated == 0
        assert mock_repo.count() == 1

        # Second run with modified name: 1 updated, 0 inserted, count remains 1
        element_updated = {
            "type": "way",
            "id": 4040,
            "tags": {"name": "Updated Sanctuary Name", "natural": "wood"},
            "geometry": element["geometry"],
        }
        stats2 = service.ingest_raw_elements([element_updated])
        assert stats2.inserted == 0
        assert stats2.updated == 1
        assert mock_repo.count() == 1

        saved = mock_repo.get_forest_by_osm_identity("way:4040")
        assert saved is not None
        assert saved.name == "Updated Sanctuary Name"

    def test_19_api_ingest_endpoint_valid_bbox(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test 19: POST /forests/ingest with valid dry_run bounding box."""
        mock_response = {
            "elements": [
                {
                    "type": "way",
                    "id": 8801,
                    "tags": {"name": "Mock Test Forest", "natural": "wood"},
                    "geometry": [
                        {"lat": 21.1, "lon": 70.6},
                        {"lat": 21.1, "lon": 70.8},
                        {"lat": 21.3, "lon": 70.8},
                        {"lat": 21.3, "lon": 70.6},
                        {"lat": 21.1, "lon": 70.6},
                    ],
                }
            ]
        }
        monkeypatch.setattr(
            ForestOverpassClient, "execute_query", lambda *args, **kwargs: mock_response
        )

        payload = {
            "south": 21.0,
            "west": 70.5,
            "north": 21.5,
            "east": 71.0,
            "country_code": "IN",
            "dry_run": True,
            "limit": 10,
        }
        response = client.post("/forests/ingest", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["source"] == "openstreetmap"
        assert data["bounding_box"]["south"] == 21.0
        assert "statistics" in data
        assert data["statistics"]["objects_received"] == 1
        assert data["statistics"]["polygons_parsed"] == 1

    def test_20_api_ingest_endpoint_invalid_bbox_rejected(
        self, client: TestClient
    ) -> None:
        """Test 20: POST /forests/ingest rejects invalid bounding boxes."""
        # South > North
        payload_inverted = {
            "south": 25.0,
            "west": 70.0,
            "north": 20.0,
            "east": 71.0,
        }
        resp = client.post("/forests/ingest", json=payload_inverted)
        assert resp.status_code == 422

        # Exceeds max bbox safety span limit (> 5 degrees)
        payload_oversized = {
            "south": 0.0,
            "west": 0.0,
            "north": 20.0,
            "east": 20.0,
        }
        resp = client.post("/forests/ingest", json=payload_oversized)
        assert resp.status_code == 422

    def test_21_end_to_end_integration_ingest_to_proximity_query(
        self, mock_repo: InMemoryForestRepository
    ) -> None:
        """Test 21: Full integration: raw OSM -> ingestion -> DB -> proximity query."""
        raw_elements = [
            {
                "type": "way",
                "id": 9001,
                "tags": {
                    "name": "Integration Test Forest Alpha",
                    "natural": "wood",
                },
                "geometry": [
                    {"lat": 25.0, "lon": 82.0},
                    {"lat": 25.0, "lon": 82.1},
                    {"lat": 25.1, "lon": 82.1},
                    {"lat": 25.1, "lon": 82.0},
                    {"lat": 25.0, "lon": 82.0},
                ],
            },
            {
                "type": "way",
                "id": 9002,
                "tags": {
                    "name": "Integration Test Forest Beta",
                    "landuse": "forest",
                },
                "geometry": [
                    {"lat": 26.0, "lon": 82.0},
                    {"lat": 26.0, "lon": 82.1},
                    {"lat": 26.1, "lon": 82.1},
                    {"lat": 26.1, "lon": 82.0},
                    {"lat": 26.0, "lon": 82.0},
                ],
            },
        ]

        service = ForestIngestionService(repository=mock_repo)
        stats = service.ingest_raw_elements(raw_elements, default_country="IN")

        assert stats.objects_received == 2
        assert stats.polygons_parsed == 2
        assert stats.inserted == 2
        assert mock_repo.count() == 2

        # Query proximity near Alpha (lat=25.05, lon=82.05)
        nearby = mock_repo.find_nearby_forests(lat=25.05, lon=82.05, radius_km=50.0)
        assert len(nearby) >= 1
        assert nearby[0].name == "Integration Test Forest Alpha"
        assert nearby[0].distance_km < 15.0


class TestForestThreatSpatialIntelligence:
    """Deterministic automated tests for Phase 3 Fire-to-Forest Spatial Intelligence.

    Covers:
    - TEST 1: Fire far away from forest (NONE)
    - TEST 2: Fire on forest boundary (CRITICAL, ~0 km)
    - TEST 3: Fire inside forest polygon (CRITICAL, 0 km)
    - TEST 4: Fire 1 km from forest (CRITICAL)
    - TEST 5: Fire 3 km from forest (MODERATE)
    - TEST 6: Fire 6 km from forest (outside 5 km threat radius, NONE)
    - TEST 7: Fire near multiple forests (all returned in radius, sorted)
    - TEST 8: MultiPolygon forest minimum distance calculation
    - TEST 9: Malformed forest geometry safe fallback
    - TEST 10: Repeated evaluation idempotency
    - TEST 11: Invalid fire coordinates (out of range / NaN)
    - TEST 12: Spatial prefiltering candidate reduction
    - TEST 13: Dynamic query API endpoint /forests/threat/evaluate
    - TEST 14: FIRMS event threat assessment API endpoint /forests/threat/{event_id}
    """

    @pytest.fixture
    def populated_threat_repo(self) -> InMemoryForestRepository:
        """Repository pre-populated with a standard 10km x 10km test forest box.

        Forest boundary:
        lat: 20.00 to 20.10 (~11.1 km)
        lon: 78.00 to 78.10 (~10.4 km)
        """
        repo = InMemoryForestRepository()
        raw_forest = {
            "type": "way",
            "id": 10001,
            "tags": {"name": "Satpura Sector Alpha", "natural": "wood"},
            "geometry": [
                {"lat": 20.00, "lon": 78.00},
                {"lat": 20.00, "lon": 78.10},
                {"lat": 20.10, "lon": 78.10},
                {"lat": 20.10, "lon": 78.00},
                {"lat": 20.00, "lon": 78.00},
            ],
        }
        service = ForestIngestionService(repository=repo)
        service.ingest_raw_elements([raw_forest], default_country="IN")
        return repo

    def test_01_fire_far_away_no_threat(
        self, populated_threat_repo: InMemoryForestRepository
    ) -> None:
        """TEST 1: Fire 50km away from every forest has no threat."""
        service = ForestThreatService(repository=populated_threat_repo)
        # Forest is around lat=20.0-20.1, lon=78.0-78.1
        # Fire at lat=20.5, lon=78.5 is ~60 km away
        assessment = service.evaluate_fire_point(
            latitude=20.5,
            longitude=78.5,
            search_radius_km=10.0,
            threat_radius_km=5.0,
        )
        assert assessment.is_threatened is False
        assert assessment.nearest_forest is None
        assert len(assessment.nearby_forests) == 0

    def test_02_fire_on_forest_boundary(
        self, populated_threat_repo: InMemoryForestRepository
    ) -> None:
        """TEST 2: Fire exactly on forest boundary -> distance ≈ 0 km, CRITICAL."""
        service = ForestThreatService(repository=populated_threat_repo)
        # Point right on the southern edge: lat=20.00, lon=78.05
        assessment = service.evaluate_fire_point(
            latitude=20.00,
            longitude=78.05,
        )
        assert assessment.is_threatened is True
        assert assessment.nearest_forest is not None
        assert pytest.approx(assessment.nearest_forest.distance_km, abs=0.05) == 0.0
        assert assessment.nearest_forest.threat_level in (
            ForestThreatLevel.CRITICAL,
            ForestThreatLevel.INSIDE_FOREST,
        )
        assert assessment.nearest_forest.is_within_threat_radius is True

    def test_03_fire_inside_forest(
        self, populated_threat_repo: InMemoryForestRepository
    ) -> None:
        """TEST 3: Fire inside forest polygon -> distance = 0.0 km, INSIDE_FOREST."""
        service = ForestThreatService(repository=populated_threat_repo)
        # Inside the box: lat=20.05, lon=78.05
        assessment = service.evaluate_fire_point(
            latitude=20.05,
            longitude=78.05,
        )
        assert assessment.is_threatened is True
        assert assessment.nearest_forest is not None
        assert assessment.nearest_forest.distance_km == 0.0
        assert assessment.nearest_forest.threat_level in (
            ForestThreatLevel.CRITICAL,
            ForestThreatLevel.INSIDE_FOREST,
        )
        assert assessment.nearest_forest.is_within_threat_radius is True

    def test_04_fire_1km_from_forest_critical(
        self, populated_threat_repo: InMemoryForestRepository
    ) -> None:
        """TEST 4: Fire ~0.8 km south of forest boundary -> CRITICAL."""
        # 1 deg latitude ~ 111 km, so 0.007 deg ~ 0.78 km south of 20.00 -> lat = 19.993
        service = ForestThreatService(repository=populated_threat_repo)
        assessment = service.evaluate_fire_point(
            latitude=19.993,
            longitude=78.05,
        )
        assert assessment.is_threatened is True
        assert assessment.nearest_forest is not None
        assert assessment.nearest_forest.distance_km <= 1.0
        assert assessment.nearest_forest.threat_level == ForestThreatLevel.CRITICAL

    def test_05_fire_3km_from_forest_moderate(
        self, populated_threat_repo: InMemoryForestRepository
    ) -> None:
        """TEST 5: Fire ~3.3 km south of boundary (lat=19.97) -> MODERATE / WARNING."""
        # (20.00 - 19.97) = 0.03 deg * 111.139 km/deg ~ 3.33 km
        service = ForestThreatService(repository=populated_threat_repo)
        assessment = service.evaluate_fire_point(
            latitude=19.97,
            longitude=78.05,
        )
        assert assessment.is_threatened is True
        assert assessment.nearest_forest is not None
        assert 2.5 < assessment.nearest_forest.distance_km <= 5.0
        assert assessment.nearest_forest.threat_level in (
            ForestThreatLevel.MODERATE,
            ForestThreatLevel.WARNING,
        )

    def test_06_fire_6km_from_forest_outside_threat_radius(
        self, populated_threat_repo: InMemoryForestRepository
    ) -> None:
        """TEST 6: Fire ~6.6 km south of boundary -> outside threat radius."""
        # (20.00 - 19.94) = 0.06 deg * 111.139 km/deg ~ 6.67 km
        # Within search radius (10km) but outside threat radius (5km)
        service = ForestThreatService(repository=populated_threat_repo)
        assessment = service.evaluate_fire_point(
            latitude=19.94,
            longitude=78.05,
            search_radius_km=10.0,
            threat_radius_km=5.0,
        )
        assert assessment.is_threatened is False
        assert assessment.nearest_forest is not None
        assert assessment.nearest_forest.distance_km > 5.0
        assert assessment.nearest_forest.is_within_threat_radius is False
        assert assessment.nearest_forest.threat_level == ForestThreatLevel.NONE

    def test_07_multiple_forests_threat_evaluation(self) -> None:
        """TEST 7: Fire near multiple forests returns all in search radius, sorted."""
        repo = InMemoryForestRepository()
        # Forest A: lat 20.00-20.10, lon 78.00-78.10 (North of fire)
        # Forest B: lat 19.85-19.95, lon 78.00-78.10 (South of fire)
        raw_elements = [
            {
                "type": "way",
                "id": 201,
                "tags": {"name": "Forest North", "natural": "wood"},
                "geometry": [
                    {"lat": 20.00, "lon": 78.00},
                    {"lat": 20.00, "lon": 78.10},
                    {"lat": 20.10, "lon": 78.10},
                    {"lat": 20.10, "lon": 78.00},
                    {"lat": 20.00, "lon": 78.00},
                ],
            },
            {
                "type": "way",
                "id": 202,
                "tags": {"name": "Forest South", "natural": "wood"},
                "geometry": [
                    {"lat": 19.85, "lon": 78.00},
                    {"lat": 19.85, "lon": 78.10},
                    {"lat": 19.95, "lon": 78.10},
                    {"lat": 19.95, "lon": 78.00},
                    {"lat": 19.85, "lon": 78.00},
                ],
            },
        ]
        ForestIngestionService(repository=repo).ingest_raw_elements(raw_elements)

        # Fire at lat=19.99, lon=78.05:
        # Distance to North (at 20.00): ~1.1 km -> CRITICAL / HIGH
        # Distance to South (at 19.95): ~4.4 km -> WARNING / MODERATE
        service = ForestThreatService(repository=repo)
        assessment = service.evaluate_fire_point(
            latitude=19.99,
            longitude=78.05,
            search_radius_km=10.0,
            threat_radius_km=5.0,
        )

        assert assessment.is_threatened is True
        assert len(assessment.nearby_forests) == 2
        assert assessment.nearest_forest is not None
        assert assessment.nearest_forest.name == "Forest North"
        assert assessment.nearest_forest.threat_level in (
            ForestThreatLevel.HIGH,
            ForestThreatLevel.CRITICAL,
        )

        # Verify sorted ascending
        assert (
            assessment.nearby_forests[0].distance_km
            <= assessment.nearby_forests[1].distance_km
        )
        assert assessment.nearby_forests[1].name == "Forest South"
        assert assessment.nearby_forests[1].threat_level in (
            ForestThreatLevel.MODERATE,
            ForestThreatLevel.WARNING,
        )

    def test_08_multipolygon_minimum_distance(self) -> None:
        """TEST 8: MultiPolygon calculates min distance against all polygons."""
        # MultiPolygon with 2 disjoint islands
        geometry = ForestGeometry(
            type="MultiPolygon",
            coordinates=[
                # Island 1
                [
                    [
                        [80.0, 10.0],
                        [80.1, 10.0],
                        [80.1, 10.1],
                        [80.0, 10.1],
                        [80.0, 10.0],
                    ]
                ],
                # Island 2
                [
                    [
                        [80.0, 10.5],
                        [80.1, 10.5],
                        [80.1, 10.6],
                        [80.0, 10.6],
                        [80.0, 10.5],
                    ]
                ],
            ],
        )

        # Fire close to Island 1: lat=10.01, lon=80.01 (Inside Island 1)
        dist_inside, _ = calculate_point_to_polygon_distance_km(10.01, 80.01, geometry)
        assert dist_inside == 0.0

        # Fire 2 km below Island 1: lat=9.98, lon=80.05
        dist_near_island1, _ = calculate_point_to_polygon_distance_km(
            9.98, 80.05, geometry
        )
        assert pytest.approx(dist_near_island1, abs=0.5) == 2.22

    def test_09_malformed_forest_geometry_safe_handling(self) -> None:
        """TEST 9: Malformed forest geometry does not crash distance evaluation."""
        malformed_geom = ForestGeometry(
            type="Polygon",
            coordinates=[],  # Empty coordinates
        )
        dist, nearest = calculate_point_to_polygon_distance_km(
            20.0, 78.0, malformed_geom
        )
        assert dist == float("inf")
        assert nearest is None

    def test_10_repeated_evaluation_idempotency(
        self, populated_threat_repo: InMemoryForestRepository
    ) -> None:
        """TEST 10: Repeated evaluation of same event produces identical output."""
        service = ForestThreatService(repository=populated_threat_repo)

        run1 = service.evaluate_fire_point(
            latitude=20.02,
            longitude=78.05,
            fire_event_id="FIRMS_TEST_REPEAT_001",
        )
        run2 = service.evaluate_fire_point(
            latitude=20.02,
            longitude=78.05,
            fire_event_id="FIRMS_TEST_REPEAT_001",
        )

        assert run1.fire_event_id == run2.fire_event_id
        assert run1.nearest_forest is not None and run2.nearest_forest is not None
        assert run1.nearest_forest.forest_id == run2.nearest_forest.forest_id
        assert run1.nearest_forest.distance_km == run2.nearest_forest.distance_km
        assert run1.nearest_forest.threat_level == run2.nearest_forest.threat_level

    def test_11_invalid_fire_coordinates_raise_error(
        self, populated_threat_repo: InMemoryForestRepository
    ) -> None:
        """TEST 11: Invalid fire coordinates (NaN/out-of-bounds) raise error."""
        service = ForestThreatService(repository=populated_threat_repo)

        with pytest.raises(InvalidCoordinateError):
            service.evaluate_fire_point(latitude=120.0, longitude=78.0)

        with pytest.raises(InvalidCoordinateError):
            service.evaluate_fire_point(latitude=float("nan"), longitude=78.0)

        with pytest.raises(InvalidCoordinateError):
            service.evaluate_fire_point(latitude=20.0, longitude=200.0)

    def test_12_spatial_prefilter_candidate_reduction(self) -> None:
        """TEST 12: Spatial prefiltering candidate reduction on large dataset."""
        repo = InMemoryForestRepository()
        # Ingest 50 synthetic forests distributed across India (lat 10 to 30)
        elements = []
        for i in range(50):
            lat = 10.0 + (i * 0.4)
            elements.append(
                {
                    "type": "way",
                    "id": 5000 + i,
                    "tags": {"name": f"Synthetic Forest {i}", "natural": "wood"},
                    "geometry": [
                        {"lat": lat, "lon": 75.0},
                        {"lat": lat, "lon": 75.1},
                        {"lat": lat + 0.1, "lon": 75.1},
                        {"lat": lat + 0.1, "lon": 75.0},
                        {"lat": lat, "lon": 75.0},
                    ],
                }
            )
        ForestIngestionService(repository=repo).ingest_raw_elements(elements)
        assert repo.count() == 50

        # Query near lat=10.05, lon=75.05 with small 10km radius
        # Only forest 0 (lat=10.0) and forest 1 (lat=10.4) should even be considered
        service = ForestThreatService(repository=repo)
        assessment = service.evaluate_fire_point(
            latitude=10.05, longitude=75.05, search_radius_km=10.0
        )
        assert assessment.is_threatened is True
        assert len(assessment.nearby_forests) == 1
        assert assessment.nearest_forest is not None
        assert assessment.nearest_forest.name == "Synthetic Forest 0"

    def test_13_api_evaluate_point_endpoint(self, client: TestClient) -> None:
        """TEST 13: GET /forests/threat/evaluate endpoint returns canonical response."""
        # Query near Gir Forest centroid (lat: 21.15, lon: 70.75)
        response = client.get(
            "/forests/threat/evaluate?latitude=21.15&longitude=70.75&search_radius_km=50&threat_radius_km=10"
        )
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "fire_coordinate" in data
        assert pytest.approx(data["fire_coordinate"]["latitude"], 0.001) == 21.15
        assert pytest.approx(data["fire_coordinate"]["longitude"], 0.001) == 70.75
        assert "configuration" in data
        assert data["configuration"]["search_radius_km"] == 50.0
        assert data["configuration"]["threat_radius_km"] == 10.0
        assert "is_threatened" in data
        assert "nearest_forest" in data
        assert "nearby_forests" in data
        assert isinstance(data["nearby_forests"], list)

    def test_14_api_evaluate_firms_event_endpoint(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TEST 14: GET /forests/threat/{event_id} evaluates indexed FIRMS event."""
        from datetime import UTC, datetime

        mock_item = NearbyForestThreatItem(
            forest_id="forest_way_999",
            osm_identity="relation:999",
            name="Gir National Park & Wildlife Sanctuary",
            country_code="IN",
            forest_type=ForestType.NATURAL_WOOD,
            osm_tag="natural=wood",
            distance_km=0.0,
            is_within_threat_radius=True,
            threat_level=ForestThreatLevel.CRITICAL,
            nearest_point=Coordinate(latitude=21.15, longitude=70.75),
            centroid=Coordinate(latitude=21.15, longitude=70.75),
            area_km2=1412.0,
        )

        mock_assessment = ForestThreatAssessment(
            fire_event_id="FIRMS_EVT_GIR_001",
            fire_coordinate=Coordinate(latitude=21.15, longitude=70.75),
            search_radius_km=10.0,
            threat_radius_km=5.0,
            critical_radius_km=1.0,
            high_radius_km=2.5,
            moderate_radius_km=5.0,
            is_threatened=True,
            threat_level=ForestThreatLevel.CRITICAL,
            nearest_forest=mock_item,
            nearby_forests=[mock_item],
            total_threatened_forests=1,
            evaluated_at=datetime.now(UTC),
        )

        monkeypatch.setattr(
            "packages.data.forests.threat_service.ForestThreatService.evaluate_fire_event_by_id",
            lambda self, event_id, **kw: mock_assessment,
        )

        response = client.get("/forests/threat/FIRMS_EVT_GIR_001")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["fire_event_id"] == "FIRMS_EVT_GIR_001"
        assert data["is_threatened"] is True
        assert (
            data["nearest_forest"]["name"] == "Gir National Park & Wildlife Sanctuary"
        )
        assert data["nearest_forest"]["threat_level"] == "CRITICAL"


class TestForestProximityAlertSystemPhase4:
    """Comprehensive test suite for Phase 4: Proximity Detection & Alert System."""

    @pytest.fixture
    def phase4_repo(self) -> InMemoryForestRepository:
        """Create a repository with a known 10x10 km forest polygon at [20.0, 75.0]."""
        repo = InMemoryForestRepository()
        # Forest from lat 20.0 to 20.1, lon 75.0 to 75.1 (roughly 11x10 km)
        forest_element = {
            "type": "way",
            "id": 880011,
            "tags": {
                "name": "Satpura Central Forest Reserve",
                "natural": "wood",
                "addr:country": "IN",
            },
            "geometry": [
                {"lat": 20.0, "lon": 75.0},
                {"lat": 20.0, "lon": 75.1},
                {"lat": 20.1, "lon": 75.1},
                {"lat": 20.1, "lon": 75.0},
                {"lat": 20.0, "lon": 75.0},
            ],
        }
        ForestIngestionService(repository=repo).ingest_raw_elements([forest_element])
        return repo

    def test_01_outside_awareness_distance_classified_as_none(
        self, phase4_repo: InMemoryForestRepository
    ) -> None:
        """Fire > 10 km away is classified as NONE threat and not threatened."""
        service = ForestThreatService(repository=phase4_repo)
        # 20.0 - (15 / 111) = 19.864 (~15 km south of boundary lat 20.0)
        assessment = service.evaluate_fire_point(
            latitude=19.864,
            longitude=75.05,
            search_radius_km=30.0,
        )
        assert assessment.nearest_forest is not None
        assert pytest.approx(assessment.nearest_forest.distance_km, abs=0.5) == 15.1
        assert assessment.nearest_forest.threat_level == ForestThreatLevel.NONE
        assert assessment.nearest_forest.is_within_threat_radius is False
        assert assessment.is_threatened is False
        assert assessment.threat_level == ForestThreatLevel.NONE

    def test_02_awareness_distance_classification(
        self, phase4_repo: InMemoryForestRepository
    ) -> None:
        """Fire between 5.0 km and 10.0 km is classified as AWARENESS threat."""
        service = ForestThreatService(repository=phase4_repo)
        # 20.0 - (7.0 / 111) = 19.937 (~7 km south)
        assessment = service.evaluate_fire_point(
            latitude=19.937,
            longitude=75.05,
            search_radius_km=30.0,
        )
        assert assessment.nearest_forest is not None
        assert pytest.approx(assessment.nearest_forest.distance_km, abs=0.5) == 7.0
        assert assessment.nearest_forest.threat_level == ForestThreatLevel.AWARENESS
        assert assessment.nearest_forest.is_within_threat_radius is True
        assert assessment.is_threatened is True
        assert assessment.threat_level == ForestThreatLevel.AWARENESS

    def test_03_warning_distance_classification(
        self, phase4_repo: InMemoryForestRepository
    ) -> None:
        """Fire between 2.0 km and 5.0 km is classified as WARNING threat."""
        service = ForestThreatService(repository=phase4_repo)
        # 20.0 - (3.5 / 111) = 19.9685 (~3.5 km south)
        assessment = service.evaluate_fire_point(
            latitude=19.9685,
            longitude=75.05,
            search_radius_km=30.0,
        )
        assert assessment.nearest_forest is not None
        assert pytest.approx(assessment.nearest_forest.distance_km, abs=0.5) == 3.5
        assert assessment.nearest_forest.threat_level == ForestThreatLevel.WARNING
        assert assessment.is_threatened is True
        assert assessment.threat_level == ForestThreatLevel.WARNING

    def test_04_critical_distance_classification(
        self, phase4_repo: InMemoryForestRepository
    ) -> None:
        """Fire between 0.0 km and 2.0 km is classified as CRITICAL threat."""
        service = ForestThreatService(repository=phase4_repo)
        # 20.0 - (1.0 / 111) = 19.991 (~1.0 km south)
        assessment = service.evaluate_fire_point(
            latitude=19.991,
            longitude=75.05,
            search_radius_km=30.0,
        )
        assert assessment.nearest_forest is not None
        assert pytest.approx(assessment.nearest_forest.distance_km, abs=0.3) == 1.0
        assert assessment.nearest_forest.threat_level == ForestThreatLevel.CRITICAL
        assert assessment.nearest_forest.inside_forest is False
        assert assessment.is_threatened is True
        assert assessment.threat_level == ForestThreatLevel.CRITICAL

    def test_05_inside_forest_boundary_classification(
        self, phase4_repo: InMemoryForestRepository
    ) -> None:
        """Fire inside the forest polygon is classified as INSIDE_FOREST (0 km)."""
        service = ForestThreatService(repository=phase4_repo)
        # Inside polygon: lat 20.05, lon 75.05
        assessment = service.evaluate_fire_point(
            latitude=20.05,
            longitude=75.05,
            search_radius_km=30.0,
        )
        assert assessment.nearest_forest is not None
        assert assessment.nearest_forest.distance_km == 0.0
        assert assessment.nearest_forest.inside_forest is True
        assert assessment.nearest_forest.threat_level == ForestThreatLevel.INSIDE_FOREST
        assert assessment.is_threatened is True
        assert assessment.threat_level == ForestThreatLevel.INSIDE_FOREST

    def test_06_proximity_alert_creation_and_notification(
        self, phase4_repo: InMemoryForestRepository, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Creating an alert dispatches multi-channel notification and logs record."""
        service = ForestThreatService(repository=phase4_repo)
        forests, _ = phase4_repo.list_forests()
        forest = forests[0]

        mock_item = NearbyForestThreatItem(
            forest_id=forest.forest_id,
            osm_identity=forest.osm_identity,
            name=forest.name,
            country_code=forest.country_code,
            forest_type=forest.forest_type,
            osm_tag=forest.osm_tag,
            distance_km=1.2,
            inside_forest=False,
            is_within_threat_radius=True,
            threat_level=ForestThreatLevel.CRITICAL,
            nearest_point=Coordinate(latitude=20.0, longitude=75.05),
            centroid=forest.centroid,
            area_km2=forest.area_km2,
        )
        mock_assessment = ForestThreatAssessment(
            fire_event_id="FIRMS_TEST_PHASE4_001",
            fire_coordinate=Coordinate(latitude=19.989, longitude=75.05),
            search_radius_km=30.0,
            threat_radius_km=10.0,
            critical_radius_km=2.0,
            high_radius_km=2.5,
            moderate_radius_km=5.0,
            is_threatened=True,
            threat_level=ForestThreatLevel.CRITICAL,
            nearest_forest=mock_item,
            nearby_forests=[mock_item],
            total_threatened_forests=1,
            evaluated_at=forest.created_at,
        )
        monkeypatch.setattr(
            service, "evaluate_fire_event_by_id", lambda *a, **kw: mock_assessment
        )

        alert = service.create_forest_proximity_alert(
            event_id="FIRMS_TEST_PHASE4_001",
            forest_id=forest.forest_id,
            fire_confidence=98.0,
            channels=["sms", "whatsapp"],
        )

        assert alert.event_id == "FIRMS_TEST_PHASE4_001"
        assert alert.forest_id == forest.forest_id
        assert alert.forest_name == "Satpura Central Forest Reserve"
        assert alert.threat_level in (
            ForestThreatLevel.CRITICAL,
            ForestThreatLevel.INSIDE_FOREST,
            ForestThreatLevel.WARNING,
            ForestThreatLevel.AWARENESS,
        )
        assert alert.notification_dispatched is True

    def test_07_alert_deduplication_prevents_duplicate_notifications(
        self, phase4_repo: InMemoryForestRepository, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Repeated alert triggers for same event/forest/threat do not re-dispatch."""
        service = ForestThreatService(repository=phase4_repo)
        forests, _ = phase4_repo.list_forests()
        forest = forests[0]

        mock_item = NearbyForestThreatItem(
            forest_id=forest.forest_id,
            osm_identity=forest.osm_identity,
            name=forest.name,
            country_code=forest.country_code,
            forest_type=forest.forest_type,
            osm_tag=forest.osm_tag,
            distance_km=1.2,
            inside_forest=False,
            is_within_threat_radius=True,
            threat_level=ForestThreatLevel.CRITICAL,
            nearest_point=Coordinate(latitude=20.0, longitude=75.05),
            centroid=forest.centroid,
            area_km2=forest.area_km2,
        )
        mock_assessment = ForestThreatAssessment(
            fire_event_id="FIRMS_DEDUP_001",
            fire_coordinate=Coordinate(latitude=19.989, longitude=75.05),
            search_radius_km=30.0,
            threat_radius_km=10.0,
            critical_radius_km=2.0,
            high_radius_km=2.5,
            moderate_radius_km=5.0,
            is_threatened=True,
            threat_level=ForestThreatLevel.CRITICAL,
            nearest_forest=mock_item,
            nearby_forests=[mock_item],
            total_threatened_forests=1,
            evaluated_at=forest.created_at,
        )
        monkeypatch.setattr(
            service, "evaluate_fire_event_by_id", lambda *a, **kw: mock_assessment
        )

        # First alert dispatch
        alert1 = service.create_forest_proximity_alert(
            event_id="FIRMS_DEDUP_001",
            forest_id=forest.forest_id,
        )
        assert alert1.notification_dispatched is True

        # Second alert call for same event/forest
        alert2 = service.create_forest_proximity_alert(
            event_id="FIRMS_DEDUP_001",
            forest_id=forest.forest_id,
            force_dispatch=False,
        )
        # Should NOT re-dispatch
        assert alert2.notification_dispatched is False
        assert alert2.is_escalation is False

        # If forced, it will dispatch
        alert3 = service.create_forest_proximity_alert(
            event_id="FIRMS_DEDUP_001",
            forest_id=forest.forest_id,
            force_dispatch=True,
        )
        assert alert3.notification_dispatched is True

    def test_08_alert_escalation_triggers_new_notification(
        self, phase4_repo: InMemoryForestRepository, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Escalating threat level (e.g. WARNING -> CRITICAL) triggers notification."""
        service = ForestThreatService(repository=phase4_repo)
        forests, _ = phase4_repo.list_forests()
        forest = forests[0]

        # Simulate initial WARNING assessment
        def mock_eval_warning(*args, **kwargs):
            item = NearbyForestThreatItem(
                forest_id=forest.forest_id,
                osm_identity=forest.osm_identity,
                name=forest.name,
                country_code=forest.country_code,
                forest_type=forest.forest_type,
                osm_tag=forest.osm_tag,
                distance_km=3.5,
                inside_forest=False,
                is_within_threat_radius=True,
                threat_level=ForestThreatLevel.WARNING,
                nearest_point=Coordinate(latitude=20.0, longitude=75.05),
                centroid=forest.centroid,
                area_km2=forest.area_km2,
            )
            return ForestThreatAssessment(
                fire_event_id="FIRMS_ESCALATE_001",
                fire_coordinate=Coordinate(latitude=19.968, longitude=75.05),
                search_radius_km=30.0,
                threat_radius_km=10.0,
                critical_radius_km=2.0,
                high_radius_km=2.5,
                moderate_radius_km=5.0,
                is_threatened=True,
                threat_level=ForestThreatLevel.WARNING,
                nearest_forest=item,
                nearby_forests=[item],
                total_threatened_forests=1,
                evaluated_at=forest.created_at,
            )

        monkeypatch.setattr(service, "evaluate_fire_event_by_id", mock_eval_warning)
        alert_w = service.create_forest_proximity_alert(
            event_id="FIRMS_ESCALATE_001",
            forest_id=forest.forest_id,
        )
        assert alert_w.threat_level == ForestThreatLevel.WARNING
        assert alert_w.notification_dispatched is True

        # Now simulate escalation to CRITICAL
        def mock_eval_critical(*args, **kwargs):
            item = NearbyForestThreatItem(
                forest_id=forest.forest_id,
                osm_identity=forest.osm_identity,
                name=forest.name,
                country_code=forest.country_code,
                forest_type=forest.forest_type,
                osm_tag=forest.osm_tag,
                distance_km=1.2,
                inside_forest=False,
                is_within_threat_radius=True,
                threat_level=ForestThreatLevel.CRITICAL,
                nearest_point=Coordinate(latitude=20.0, longitude=75.05),
                centroid=forest.centroid,
                area_km2=forest.area_km2,
            )
            return ForestThreatAssessment(
                fire_event_id="FIRMS_ESCALATE_001",
                fire_coordinate=Coordinate(latitude=19.989, longitude=75.05),
                search_radius_km=30.0,
                threat_radius_km=10.0,
                critical_radius_km=2.0,
                high_radius_km=2.5,
                moderate_radius_km=5.0,
                is_threatened=True,
                threat_level=ForestThreatLevel.CRITICAL,
                nearest_forest=item,
                nearby_forests=[item],
                total_threatened_forests=1,
                evaluated_at=forest.created_at,
            )

        monkeypatch.setattr(service, "evaluate_fire_event_by_id", mock_eval_critical)
        alert_c = service.create_forest_proximity_alert(
            event_id="FIRMS_ESCALATE_001",
            forest_id=forest.forest_id,
        )
        assert alert_c.threat_level == ForestThreatLevel.CRITICAL
        assert alert_c.is_escalation is True
        assert alert_c.notification_dispatched is True

    def test_09_api_post_threat_alert_endpoint(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """POST /forests/threat/alert triggers alert workflow and returns 200."""
        from datetime import UTC, datetime

        from packages.schemas.forest import ForestProximityAlertEvent

        mock_alert = ForestProximityAlertEvent(
            alert_id="alert:EVT_101:FOR_202:CRITICAL",
            event_id="EVT_101",
            forest_id="FOR_202",
            forest_name="Nagarhole Tiger Reserve",
            distance_km=1.45,
            inside_forest=False,
            threat_level=ForestThreatLevel.CRITICAL,
            fire_confidence=99.0,
            fire_coordinate=Coordinate(latitude=12.0, longitude=76.0),
            created_at=datetime.now(UTC),
            is_escalation=False,
            notification_dispatched=True,
            notification_id="notif_EVT_101_FOR_202_123456",
        )

        monkeypatch.setattr(
            "packages.data.forests.threat_service.ForestThreatService.create_forest_proximity_alert",
            lambda self, **kw: mock_alert,
        )

        payload = {
            "event_id": "EVT_101",
            "forest_id": "FOR_202",
            "fire_confidence": 99.0,
            "channels": ["sms", "whatsapp"],
        }
        response = client.post("/forests/threat/alert", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["alert_id"] == "alert:EVT_101:FOR_202:CRITICAL"
        assert data["forest_name"] == "Nagarhole Tiger Reserve"
        assert data["threat_level"] == "CRITICAL"
        assert data["notification_dispatched"] is True
        assert data["distance_km"] == 1.45


def _make_test_forest(
    forest_id: str = "forest_way_101",
    lat: float = 20.0,
    lon: float = 75.0,
    name: str = "Test Forest",
    country_code: str = "IN",
) -> ForestAreaRecord:
    from datetime import UTC, datetime

    from packages.schemas.forest import ForestAreaRecord

    return ForestAreaRecord(
        forest_id=forest_id,
        osm_id=101,
        osm_type="way",
        osm_identity=f"way:{forest_id}",
        name=name,
        name_en=name,
        country_code=country_code,
        region="Western Ghats",
        forest_type=ForestType.NATURAL_WOOD,
        osm_tag="natural=wood",
        geometry=ForestGeometry(
            type="Polygon",
            coordinates=[
                [
                    [lon - 0.05, lat - 0.05],
                    [lon + 0.05, lat - 0.05],
                    [lon + 0.05, lat + 0.05],
                    [lon - 0.05, lat + 0.05],
                    [lon - 0.05, lat - 0.05],
                ]
            ],
        ),
        centroid=Coordinate(latitude=lat, longitude=lon),
        area_km2=120.5,
        metadata_tags={"natural": "wood"},
        source="openstreetmap",
        is_repaired=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


class TestForestThreatMonitoringPhase5:
    """Tests for Phase 5 Global Forest Monitoring & Threat Intelligence."""

    def test_01_global_monitoring_dashboard_aggregation(
        self, mock_repo: InMemoryForestRepository
    ) -> None:
        """Dashboard evaluates forests against active fires and calculates KPIs."""
        service = ForestThreatService(repository=mock_repo)
        events = service.get_all_active_events_for_evaluation()
        ref_lat = events[0]["latitude"] if events else 22.45
        ref_lon = events[0]["longitude"] if events else 69.85

        # Insert 2 forests: 1 safe (far away), 1 threatened (near active event)
        forest_safe = _make_test_forest(
            forest_id="for_safe_01",
            lat=10.0,
            lon=10.0,
            name="Safe Reserve",
        )
        forest_crit = _make_test_forest(
            forest_id="for_crit_02",
            lat=ref_lat + 0.01,
            lon=ref_lon + 0.01,
            name="Near Event Reserve",
        )
        mock_repo.save_forest(forest_safe)
        mock_repo.save_forest(forest_crit)

        summary, paged_items, total = service.get_global_monitoring_dashboard()

        assert summary.total_monitored_forests >= 2
        assert summary.total_threatened_forests >= 1
        assert total >= 2
        assert len(paged_items) >= 2

        # Primary item should be the threatened forest
        assert paged_items[0].forest_id == "for_crit_02"
        assert paged_items[0].threat_level in (
            ForestThreatLevel.CRITICAL,
            ForestThreatLevel.ACTIVE_FIRE,
            ForestThreatLevel.WARNING,
            ForestThreatLevel.AWARENESS,
        )
        assert len(paged_items[0].why_at_risk) >= 1

    def test_02_multi_event_priority_ranking(
        self, mock_repo: InMemoryForestRepository, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When multiple fires threaten a forest, highest severity event is primary."""
        forest = _make_test_forest(
            forest_id="for_multi_01",
            lat=20.0,
            lon=75.0,
            name="Multi Threat Forest",
        )
        mock_repo.save_forest(forest)

        # Mock two active events: one at ~7.7 km (AWARENESS) and one at ~1.1 km (CRITICAL)
        mock_events = [
            {
                "event_id": "EVT_AWARE",
                "latitude": 20.12,  # ~7.7 km away from northern boundary (20.05)
                "longitude": 75.0,
                "frp_mw": 15.0,
                "confidence": 80.0,
                "classification": "AGRICULTURAL_FIRE",
                "detected_at": None,
            },
            {
                "event_id": "EVT_CRIT",
                "latitude": 20.06,  # ~1.1 km away from northern boundary (20.05)
                "longitude": 75.0,
                "frp_mw": 85.0,
                "confidence": 98.0,
                "classification": "INDUSTRIAL_FLARE",
                "detected_at": None,
            },
        ]

        service = ForestThreatService(repository=mock_repo)
        monkeypatch.setattr(
            service, "get_all_active_events_for_evaluation", lambda: mock_events
        )

        detail = service.get_forest_threat_detail_by_id("for_multi_01")
        assert detail.threat_level == ForestThreatLevel.CRITICAL
        assert detail.nearest_event_id == "EVT_CRIT"
        assert detail.primary_frp_mw == 85.0
        assert len(detail.threatening_events) == 2
        assert any("Multi" in b or "2 active" in b for b in detail.why_at_risk)

    def test_03_explainability_why_at_risk_generation(
        self, mock_repo: InMemoryForestRepository
    ) -> None:
        """Why-at-risk bullets are grounded in distance, FRP, and classification."""
        forest = _make_test_forest(
            forest_id="for_gir_01",
            lat=21.15,
            lon=70.80,
            name="Gir National Park",
        )
        mock_repo.save_forest(forest)
        service = ForestThreatService(repository=mock_repo)

        summary, paged_items, _ = service.get_global_monitoring_dashboard(
            search="Gir"
        )
        assert len(paged_items) == 1
        gir_item = paged_items[0]
        assert len(gir_item.why_at_risk) >= 1
        for bullet in gir_item.why_at_risk:
            assert isinstance(bullet, str)
            assert len(bullet) > 10

    def test_04_status_and_search_filtering(
        self, mock_repo: InMemoryForestRepository
    ) -> None:
        """Dashboard filters properly by status, country code, and search term."""
        f_in = _make_test_forest(
            forest_id="for_in_01",
            lat=15.0,
            lon=75.0,
            name="Dandeli Forest",
            country_code="IN",
        )
        f_br = _make_test_forest(
            forest_id="for_br_01",
            lat=-3.0,
            lon=-60.0,
            name="Amazon Reserve",
            country_code="BR",
        )
        mock_repo.save_forest(f_in)
        mock_repo.save_forest(f_br)

        service = ForestThreatService(repository=mock_repo)

        # Search filter
        _, results_search, total_search = service.get_global_monitoring_dashboard(
            search="Dandeli"
        )
        assert total_search == 1
        assert results_search[0].forest_id == "for_in_01"

        # Country filter
        _, results_br, total_br = service.get_global_monitoring_dashboard(
            country_code="BR"
        )
        assert total_br == 1
        assert results_br[0].forest_id == "for_br_01"

    def test_05_single_forest_threat_detail(
        self, mock_repo: InMemoryForestRepository
    ) -> None:
        """Single forest threat detail returns comprehensive report."""
        forest = _make_test_forest(
            forest_id="for_detail_01",
            lat=22.45,
            lon=69.85,
            name="Detailed Forest",
        )
        mock_repo.save_forest(forest)
        service = ForestThreatService(repository=mock_repo)

        detail = service.get_forest_threat_detail_by_id("for_detail_01")
        assert detail.forest.forest_id == "for_detail_01"
        assert detail.evaluated_at is not None
        assert isinstance(detail.why_at_risk, list)

    def test_06_deterministic_simulation_escalation_lifecycle(
        self, mock_repo: InMemoryForestRepository, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deterministic simulation progresses cleanly and handles deduplication."""
        service = ForestThreatService(repository=mock_repo)
        events = service.get_all_active_events_for_evaluation()
        active_ev_id = events[0]["event_id"] if events else "evt_jamnagar_flaring_001"
        ev_lat = events[0]["latitude"] if events else 22.45
        ev_lon = events[0]["longitude"] if events else 70.05

        forest = _make_test_forest(
            forest_id="for_demo_01",
            lat=ev_lat,
            lon=ev_lon + 0.01,
            name="Gir Escalation Demo Forest",
        )
        mock_repo.save_forest(forest)

        # First alert dispatch
        alert1 = service.create_forest_proximity_alert(
            event_id=active_ev_id,
            forest_id="for_demo_01",
            fire_confidence=98.0,
            force_dispatch=True,
        )
        assert alert1.forest_id == "for_demo_01"
        assert alert1.notification_dispatched is True

        # Repeated call without force_dispatch is deduplicated
        alert2 = service.create_forest_proximity_alert(
            event_id=active_ev_id,
            forest_id="for_demo_01",
            fire_confidence=98.0,
            force_dispatch=False,
        )
        assert alert2.notification_dispatched is False

    def test_07_api_get_monitoring_dashboard_endpoint(
        self, client: TestClient
    ) -> None:
        """GET /forests/threats/monitoring returns 200 with dashboard summary."""
        response = client.get("/forests/threats/monitoring")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "summary" in data
        assert "total_monitored_forests" in data["summary"]
        assert "forests" in data
        assert isinstance(data["forests"], list)
        assert data["total_filtered"] >= 0

    def test_08_api_get_forest_threat_detail_endpoint(
        self, client: TestClient
    ) -> None:
        """GET /forests/threats/forest/{forest_id} returns 200 with detail."""
        # Query list to get an existing forest_id
        list_res = client.get("/forests?limit=1")
        assert list_res.status_code == 200
        features = list_res.json()["features"]
        if features:
            f_id = features[0]["properties"]["forest_id"]
            res = client.get(f"/forests/threats/forest/{f_id}")
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["forest"]["id"] == f_id
            assert "threat_level" in data
            assert "why_at_risk" in data

    def test_09_api_get_forest_threat_detail_not_found(
        self, client: TestClient
    ) -> None:
        """GET /forests/threats/forest/non_existent returns 404."""
        response = client.get("/forests/threats/forest/non_existent_forest_999999")
        assert response.status_code == 404


