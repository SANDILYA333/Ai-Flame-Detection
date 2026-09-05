import type { ThermalEvent } from "../../types/event.ts";

export interface GeoLocationOption {
  id: string;
  name: string;
  count?: number;
}

export interface StateGeoBounds {
  center: [number, number]; // [lat, lng]
  zoom: number;
  bbox: [number, number, number, number]; // [minLat, minLon, maxLat, maxLon]
}

// Canonical Indian State Coordinates & Bounding Boxes
export const STATE_BOUNDS_MAP: Record<string, StateGeoBounds> = {
  Telangana: {
    center: [17.85, 79.15],
    zoom: 7.2,
    bbox: [15.8, 77.2, 19.9, 81.3],
  },
  Gujarat: {
    center: [22.3, 71.2],
    zoom: 6.8,
    bbox: [20.1, 68.1, 24.7, 74.5],
  },
  Odisha: {
    center: [20.5, 84.4],
    zoom: 6.8,
    bbox: [17.8, 81.4, 22.6, 87.5],
  },
  "Madhya Pradesh": {
    center: [23.5, 78.5],
    zoom: 6.5,
    bbox: [21.1, 74.0, 26.9, 82.8],
  },
  Punjab: {
    center: [31.1, 75.4],
    zoom: 7.5,
    bbox: [29.5, 73.8, 32.5, 76.9],
  },
  Jharkhand: {
    center: [23.6, 85.3],
    zoom: 7.2,
    bbox: [21.9, 83.3, 25.3, 87.9],
  },
  "Andhra Pradesh": {
    center: [15.9, 79.7],
    zoom: 6.8,
    bbox: [12.6, 76.7, 19.1, 84.8],
  },
  Rajasthan: {
    center: [26.9, 73.8],
    zoom: 6.2,
    bbox: [23.0, 69.5, 30.2, 78.3],
  },
  "West Bengal": {
    center: [23.5, 87.8],
    zoom: 6.8,
    bbox: [21.5, 85.8, 27.2, 89.9],
  },
  Maharashtra: {
    center: [19.5, 76.0],
    zoom: 6.5,
    bbox: [15.6, 72.6, 22.0, 80.9],
  },
  Assam: {
    center: [26.2, 92.9],
    zoom: 7.0,
    bbox: [24.1, 89.7, 28.0, 96.0],
  },
  Karnataka: {
    center: [15.3, 75.7],
    zoom: 6.8,
    bbox: [11.5, 74.0, 18.5, 78.6],
  },
  TamilNadu: {
    center: [11.1, 78.6],
    zoom: 6.8,
    bbox: [8.1, 76.2, 13.6, 80.3],
  },
};

export const DEFAULT_INDIA_VIEW: StateGeoBounds = {
  center: [21.5, 79.5],
  zoom: 5.0,
  bbox: [6.5, 68.0, 37.5, 97.5],
};

/**
 * Derives state name from location string or coordinates
 */
export function deriveStateFromLocation(locationName?: string, lat?: number, lon?: number): string | null {
  if (!locationName) return null;
  const loc = locationName.toLowerCase();

  if (loc.includes("telangana") || loc.includes("hyderabad") || loc.includes("nalgonda") || loc.includes("adilabad") || loc.includes("warangal") || loc.includes("karimnagar") || loc.includes("khammam") || loc.includes("nizamabad")) {
    return "Telangana";
  }
  if (loc.includes("gujarat") || loc.includes("jamnagar") || loc.includes("surat") || loc.includes("hazira") || loc.includes("porbandar") || loc.includes("vadodara") || loc.includes("mundra")) {
    return "Gujarat";
  }
  if (loc.includes("odisha") || loc.includes("angul") || loc.includes("paradip") || loc.includes("talcher") || loc.includes("rourkela")) {
    return "Odisha";
  }
  if (loc.includes("madhya pradesh") || loc.includes(" mp") || loc.includes(", mp") || loc.includes("singrauli") || loc.includes("umaria")) {
    return "Madhya Pradesh";
  }
  if (loc.includes("punjab") || loc.includes("ludhiana") || loc.includes("amritsar") || loc.includes("bathinda") || loc.includes("jalandhar")) {
    return "Punjab";
  }
  if (loc.includes("jharkhand") || loc.includes("bokaro") || loc.includes("jamshedpur") || loc.includes("dhanbad") || loc.includes("ranchi")) {
    return "Jharkhand";
  }
  if (loc.includes("andhra pradesh") || loc.includes("visakhapatnam") || loc.includes("vizag") || loc.includes("vijayawada")) {
    return "Andhra Pradesh";
  }
  if (loc.includes("rajasthan") || loc.includes("thar") || loc.includes("jaipur") || loc.includes("jodhpur") || loc.includes("barmer")) {
    return "Rajasthan";
  }
  if (loc.includes("west bengal") || loc.includes("haldia") || loc.includes("kolkata") || loc.includes("durgapur") || loc.includes("asansol")) {
    return "West Bengal";
  }
  if (loc.includes("maharashtra") || loc.includes("mumbai") || loc.includes("pune") || loc.includes("nagpur") || loc.includes("tarapur")) {
    return "Maharashtra";
  }
  if (loc.includes("assam") || loc.includes("baghjan") || loc.includes("digboi") || loc.includes("guwahati")) {
    return "Assam";
  }

  // Fallback spatial bounding box checks if coordinates available
  if (lat !== undefined && lon !== undefined) {
    for (const [stateName, bounds] of Object.entries(STATE_BOUNDS_MAP)) {
      const [minLat, minLon, maxLat, maxLon] = bounds.bbox;
      if (lat >= minLat && lat <= maxLat && lon >= minLon && lon <= maxLon) {
        return stateName;
      }
    }
  }

  return null;
}

/**
 * Derives district / city name from location string
 */
export function deriveDistrictFromLocation(locationName?: string): string | null {
  if (!locationName) return null;
  const loc = locationName.toLowerCase();

  const knownDistricts = [
    "Nalgonda",
    "Adilabad",
    "Hyderabad",
    "Warangal",
    "Karimnagar",
    "Khammam",
    "Nizamabad",
    "Jamnagar",
    "Surat",
    "Porbandar",
    "Vadodara",
    "Mundra",
    "Angul",
    "Paradip",
    "Talcher",
    "Singrauli",
    "Umaria",
    "Ludhiana",
    "Bokaro",
    "Visakhapatnam",
    "Haldia",
    "Mumbai",
    "Thar Desert",
    "Basra",
    "Rotterdam",
    "Permian Basin",
    "Riau",
    "Ekofisk",
    "Athabasca",
  ];

  for (const d of knownDistricts) {
    if (loc.includes(d.toLowerCase())) {
      return d;
    }
  }

  const parts = locationName.split(",");
  if (parts.length > 1) {
    return parts[0].trim();
  }

  return null;
}

/**
 * Derives country name from location string or default to India
 */
export function deriveCountryFromLocation(locationName?: string): string {
  if (!locationName) return "India";
  const loc = locationName.toLowerCase();

  if (loc.includes("iraq")) return "Iraq";
  if (loc.includes("netherlands")) return "Netherlands";
  if (loc.includes("usa") || loc.includes("united states") || loc.includes("texas")) return "USA";
  if (loc.includes("indonesia") || loc.includes("sumatra")) return "Indonesia";
  if (loc.includes("persian gulf")) return "Persian Gulf";
  if (loc.includes("north sea") || loc.includes("norway")) return "North Sea";
  if (loc.includes("canada") || loc.includes("alberta")) return "Canada";

  return "India";
}

/**
 * Filters a list of ThermalEvents by geographic criteria
 */
export function filterEventsByLocation(
  events: ThermalEvent[],
  country: string = "ALL",
  state: string = "ALL",
  district: string = "ALL"
): ThermalEvent[] {
  return events.filter((evt) => {
    // 1. Country Filter
    if (country !== "ALL") {
      const evtCountry = deriveCountryFromLocation(evt.location_name);
      if (evtCountry.toLowerCase() !== country.toLowerCase()) {
        return false;
      }
    }

    // 2. State Filter
    if (state !== "ALL") {
      const evtState = deriveStateFromLocation(evt.location_name, evt.latitude, evt.longitude);
      if (!evtState || evtState.toLowerCase() !== state.toLowerCase()) {
        return false;
      }
    }

    // 3. District Filter
    if (district !== "ALL") {
      const evtDistrict = deriveDistrictFromLocation(evt.location_name);
      const locStr = (evt.location_name || "").toLowerCase();
      const distMatch =
        (evtDistrict && evtDistrict.toLowerCase() === district.toLowerCase()) ||
        locStr.includes(district.toLowerCase());
      if (!distMatch) {
        return false;
      }
    }

    return true;
  });
}

/**
 * Extracts available Countries, States, and Districts with event counts from the catalog
 */
export function extractAvailableLocations(events: ThermalEvent[]) {
  const countriesMap = new Map<string, number>();
  const statesMap = new Map<string, number>();
  const districtsMap = new Map<string, { count: number; state: string }>();

  events.forEach((evt) => {
    const country = deriveCountryFromLocation(evt.location_name);
    countriesMap.set(country, (countriesMap.get(country) || 0) + 1);

    const state = deriveStateFromLocation(evt.location_name, evt.latitude, evt.longitude);
    if (state) {
      statesMap.set(state, (statesMap.get(state) || 0) + 1);
    }

    const district = deriveDistrictFromLocation(evt.location_name);
    if (district) {
      const current = districtsMap.get(district) || { count: 0, state: state || "India" };
      districtsMap.set(district, {
        count: current.count + 1,
        state: state || current.state,
      });
    }
  });

  const countries: GeoLocationOption[] = Array.from(countriesMap.entries())
    .map(([name, count]) => ({ id: name, name, count }))
    .sort((a, b) => b.count! - a.count!);

  const states: GeoLocationOption[] = Array.from(statesMap.entries())
    .map(([name, count]) => ({ id: name, name, count }))
    .sort((a, b) => b.count! - a.count!);

  const districts: (GeoLocationOption & { state: string })[] = Array.from(districtsMap.entries())
    .map(([name, data]) => ({ id: name, name, count: data.count, state: data.state }))
    .sort((a, b) => b.count! - a.count!);

  return { countries, states, districts };
}
