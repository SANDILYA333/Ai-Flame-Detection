export interface Incident {
  id: string;
  title: string;
  category: 'accidental' | 'routine' | 'glint' | 'crop' | 'wildfire' | 'coal';
  confidence: number;
  subtitle: string;
  facility: string;
  state: string;
  sector: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  lat: number;
  lon: number;
  tempK: number;
  frpMw: number;
  areaM2: number;
  windSpeed: string;
  windDir: string;
  chemicals: string[];
  unNumber: string;
  evacRadiusKm: number;
  dayIndex: number; // 0 to 29 (30 days timeline)
  caseId?: string;
}

export interface FacilityMarker {
  name: string;
  category: string;
  lat: number;
  lon: number;
  type: string;
  capacityMw?: number;
}

export interface EmergencyResponder {
  id: string;
  type: 'hospital' | 'fire_station' | 'ndrf';
  name: string;
  city: string;
  state: string;
  lat: number;
  lon: number;
  beds?: number;
  tenders?: number;
  phone: string;
  hazmat_ready?: boolean;
}

export interface ActiveFilters {
  state: string | null;
  sector: string | null;
  severity: string | null;
  category: 'accidental' | 'routine' | 'glint' | 'crop' | 'wildfire' | 'coal' | null;
  searchQuery?: string;
  dayFilterActive?: boolean;
}

export interface DatabaseLayers {
  showFacilities: boolean;
  showEmergencyFire: boolean;
  showHospitals: boolean;
  showPlumes: boolean;
  showEvacPerimeter: boolean;
  showAccidental: boolean;
  showRoutine: boolean;
  showWildfire: boolean;
  showCrop: boolean;
  showCoal: boolean;
  showGlint: boolean;
}
