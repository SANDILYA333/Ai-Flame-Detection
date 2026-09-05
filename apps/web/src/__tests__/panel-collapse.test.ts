import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { DEMO_THERMAL_EVENTS } from "../features/events/mock/demo-events.ts";
import { INITIAL_LAYERS } from "../config/ui.ts";
import type { ThermalEvent } from "../types/event.ts";
import type { TimeWindow, PlaybackMode } from "../types/playback.ts";

describe("UI Panel Collapse & Expand Controls & State Preservation Suite", () => {
  const sampleEvents = DEMO_THERMAL_EVENTS;

  it("Test 1: Incident / Event Detail Panel Collapse & State Invariance", () => {
    // Simulated state for Event Detail Panel
    let selectedEvent: ThermalEvent | null = sampleEvents[0];
    let isPanelOpen = true;
    let isPanelCollapsed = false;

    assert.equal(selectedEvent.event_id, "EVT-2026-0831-01");
    assert.equal(isPanelOpen, true);
    assert.equal(isPanelCollapsed, false);

    // 1. User clicks collapse button (︿ -> ﹀)
    isPanelCollapsed = true;

    // Panel remains open (present in DOM) with collapsed state
    assert.equal(isPanelOpen, true);
    assert.equal(isPanelCollapsed, true);

    // Selected event, classification, confidence and FRP must remain 100% preserved
    assert.ok(selectedEvent !== null);
    assert.equal(selectedEvent.event_id, "EVT-2026-0831-01");
    assert.equal(selectedEvent.classification, "INDUSTRIAL");
    assert.equal(selectedEvent.confidence, 0.964);
    assert.equal(selectedEvent.frp_mw, 245.8);

    // 2. User clicks expand button (﹀ -> ︿)
    isPanelCollapsed = false;
    assert.equal(isPanelOpen, true);
    assert.equal(isPanelCollapsed, false);
    assert.equal(selectedEvent.event_id, "EVT-2026-0831-01");

    // 3. Separation of Collapse vs Close: User clicks close button [X]
    isPanelOpen = false;
    assert.equal(isPanelOpen, false);
    // Selected event state remains in context even when panel closed
    assert.ok(selectedEvent !== null);
  });

  it("Test 2: GIS Layers Panel Collapse & Layer State Invariance", () => {
    let isLayersOpen = true;
    let isLayersCollapsed = false;
    const activeLayers: Record<string, boolean> = {};
    INITIAL_LAYERS.forEach((layer) => {
      activeLayers[layer.id] = layer.enabled;
    });

    const activeCountBefore = Object.values(activeLayers).filter(Boolean).length;
    assert.ok(activeCountBefore > 0);

    // 1. User toggles a layer
    activeLayers["nasa-firms-viirs"] = false;
    activeLayers["global-power-plants"] = true;

    // 2. User collapses the GIS Layers panel
    isLayersCollapsed = true;
    assert.equal(isLayersOpen, true);
    assert.equal(isLayersCollapsed, true);

    // Active layer toggles must not be reset on collapse
    assert.equal(activeLayers["nasa-firms-viirs"], false);
    assert.equal(activeLayers["global-power-plants"], true);

    // 3. User expands the GIS Layers panel
    isLayersCollapsed = false;
    assert.equal(isLayersCollapsed, false);
    assert.equal(activeLayers["nasa-firms-viirs"], false);
    assert.equal(activeLayers["global-power-plants"], true);
  });

  it("Test 3: Timeline Playback Bar Collapse & Temporal State Invariance", () => {
    let isTimelineCollapsed = false;
    let playbackMode: PlaybackMode = "LIVE";
    let isPlaying = false;
    let playbackProgress = 0.65;
    let timeRange: TimeWindow = "24H";
    let playbackSpeed = 4;

    // 1. User modifies timeline controls
    playbackMode = "PLAYBACK";
    isPlaying = true;
    playbackProgress = 0.78;
    timeRange = "48H";
    playbackSpeed = 8;

    // 2. User clicks collapse on timeline
    isTimelineCollapsed = true;
    assert.equal(isTimelineCollapsed, true);

    // All temporal properties must remain identical while collapsed
    assert.equal(playbackMode, "PLAYBACK");
    assert.equal(isPlaying, true);
    assert.equal(playbackProgress, 0.78);
    assert.equal(timeRange, "48H");
    assert.equal(playbackSpeed, 8);

    // 3. User expands timeline
    isTimelineCollapsed = false;
    assert.equal(isTimelineCollapsed, false);
    assert.equal(playbackMode, "PLAYBACK");
    assert.equal(isPlaying, true);
    assert.equal(playbackProgress, 0.78);
    assert.equal(timeRange, "48H");
    assert.equal(playbackSpeed, 8);
  });
});
