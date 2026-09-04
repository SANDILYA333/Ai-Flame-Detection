# SIH26162 — PYROSAT-AI / FLAME INTELLIGENCE
## Official Demonstration Runbook & Showcase Guide

---

## 1. Environment Prerequisites

### System Requirements
- Python 3.11+ (Virtualenv at `.venv`)
- Node.js 18+ (npm)
- Operating System: Linux / macOS / Windows WSL2

### Environment Variables
Configure your local `.env` file (copied from `.env.example`). Variable names only:
```env
# NASA FIRMS Ingestion
FIRMS_MAP_KEY=
FIRMS_DEFAULT_SOURCE=VIIRS_NOAA20_NRT

# Emergency Escalation Policy
EMERGENCY_REVIEW_MIN_CONFIDENCE=0.94
EMERGENCY_AUTO_ESCALATION_MIN_CONFIDENCE=0.98

# Real SMS Provider (Fast2SMS)
FAST2SMS_API_KEY=
FAST2SMS_ENABLED=false
FAST2SMS_SENDER_ID=FSTSMS
FAST2SMS_ROUTE=q

# Real WhatsApp Provider (RichAutomate)
RICHAUTOMATE_API_KEY=
RICHAUTOMATE_ENABLED=false
RICHAUTOMATE_BASE_URL=https://api.richautomate.com/v1

# Notification Delivery & Retries
NOTIFICATION_MODE=SIMULATED
NOTIFICATION_TIMEOUT_SECONDS=10.0
NOTIFICATION_MAX_RETRIES=2
NOTIFICATION_RETRY_BACKOFF_SECONDS=0.1
```

> **Security Invariant**: Never commit real API keys or credentials. By default, `NOTIFICATION_MODE=SIMULATED` runs 100% safe offline simulations.

---

## 2. Startup Sequence

Launch the services in separate terminal tabs:

```bash
# Terminal 1: Authoritative FastAPI Backend
cd ~/Coding/SIH-Hackathon
source .venv/bin/activate
uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Next.js Frontend Console
cd ~/Coding/SIH-Hackathon/apps/web
npm run dev
```

Open your browser at:
`http://localhost:3000`

---

## 3. Pre-Flight Verification Checklist

Before starting the judging demonstration:
- [ ] Backend is running at `http://localhost:8000/docs` (FastAPI Swagger UI accessible).
- [ ] Frontend loads at `http://localhost:3000` without console errors.
- [ ] Interactive 2D Map & 3D Globe render thermal event markers across India.
- [ ] Selecting an event highlights the marker and opens the Event Intelligence panel.
- [ ] `OPEN RESPONSE CENTER` button launches the Emergency Response Center modal.
- [ ] Responder Directory renders nearest fire stations and hospitals with geodesic distances.
- [ ] Demo Phone Number input is visible and defaults to `+91 9876543210`.
- [ ] Activity Feed displays the audit trail.

---

## 4. Primary Demonstration Scenario: High-Confidence Industrial Event

**Objective**: Demonstrate end-to-end processing of a major industrial thermal event from satellite detection to verified multi-channel notification.

1. **Step 1 — Event Selection**:
   - On the map or event list, select the primary Jamnagar Refinery event (`evt_75b4be64d755eaf628f7600d` or top high-FRP event).
   - Point out the calibrated confidence ($>98\%$) and industrial classification in the Event Intelligence header.
2. **Step 2 — Tactical & Contextual Evidence**:
   - Show the Planck pyrometry curve (temperature $\approx 1400\text{ K}$) and proximate industrial infrastructure (refining SEZ).
3. **Step 3 — Open Emergency Response Center**:
   - Click **`OPEN RESPONSE CENTER`**.
   - Note the **Authoritative Escalation State** banner: `AUTOMATIC ESCALATION (>98% Confidence)`.
4. **Step 4 — Responder Intelligence**:
   - Show ranked responders:
     - Fire: *Jamnagar Industrial Fire Brigade HQ* (Chemical foam capability, $\approx 1.2\text{ km}$, ETA $\approx 4\text{ min}$).
     - Medical: *GG Government Hospital & Toxic Trauma ICU* (Burn ICU capability).
5. **Step 5 — Multi-Channel Notification**:
   - Click **`NOTIFY`** on the top fire brigade.
   - Confirmation modal opens with SMS and WhatsApp pre-checked.
   - Enter/verify demo destination phone number (`+91 9876543210`).
   - Add analyst directive notes: *"Operational containment team dispatched"*.
   - Click **`CONFIRM & NOTIFY RESPONDER`**.
6. **Step 6 — Authoritative Audit & Delivery Tracking**:
   - The exact banner appears: `"Notification has been sent successfully to +91 9876543210. (SIMULATED)"` (or live provider confirmation if configured).
   - The **Authoritative Response Audit Log** at the bottom immediately updates with:
     - Responder Name & masked phone (`+91 ******3210`)
     - Unique correlation ID (`CORR-evt_...`)
     - Per-channel status badges (`SMS: SIMULATED`, `WHATSAPP: SIMULATED` or `PROVIDER_ACCEPTED`)
     - Timestamp and analyst notes.

---

## 5. Secondary Scenario: Admin Review Required (94% < Conf ≤ 98%)

1. Select an event with $95\%\text{--}98\%$ confidence (e.g. agricultural-adjacent or flare event).
2. Open Response Center.
3. Show the **`ADMIN REVIEW REQUIRED`** banner.
4. Explain to judges: The system **never sends automatic alarms** for ambiguous events. It demands human-in-the-loop analyst confirmation.
5. Click **`NOTIFY`**, approve the prompt, and show that analyst authorization transitions the event state to `ADMIN_CONFIRMED` in the audit log.

---

## 6. Tertiary Scenario: Low-Confidence & Routine Standby (Conf ≤ 94%)

1. Select a routine operational flaring or low-confidence event ($\le 94\%$).
2. Open Response Center.
3. Show the **`STANDBY / MONITOR ONLY`** policy decision.
4. Point out the policy driver: *"Confidence below operational threshold. Emergency dispatch prevented to avoid false alarm fatigue."*

---

## 7. Quaternary Scenario: CRITICAL Medical & Trauma Mobilization

1. Select a `CRITICAL` severity event ($>50\text{ MW}$ FRP or critical infrastructure proximity).
2. Open Response Center.
3. Highlight the red **`CRITICAL MEDICAL MOBILIZATION REQUIRED`** alert.
4. Point out that the system automatically prioritizes the nearest **Burn ICU / Toxic Trauma Unit** rather than a standard primary clinic.
5. Click **`MOBILIZE NDRF / MEDICAL`** to demonstrate rapid disaster mobilization.

---

## 8. Idempotency & Duplicate Suppression Demo

1. In the Response Center, click **`NOTIFY`** and confirm.
2. Immediately attempt to click **`NOTIFY`** a second time for the exact same responder and channel.
3. Show that the backend returns `DUPLICATE_SUPPRESSED` and does not spam the recipient with repeat SMS or WhatsApp messages.
4. Point to the audit log displaying the **`DUPLICATE SUPPRESSED`** protection badge.

---

## 9. Live Provider vs Simulation Toggle

- **Simulation Mode (Default)**:
  Runs offline, formats realistic payloads, validates phone numbers, records audit entries, and generates mock provider receipts (`SIM-SMS-...`, `SIM-WA-...`).
- **Live Mode**:
  Set `FAST2SMS_ENABLED=true` and `FAST2SMS_API_KEY=...` (or `RICHAUTOMATE_ENABLED=true`) in `.env`, and start the backend with `NOTIFICATION_MODE=LIVE`. Dispatches real live SMS and WhatsApp messages to the configured demo destination.

---

## 10. Troubleshooting Runbook

| Symptom | Cause | Remedy |
| :--- | :--- | :--- |
| **Map not loading / blank canvas** | Internet connection or WebGL disabled | Ensure hardware acceleration is enabled; tiles fall back to OSM standard |
| **Response Center shows error** | FastAPI backend not running | Run `uvicorn services.api.main:app --reload` on port 8000 |
| **SMS fails with HTTP 401** | Invalid Fast2SMS API key | Verify `FAST2SMS_API_KEY` in `.env` or run in safe `SIMULATED` mode |
| **Activity feed empty** | Fresh session / server restart | In-memory audit log resets on full restart; send a notification to populate |
| **Duplicate notification blocked** | Idempotency cache active | Expected behavior! Use a different responder or channel to send fresh alerts |
