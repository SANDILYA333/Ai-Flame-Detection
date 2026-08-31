import { useState, useEffect, useMemo } from 'react';
import { MinimalMap, type ForestReserve } from './components/MinimalMap';
import { LayersPanel } from './components/LayersPanel';
import { LayerInfoModal } from './components/LayerInfoModal';
import { TimeRangeControls, type TimeRange } from './components/TimeRangeControls';
import { XAIEvidenceCard } from './components/XAIEvidenceCard';
import { InteractiveClassifierModal } from './components/InteractiveClassifierModal';
import { LAYER_DEFINITIONS, type LayerDefinition } from './layersConfig';
import type { Incident, ActiveFilters, FacilityMarker, EmergencyResponder } from './types';
import { 
  Flame, 
  FileText, 
  Play, 
  Pause, 
  X, 
  ShieldAlert, 
  Hospital, 
  Download,
  CheckCircle2,
  Search,
  Filter,
  RefreshCw,
  AlertTriangle,
  SlidersHorizontal,
  Sparkles
} from 'lucide-react';

const SEED_INCIDENTS: Incident[] = [
  {
    id: 'INC-001',
    caseId: 'HIST_DISASTER_VIZAG_2020',
    title: 'Accidental fire',
    category: 'accidental',
    confidence: 96,
    subtitle: 'Petrochem tank · FRP 11.5x baseline',
    facility: 'LG Polymers / HPCL Visakhapatnam Petrochem SEZ',
    state: 'Andhra Pradesh',
    sector: 'Refinery & Petrochemicals',
    severity: 'high',
    lat: 17.7607,
    lon: 83.2185,
    tempK: 1180,
    frpMw: 142.5,
    areaM2: 42.8,
    windSpeed: '18.5 km/h',
    windDir: 'SE → NW (315°)',
    chemicals: ['Styrene Monomer (UN2055)', 'Benzene (UN1114)', 'Naphtha (UN1268)'],
    unNumber: 'UN 2055',
    evacRadiusKm: 3.0,
    dayIndex: 21,
  },
  {
    id: 'INC-002',
    caseId: 'HIST_DISASTER_JAIPUR_2009',
    title: 'Petroleum depot explosion',
    category: 'accidental',
    confidence: 98,
    subtitle: 'Bulk terminal · FRP 111x baseline',
    facility: 'IOCL Bulk Petroleum Terminal, Sitapura',
    state: 'Rajasthan',
    sector: 'Refinery & Petrochemicals',
    severity: 'high',
    lat: 26.7925,
    lon: 75.8272,
    tempK: 1250,
    frpMw: 890.5,
    areaM2: 2800.0,
    windSpeed: '16.2 km/h',
    windDir: 'SW → NE (45°)',
    chemicals: ['Motor Spirit (Petrol)', 'Diesel', 'Kerosene (UN1268)'],
    unNumber: 'UN 1268',
    evacRadiusKm: 5.0,
    dayIndex: 14,
  },
  {
    id: 'INC-003',
    caseId: 'HIST_ROUTINE_JAMNAGAR_FLARE',
    title: 'Persistent flare stack',
    category: 'routine',
    confidence: 97,
    subtitle: 'Reliance Jamnagar FCCU unit',
    facility: 'Reliance Jamnagar Refinery Complex',
    state: 'Gujarat',
    sector: 'Refinery & Petrochemicals',
    severity: 'low',
    lat: 22.3556,
    lon: 69.8653,
    tempK: 1650,
    frpMw: 44.0,
    areaM2: 18.5,
    windSpeed: '15.4 km/h',
    windDir: 'SW → NE (45°)',
    chemicals: ['Hydrocarbons (LPG/Methane)', 'SO2'],
    unNumber: 'UN 1075',
    evacRadiusKm: 0.5,
    dayIndex: 21,
  },
  {
    id: 'INC-004',
    caseId: 'HIST_ROUTINE_TATA_STEEL_BLAST',
    title: 'Blast furnace operations',
    category: 'routine',
    confidence: 94,
    subtitle: 'Continuous smelter · baseline matched',
    facility: 'Tata Steel Jamshedpur Works',
    state: 'Jharkhand',
    sector: 'Iron & Steel',
    severity: 'low',
    lat: 22.8046,
    lon: 86.2029,
    tempK: 1400,
    frpMw: 24.1,
    areaM2: 45.0,
    windSpeed: '7.5 km/h',
    windDir: 'W → E (90°)',
    chemicals: ['Liquid Molten Iron', 'Blast Furnace Gas (CO)'],
    unNumber: 'UN 1910',
    evacRadiusKm: 0.2,
    dayIndex: 10,
  },
  {
    id: 'INC-005',
    caseId: 'HIST_MINING_JHARIA_COAL_FIRE',
    title: 'Coal seam smoldering',
    category: 'coal',
    confidence: 91,
    subtitle: 'Subsurface seam · mining zone',
    facility: 'BCCL Jharia Coalfield Block IV',
    state: 'Jharkhand',
    sector: 'Coal Mining',
    severity: 'medium',
    lat: 23.7431,
    lon: 86.4172,
    tempK: 710,
    frpMw: 28.5,
    areaM2: 450.0,
    windSpeed: '8.5 km/h',
    windDir: 'E → W (270°)',
    chemicals: ['CO', 'Methane (CH4)', 'Sulfur Dioxide (SO2)'],
    unNumber: 'UN 1361',
    evacRadiusKm: 1.2,
    dayIndex: 18,
  },
  {
    id: 'INC-006',
    caseId: 'HIST_AGRO_PUNJAB_STUBBLE_2023',
    title: 'Crop stubble burning',
    category: 'crop',
    confidence: 93,
    subtitle: 'Rural belt · seasonal pattern',
    facility: 'Sangrur Agricultural Paddy Belt',
    state: 'Punjab',
    sector: 'Agriculture',
    severity: 'medium',
    lat: 30.2458,
    lon: 75.8421,
    tempK: 820,
    frpMw: 36.8,
    areaM2: 210.0,
    windSpeed: '14.0 km/h',
    windDir: 'NW → SE (120°)',
    chemicals: ['Biomass Smoke (PM2.5, CO, VOCs)'],
    unNumber: 'N/A',
    evacRadiusKm: 0.8,
    dayIndex: 5,
  },
  {
    id: 'INC-007',
    caseId: 'HIST_WILDFIRE_SIMLIPAL_2021',
    title: 'Forest canopy wildfire',
    category: 'wildfire',
    confidence: 95,
    subtitle: 'Protected biosphere reserve',
    facility: 'Simlipal Biosphere Reserve Core',
    state: 'Odisha',
    sector: 'Forestry',
    severity: 'medium',
    lat: 21.8653,
    lon: 86.3475,
    tempK: 680,
    frpMw: 310.0,
    areaM2: 45000.0,
    windSpeed: '14.8 km/h',
    windDir: 'NW → SE (135°)',
    chemicals: ['Dry Sal Leaf Biomass (PM2.5)'],
    unNumber: 'N/A',
    evacRadiusKm: 0.0,
    dayIndex: 8,
  },
  {
    id: 'INC-008',
    title: 'Solar glint reflection',
    category: 'glint',
    confidence: 42,
    subtitle: 'Photovoltaic reflection · false positive',
    facility: 'Bhadla Solar Park Boundary Sector 4',
    state: 'Rajasthan',
    sector: 'Solar & Renewable',
    severity: 'low',
    lat: 27.538,
    lon: 71.916,
    tempK: 330,
    frpMw: 1.2,
    areaM2: 150.0,
    windSpeed: '9.0 km/h',
    windDir: 'NW → SE (135°)',
    chemicals: ['None (Photovoltaic Optical Glint)'],
    unNumber: 'N/A',
    evacRadiusKm: 0.0,
    dayIndex: 12,
  }
];

export default function App() {
  const [incidents, setIncidents] = useState<Incident[]>(SEED_INCIDENTS);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(SEED_INCIDENTS[0]);
  const [showDossierDrawer, setShowDossierDrawer] = useState<boolean>(false);
  const [showClassifierModal, setShowClassifierModal] = useState<boolean>(false);
  const [isExportingPdf, setIsExportingPdf] = useState<boolean>(false);
  const [showFilterModal, setShowFilterModal] = useState<boolean>(false);
  const [isRefreshingFeed, setIsRefreshingFeed] = useState<boolean>(false);

  // Time Range Filter State (Reference image aesthetic)
  const [selectedTimeRange, setSelectedTimeRange] = useState<TimeRange>('7d');

  // Metadata Inspector Modal State
  const [inspectedLayer, setInspectedLayer] = useState<LayerDefinition | null>(null);

  // Central Active Layers State (12 Exact Datasets)
  const [activeLayers, setActiveLayers] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    LAYER_DEFINITIONS.forEach(l => {
      initial[l.id] = l.defaultEnabled;
    });
    return initial;
  });

  // Database Datasets
  const [facilities, setFacilities] = useState<FacilityMarker[]>([]);
  const [emergencyResponders, setEmergencyResponders] = useState<EmergencyResponder[]>([]);
  const [forestReserves, setForestReserves] = useState<ForestReserve[]>([]);
  const [liveFirmsHotspots, setLiveFirmsHotspots] = useState<any[]>([]);

  // Search and Filters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filters, setFilters] = useState<ActiveFilters>({
    state: null,
    sector: null,
    severity: null,
    category: null,
    dayFilterActive: false,
  });

  // Timeline (Day 1 to 30)
  const [currentDay, setCurrentDay] = useState<number>(21);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Load datasets from backend APIs
  useEffect(() => {
    // 1. Fetch 1,704 Master Industrial Facilities
    fetch('/api/facilities')
      .then(res => res.json())
      .then(data => {
        if (data.features) {
          const mapped: FacilityMarker[] = data.features.map((f: any) => ({
            name: f.properties?.name || 'Industrial Facility',
            category: f.properties?.category || f.properties?.type || 'Industrial',
            type: f.properties?.type || 'Factory',
            lat: f.geometry?.coordinates[1],
            lon: f.geometry?.coordinates[0],
            capacityMw: f.properties?.capacity_mw,
          })).filter((f: any) => f.lat && f.lon);
          setFacilities(mapped);
        }
      })
      .catch(() => {});

    // 2. Fetch Emergency Services Database
    fetch('/api/emergency-responders')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setEmergencyResponders(data);
        }
      })
      .catch(() => {});

    // 3. Fetch Forest Reserves
    fetch('/api/forest-reserves')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data) && data.length > 0) {
          setForestReserves(data);
        }
      })
      .catch(() => {});
  }, []);

  // Fetch Live NASA FIRMS API Stream when active
  useEffect(() => {
    if (activeLayers['nasa-firms-live-api']) {
      fetch('/api/live-firms')
        .then(res => res.json())
        .then(data => {
          if (data.features && Array.isArray(data.features)) {
            setLiveFirmsHotspots(data.features);
          }
        })
        .catch(() => {});
    }
  }, [activeLayers['nasa-firms-live-api']]);

  // Available Filter Options
  const availableStates = useMemo(() => {
    const states = Array.from(new Set(incidents.map(i => i.state).filter(Boolean)));
    return ['All States', ...states.sort()];
  }, [incidents]);

  const availableSectors = useMemo(() => {
    const sectors = Array.from(new Set(incidents.map(i => i.sector).filter(Boolean)));
    return ['All Sectors', ...sectors.sort()];
  }, [incidents]);

  // Load telemetry from backend API
  const fetchTelemetry = () => {
    setIsRefreshingFeed(true);
    fetch('/api/thermal-events?limit=1400')
      .then(res => res.json())
      .then(data => {
        if (data.features && data.features.length > 0) {
          const mapped: Incident[] = data.features.map((f: any, idx: number) => {
            const p = f.properties;
            const cId = p.predicted_class_id;
            let cat: Incident['category'] = 'routine';
            let title = 'Kiln operation';
            let sev: Incident['severity'] = 'low';

            if (cId === 1) {
              cat = 'accidental';
              title = 'Accidental fire';
              sev = 'high';
            } else if (cId === 0) {
              cat = 'routine';
              title = idx % 3 === 0 ? 'Kiln operation' : 'Persistent flare';
              sev = 'low';
            } else if (cId === 2) {
              cat = 'wildfire';
              title = 'Forest wildfire';
              sev = 'medium';
            } else if (cId === 3) {
              cat = 'crop';
              title = 'Crop burning';
              sev = 'medium';
            } else if (cId === 4) {
              cat = 'coal';
              title = 'Coal smoldering';
              sev = 'medium';
            } else if (cId === 5) {
              cat = 'glint';
              title = 'Solar glint';
              sev = 'low';
            }

            let subtitle = `${p.nearest_facility || 'Industrial asset'} · FRP 4.2x baseline`;
            if (cat === 'routine') subtitle = `${p.nearest_facility || 'Industrial plant'} · routine flare`;
            if (cat === 'crop') subtitle = 'Rural belt · seasonal pattern';
            if (cat === 'glint') subtitle = 'Low confidence · false positive';
            if (cat === 'wildfire') subtitle = 'Protected canopy · biomass';
            if (cat === 'coal') subtitle = 'Subsurface seam · mining zone';

            let sector = 'Refinery & Petrochemicals';
            if (cat === 'coal') sector = 'Coal Mining';
            if (cat === 'crop') sector = 'Agriculture';
            if (cat === 'wildfire') sector = 'Forestry';
            if (cat === 'glint') sector = 'Solar & Renewable';
            if (idx % 4 === 1) sector = 'Iron & Steel';

            return {
              id: p.event_id || `INC-${idx + 1}`,
              caseId: p.event_id,
              title,
              category: cat,
              confidence: Math.round(p.confidence_score || 94),
              subtitle,
              facility: p.nearest_facility || p.site_name || 'Industrial Facility',
              state: p.region_split || 'India',
              sector,
              severity: sev,
              lat: f.geometry.coordinates[1],
              lon: f.geometry.coordinates[0],
              tempK: Math.round(p.estimated_emitter_temp_k || 1200),
              frpMw: parseFloat(p.frp_mw?.toFixed(1) || '25.0'),
              areaM2: parseFloat(p.estimated_emitter_area_m2?.toFixed(1) || '40.0'),
              windSpeed: '14.5 km/h',
              windDir: 'SW → NE (45°)',
              chemicals: ['Styrene Monomer (UN2055)', 'Benzene (UN1114)', 'SO2 (UN1079)'],
              unNumber: 'UN 2055',
              evacRadiusKm: cat === 'accidental' ? 2.8 : 0.4,
              dayIndex: (idx % 30) + 1
            };
          });

          const combined = [...SEED_INCIDENTS, ...mapped.filter(m => !SEED_INCIDENTS.some(s => s.id === m.id))];
          setIncidents(combined);
          setSelectedIncident(combined[0]);
        }
      })
      .catch(() => {
        setIncidents(SEED_INCIDENTS);
        setSelectedIncident(SEED_INCIDENTS[0]);
      })
      .finally(() => {
        setIsRefreshingFeed(false);
      });
  };

  useEffect(() => {
    fetchTelemetry();
  }, []);

  // Playback timer for timeline
  useEffect(() => {
    let interval: any = null;
    if (isPlaying) {
      interval = setInterval(() => {
        setCurrentDay((prev) => (prev >= 30 ? 1 : prev + 1));
      }, 1200);
    }
    return () => clearInterval(interval);
  }, [isPlaying]);

  // Robust Filter Pipeline
  const filteredIncidents = useMemo(() => {
    return incidents.filter((inc) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesFacility = inc.facility.toLowerCase().includes(q);
        const matchesTitle = inc.title.toLowerCase().includes(q);
        const matchesState = inc.state.toLowerCase().includes(q);
        const matchesSector = inc.sector.toLowerCase().includes(q);
        const matchesId = inc.id.toLowerCase().includes(q);
        if (!matchesFacility && !matchesTitle && !matchesState && !matchesSector && !matchesId) {
          return false;
        }
      }

      if (filters.category && inc.category !== filters.category) return false;
      if (filters.state && filters.state !== 'All States' && inc.state !== filters.state) return false;
      if (filters.sector && filters.sector !== 'All Sectors' && inc.sector !== filters.sector) return false;
      if (filters.severity && filters.severity !== 'All Severities' && inc.severity !== filters.severity) return false;
      if ((filters.dayFilterActive || isPlaying) && inc.dayIndex !== currentDay) return false;

      return true;
    });
  }, [incidents, searchQuery, filters, currentDay, isPlaying]);

  const activeAlertsCount = useMemo(() => {
    return incidents.filter((i) => i.category === 'accidental' || i.severity === 'high').length;
  }, [incidents]);

  const handleExportPdf = () => {
    setIsExportingPdf(true);
    const caseId = selectedIncident?.caseId || 'HIST_DISASTER_VIZAG_2020';
    window.open(`/api/incident-dossier/${caseId}`, '_blank');
    setTimeout(() => {
      setIsExportingPdf(false);
    }, 1200);
  };

  const handleToggleCategory = (cat: Incident['category'] | null) => {
    setFilters(prev => ({
      ...prev,
      category: prev.category === cat ? null : cat
    }));
  };

  const handleResetFilters = () => {
    setFilters({
      state: null,
      sector: null,
      severity: null,
      category: null,
      dayFilterActive: false,
    });
    setSearchQuery('');
  };

  // Central Layer Toggle Handler
  const handleToggleLayer = (layerId: string) => {
    setActiveLayers(prev => ({
      ...prev,
      [layerId]: !prev[layerId]
    }));
  };

  const handleClassifiedEventCreated = (classifiedData: any) => {
    const c = classifiedData.classification;
    const p = classifiedData.physical_characterization;
    const s = classifiedData.spatial_attribution;
    const newInc: Incident = {
      id: `INC-SIM-${Date.now().toString().slice(-4)}`,
      caseId: 'SIMULATED_EVENT',
      title: c.predicted_class_name.replace(/_/g, ' '),
      category: c.predicted_class_id === 1 ? 'accidental' : (c.predicted_class_id === 0 ? 'routine' : (c.predicted_class_id === 2 ? 'wildfire' : (c.predicted_class_id === 3 ? 'crop' : 'coal'))),
      confidence: Math.round(c.confidence_score),
      subtitle: `${s.nearest_facility} · ${s.dist_km.toFixed(1)} km`,
      facility: s.nearest_facility,
      state: 'Classified Zone',
      sector: s.dominant_lulc,
      severity: c.predicted_class_id === 1 ? 'high' : 'medium',
      lat: classifiedData.event_coordinates[1],
      lon: classifiedData.event_coordinates[0],
      tempK: p.estimated_emitter_temp_k,
      frpMw: p.frp_mw,
      areaM2: p.estimated_emitter_area_m2,
      windSpeed: '14.2 km/h',
      windDir: 'SW → NE (45°)',
      chemicals: ['Combustion Byproducts', 'Thermal Radiation'],
      unNumber: 'UN 1993',
      evacRadiusKm: c.predicted_class_id === 1 ? 3.0 : 0.5,
      dayIndex: currentDay
    };
    setIncidents(prev => [newInc, ...prev]);
    setSelectedIncident(newInc);
  };

  return (
    <div className="h-screen w-screen bg-[#0c0d12] text-[#f3f4f6] flex flex-col font-sans select-none overflow-hidden">
      
      {/* 1. Header Bar */}
      <header className="h-14 border-b border-[#1b1e28] px-5 flex items-center justify-between bg-[#0e1017] z-20">
        
        {/* Left: Brand & Title */}
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg bg-[#271418] border border-[#441a20]">
            <Flame className="w-4 h-4 text-[#ef4444] stroke-[2.2]" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-[#f3f4f6] flex items-center gap-2">
              <span>PyroSat-AI</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#181b24] border border-[#262b3a] text-[#94a3b8]">
                v2.5
              </span>
            </h1>
            <div className="text-[10.5px] text-[#64748b]">Thermal Anomaly Intelligence & HAZMAT Dispersion</div>
          </div>
        </div>

        {/* Center: Search Input */}
        <div className="hidden md:flex items-center w-72 lg:w-96 relative">
          <Search className="w-3.5 h-3.5 text-[#64748b] absolute left-3 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search facility, state, sector..."
            className="w-full bg-[#13151c] border border-[#232734] focus:border-[#38bdf8] focus:bg-[#161822] rounded-lg pl-8 pr-7 py-1.5 text-xs text-[#f3f4f6] placeholder-[#64748b] transition-all outline-none"
          />
          {searchQuery && (
            <button 
              onClick={() => setSearchQuery('')} 
              className="absolute right-2.5 text-[#64748b] hover:text-white"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2.5">
          {/* Live NASA Feed Refresh Button */}
          <button
            onClick={fetchTelemetry}
            disabled={isRefreshingFeed}
            className="px-2.5 py-1.5 rounded-lg bg-[#161822] border border-[#262b3a] hover:bg-[#1e2333] hover:border-[#384158] text-[#cbd5e1] text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            title="Refresh Live Telemetry"
          >
            <RefreshCw className={`w-3 h-3 text-[#38bdf8] ${isRefreshingFeed ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Sync Live</span>
          </button>

          {/* Active Alerts Pill */}
          <button
            onClick={() => setFilters(f => ({ ...f, category: f.category === 'accidental' ? null : 'accidental' }))}
            className={`px-3 py-1.5 rounded-lg border text-xs font-medium tracking-wide flex items-center gap-1.5 cursor-pointer transition-all active:scale-95 ${
              filters.category === 'accidental'
                ? 'bg-[#ef4444] text-white border-[#dc2626] shadow-[0_0_12px_rgba(239,68,68,0.4)]'
                : 'bg-[#271418] border-[#441a20] text-[#f87171] hover:bg-[#34181e]'
            }`}
          >
            <AlertTriangle className="w-3 h-3" />
            <span>{activeAlertsCount} Alerts</span>
          </button>

          {/* AI Classifier Lab Modal Button */}
          <button
            onClick={() => setShowClassifierModal(true)}
            className="px-3 py-1.5 rounded-lg bg-indigo-600/20 border border-indigo-500/40 hover:bg-indigo-600/30 text-indigo-300 text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer shadow-[0_0_12px_rgba(99,102,241,0.2)] active:scale-95"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>AI Classifier Lab</span>
          </button>

          {/* Dossier Modal Button */}
          <button
            onClick={() => setShowDossierDrawer(true)}
            className="px-3 py-1.5 rounded-lg bg-[#161822] border border-[#262b3a] hover:bg-[#1e2333] hover:border-[#384158] text-[#e2e8f0] text-xs font-medium transition-colors flex items-center gap-1.5 cursor-pointer shadow-sm active:scale-95"
          >
            <FileText className="w-3.5 h-3.5 text-[#38bdf8]" />
            <span>Dossier</span>
          </button>
        </div>
      </header>

      {/* 2. Filter & Category Toolbar */}
      <div className="h-11 border-b border-[#1b1e28] px-5 flex items-center justify-between bg-[#0c0d12] overflow-x-auto gap-3">
        
        {/* Left: Category Quick Pills */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={() => handleToggleCategory(null)}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all cursor-pointer ${
              filters.category === null
                ? 'bg-[#262b3a] text-white'
                : 'text-[#8b92a4] hover:text-[#e2e8f0] hover:bg-[#161822]'
            }`}
          >
            All ({incidents.length})
          </button>

          <button
            onClick={() => handleToggleCategory('accidental')}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
              filters.category === 'accidental'
                ? 'bg-[#ef4444]/20 border border-[#ef4444] text-[#fca5a5]'
                : 'text-[#8b92a4] hover:text-[#f87171] hover:bg-[#1f1518]'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#ef4444]"></span>
            <span>Accidental</span>
          </button>

          <button
            onClick={() => handleToggleCategory('routine')}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
              filters.category === 'routine'
                ? 'bg-[#f59e0b]/20 border border-[#f59e0b] text-[#fde68a]'
                : 'text-[#8b92a4] hover:text-[#fbbf24] hover:bg-[#1a1712]'
            }`}
          >
            <span className="w-1.5 h-1.5 rotate-45 bg-[#f59e0b]"></span>
            <span>Routine Flare</span>
          </button>

          <button
            onClick={() => handleToggleCategory('wildfire')}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
              filters.category === 'wildfire'
                ? 'bg-[#10b981]/20 border border-[#10b981] text-[#a7f3d0]'
                : 'text-[#8b92a4] hover:text-[#34d399] hover:bg-[#101915]'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#10b981]"></span>
            <span>Wildfire</span>
          </button>

          <button
            onClick={() => handleToggleCategory('crop')}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
              filters.category === 'crop'
                ? 'bg-[#ea580c]/20 border border-[#ea580c] text-[#fdba74]'
                : 'text-[#8b92a4] hover:text-[#fb923c] hover:bg-[#1c1511]'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#ea580c]"></span>
            <span>Crop Stubble</span>
          </button>

          <button
            onClick={() => handleToggleCategory('coal')}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
              filters.category === 'coal'
                ? 'bg-[#a855f7]/20 border border-[#a855f7] text-[#e9d5ff]'
                : 'text-[#8b92a4] hover:text-[#c084fc] hover:bg-[#191322]'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-sm bg-[#a855f7]"></span>
            <span>Coal Mining</span>
          </button>

          <button
            onClick={() => handleToggleCategory('glint')}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
              filters.category === 'glint'
                ? 'bg-[#64748b]/20 border border-[#64748b] text-[#cbd5e1]'
                : 'text-[#8b92a4] hover:text-[#94a3b8] hover:bg-[#15171e]'
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full border border-dashed border-[#94a3b8]"></span>
            <span>Glint Rejection</span>
          </button>
        </div>

        {/* Right: Filter Chips & Filter Modal Trigger */}
        <div className="flex items-center gap-2 shrink-0">
          {filters.state && (
            <div className="px-2.5 py-0.5 rounded-full bg-[#161922] border border-[#262b3a] text-[#cbd5e1] text-xs flex items-center gap-1.5">
              <span>{filters.state}</span>
              <button 
                onClick={() => setFilters(f => ({ ...f, state: null }))}
                className="text-[#64748b] hover:text-white"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {filters.sector && (
            <div className="px-2.5 py-0.5 rounded-full bg-[#161922] border border-[#262b3a] text-[#cbd5e1] text-xs flex items-center gap-1.5">
              <span>{filters.sector}</span>
              <button 
                onClick={() => setFilters(f => ({ ...f, sector: null }))}
                className="text-[#64748b] hover:text-white"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          {filters.severity && (
            <div className="px-2.5 py-0.5 rounded-full bg-[#271418] border border-[#441a20] text-[#fca5a5] text-xs flex items-center gap-1.5">
              <span>Severity: {filters.severity}</span>
              <button 
                onClick={() => setFilters(f => ({ ...f, severity: null }))}
                className="text-[#f87171] hover:text-white"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

          <button 
            onClick={() => setShowFilterModal(true)}
            className="px-2.5 py-1 rounded-md bg-[#161822] hover:bg-[#1f2433] border border-[#262b3a] text-[#8b92a4] hover:text-[#cbd5e1] text-xs transition-colors flex items-center gap-1 cursor-pointer"
          >
            <SlidersHorizontal className="w-3 h-3 text-[#38bdf8]" />
            <span>Filter</span>
          </button>

          {(filters.state || filters.sector || filters.severity || filters.category || searchQuery) && (
            <button
              onClick={handleResetFilters}
              className="text-[11px] text-[#ef4444] hover:underline px-1 cursor-pointer"
            >
              Reset
            </button>
          )}
        </div>

      </div>

      {/* 3. Main Dashboard Body (Map + Incident Cards) */}
      <div className="flex-1 flex min-h-0 relative">
        
        {/* Left: Minimal Map Area + Floating Controls (68% width) */}
        <div className="flex-1 flex flex-col border-r border-[#1b1e28] relative">
          
          {/* Leaflet Map Viewport */}
          <div className="flex-1 w-full h-full relative">
            <MinimalMap
              incidents={filteredIncidents}
              selectedIncident={selectedIncident}
              onSelectIncident={(inc) => setSelectedIncident(inc)}
              activeLayers={activeLayers}
              facilities={facilities}
              emergencyResponders={emergencyResponders}
              forestReserves={forestReserves}
              liveFirmsHotspots={liveFirmsHotspots}
            />

            {/* FLOATING DARK GIS LAYERS PANEL (Matches Visual Reference) */}
            <LayersPanel
              layerDefinitions={LAYER_DEFINITIONS}
              activeLayers={activeLayers}
              onToggleLayer={handleToggleLayer}
              onOpenInfo={(layer) => setInspectedLayer(layer)}
            />

            {/* FLOATING TIME-RANGE CONTROLS (Top-Center over Map) */}
            <div className="absolute left-[360px] top-4 z-[400] hidden md:block">
              <TimeRangeControls
                selectedRange={selectedTimeRange}
                onSelectRange={(range) => setSelectedTimeRange(range)}
              />
            </div>

          </div>

          {/* Bottom Timeline Playback Scrubber */}
          <div className="h-12 border-t border-[#1b1e28] px-5 flex items-center justify-between bg-[#0e1017] gap-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setIsPlaying(!isPlaying)}
                className="p-1.5 rounded-lg bg-[#161822] border border-[#262b3a] hover:bg-[#1e2333] text-[#94a3b8] hover:text-white transition-all cursor-pointer"
                title={isPlaying ? 'Pause Timeline' : 'Play 30-Day Timeline'}
              >
                {isPlaying ? (
                  <Pause className="w-3.5 h-3.5 text-[#ef4444]" />
                ) : (
                  <Play className="w-3.5 h-3.5 text-[#38bdf8] fill-current ml-0.5" />
                )}
              </button>

              <button
                onClick={() => setFilters(f => ({ ...f, dayFilterActive: !f.dayFilterActive }))}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium border transition-all cursor-pointer ${
                  filters.dayFilterActive || isPlaying
                    ? 'bg-[#38bdf8]/15 border-[#38bdf8] text-[#38bdf8]'
                    : 'bg-[#161822] border-[#262b3a] text-[#8b92a4] hover:text-[#cbd5e1]'
                }`}
              >
                {filters.dayFilterActive || isPlaying ? `Day ${currentDay} Only` : 'Showing All 30 Days'}
              </button>
            </div>

            <div className="flex-1 max-w-xl relative flex items-center">
              <input
                type="range"
                min="1"
                max="30"
                value={currentDay}
                onChange={(e) => {
                  setCurrentDay(parseInt(e.target.value));
                  if (!filters.dayFilterActive) {
                    setFilters(f => ({ ...f, dayFilterActive: true }));
                  }
                }}
                className="w-full h-1 bg-[#232734] rounded-lg appearance-none cursor-pointer accent-[#38bdf8]"
              />
            </div>

            <div className="text-xs font-mono text-[#8b92a4] shrink-0">
              Day <span className="text-[#38bdf8] font-bold">{currentDay}</span> / 30
            </div>
          </div>
        </div>

        {/* Right: Incidents Sidebar List */}
        <div className="w-[360px] xl:w-[400px] flex flex-col bg-[#0e1017] p-4 overflow-y-auto">
          
          <div className="flex items-center justify-between text-xs font-medium text-[#8b92a4] mb-3">
            <span>Detected Thermal Events ({filteredIncidents.length})</span>
            {filters.category && (
              <span className="text-[11px] text-[#38bdf8] uppercase font-semibold">
                {filters.category}
              </span>
            )}
          </div>

          {/* Cards Stack */}
          <div className="space-y-2.5 flex-1 overflow-y-auto pr-1">
            {filteredIncidents.length === 0 ? (
              <div className="p-8 text-center bg-[#13151c] rounded-xl border border-[#1f232e] text-xs text-[#8b92a4] space-y-2">
                <Filter className="w-6 h-6 mx-auto text-[#64748b]" />
                <div>No thermal events match active filters</div>
                <button
                  onClick={handleResetFilters}
                  className="px-3 py-1.5 rounded-lg bg-[#1f2433] text-[#38bdf8] text-xs font-medium hover:bg-[#282f42]"
                >
                  Clear All Filters
                </button>
              </div>
            ) : (
              filteredIncidents.map((inc) => {
                const isSelected = selectedIncident?.id === inc.id;
                const isAccidental = inc.category === 'accidental';

                return (
                  <div
                    key={inc.id}
                    onClick={() => setSelectedIncident(inc)}
                    className={`p-3.5 rounded-xl transition-all cursor-pointer border ${
                      isSelected && isAccidental
                        ? 'bg-[#231215] border-[#ef4444]/80 border-l-4 shadow-[0_0_24px_rgba(239,68,68,0.2)]'
                        : isSelected
                        ? 'bg-[#181b24] border-[#38bdf8]/80 border-l-4 border-l-[#38bdf8]'
                        : 'bg-[#13151c] border-[#1f232e] hover:bg-[#171a22] hover:border-[#282e3d]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`text-sm font-semibold tracking-tight ${
                        isSelected && isAccidental ? 'text-[#fca5a5]' : isSelected ? 'text-white' : 'text-[#f3f4f6]'
                      }`}>
                        {inc.title}
                      </span>
                      <span className={`text-xs font-mono font-medium ${
                        isAccidental ? 'text-[#f87171]' : 'text-[#8b92a4]'
                      }`}>
                        {inc.confidence}%
                      </span>
                    </div>

                    <div className="text-xs text-[#8b92a4] mt-1 font-normal line-clamp-1">
                      {inc.subtitle}
                    </div>

                    <div className="flex items-center justify-between mt-2 pt-2 border-t border-[#1b1e28] text-[10.5px] text-[#64748b]">
                      <span className="line-clamp-1 max-w-[200px]">📍 {inc.facility}</span>
                      <span className="font-mono text-[#cbd5e1]">{inc.frpMw} MW</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Selected Incident Telemetry & XAI Evidence Card */}
          {selectedIncident && (
            <div className="mt-3 pt-2 border-t border-[#1b1e28] text-xs shrink-0">
              <XAIEvidenceCard 
                incident={selectedIncident} 
                onDownloadDossier={(_caseId) => handleExportPdf()} 
              />
            </div>
          )}

        </div>
      </div>

      {/* 4. Filter Selector Popover */}
      {showFilterModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-[#11131a] border border-[#262b3a] rounded-2xl p-5 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-100">
            <div className="flex items-center justify-between pb-2 border-b border-[#1f232e]">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-[#38bdf8]" />
                <h3 className="text-sm font-semibold text-white">Filter Thermal Events</h3>
              </div>
              <button 
                onClick={() => setShowFilterModal(false)}
                className="text-[#64748b] hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-[#8b92a4] font-medium">State / Region</label>
              <select
                value={filters.state || 'All States'}
                onChange={(e) => setFilters(f => ({ ...f, state: e.target.value === 'All States' ? null : e.target.value }))}
                className="w-full bg-[#161822] border border-[#262b3a] rounded-lg px-3 py-2 text-xs text-[#f3f4f6] outline-none"
              >
                {availableStates.map(st => (
                  <option key={st} value={st} className="bg-[#11131a]">{st}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-[#8b92a4] font-medium">Industrial Sector</label>
              <select
                value={filters.sector || 'All Sectors'}
                onChange={(e) => setFilters(f => ({ ...f, sector: e.target.value === 'All Sectors' ? null : e.target.value }))}
                className="w-full bg-[#161822] border border-[#262b3a] rounded-lg px-3 py-2 text-xs text-[#f3f4f6] outline-none"
              >
                {availableSectors.map(sec => (
                  <option key={sec} value={sec} className="bg-[#11131a]">{sec}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] text-[#8b92a4] font-medium">Alert Severity</label>
              <div className="grid grid-cols-4 gap-2">
                {['All Severities', 'high', 'medium', 'low'].map(sev => (
                  <button
                    key={sev}
                    onClick={() => setFilters(f => ({ ...f, severity: sev === 'All Severities' ? null : sev }))}
                    className={`py-1.5 rounded-lg border text-xs capitalize transition-all ${
                      (filters.severity === sev) || (sev === 'All Severities' && !filters.severity)
                        ? 'bg-[#38bdf8]/20 border-[#38bdf8] text-[#38bdf8] font-semibold'
                        : 'bg-[#161822] border-[#262b3a] text-[#8b92a4] hover:text-white'
                    }`}
                  >
                    {sev === 'All Severities' ? 'All' : sev}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-[#1f232e]">
              <button
                onClick={handleResetFilters}
                className="text-xs text-[#ef4444] hover:underline"
              >
                Reset All Filters
              </button>
              <button
                onClick={() => setShowFilterModal(false)}
                className="px-4 py-2 rounded-xl bg-[#38bdf8] hover:bg-[#0284c7] text-xs font-semibold text-[#0c0d12]"
              >
                Apply Filters
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 5. Slide-Out HAZMAT Dossier Modal */}
      {showDossierDrawer && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center p-4">
          <div className="w-full max-w-xl bg-[#11131a] border border-[#262b3a] rounded-2xl p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-3 border-b border-[#1f232e]">
              <div className="flex items-center gap-2.5">
                <ShieldAlert className="w-5 h-5 text-[#ef4444]" />
                <div>
                  <h3 className="text-sm font-semibold text-[#f3f4f6]">
                    Tactical First Responder HAZMAT Dossier
                  </h3>
                  <div className="text-[11px] text-[#8b92a4]">
                    Incident Ref: {selectedIncident?.id || 'INC-001'} · ISO Incident Profile
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setShowDossierDrawer(false)}
                className="text-[#64748b] hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="bg-[#161822] p-3 rounded-xl border border-[#232734] space-y-1">
              <div className="text-[11px] text-[#64748b] uppercase font-semibold tracking-wider">
                TARGET ASSET & GEOLOCATION
              </div>
              <div className="text-sm font-bold text-[#f3f4f6]">
                {selectedIncident?.facility}
              </div>
              <div className="text-xs text-[#8b92a4] font-mono">
                GPS: {selectedIncident?.lat.toFixed(4)}°N, {selectedIncident?.lon.toFixed(4)}°E ({selectedIncident?.state})
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="bg-[#161822] p-3 rounded-xl border border-[#232734] space-y-1">
                <div className="text-[11px] text-[#ef4444] font-semibold">
                  HAZMAT INVENTORY
                </div>
                <div className="text-xs text-[#cbd5e1] font-medium">
                  {selectedIncident?.chemicals.join(', ')}
                </div>
                <div className="text-[10px] text-[#64748b]">
                  UN Class: {selectedIncident?.unNumber}
                </div>
              </div>

              <div className="bg-[#161822] p-3 rounded-xl border border-[#232734] space-y-1">
                <div className="text-[11px] text-[#f59e0b] font-semibold">
                  DOWNWIND CORRIDOR
                </div>
                <div className="text-xs text-[#cbd5e1] font-medium">
                  {selectedIncident?.evacRadiusKm} km Safety Radius
                </div>
                <div className="text-[10px] text-[#64748b]">
                  Atmospheric Stability: Class D (Open-Meteo)
                </div>
              </div>
            </div>

            <div className="bg-[#161822] p-3 rounded-xl border border-[#232734] space-y-2">
              <div className="text-[11px] text-[#64748b] uppercase font-semibold tracking-wider flex items-center justify-between">
                <span>NEAREST EMERGENCY RESPONDERS</span>
                <span className="text-[#10b981] flex items-center gap-1"><CheckCircle2 className="w-3 h-3" /> Level-1 Ready</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-[#cbd5e1]">
                  <Hospital className="w-3.5 h-3.5 text-[#38bdf8]" />
                  King George Hospital Burn ICU (220 Beds)
                </span>
                <span className="font-mono text-[#38bdf8]">+91-891-2564891</span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 text-[#cbd5e1]">
                  <ShieldAlert className="w-3.5 h-3.5 text-[#ef4444]" />
                  Vizag Port & Chemical Fire Station (16 Tenders)
                </span>
                <span className="font-mono text-[#ef4444]">+91-891-2873101</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowDossierDrawer(false)}
                className="px-4 py-2 rounded-xl bg-[#161822] hover:bg-[#1e2333] border border-[#262b3a] text-xs font-medium text-[#cbd5e1]"
              >
                Close
              </button>
              <button
                onClick={handleExportPdf}
                disabled={isExportingPdf}
                className="px-4 py-2 rounded-xl bg-[#ef4444] hover:bg-[#dc2626] text-xs font-semibold text-white shadow-lg shadow-red-900/30 flex items-center gap-1.5 cursor-pointer active:scale-95 disabled:opacity-60"
              >
                <Download className={`w-3.5 h-3.5 ${isExportingPdf ? 'animate-bounce' : ''}`} />
                <span>{isExportingPdf ? 'Generating PDF...' : 'Export PDF Dossier'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. Live Anomaly Classification & Pyrometry Lab Modal */}
      <InteractiveClassifierModal
        isOpen={showClassifierModal}
        onClose={() => setShowClassifierModal(false)}
        onClassifiedEventCreated={handleClassifiedEventCreated}
      />

      {/* 7. Metadata Inspector Modal for Layers */}
      <LayerInfoModal
        layer={inspectedLayer}
        onClose={() => setInspectedLayer(null)}
      />

    </div>
  );
}
