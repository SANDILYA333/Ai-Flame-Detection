# SIH26 — Frontend UI Context & Implementation Constitution

> **Document status:** LOCKED FRONTEND SOURCE OF TRUTH  
> **Project:** SIH26162 — AI-Based Detection and Classification of Industrial Fires and Persistent Thermal Sources Using NASA FIRMS, OSM & Satellite Data  
> **Frontend target:** `apps/web/`  
> **Primary goal:** Turn the already-built scientific/backend system into a polished, analyst-grade geospatial intelligence product.  
> **Execution constraint:** Prototype frontend must be built rapidly with agents, approximately 3–4 hours, while preserving visual quality and engineering correctness.

---

# 0. READ THIS FIRST — NON-NEGOTIABLE DIRECTIVE

This file is the **frontend constitution**.

Any implementation agent working inside `apps/web/` must read this document before modifying the UI.

The backend, data pipeline, event engine, context system, and production ML system already exist. The frontend is **productization**, not a reason to restart or redesign the foundation.

The product should feel like a **premium operational thermal-intelligence console**, inspired by the information density, map-first workflow, visual hierarchy, motion quality, and interaction patterns of World Monitor.

It must **not** become a generic admin dashboard.

It must **not** blindly clone World Monitor.

It must **not** copy proprietary branding, text, logos, or unrelated geopolitical functionality.

The correct mental model is:

```text
NASA FIRMS / Existing Data
        ↓
Canonical Detection
        ↓
Canonical Thermal Event
        ↓
Context / Evidence
        ↓
Production ML
        ↓
Uncertainty / Review State
        ↓
FastAPI
        ↓
SIH26 WEB CONSOLE
        ↓
Human investigation
```

The frontend's job is to make the intelligence above **immediately understandable, spatially explorable, visually compelling, and operationally useful**.

---

# 1. PRODUCT IDENTITY

## 1.1 Product category

The application is a:

**Thermal / Industrial Flame Intelligence Platform**

It is a geospatial intelligence interface for understanding satellite-observed thermal anomalies.

It is not primarily:

- a wildfire app;
- a generic disaster dashboard;
- a weather map;
- a raw FIRMS viewer;
- an ML demo;
- a generic GIS editor;
- a conventional CRUD dashboard.

The central question the product answers is:

> **What thermal activity is happening, where is it happening, what does the system think it represents, how confident is that assessment, what evidence supports it, and does it require review?**

---

# 2. PRIMARY USER EXPERIENCE

A user opening the application should understand the situation in seconds.

The first screen should communicate:

1. **WHERE** thermal activity is occurring.
2. **WHAT** type of thermal activity it may represent.
3. **WHEN** it occurred.
4. **HOW CONFIDENT** the system is.
5. **WHY** the system believes the classification.
6. **WHAT CONTEXT** exists around the event.
7. **WHETHER REVIEW IS REQUIRED.**
8. **WHAT SOURCE** produced the observation.

The map/globe is the dominant visual anchor.

The UI should allow the user to:

- rotate the globe;
- switch between 3D and 2D;
- zoom and pan;
- select a thermal event;
- inspect event details;
- toggle event layers;
- filter by classification;
- filter by confidence;
- filter by time;
- inspect detections;
- inspect persistent sources where supported;
- inspect contextual evidence;
- understand uncertainty;
- jump from a map marker to an intelligence panel;
- reset the camera;
- preserve smooth interactions while data changes.

---

# 3. DESIGN REFERENCE — WORLD MONITOR

The visual reference is the open-source World Monitor project and the supplied screenshots.

The current World Monitor repository describes a dual map architecture using:

- `globe.gl` + Three.js for the 3D globe;
- `deck.gl` + MapLibre GL for WebGL flat-map rendering;
- Vanilla TypeScript/Vite for its UI;
- Web Workers for off-main-thread work in its current documentation.

For this project, **do not copy World Monitor's entire architecture**.

Instead, extract the useful interaction principles:

- map-first layout;
- dark command-center aesthetic;
- dense but organized information;
- compact control chrome;
- clear layer controls;
- 2D/3D switching;
- persistent map controls;
- high-quality globe;
- subtle animated data markers;
- panel-based intelligence;
- status indicators;
- strong typography;
- restrained color usage;
- crisp borders;
- responsive interactions;
- clear active/inactive states;
- minimal visual noise.

Reference repository:

`koala73/worldmonitor`

Reference website:

`worldmonitor.app`

The World Monitor repository is explicitly useful as **inspiration and implementation research**, not as a specification for this application's backend or domain model.

---

# 4. ABSOLUTE VISUAL TARGET

The application should feel like:

```text
         HIGH-END INTELLIGENCE CONSOLE
                    +
        SATELLITE THERMAL MONITOR
                    +
             MODERN GIS TOOL
```

Desired emotional response:

- serious;
- technical;
- precise;
- futuristic;
- calm;
- trustworthy;
- information-dense;
- premium;
- operational.

Avoid:

- playful SaaS styling;
- excessive rounded cards;
- giant headings;
- pastel dashboards;
- excessive gradients;
- excessive shadows;
- cartoonish map markers;
- random neon colors;
- excessive glassmorphism;
- default component-library appearance.

The interface should look **intentional at every pixel**.

---

# 5. TECH STACK — LOCKED

## 5.1 Core

| Layer | Technology | Rule |
|---|---|---|
| Framework | Next.js | Use existing project setup if already present; do not migrate without reason |
| Language | TypeScript | Strict typing |
| Rendering | React | Componentized UI |
| 3D globe | `globe.gl` + Three.js | Primary 3D visualization |
| 2D map | MapLibre GL JS | Primary flat-map visualization |
| Geographic data | GeoJSON | Consume backend GIS output |
| Styling | Tailwind CSS | Centralized design tokens |
| UI primitives | shadcn/ui | Use selectively; customize heavily |
| Icons | Lucide React | Consistent stroke icons |
| Server/API state | TanStack Query | Fetch/cache server data |
| Runtime validation | Zod | Validate API boundaries where useful |
| Dates | date-fns | Consistent timestamp formatting |
| Charts | Recharts | Only for meaningful analytics panels |
| Forms | React Hook Form | Only where forms are needed |
| Unit/component tests | Vitest + Testing Library | Test important UI behavior |
| E2E | Playwright | Validate critical browser flows |

## 5.2 Do not add initially

Do not introduce these without a concrete need:

- Redux;
- Zustand;
- MobX;
- Apollo;
- GraphQL;
- Firebase;
- Supabase;
- another backend;
- another database;
- Kafka;
- Celery;
- a second map engine;
- a heavyweight GIS framework;
- a 3D game engine;
- a UI framework replacing the existing one;
- a charting library beyond what is already needed.

The frontend is not the place to create architectural complexity.

---

# 6. MAP / GLOBE ARCHITECTURE

## 6.1 Why two renderers

The desired UX explicitly requires:

- a high-quality rotating 3D globe;
- a practical 2D geographic map.

Therefore the UI should have two visualization modes.

```text
MapWorkspace
├── GlobeView
│   └── globe.gl
│       └── Three.js
│
└── FlatMapView
    └── MapLibre GL JS
```

Both renderers consume the **same canonical frontend event/view-model data**.

They must not have separate business logic.

---

# 7. 3D GLOBE — QUALITY REQUIREMENTS

The globe is one of the highest-priority features.

It must not look like a low-quality spinning sphere.

## 7.1 Globe characteristics

The 3D globe should provide:

- realistic Earth proportions;
- high-resolution Earth texture;
- dark/night appearance;
- subtle atmospheric glow;
- city-light/night texture if technically feasible;
- smooth continuous rotation;
- smooth user drag;
- inertial-feeling camera movement;
- zoom/distance control;
- event markers attached to geographic coordinates;
- marker depth/occlusion behaving naturally;
- no visible jitter;
- no excessive aliasing;
- no sudden camera jumps.

## 7.2 Globe composition

Conceptually:

```text
                   atmosphere
                ┌───────────────┐
             ┌──┴───────────────┴──┐
           /                         \
          /       EARTH SPHERE       \
         |       night texture        |
         |                             |
         |    🔥     🔥               |
         |             🔥             |
          \                           /
           \_________________________/
```

## 7.3 Globe lighting

Use subtle lighting.

The target is **dark Earth at night**, not a bright blue educational globe.

Prefer:

- dark satellite/night texture;
- restrained specular lighting;
- subtle ambient light;
- subtle directional light;
- optional atmosphere;
- subtle bloom only if performance remains excellent.

Avoid:

- excessive bloom;
- glowing oceans;
- cartoon continents;
- oversaturated colors;
- heavy fog.

## 7.4 Globe interaction

Required:

- drag to rotate;
- wheel/pinch to zoom;
- click marker to select;
- hover marker to preview where useful;
- reset/home;
- smooth transition to selected region;
- preserve current camera when switching layers;
- avoid accidental page scrolling while interacting with the globe.

## 7.5 Automatic rotation

The globe may rotate slowly when idle.

Rules:

- rotation should be slow;
- stop or reduce rotation during active user interaction;
- resume gradually after inactivity;
- never fight the user's pointer;
- respect `prefers-reduced-motion`;
- do not animate at an unnecessarily high frame rate.

---

# 8. 2D MAP — QUALITY REQUIREMENTS

The 2D view should be operational rather than decorative.

It should support:

- world view;
- regional zoom;
- pan;
- zoom;
- event markers;
- event selection;
- event highlighting;
- layer toggling;
- viewport-aware rendering;
- contextual layers where supported;
- detections;
- sources;
- filters;
- time ranges.

Use MapLibre GL JS.

The frontend must render backend GIS data.

Do not recreate scientific geospatial calculations in the browser.

---

# 9. 2D / 3D SWITCHING

The top map toolbar should contain an obvious segmented control:

```text
┌────────┬────────┐
│   2D   │   3D   │
└────────┴────────┘
```

The active mode should be visually unmistakable.

Recommended:

- active control = bright primary accent;
- inactive control = dark neutral surface;
- transition = quick, smooth, subtle;
- no full-page reload.

Switching modes should preserve:

- selected event where possible;
- active filters;
- active layers;
- current time range;
- application state.

If exact geographic camera preservation is technically difficult, prefer a clean transition to a sensible world/regional view rather than a broken or disorienting camera state.

---

# 10. FIRE / THERMAL EVENT MARKERS

This is a major visual signature.

## 10.1 Marker design

The marker should visually communicate heat without becoming childish.

Primary visual:

**🔥**

Possible treatment:

- emoji marker for immediate recognizability;
- subtle outer glow;
- animated pulse;
- variable scale based on event importance;
- stronger glow for higher-severity/priority events;
- selected marker receives a larger ring/halo.

Do not use huge emojis that cover the map.

## 10.2 Marker states

At minimum:

### Normal

```text
🔥
```

### Hover

```text
   ◉
  🔥
```

with subtle scale-up and tooltip.

### Selected

```text
   ╭─────╮
   │ 🔥  │
   ╰─────╯
```

with a strong but restrained selection ring.

### Review required

Use an additional visual cue such as:

```text
🔥  !
```

or a small review badge.

Do not rely on color alone.

### Unknown

Do not visually imply `unknown == non-industrial`.

This distinction is scientifically locked.

---

# 11. FIRE ANIMATION

Animation should be **subtle, smooth, and GPU-friendly**.

Possible animation:

```text
scale: 0.96 → 1.04 → 0.96
opacity: 0.90 → 1.00 → 0.90
glow: subtle pulse
```

Duration:

approximately 1.2–2.0 seconds depending on marker importance.

Use staggered animation phases.

Do not make every fire pulse in perfect synchronization.

That would look artificial.

For many events:

- animate only visible/high-priority events;
- use CSS/transform-based animation where possible;
- avoid hundreds of independent JS timers;
- avoid React re-rendering every animation frame;
- prefer renderer-level animation or CSS.

---

# 12. EVENT IMPORTANCE VISUAL ENCODING

Do not make marker size purely decorative.

Potential mapping:

```text
event importance
      ↓
marker scale
      +
glow intensity
      +
selection priority
```

Possible factors:

- severity;
- confidence;
- persistence;
- FRP;
- review state;
- event type.

However, **the frontend must not invent a new scientific score**.

If the backend provides a priority/severity value, consume it.

If it does not, use a simple UI-only size hierarchy and clearly treat it as visual emphasis rather than a scientific ranking.

---

# 13. LAYER SYSTEM

The layer panel is inspired strongly by the supplied screenshots.

It should appear as a compact floating control panel over the map.

Conceptually:

```text
┌────────────────────────────────────┐
│ LAYERS                         ▼   │
├────────────────────────────────────┤
│ Search layers...                   │
├────────────────────────────────────┤
│ □ 🔥 All Thermal Events       ⓘ   │
│ □ 🏭 Industrial              ⓘ   │
│ □ 🌲 Natural / Vegetation     ⓘ   │
│ □ 🌾 Agricultural             ⓘ   │
│ □ 🛢️ Oil / Gas / Flare         ⓘ   │
│ □ ⚡ Thermal Power             ⓘ   │
│ □ ⛏️ Mining / Extraction       ⓘ   │
│ □ 🔥 Persistent Sources        ⓘ   │
│ □ ⚠️ Review Required           ⓘ   │
│ □ ? Unknown / Uncertain        ⓘ   │
│ □ 📡 Raw FIRMS Detections      ⓘ   │
└────────────────────────────────────┘
```

## IMPORTANT

The actual classification names must be driven by the backend taxonomy.

Do **not** invent classes that the model does not support.

The above list is a UI concept.

Before implementation:

1. inspect the production classification schema;
2. inspect the event/intelligence API;
3. inspect the actual model class taxonomy;
4. map backend values to display labels;
5. preserve `unknown` separately;
6. never silently merge unsupported classes.

---

# 14. LAYER CATEGORIES

Organize layers logically.

## A. Core thermal layers

- All thermal events
- Recent thermal events
- Raw FIRMS detections

## B. Classification layers

Only expose classes actually supported by the backend, for example:

- Industrial
- Non-industrial
- Unknown
- Review Required

If a more granular taxonomy exists, expose those categories.

## C. Context layers

Where API support exists:

- industrial infrastructure;
- land-cover/context;
- persistent source;
- contextual evidence.

## D. Quality / review layers

- high confidence;
- low confidence;
- review required;
- abstained/uncertain.

---

# 15. LAYER PANEL UX

Requirements:

- floating over the map;
- compact;
- draggable only if genuinely useful;
- collapsible;
- scrollable;
- searchable if there are many layers;
- keyboard accessible;
- active state obvious;
- hover state subtle;
- info icon available;
- no giant panel consuming the map.

The panel should feel like a professional GIS control, not a generic dropdown.

---

# 16. TOP APPLICATION BAR

The top bar should resemble a compact operational command header.

Conceptual structure:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🌐 SIH26   THERMAL MONITOR   ● LIVE   [Global ▼]   [MISSION]   [STATUS]   │
└─────────────────────────────────────────────────────────────────────────────┘
```

Potential items:

- application identity;
- LIVE/connection status;
- current geography;
- mission/demo indicator;
- event count;
- search;
- settings;
- fullscreen;
- time;
- system health.

Do not blindly copy World Monitor's labels.

Use terminology relevant to this product.

---

# 17. APPLICATION TITLE

Preferred identity:

**THERMAL MONITOR**

or a final project-approved brand.

Secondary identity:

**SIH26**

Possible descriptor:

**THERMAL INTELLIGENCE**

The application should look like a real product, not:

`SIH Project Dashboard`

Avoid student-project-looking branding.

---

# 18. TIME / LIVE STATUS

The interface should expose temporal state.

Possible header:

```text
GLOBAL SITUATION
MON, 31 AUG 2026 13:11:03 UTC
```

Requirements:

- UTC should be used where operational timestamps are shown;
- local time may be offered as secondary information;
- live status must be honest;
- never label historical/static data as live;
- show last updated timestamp when data is cached;
- show data freshness where useful.

Example:

```text
● LIVE
Updated 24s ago
```

or:

```text
● SNAPSHOT
31 Aug 2026 · 13:11 UTC
```

---

# 19. RIGHT-SIDE INTELLIGENCE PANEL

The screenshots show a strong right-side information column.

For SIH26, adapt it to thermal intelligence.

Recommended structure:

```text
┌──────────────────────────────────┐
│ THERMAL INTELLIGENCE             │
├──────────────────────────────────┤
│ ACTIVE EVENTS              128   │
│ INDUSTRIAL                  24   │
│ REVIEW REQUIRED              7   │
│ UNKNOWN                     13   │
├──────────────────────────────────┤
│ RECENT INTELLIGENCE              │
│                                  │
│ 🔥 Event detected                │
│ Industrial probability: 94%      │
│ Context: refinery               │
│ Review: not required             │
└──────────────────────────────────┘
```

This is not mandatory exact content.

The panel should be driven by actual API data.

---

# 20. EVENT DETAIL PANEL

Selecting an event should open a detail interface.

The detail panel is one of the most important product surfaces.

Suggested sections:

## EVENT

- Event ID
- event type
- source
- start time
- end time
- duration
- latitude
- longitude
- detection count
- FRP where available
- geometry

## CLASSIFICATION

- predicted class;
- confidence;
- model name;
- model version;
- feature schema version;
- classification mode if exposed.

## CONTEXT

- context label;
- context confidence;
- nearby infrastructure;
- land-use/context evidence;
- spatial relationship;
- temporal relationship.

## UNCERTAINTY

- review required;
- abstained;
- uncertainty state;
- reason.

## PROVENANCE

- FIRMS;
- satellite;
- instrument;
- acquisition timestamps;
- source metadata.

Only display fields actually provided by the backend.

Do not fabricate data.

---

# 21. EVENT DETAIL VISUAL DESIGN

The panel should not be one giant wall of JSON.

Bad:

```text
{
  "event_id": "...",
  "confidence": 0.94,
  ...
}
```

Good:

```text
┌──────────────────────────────────────┐
│ 🔥  EVENT-2026-00142            ×   │
│ INDUSTRIAL                         │
│                                      │
│ 94% CONFIDENCE                       │
│                                      │
│ ─────────────────────────────────── │
│ LOCATION                             │
│ 22.31° N, 70.82° E                  │
│                                      │
│ TIMELINE                             │
│ 31 Aug · 09:42 → 10:16 UTC          │
│                                      │
│ CONTEXT                              │
│ 🏭 Industrial facility nearby       │
│                                      │
│ REVIEW                               │
│ ✓ No review required                │
└──────────────────────────────────────┘
```

---

# 22. CONFIDENCE DISPLAY

Confidence should be understandable.

Preferred:

```text
94%
HIGH CONFIDENCE
```

Avoid requiring users to interpret:

`0.94`.

Where appropriate:

```text
Industrial
94% confidence
```

Do not imply that confidence equals certainty.

Use the backend's semantic meaning.

---

# 23. UNKNOWN / ABSTENTION

This is scientifically important.

The UI must preserve:

```text
UNKNOWN
```

as distinct from:

```text
NON-INDUSTRIAL
```

Also preserve:

```text
ABSTAINED
```

or:

```text
REVIEW REQUIRED
```

if provided.

Never turn:

```text
unknown
```

into:

```text
non-industrial
```

for visual convenience.

Never hide abstention.

Uncertainty should be a first-class UX state.

---

# 24. EVIDENCE DISPLAY

The system is evidence-first.

The UI should make evidence understandable.

Example:

```text
WHY THIS CLASSIFICATION?

✓ High-confidence FIRMS detection
✓ Persistent thermal behavior
✓ Industrial facility within context radius
✓ Supporting land-use context

CONFLICTS

⚠ Context evidence is incomplete
```

The UI should distinguish:

- evidence;
- model prediction;
- contextual signal;
- uncertainty;
- final intelligence state.

Do not make contextual evidence look like ground truth.

---

# 25. MODEL PROVENANCE

The frontend must not hard-code the production model name.

The backend remains authoritative.

If provided, display:

```text
MODEL
Production classifier

VERSION
x.y.z

FEATURE SCHEMA
feat_v1.0.0
```

This is valuable in analyst/debug views.

Do not expose implementation details such as raw sklearn objects.

---

# 26. SEARCH

Search should be useful but not overbuilt.

Potential search targets:

- event ID;
- location;
- region;
- source;
- classification.

If event search is not supported by the backend, do not build a fake universal search.

A compact search control may exist in the top bar.

Keyboard shortcut:

`Ctrl/Cmd + K`

may be added only if it can be implemented cleanly within the time budget.

---

# 27. FILTERS

Filters should be compact.

Minimum useful filters:

### Classification

- All
- Industrial
- Non-industrial
- Unknown

### Confidence

- All
- High
- Medium
- Low

### Review

- All
- Review required
- No review required

### Time

- 1h
- 6h
- 24h
- 48h
- 7d
- All
- Custom range if API supports it

### Geography

- current viewport where supported.

Do not implement filters that require backend data unavailable from the API.

---

# 28. TIME CONTROL

A compact time selector should sit near the map.

Inspired by the supplied UI:

```text
┌────┬────┬─────┬─────┬────┬────┐
│ 1h │ 6h │ 24h │ 48h │ 7d │ All│
└────┴────┴─────┴─────┴────┴────┘
```

Active state:

- bright accent;
- clear contrast.

Inactive state:

- dark surface;
- subtle border.

The time control must update the data source through the API.

It must not merely hide markers locally if the backend query is intended to be authoritative.

---

# 29. MAP CONTROLS

Right side of map:

```text
┌────┐
│ +  │
├────┤
│ −  │
├────┤
│ ⌂  │
└────┘
```

Additional controls:

- 2D/3D;
- fullscreen;
- reset camera;
- layer panel;
- optional legend.

Controls should:

- be compact;
- use consistent dimensions;
- have clear hover feedback;
- have tooltips;
- remain usable on smaller screens.

---

# 30. LEGEND

The legend should explain visual encoding.

Example:

```text
THERMAL EVENTS

🔥 Industrial
🔥 Non-industrial
?  Unknown
⚠ Review required

MARKER SIZE
Larger = stronger visual emphasis
```

Do not claim a semantic relationship that does not exist.

---

# 31. COLOR SYSTEM

All components must use design tokens.

Do not scatter hard-coded colors across components.

## 31.1 Core tokens

```css
:root {
  --bg-base: #07090d;
  --bg-surface: #0d1117;
  --bg-surface-raised: #121821;
  --bg-surface-hover: #171f29;
  --bg-surface-active: #1b2632;

  --text-primary: #f2f5f7;
  --text-secondary: #b5bec8;
  --text-muted: #737e89;
  --text-disabled: #4b545e;

  --accent-primary: #39ff88;
  --accent-primary-soft: rgba(57, 255, 136, 0.16);
  --accent-cyan: #00d9ff;
  --accent-blue: #4da3ff;

  --state-success: #39ff88;
  --state-warning: #ffbf24;
  --state-error: #ff4d5a;
  --state-info: #49b9ff;

  --border-default: #252c35;
  --border-strong: #3a434e;
  --border-active: #39ff88;

  --overlay-backdrop: rgba(0, 0, 0, 0.62);

  --thermal-primary: #ff6a00;
  --thermal-hot: #ff3d2e;
  --thermal-glow: rgba(255, 106, 0, 0.38);
}
```

These are the **initial locked visual tokens**.

If the existing repository already contains a coherent token system, integrate these concepts into that system rather than creating duplicates.

## 31.2 Color semantics

Green:

- active;
- healthy;
- live;
- selected;
- confirmed UI state.

Cyan:

- technical;
- geographic;
- information;
- map controls.

Orange/red:

- thermal intensity;
- alert;
- review;
- high-priority state.

Yellow:

- warning;
- medium severity.

Do not use red everywhere.

Red should retain meaning.

---

# 32. TYPOGRAPHY

Use a highly legible modern sans for primary UI.

Recommended:

```text
Inter
```

or the project's existing equivalent.

For technical metadata and timestamps:

```text
JetBrains Mono
```

or:

```text
Geist Mono
```

## Typography hierarchy

Application title:

- uppercase;
- compact;
- letter spacing;
- medium/bold.

Section title:

- uppercase;
- mono or technical sans;
- 12–14px;
- letter spacing around 0.08em.

Primary value:

- 18–32px depending on importance.

Metadata:

- 11–13px.

Timestamp:

- mono;
- 11–12px.

Avoid excessive font-size variation.

---

# 33. BORDER RADIUS

The visual reference uses mostly restrained corners.

Recommended:

```text
small controls: 4px
cards/panels: 6px
large overlays: 8px
pills/status badges: 9999px
```

Avoid making every component a large rounded card.

---

# 34. BORDERS

Borders are an important part of the command-console aesthetic.

Use:

```css
border: 1px solid var(--border-default);
```

for normal surfaces.

Use stronger borders for:

- selected items;
- active tabs;
- focused controls;
- important alerts.

Avoid heavy drop shadows.

Prefer:

- border;
- subtle inset highlight;
- restrained shadow.

---

# 35. GLASS / SURFACE TREATMENT

Use only subtle transparency.

Good:

```text
rgba(13, 17, 23, 0.88)
backdrop-filter: blur(...)
```

Bad:

- translucent everything;
- giant frosted-glass cards;
- rainbow gradients;
- excessive blur.

The interface should remain readable and fast.

---

# 36. LAYOUT ARCHITECTURE

The main screen should be approximately:

```text
┌───────────────────────────────────────────────────────────────────────┐
│ TOP BAR                                                               │
├───────────────────────────────────────────────────────────────────────┤
│                                                                       │
│                    MAP / GLOBE WORKSPACE                             │
│                                                                       │
│   ┌───────────────┐                              ┌────────────────┐   │
│   │ LAYERS        │                              │ INTELLIGENCE   │   │
│   │               │                              │                │   │
│   │ filters       │                              │ summary        │   │
│   │ categories    │                              │ selected event │   │
│   └───────────────┘                              └────────────────┘   │
│                                                                       │
│                map controls                     details              │
│                                                                       │
├───────────────────────────────────────────────────────────────────────┤
│ TIME / STATUS / LEGEND                                                │
└───────────────────────────────────────────────────────────────────────┘
```

The map must retain the largest visual area.

---

# 37. RESPONSIVE BEHAVIOR

Desktop is the primary target.

Still support:

- laptop;
- large desktop;
- tablet;
- narrow screens.

For smaller screens:

- side panels become drawers;
- layer panel becomes a compact sheet;
- event detail becomes bottom sheet/full-height panel;
- map remains primary;
- controls remain reachable.

Do not try to reproduce the full desktop density on a phone.

---

# 38. RECOMMENDED FRONTEND FOLDER STRUCTURE

The target structure is:

```text
apps/
└── web/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   ├── globals.css
    │   └── api/
    │       └── ...
    │
    ├── components/
    │   ├── app-shell/
    │   │   ├── AppShell.tsx
    │   │   ├── TopBar.tsx
    │   │   ├── StatusBar.tsx
    │   │   └── Workspace.tsx
    │   │
    │   ├── map/
    │   │   ├── MapWorkspace.tsx
    │   │   ├── GlobeView.tsx
    │   │   ├── FlatMapView.tsx
    │   │   ├── MapControls.tsx
    │   │   ├── ViewModeToggle.tsx
    │   │   ├── LayerPanel.tsx
    │   │   ├── LayerRow.tsx
    │   │   ├── MapLegend.tsx
    │   │   ├── TimeControl.tsx
    │   │   ├── EventMarker.tsx
    │   │   ├── EventMarkerOverlay.tsx
    │   │   └── CameraController.tsx
    │   │
    │   ├── events/
    │   │   ├── EventDetailPanel.tsx
    │   │   ├── EventSummary.tsx
    │   │   ├── EventClassification.tsx
    │   │   ├── EventContext.tsx
    │   │   ├── EventEvidence.tsx
    │   │   ├── EventUncertainty.tsx
    │   │   ├── EventProvenance.tsx
    │   │   └── EventTimeline.tsx
    │   │
    │   ├── intelligence/
    │   │   ├── IntelligencePanel.tsx
    │   │   ├── IntelligenceSummary.tsx
    │   │   ├── ConfidenceIndicator.tsx
    │   │   ├── ReviewBadge.tsx
    │   │   └── EvidenceList.tsx
    │   │
    │   ├── filters/
    │   │   ├── FilterBar.tsx
    │   │   ├── ClassificationFilter.tsx
    │   │   ├── ConfidenceFilter.tsx
    │   │   └── ReviewFilter.tsx
    │   │
    │   └── ui/
    │       ├── Badge.tsx
    │       ├── StatusDot.tsx
    │       ├── Tooltip.tsx
    │       ├── Panel.tsx
    │       └── ...
    │
    ├── lib/
    │   ├── api/
    │   │   ├── client.ts
    │   │   ├── events.ts
    │   │   ├── detections.ts
    │   │   ├── layers.ts
    │   │   ├── inference.ts
    │   │   └── sources.ts
    │   │
    │   ├── map/
    │   │   ├── globe.ts
    │   │   ├── maplibre.ts
    │   │   ├── layers.ts
    │   │   ├── markers.ts
    │   │   └── camera.ts
    │   │
    │   ├── format/
    │   │   ├── dates.ts
    │   │   ├── numbers.ts
    │   │   └── coordinates.ts
    │   │
    │   └── utils.ts
    │
    ├── hooks/
    │   ├── useEvents.ts
    │   ├── useDetections.ts
    │   ├── useLayers.ts
    │   ├── useInference.ts
    │   ├── useSelectedEvent.ts
    │   ├── useMapMode.ts
    │   └── useFilters.ts
    │
    ├── types/
    │   ├── api.ts
    │   ├── event.ts
    │   ├── layer.ts
    │   ├── intelligence.ts
    │   └── map.ts
    │
    ├── config/
    │   ├── layers.ts
    │   ├── map.ts
    │   └── ui.ts
    │
    ├── public/
    │   ├── textures/
    │   ├── icons/
    │   └── ...
    │
    └── package.json
```

This is a target structure, not a mandate to create empty files.

Do not create directories simply because they look architecturally impressive.

---

# 39. COMPONENT RESPONSIBILITY RULE

Every component should have one clear responsibility.

Bad:

`DashboardEverything.tsx`

Good:

```text
MapWorkspace
LayerPanel
EventMarker
EventDetailPanel
IntelligencePanel
```

Do not build a 1,500-line page component.

---

# 40. STATE ARCHITECTURE

Use three categories.

## Server state

Handled by TanStack Query:

- events;
- detections;
- layers;
- intelligence;
- sources;
- health/readiness.

## UI state

React state/hooks:

- selected event;
- open/closed panels;
- 2D/3D mode;
- active layer toggles;
- filters;
- hover state;
- camera mode.

## URL state

Use URL/query parameters only where useful:

- geography;
- selected event;
- time range;
- map mode.

Do not make every UI interaction a URL mutation.

---

# 41. API ARCHITECTURE

Create a typed API client.

Do not scatter:

```ts
fetch(...)
```

throughout components.

Prefer:

```text
lib/api/
    client
    events
    detections
    layers
    inference
    sources
```

Components consume hooks.

Hooks consume the API client.

The API client consumes the backend.

```text
Component
    ↓
Hook
    ↓
Typed API client
    ↓
FastAPI
```

---

# 42. API CONTRACT AUTHORITY

The actual backend schemas are authoritative.

Before implementing TypeScript types:

1. inspect `services/api/`;
2. inspect API routes;
3. inspect Pydantic schemas;
4. inspect `packages/schemas/`;
5. inspect OpenAPI if available;
6. inspect GIS serialization;
7. inspect intelligence output.

Do not blindly copy conceptual examples from documentation.

If OpenAPI generation is practical, use generated TypeScript types.

If not, maintain a small, explicit typed client that matches the real contract.

---

# 43. GIS CONTRACT RULES

GeoJSON is authoritative for GIS layers.

Remember:

```text
GeoJSON coordinates = [longitude, latitude]
```

Do not swap:

```text
latitude ↔ longitude
```

Do not:

- recompute event centroids in the browser;
- recreate scientific clustering;
- run Haversine logic for domain decisions;
- alter backend event identity;
- invent frontend event IDs.

The backend event is canonical.

The frontend may create a UI view model, but it must preserve the canonical event identity.

---

# 44. SCIENTIFIC INVARIANTS THE UI MUST PRESERVE

These are locked.

1. `UNKNOWN != NON_INDUSTRIAL`
2. Context is evidence, not ground truth.
3. Abstention remains abstention.
4. ML/context conflicts remain visible where provided.
5. Model provenance remains traceable.
6. Event IDs remain stable.
7. Historical timestamps must not be mutated.
8. Frontend must not introduce scientific inference.
9. Frontend must not silently overwrite backend classifications.
10. Missing evidence must remain visibly missing.
11. Confidence must not be represented as certainty.
12. The backend remains scientifically authoritative.

---

# 45. ERROR STATES

Never show:

```text
Something went wrong.
```

for every failure.

Use specific states.

## Backend unavailable

```text
INTELLIGENCE SERVICE UNAVAILABLE
Unable to reach the analysis service.
Retry
```

## No events

```text
NO THERMAL EVENTS
No events match the current region and time range.
```

## Missing context

```text
CONTEXT UNAVAILABLE
No contextual evidence is available for this event.
```

## Model abstained

```text
REVIEW REQUIRED
The model did not have sufficient evidence for a confident classification.
```

## Partial failure

```text
PARTIAL DATA
Thermal events loaded. Context data is currently unavailable.
```

---

# 46. LOADING UX

Avoid giant spinners.

Prefer:

- skeleton panels;
- subtle status indicators;
- map loading state;
- progressive data loading;
- preserve existing content during refetch;
- show "updating" rather than blanking the screen.

Example:

```text
● LIVE
Updating thermal events...
```

Do not make the whole screen disappear while a small panel is refreshing.

---

# 47. EMPTY STATES

Empty state should explain the reason.

Examples:

```text
NO EVENTS IN VIEW
Try widening the time range.
```

or:

```text
NO REVIEW ITEMS
No events currently require analyst review.
```

---

# 48. PERFORMANCE RULES

Performance is a first-class requirement.

## 48.1 React

Avoid:

- unnecessary global state;
- whole-page rerenders;
- recreating large GeoJSON objects on every render;
- expensive calculations in render;
- inline object churn for high-frequency map components.

## 48.2 Map

Use:

- renderer-native layers;
- memoized data;
- viewport-aware rendering;
- batching;
- efficient GeoJSON;
- marker limits where necessary.

## 48.3 Globe

Do not create a separate React component for every continuously animated frame.

Animation should occur in the visualization engine.

## 48.4 Data

Use TanStack Query caching.

Do not repeatedly refetch unchanged data.

## 48.5 Large datasets

If event counts become large:

- use backend viewport queries if available;
- use map-native rendering;
- use visual clustering only when needed;
- do not move scientific clustering into the browser.

---

# 49. TARGET PERFORMANCE

For normal demo workloads:

- smooth 60-ish FPS interaction where hardware allows;
- no visible lag when dragging the map;
- no marker jitter;
- no layout thrashing;
- fast panel transitions;
- fast event selection;
- no full-screen loading flashes.

On weaker hardware:

- graceful degradation;
- fewer animations;
- reduced marker effects;
- still usable.

---

# 50. ANIMATION SYSTEM

Animation should reinforce hierarchy.

Use motion for:

- panel opening;
- panel closing;
- marker selection;
- marker pulse;
- status changes;
- mode switching;
- hover states;
- data refresh.

Avoid animation for:

- every label;
- every card;
- every list item simultaneously;
- decorative purposes without information value.

Preferred durations:

```text
micro interaction: 100–160ms
small transition: 160–220ms
panel transition: 220–320ms
camera transition: 400–800ms
```

Use easing that feels controlled.

---

# 51. ACCESSIBILITY

Even though this is a visually dense technical application:

- buttons must have labels;
- icon-only buttons require tooltips/aria-labels;
- focus states must remain visible;
- keyboard navigation must work for controls;
- color must not be the only semantic indicator;
- reduced-motion preference must be respected;
- text contrast must remain readable;
- event state must have text/icon representation.

---

# 52. ICONOGRAPHY

Use Lucide React for UI controls.

Recommended:

- Layers
- Search
- Maximize
- Minimize
- Home
- Plus
- Minus
- Settings
- Info
- X
- ChevronDown
- ChevronRight
- RefreshCw
- AlertTriangle
- CircleCheck
- CircleHelp
- Satellite
- Map
- Globe
- Clock
- Filter

Use emoji only where they provide a meaningful visual identity, especially for thermal events.

Do not replace every icon with an emoji.

---

# 53. MAP LABELS

Labels should be restrained.

Avoid clutter.

World-scale:

- country labels;
- major regions;
- major cities only if useful.

Zoomed:

- local labels;
- relevant infrastructure if API supports it.

The thermal events remain the primary signal.

---

# 54. VISUAL DEPTH

The UI should have a clear z-index hierarchy:

```text
background
↓
map
↓
map data
↓
map controls
↓
floating layer panel
↓
top navigation
↓
event selection overlays
↓
detail drawers/modals
↓
system alerts/toasts
```

Avoid arbitrary z-index values everywhere.

Centralize important layer ordering.

---

# 55. PANEL SYSTEM

All floating panels should share a common visual language.

Panel:

```text
background:
  --bg-surface

border:
  --border-default

radius:
  6px

shadow:
  subtle

header:
  technical uppercase typography

padding:
  compact
```

This creates cohesion.

---

# 56. STATUS INDICATORS

Use small status dots.

Example:

```text
● LIVE
```

Green dot = healthy/live.

Yellow = degraded/stale.

Red = unavailable/error.

Gray = offline/unknown.

The text must accompany the color.

---

# 57. CONNECTION / DATA FRESHNESS

Top-level status should ideally expose:

```text
● LIVE
```

and optionally:

```text
Last update 18s ago
```

Do not fake live updates.

If the backend is historical/demo data:

```text
● DEMO SNAPSHOT
```

or another truthful state should be used.

---

# 58. FOOTER / SYSTEM BAR

A thin bottom status bar may contain:

```text
THERMAL MONITOR
FIRMS
EVENTS 128
LAST UPDATE 13:11 UTC
API HEALTH ●
```

This is optional if it improves the desktop layout.

Do not let a footer consume valuable map area.

---

# 59. FRONTEND IMPLEMENTATION PLAN

The implementation is intentionally divided into small agent-sized phases.

The rule is:

**3 tasks → visual checkpoint → continue.**

Never let an agent run an enormous ambiguous task.

---

# 60. PHASE 0 — RECONNAISSANCE

### Task 1 — Inspect `apps/web`

Agent must:

- inspect recursively;
- identify framework;
- identify package manager;
- identify existing components;
- identify existing CSS;
- identify build scripts;
- identify current route structure.

### Task 2 — Inspect backend API

Inspect:

- `services/api/app.py`;
- all relevant routes;
- schemas;
- OpenAPI;
- CORS.

### Task 3 — Inspect GIS/intelligence contracts

Inspect:

- `packages/schemas/`;
- `packages/geospatial/`;
- events;
- detections;
- inference/intelligence;
- actual JSON/GeoJSON output.

## CHECKPOINT 0

Expected result:

A short reconnaissance report containing:

- current frontend stack;
- existing files;
- actual API base URL;
- available endpoints;
- event schema;
- GIS schema;
- intelligence schema;
- genuine blockers.

No UI should be substantially built before this information is known.

---

# 61. PHASE 1 — FOUNDATION

### Task 4 — Establish design tokens

Implement:

- colors;
- typography;
- borders;
- radius;
- shadows;
- status states.

### Task 5 — Build AppShell

Implement:

- full viewport;
- top bar;
- map workspace;
- panel regions;
- status area.

### Task 6 — Build reusable UI primitives

Implement:

- Panel;
- StatusDot;
- Badge;
- IconButton;
- Tooltip;
- segmented control.

## CHECKPOINT 1

Expected visual:

A convincing dark intelligence-console shell with:

- top bar;
- map-sized central workspace;
- floating panels;
- correct typography;
- polished controls.

It should already look like a serious product even before the real map is integrated.

---

# 62. PHASE 2 — MAP ENGINE

### Task 7 — Build 2D Map

Implement:

- MapLibre;
- basemap;
- navigation;
- resize handling;
- cleanup.

### Task 8 — Build 3D Globe

Implement:

- globe.gl;
- Three.js;
- Earth texture;
- atmosphere;
- rotation;
- interaction;
- resize.

### Task 9 — Build 2D/3D toggle

Implement:

- segmented control;
- mode state;
- renderer mounting/unmounting;
- sensible transition.

## CHECKPOINT 2

Expected visual:

A beautiful operational map experience:

- 2D map works;
- 3D globe works;
- globe rotates smoothly;
- controls work;
- 2D/3D toggle works;
- no console errors;
- no obvious jank.

This is a **major visual checkpoint**.

---

# 63. PHASE 3 — THERMAL EVENTS

### Task 10 — API event query

Implement typed event fetching.

### Task 11 — Event rendering

Implement:

- fire markers;
- event coordinates;
- visible event set;
- selection;
- hover.

### Task 12 — Marker animation/polish

Implement:

- subtle pulse;
- selected state;
- review state;
- visual hierarchy.

## CHECKPOINT 3

Expected visual:

The globe/map should now show **real backend thermal events** as beautiful animated fire markers.

User can:

- see fires;
- hover;
- click;
- select.

No fake production data should be required if real API data exists.

---

# 64. PHASE 4 — LAYERS

### Task 13 — Layer configuration

Create backend-aligned layer metadata.

### Task 14 — Layer panel

Implement:

- search;
- groups;
- toggles;
- info buttons;
- scrolling.

### Task 15 — Layer integration

Connect layer state to the actual map.

## CHECKPOINT 4

Expected visual:

A World Monitor-inspired floating Layers panel with real SIH26 categories and functional toggles.

---

# 65. PHASE 5 — EVENT INTELLIGENCE

### Task 16 — Event detail shell

Build the panel.

### Task 17 — Classification/confidence

Show:

- predicted class;
- confidence;
- review;
- uncertainty.

### Task 18 — Context/evidence/provenance

Show:

- context;
- evidence;
- model provenance;
- source.

## CHECKPOINT 5

Expected visual:

Clicking a fire produces an analyst-grade event intelligence panel.

The user should understand:

```text
WHERE
WHEN
WHAT
HOW CONFIDENT
WHY
EVIDENCE
REVIEW?
SOURCE
```

---

# 66. PHASE 6 — FILTERS/TIME

### Task 19 — Classification filter

### Task 20 — Time control

### Task 21 — Confidence/review filters

## CHECKPOINT 6

Expected visual:

The map becomes an actual investigation tool rather than a static visualization.

---

# 67. PHASE 7 — POLISH

### Task 22 — Loading/error/empty states

### Task 23 — Animation/performance pass

### Task 24 — Responsive/accessibility pass

## CHECKPOINT 7

Expected visual:

The entire interface should feel cohesive and production-like.

---

# 68. PHASE 8 — FINAL INTEGRATION

### Task 25 — End-to-end API/browser test

### Task 26 — Regression test

### Task 27 — Demo polish

## FINAL CHECKPOINT

The application must demonstrate:

```text
OPEN APP
  ↓
SEE GLOBE
  ↓
SEE THERMAL EVENTS
  ↓
SWITCH 2D/3D
  ↓
TOGGLE LAYERS
  ↓
FILTER EVENTS
  ↓
SELECT FIRE
  ↓
SEE INTELLIGENCE
  ↓
SEE CONFIDENCE
  ↓
SEE CONTEXT/EVIDENCE
  ↓
SEE UNCERTAINTY
```

---

# 69. AGENT EXECUTION RULES

Every agent prompt should explicitly tell the agent:

1. Read this file first.
2. Inspect existing code before changing anything.
3. Reuse existing components.
4. Do not redesign the backend.
5. Do not invent API contracts.
6. Do not create fake scientific data.
7. Keep changes scoped to the task.
8. Run relevant checks.
9. Fix obvious regressions before finishing.
10. Report files changed.
11. Report tests/checks run.
12. Report anything blocked.
13. Do not modify unrelated areas.

---

# 70. AGENT TASK SIZE

A good agent task should generally change:

- one feature;
- one subsystem;
- a small set of components;
- one API integration;
- one visual surface.

Avoid:

> "Build the entire dashboard."

Prefer:

> "Implement the MapLibre 2D renderer with lifecycle handling and world-level basemap. Do not add event markers yet."

This makes agents reliable.

---

# 71. CHECKPOINT RULE

After every three completed tasks:

STOP.

Do a visual review.

Check:

### Functionality

- Does it work?
- Does it use real data?
- Are there console errors?

### Visual

- Does it resemble the intended aesthetic?
- Are spacing and alignment clean?
- Are borders consistent?
- Is typography correct?

### Interaction

- Are transitions smooth?
- Are controls obvious?
- Is the map responsive?

### Performance

- Is FPS acceptable?
- Are there unnecessary renders?
- Are animations efficient?

### Architecture

- Are responsibilities clean?
- Did the agent duplicate logic?
- Did it create unnecessary dependencies?

Do not continue blindly after a failed checkpoint.

---

# 72. WHAT "DONE" MEANS

Frontend is done when:

## Map

- [ ] high-quality 3D globe;
- [ ] smooth rotation;
- [ ] smooth interaction;
- [ ] 2D map;
- [ ] 2D/3D switch;
- [ ] reset/home;
- [ ] zoom;
- [ ] responsive resize.

## Thermal events

- [ ] real events;
- [ ] fire markers;
- [ ] animation;
- [ ] hover;
- [ ] selection;
- [ ] selected state;
- [ ] review state.

## Layers

- [ ] layer panel;
- [ ] backend-aligned taxonomy;
- [ ] toggles;
- [ ] active state;
- [ ] search if needed;
- [ ] info state.

## Intelligence

- [ ] classification;
- [ ] confidence;
- [ ] context;
- [ ] evidence;
- [ ] provenance;
- [ ] uncertainty;
- [ ] review.

## Filters

- [ ] time;
- [ ] classification;
- [ ] confidence;
- [ ] review.

## UX

- [ ] loading;
- [ ] empty;
- [ ] error;
- [ ] partial data;
- [ ] accessible controls;
- [ ] responsive layout.

## Quality

- [ ] no obvious console errors;
- [ ] no fake live status;
- [ ] no scientific logic duplicated in frontend;
- [ ] no hardcoded backend assumptions;
- [ ] no giant monolithic component;
- [ ] smooth demo flow.

---

# 73. PRIORITY ORDER UNDER TIME PRESSURE

If the 3–4 hour window becomes tight:

## P0 — MUST

1. App shell
2. 3D globe
3. 2D map
4. 2D/3D toggle
5. real thermal events
6. event selection
7. event detail
8. layers
9. classification/confidence

## P1 — HIGH VALUE

10. time filtering
11. review/uncertainty
12. context/evidence
13. polished animations
14. loading/error states

## P2 — NICE TO HAVE

15. advanced charts
16. universal search
17. advanced analytics
18. persistent-source timelines
19. extra responsive optimizations

Never sacrifice P0 to build P2.

---

# 74. DEMO-FIRST VISUAL PRIORITY

For the live demonstration, the strongest sequence is:

### Scene 1

Dark interface loads.

### Scene 2

High-quality Earth globe is visible.

### Scene 3

Globe slowly rotates.

### Scene 4

Thermal fire markers appear.

### Scene 5

User switches to 2D.

### Scene 6

User enables a fire/classification layer.

### Scene 7

User clicks a thermal event.

### Scene 8

Detail panel opens.

### Scene 9

Classification and confidence appear.

### Scene 10

Context/evidence appears.

### Scene 11

User sees uncertainty/review state.

This sequence should feel **instant, coherent, and cinematic without becoming gimmicky**.

---

# 75. ANTI-PATTERNS

Never:

- put the entire app in one component;
- use random colors per component;
- use hard-coded API responses;
- hard-code fake confidence values;
- call the model directly from the browser;
- access PostGIS from the browser;
- expose FIRMS secrets;
- duplicate scientific clustering;
- invent classifications;
- merge unknown into non-industrial;
- hide abstention;
- label snapshots as live;
- create excessive animation;
- make every card rounded;
- use excessive glassmorphism;
- create a generic dashboard template;
- install dependencies without justification;
- restructure the repository for aesthetics;
- rewrite backend code to make the frontend easier.

---

# 76. SECURITY

Browser code may contain only public configuration.

Never expose:

- FIRMS private credentials;
- database credentials;
- Redis credentials;
- model artifact paths;
- internal service secrets;
- server-side tokens.

The browser communicates with FastAPI.

Conceptually:

```text
Browser
   │
   │ HTTP
   ▼
FastAPI
   │
   ├── Events
   ├── Detections
   ├── GIS
   ├── Intelligence
   ├── Sources
   └── Health
```

Never:

```text
Browser → PostGIS
Browser → Redis
Browser → model files
Browser → FIRMS secret API
```

---

# 77. DATA PROVENANCE

When provenance is available, preserve it.

The UI should make it possible to understand:

```text
Observed by
↓
FIRMS

Satellite
↓
[actual backend value]

Acquisition
↓
[actual timestamp]

Processed as
↓
Event

Classified by
↓
[actual production model]

Context
↓
[actual evidence]
```

This strengthens trust.

---

# 78. DESIGN LANGUAGE SUMMARY

The design language can be summarized as:

```text
DARK
+
DENSE
+
TECHNICAL
+
SPATIAL
+
PRECISE
+
MINIMAL
+
ANIMATED
+
OPERATIONAL
```

Not:

```text
COLORFUL
+
PLAYFUL
+
MARKETING
+
CARD-HEAVY
```

---

# 79. FINAL ARCHITECTURAL PICTURE

```text
┌───────────────────────────────────────────────────────────────┐
│                         SIH26 WEB                             │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ TOP BAR                                                 │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────┐   ┌─────────────────────┐   ┌──────────┐ │
│  │ LAYERS        │   │                     │   │ INTEL    │ │
│  │               │   │    MAP WORKSPACE    │   │ PANEL    │ │
│  │ filters       │   │                     │   │          │ │
│  │ categories    │   │     🌍 / 2D         │   │ events   │ │
│  │ toggles       │   │                     │   │ status   │ │
│  │               │   │ 🔥  🔥      🔥      │   │ insight  │ │
│  └───────────────┘   │                     │   └──────────┘ │
│                      │                     │                │
│                      └─────────────────────┘                │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ TIME / STATUS / LEGEND                                  │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘

                            │
                            ▼

                         FastAPI

                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
           Events       GIS Layers    Intelligence
              │             │             │
              └─────────────┼─────────────┘
                            ▼
                    Existing backend
```

---

# 80. FINAL AGENT COMMAND

If there is any ambiguity, the agent should follow this decision hierarchy:

```text
1. Actual backend/API contract
        ↓
2. Existing repository architecture
        ↓
3. This UI context
        ↓
4. Visual reference screenshots
        ↓
5. World Monitor as interaction inspiration
        ↓
6. Agent judgment
```

Never reverse this order.

The screenshots are visual references.

The backend contracts are data truth.

This document is the frontend product/UX constitution.

---

# 81. THE MOST IMPORTANT PRINCIPLE

The backend has already done the difficult scientific work.

The frontend now has one job:

> **Make that intelligence feel obvious.**

A user should not need to understand:

- clustering algorithms;
- feature engineering;
- model calibration;
- PostGIS;
- Pydantic;
- FIRMS ingestion;
- ML internals.

They should be able to look at the interface and immediately understand:

```text
🔥 Something happened.

📍 Here.

🕒 At this time.

🏭 It is likely industrial.

📊 Confidence is high.

🧠 These signals support the assessment.

⚠️ There is / is not uncertainty.

🔎 Here is the evidence.

```

That is the product.

Build the interface that makes the existing system valuable.

---

# 82. LOCK STATUS

**THIS PLAN IS LOCKED.**

Do not change the fundamental:

- architecture;
- visual language;
- map-first strategy;
- 2D/3D requirement;
- backend-authoritative model;
- event-centric workflow;
- layer system;
- checkpoint system;
- implementation order;

unless explicitly instructed by the project owner.

The frontend should evolve through **small, verifiable increments**, not uncontrolled redesign.

**End of UI Context.**
