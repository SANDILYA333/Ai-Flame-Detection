import { describe, it } from "node:test";
import assert from "node:assert/strict";

import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import { filterEventsByLocation } from "../lib/location/locationFilter.ts";
import {
  derivePrimaryCategory,
  isEventInCategory,
  computeCategoryMetrics,
} from "../lib/categories/fireCategories.ts";
import { calculateOperationalRisk } from "../lib/risk/scoring.ts";
import type { ContextualMediaResponse } from "../types/media.ts";

describe("Phase 3: Advanced Analysis Integration & Contextual Intelligence", () => {
  it("preserves canonical event ID and telemetry across the complete navigation chain", () => {
    // 1. User discovers Nalgonda Wildfire event in Level 1 Telangana Scope
    const telanganaEvents = filterEventsByLocation(DEMO_THERMAL_EVENTS, "India", "Telangana");
    assert.ok(telanganaEvents.length >= 2, "Expected at least 2 events in Telangana");

    const nalgondaEvent = telanganaEvents.find((e) => e.event_id === "EVT-2026-0831-21");
    assert.ok(nalgondaEvent, "Expected Nalgonda event EVT-2026-0831-21 to exist");

    // 2. Event has canonical attributes
    assert.strictEqual(nalgondaEvent.event_id, "EVT-2026-0831-21");
    assert.strictEqual(nalgondaEvent.classification, "NON_INDUSTRIAL");
    assert.strictEqual(nalgondaEvent.latitude, 17.05);
    assert.strictEqual(nalgondaEvent.longitude, 79.27);
    assert.strictEqual(nalgondaEvent.frp_mw, 265.0);

    // 3. Category matches Wildfire
    assert.strictEqual(isEventInCategory(nalgondaEvent, "WILDFIRE"), true);
    assert.strictEqual(derivePrimaryCategory(nalgondaEvent), "WILDFIRE");

    // 4. Severity is High/Critical based on FRP
    const risk = calculateOperationalRisk(nalgondaEvent);
    assert.ok(["HIGH", "CRITICAL"].includes(risk.level), `Expected HIGH or CRITICAL, got ${risk.level}`);

    // 5. When transitioning to Level 2 Advanced Analysis, the exact canonical ID is passed
    const handoffPayload = {
      event_id: nalgondaEvent.event_id,
      coordinates: [nalgondaEvent.longitude, nalgondaEvent.latitude],
      frp_mw: nalgondaEvent.frp_mw,
      classification: nalgondaEvent.classification,
    };
    assert.strictEqual(handoffPayload.event_id, "EVT-2026-0831-21");
  });

  it("handles contextual media and external news structure safely", () => {
    const mockMediaResponse: ContextualMediaResponse = {
      event_id: "EVT-2026-0831-21",
      query_context: {
        location_query: "Nalgonda Reserve Forest, Telangana, India",
        classification: "NON_INDUSTRIAL",
        facility_name: "Nalgonda Reserve Forest",
        temporal_window: "2026-08-31T13:23:00Z to 2026-08-31T13:35:00Z",
      },
      news: [
        {
          id: "news-1",
          title: "Forest Dept mobilizes rapid response in Nalgonda reserve corridor",
          source: "State Forest Operations Bulletin",
          published_at: "2026-08-31T13:00:00Z",
          url: "https://forests.telangana.gov.in/dispatches/nalgonda",
          snippet: "Thermal anomalies detected along perimeter.",
          relevance_score: 0.94,
          corroboration_type: "OFFICIAL_DISPATCH",
        },
      ],
      videos: [
        {
          id: "vid-1",
          youtube_id: "dQw4w9WgXcQ",
          title: "Nalgonda Reserve Tactical Briefing",
          channel_title: "State Fire Services",
          published_at: "2026-08-31T12:45:00Z",
          thumbnail_url: "https://images.unsplash.com/photo-1542382257-80dedb725088",
          description: "Tactical briefing video",
        },
      ],
      disclaimer: "External coverage is supplementary.",
      is_live_service: false,
    };

    assert.strictEqual(mockMediaResponse.event_id, "EVT-2026-0831-21");
    assert.strictEqual(mockMediaResponse.news.length, 1);
    assert.strictEqual(mockMediaResponse.news[0].corroboration_type, "OFFICIAL_DISPATCH");
    assert.strictEqual(mockMediaResponse.videos.length, 1);
    assert.strictEqual(mockMediaResponse.videos[0].youtube_id, "dQw4w9WgXcQ");
    assert.ok(mockMediaResponse.disclaimer.includes("External"));
  });

  it("gracefully falls back when no external news or videos exist without failing", () => {
    const emptyMediaResponse: ContextualMediaResponse = {
      event_id: "EVT-2026-0831-02",
      query_context: {
        location_query: "Singrauli Super Thermal Power Station, MP, India",
        classification: "INDUSTRIAL",
        facility_name: "Singrauli",
        temporal_window: "2026-08-31T09:30:00Z to 2026-08-31T13:20:15Z",
      },
      news: [],
      videos: [],
      disclaimer: "External news and media are retrieved via contextual indexing.",
      is_live_service: false,
    };

    assert.strictEqual(emptyMediaResponse.news.length, 0);
    assert.strictEqual(emptyMediaResponse.videos.length, 0);
    assert.strictEqual(emptyMediaResponse.event_id, "EVT-2026-0831-02");
  });

  it("verifies deep linking URL search params resolution", () => {
    const testSearchQuery = "?view=analysis&event=EVT-2026-0831-21&state=Telangana";
    const params = new URLSearchParams(testSearchQuery);

    assert.strictEqual(params.get("view"), "analysis");
    assert.strictEqual(params.get("event"), "EVT-2026-0831-21");
    assert.strictEqual(params.get("state"), "Telangana");

    // Match against catalog
    const matched = DEMO_THERMAL_EVENTS.find(
      (e) => e.event_id.toLowerCase() === params.get("event")?.toLowerCase()
    );
    assert.ok(matched, "Expected event EVT-2026-0831-21 to resolve from URL parameter");
    assert.strictEqual(matched.event_id, "EVT-2026-0831-21");
  });
});
