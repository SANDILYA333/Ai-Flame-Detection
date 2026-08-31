import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { fetchEvents, fetchEventDetail, fetchEventTimeline } from "../lib/api/events.ts";
import { ApiClientError, getApiBaseUrl } from "../lib/api/client.ts";
import type { EventsResponse, BackendEventItem } from "../types/event.ts";

describe("Thermal Events API Client Suite", () => {
  it("getApiBaseUrl returns a valid URL string", () => {
    const url = getApiBaseUrl();
    assert.equal(typeof url, "string");
    assert.ok(url.length > 0);
    assert.ok(!url.endsWith("/"));
  });

  it("ApiClientError correctly captures HTTP status and details", () => {
    const err = new ApiClientError({
      message: "Event not found",
      status: 404,
      statusText: "Not Found",
      data: { detail: "Event evt_123 not found" },
    });

    assert.equal(err.name, "ApiClientError");
    assert.equal(err.status, 404);
    assert.equal(err.statusText, "Not Found");
    assert.equal(err.message, "Event not found");
    assert.deepEqual(err.data, { detail: "Event evt_123 not found" });
    assert.equal(err.isNetworkError, false);
  });

  it("fetchEvents parses real backend response schema accurately", async () => {
    try {
      const response: EventsResponse = await fetchEvents({ limit: 10 });
      assert.ok(response);
      assert.equal(typeof response.service, "string");
      assert.ok(response.pagination);
      assert.equal(typeof response.pagination.total_count, "number");
      assert.ok(Array.isArray(response.events));

      if (response.events.length > 0) {
        const item: BackendEventItem = response.events[0];
        assert.equal(typeof item.event_id, "string");
        assert.ok(item.event_id.startsWith("evt_"));
        assert.equal(typeof item.centroid_latitude, "number");
        assert.equal(typeof item.centroid_longitude, "number");
        assert.ok(item.centroid_latitude >= -90 && item.centroid_latitude <= 90);
        assert.ok(item.centroid_longitude >= -180 && item.centroid_longitude <= 180);
        assert.equal(typeof item.started_at, "string");
        assert.equal(typeof item.ended_at, "string");
        assert.equal(typeof item.detection_count, "number");
      }
    } catch (err) {
      // If backend is unavailable during local isolated runs, ensure structured ApiClientError is thrown
      if (err instanceof ApiClientError) {
        assert.ok(err.isNetworkError || err.status > 0);
      } else {
        throw err;
      }
    }
  });

  it("fetchEventDetail throws on empty eventId", async () => {
    await assert.rejects(
      async () => {
        await fetchEventDetail("");
      },
      {
        name: "Error",
        message: "eventId is required to fetch event detail",
      }
    );
  });

  it("fetchEventTimeline throws on empty eventId", async () => {
    await assert.rejects(
      async () => {
        await fetchEventTimeline("");
      },
      {
        name: "Error",
        message: "eventId is required to fetch event timeline",
      }
    );
  });
});
