import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Incident, FacilityMarker, EmergencyResponder } from '../types';
import { Layers, Crosshair } from 'lucide-react';

export interface ForestReserve {
  name: string;
  state: string;
  type: string;
  latitude: number;
  longitude: number;
  radius_km: number;
}

interface MinimalMapProps {
  incidents: Incident[];
  selectedIncident: Incident | null;
  onSelectIncident: (incident: Incident) => void;
  activeLayers: Record<string, boolean>;
  facilities: FacilityMarker[];
  emergencyResponders: EmergencyResponder[];
  forestReserves: ForestReserve[];
  liveFirmsHotspots: any[];
}

type BasemapStyle = 'dark' | 'osm' | 'satellite';

export const MinimalMap: React.FC<MinimalMapProps> = ({
  incidents,
  selectedIncident,
  onSelectIncident,
  activeLayers,
  facilities,
  emergencyResponders,
  forestReserves,
  liveFirmsHotspots,
}) => {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<L.Map | null>(null);

  // Dedicated Layer Groups for each dataset
  const firmsLayerRef = useRef<L.LayerGroup | null>(null);
  const liveApiLayerRef = useRef<L.LayerGroup | null>(null);
  const facilitiesLayerRef = useRef<L.LayerGroup | null>(null);
  const powerPlantsLayerRef = useRef<L.LayerGroup | null>(null);
  const oilGasLayerRef = useRef<L.LayerGroup | null>(null);
  const steelLayerRef = useRef<L.LayerGroup | null>(null);
  const hazmatLayerRef = useRef<L.LayerGroup | null>(null);
  const disastersLayerRef = useRef<L.LayerGroup | null>(null);
  const emergencyLayerRef = useRef<L.LayerGroup | null>(null);
  const benchmarkLayerRef = useRef<L.LayerGroup | null>(null);
  const boundariesLayerRef = useRef<L.LayerGroup | null>(null);
  const forestLayerRef = useRef<L.LayerGroup | null>(null);
  const tileLayerRef = useRef<L.TileLayer | null>(null);

  const [basemapStyle, setBasemapStyle] = useState<BasemapStyle>('dark');
  const [showBasemapMenu, setShowBasemapMenu] = useState<boolean>(false);

  // Initialize Map
  useEffect(() => {
    if (!mapRef.current || leafletMapRef.current) return;

    const map = L.map(mapRef.current, {
      center: [21.5, 79.5], // Centered on India
      zoom: 5,
      minZoom: 4,
      maxZoom: 16,
      zoomControl: false,
      attributionControl: false,
    });

    // Dark sleek minimalistic tile layer
    const darkTile = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 16,
      opacity: 0.95,
    }).addTo(map);

    tileLayerRef.current = darkTile;

    // Zoom controls bottom right
    L.control.zoom({ position: 'bottomright' }).addTo(map);

    // Initialize all Layer Groups
    boundariesLayerRef.current = L.layerGroup().addTo(map);
    facilitiesLayerRef.current = L.layerGroup().addTo(map);
    powerPlantsLayerRef.current = L.layerGroup().addTo(map);
    oilGasLayerRef.current = L.layerGroup().addTo(map);
    steelLayerRef.current = L.layerGroup().addTo(map);
    forestLayerRef.current = L.layerGroup().addTo(map);
    emergencyLayerRef.current = L.layerGroup().addTo(map);
    hazmatLayerRef.current = L.layerGroup().addTo(map);
    disastersLayerRef.current = L.layerGroup().addTo(map);
    benchmarkLayerRef.current = L.layerGroup().addTo(map);
    firmsLayerRef.current = L.layerGroup().addTo(map);
    liveApiLayerRef.current = L.layerGroup().addTo(map);

    leafletMapRef.current = map;

    return () => {
      map.remove();
      leafletMapRef.current = null;
    };
  }, []);

  // Update Basemap Layer when user toggles
  useEffect(() => {
    const map = leafletMapRef.current;
    if (!map) return;

    if (tileLayerRef.current) {
      map.removeLayer(tileLayerRef.current);
    }

    let newTile: L.TileLayer;
    if (basemapStyle === 'osm') {
      newTile = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap contributors',
      });
    } else if (basemapStyle === 'satellite') {
      newTile = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: 'Esri, Maxar, Earthstar Geographics',
      });
    } else {
      newTile = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 16,
        opacity: 0.95,
      });
    }

    newTile.addTo(map);
    tileLayerRef.current = newTile;
  }, [basemapStyle]);

  // Center on selected incident smoothly
  useEffect(() => {
    if (!leafletMapRef.current || !selectedIncident) return;
    leafletMapRef.current.flyTo([selectedIncident.lat, selectedIncident.lon], 8, {
      duration: 1.0,
      easeLinearity: 0.25,
    });
  }, [selectedIncident]);

  const handleRecenter = () => {
    if (!leafletMapRef.current) return;
    leafletMapRef.current.flyTo([21.5, 79.5], 5, { duration: 1.0 });
  };

  // =========================================================================
  // LAYER 1: NASA FIRMS VIIRS Thermal Telemetry Database
  // =========================================================================
  useEffect(() => {
    const group = firmsLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['nasa-firms-viirs']) return;

    incidents.forEach((inc) => {
      const isSelected = selectedIncident?.id === inc.id;
      let iconHtml = '';

      if (inc.category === 'accidental') {
        iconHtml = `
          <div style="
            position: relative;
            width: ${isSelected ? '26px' : '18px'};
            height: ${isSelected ? '26px' : '18px'};
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
          ">
            <div style="
              position: absolute;
              inset: 0;
              border-radius: 50%;
              border: 2px solid #ef4444;
              background: rgba(239, 68, 68, 0.35);
              box-shadow: ${isSelected ? '0 0 16px #ef4444' : '0 0 6px rgba(239,68,68,0.5)'};
            "></div>
            <div style="width: 6px; height: 6px; border-radius: 50%; background: #ffffff;"></div>
          </div>
        `;
      } else if (inc.category === 'routine') {
        iconHtml = `
          <div style="
            width: ${isSelected ? '16px' : '11px'};
            height: ${isSelected ? '16px' : '11px'};
            border: 1.5px solid #f59e0b;
            background: rgba(245, 158, 11, 0.4);
            transform: rotate(45deg);
            cursor: pointer;
            box-shadow: ${isSelected ? '0 0 12px #f59e0b' : 'none'};
          "></div>
        `;
      } else if (inc.category === 'crop') {
        iconHtml = `
          <div style="
            width: ${isSelected ? '13px' : '8px'};
            height: ${isSelected ? '13px' : '8px'};
            border-radius: 50%;
            border: 1.5px solid #ea580c;
            background: #ea580c;
            cursor: pointer;
          "></div>
        `;
      } else if (inc.category === 'coal') {
        iconHtml = `
          <div style="
            width: ${isSelected ? '14px' : '9px'};
            height: ${isSelected ? '14px' : '9px'};
            border-radius: 2px;
            border: 1.5px solid #a855f7;
            background: rgba(168, 85, 247, 0.4);
            cursor: pointer;
          "></div>
        `;
      } else if (inc.category === 'wildfire') {
        iconHtml = `
          <div style="
            width: ${isSelected ? '14px' : '9px'};
            height: ${isSelected ? '14px' : '9px'};
            border-radius: 50%;
            border: 1.5px solid #10b981;
            background: #10b981;
            cursor: pointer;
          "></div>
        `;
      } else {
        iconHtml = `
          <div style="
            width: ${isSelected ? '12px' : '8px'};
            height: ${isSelected ? '12px' : '8px'};
            border-radius: 50%;
            border: 1.5px dashed #94a3b8;
            background: rgba(148, 163, 184, 0.15);
            cursor: pointer;
          "></div>
        `;
      }

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'firms-marker',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([inc.lat, inc.lon], { icon: customIcon });

      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        onSelectIncident(inc);
      });

      marker.bindTooltip(`
        <div style="background: #11141c; border: 1px solid #232836; border-radius: 8px; padding: 6px 10px; color: #f3f4f6; font-size: 11px; font-family: sans-serif; box-shadow: 0 8px 24px rgba(0,0,0,0.7);">
          <div style="font-weight: 600; color: ${inc.category === 'accidental' ? '#ef4444' : '#f3f4f6'}; display: flex; align-items: center; justify-content: space-between; gap: 8px;">
            <span>${inc.title}</span>
            <span style="font-family: monospace; font-size: 10px;">${inc.confidence}%</span>
          </div>
          <div style="font-size: 10px; color: #8b92a4; margin-top: 2px;">${inc.subtitle}</div>
          <div style="font-size: 9.5px; color: #64748b; margin-top: 3px;">📍 ${inc.facility} (${inc.state}) · FRP ${inc.frpMw} MW</div>
        </div>
      `, { direction: 'top', offset: [0, -10], opacity: 1 });

      marker.addTo(group);
    });
  }, [incidents, selectedIncident, onSelectIncident, activeLayers]);

  // =========================================================================
  // LAYER 2: NASA FIRMS LIVE API Stream
  // =========================================================================
  useEffect(() => {
    const group = liveApiLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['nasa-firms-live-api'] || !liveFirmsHotspots || liveFirmsHotspots.length === 0) return;

    liveFirmsHotspots.forEach((spot: any) => {
      const lat = spot.geometry?.coordinates[1] || spot.latitude;
      const lon = spot.geometry?.coordinates[0] || spot.longitude;
      const frp = spot.properties?.frp_mw || spot.frp || 15.0;
      const name = spot.properties?.predicted_class_name || 'Live VIIRS Hotspot';

      if (!lat || !lon) return;

      const iconHtml = `
        <div style="
          position: relative;
          width: 14px;
          height: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
        ">
          <div style="
            position: absolute;
            inset: 0;
            border-radius: 50%;
            border: 1.5px solid #00f0ff;
            background: rgba(0, 240, 255, 0.35);
            box-shadow: 0 0 8px #00f0ff;
            animation: pulse 1.5s infinite;
          "></div>
          <div style="width: 4px; height: 4px; border-radius: 50%; background: #ffffff;"></div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'live-api-marker',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });

      const marker = L.marker([lat, lon], { icon: customIcon });

      marker.bindTooltip(`
        <div style="background: #091a24; border: 1px solid #00f0ff; border-radius: 6px; padding: 5px 8px; color: #f8fafc; font-size: 11px; font-family: sans-serif;">
          <div style="font-weight: 700; color: #00f0ff;">📡 LIVE NASA VIIRS STREAM</div>
          <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">Class: ${name} · FRP: ${frp} MW</div>
          <div style="font-size: 9.5px; color: #64748b; margin-top: 2px;">GPS: ${lat.toFixed(3)}°N, ${lon.toFixed(3)}°E</div>
        </div>
      `, { direction: 'top', offset: [0, -6], opacity: 1 });

      marker.addTo(group);
    });
  }, [activeLayers, liveFirmsHotspots]);

  // =========================================================================
  // LAYER 3: Master India Heavy Industrial Facilities (1,704 Assets)
  // =========================================================================
  useEffect(() => {
    const group = facilitiesLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['india-industrial-facilities'] || facilities.length === 0) return;

    facilities.forEach((fac) => {
      const iconHtml = `
        <div style="
          width: 7px;
          height: 7px;
          border-radius: 1px;
          background: #38bdf8;
          border: 1px solid rgba(255,255,255,0.8);
          box-shadow: 0 0 4px #38bdf8;
          cursor: pointer;
        "></div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'facility-marker',
        iconSize: [8, 8],
        iconAnchor: [4, 4],
      });

      const marker = L.marker([fac.lat, fac.lon], { icon: customIcon });

      marker.bindTooltip(`
        <div style="background: #0f172a; border: 1px solid #38bdf8; border-radius: 6px; padding: 5px 8px; color: #f8fafc; font-size: 11px; font-family: sans-serif;">
          <div style="font-weight: 700; color: #38bdf8;">🏭 ${fac.name}</div>
          <div style="font-size: 10px; color: #94a3b8; margin-top: 2px;">${fac.type || fac.category || 'Heavy Industry Complex'}</div>
          <div style="font-size: 9.5px; color: #64748b; margin-top: 2px;">📍 ${fac.lat.toFixed(3)}°N, ${fac.lon.toFixed(3)}°E</div>
        </div>
      `, { direction: 'top', offset: [0, -4], opacity: 1 });

      marker.addTo(group);
    });
  }, [activeLayers, facilities]);

  // =========================================================================
  // LAYER 4: Global Power Plant Database (GPPD)
  // =========================================================================
  useEffect(() => {
    const group = powerPlantsLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['global-power-plants'] || facilities.length === 0) return;

    const powerPlants = facilities.filter(f => 
      f.type?.toLowerCase().includes('power') || 
      f.category?.toLowerCase().includes('power') ||
      f.name?.toLowerCase().includes('thermal') ||
      f.name?.toLowerCase().includes('tps') ||
      f.name?.toLowerCase().includes('super')
    );

    powerPlants.forEach((pp) => {
      const iconHtml = `
        <div style="
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: #60a5fa;
          border: 1.5px solid #ffffff;
          box-shadow: 0 0 6px #60a5fa;
          cursor: pointer;
        "></div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'power-marker',
        iconSize: [12, 12],
        iconAnchor: [6, 6],
      });

      const marker = L.marker([pp.lat, pp.lon], { icon: customIcon });

      marker.bindTooltip(`
        <div style="background: #111827; border: 1px solid #60a5fa; border-radius: 6px; padding: 5px 8px; color: #f8fafc; font-size: 11px; font-family: sans-serif;">
          <div style="font-weight: 700; color: #60a5fa;">⚡ ${pp.name}</div>
          <div style="font-size: 10px; color: #cbd5e1; margin-top: 2px;">Thermal Power Generation (${pp.type || 'Coal/Gas/Renewable'})</div>
          <div style="font-size: 9.5px; color: #64748b; margin-top: 2px;">WRI Global Power Plant Registry</div>
        </div>
      `, { direction: 'top', offset: [0, -6], opacity: 1 });

      marker.addTo(group);
    });
  }, [activeLayers, facilities]);

  // =========================================================================
  // LAYER 5: Global Oil & Gas Tracker (GOGPT)
  // =========================================================================
  useEffect(() => {
    const group = oilGasLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['global-oil-gas-tracker'] || facilities.length === 0) return;

    const oilGas = facilities.filter(f => 
      f.type?.toLowerCase().includes('refin') || 
      f.type?.toLowerCase().includes('oil') || 
      f.type?.toLowerCase().includes('gas') ||
      f.name?.toLowerCase().includes('refinery') ||
      f.name?.toLowerCase().includes('petro') ||
      f.name?.toLowerCase().includes('iocl') ||
      f.name?.toLowerCase().includes('hpcl') ||
      f.name?.toLowerCase().includes('bpcl')
    );

    oilGas.forEach((og) => {
      const iconHtml = `
        <div style="
          width: 10px;
          height: 10px;
          border-radius: 2px;
          background: #f59e0b;
          border: 1.5px solid #ffffff;
          box-shadow: 0 0 6px #f59e0b;
          cursor: pointer;
        "></div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'oil-marker',
        iconSize: [12, 12],
        iconAnchor: [6, 6],
      });

      const marker = L.marker([og.lat, og.lon], { icon: customIcon });

      marker.bindTooltip(`
        <div style="background: #1c1509; border: 1px solid #f59e0b; border-radius: 6px; padding: 5px 8px; color: #f8fafc; font-size: 11px; font-family: sans-serif;">
          <div style="font-weight: 700; color: #f59e0b;">🛢️ ${og.name}</div>
          <div style="font-size: 10px; color: #cbd5e1; margin-top: 2px;">Refinery & Bulk Petrochemical Terminal</div>
          <div style="font-size: 9.5px; color: #64748b; margin-top: 2px;">Global Energy Monitor (GOGPT)</div>
        </div>
      `, { direction: 'top', offset: [0, -6], opacity: 1 });

      marker.addTo(group);
    });
  }, [activeLayers, facilities]);

  // =========================================================================
  // LAYER 6: Global Iron & Steel Plant Tracker
  // =========================================================================
  useEffect(() => {
    const group = steelLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['global-iron-steel-tracker'] || facilities.length === 0) return;

    const steelPlants = facilities.filter(f => 
      f.type?.toLowerCase().includes('steel') || 
      f.type?.toLowerCase().includes('smelt') ||
      f.name?.toLowerCase().includes('steel') ||
      f.name?.toLowerCase().includes('sail') ||
      f.name?.toLowerCase().includes('jsw') ||
      f.name?.toLowerCase().includes('tata steel')
    );

    steelPlants.forEach((sp) => {
      const iconHtml = `
        <div style="
          width: 9px;
          height: 9px;
          transform: rotate(45deg);
          background: #94a3b8;
          border: 1.5px solid #ffffff;
          box-shadow: 0 0 6px #94a3b8;
          cursor: pointer;
        "></div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'steel-marker',
        iconSize: [12, 12],
        iconAnchor: [6, 6],
      });

      const marker = L.marker([sp.lat, sp.lon], { icon: customIcon });

      marker.bindTooltip(`
        <div style="background: #141720; border: 1px solid #94a3b8; border-radius: 6px; padding: 5px 8px; color: #f8fafc; font-size: 11px; font-family: sans-serif;">
          <div style="font-weight: 700; color: #94a3b8;">⚙️ ${sp.name}</div>
          <div style="font-size: 10px; color: #cbd5e1; margin-top: 2px;">Integrated Steel & Blast Furnace Smelter</div>
          <div style="font-size: 9.5px; color: #64748b; margin-top: 2px;">Global Iron & Steel Tracker</div>
        </div>
      `, { direction: 'top', offset: [0, -6], opacity: 1 });

      marker.addTo(group);
    });
  }, [activeLayers, facilities]);

  // =========================================================================
  // LAYER 7: CAMEO / NIOSH HAZMAT & Downwind Plumes
  // =========================================================================
  useEffect(() => {
    const group = hazmatLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['cameo-niosh-hazmat'] || !selectedIncident) return;

    let angleDeg = 315;
    if (selectedIncident.windDir.includes('45')) angleDeg = 45;
    else if (selectedIncident.windDir.includes('90')) angleDeg = 90;
    else if (selectedIncident.windDir.includes('120')) angleDeg = 120;
    else if (selectedIncident.windDir.includes('135')) angleDeg = 135;
    else if (selectedIncident.windDir.includes('180')) angleDeg = 180;
    else if (selectedIncident.windDir.includes('270')) angleDeg = 270;

    const rad = (angleDeg * Math.PI) / 180;
    const length = (selectedIncident.evacRadiusKm || 2.0) * 0.035;
    const spread = length * 0.35;

    const dx = Math.sin(rad) * length;
    const dy = Math.cos(rad) * length;
    const px = -Math.cos(rad) * spread;
    const py = Math.sin(rad) * spread;

    const plumeCoords: [number, number][] = [
      [selectedIncident.lat, selectedIncident.lon],
      [selectedIncident.lat + dy + py, selectedIncident.lon + dx + px],
      [selectedIncident.lat + dy * 1.15, selectedIncident.lon + dx * 1.15],
      [selectedIncident.lat + dy - py, selectedIncident.lon + dx - px],
      [selectedIncident.lat, selectedIncident.lon],
    ];

    const plumeColor = selectedIncident.category === 'accidental' ? '#ef4444' : '#f59e0b';

    L.polygon(plumeCoords, {
      color: plumeColor,
      weight: 1.5,
      dashArray: '4, 4',
      fillColor: plumeColor,
      fillOpacity: 0.22,
    }).addTo(group);

    if (selectedIncident.evacRadiusKm > 0) {
      L.circle([selectedIncident.lat, selectedIncident.lon], {
        radius: selectedIncident.evacRadiusKm * 1000,
        color: plumeColor,
        weight: 1.2,
        dashArray: '2, 5',
        fillColor: plumeColor,
        fillOpacity: 0.07,
      }).addTo(group);
    }
  }, [selectedIncident, activeLayers]);

  // =========================================================================
  // LAYER 8: Historical Industrial Disasters Benchmark Cases
  // =========================================================================
  useEffect(() => {
    const group = disastersLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['historical-disasters']) return;

    const historicalCases = incidents.filter(i => i.caseId);

    historicalCases.forEach((hc) => {
      const iconHtml = `
        <div style="
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #f43f5e;
          border: 2px solid #ffffff;
          box-shadow: 0 0 10px #f43f5e;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 9px;
          color: white;
          cursor: pointer;
        ">★</div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'disaster-case-marker',
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      });

      const marker = L.marker([hc.lat, hc.lon], { icon: customIcon });

      marker.on('click', (e) => {
        L.DomEvent.stopPropagation(e);
        onSelectIncident(hc);
      });

      marker.bindTooltip(`
        <div style="background: #240e14; border: 1px solid #f43f5e; border-radius: 6px; padding: 6px 9px; color: #f8fafc; font-size: 11px; font-family: sans-serif;">
          <div style="font-weight: 700; color: #f43f5e;">★ HISTORICAL GROUND-TRUTH CASE</div>
          <div style="font-size: 10px; color: #cbd5e1; margin-top: 2px;">${hc.title} (${hc.facility})</div>
          <div style="font-size: 9.5px; color: #fca5a5; margin-top: 2px;">FRP: ${hc.frpMw} MW · Flame Temp: ${hc.tempK} K</div>
        </div>
      `, { direction: 'top', offset: [0, -8], opacity: 1 });

      marker.addTo(group);
    });
  }, [activeLayers, incidents, onSelectIncident]);

  // =========================================================================
  // LAYER 9: India Emergency Services & Tactical Responders
  // =========================================================================
  useEffect(() => {
    const group = emergencyLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['india-emergency-services'] || emergencyResponders.length === 0) return;

    emergencyResponders.forEach((resp) => {
      const isFire = resp.type === 'fire_station' || resp.type === 'ndrf';

      const iconHtml = isFire
        ? `<div style="width: 14px; height: 14px; border-radius: 4px; background: #dc2626; border: 1.5px solid #ffffff; color: #ffffff; display: flex; align-items: center; justify-content: center; font-size: 9px; box-shadow: 0 0 8px #dc2626; cursor: pointer;">🚒</div>`
        : `<div style="width: 14px; height: 14px; border-radius: 4px; background: #0284c7; border: 1.5px solid #ffffff; color: #ffffff; display: flex; align-items: center; justify-content: center; font-size: 9px; box-shadow: 0 0 8px #0284c7; cursor: pointer;">🏥</div>`;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'emergency-marker',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });

      const marker = L.marker([resp.lat, resp.lon], { icon: customIcon });

      marker.bindTooltip(`
        <div style="background: #11141c; border: 1px solid ${isFire ? '#ef4444' : '#38bdf8'}; border-radius: 6px; padding: 6px 9px; color: #f3f4f6; font-size: 11px; font-family: sans-serif;">
          <div style="font-weight: 700; color: ${isFire ? '#f87171' : '#38bdf8'};">${isFire ? '🚒' : '🏥'} ${resp.name}</div>
          <div style="font-size: 10px; color: #cbd5e1; margin-top: 2px;">${resp.city}, ${resp.state} ${resp.beds ? `· ${resp.beds} Beds` : ''}</div>
          <div style="font-size: 10px; color: #10b981; font-family: monospace; margin-top: 3px;">📞 ${resp.phone}</div>
        </div>
      `, { direction: 'top', offset: [0, -8], opacity: 1 });

      marker.addTo(group);
    });
  }, [activeLayers, emergencyResponders]);

  // =========================================================================
  // LAYER 10: Multi-Modal AI Ground-Truth Benchmark
  // =========================================================================
  useEffect(() => {
    const group = benchmarkLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['multimodal-benchmark']) return;

    // Subtle benchmark clusters
    const benchmarkGrid = [
      { lat: 17.7607, lon: 83.2185, label: 'Vizag Petrochem Split (Level-2 Accidental)' },
      { lat: 22.3556, lon: 69.8653, label: 'Jamnagar Flare Split (Level-2 Routine)' },
      { lat: 23.7431, lon: 86.4172, label: 'Jharia Coalfield Split (Level-2 Coal)' },
      { lat: 30.2458, lon: 75.8421, label: 'Sangrur Stubble Split (Level-2 Crop)' },
      { lat: 21.8653, lon: 86.3475, label: 'Similipal Biosphere Split (Level-2 Wildfire)' },
      { lat: 27.5380, lon: 71.9160, label: 'Bhadla Solar Split (Level-1 Glint)' },
    ];

    benchmarkGrid.forEach((bg) => {
      const iconHtml = `
        <div style="
          width: 8px;
          height: 8px;
          border-radius: 50%;
          border: 1px solid #a855f7;
          background: rgba(168, 85, 247, 0.4);
          box-shadow: 0 0 5px #a855f7;
          cursor: pointer;
        "></div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'benchmark-marker',
        iconSize: [10, 10],
        iconAnchor: [5, 5],
      });

      const marker = L.marker([bg.lat, bg.lon], { icon: customIcon });

      marker.bindTooltip(`
        <div style="background: #170d24; border: 1px solid #a855f7; border-radius: 6px; padding: 5px 8px; color: #f8fafc; font-size: 11px; font-family: sans-serif;">
          <div style="font-weight: 700; color: #c084fc;">🧠 AI TRAINING BENCHMARK NODE</div>
          <div style="font-size: 10px; color: #cbd5e1; margin-top: 2px;">${bg.label}</div>
          <div style="font-size: 9.5px; color: #a855f7; margin-top: 2px;">26-Dimensional Feature Extracted</div>
        </div>
      `, { direction: 'top', offset: [0, -6], opacity: 1 });

      marker.addTo(group);
    });
  }, [activeLayers]);

  // =========================================================================
  // LAYER 11: India Administrative Boundaries
  // =========================================================================
  useEffect(() => {
    const group = boundariesLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['india-boundaries']) return;

    // Regional grid representation of state boundaries
    const gridLines = [
      [[35.5, 74.0], [31.0, 78.5], [28.0, 77.0], [22.0, 77.0], [15.0, 74.0], [8.0, 77.5]],
      [[24.0, 68.5], [22.0, 73.0], [15.0, 74.0], [10.0, 76.5]],
      [[22.0, 89.0], [18.0, 84.0], [13.0, 80.0], [8.0, 77.5]],
      [[26.0, 89.0], [27.0, 95.0], [24.0, 93.0]],
      [[28.0, 77.0], [25.0, 85.0], [22.0, 88.0]],
    ];

    gridLines.forEach((pts) => {
      L.polyline(pts as any, {
        color: '#38bdf8',
        weight: 1.2,
        dashArray: '4, 4',
        opacity: 0.45,
      }).addTo(group);
    });
  }, [activeLayers]);

  // =========================================================================
  // LAYER 12: Indian Protected Forest Reserves
  // =========================================================================
  useEffect(() => {
    const group = forestLayerRef.current;
    if (!group) return;
    group.clearLayers();

    if (!activeLayers['indian-forest-reserves'] || forestReserves.length === 0) return;

    forestReserves.forEach((fr) => {
      const iconHtml = `
        <div style="
          width: 14px;
          height: 14px;
          border-radius: 4px;
          background: #059669;
          border: 1.5px solid #ffffff;
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 8px;
          box-shadow: 0 0 8px #059669;
          cursor: pointer;
        ">🌲</div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'forest-marker',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });

      const marker = L.marker([fr.latitude, fr.longitude], { icon: customIcon });

      marker.bindTooltip(`
        <div style="background: #06241b; border: 1px solid #10b981; border-radius: 6px; padding: 5px 8px; color: #f8fafc; font-size: 11px; font-family: sans-serif;">
          <div style="font-weight: 700; color: #34d399;">🌲 ${fr.name}</div>
          <div style="font-size: 10px; color: #a7f3d0; margin-top: 2px;">${fr.type} (${fr.state})</div>
          <div style="font-size: 9.5px; color: #6ee7b7; margin-top: 2px;">Core Protection Buffer: ${fr.radius_km} km</div>
        </div>
      `, { direction: 'top', offset: [0, -6], opacity: 1 });

      marker.addTo(group);

      // Protection Buffer Circle
      L.circle([fr.latitude, fr.longitude], {
        radius: fr.radius_km * 1000,
        color: '#10b981',
        weight: 1,
        dashArray: '3, 4',
        fillColor: '#10b981',
        fillOpacity: 0.05,
      }).addTo(group);
    });
  }, [activeLayers, forestReserves]);

  return (
    <div className="w-full h-full relative bg-[#0c0d12]">
      
      {/* Map Viewport */}
      <div 
        ref={mapRef} 
        className="w-full h-full bg-[#0c0d12] relative outline-none"
      />

      {/* Top Right Controls (Recenter & Basemap Switcher) */}
      <div className="absolute right-4 top-4 z-[400] font-sans flex items-center gap-2">
        
        {/* Recenter Button */}
        <button
          onClick={handleRecenter}
          className="p-2 rounded-lg bg-[#11141c]/90 backdrop-blur-md border border-[#232836] text-[#cbd5e1] hover:text-white hover:border-[#384158] text-xs shadow-lg flex items-center gap-1.5 cursor-pointer transition-all active:scale-95"
          title="Reset Zoom to India"
        >
          <Crosshair className="w-3.5 h-3.5 text-[#10b981]" />
          <span className="hidden sm:inline">Center India</span>
        </button>

        {/* Basemap Switcher */}
        <div className="relative">
          <button
            onClick={() => setShowBasemapMenu(!showBasemapMenu)}
            className="p-2 rounded-lg bg-[#11141c]/90 backdrop-blur-md border border-[#232836] text-[#cbd5e1] hover:text-white hover:border-[#384158] text-xs shadow-lg flex items-center gap-1.5 cursor-pointer transition-all active:scale-95"
            title="Switch Map Basemap Style"
          >
            <Layers className="w-3.5 h-3.5 text-[#38bdf8]" />
            <span className="capitalize">{basemapStyle} Map</span>
          </button>

          {showBasemapMenu && (
            <div className="absolute right-0 mt-1.5 w-44 bg-[#11141c] border border-[#232836] rounded-xl p-1.5 shadow-2xl space-y-1 text-xs animate-in fade-in zoom-in-95 duration-100">
              <button
                onClick={() => { setBasemapStyle('dark'); setShowBasemapMenu(false); }}
                className={`w-full text-left px-2.5 py-1.5 rounded-lg transition-colors flex items-center justify-between ${
                  basemapStyle === 'dark' ? 'bg-[#1f2433] text-[#38bdf8] font-medium' : 'text-[#8b92a4] hover:bg-[#161922] hover:text-white'
                }`}
              >
                <span>🌑 Dark Canvas</span>
                {basemapStyle === 'dark' && <span className="w-1.5 h-1.5 rounded-full bg-[#38bdf8]"></span>}
              </button>
              <button
                onClick={() => { setBasemapStyle('osm'); setShowBasemapMenu(false); }}
                className={`w-full text-left px-2.5 py-1.5 rounded-lg transition-colors flex items-center justify-between ${
                  basemapStyle === 'osm' ? 'bg-[#1f2433] text-[#38bdf8] font-medium' : 'text-[#8b92a4] hover:bg-[#161922] hover:text-white'
                }`}
              >
                <span>🗺️ OpenStreetMap</span>
                {basemapStyle === 'osm' && <span className="w-1.5 h-1.5 rounded-full bg-[#38bdf8]"></span>}
              </button>
              <button
                onClick={() => { setBasemapStyle('satellite'); setShowBasemapMenu(false); }}
                className={`w-full text-left px-2.5 py-1.5 rounded-lg transition-colors flex items-center justify-between ${
                  basemapStyle === 'satellite' ? 'bg-[#1f2433] text-[#38bdf8] font-medium' : 'text-[#8b92a4] hover:bg-[#161922] hover:text-white'
                }`}
              >
                <span>🛰️ Satellite Imagery</span>
                {basemapStyle === 'satellite' && <span className="w-1.5 h-1.5 rounded-full bg-[#38bdf8]"></span>}
              </button>
            </div>
          )}
        </div>

      </div>

    </div>
  );
};
