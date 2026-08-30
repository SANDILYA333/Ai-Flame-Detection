"""Unit, validation, determinism, and integration tests for DATA-004."""

import json
import random
from pathlib import Path

import pytest

from packages.config.scientific import ScientificConfig
from packages.context.service import enrich_with_context
from packages.data.context import (
    ContextValidationError,
    compute_canonical_feature_id,
    compute_context_raw_hash,
    map_fuel_or_industry_to_context_type,
    map_tags_to_context_type,
    parse_context_geojson,
    parse_context_geojson_with_report,
    parse_industrial_catalog_csv,
    parse_industrial_catalog_csv_with_report,
)
from packages.schemas.common import Coordinate
from packages.schemas.enums import ContextType

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "context"
_OSM_FIXTURE = _FIXTURES_DIR / "osm_industrial_zones.geojson"
_WRI_FIXTURE = _FIXTURES_DIR / "wri_power_plants_sample.csv"
_BAD_COORDS_FIXTURE = _FIXTURES_DIR / "malformed_coordinates.geojson"
_BAD_GEOMS_FIXTURE = _FIXTURES_DIR / "malformed_geometries.geojson"
_EMPTY_FIXTURE = _FIXTURES_DIR / "empty.geojson"


class TestGeoJsonParsing:
    """Test GeoJSON context ingestion and normalization."""

    def test_valid_osm_geojson_fixture(self) -> None:
        """OSM GeoJSON fixture parses into canonical ContextFeature records."""
        features = parse_context_geojson(
            geojson_input=_OSM_FIXTURE,
            provider="osm",
            dataset_name="osm_industrial_zones",
            dataset_version="2026-08",
            strict=True,
        )

        assert len(features) == 5

        # Check types parsed
        types = {f.context_type for f in features}
        assert ContextType.OIL_GAS in types
        assert ContextType.POWER in types
        assert ContextType.MINING in types
        assert ContextType.AGRICULTURAL in types

        # Check provenance
        for f in features:
            assert f.provider == "osm"
            assert f.dataset_name == "osm_industrial_zones"
            assert f.dataset_version == "2026-08"
            assert f.feature_id.startswith("ctx_osm_")

    def test_geojson_coordinates_order(self) -> None:
        """GeoJSON [lon, lat] is mapped to Coordinate(latitude=lat, longitude=lon)."""
        single_point_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "node_test_1",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [70.0512, 22.4502],  # [lon, lat]
                    },
                    "properties": {
                        "name": "Jamnagar Flare Point",
                        "industrial": "refinery",
                    },
                }
            ],
        }

        features = parse_context_geojson(
            geojson_input=single_point_geojson,
            provider="osm",
            dataset_name="test_points",
        )

        assert len(features) == 1
        feat = features[0]
        assert feat.geometry.latitude == pytest.approx(22.4502)
        assert feat.geometry.longitude == pytest.approx(70.0512)
        assert feat.bounding_box is None  # Point feature has no bounding envelope
        assert feat.facility_name == "Jamnagar Flare Point"
        assert feat.context_type == ContextType.OIL_GAS

    def test_polygon_bounding_box_and_centroid(self) -> None:
        """Polygon features compute envelope bounding_box and spherical centroid."""
        polygon_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "id": "poly_test_1",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [70.0, 22.0],
                                [70.2, 22.0],
                                [70.2, 22.2],
                                [70.0, 22.2],
                                [70.0, 22.0],
                            ]
                        ],
                    },
                    "properties": {
                        "name": "Test Industrial Area",
                        "landuse": "industrial",
                    },
                }
            ],
        }

        features = parse_context_geojson(
            geojson_input=polygon_geojson,
            provider="osm",
            dataset_name="test_polygons",
        )

        assert len(features) == 1
        feat = features[0]
        assert feat.bounding_box is not None
        assert feat.bounding_box.min_latitude == pytest.approx(22.0)
        assert feat.bounding_box.max_latitude == pytest.approx(22.2)
        assert feat.bounding_box.min_longitude == pytest.approx(70.0)
        assert feat.bounding_box.max_longitude == pytest.approx(70.2)

        # Centroid is inside bounds
        assert 22.0 < feat.geometry.latitude < 22.2
        assert 70.0 < feat.geometry.longitude < 70.2

    def test_empty_geojson_returns_empty_list(self) -> None:
        """Empty GeoJSON FeatureCollection returns an empty list."""
        features = parse_context_geojson(
            geojson_input=_EMPTY_FIXTURE,
            provider="osm",
            dataset_name="empty",
        )
        assert features == []


class TestCsvCatalogParsing:
    """Test tabular industrial / power plant catalog ingestion."""

    def test_valid_wri_csv_fixture(self) -> None:
        """WRI power plants CSV parses into canonical ContextFeature records."""
        features = parse_industrial_catalog_csv(
            csv_input=_WRI_FIXTURE,
            provider="wri",
            dataset_name="power_plants",
            dataset_version="v1.3",
            strict=True,
        )

        assert len(features) == 4
        for f in features:
            assert f.provider == "wri"
            assert f.dataset_name == "power_plants"
            assert f.dataset_version == "v1.3"
            assert f.context_type == ContextType.POWER
            assert f.bounding_box is None
            assert f.facility_name is not None
            assert f.raw_metadata is not None
            assert "capacity_mw" in f.raw_metadata

    def test_csv_missing_coordinates_raises_strict(self) -> None:
        """Missing coordinate columns in CSV raises ContextValidationError."""
        bad_csv = "name,capacity_mw,primary_fuel\nBad Plant,500,Coal\n"
        with pytest.raises(ContextValidationError) as exc_info:
            parse_industrial_catalog_csv(bad_csv, strict=True)

        assert "missing 'latitude' or 'longitude'" in str(exc_info.value).lower()

    def test_csv_empty_stream_returns_empty_list(self) -> None:
        """Empty CSV stream returns an empty list."""
        features = parse_industrial_catalog_csv("")
        assert features == []


class TestTagClassification:
    """Test OSM tag and industrial sector categorization rules."""

    def test_osm_tag_mappings(self) -> None:
        """OSM metadata tags map to appropriate ContextType categories."""
        assert map_tags_to_context_type({"power": "plant"}) == ContextType.POWER
        assert map_tags_to_context_type({"amenity": "power"}) == ContextType.POWER
        assert (
            map_tags_to_context_type({"industrial": "refinery"}) == ContextType.OIL_GAS
        )
        assert map_tags_to_context_type({"man_made": "flare"}) == ContextType.OIL_GAS
        assert map_tags_to_context_type({"landuse": "quarry"}) == ContextType.MINING
        assert map_tags_to_context_type({"resource": "coal"}) == ContextType.MINING
        assert (
            map_tags_to_context_type({"landuse": "industrial"})
            == ContextType.INDUSTRIAL
        )
        assert (
            map_tags_to_context_type({"industrial": "steel"}) == ContextType.INDUSTRIAL
        )
        assert (
            map_tags_to_context_type({"landuse": "farmland"})
            == ContextType.AGRICULTURAL
        )
        assert (
            map_tags_to_context_type({"natural": "wood"})
            == ContextType.FOREST_VEGETATION
        )
        assert map_tags_to_context_type({"landuse": "residential"}) == ContextType.URBAN
        assert map_tags_to_context_type({"highway": "motorway"}) == ContextType.OTHER

    def test_industrial_fuel_mappings(self) -> None:
        """Fuel and sector types map to appropriate ContextType categories."""
        assert (
            map_fuel_or_industry_to_context_type("Thermal", "Coal") == ContextType.POWER
        )
        assert (
            map_fuel_or_industry_to_context_type("Refinery", "Oil")
            == ContextType.OIL_GAS
        )
        assert (
            map_fuel_or_industry_to_context_type("Mining", "Lignite")
            == ContextType.MINING
        )
        assert (
            map_fuel_or_industry_to_context_type("Manufacturing", "Steel")
            == ContextType.INDUSTRIAL
        )


class TestStrictVsReportMode:
    """Test strict rejection versus diagnostic batch error reporting."""

    def test_strict_mode_raises_on_invalid_coordinate(self) -> None:
        """Strict GeoJSON parser raises ContextValidationError on bad coords."""
        with pytest.raises(ContextValidationError) as exc_info:
            parse_context_geojson(
                geojson_input=_BAD_COORDS_FIXTURE,
                provider="osm",
                dataset_name="bad_coords",
                strict=True,
            )

        assert (
            "latitude" in str(exc_info.value).lower()
            or "coordinates" in str(exc_info.value).lower()
        )

    def test_report_mode_captures_all_errors(self) -> None:
        """Report mode processes batch without aborting and captures all errors."""
        report = parse_context_geojson_with_report(
            geojson_input=_BAD_COORDS_FIXTURE,
            provider="osm",
            dataset_name="bad_coords",
        )

        assert report.total_items == 3
        assert report.valid_count == 0
        assert report.error_count == 3
        assert len(report.errors) == 3
        assert report.errors[0].item_index == 0

    def test_malformed_geometries_in_report_mode(self) -> None:
        """Report mode records errors for missing geometry and empty rings."""
        report = parse_context_geojson_with_report(
            geojson_input=_BAD_GEOMS_FIXTURE,
            provider="osm",
            dataset_name="bad_geoms",
        )

        assert report.total_items == 3
        assert report.valid_count == 0
        assert report.error_count == 3

    def test_csv_report_mode(self) -> None:
        """CSV report mode collects valid rows and isolates bad rows."""
        csv_data = (
            "facility_name,latitude,longitude,primary_fuel\n"
            "Plant A,24.10,82.60,Coal\n"
            "Plant B,invalid_lat,82.60,Gas\n"
            "Plant C,24.12,82.62,Hydro\n"
        )
        report = parse_industrial_catalog_csv_with_report(
            csv_input=csv_data,
            provider="wri",
            dataset_name="power_mix",
        )

        assert report.total_items == 3
        assert report.valid_count == 2
        assert report.error_count == 1
        assert report.errors[0].item_index == 1


class TestMissingnessAndProvenance:
    """Test missingness preservation and cryptographic hashing."""

    def test_missing_optional_attributes_remain_none(self) -> None:
        """Missing optional fields remain None rather than default values."""
        minimal_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [70.0, 20.0],
                    },
                    "properties": {},
                }
            ],
        }

        features = parse_context_geojson(
            geojson_input=minimal_geojson,
            provider="test_prov",
            dataset_name="minimal",
        )

        assert len(features) == 1
        feat = features[0]
        assert feat.facility_name is None
        assert feat.bounding_box is None
        assert feat.valid_from is None
        assert feat.valid_to is None
        assert feat.raw_metadata is None

    def test_raw_hash_determinism_and_sensitivity(self) -> None:
        """Raw hash is deterministic SHA-256 and sensitive to mutations."""
        dict_1 = {"name": "Plant 1", "lat": 20.0, "lon": 70.0}
        # Same contents with different key insertion order
        dict_2 = {"lon": 70.0, "name": "Plant 1", "lat": 20.0}
        dict_3 = {"name": "Plant 2", "lat": 20.0, "lon": 70.0}

        h1 = compute_context_raw_hash(dict_1)
        h2 = compute_context_raw_hash(dict_2)
        h3 = compute_context_raw_hash(dict_3)

        assert h1 == h2
        assert len(h1) == 64
        assert h1 != h3

    def test_deterministic_feature_id(self) -> None:
        """Feature ID generation is deterministic and sanitized."""
        id1 = compute_canonical_feature_id("OSM", "way/12345", "a" * 64)
        id2 = compute_canonical_feature_id("OSM", "way/12345", "a" * 64)
        id_fallback = compute_canonical_feature_id("OSM", None, "abcdef1234567890" * 4)

        assert id1 == id2
        assert id1 == "ctx_osm_way_12345"
        assert id_fallback == "ctx_osm_abcdef123456"


class TestPermutationDeterminism:
    """Test ordering determinism and permutation invariance across trials."""

    def test_geojson_permutation_invariance_20_trials(self) -> None:
        """Randomly shuffled GeoJSON inputs yield identical canonical output."""
        with open(_OSM_FIXTURE, encoding="utf-8") as f:
            base_data = json.load(f)

        features_list = base_data["features"]

        # Baseline parse
        baseline = parse_context_geojson(
            geojson_input=base_data,
            provider="osm",
            dataset_name="osm_industrial_zones",
        )
        baseline_ids = [f.feature_id for f in baseline]

        rng = random.Random(42)
        for trial in range(20):
            shuffled = list(features_list)
            rng.shuffle(shuffled)
            trial_data = {"type": "FeatureCollection", "features": shuffled}

            trial_features = parse_context_geojson(
                geojson_input=trial_data,
                provider="osm",
                dataset_name="osm_industrial_zones",
            )
            trial_ids = [f.feature_id for f in trial_features]

            assert trial_ids == baseline_ids, (
                f"Permutation mismatch at trial {trial + 1}"
            )

    def test_csv_permutation_invariance_20_trials(self) -> None:
        """Randomly shuffled CSV input rows yield identical canonical output."""
        with open(_WRI_FIXTURE, encoding="utf-8") as f:
            lines = f.readlines()

        header = lines[0]
        data_rows = lines[1:]

        baseline = parse_industrial_catalog_csv(
            csv_input="".join(lines),
            provider="wri",
            dataset_name="power_plants",
        )
        baseline_ids = [f.feature_id for f in baseline]

        rng = random.Random(42)
        for trial in range(20):
            shuffled_rows = list(data_rows)
            rng.shuffle(shuffled_rows)
            trial_csv = header + "".join(shuffled_rows)

            trial_features = parse_industrial_catalog_csv(
                csv_input=trial_csv,
                provider="wri",
                dataset_name="power_plants",
            )
            trial_ids = [f.feature_id for f in trial_features]

            assert trial_ids == baseline_ids, (
                f"CSV permutation mismatch at trial {trial + 1}"
            )


class TestPhase3ContextHandover:
    """Verify ingested ContextFeature objects integrate with Phase 3 CONTEXT."""

    def test_enrich_with_parsed_context_features(self) -> None:
        """Parsed context features enrich target entity via Phase 3 service."""
        from datetime import UTC, datetime

        features = parse_context_geojson(
            geojson_input=_OSM_FIXTURE,
            provider="osm",
            dataset_name="osm_industrial_zones",
        )

        # Jamnagar target coordinate
        target_coord = Coordinate(latitude=22.4500, longitude=70.0500)
        target_time = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
        config = ScientificConfig(
            version="v1.0-test",
            name="test_profile",
            description="Calibrated test config",
            spatial_cluster_radius_meters=1000.0,
            temporal_window_hours=2.0,
            persistence_threshold_days=30.0,
            persistence_min_observations=3,
            attribution_radius_meters=5000.0,
            attribution_confidence_threshold=0.6,
            minimum_event_confidence=0.5,
            abstention_confidence_threshold=0.3,
        )

        evidence_list = enrich_with_context(
            target_id="evt_test_123",
            target_coord=target_coord,
            target_time=target_time,
            candidate_features=features,
            config=config,
        )

        # Nearby Jamnagar features are within attribution radius
        assert len(evidence_list) >= 2
        assert config.attribution_radius_meters is not None
        for ev in evidence_list:
            assert ev.context_id.startswith("ctx_")
            assert ev.distance_to_event_meters is not None
            assert ev.distance_to_event_meters <= config.attribution_radius_meters
