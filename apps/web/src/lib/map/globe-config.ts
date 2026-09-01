/**
 * 3D Globe Visual Configuration & Camera Settings
 */

export const GLOBE_CONFIG = {
  // High-resolution dark earth textures
  textures: {
    // NASA Blue Marble Night Lights
    globeNight: "https://unpkg.com/three-globe/example/img/earth-night.jpg",
    // Dark topography bump map for realistic mountain/ocean depth
    bumpMap: "https://unpkg.com/three-globe/example/img/earth-topology.png",
    // Subtle background night sky / deep space environment
    background: null, // Transparent to blend seamlessly into --bg-base
  },

  // Atmospheric glow parameters matching the design tokens
  atmosphere: {
    color: "#00d9ff", // Subtle cyan atmospheric edge
    altitude: 0.14,
    show: true,
  },

  // Camera POV for India / Jamnagar Study Area
  initialCamera: {
    lat: 22.4707,
    lng: 70.0577,
    altitude: 2.1,
  },

  // Orbital controls & zoom boundaries
  controls: {
    autoRotateSpeed: 0.35, // Slow, dignified rotation (0.35 deg/sec)
    autoRotateResumeDelay: 3500, // Resume auto-rotation 3.5s after user interaction
    minAltitude: 0.15, // Closest zoom limit (prevents clipping through earth)
    maxAltitude: 4.2,  // Furthest zoom limit (keeps globe in frame)
    enableDamping: true,
    dampingFactor: 0.05,
  },

  // Color tokens
  colors: {
    ocean: "#07090d",
    atmosphere: "rgba(0, 217, 255, 0.18)",
    highlight: "#39ff88",
  },
};
