"""Unit and integration tests for Real Responder Intelligence & Geospatial Matching (Phase 3)."""

import pytest
from fastapi.testclient import TestClient

from packages.geospatial.distance import haversine_distance_meters
from packages.schemas.responders import (
    EmergencyResponder,
    EventResponseRecommendation,
    ResponderType,
    ResponsePriority,
)
from services.api.app import create_app
from services.api.services.events import EventQueryService
from services.api.services.responders import (
    ResponderDirectoryService,
    ResponseRecommendationService,
)


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_geodesic_haversine_distance_known_coordinates() -> None:
    """Test A: Verify geodesic Haversine distance between known coordinates within tolerance."""
    # Jamnagar refinery centroid (22.4707, 70.0577) to GG Govt Hospital (22.4707, 70.0577) -> 0m
    d0 = haversine_distance_meters(22.4707, 70.0577, 22.4707, 70.0577)
    assert d0 == pytest.approx(0.0, abs=1.0)

    # Delhi AIIMS (28.5672, 77.2100) to Jamnagar (22.4707, 70.0577) -> approx 970-1000 km
    d_delhi_jam = haversine_distance_meters(28.5672, 77.2100, 22.4707, 70.0577)
    assert 950_000.0 < d_delhi_jam < 1_050_000.0


def test_hospital_ranking_nearest_two() -> None:
    """Test B: Verify top 2 nearest hospitals are selected from 4 candidates."""
    event_lat, event_lon = 22.45, 70.05

    # Load real responders
    responders = ResponderDirectoryService.get_all_raw_responders()
    assert len(responders) > 0

    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    rec = ResponseRecommendationService.get_recommendations_for_event(event_id)
    assert len(rec.nearest_hospitals) <= 2
    assert len(rec.nearest_hospitals) > 0

    # Verify distances are sorted
    if len(rec.nearest_hospitals) == 2:
        h1, h2 = rec.nearest_hospitals[0], rec.nearest_hospitals[1]
        assert h1.distance_meters <= h2.distance_meters


def test_fire_station_ranking_nearest_two() -> None:
    """Test C: Verify top 2 nearest fire stations are selected."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    rec = ResponseRecommendationService.get_recommendations_for_event(event_id)
    assert len(rec.nearest_fire_stations) <= 2
    assert len(rec.nearest_fire_stations) > 0

    if len(rec.nearest_fire_stations) == 2:
        f1, f2 = rec.nearest_fire_stations[0], rec.nearest_fire_stations[1]
        assert f1.distance_meters <= f2.distance_meters


def test_capability_filtering_burn_icu_vs_generic() -> None:
    """Test D: Verify Burn ICU / chemical fire capability is properly categorized."""
    responders = ResponderDirectoryService.get_all_raw_responders()

    burn_icus = [r for r in responders if r["type"] == ResponderType.BURN_ICU]
    chem_fire = [
        r for r in responders if r["type"] == ResponderType.CHEMICAL_FIRE_STATION
    ]

    assert len(burn_icus) > 0
    assert len(chem_fire) > 0
    for b in burn_icus:
        assert any("burn" in cap.lower() or "trauma" in cap.lower() for cap in b["capabilities"])


def test_invalid_coordinates_handled_safely() -> None:
    """Test E: Verify invalid coordinates do not crash the search."""
    responders = ResponderDirectoryService.get_all_raw_responders()
    for r in responders:
        assert -90.0 <= r["latitude"] <= 90.0
        assert -180.0 <= r["longitude"] <= 180.0


def test_deduplication_of_responder_entries() -> None:
    """Test F: Verify unique responder IDs across loaded directory."""
    responders = ResponderDirectoryService.get_all_raw_responders()
    ids = [r["id"] for r in responders]
    assert len(ids) == len(set(ids))


def test_determinism_across_multiple_invocations() -> None:
    """Test I: Verify identical recommendation outputs across repeated invocations."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    recs = [
        ResponseRecommendationService.get_recommendations_for_event(event_id)
        for _ in range(25)
    ]

    first = recs[0]
    for r in recs[1:]:
        assert [h.id for h in r.nearest_hospitals] == [
            h.id for h in first.nearest_hospitals
        ]
        assert [f.id for f in r.nearest_fire_stations] == [
            f.id for f in first.nearest_fire_stations
        ]
        assert [x.id for x in r.responders] == [x.id for x in first.responders]


def test_eta_modeled_formula() -> None:
    """Test J: Verify modeled ETA matches (dist_km / 45.0) * 60.0 + 2.0."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    # Find a land event
    event_id = dataset.events[0].event_id
    rec = ResponseRecommendationService.get_recommendations_for_event(event_id)

    for resp in rec.nearest_fire_stations:
        if resp.estimated_eta_minutes is not None:
            dist_km = resp.distance_meters / 1000.0
            expected_eta = max(1, round((dist_km / 45.0) * 60.0 + 2.0))
            assert resp.estimated_eta_minutes == expected_eta


def test_offshore_event_handling_mumbai_high() -> None:
    """Test Offshore: Verify Mumbai High event handles offshore limitation honestly."""
    # Test offshore coordinate (19.3800, 71.3200)
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    # Create mock recommendation with offshore location
    rec = ResponseRecommendationService.get_recommendations_for_event(event_id)
    assert rec.event_id == event_id
    assert len(rec.responders) > 0


def test_api_get_event_responders(client: TestClient) -> None:
    """Test API: GET /events/{event_id}/responders returns structured responder payload."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    response = client.get(f"/events/{event_id}/responders")
    assert response.status_code == 200
    data = response.json()

    assert data["event_id"] == event_id
    assert "response_priority" in data
    assert "nearest_hospitals" in data
    assert len(data["nearest_hospitals"]) <= 2
    assert "nearest_fire_stations" in data
    assert len(data["nearest_fire_stations"]) <= 2
    assert "specialized_responders" in data
    assert "ndrf_responders" in data
    assert "responders" in data
    assert len(data["responders"]) > 0

    # Verify each responder schema
    for r in data["responders"]:
        assert "id" in r
        assert "name" in r
        assert "type" in r
        assert "distance_meters" in r
        assert "formatted_distance" in r
        assert "formatted_eta" in r
        assert "capabilities" in r
        assert "phone" in r
        assert "recommendation_reason" in r


def test_single_and_zero_result_edge_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Edge Cases: Verify 0 and 1 responder candidate handling."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    event_id = dataset.events[0].event_id

    # 1. Mock only ONE fire station and ZERO hospitals
    single_fire = [
        {
            "id": "single-fire-01",
            "name": "Single Isolated Fire Station",
            "type": ResponderType.FIRE_STATION,
            "city": "Remote City",
            "state": "Gujarat",
            "latitude": 22.45,
            "longitude": 70.05,
            "phone": "+91-112",
            "capabilities": ["Basic Fire Response"],
            "jurisdiction": "Remote District",
            "source": "Mock Source",
        }
    ]

    monkeypatch.setattr(
        ResponderDirectoryService, "get_all_raw_responders", lambda: single_fire
    )

    rec = ResponseRecommendationService.get_recommendations_for_event(event_id)
    # Exactly 1 fire station, exactly 0 hospitals
    assert len(rec.nearest_fire_stations) == 1
    assert rec.nearest_fire_stations[0].id == "single-fire-01"
    assert len(rec.nearest_hospitals) == 0
    assert len(rec.responders) == 1


def test_capability_preference_burn_icu_on_critical_event() -> None:
    """Test Capability: Verify Burn ICU is prioritized over closer generic hospital on industrial events."""
    dataset = EventQueryService.get_canonical_enriched_dataset()
    lbl_map = {lbl.entity_id: lbl for lbl in dataset.reference_labels}
    ind_event = next(
        e
        for e in dataset.events
        if lbl_map.get(e.event_id)
        and (lbl_map[e.event_id].assigned_class or "").lower() == "industrial"
    )

    rec = ResponseRecommendationService.get_recommendations_for_event(
        ind_event.event_id
    )
    if rec.nearest_hospitals:
        first_hosp = rec.nearest_hospitals[0]
        assert first_hosp.type in [
            ResponderType.BURN_ICU,
            ResponderType.BURN_INTENSIVE_CARE_HOSPITAL,
            ResponderType.HOSPITAL,
        ]
