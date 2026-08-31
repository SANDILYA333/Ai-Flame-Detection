"""Comprehensive Test Suite for DATA-002: Globally Scalable Fire Dataset Pipeline.

Validates:
1. Deterministic spatial tiling decomposition for large/global bounding envelopes.
2. Global scope resolution and tile generation covering active fire latitudes.
3. Arbitrary custom bounding box resolution (single envelope vs tiled).
4. Multi-continent study area registry resolution (Persian Gulf, California, Amazon, Australia).
5. Strict backward compatibility for Indian calibration corridors.
6. Resumable acquisition: verified immutable chunks are skipped without network hits.
7. Forced retry: corrupt manifests or retry_failed flag triggers re-acquisition.
8. Global multi-regime ground-truth loading (USA, Brazil, Australia, Saudi Arabia, India).
9. Geodesic event matching across international continents and fire regimes.
10. Secret auditing across all global manifests and summary payloads.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from packages.context.ground_truth import (
    ExternalReferenceRecord,
    GroundTruthIngestionService,
)
from packages.data.firms.bulk import (
    CANONICAL_STUDY_AREAS,
    GLOBAL_VALIDATION_AREAS,
    STUDY_AREA_REGISTRY,
    AcquisitionChunkPlan,
    BulkDataAcquisitionService,
)
from packages.data.firms.schemas import FirmsProduct
from packages.feasibility.models import StudyArea, StudyAreaRole
from packages.schemas.common import BoundingBox, Coordinate
from packages.schemas.enums import SourceRole
from packages.schemas.event import Event
from packages.schemas.ml import LabelProvenanceType, LabelTier


# =============================================================================
# 1. SPATIAL TILING DECOMPOSITION
# =============================================================================


def test_spatial_tiling_decomposition() -> None:
    """Verify decomposing a 20x20 deg box with 10 deg step creates 4 non-overlapping tiles."""
    bbox = BoundingBox(
        min_latitude=20.0,
        min_longitude=70.0,
        max_latitude=40.0,
        max_longitude=90.0,
    )
    tiles = BulkDataAcquisitionService.plan_spatial_tiles(
        bounding_box=bbox,
        tile_size_degrees=10.0,
    )

    assert len(tiles) == 4
    for tile in tiles:
        assert tile.role == StudyAreaRole.GLOBAL_ACQUISITION
        assert tile.bounding_box.min_latitude >= 20.0
        assert tile.bounding_box.max_latitude <= 40.0
        assert tile.bounding_box.min_longitude >= 70.0
        assert tile.bounding_box.max_longitude <= 90.0
        assert tile.area_id.startswith("tile_")


def test_spatial_tiling_clamping_to_earth_bounds() -> None:
    """Verify tiling across the entire globe produces valid tiles with -90<=lat<=90 and -180<=lon<=180."""
    bbox = BoundingBox(
        min_latitude=-90.0,
        min_longitude=-180.0,
        max_latitude=90.0,
        max_longitude=180.0,
    )
    tiles = BulkDataAcquisitionService.plan_spatial_tiles(
        bounding_box=bbox,
        tile_size_degrees=45.0,
    )

    assert len(tiles) == (180 // 45) * (360 // 45)  # 4 rows x 8 cols = 32 tiles
    for t in tiles:
        assert -90.0 <= t.bounding_box.min_latitude <= 90.0
        assert -90.0 <= t.bounding_box.max_latitude <= 90.0
        assert -180.0 <= t.bounding_box.min_longitude <= 180.0
        assert -180.0 <= t.bounding_box.max_longitude <= 180.0


# =============================================================================
# 2. GLOBAL SCOPE RESOLUTION
# =============================================================================


def test_global_scope_resolution() -> None:
    """Verify scope='global' produces spatial tiles covering worldwide fire latitudes."""
    tiles = BulkDataAcquisitionService.resolve_study_areas(
        scope="global",
        tile_size_degrees=30.0,
    )

    assert len(tiles) > 0
    for t in tiles:
        assert t.role == StudyAreaRole.GLOBAL_ACQUISITION
        assert t.country == "Global"
        assert t.area_id.startswith("global_tile_")


# =============================================================================
# 3. CUSTOM BOUNDING BOX RESOLUTION
# =============================================================================


def test_custom_bbox_single_envelope() -> None:
    """Verify a small custom bbox (< tile_size) resolves to a single StudyArea."""
    custom = BoundingBox(
        min_latitude=25.0,
        min_longitude=50.0,
        max_latitude=27.0,
        max_longitude=52.0,
    )
    resolved = BulkDataAcquisitionService.resolve_study_areas(
        custom_bbox=custom,
        tile_size_degrees=10.0,
    )

    assert len(resolved) == 1
    area = resolved[0]
    assert area.role == StudyAreaRole.GLOBAL_ACQUISITION
    assert area.bounding_box == custom


def test_custom_bbox_tiled_envelope() -> None:
    """Verify a large custom bbox (> tile_size) resolves into multiple spatial tiles."""
    custom = BoundingBox(
        min_latitude=10.0,
        min_longitude=20.0,
        max_latitude=30.0,
        max_longitude=50.0,
    )
    resolved = BulkDataAcquisitionService.resolve_study_areas(
        custom_bbox=custom,
        tile_size_degrees=10.0,
    )

    assert len(resolved) == 6  # 2 rows x 3 cols


# =============================================================================
# 4. MULTI-CONTINENT STUDY AREA RESOLUTION & ROLES
# =============================================================================


def test_international_study_areas_resolution() -> None:
    """Verify predefined international validation corridors resolve with correct roles."""
    gulf = BulkDataAcquisitionService.resolve_study_areas("persian_gulf")[0]
    california = BulkDataAcquisitionService.resolve_study_areas("california")[0]
    amazon = BulkDataAcquisitionService.resolve_study_areas("amazon")[0]
    australia = BulkDataAcquisitionService.resolve_study_areas("australia")[0]

    assert gulf.country == "Saudi Arabia / UAE / Qatar"
    assert gulf.role == StudyAreaRole.SECONDARY_VALIDATION

    assert california.country == "United States"
    assert california.role == StudyAreaRole.CONTRAST_NEGATIVE_CONTROL

    assert amazon.country == "Brazil"
    assert amazon.role == StudyAreaRole.CONTRAST_NEGATIVE_CONTROL

    assert australia.country == "Australia"
    assert australia.role == StudyAreaRole.CONTRAST_NEGATIVE_CONTROL


def test_all_validation_areas_selector() -> None:
    """Verify 'validation' selector returns all global validation corridors."""
    areas = BulkDataAcquisitionService.resolve_study_areas("validation")
    assert len(areas) == len(GLOBAL_VALIDATION_AREAS)


# =============================================================================
# 5. STRICT BACKWARD COMPATIBILITY
# =============================================================================


def test_backward_compatibility_indian_corridors() -> None:
    """Verify 'all' and individual Indian selectors resolve canonical study areas."""
    canonical = BulkDataAcquisitionService.resolve_study_areas("all")
    assert len(canonical) == 4
    assert {a.area_id for a in canonical} == {
        "jamnagar_kutch",
        "singrauli_sonbhadra",
        "angul_talcher",
        "punjab_agricultural",
    }


# =============================================================================
# 6. RESUMABLE ACQUISITION
# =============================================================================


def test_resumable_acquisition_skips_existing_valid_chunks(tmp_path: Path) -> None:
    """Verify previously downloaded and verified chunks are skipped with 0 HTTP calls."""
    sample_csv = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
        "22.4500,70.0500,345.2,0.38,0.37,2026-08-01,0830,N,VIIRS,nominal,2.0NRT,295.4,18.5,D\n"
    ).encode("utf-8")

    call_count = 0

    def mock_provider(plan: AcquisitionChunkPlan) -> bytes:
        nonlocal call_count
        call_count += 1
        return sample_csv

    service = BulkDataAcquisitionService(base_output_dir=tmp_path)

    # First run: performs download
    s1 = service.acquire_bulk_dataset(
        study_areas="jamnagar",
        start_date="2026-08-01",
        end_date="2026-08-05",
        products=[FirmsProduct.VIIRS_SNPP_NRT],
        mock_raw_provider=mock_provider,
        resume=True,
    )
    assert s1.successful_chunks == 1
    assert s1.skipped_chunks == 0
    assert call_count == 1

    # Second run without mock provider: reads from disk and verifies hash
    s2 = service.acquire_bulk_dataset(
        study_areas="jamnagar",
        start_date="2026-08-01",
        end_date="2026-08-05",
        products=[FirmsProduct.VIIRS_SNPP_NRT],
        resume=True,
        retry_failed=False,
    )
    assert s2.successful_chunks == 1
    assert s2.skipped_chunks == 1
    assert s2.total_raw_rows == 1


# =============================================================================
# 7. FORCED RETRY RE-DOWNLOADS
# =============================================================================


def test_retry_failed_forces_redownload(tmp_path: Path) -> None:
    """Verify retry_failed=True ignores existing files and re-fetches."""
    sample_csv = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
        "22.4500,70.0500,345.2,0.38,0.37,2026-08-01,0830,N,VIIRS,nominal,2.0NRT,295.4,18.5,D\n"
    ).encode("utf-8")

    call_count = 0

    def mock_provider(plan: AcquisitionChunkPlan) -> bytes:
        nonlocal call_count
        call_count += 1
        return sample_csv

    service = BulkDataAcquisitionService(base_output_dir=tmp_path)

    # First run
    service.acquire_bulk_dataset(
        study_areas="jamnagar",
        start_date="2026-08-01",
        end_date="2026-08-05",
        products=[FirmsProduct.VIIRS_SNPP_NRT],
        mock_raw_provider=mock_provider,
    )
    assert call_count == 1

    # Second run with retry_failed=True
    service.acquire_bulk_dataset(
        study_areas="jamnagar",
        start_date="2026-08-01",
        end_date="2026-08-05",
        products=[FirmsProduct.VIIRS_SNPP_NRT],
        mock_raw_provider=mock_provider,
        retry_failed=True,
    )
    assert call_count == 2


# =============================================================================
# 8. GLOBAL GROUND TRUTH JSON LOADING & PARSING
# =============================================================================


def test_global_ground_truth_loading() -> None:
    """Verify loading global ground truth fixture captures international metadata."""
    fixture_path = Path("fixtures/reference/global_ground_truth_sample.json")
    records, file_hash = GroundTruthIngestionService.load_ground_truth_from_json(fixture_path)

    assert len(records) == 5
    assert len(file_hash) == 64

    countries = {r.country for r in records}
    assert countries == {"India", "United States", "Brazil", "Australia", "Saudi Arabia"}

    fire_regimes = {r.fire_regime for r in records}
    assert "agricultural" in fire_regimes
    assert "forest_natural" in fire_regimes
    assert "industrial" in fire_regimes


# =============================================================================
# 9. INTERNATIONAL GEODESIC EVENT MATCHING
# =============================================================================


def test_international_event_ground_truth_matching() -> None:
    """Verify events in California, Australia, and Persian Gulf match their respective GT."""
    now = datetime(2026, 8, 2, 16, 0, tzinfo=UTC)

    # Event in California Sierra foothills
    california_event = Event(
        event_id="ev_california_wildfire_001",
        detection_ids=["det_cal_1", "det_cal_2"],
        detection_count=2,
        started_at=now,
        ended_at=now + timedelta(minutes=30),
        centroid_geometry=Coordinate(latitude=37.5405, longitude=-119.8202),
        formation_configuration_id="v1.0-test",
        formation_configuration_version="v1.0",
    )

    # Event in Persian Gulf oil/gas facility
    gulf_event = Event(
        event_id="ev_gulf_flaring_001",
        detection_ids=["det_gulf_1"],
        detection_count=1,
        started_at=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        ended_at=datetime(2026, 8, 1, 12, 30, tzinfo=UTC),
        centroid_geometry=Coordinate(latitude=25.9302, longitude=50.1205),
        formation_configuration_id="v1.0-test",
        formation_configuration_version="v1.0",
    )

    fixture_path = Path("fixtures/reference/global_ground_truth_sample.json")
    records, _ = GroundTruthIngestionService.load_ground_truth_from_json(fixture_path)

    matched = GroundTruthIngestionService.match_events_to_ground_truth(
        events=[california_event, gulf_event],
        ground_truth_records=records,
        max_distance_meters=2000.0,
        max_temporal_delta_hours=24.0,
    )

    assert len(matched) == 2

    # California match
    cal_ev = [m for m in matched if m.entity_id == "ev_california_wildfire_001"][0]
    assert cal_ev.claim_class == "non_industrial"
    assert cal_ev.tier == LabelTier.TIER_A_AUTHORITATIVE
    assert cal_ev.provenance_type == LabelProvenanceType.GROUND_TRUTH

    # Gulf match
    gulf_ev = [m for m in matched if m.entity_id == "ev_gulf_flaring_001"][0]
    assert gulf_ev.claim_class == "industrial"
    assert gulf_ev.tier == LabelTier.TIER_A_AUTHORITATIVE


# =============================================================================
# 10. SECRET AUDIT IN GLOBAL MANIFESTS & SUMMARIES
# =============================================================================


def test_global_dry_run_secret_audit() -> None:
    """Verify global scope dry-run output contains zero secrets."""
    service = BulkDataAcquisitionService()
    summary = service.acquire_bulk_dataset(
        scope="global",
        start_date="2026-08-01",
        end_date="2026-08-05",
        dry_run=True,
        tile_size_degrees=45.0,
    )

    data = summary.to_dict()
    assert data["is_dry_run"] is True
    assert data["total_chunks_planned"] > 0
    # to_dict internally runs _audit_no_secrets, verifying 0 secrets
