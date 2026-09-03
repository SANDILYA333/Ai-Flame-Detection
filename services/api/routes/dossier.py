"""FastAPI routes for Tactical Incident Dossiers and reporting (DOSSIER-003)."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from services.api.schemas.dossier import TacticalDossierResponse
from services.api.services.dossier import TacticalDossierService

router = APIRouter(tags=["tactical-dossier"])


@router.get(
    "/events/{event_id}/dossier",
    response_model=TacticalDossierResponse,
    operation_id="get_event_tactical_dossier",
    summary="Generate comprehensive Tactical Incident Dossier",
    description=(
        "Synthesizes complete operational intelligence package for an incident: "
        "classification, Planck pyrometry, CAMEO-NIOSH chemical hazard profile, "
        "Gaussian dispersion plume, and recommended emergency responders."
    ),
)
@router.get(
    "/api/incident-dossier/{event_id}",
    response_model=TacticalDossierResponse,
    operation_id="get_incident_dossier_alias",
    summary="Alias for Tactical Incident Dossier",
    include_in_schema=False,
)
def get_tactical_dossier(event_id: str) -> TacticalDossierResponse:
    """Generate comprehensive Tactical Incident Dossier for a thermal event."""
    return TacticalDossierService.generate_dossier(event_id)


@router.get(
    "/events/{event_id}/dossier/html",
    response_class=HTMLResponse,
    operation_id="get_event_dossier_html",
    summary="Render printable HTML Tactical Incident Dossier report",
    description=(
        "Returns styled, printable HTML briefing document for PDF export."
    ),
)
@router.get(
    "/api/incident-dossier/{event_id}/pdf",
    response_class=HTMLResponse,
    operation_id="get_incident_dossier_pdf_alias",
    summary="Alias for printable HTML dossier",
    include_in_schema=False,
)
def get_dossier_printable_html(event_id: str) -> HTMLResponse:
    """Render high-contrast, printable tactical dossier briefing."""
    dossier = TacticalDossierService.generate_dossier(event_id)

    hazmat_section = ""
    if dossier.hazmat:
        un_codes = ", ".join(dossier.hazmat.un_na_numbers)
        byproducts = ", ".join(dossier.hazmat.toxic_combustion_byproducts)
        iso = dossier.hazmat.initial_isolation_distance_meters
        sec = dossier.hazmat.facility_sector
        cls_name = dossier.hazmat.cameo_hazmat_class
        risk = dossier.hazmat.primary_disaster_risk
        prot = dossier.hazmat.firefighting_protocol
        hazmat_section = (
            '<div class="card">'
            "<h2>⚠️ HAZMAT RISK ASSESSMENT (CAMEO-NIOSH)</h2>"
            '<div class="grid">'
            f"<div><strong>Sector:</strong> {sec}</div>"
            f"<div><strong>Class:</strong> {cls_name}</div>"
            f"<div><strong>UN/NA:</strong> {un_codes}</div>"
            f"<div><strong>Isolation:</strong> {iso}m</div>"
            "</div>"
            f"<p><strong>Hazard:</strong> {risk}</p>"
            f"<p><strong>Byproducts:</strong> {byproducts}</p>"
            f"<p><strong>Protocol:</strong> {prot}</p>"
            "</div>"
        )

    responders_rows = "".join(
        "<tr>"
        f"<td><strong>{r.name}</strong><br><small>{r.type}</small></td>"
        f"<td>{r.formatted_distance}</td>"
        f"<td><strong>{r.formatted_eta}</strong></td>"
        f"<td>{r.phone}</td>"
        "</tr>"
        for r in dossier.recommended_responders
    )

    ops_items = "".join(
        f"<li>{rec}</li>" for rec in dossier.operational_recommendations
    )

    conf_pct = dossier.confidence * 100.0
    ts_str = dossier.generated_at.strftime("%Y-%m-%d %H:%M UTC")
    emitter_c = dossier.pyrometry.emitter_temp_k - 273.15

    styles = (
        "body { font-family: sans-serif; background: #0c0d12; color: #e2e8f0; "
        "padding: 20px; font-size: 13px; }\n"
        ".container { max-width: 850px; margin: 0 auto; background: #11131a; "
        "border: 1px solid #232836; border-radius: 8px; padding: 20px; }\n"
        ".header { border-bottom: 2px solid #ef4444; padding-bottom: 10px; "
        "margin-bottom: 16px; display: flex; justify-content: space-between; }\n"
        ".card { background: #161922; border: 1px solid #1e2230; "
        "border-radius: 6px; padding: 12px; margin-bottom: 12px; }\n"
        ".card h2 { font-size: 12px; color: #38bdf8; margin: 0 0 8px 0; "
        "border-bottom: 1px solid #232836; padding-bottom: 4px; }\n"
        ".grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }\n"
        "table { width: 100%; border-collapse: collapse; font-size: 11px; }\n"
        "th, td { text-align: left; padding: 6px; border-bottom: 1px solid #232836; }\n"
        "th { color: #94a3b8; text-transform: uppercase; }\n"
        "ul { margin: 0; padding-left: 20px; }\n"
    )

    badge_style = (
        "background: rgba(239, 68, 68, 0.2); color: #ef4444; "
        "padding: 2px 6px; border-radius: 4px; font-weight: bold;"
    )

    p_len = dossier.plume.plume_length_km
    p_evac = dossier.plume.evacuation_radius_km
    w_spd = dossier.plume.wind_speed_ms
    w_dir = dossier.plume.wind_direction_deg
    dw_az = dossier.plume.downwind_azimuth_deg
    pyro_t = dossier.pyrometry.emitter_temp_k
    pyro_a = dossier.pyrometry.emitter_area_m2
    lat_str = f"{dossier.latitude:.4f}°N, {dossier.longitude:.4f}°E"

    card_inc = (
        "<div class='card'>"
        "<h2>📍 Incident & Context</h2>"
        f"<div><strong>Centroid:</strong> {lat_str}</div>"
        f"<div><strong>Intensity:</strong> {dossier.frp_mw:.1f} MW FRP</div>"
        f"<div><strong>Facility:</strong> {dossier.facility_name}</div>"
        "</div>"
    )

    card_pyro = (
        "<div class='card'>"
        "<h2>🔬 Planck Pyrometry</h2>"
        f"<div><strong>Temp:</strong> {pyro_t:.0f} K ({emitter_c:.0f}°C)</div>"
        f"<div><strong>Area:</strong> {pyro_a:.1f} m²</div>"
        f"<div><strong>Inversion:</strong> {dossier.pyrometry.convergence_status}</div>"
        "</div>"
    )

    card_plume = (
        "<div class='card'>"
        "<h2>💨 Plume Dispersion & Evacuation</h2>"
        "<div class='grid'>"
        f"<div><strong>Wind:</strong> {w_spd:.1f} m/s ({w_dir:.0f}°)</div>"
        f"<div><strong>Downwind:</strong> {dw_az:.0f}° Azimuth</div>"
        f"<div><strong>Plume Length:</strong> {p_len:.1f} km</div>"
        f"<div><strong>Evacuation:</strong> {p_evac:.1f} km</div>"
        "</div>"
        "</div>"
    )

    html_content = (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
        f"<title>Tactical Incident Dossier - {dossier.event_id}</title>"
        f"<style>{styles}</style></head><body>"
        f"<div class='container'><div class='header'><div>"
        f"<h1 style='font-size: 16px; margin: 0;'>🔥 PyroSat-AI Tactical Briefing</h1>"
        f"<div style='color: #94a3b8; font-size: 11px;'>"
        f"Event: {dossier.event_id} • {dossier.classification} ({conf_pct:.1f}% Conf)"
        f"</div></div><div style='text-align: right;'>"
        f"<span style='{badge_style}'>{dossier.response_priority.value}</span>"
        f"<div style='color: #64748b; font-size: 10px; margin-top: 4px;'>{ts_str}</div>"
        f"</div></div><div class='grid'>{card_inc}{card_pyro}</div>"
        f"{card_plume}{hazmat_section}<div class='card'>"
        f"<h2>🚒 Recommended Responders</h2><table>"
        f"<thead><tr><th>Responder</th><th>Distance</th><th>ETA</th><th>Phone</th></tr></thead>"
        f"<tbody>{responders_rows}</tbody></table></div>"
        f"<div class='card'><h2>📋 Directives</h2><ul>{ops_items}</ul></div>"
        f"</div></body></html>"
    )
    return HTMLResponse(content=html_content, status_code=200)
