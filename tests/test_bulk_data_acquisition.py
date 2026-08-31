"""Comprehensive Test Suite for DATA-001: Bulk Real-World Data Acquisition.

Validates:
1. Multi-region study area resolution and registry lookups.
2. Contiguous temporal chunking with exact date boundaries.
3. Multi-sensor product selection (VIIRS + MODIS).
4. Raw data capture, SHA-256 cryptographic hashing, and manifest generation.
5. Raw CSV validation and malformed row handling.
6. Deduplication and cross-sensor observation preservation.
7. Incremental multi-file merge determinism.
8. Dry-run planning mode.
9. Zero-secret safety across manifests, dictionaries, and error messages.
10. Full compatibility with FirmsDataActivationService (ML-010).
11. Integration with RealEventConstructionService (ML-011).
12. Training gate re-evaluation on observational data.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from packages.config.scientific import ScientificConfig
from packages.data.firms.activation import FirmsDataActivationService, _audit_no_secrets
from packages.data.firms.bulk import (
    CANONICAL_STUDY_AREAS,
    STUDY_AREA_REGISTRY,
    AcquisitionChunkPlan,
    BulkAcquisitionSummary,
    BulkDataAcquisitionService,
)
from packages.data.firms.capture import compute_content_hash
from packages.data.firms.schemas import FirmsProduct
from packages.context.pipeline import RealContextLabelingService
from packages.events.pipeline import RealEventConstructionService
from packages.feasibility.candidates import (
    ANGUL_TALCHER,
    JAMNAGAR_KUTCH,
    PUNJAB_AGRICULTURAL,
    SINGRAULI_SONBHADRA,
)
from packages.feasibility.models import StudyArea
from services.ml.labels.dataset import SupervisedDatasetBuilder
from services.ml.training.gate import RealTrainingGateEvaluator


@pytest.fixture
def calibrated_config() -> ScientificConfig:
    return ScientificConfig(
        version="v1.0-test",
        name="test_profile",
        description="Calibrated test profile",
        spatial_cluster_radius_meters=1000.0,
        temporal_window_hours=2.0,
        persistence_threshold_days=10.0,
        persistence_min_observations=3,
        attribution_radius_meters=1500.0,
        attribution_confidence_threshold=0.7,
        minimum_event_confidence=0.5,
        abstention_confidence_threshold=0.4,
    )


@pytest.fixture
def sample_viirs_csv_bytes() -> bytes:
    csv_text = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
        "22.4501,70.0502,345.2,0.38,0.37,2026-08-01,0830,N,VIIRS,nominal,2.0NRT,295.4,18.5,D\n"
        "22.4505,70.0509,350.8,0.38,0.37,2026-08-01,0830,N,VIIRS,nominal,2.0NRT,296.1,24.2,D\n"
        "22.4510,70.0515,338.4,0.39,0.38,2026-08-02,2015,N,VIIRS,nominal,2.0NRT,290.0,12.0,N\n"
    )
    return csv_text.encode("utf-8")


@pytest.fixture
def sample_modis_csv_bytes() -> bytes:
    csv_text = (
        "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight\n"
        "22.4500,70.0500,320.5,1.0,1.0,2026-08-01,0545,Terra,MODIS,85,6.1NRT,292.0,35.0,D\n"
        "22.4508,70.0506,325.0,1.0,1.0,2026-08-02,0630,Aqua,MODIS,90,6.1NRT,294.0,42.0,D\n"
    )
    return csv_text.encode("utf-8")


# =============================================================================
# 1. STUDY AREA RESOLUTION
# =============================================================================


def test_study_area_resolution() -> None:
    """Verify study areas resolve accurately from strings, lists, and 'all' keyword."""
    all_areas = BulkDataAcquisitionService.resolve_study_areas("all")
    assert len(all_areas) == 4
    assert JAMNAGAR_KUTCH in all_areas
    assert SINGRAULI_SONBHADRA in all_areas
    assert ANGUL_TALCHER in all_areas
    assert PUNJAB_AGRICULTURAL in all_areas

    single = BulkDataAcquisitionService.resolve_study_areas("singrauli")
    assert len(single) == 1
    assert single[0].area_id == "singrauli_sonbhadra"

    multi = BulkDataAcquisitionService.resolve_study_areas("jamnagar,punjab")
    assert len(multi) == 2
    assert multi[0].area_id == "jamnagar_kutch"
    assert multi[1].area_id == "punjab_agricultural"

    with pytest.raises(ValueError, match="Unknown study area"):
        BulkDataAcquisitionService.resolve_study_areas("unknown_desert_region")


# =============================================================================
# 2. TEMPORAL CHUNKING
# =============================================================================


def test_temporal_chunking() -> None:
    """Verify temporal chunking divides date ranges into contiguous <= 10-day chunks."""
    # 25-day range -> 5 chunks of 5 days
    chunks = BulkDataAcquisitionService.plan_temporal_chunks(
        study_area=JAMNAGAR_KUTCH,
        product=FirmsProduct.VIIRS_SNPP_NRT,
        start_date="2026-08-01",
        end_date="2026-08-25",
    )
    assert len(chunks) == 5
    assert chunks[0].start_date == "2026-08-01"
    assert chunks[0].end_date == "2026-08-05"
    assert chunks[0].day_range == 5

    assert chunks[1].start_date == "2026-08-06"
    assert chunks[1].end_date == "2026-08-10"
    assert chunks[1].day_range == 5

    assert chunks[4].start_date == "2026-08-21"
    assert chunks[4].end_date == "2026-08-25"
    assert chunks[4].day_range == 5

    # Invalid dates
    with pytest.raises(ValueError, match="cannot be after end_date"):
        BulkDataAcquisitionService.plan_temporal_chunks(
            study_area=JAMNAGAR_KUTCH,
            product=FirmsProduct.VIIRS_SNPP_NRT,
            start_date="2026-08-25",
            end_date="2026-08-01",
        )


# =============================================================================
# 3. MULTI-SENSOR PRODUCT SELECTION
# =============================================================================


def test_multi_sensor_product_planning() -> None:
    """Verify chunk generation plans both VIIRS and MODIS products."""
    service = BulkDataAcquisitionService()
    summary = service.acquire_bulk_dataset(
        study_areas=["jamnagar"],
        start_date="2026-08-01",
        end_date="2026-08-10",
        products=[FirmsProduct.VIIRS_SNPP_NRT, FirmsProduct.MODIS_NRT],
        dry_run=True,
    )
    # 10 days -> 2 chunks of 5 days * 2 products = 4 chunks
    assert summary.total_chunks_planned == 4
    assert "VIIRS_SNPP_NRT" in summary.products
    assert "MODIS_NRT" in summary.products


# =============================================================================
# 4. DRY RUN PLANNING
# =============================================================================


def test_dry_run_planning() -> None:
    """Verify dry run outputs full plan without writing files or invoking network."""
    service = BulkDataAcquisitionService()
    summary = service.acquire_bulk_dataset(
        study_areas="all",
        start_date="2026-08-01",
        end_date="2026-08-20",  # 20 days -> 4 chunks per region * 3 products * 4 regions = 48 chunks
        products=[
            FirmsProduct.VIIRS_SNPP_NRT,
            FirmsProduct.VIIRS_NOAA20_NRT,
            FirmsProduct.MODIS_NRT,
        ],
        dry_run=True,
    )
    assert summary.is_dry_run is True
    assert summary.total_chunks_planned == 48
    assert len(summary.raw_files) == 0
    assert len(summary.manifest_paths) == 0


# =============================================================================
# 5. RAW ACQUISITION & MANIFEST GENERATION
# =============================================================================


def test_acquisition_with_mock_provider(
    sample_viirs_csv_bytes: bytes,
    tmp_path: Path,
) -> None:
    """Verify raw capture writes files, computes SHA-256, and generates clean manifests."""
    service = BulkDataAcquisitionService(base_output_dir=tmp_path / "raw")

    def mock_provider(plan: AcquisitionChunkPlan) -> bytes:
        return sample_viirs_csv_bytes

    summary = service.acquire_bulk_dataset(
        study_areas=["jamnagar"],
        start_date="2026-08-01",
        end_date="2026-08-10",
        products=[FirmsProduct.VIIRS_SNPP_NRT],
        mock_raw_provider=mock_provider,
    )

    assert summary.is_dry_run is False
    assert summary.successful_chunks == 2
    assert summary.total_raw_rows == 6
    assert len(summary.raw_files) == 2
    assert len(summary.manifest_paths) == 2

    # Verify written raw file
    raw_path = Path(summary.raw_files[0])
    assert raw_path.exists()
    assert compute_content_hash(raw_path.read_bytes()) == compute_content_hash(
        sample_viirs_csv_bytes
    )

    # Verify manifest JSON
    manifest_path = Path(summary.manifest_paths[0])
    assert manifest_path.exists()
    manifest_data = json.loads(manifest_path.read_text())
    assert manifest_data["study_area_id"] == "jamnagar_kutch"
    assert manifest_data["raw_row_count"] == 3
    assert manifest_data["raw_file_sha256"] == compute_content_hash(
        sample_viirs_csv_bytes
    )

    # Verify zero secrets
    _audit_no_secrets(manifest_data)


# =============================================================================
# 6. DEDUPLICATION & CROSS-SENSOR PRESERVATION
# =============================================================================


def test_merge_and_deduplication(
    sample_viirs_csv_bytes: bytes,
    sample_modis_csv_bytes: bytes,
    tmp_path: Path,
) -> None:
    """Verify merge deduplicates duplicate lines while preserving cross-sensor observations."""
    p_viirs = tmp_path / "viirs.csv"
    p_modis = tmp_path / "modis.csv"
    p_dup = tmp_path / "viirs_dup.csv"

    p_viirs.write_bytes(sample_viirs_csv_bytes)
    p_modis.write_bytes(sample_modis_csv_bytes)
    p_dup.write_bytes(sample_viirs_csv_bytes)  # Exact duplicate file

    merged_csv = BulkDataAcquisitionService.merge_raw_csv_files(
        raw_csv_paths=[p_viirs, p_modis, p_dup]
    )

    lines = [ln.strip() for ln in merged_csv.splitlines() if ln.strip()]
    header = lines[0]
    data_rows = lines[1:]

    # 3 unique VIIRS rows + 2 unique MODIS rows = 5 unique observation rows
    assert len(data_rows) == 5
    assert "latitude" in header
    # Check both instruments are represented
    assert any("VIIRS" in r for r in data_rows)
    assert any("MODIS" in r for r in data_rows)


# =============================================================================
# 7. DETERMINISTIC MERGE REPRODUCIBILITY
# =============================================================================


def test_merge_determinism(
    sample_viirs_csv_bytes: bytes,
    sample_modis_csv_bytes: bytes,
    tmp_path: Path,
) -> None:
    """Verify repeated merge produces identical byte-for-byte content."""
    p_viirs = tmp_path / "viirs.csv"
    p_modis = tmp_path / "modis.csv"
    p_viirs.write_bytes(sample_viirs_csv_bytes)
    p_modis.write_bytes(sample_modis_csv_bytes)

    m1 = BulkDataAcquisitionService.merge_raw_csv_files([p_viirs, p_modis])
    m2 = BulkDataAcquisitionService.merge_raw_csv_files([p_modis, p_viirs])

    assert m1 == m2
    assert compute_content_hash(m1.encode()) == compute_content_hash(m2.encode())


# =============================================================================
# 8. ACTIVATION PIPELINE COMPATIBILITY (ML-010)
# =============================================================================


def test_activation_pipeline_compatibility(
    sample_viirs_csv_bytes: bytes,
    tmp_path: Path,
) -> None:
    """Verify acquired raw CSV activates cleanly through FirmsDataActivationService."""
    det_ds = FirmsDataActivationService.activate_from_csv(
        csv_input=sample_viirs_csv_bytes,
        study_area=JAMNAGAR_KUTCH,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
        source_product="VIIRS_SNPP_NRT",
        sensor="VIIRS",
    )

    assert det_ds.manifest.study_area_id == "jamnagar_kutch"
    assert det_ds.manifest.canonical_record_count == 3
    assert len(det_ds.detections) == 3
    assert det_ds.detections[0].instrument == "VIIRS"


# =============================================================================
# 9. EVENT CONSTRUCTION COMPATIBILITY (ML-011)
# =============================================================================


def test_event_construction_compatibility(
    sample_viirs_csv_bytes: bytes,
    calibrated_config: ScientificConfig,
) -> None:
    """Verify activated detection dataset feeds into RealEventConstructionService."""
    det_ds = FirmsDataActivationService.activate_from_csv(
        csv_input=sample_viirs_csv_bytes,
        study_area=JAMNAGAR_KUTCH,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
    )

    ev_ds = RealEventConstructionService.construct_events_and_sources(
        detection_dataset=det_ds,
        config=calibrated_config,
    )

    assert ev_ds.dataset_id == "ds_real_events_v1.0.0"
    assert len(ev_ds.events) > 0


# =============================================================================
# 10. SECRET NON-LEAKAGE IN SUMMARY
# =============================================================================


def test_secret_safety_in_summary() -> None:
    """Verify BulkAcquisitionSummary audits cleanly against sensitive key patterns."""
    summary = BulkAcquisitionSummary(
        is_dry_run=True,
        study_areas=["jamnagar_kutch"],
        products=["VIIRS_SNPP_NRT"],
        start_date="2026-08-01",
        end_date="2026-08-10",
        total_chunks_planned=1,
        successful_chunks=1,
        failed_chunks=0,
        total_raw_rows=10,
        total_accepted_observations=10,
        total_rejected_rows=0,
        total_duplicate_rows=0,
    )
    d = summary.to_dict()
    assert "is_dry_run" in d
    assert "FIRMS_MAP_KEY" not in str(d)


# =============================================================================
# 11. MULTI-REGION BULK INTEGRATION
# =============================================================================


def test_multi_region_bulk_integration(tmp_path: Path) -> None:
    """Verify multi-region acquisition executes cleanly across all 4 candidate areas."""
    service = BulkDataAcquisitionService(base_output_dir=tmp_path / "multi_region")

    def mock_provider(plan: AcquisitionChunkPlan) -> bytes:
        lat = plan.bounding_box.min_latitude + 0.1
        lon = plan.bounding_box.min_longitude + 0.1
        sensor = "MODIS" if "MODIS" in plan.product.value else "VIIRS"
        sat = "Terra" if sensor == "MODIS" else "N"
        csv_str = (
            "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
            f"{lat:.4f},{lon:.4f},335.0,0.4,0.4,{plan.start_date},0800,{sat},{sensor},nominal,2.0,290.0,15.0,D\n"
        )
        return csv_str.encode("utf-8")

    summary = service.acquire_bulk_dataset(
        study_areas="all",
        start_date="2026-08-01",
        end_date="2026-08-10",
        products=[FirmsProduct.VIIRS_SNPP_NRT, FirmsProduct.MODIS_NRT],
        mock_raw_provider=mock_provider,
    )

    # 4 study areas * 2 products * 2 chunks (5 days each) = 16 chunks
    assert summary.total_chunks_planned == 16
    assert summary.successful_chunks == 16
    assert summary.total_raw_rows == 16
    assert len(summary.raw_files) == 16
    assert len(summary.manifest_paths) == 16
    assert len(summary.quality_breakdown["regional_observations"]) == 4
    assert len(summary.quality_breakdown["sensor_observations"]) == 2


# =============================================================================
# 12. RAW VALIDATION & MALFORMED ROW HANDLING
# =============================================================================


def test_raw_csv_validation_and_malformed_row_rejection() -> None:
    """Verify malformed CSV rows (invalid latitude, FRP, missing headers) are properly caught."""
    malformed_csv = (
        "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight\n"
        "999.0,70.0502,345.2,0.38,0.37,2026-08-01,0830,N,VIIRS,nominal,2.0,295.4,18.5,D\n"  # Invalid lat
        "22.4501,70.0502,345.2,0.38,0.37,2026-08-01,0830,N,VIIRS,nominal,2.0,295.4,-5.0,D\n"  # Invalid negative FRP
        "22.4501,70.0502,345.2,0.38,0.37,2026-08-01,0830,N,VIIRS,nominal,2.0,295.4,18.5,D\n"  # Valid
    )

    det_ds = FirmsDataActivationService.activate_from_csv(
        csv_input=malformed_csv.encode("utf-8"),
        study_area=JAMNAGAR_KUTCH,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
    )

    assert det_ds.manifest.raw_record_count == 3
    assert det_ds.manifest.canonical_record_count == 1
    assert det_ds.manifest.invalid_record_count >= 1


# =============================================================================
# 13. TRAINING GATE AUDIT ON OBSERVATIONAL DATA
# =============================================================================


def test_training_gate_audit_on_observational_data(
    sample_viirs_csv_bytes: bytes,
    calibrated_config: ScientificConfig,
) -> None:
    """Verify observational dataset correctly evaluates through the scientific training gate."""
    det_ds = FirmsDataActivationService.activate_from_csv(
        csv_input=sample_viirs_csv_bytes,
        study_area=JAMNAGAR_KUTCH,
        requested_start_date="2026-08-01",
        requested_end_date="2026-08-10",
    )

    ev_ds = RealEventConstructionService.construct_events_and_sources(
        detection_dataset=det_ds,
        config=calibrated_config,
    )

    ctx_path = Path("fixtures/context/context_sample_jamnagar.json")
    features, hashes = RealContextLabelingService.load_context_features_from_fixture(
        ctx_path
    )
    enriched_ds = RealContextLabelingService.enrich_and_adjudicate_dataset(
        event_dataset=ev_ds,
        candidate_features=features,
        snapshot_hashes=hashes,
        config=calibrated_config,
    )

    builder = SupervisedDatasetBuilder()
    supervised_ds = builder.build_from_real_enriched_dataset(
        enriched_dataset=enriched_ds,
        detection_dataset=det_ds,
        target_ids=["target_industrial_segregation"],
    )

    gate_eval = RealTrainingGateEvaluator.evaluate(
        dataset=supervised_ds,
        target_id="target_industrial_segregation",
    )

    assert gate_eval.gate_status == "NOT_PASSED"
    assert gate_eval.is_production_ready is False
    assert len(gate_eval.rejection_reasons) > 0
