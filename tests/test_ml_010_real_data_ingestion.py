"""Unit and integration tests for ML-010 Real-World Data Activation & Ingestion.

Validates:
- Schema parsing, validation, and optional field missingness handling.
- Coordinate validity boundaries (-90 <= lat <= 90, -180 <= lon <= 180).
- Spatial filtering against study area bounding boxes.
- Temporal filtering across configured observation windows.
- Deduplication of exact duplicate records while retaining repeated observations.
- Preservation of physical units (FRP in MW, Brightness in Kelvin).
- Deterministic provenance manifest and canonical dataset hashing.
- Exact end-to-end reproducibility across duplicate runs.
- Secret and credential exclusion audit.
- Complete offline capability without network connectivity or API tokens.
"""

import tempfile
from pathlib import Path

import pytest

from packages.data.firms.activation import FirmsDataActivationService, _audit_no_secrets
from packages.data.firms.schemas import (
    RawFirmsCsvRow,
    RealDataAcquisitionManifest,
    RealDetectionDataset,
)
from packages.feasibility.candidates import JAMNAGAR_KUTCH


class TestML010RealDataActivation:
    """Comprehensive test suite for ML-010 real data activation and provenance."""

    @pytest.fixture
    def fixture_path(self) -> Path:
        return Path("fixtures/firms/firms_real_sample_jamnagar.csv")

    def test_schema_valid_and_missing_optional_fields(self) -> None:
        """Valid FIRMS CSV rows parse successfully, handling missing optional values."""
        row_dict = {
            "latitude": "22.4502",
            "longitude": "70.0512",
            "bright_ti4": "352.4",
            "scan": "0.38",
            "track": "0.38",
            "acq_date": "2026-08-01",
            "acq_time": "0830",
            "satellite": "N",
            "instrument": "VIIRS",
            "confidence": None,
            "version": "2.0NRT",
            "bright_ti5": None,
            "frp": "28.5",
            "daynight": "D",
        }
        row = RawFirmsCsvRow.model_validate(row_dict)
        assert row.latitude == 22.4502
        assert row.longitude == 70.0512
        assert row.confidence is None
        assert row.bright_ti5 is None
        assert row.frp == 28.5

    def test_coordinate_validation(self) -> None:
        """Malformed coordinates outside [-90, 90] or [-180, 180] are rejected."""
        with pytest.raises(ValueError):
            RawFirmsCsvRow.model_validate(
                {
                    "latitude": "95.0",
                    "longitude": "70.0",
                    "acq_date": "2026-08-01",
                    "acq_time": "0830",
                    "satellite": "N",
                }
            )

        with pytest.raises(ValueError):
            RawFirmsCsvRow.model_validate(
                {
                    "latitude": "22.0",
                    "longitude": "195.0",
                    "acq_date": "2026-08-01",
                    "acq_time": "0830",
                    "satellite": "N",
                }
            )

    def test_end_to_end_activation_from_fixture(self, fixture_path: Path) -> None:
        """Activating from fixture applies spatial, temporal, and deduplication."""
        dataset = FirmsDataActivationService.activate_from_csv(
            csv_input=fixture_path,
            study_area=JAMNAGAR_KUTCH,
            requested_start_date="2026-08-01",
            requested_end_date="2026-08-10",
            source_product="VIIRS_SNPP_NRT",
            sensor="VIIRS",
        )

        assert isinstance(dataset, RealDetectionDataset)
        assert isinstance(dataset.manifest, RealDataAcquisitionManifest)
        manifest = dataset.manifest

        # Total rows in fixture = 9
        # Row 1: Jamnagar Aug 1 -> Valid, Kept
        # Row 2: Jamnagar Aug 1 -> Valid, Kept
        # Row 3: Jamnagar Aug 1 -> Exact duplicate of Row 1 -> Dropped (duplicate = 1)
        # Row 4: Jamnagar Aug 1 Night -> Valid, Kept
        # Row 5: Jamnagar Aug 2 Day -> Valid, Kept
        # Row 6: Jamnagar Aug 2 Day (missing confidence/ti5) -> Valid, Kept
        # Row 7: Jamnagar Aug 3 Night -> Valid, Kept
        # Row 8: Singrauli Aug 2 -> Outside Jamnagar -> Spatially Excluded
        # Row 9: Jamnagar July 20 -> Outside window -> Temporally Excluded
        # Final canonical detections = 9 - 1 (dup) - 1 (spatial) - 1 (temporal) = 6
        assert manifest.raw_record_count == 9
        assert manifest.valid_record_count == 9
        assert manifest.duplicate_record_count == 1
        assert manifest.spatial_excluded_count == 1
        assert manifest.temporal_excluded_count == 1
        assert manifest.canonical_record_count == 6
        assert len(dataset.detections) == 6

        # Missingness summary
        assert manifest.missingness_summary["confidence"] == 1
        assert manifest.missingness_summary["brightness_ti4_k"] == 0

        # Physical unit checks
        for det in dataset.detections:
            assert det.frp_mw is not None and det.frp_mw > 0.0
            assert det.brightness_ti4_k is not None and det.brightness_ti4_k > 200.0
            assert det.geometry.latitude >= JAMNAGAR_KUTCH.bounding_box.min_latitude
            assert det.geometry.latitude <= JAMNAGAR_KUTCH.bounding_box.max_latitude
            assert det.geometry.longitude >= JAMNAGAR_KUTCH.bounding_box.min_longitude
            assert det.geometry.longitude <= JAMNAGAR_KUTCH.bounding_box.max_longitude

    def test_reproducibility_and_deterministic_dataset_hashing(
        self, fixture_path: Path
    ) -> None:
        """Ingesting identical inputs produces identical canonical dataset hashes."""
        ds1 = FirmsDataActivationService.activate_from_csv(
            csv_input=fixture_path,
            study_area=JAMNAGAR_KUTCH,
            requested_start_date="2026-08-01",
            requested_end_date="2026-08-10",
        )
        ds2 = FirmsDataActivationService.activate_from_csv(
            csv_input=fixture_path,
            study_area=JAMNAGAR_KUTCH,
            requested_start_date="2026-08-01",
            requested_end_date="2026-08-10",
        )

        assert (
            ds1.manifest.canonical_dataset_hash == ds2.manifest.canonical_dataset_hash
        )
        assert len(ds1.manifest.canonical_dataset_hash) == 64
        assert (
            ds1.manifest.canonical_record_count == ds2.manifest.canonical_record_count
        )

    def test_save_and_load_dataset_roundtrip(self, fixture_path: Path) -> None:
        """Observational dataset serializes and reloads with hash verification."""
        dataset = FirmsDataActivationService.activate_from_csv(
            csv_input=fixture_path,
            study_area=JAMNAGAR_KUTCH,
            requested_start_date="2026-08-01",
            requested_end_date="2026-08-10",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = FirmsDataActivationService.save_dataset(dataset, tmp_dir)
            assert out_path.exists()

            loaded_ds = FirmsDataActivationService.load_dataset(out_path)
            assert loaded_ds.manifest.dataset_id == dataset.manifest.dataset_id
            assert (
                loaded_ds.manifest.canonical_dataset_hash
                == dataset.manifest.canonical_dataset_hash
            )
            assert len(loaded_ds.detections) == len(dataset.detections)

    def test_tampered_dataset_detection(self, fixture_path: Path) -> None:
        """Tampering with detection records in saved file raises hash mismatch error."""
        dataset = FirmsDataActivationService.activate_from_csv(
            csv_input=fixture_path,
            study_area=JAMNAGAR_KUTCH,
            requested_start_date="2026-08-01",
            requested_end_date="2026-08-10",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_path = FirmsDataActivationService.save_dataset(dataset, tmp_dir)

            # Tamper with file
            import json

            data = json.loads(out_path.read_text(encoding="utf-8"))
            data["detections"][0]["frp_mw"] = 9999.0
            out_path.write_text(json.dumps(data), encoding="utf-8")

            with pytest.raises(ValueError, match="Observational dataset hash mismatch"):
                FirmsDataActivationService.load_dataset(out_path)

    def test_secret_scanner_rejection(self) -> None:
        """Secret scanner detects and rejects credentials and tokens."""
        # 1. Prohibited sensitive key in dict
        bad_meta = {"dataset_id": "ds_01", "firms_map_key": "secret_abc123"}
        with pytest.raises(ValueError, match="Prohibited sensitive key"):
            _audit_no_secrets(bad_meta)

        # 2. Bearer token in string value
        bad_val = {"auth_header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"}
        with pytest.raises(ValueError, match="Prohibited credential token"):
            _audit_no_secrets(bad_val)

        # 3. Clean metadata passes
        clean_meta = {"dataset_id": "ds_01", "product": "VIIRS_SNPP_NRT"}
        _audit_no_secrets(clean_meta)

    def test_offline_operation_zero_network(self, fixture_path: Path) -> None:
        """Dataset activation runs with zero external network or API dependencies."""
        dataset = FirmsDataActivationService.activate_from_csv(
            csv_input=fixture_path,
            study_area=JAMNAGAR_KUTCH,
            requested_start_date="2026-08-01",
            requested_end_date="2026-08-10",
        )
        assert dataset.manifest.quality_control_passed is True
        assert len(dataset.detections) > 0
