"""Unit, validation, determinism, and integration tests.
Tests industrial asset data normalization, enrichment, and deduplication.
"""

import pytest

from packages.data.industrial import (
    AssetType,
    IndustrialAsset,
    IndustrialAssetCollection,
    IndustrialDataLoader,
    IndustryType,
    OperationalStatus,
    compute_canonical_asset_id,
    find_duplicate_candidates,
    haversine_distance_meters,
    link_duplicate_records,
    normalize_coordinates,
    normalize_facility_name,
    normalize_industry_and_asset_type,
    normalize_operational_status,
    normalize_state_name,
)
from packages.schemas.enums import ContextType


class TestCoordinateValidation:
    """Test coordinate validation and bounds enforcement."""

    def test_valid_wgs84_coordinates(self) -> None:
        """Valid coordinates are accepted and rounded to 6 decimals."""
        lat, lon, is_valid = normalize_coordinates(22.450212345, 70.051212345)
        assert is_valid is True
        assert lat == pytest.approx(22.450212)
        assert lon == pytest.approx(70.051212)

    def test_string_numeric_coordinates(self) -> None:
        """String numerical coordinates are properly converted and validated."""
        lat, lon, is_valid = normalize_coordinates("28.6139", "77.2090")
        assert is_valid is True
        assert lat == pytest.approx(28.6139)
        assert lon == pytest.approx(77.2090)

    def test_out_of_range_latitude_rejected(self) -> None:
        """Latitude outside [-90, 90] is flagged as invalid."""
        _, _, is_valid = normalize_coordinates(95.0, 77.0)
        assert is_valid is False
        _, _, is_valid = normalize_coordinates(-91.0, 77.0)
        assert is_valid is False

    def test_out_of_range_longitude_rejected(self) -> None:
        """Longitude outside [-180, 180] is flagged as invalid."""
        _, _, is_valid = normalize_coordinates(22.0, 185.0)
        assert is_valid is False
        _, _, is_valid = normalize_coordinates(22.0, -181.0)
        assert is_valid is False

    def test_nan_and_inf_rejected(self) -> None:
        """Non-finite floats are rejected safely."""
        _, _, is_valid = normalize_coordinates(float("nan"), 77.0)
        assert is_valid is False
        _, _, is_valid = normalize_coordinates(22.0, float("inf"))
        assert is_valid is False

    def test_none_and_malformed_rejected(self) -> None:
        """None and non-numeric strings are rejected safely without crashing."""
        _, _, is_valid = normalize_coordinates(None, 77.0)
        assert is_valid is False
        _, _, is_valid = normalize_coordinates("invalid_coord", "77.0")
        assert is_valid is False


class TestNameNormalization:
    """Test facility name cleaning and normalization."""

    def test_whitespace_and_newline_cleaning(self) -> None:
        """Excess whitespace, tabs, and newlines are collapsed."""
        raw = "  Jamnagar   Refinery\n\tComplex  "
        clean = normalize_facility_name(raw)
        assert clean == "Jamnagar Refinery Complex"

    def test_preserves_acronyms(self) -> None:
        """Industry acronyms (NTPC, BHEL, CCGT, GT) are preserved."""
        raw = "NTPC Dadri CCGT Power Station"
        assert normalize_facility_name(raw) == raw

    def test_none_and_empty_fallback(self) -> None:
        """None and blank names fall back to default unknown designation."""
        assert normalize_facility_name(None) == "Unknown Industrial Facility"
        assert normalize_facility_name("   ") == "Unknown Industrial Facility"


class TestCategoryAndIndustryMapping:
    """Test industry and asset classification mapping."""

    def test_solar_mapping(self) -> None:
        ind, asset_t, ctx_t = normalize_industry_and_asset_type(
            raw_type="Power Plant (Solar)", raw_category="Thermal/Power Industry"
        )
        assert ind == IndustryType.POWER
        assert asset_t == AssetType.POWER_PLANT_SOLAR
        assert ctx_t == ContextType.POWER

    def test_coal_mapping(self) -> None:
        ind, asset_t, ctx_t = normalize_industry_and_asset_type(
            raw_type="Power Plant (Coal)", raw_category="Thermal/Power Industry"
        )
        assert ind == IndustryType.POWER
        assert asset_t == AssetType.POWER_PLANT_COAL
        assert ctx_t == ContextType.POWER

    def test_refinery_mapping(self) -> None:
        ind, asset_t, ctx_t = normalize_industry_and_asset_type(
            raw_type="Oil & Gas / Petrochemical Facility",
            raw_category="Petrochemical / Refinery",
        )
        assert ind == IndustryType.OIL_GAS
        assert asset_t == AssetType.PETROCHEMICAL_COMPLEX
        assert ctx_t == ContextType.OIL_GAS

    def test_steel_mapping(self) -> None:
        ind, asset_t, ctx_t = normalize_industry_and_asset_type(
            raw_type="Integrated Steel Plant (Blast Furnace)",
            raw_category="Metallurgy",
        )
        assert ind == IndustryType.METALLURGY
        assert asset_t == AssetType.STEEL_PLANT
        assert ctx_t == ContextType.INDUSTRIAL


class TestOperationalStatusNormalization:
    """Test operational status string normalization."""

    def test_status_mapping(self) -> None:
        assert normalize_operational_status("operating") == OperationalStatus.OPERATING
        assert (
            normalize_operational_status("Operating pre-retirement")
            == OperationalStatus.OPERATING
        )
        assert (
            normalize_operational_status("construction")
            == OperationalStatus.CONSTRUCTION
        )
        assert normalize_operational_status("announced") == OperationalStatus.ANNOUNCED
        assert normalize_operational_status("retired") == OperationalStatus.RETIRED
        assert (
            normalize_operational_status("cancelled - inferred 4 y")
            == OperationalStatus.CANCELLED
        )
        assert normalize_operational_status("mothballed") == OperationalStatus.SHELVED
        assert normalize_operational_status(None) == OperationalStatus.OPERATING


class TestStateNormalization:
    """Test Indian State/UT name normalization."""

    def test_state_variants(self) -> None:
        assert normalize_state_name("Orissa") == "Odisha"
        assert normalize_state_name("Pondicherry") == "Puducherry"
        assert normalize_state_name("Gujarat") == "Gujarat"
        assert normalize_state_name("NCT of Delhi") == "Delhi"
        assert normalize_state_name(None) is None


class TestDeterministicIdGeneration:
    """Test deterministic canonical identifier generation."""

    def test_with_raw_provider_id(self) -> None:
        id1 = compute_canonical_asset_id(
            "wri", "WRI1020239", "ACME Solar", 28.1839, 73.2407
        )
        assert id1 == "ind_asset_wri_WRI1020239"

    def test_without_raw_id_hash_determinism(self) -> None:
        id1 = compute_canonical_asset_id(
            "master", None, "Jamnagar Refinery", 22.4502, 70.0512
        )
        id2 = compute_canonical_asset_id(
            "master", None, "Jamnagar Refinery", 22.4502, 70.0512
        )
        assert id1 == id2
        assert id1.startswith("ind_asset_master_")

    def test_distinct_facilities_produce_distinct_ids(self) -> None:
        id1 = compute_canonical_asset_id("master", None, "Facility A", 22.4502, 70.0512)
        id2 = compute_canonical_asset_id("master", None, "Facility B", 22.4502, 70.0512)
        assert id1 != id2


class TestDuplicateDetectionAndLinking:
    """Test deterministic duplicate detection and cross-source linking."""

    def test_haversine_distance_zero(self) -> None:
        d = haversine_distance_meters(22.4502, 70.0512, 22.4502, 70.0512)
        assert d == pytest.approx(0.0)

    def test_haversine_distance_known_points(self) -> None:
        # Distance between Mumbai (18.9220, 72.8347) and Pune (18.5204, 73.8567)
        # is approximately ~120 km.
        d = haversine_distance_meters(18.9220, 72.8347, 18.5204, 73.8567)
        assert 115000 < d < 125000

    def test_co_located_duplicate_candidates(self) -> None:
        a1 = IndustrialAsset(
            id="ind_asset_wri_WRI1020001",
            name="Anta Gas Thermal Power Station",
            asset_type=AssetType.POWER_PLANT_GAS,
            industry=IndustryType.POWER,
            context_type=ContextType.POWER,
            latitude=25.1797,
            longitude=76.3188,
            source="WRI Power Database",
            capacity=419.33,
            capacity_unit="MW",
        )
        a2 = IndustrialAsset(
            id="ind_asset_gem_G1000001000",
            name="Anta power plant",
            asset_type=AssetType.POWER_PLANT_GAS,
            industry=IndustryType.POWER,
            context_type=ContextType.POWER,
            latitude=25.1797,
            longitude=76.3188,
            source="GEM Oil & Gas Tracker",
            capacity=419.3,
            capacity_unit="MW",
        )
        a3 = IndustrialAsset(
            id="ind_asset_wri_WRI1029999",
            name="Unrelated Distant Solar Plant",
            asset_type=AssetType.POWER_PLANT_SOLAR,
            industry=IndustryType.POWER,
            context_type=ContextType.POWER,
            latitude=28.1839,
            longitude=73.2407,
            source="WRI Power Database",
            capacity=10.0,
            capacity_unit="MW",
        )

        candidates = find_duplicate_candidates([a1, a2, a3], max_distance_meters=1000.0)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.primary_asset_id == a2.id or c.primary_asset_id == a1.id
        assert c.distance_meters <= 1.0
        assert c.confidence >= 0.70

        # Test linking
        updated = link_duplicate_records([a1, a2, a3], candidates, link_threshold=0.70)
        assert len(updated) == 3
        # Check that a1 and a2 link to each other
        u_map = {u.id: u for u in updated}
        assert a2.id in u_map[a1.id].linked_source_ids
        assert a1.id in u_map[a2.id].linked_source_ids
        # Unrelated asset is untouched
        assert len(u_map[a3.id].linked_source_ids) == 0


class TestGeoJsonSerialization:
    """Test RFC 7946 GeoJSON export serialization."""

    def test_single_asset_geojson_feature(self) -> None:
        asset = IndustrialAsset(
            id="ind_asset_wri_WRI1020239",
            name="ACME Solar Tower",
            asset_type=AssetType.POWER_PLANT_SOLAR,
            industry=IndustryType.POWER,
            context_type=ContextType.POWER,
            latitude=28.1839,
            longitude=73.2407,
            source="WRI Power Database",
            source_id="WRI1020239",
            state="Rajasthan",
            capacity=2.5,
            capacity_unit="MW",
            primary_fuel="Solar",
            commissioning_year=2011,
            operator="ACME Solar",
            owner="Solar Paces",
            metadata={"source_url": "http://example.com"},
        )
        feat = asset.to_geojson_feature(precision=6)
        assert feat["type"] == "Feature"
        assert feat["id"] == "ind_asset_wri_WRI1020239"
        assert feat["geometry"]["type"] == "Point"
        # GeoJSON is [lon, lat]
        assert feat["geometry"]["coordinates"] == [73.2407, 28.1839]
        props = feat["properties"]
        assert props["name"] == "ACME Solar Tower"
        assert props["asset_type"] == "power_plant_solar"
        assert props["industry"] == "power"
        assert props["state"] == "Rajasthan"
        assert props["capacity"] == 2.5
        assert props["primary_fuel"] == "Solar"

    def test_collection_geojson_feature_collection(self) -> None:
        asset1 = IndustrialAsset(
            id="asset_1",
            name="Facility 1",
            asset_type=AssetType.POWER_PLANT_SOLAR,
            industry=IndustryType.POWER,
            context_type=ContextType.POWER,
            latitude=20.0,
            longitude=75.0,
            source="Test Source",
        )
        asset2 = IndustrialAsset(
            id="asset_2",
            name="Facility 2",
            asset_type=AssetType.REFINERY,
            industry=IndustryType.OIL_GAS,
            context_type=ContextType.OIL_GAS,
            latitude=25.0,
            longitude=80.0,
            source="Test Source",
        )
        collection = IndustrialAssetCollection(
            assets=[asset1, asset2],
            total_count=2,
            map_eligible_count=2,
        )
        fc = collection.to_geojson_feature_collection()
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 2
        # Bbox is [min_lon, min_lat, max_lon, max_lat]
        assert fc["bbox"] == [75.0, 20.0, 80.0, 25.0]


class TestRealDatasetIngestion:
    """Integration test loading actual datasets in data2/industrial_infra/."""

    def test_load_primary_master_facilities(self) -> None:
        """Loader successfully loads and enriches all 1,704 primary facilities."""
        loader = IndustrialDataLoader()
        collection = loader.load_primary_master_facilities(
            enrich=True, detect_duplicates=True
        )

        assert collection.total_count == 1704
        assert collection.map_eligible_count == 1704
        assert len(collection.assets) == 1704

        # Verify sources
        assert collection.sources_summary["WRI Power Database"] == 1589
        assert collection.sources_summary["GEM Oil & Gas Tracker"] == 115

        # Verify enrichment
        wri_with_source_id = sum(
            1
            for a in collection.assets
            if a.source == "WRI Power Database" and a.source_id is not None
        )
        assert (
            wri_with_source_id == 1589
        )  # 100% of WRI facilities enriched with gppd_idnr

        gem_with_source_id = sum(
            1
            for a in collection.assets
            if a.source == "GEM Oil & Gas Tracker" and a.source_id is not None
        )
        assert gem_with_source_id == 115  # 100% of GEM facilities enriched with GEM IDs

        # Verify state attribution rate
        with_state = sum(1 for a in collection.assets if a.state is not None)
        assert (
            with_state > 1650
        )  # Over 97% of facilities have canonical Indian state assigned

        # Verify duplicate detection
        assert collection.duplicate_candidates_count > 0

    def test_load_expansion_steel_facilities(self) -> None:
        """Loader successfully parses GEM steel tracker facilities."""
        loader = IndustrialDataLoader()
        steel_assets = loader.load_expansion_steel_facilities()
        assert len(steel_assets) == 113
        for a in steel_assets:
            assert a.industry == IndustryType.METALLURGY
            assert a.asset_type == AssetType.STEEL_PLANT
            assert a.is_map_eligible is True
            assert -90.0 <= a.latitude <= 90.0
            assert -180.0 <= a.longitude <= 180.0
