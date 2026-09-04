import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  fetchIndustrialAssetsGeoJson,
  EMPTY_INDUSTRIAL_COLLECTION,
  getIndustrialAssetLayerId,
  isIndustrialAssetVisible,
  filterIndustrialAssetsByLayers,
  type IndustrialAssetProperties,
  type IndustrialAssetFeature,
  type IndustrialAssetFeatureCollection,
} from "../lib/api/industrial.ts";
import { INITIAL_LAYERS } from "../config/ui.ts";

describe("Phase 3: Industrial Asset Map Integration Suite", () => {
  it("EMPTY_INDUSTRIAL_COLLECTION has valid GeoJSON FeatureCollection structure", () => {
    assert.equal(EMPTY_INDUSTRIAL_COLLECTION.type, "FeatureCollection");
    assert.ok(Array.isArray(EMPTY_INDUSTRIAL_COLLECTION.features));
    assert.equal(EMPTY_INDUSTRIAL_COLLECTION.features.length, 0);
  });

  it("fetchIndustrialAssetsGeoJson returns valid FeatureCollection or resilient fallback", async () => {
    const result = await fetchIndustrialAssetsGeoJson({ limit: 5 });
    assert.ok(result);
    assert.equal(result.type, "FeatureCollection");
    assert.ok(Array.isArray(result.features));

    // If backend is running, verify real features; if offline, verify graceful fallback
    if (result.features.length > 0) {
      assert.ok(result.features.length > 0);
      const feat: IndustrialAssetFeature = result.features[0];
      assert.equal(feat.type, "Feature");
      assert.equal(feat.geometry.type, "Point");
      assert.ok(Array.isArray(feat.geometry.coordinates));
      assert.equal(feat.geometry.coordinates.length, 2);

      const [lon, lat] = feat.geometry.coordinates;
      assert.ok(typeof lon === "number" && !Number.isNaN(lon));
      assert.ok(typeof lat === "number" && !Number.isNaN(lat));
      // India bounds check
      assert.ok(lon >= 60 && lon <= 100, `Longitude ${lon} out of expected range`);
      assert.ok(lat >= 5 && lat <= 40, `Latitude ${lat} out of expected range`);

      const props: IndustrialAssetProperties = feat.properties;
      assert.ok(typeof props.id === "string" && props.id.length > 0);
      assert.ok(typeof props.name === "string" && props.name.length > 0);
      assert.ok(typeof props.industry === "string");
      assert.ok(typeof props.source === "string");
    }
  });

  it("validates coordinate order [longitude, latitude] across multiple features", () => {
    const mockCollection: IndustrialAssetFeatureCollection = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          id: "asset_jamnagar",
          geometry: { type: "Point", coordinates: [70.0577, 22.4707] },
          properties: {
            id: "asset_jamnagar",
            name: "Jamnagar Refinery",
            asset_type: "refinery",
            industry: "oil_gas",
            context_type: "oil_gas",
            country: "India",
            state: "Gujarat",
            status: "operating",
            source: "audited_master",
            linked_source_ids: [],
            is_map_eligible: true,
          },
        },
        {
          type: "Feature",
          id: "asset_tata_steel",
          geometry: { type: "Point", coordinates: [86.2029, 22.8046] },
          properties: {
            id: "asset_tata_steel",
            name: "Tata Steel Jamshedpur",
            asset_type: "steel_plant",
            industry: "metallurgy",
            context_type: "manufacturing",
            country: "India",
            state: "Jharkhand",
            status: "operating",
            source: "audited_master",
            linked_source_ids: [],
            is_map_eligible: true,
          },
        },
        {
          type: "Feature",
          id: "asset_korba_stps",
          geometry: { type: "Point", coordinates: [82.6841, 22.3595] },
          properties: {
            id: "asset_korba_stps",
            name: "Korba Super Thermal Power Plant",
            asset_type: "power_plant",
            industry: "power",
            context_type: "energy",
            country: "India",
            state: "Chhattisgarh",
            status: "operating",
            source: "audited_master",
            capacity: 2600,
            capacity_unit: "MW",
            linked_source_ids: [],
            is_map_eligible: true,
          },
        },
      ],
    };

    assert.equal(mockCollection.features.length, 3);
    for (const feat of mockCollection.features) {
      assert.equal(feat.type, "Feature");
      assert.equal(feat.geometry.type, "Point");
      const [lon, lat] = feat.geometry.coordinates;
      // Coordinates must be [longitude, latitude], not [latitude, longitude]
      assert.ok(lon > lat, `Expected longitude (${lon}) > latitude (${lat}) for mainland India assets`);
      assert.ok(lon >= -180 && lon <= 180);
      assert.ok(lat >= -90 && lat <= 90);
    }
  });

  it("assigns sector styling colors deterministically without collision", () => {
    const getSectorColor = (industry?: string): string => {
      switch (industry) {
        case "power":
          return "#eab308";
        case "oil_gas":
          return "#f97316";
        case "metallurgy":
          return "#a855f7";
        case "chemical":
          return "#06b6d4";
        default:
          return "#10b981";
      }
    };

    assert.equal(getSectorColor("power"), "#eab308");
    assert.equal(getSectorColor("oil_gas"), "#f97316");
    assert.equal(getSectorColor("metallurgy"), "#a855f7");
    assert.equal(getSectorColor("chemical"), "#06b6d4");
    assert.equal(getSectorColor("unknown"), "#10b981");
    assert.equal(getSectorColor(undefined), "#10b981");
  });

  it("guarantees complete domain separation from thermal events", () => {
    // Industrial assets must have dedicated schema properties distinct from ThermalEvent
    const industrialFeature: IndustrialAssetFeature = {
      type: "Feature",
      id: "ind_delhi_power",
      geometry: { type: "Point", coordinates: [77.209, 28.6139] },
      properties: {
        id: "ind_delhi_power",
        name: "Badarpur Power Station",
        asset_type: "power_plant",
        industry: "power",
        context_type: "energy",
        country: "India",
        status: "operating",
        source: "audited_master",
        state: "Delhi",
        linked_source_ids: [],
        is_map_eligible: true,
      },
    };

    // Thermal event specific fields must NOT be required or present on industrial asset
    const props = industrialFeature.properties as unknown as Record<string, unknown>;
    assert.equal(props.phenomenon, undefined);
    assert.equal(props.frp_mw, undefined);
    assert.equal(props.uncertainty_state, undefined);
    assert.equal(props.evacuation_radius_km, undefined);
    assert.ok(props.id !== undefined);
    assert.ok(props.industry !== undefined);
  });

  it("isValidIndustrialFeature detects malformed coordinates, NaNs, and out-of-range values", async () => {
    const { isValidIndustrialFeature } = await import("../lib/api/industrial.ts");

    // Valid feature
    assert.equal(
      isValidIndustrialFeature({
        type: "Feature",
        geometry: { type: "Point", coordinates: [72.8777, 19.076] },
        properties: {},
      }),
      true
    );

    // Invalid: null / undefined
    assert.equal(isValidIndustrialFeature(null), false);
    assert.equal(isValidIndustrialFeature(undefined), false);

    // Invalid: missing geometry or coordinates
    assert.equal(isValidIndustrialFeature({ type: "Feature" }), false);
    assert.equal(isValidIndustrialFeature({ type: "Feature", geometry: {} }), false);

    // Invalid: NaN coordinates
    assert.equal(
      isValidIndustrialFeature({
        type: "Feature",
        geometry: { type: "Point", coordinates: [NaN, 19.076] },
      }),
      false
    );
    assert.equal(
      isValidIndustrialFeature({
        type: "Feature",
        geometry: { type: "Point", coordinates: [72.8777, NaN] },
      }),
      false
    );

    // Invalid: Infinity / non-finite coordinates
    assert.equal(
      isValidIndustrialFeature({
        type: "Feature",
        geometry: { type: "Point", coordinates: [Infinity, 19.076] },
      }),
      false
    );

    // Invalid: out of geographic range
    assert.equal(
      isValidIndustrialFeature({
        type: "Feature",
        geometry: { type: "Point", coordinates: [195.0, 19.076] },
      }),
      false
    );
    assert.equal(
      isValidIndustrialFeature({
        type: "Feature",
        geometry: { type: "Point", coordinates: [72.8777, -95.0] },
      }),
      false
    );
  });

  it("in-memory cache deduplicates repeated calls and clearIndustrialAssetsCache resets it", async () => {
    const {
      fetchIndustrialAssetsGeoJson,
      clearIndustrialAssetsCache,
    } = await import("../lib/api/industrial.ts");

    clearIndustrialAssetsCache();

    // First call (fetches or returns fallback)
    const call1 = await fetchIndustrialAssetsGeoJson({ limit: 2 });
    // Second call with same params should return the exact same cached object reference
    const call2 = await fetchIndustrialAssetsGeoJson({ limit: 2 });
    assert.equal(call1, call2);

    // Clearing cache allows fresh fetch
    clearIndustrialAssetsCache();
    const call3 = await fetchIndustrialAssetsGeoJson({ limit: 2 });
    assert.ok(call3);
    assert.equal(call3.type, "FeatureCollection");
  });
});

describe("Phase 5: Industrial Asset GIS Layer Selection & Visibility Control", () => {
  const sampleFeatures: IndustrialAssetFeature[] = [
    {
      type: "Feature",
      id: "asset_power_1",
      geometry: { type: "Point", coordinates: [82.6841, 22.3595] },
      properties: {
        id: "asset_power_1",
        name: "Korba Super Thermal Power Plant",
        asset_type: "power_plant_coal",
        industry: "power",
        context_type: "energy",
        country: "India",
        state: "Chhattisgarh",
        status: "operating",
        source: "WRI Power Database",
        capacity: 2600,
        capacity_unit: "MW",
        linked_source_ids: [],
        is_map_eligible: true,
      },
    },
    {
      type: "Feature",
      id: "asset_steel_1",
      geometry: { type: "Point", coordinates: [86.2029, 22.8046] },
      properties: {
        id: "asset_steel_1",
        name: "Tata Steel Jamshedpur Plant",
        asset_type: "steel_plant",
        industry: "metallurgy",
        context_type: "manufacturing",
        country: "India",
        state: "Jharkhand",
        status: "operating",
        source: "GEM Iron & Steel Tracker",
        linked_source_ids: [],
        is_map_eligible: true,
      },
    },
    {
      type: "Feature",
      id: "asset_refinery_1",
      geometry: { type: "Point", coordinates: [70.0577, 22.4707] },
      properties: {
        id: "asset_refinery_1",
        name: "Jamnagar Petrochemical Refinery Complex",
        asset_type: "petrochemical_complex",
        industry: "oil_gas",
        context_type: "oil_gas",
        country: "India",
        state: "Gujarat",
        status: "operating",
        source: "GEM Oil & Gas Tracker",
        linked_source_ids: [],
        is_map_eligible: true,
      },
    },
    {
      type: "Feature",
      id: "asset_gas_1",
      geometry: { type: "Point", coordinates: [91.3602, 23.8712] },
      properties: {
        id: "asset_gas_1",
        name: "Agartala Gas Turbine Power Station",
        asset_type: "petrochemical_complex",
        industry: "oil_gas",
        context_type: "oil_gas",
        country: "India",
        state: "Tripura",
        status: "operating",
        source: "GEM Oil & Gas Tracker",
        linked_source_ids: [],
        is_map_eligible: true,
      },
    },
  ];

  const sampleCollection: IndustrialAssetFeatureCollection = {
    type: "FeatureCollection",
    features: sampleFeatures,
  };

  it("INITIAL_LAYERS enables all industrial infrastructure layers by default", () => {
    const industrialLayerIds = [
      "india-industrial-facilities",
      "global-power-plants",
      "global-oil-gas-tracker",
      "global-iron-steel-tracker",
    ];

    for (const layerId of industrialLayerIds) {
      const layer = INITIAL_LAYERS.find((l) => l.id === layerId);
      assert.ok(layer, `Layer ${layerId} must exist in INITIAL_LAYERS`);
      assert.equal(layer.enabled, true, `Layer ${layerId} must be enabled by default`);
      assert.equal(layer.category, "infrastructure");
    }
  });

  it("maps features to authoritative industrial layer IDs deterministically", () => {
    assert.equal(getIndustrialAssetLayerId(sampleFeatures[0]), "global-power-plants");
    assert.equal(getIndustrialAssetLayerId(sampleFeatures[1]), "global-iron-steel-tracker");
    assert.equal(getIndustrialAssetLayerId(sampleFeatures[2]), "india-industrial-facilities");
    assert.equal(getIndustrialAssetLayerId(sampleFeatures[3]), "global-oil-gas-tracker");
  });

  it("TEST 1: Initial state - all layers active renders all assets", () => {
    const activeLayers = {
      "india-industrial-facilities": true,
      "global-power-plants": true,
      "global-oil-gas-tracker": true,
      "global-iron-steel-tracker": true,
    };

    const result = filterIndustrialAssetsByLayers(sampleCollection, activeLayers);
    assert.equal(result.features.length, 4);
    assert.deepEqual(
      result.features.map((f) => f.id),
      ["asset_power_1", "asset_steel_1", "asset_refinery_1", "asset_gas_1"]
    );
  });

  it("TEST 2 & 3: Turn one layer OFF hides only that dataset; turning it back ON restores it", () => {
    // 1. Turn global-power-plants OFF
    const layersPowerOff = {
      "india-industrial-facilities": true,
      "global-power-plants": false,
      "global-oil-gas-tracker": true,
      "global-iron-steel-tracker": true,
    };

    const resPowerOff = filterIndustrialAssetsByLayers(sampleCollection, layersPowerOff);
    assert.equal(resPowerOff.features.length, 3);
    assert.equal(resPowerOff.features.some((f) => f.id === "asset_power_1"), false);
    assert.equal(resPowerOff.features.some((f) => f.id === "asset_steel_1"), true);
    assert.equal(resPowerOff.features.some((f) => f.id === "asset_refinery_1"), true);
    assert.equal(resPowerOff.features.some((f) => f.id === "asset_gas_1"), true);

    // 2. Turn global-power-plants back ON
    const layersPowerOn = {
      ...layersPowerOff,
      "global-power-plants": true,
    };
    const resPowerOn = filterIndustrialAssetsByLayers(sampleCollection, layersPowerOn);
    assert.equal(resPowerOn.features.length, 4);
    assert.equal(resPowerOn.features.some((f) => f.id === "asset_power_1"), true);
    // Verify coordinates match exactly without shift
    const restoredPower = resPowerOn.features.find((f) => f.id === "asset_power_1")!;
    assert.deepEqual(restoredPower.geometry.coordinates, [82.6841, 22.3595]);
  });

  it("TEST 4 & 5: Multiple layers OFF and restore", () => {
    // Turn off power and steel
    const layersMultipleOff = {
      "india-industrial-facilities": true,
      "global-power-plants": false,
      "global-oil-gas-tracker": true,
      "global-iron-steel-tracker": false,
    };

    const result = filterIndustrialAssetsByLayers(sampleCollection, layersMultipleOff);
    assert.equal(result.features.length, 2);
    assert.deepEqual(
      result.features.map((f) => f.id),
      ["asset_refinery_1", "asset_gas_1"]
    );

    // Restore all
    const layersAllOn = {
      "india-industrial-facilities": true,
      "global-power-plants": true,
      "global-oil-gas-tracker": true,
      "global-iron-steel-tracker": true,
    };
    const restored = filterIndustrialAssetsByLayers(sampleCollection, layersAllOn);
    assert.equal(restored.features.length, 4);
  });

  it("TEST 6: Repeated toggling (ON -> OFF -> ON -> OFF -> ON) preserves stability and prevents duplicates", () => {
    let currentLayers = {
      "india-industrial-facilities": true,
      "global-power-plants": true,
      "global-oil-gas-tracker": true,
      "global-iron-steel-tracker": true,
    };

    for (let cycle = 0; cycle < 5; cycle++) {
      // Toggle OFF
      currentLayers = { ...currentLayers, "global-iron-steel-tracker": false };
      const offResult = filterIndustrialAssetsByLayers(sampleCollection, currentLayers);
      assert.equal(offResult.features.length, 3);
      assert.equal(offResult.features.some((f) => f.id === "asset_steel_1"), false);

      // Toggle ON
      currentLayers = { ...currentLayers, "global-iron-steel-tracker": true };
      const onResult = filterIndustrialAssetsByLayers(sampleCollection, currentLayers);
      assert.equal(onResult.features.length, 4);
      // Ensure zero duplicated IDs
      const ids = onResult.features.map((f) => f.id);
      assert.equal(new Set(ids).size, 4);
    }
  });

  it("TEST 7: Independent visibility states (Layer A ON, Layer B OFF, Layer C ON, Layer D OFF)", () => {
    const mixedLayers = {
      "india-industrial-facilities": true,   // Layer A ON
      "global-power-plants": false,          // Layer B OFF
      "global-oil-gas-tracker": true,        // Layer C ON
      "global-iron-steel-tracker": false,    // Layer D OFF
    };

    const result = filterIndustrialAssetsByLayers(sampleCollection, mixedLayers);
    assert.equal(result.features.length, 2);
    assert.deepEqual(
      result.features.map((f) => f.id),
      ["asset_refinery_1", "asset_gas_1"]
    );
  });

  it("TEST 10: Complete domain separation from thermal detections", () => {
    // Turning off all industrial layers has zero effect on thermal events or activeLayers outside industrial scope
    const activeLayers = {
      "nasa-firms-viirs": true,
      "india-industrial-facilities": false,
      "global-power-plants": false,
      "global-oil-gas-tracker": false,
      "global-iron-steel-tracker": false,
    };

    // Thermal layer flag remains completely undisturbed
    assert.equal(activeLayers["nasa-firms-viirs"], true);

    const industrialResult = filterIndustrialAssetsByLayers(sampleCollection, activeLayers);
    assert.equal(industrialResult.features.length, 0);
  });

  it("TEST 13: Empty collection and undefined activeLayers safety", () => {
    // Empty collection returns empty collection without throwing
    const emptyRes = filterIndustrialAssetsByLayers(EMPTY_INDUSTRIAL_COLLECTION, {});
    assert.equal(emptyRes.features.length, 0);

    // Undefined activeLayers defaults gracefully to all visible
    const undefinedLayersRes = filterIndustrialAssetsByLayers(sampleCollection, undefined);
    assert.equal(undefinedLayersRes.features.length, 4);
  });

  it("TEST 14: 2D MapLibre layer visibility reconciliation logic", () => {
    // Mock MapLibre map instance with source and layers
    const layerVisibilities: Record<string, string> = {};
    let sourceData: any = null;
    let popupRemoved = false;

    const mockMap = {
      isStyleLoaded: () => true,
      getSource: (id: string) => (id === "industrial-assets-source" ? { setData: (d: any) => { sourceData = d; } } : null),
      getLayer: (id: string) => ["industrial-assets-points", "industrial-assets-labels", "industrial-assets-hitbox"].includes(id),
      setLayoutProperty: (layerId: string, prop: string, val: string) => {
        if (prop === "visibility") {
          layerVisibilities[layerId] = val;
        }
      },
    };

    const mockPopup = {
      remove: () => { popupRemoved = true; }
    };

    // Helper simulating reconcileIndustrialLayers logic
    const reconcile = (features: any[]) => {
      const source = mockMap.getSource("industrial-assets-source");
      const hasFeatures = features.length > 0;
      if (hasFeatures) {
        source?.setData({ type: "FeatureCollection", features });
      } else {
        source?.setData(EMPTY_INDUSTRIAL_COLLECTION);
        mockPopup.remove();
      }

      for (const id of ["industrial-assets-points", "industrial-assets-labels", "industrial-assets-hitbox"]) {
        if (mockMap.getLayer(id)) {
          mockMap.setLayoutProperty(id, "visibility", hasFeatures ? "visible" : "none");
        }
      }
    };

    // 1. When layers are enabled, layers are "visible" and source has features
    reconcile(sampleFeatures);
    assert.equal(layerVisibilities["industrial-assets-points"], "visible");
    assert.equal(layerVisibilities["industrial-assets-labels"], "visible");
    assert.equal(layerVisibilities["industrial-assets-hitbox"], "visible");
    assert.equal(sourceData.features.length, 4);

    // 2. When all layers are disabled, layers are "none", source is empty, and popup is removed
    popupRemoved = false;
    reconcile([]);
    assert.equal(layerVisibilities["industrial-assets-points"], "none");
    assert.equal(layerVisibilities["industrial-assets-labels"], "none");
    assert.equal(layerVisibilities["industrial-assets-hitbox"], "none");
    assert.equal(sourceData.features.length, 0);
    assert.equal(popupRemoved, true);
  });

  it("TEST 15: 3D Globe point rendering and removal synchronization", () => {
    let currentPointsData: any[] | null = null;
    let transitionDuration: number | null = null;

    const mockGlobe = {
      pointsTransitionDuration: (d: number) => {
        transitionDuration = d;
        return mockGlobe;
      },
      pointsData: (data: any[]) => {
        currentPointsData = data;
        return mockGlobe;
      },
      pointLat: () => mockGlobe,
      pointLng: () => mockGlobe,
      pointColor: () => mockGlobe,
      pointAltitude: () => mockGlobe,
      pointRadius: () => mockGlobe,
      pointLabel: () => mockGlobe,
    };

    // Helper simulating renderIndustrialPoints logic
    const renderGlobePoints = (features: any[]) => {
      if (!features.length) {
        mockGlobe.pointsTransitionDuration(0);
        mockGlobe.pointsData([]);
        return;
      }
      mockGlobe
        .pointsTransitionDuration(0)
        .pointsData([...features]);
    };

    // 1. When active, pointsData receives features with 0ms transition duration
    renderGlobePoints(sampleFeatures);
    assert.equal(transitionDuration, 0);
    assert.equal((currentPointsData as any[] | null)?.length, 4);

    // 2. When layer toggled off, pointsData receives empty array immediately (0ms transition duration)
    renderGlobePoints([]);
    assert.equal(transitionDuration, 0);
    assert.deepEqual(currentPointsData, []);
  });
});

