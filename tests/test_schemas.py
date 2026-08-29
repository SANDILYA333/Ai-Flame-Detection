"""Comprehensive unit and invariant tests for canonical domain schemas."""

import unittest
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from packages.schemas import (
    AttributionStrength,
    BoundingBox,
    ContextEvidence,
    ContextType,
    Coordinate,
    DayNight,
    Detection,
    Event,
    EvidenceAvailabilityState,
    EvidenceCategoryState,
    EvidenceCompleteness,
    IntelligenceResult,
    PersistenceState,
    PersistentSource,
    PhenomenonType,
    UncertaintyMetric,
)


class TestCoordinateAndBoundingBox(unittest.TestCase):
    """Tests for geographic coordinate and bounding box models."""

    def test_valid_coordinate(self) -> None:
        coord = Coordinate(latitude=21.5, longitude=85.2)
        self.assertEqual(coord.latitude, 21.5)
        self.assertEqual(coord.longitude, 85.2)

    def test_invalid_latitude(self) -> None:
        with self.assertRaises(ValidationError):
            Coordinate(latitude=95.0, longitude=85.2)
        with self.assertRaises(ValidationError):
            Coordinate(latitude=-91.0, longitude=85.2)

    def test_invalid_longitude(self) -> None:
        with self.assertRaises(ValidationError):
            Coordinate(latitude=21.5, longitude=185.0)
        with self.assertRaises(ValidationError):
            Coordinate(latitude=21.5, longitude=-185.0)

    def test_non_finite_coordinate(self) -> None:
        with self.assertRaises(ValidationError):
            Coordinate(latitude=float("nan"), longitude=85.2)
        with self.assertRaises(ValidationError):
            Coordinate(latitude=21.5, longitude=float("inf"))

    def test_valid_bounding_box(self) -> None:
        bbox = BoundingBox(
            min_latitude=20.0,
            min_longitude=80.0,
            max_latitude=22.0,
            max_longitude=82.0,
        )
        self.assertEqual(bbox.min_latitude, 20.0)
        self.assertEqual(bbox.max_latitude, 22.0)

    def test_invalid_bounding_box_inverted(self) -> None:
        with self.assertRaises(ValidationError):
            BoundingBox(
                min_latitude=25.0,
                min_longitude=80.0,
                max_latitude=20.0,
                max_longitude=82.0,
            )


class TestDetectionSchema(unittest.TestCase):
    """Tests for the canonical Detection domain model."""

    def _sample_detection_kwargs(self) -> dict[str, Any]:
        return {
            "detection_id": "det-12345",
            "source": "firms",
            "source_snapshot_id": "snap-20260829-001",
            "acquired_at": datetime(2026, 8, 29, 6, 30, tzinfo=UTC),
            "geometry": Coordinate(latitude=21.5, longitude=85.2),
            "satellite": "NOAA-20",
            "instrument": "VIIRS",
            "product_type": "nrt",
            "product_version": "v2.0NRT",
            "raw_hash": (
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            ),
            "frp_mw": 14.5,
            "brightness_ti4_k": 345.2,
            "brightness_ti5_k": 298.1,
            "confidence": "nominal",
            "scan_km": 0.375,
            "track_km": 0.375,
            "day_night": DayNight.DAY,
        }

    def test_valid_detection(self) -> None:
        kwargs = self._sample_detection_kwargs()
        detection = Detection(**kwargs)
        self.assertEqual(detection.detection_id, "det-12345")
        self.assertEqual(detection.satellite, "NOAA-20")
        self.assertEqual(detection.frp_mw, 14.5)
        self.assertEqual(detection.day_night, DayNight.DAY)

    def test_detection_naive_timestamp_rejection(self) -> None:
        kwargs = self._sample_detection_kwargs()
        kwargs["acquired_at"] = datetime(2026, 8, 29, 6, 30)  # Naive (no tzinfo)
        with self.assertRaises(ValidationError):
            Detection(**kwargs)

    def test_detection_empty_string_rejection(self) -> None:
        kwargs = self._sample_detection_kwargs()
        kwargs["detection_id"] = "   "  # Whitespace only
        with self.assertRaises(ValidationError):
            Detection(**kwargs)

    def test_detection_immutability(self) -> None:
        detection = Detection(**self._sample_detection_kwargs())
        with self.assertRaises(ValidationError):
            detection.satellite = "Terra"  # type: ignore[misc]

    def test_detection_forbid_extra_fields(self) -> None:
        kwargs = self._sample_detection_kwargs()
        kwargs["unexpected_vendor_field"] = "leaked_vendor_data"
        with self.assertRaises(ValidationError):
            Detection(**kwargs)


class TestEventSchema(unittest.TestCase):
    """Tests for the canonical Event domain model."""

    def _sample_event_kwargs(self) -> dict[str, Any]:
        return {
            "event_id": "evt-9876",
            "detection_ids": ["det-1", "det-2", "det-3"],
            "detection_count": 3,
            "started_at": datetime(2026, 8, 29, 6, 0, tzinfo=UTC),
            "ended_at": datetime(2026, 8, 29, 7, 0, tzinfo=UTC),
            "centroid_geometry": Coordinate(latitude=21.55, longitude=85.25),
            "formation_configuration_id": "cfg-spatial-temp-v1",
            "formation_configuration_version": "1.0.0",
            "duration_seconds": 3600.0,
            "mean_frp_mw": 22.4,
            "max_frp_mw": 45.1,
        }

    def test_valid_event(self) -> None:
        event = Event(**self._sample_event_kwargs())
        self.assertEqual(event.event_id, "evt-9876")
        self.assertEqual(event.detection_count, 3)
        self.assertEqual(len(event.detection_ids), 3)

    def test_event_count_mismatch(self) -> None:
        kwargs = self._sample_event_kwargs()
        kwargs["detection_count"] = 5  # Mismatched with 3 IDs
        with self.assertRaises(ValidationError):
            Event(**kwargs)

    def test_event_inverted_temporal_span(self) -> None:
        kwargs = self._sample_event_kwargs()
        kwargs["started_at"] = datetime(2026, 8, 29, 8, 0, tzinfo=UTC)
        kwargs["ended_at"] = datetime(2026, 8, 29, 6, 0, tzinfo=UTC)
        with self.assertRaises(ValidationError):
            Event(**kwargs)

    def test_event_duplicate_detections(self) -> None:
        kwargs = self._sample_event_kwargs()
        kwargs["detection_ids"] = ["det-1", "det-1", "det-2"]
        kwargs["detection_count"] = 3
        with self.assertRaises(ValidationError):
            Event(**kwargs)


class TestPersistentSourceSchema(unittest.TestCase):
    """Tests for the canonical PersistentSource domain model."""

    def _sample_source_kwargs(self) -> dict[str, Any]:
        return {
            "source_id": "src-persistent-001",
            "linked_event_ids": ["evt-1", "evt-2", "evt-3"],
            "total_event_count": 3,
            "centroid_geometry": Coordinate(latitude=21.55, longitude=85.25),
            "first_seen_at": datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
            "last_seen_at": datetime(2026, 8, 29, 12, 0, tzinfo=UTC),
            "active_days_count": 45,
            "persistence_state": PersistenceState.PERSISTENT,
            "persistence_configuration_id": "cfg-persistence-score-v1",
            "persistence_configuration_version": "1.0.0",
            "recurrence_ratio": 0.85,
        }

    def test_valid_persistent_source(self) -> None:
        source = PersistentSource(**self._sample_source_kwargs())
        self.assertEqual(source.source_id, "src-persistent-001")
        self.assertEqual(source.persistence_state, PersistenceState.PERSISTENT)
        self.assertEqual(source.active_days_count, 45)

    def test_source_event_count_mismatch(self) -> None:
        kwargs = self._sample_source_kwargs()
        kwargs["total_event_count"] = 10
        with self.assertRaises(ValidationError):
            PersistentSource(**kwargs)

    def test_source_inverted_dates(self) -> None:
        kwargs = self._sample_source_kwargs()
        kwargs["first_seen_at"] = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
        kwargs["last_seen_at"] = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        with self.assertRaises(ValidationError):
            PersistentSource(**kwargs)


class TestContextEvidenceSchema(unittest.TestCase):
    """Tests for ContextEvidence and missingness/availability semantics."""

    def test_valid_context_evidence_available(self) -> None:
        context = ContextEvidence(
            context_id="ctx-osm-001",
            source_type="osm",
            context_type=ContextType.OIL_GAS,
            geometry=Coordinate(latitude=21.54, longitude=85.24),
            availability_state=EvidenceAvailabilityState.AVAILABLE,
            external_facility_id="osm_way_998877",
            facility_name="Refinery Flare Stack",
            distance_to_event_meters=120.5,
        )
        self.assertEqual(context.context_type, ContextType.OIL_GAS)
        self.assertEqual(context.distance_to_event_meters, 120.5)

    def test_context_not_found_in_source_semantics(self) -> None:
        context = ContextEvidence(
            context_id="ctx-osm-002",
            source_type="osm",
            context_type=ContextType.UNKNOWN,
            geometry=Coordinate(latitude=21.54, longitude=85.24),
            availability_state=EvidenceAvailabilityState.NOT_FOUND_IN_SOURCE,
        )
        self.assertEqual(
            context.availability_state,
            EvidenceAvailabilityState.NOT_FOUND_IN_SOURCE,
        )
        self.assertIsNone(context.external_facility_id)


class TestIntelligenceResultSchema(unittest.TestCase):
    """Tests for the canonical IntelligenceResult domain model."""

    def _sample_intelligence_kwargs(self) -> dict[str, Any]:
        return {
            "intelligence_id": "intel-res-101",
            "event_id": "evt-9876",
            "phenomenon": PhenomenonType.FLARE,
            "context": ContextType.OIL_GAS,
            "persistence": PersistenceState.PERSISTENT,
            "attribution": AttributionStrength.STRONG,
            "uncertainty": UncertaintyMetric(
                model_probability=0.94,
                calibrated_confidence=0.91,
                data_quality_score=0.98,
                abstention_recommended=False,
            ),
            "evidence_completeness": EvidenceCompleteness(
                categories=[
                    EvidenceCategoryState(
                        category="firms",
                        status=EvidenceAvailabilityState.AVAILABLE,
                        details="VIIRS 375m detection series",
                    ),
                    EvidenceCategoryState(
                        category="satellite",
                        status=EvidenceAvailabilityState.UNAVAILABLE,
                        details="Cloud cover 90%",
                    ),
                ],
                available_count=1,
                total_expected_count=2,
                completeness_ratio=0.5,
            ),
            "created_at": datetime(2026, 8, 29, 7, 15, tzinfo=UTC),
            "model_version": "v1-baseline-rules",
        }

    def test_valid_intelligence_result(self) -> None:
        intel = IntelligenceResult(**self._sample_intelligence_kwargs())
        self.assertEqual(intel.phenomenon, PhenomenonType.FLARE)
        self.assertEqual(intel.context, ContextType.OIL_GAS)
        self.assertEqual(intel.persistence, PersistenceState.PERSISTENT)
        self.assertEqual(intel.attribution, AttributionStrength.STRONG)
        self.assertFalse(intel.uncertainty.abstention_recommended)

    def test_intelligence_abstention_result(self) -> None:
        kwargs = self._sample_intelligence_kwargs()
        kwargs["phenomenon"] = PhenomenonType.UNKNOWN
        kwargs["uncertainty"] = UncertaintyMetric(
            model_probability=0.45,
            calibrated_confidence=0.38,
            data_quality_score=0.50,
            abstention_recommended=True,
            abstention_reason="Low confidence below threshold",
        )
        intel = IntelligenceResult(**kwargs)
        self.assertEqual(intel.phenomenon, PhenomenonType.UNKNOWN)
        self.assertTrue(intel.uncertainty.abstention_recommended)
        self.assertEqual(
            intel.uncertainty.abstention_reason,
            "Low confidence below threshold",
        )


class TestDomainInvariants(unittest.TestCase):
    """Property and invariant tests required by Step 30."""

    def test_invariant_1_geographic_coordinates_bounded(self) -> None:
        with self.assertRaises(ValidationError):
            Coordinate(latitude=91.0, longitude=0.0)
        with self.assertRaises(ValidationError):
            Coordinate(latitude=0.0, longitude=181.0)

    def test_invariant_2_timezone_aware_timestamps(self) -> None:
        with self.assertRaises(ValidationError):
            Detection(
                detection_id="det-1",
                source="firms",
                source_snapshot_id="snap-1",
                acquired_at=datetime(2026, 8, 29, 6, 0),  # Naive
                geometry=Coordinate(latitude=20.0, longitude=80.0),
                satellite="NOAA-20",
                instrument="VIIRS",
                product_type="nrt",
                product_version="v1",
                raw_hash="hash123",
            )

    def test_invariant_4_and_5_persistence_and_context_orthogonal(
        self,
    ) -> None:
        """Verify that any combination of orthogonal dimensions can be represented."""
        intel = IntelligenceResult(
            intelligence_id="intel-inv-1",
            event_id="evt-1",
            phenomenon=PhenomenonType.AGRICULTURAL_BURN,
            context=ContextType.AGRICULTURAL,
            persistence=PersistenceState.RECURRING,
            attribution=AttributionStrength.MODERATE,
            uncertainty=UncertaintyMetric(abstention_recommended=False),
            evidence_completeness=EvidenceCompleteness(),
            created_at=datetime.now(UTC),
        )
        self.assertEqual(intel.phenomenon, PhenomenonType.AGRICULTURAL_BURN)
        self.assertEqual(intel.persistence, PersistenceState.RECURRING)

    def test_invariant_6_facility_proximity_does_not_imply_attribution(self) -> None:
        """Context distance does not force attribution to be strong."""
        ctx = ContextEvidence(
            context_id="ctx-inv-1",
            source_type="osm",
            context_type=ContextType.INDUSTRIAL,
            geometry=Coordinate(latitude=20.0, longitude=80.0),
            availability_state=EvidenceAvailabilityState.AVAILABLE,
            distance_to_event_meters=15.0,  # Very close
        )
        # Even with close proximity, attribution in IntelligenceResult
        # remains an independent judgment
        intel = IntelligenceResult(
            intelligence_id="intel-inv-2",
            event_id="evt-1",
            phenomenon=PhenomenonType.UNKNOWN,
            context=ContextType.INDUSTRIAL,
            persistence=PersistenceState.TRANSIENT,
            attribution=AttributionStrength.UNKNOWN,  # Attribution remains independent
            uncertainty=UncertaintyMetric(abstention_recommended=True),
            evidence_completeness=EvidenceCompleteness(),
            created_at=datetime.now(UTC),
        )
        self.assertEqual(ctx.distance_to_event_meters, 15.0)
        self.assertEqual(intel.attribution, AttributionStrength.UNKNOWN)

    def test_invariant_7_and_8_unknown_and_unresolved_are_not_negative(self) -> None:
        """Confirm explicit preservation of UNKNOWN and NOT_FOUND states."""
        self.assertNotEqual(
            EvidenceAvailabilityState.NOT_FOUND_IN_SOURCE,
            EvidenceAvailabilityState.AVAILABLE,
        )
        self.assertNotEqual(
            PhenomenonType.UNKNOWN, PhenomenonType.OTHER_THERMAL_ANOMALY
        )
        self.assertNotEqual(
            PersistenceState.INSUFFICIENT_HISTORY, PersistenceState.TRANSIENT
        )


if __name__ == "__main__":
    unittest.main()
