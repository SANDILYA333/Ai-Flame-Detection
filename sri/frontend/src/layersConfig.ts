export interface LayerMetadata {
  datasetName: string;
  provider: string;
  satellites?: string[];
  sensor?: string;
  resolution?: string;
  dataType: string;
  coverage: string;
  mode: string;
  source: string;
  recordCount?: string | number;
  description: string;
  regulatorsOrSponsors?: string;
}

export type LayerCategory = 
  | 'SATELLITE / THERMAL' 
  | 'INDUSTRIAL ASSETS' 
  | 'HAZARD / VULNERABILITY' 
  | 'RESPONSE INFRASTRUCTURE' 
  | 'GROUND TRUTH / AI' 
  | 'GEOSPATIAL / ENVIRONMENT';

export interface LayerDefinition {
  id: string;
  name: string;
  subtitle: string;
  category: LayerCategory;
  iconType: 'satellite' | 'radio' | 'factory' | 'zap' | 'fuel' | 'anvil' | 'hazard' | 'history' | 'emergency' | 'database' | 'map' | 'trees';
  status: 'LIVE' | 'LOADED' | 'STATIC' | 'API';
  statusColor: string;
  defaultEnabled: boolean;
  metadata: LayerMetadata;
}

export const LAYER_DEFINITIONS: LayerDefinition[] = [
  // 1. SATELLITE / THERMAL
  {
    id: 'nasa-firms-viirs',
    name: 'NASA FIRMS VIIRS',
    subtitle: 'NOAA-20 / Suomi-NPP • 375m Archive & NRT',
    category: 'SATELLITE / THERMAL',
    iconType: 'satellite',
    status: 'LOADED',
    statusColor: '#10b981',
    defaultEnabled: true,
    metadata: {
      datasetName: 'NASA FIRMS VIIRS Satellite Thermal Telemetry Database',
      provider: 'NASA Earth Observing System Data and Information System (EOSDIS)',
      satellites: ['NOAA-20 (JPSS-1)', 'Suomi-NPP'],
      sensor: 'VIIRS (Visible Infrared Imaging Radiometer Suite)',
      resolution: '375 m (I-Bands: I4 MWIR 3.74 µm, I5 LWIR 11.45 µm)',
      dataType: 'Calibrated Brightness Temperature (K) & Fire Radiative Power (FRP in MW)',
      coverage: 'Indian Subcontinent & Regional Overpasses (68°E–97.5°E, 6.5°N–37.5°N)',
      mode: 'Historical Archive (4,559,862 Detections) & Daily NRT Stream',
      source: 'NASA LANCE / FIRMS Active Fire Database',
      recordCount: '4,559,862 Rows (~415 MB)',
      description: 'Authoritative spaceborne thermal radiometry dataset capturing hot combustion emitters across India with day and night orbits.'
    }
  },
  {
    id: 'nasa-firms-live-api',
    name: 'NASA FIRMS LIVE FEED',
    subtitle: 'NASA FIRMS API • Real-Time Satellite Stream',
    category: 'SATELLITE / THERMAL',
    iconType: 'radio',
    status: 'LIVE',
    statusColor: '#00f0ff',
    defaultEnabled: false,
    metadata: {
      datasetName: 'NASA FIRMS Near-Real-Time REST API Feed',
      provider: 'NASA Goddard Space Flight Center / LANCE',
      satellites: ['Suomi-NPP NRT', 'NOAA-20 NRT'],
      sensor: 'VIIRS 375m NRT Sensor Stream',
      resolution: '375 m Nominal Spatial Footprint',
      dataType: 'Live Unmixed Thermal Hotspot Coordinate Stream with Planck Inversion',
      coverage: 'India Real-Time Bounding Box [68, 6.5, 97.5, 37.5]',
      mode: 'Dynamic HTTP REST API Polling (Last 24h Telemetry)',
      source: 'https://firms.modaps.eosdis.nasa.gov/api/area',
      recordCount: 'Dynamic Live Stream (Real-Time Ingestion)',
      description: 'API-powered live satellite telemetry layer fetching real-time thermal hotspots across India directly from NASA servers.'
    }
  },

  // 2. INDUSTRIAL ASSETS
  {
    id: 'india-industrial-facilities',
    name: 'INDIA HEAVY INDUSTRIAL ASSETS',
    subtitle: 'GEM / WRI / OSM • 1,704 Geocoded Assets',
    category: 'INDUSTRIAL ASSETS',
    iconType: 'factory',
    status: 'LOADED',
    statusColor: '#38bdf8',
    defaultEnabled: true,
    metadata: {
      datasetName: 'Master India Heavy Industrial Facilities Database',
      provider: 'Global Energy Monitor (GEM), World Resources Institute (WRI) & OSM',
      resolution: 'Exact Sub-Facility Geolocation Points (WGS84)',
      dataType: 'Geospatial Facility Inventory with Sector & Sub-Facility Metadata',
      coverage: 'Pan-India (All 28 States & 8 Union Territories)',
      mode: 'Indexed via Spatial Haversine BallTree (< 2ms query latency)',
      source: 'Global Energy Monitor / WRI Industrial Asset Repository',
      recordCount: '1,704 Geocoded Heavy Industry Complexes',
      description: 'Master registry of heavy industrial complexes across India including petrochemical refineries, steel smelters, power plants, and chemical units.'
    }
  },
  {
    id: 'global-power-plants',
    name: 'GLOBAL POWER PLANTS (GPPD)',
    subtitle: 'World Resources Institute • Thermal & Hydro MW',
    category: 'INDUSTRIAL ASSETS',
    iconType: 'zap',
    status: 'LOADED',
    statusColor: '#60a5fa',
    defaultEnabled: false,
    metadata: {
      datasetName: 'Global Power Plant Database (GPPD) — India Network',
      provider: 'World Resources Institute (WRI) & Open Climate Data',
      resolution: 'Unit-Level Geocoded Thermal / Hydro / Renewable Coordinates',
      dataType: 'Power Station Capacity (MW), Fuel Type, Generation & Operator Attribution',
      coverage: 'National Electricity Grid Network (India)',
      mode: 'Static Geospatial Database (~12 MB)',
      source: 'WRI Open Data & Ministry of Power India Registry',
      recordCount: 'Major Indian Thermal & Renewable Generation Units',
      description: 'Comprehensive inventory of electricity generation plants tracking fossil thermal boilers, supercritical units, and capacity ratings.'
    }
  },
  {
    id: 'global-oil-gas-tracker',
    name: 'OIL & GAS INFRASTRUCTURE',
    subtitle: 'Global Energy Monitor • Refineries & Depots',
    category: 'INDUSTRIAL ASSETS',
    iconType: 'fuel',
    status: 'LOADED',
    statusColor: '#f59e0b',
    defaultEnabled: false,
    metadata: {
      datasetName: 'Global Oil and Gas Plant Tracker (GOGPT)',
      provider: 'Global Energy Monitor (GEM)',
      resolution: 'Asset Footprint & Terminal Boundary Coordinates',
      dataType: 'Crude Refining Capacity (BPD), Product Pipelines & Bulk Storage Terminals',
      coverage: 'Indian Energy Hubs (Jamnagar, Paradip, Kochi, Haldia, Visakhapatnam)',
      mode: 'Static Master Tracker (August 2026 Release)',
      source: 'Global Energy Monitor Energy Infrastructure Project',
      recordCount: 'All Operating Indian Crude Refineries & Terminals',
      description: 'Tracks oil refineries, gas processing plants, and bulk petrochemical terminals with operational status and feedstock details.'
    }
  },
  {
    id: 'global-iron-steel-tracker',
    name: 'IRON & STEEL PLANT TRACKER',
    subtitle: 'Global Steel Plant Units • Blast Furnaces',
    category: 'INDUSTRIAL ASSETS',
    iconType: 'anvil',
    status: 'LOADED',
    statusColor: '#94a3b8',
    defaultEnabled: false,
    metadata: {
      datasetName: 'Global Iron and Steel Unit Plant Tracker',
      provider: 'Global Energy Monitor & Steel Authority of India (SAIL)',
      resolution: 'Blast Furnace & Electric Arc Smelter Coordinates',
      dataType: 'Nominal Crude Steel Capacity (TTPA) & Ironmaking Technology',
      coverage: 'Indian Metallurgical Belts (Chota Nagpur, Odisha, Karnataka)',
      mode: 'Static Master Tracker (June 2026 Release)',
      source: 'Global Energy Monitor Industrial Research Hub',
      recordCount: 'Integrated Steel Plants & Large Smelting Works',
      description: 'Tracks integrated steelworks, blast furnaces, and continuous cast smelters susceptible to high continuous operational heat.'
    }
  },

  // 3. HAZARD / VULNERABILITY
  {
    id: 'cameo-niosh-hazmat',
    name: 'CAMEO / NIOSH HAZMAT DATABASE',
    subtitle: 'NOAA / EPA • Chemical Hazard Profiles & ERG',
    category: 'HAZARD / VULNERABILITY',
    iconType: 'hazard',
    status: 'STATIC',
    statusColor: '#ef4444',
    defaultEnabled: true,
    metadata: {
      datasetName: 'CAMEO Chemicals & NIOSH Pocket Guide Hazardous Materials Database',
      provider: 'US NOAA Office of Response & Restoration / US EPA / NIOSH',
      resolution: 'Chemical Commodity & UN Number Level',
      dataType: 'Chemical Toxicity, Reactivity Matrices, Combustion Byproducts, Air Dispersion Constants',
      coverage: 'Sectoral Chemical Profiles for Petrochemical, Steel, Fertilizer & Mining Facilities',
      mode: 'Emergency Response Guidebook (ERG 2024) Standardized Evacuation Matrix',
      source: 'NOAA CAMEO Chemicals / EPA Toxic Chemical Release Inventory',
      recordCount: 'Mapped Chemical Profiles across Indian Industrial Sectors',
      description: 'Official first responder chemical vulnerability index defining UN hazard classes, lethal thermal thresholds, and isolation zones.'
    }
  },
  {
    id: 'historical-disasters',
    name: 'HISTORICAL INDUSTRIAL DISASTERS',
    subtitle: '7 Benchmark Ground-Truth Incident Casefiles',
    category: 'HAZARD / VULNERABILITY',
    iconType: 'history',
    status: 'LOADED',
    statusColor: '#f43f5e',
    defaultEnabled: true,
    metadata: {
      datasetName: 'Historical Indian Industrial Disasters Benchmark Casefiles',
      provider: 'National Disaster Management Authority (NDMA) & Satellite Archives',
      resolution: 'Sub-Pixel Geocoded Incident Points with Historical Radiance Inversion',
      dataType: 'Ground-Truth Validated Industrial Disasters vs Routine Operational Baseline Multipliers',
      coverage: 'Key Indian Industrial Centers (Vizag, Jaipur, Jamnagar, Jamshedpur, Jharia, Simlipal, Sangrur)',
      mode: 'Deterministic Evaluation & Live Presentation Verification Dataset',
      source: 'Court of Inquiry Reports, NDMA Case Audits & NASA Satellite Archives',
      recordCount: '7 Comprehensive Ground-Truth Multi-Modal Casefiles',
      description: 'Curated historical disasters (including LG Polymers Vizag and IOCL Jaipur) demonstrating multi-modal AI and plume dispersion accuracy.'
    }
  },

  // 4. RESPONSE INFRASTRUCTURE
  {
    id: 'india-emergency-services',
    name: 'INDIA EMERGENCY RESPONDERS',
    subtitle: 'District Fire • Burn Trauma ICUs • NDRF',
    category: 'RESPONSE INFRASTRUCTURE',
    iconType: 'emergency',
    status: 'LOADED',
    statusColor: '#38bdf8',
    defaultEnabled: true,
    metadata: {
      datasetName: 'India Emergency Services & Tactical Response Infrastructure Registry',
      provider: 'OpenStreetMap Emergency Infrastructure & NDMA Regional Directory',
      resolution: 'Emergency Facility Coordinates & Direct Emergency Phone Numbers',
      dataType: 'District Fire Commands, Chemical Foam Brigades, Apex Burn Trauma ICUs & NDRF Bases',
      coverage: 'Major Industrial Corridors & Metropolitan Response Hubs across India',
      mode: 'Integrated Spatial Dispatch Routing & PDF Dossier Integration',
      source: 'OpenStreetMap GeoJSON Registry & National Health Portal',
      recordCount: 'Indexed Fire Commands, Trauma Centers & Regional Battalions',
      description: 'Critical disaster response infrastructure mapped for immediate tactical dispatch during catastrophic chemical and thermal emergencies.'
    }
  },

  // 5. GROUND TRUTH / AI
  {
    id: 'multimodal-benchmark',
    name: 'AI GROUND-TRUTH BENCHMARK',
    subtitle: '26-Feature Extracted Dataset • 1,400 Events',
    category: 'GROUND TRUTH / AI',
    iconType: 'database',
    status: 'LOADED',
    statusColor: '#a855f7',
    defaultEnabled: true,
    metadata: {
      datasetName: 'Multi-Modal Ground-Truth Benchmark Dataset for Thermal Anomaly Segregation',
      provider: 'PyroSat-AI Research Team & NASA Ground-Truth Validated Events',
      resolution: '26 Standardized Radiometric, Pyrometric, LULC & Temporal Features',
      dataType: '6-Class Balanced Ground-Truth Split (Flares, Disasters, Wildfires, Stubble, Coal, Glint)',
      coverage: 'Pan-India Thermal Anomaly Distribution',
      mode: '5-Fold Stratified Cross-Validation Corpus (91.4% Macro F1-Score)',
      source: 'Trained Decision Ensemble / labeled_benchmark_dataset.csv',
      recordCount: '1,400 Labeled Benchmark Events',
      description: 'Standardized machine learning training and evaluation dataset proving physical and spatial discriminatory power across all 6 classes.'
    }
  },

  // 6. GEOSPATIAL / ENVIRONMENT
  {
    id: 'india-boundaries',
    name: 'ADMINISTRATIVE BOUNDARIES',
    subtitle: 'Survey of India • State Vector Outlines',
    category: 'GEOSPATIAL / ENVIRONMENT',
    iconType: 'map',
    status: 'LOADED',
    statusColor: '#64748b',
    defaultEnabled: true,
    metadata: {
      datasetName: 'India Administrative & Boundary Geospatial Database',
      provider: 'Survey of India / Bharat Maps Geospatial Repository',
      resolution: 'High-Precision Geographic Boundary Polygons (WGS84 EPSG:4326)',
      dataType: 'State & Union Territory Geospatial Vector Outlines',
      coverage: 'Complete Territorial Boundary of the Republic of India',
      mode: 'Vector Polygon GIS Overlay (india_state.geojson)',
      source: 'Survey of India Open Geospatial Portal',
      recordCount: 'All Indian States & Union Territories',
      description: 'Authoritative administrative boundaries utilized for regional spatial partitioning, state-level filtering, and jurisdictional alerts.'
    }
  },
  {
    id: 'indian-forest-reserves',
    name: 'PROTECTED FOREST RESERVES',
    subtitle: 'Forest Survey of India • Biosphere Centroids',
    category: 'GEOSPATIAL / ENVIRONMENT',
    iconType: 'trees',
    status: 'LOADED',
    statusColor: '#10b981',
    defaultEnabled: true,
    metadata: {
      datasetName: 'Indian Protected Forest Reserves Ground-Truth Database',
      provider: 'Forest Survey of India (FSI) & Ministry of Environment, Forest and Climate Change (MoEFCC)',
      resolution: 'Core Forest Centroids with Protection Buffer Radii (km)',
      dataType: 'Protected National Parks, Tiger Reserves, and Dense Biosphere Sanctuaries',
      coverage: 'Key Ecologically Sensitive Forest Zones across India (Similipal, Corbett, Kanha, Gir, Silent Valley)',
      mode: 'Spatial Intersect Buffer for Wildfire Origin Attribution',
      source: 'Forest Survey of India State of Forest Reports (ISFR)',
      recordCount: 'Core Indian National Parks & Biosphere Reserves',
      description: 'Centroids and protection radii of critical Indian forest reserves used to classify natural canopy biomass wildfires.'
    }
  }
];
