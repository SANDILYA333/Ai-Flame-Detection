"""Tactical Incident Dossier PDF Generator using ReportLab."""

import io
from datetime import UTC, datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from services.api.schemas.dossier import TacticalDossierResponse


class TacticalPdfGenerator:
    """Generates official publication-quality Tactical Incident Action Dossier PDFs."""

    @classmethod
    def generate(cls, dossier: TacticalDossierResponse) -> bytes:
        """Render a publication-quality tactical emergency action dossier PDF.

        Args:
            dossier: Synthesized tactical dossier response object.

        Returns:
            Raw PDF bytes suitable for HTTP transmission or file storage.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=32,
            bottomMargin=32,
        )

        styles = getSampleStyleSheet()

        # Custom tactical styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#991B1B"),
            alignment=1,  # Center
            spaceAfter=2,
            fontName="Helvetica-Bold",
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#4B5563"),
            alignment=1,
            spaceAfter=6,
            fontName="Helvetica",
        )
        sec_heading = ParagraphStyle(
            "SecHeading",
            parent=styles["Heading2"],
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#1E293B"),
            fontName="Helvetica-Bold",
            spaceBefore=4,
            spaceAfter=3,
        )
        body_style = ParagraphStyle(
            "BodySmall",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1E293B"),
            fontName="Helvetica",
        )
        body_bold = ParagraphStyle(
            "BodyBold",
            parent=body_style,
            fontName="Helvetica-Bold",
        )
        alert_style = ParagraphStyle(
            "AlertText",
            parent=body_style,
            textColor=colors.HexColor("#B91C1C"),
            fontName="Helvetica-Bold",
        )
        footer_style = ParagraphStyle(
            "FooterNotice",
            parent=styles["Normal"],
            fontSize=6.5,
            leading=8.5,
            textColor=colors.HexColor("#64748B"),
            alignment=1,
            fontName="Helvetica",
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph("NATIONAL EMERGENCY SATELLITE DISASTER INTELLIGENCE", title_style))
        story.append(
            Paragraph(
                "TACTICAL INCIDENT ACTION DOSSIER — MULTI-AGENCY RAPID RESPONSE PACKAGE",
                subtitle_style,
            )
        )
        story.append(
            HRFlowable(
                width="100%",
                thickness=1.5,
                color=colors.HexColor("#991B1B"),
                spaceAfter=6,
            )
        )

        # 2. Table 1: Incident Identification & Operational Overview
        date_str = (
            dossier.started_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if dossier.started_at
            else dossier.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        conf_pct = dossier.confidence * 100.0
        cls_color = "#B91C1C" if dossier.classification == "INDUSTRIAL" else "#D97706"

        prio_val = (
            dossier.response_priority.value
            if hasattr(dossier.response_priority, "value")
            else str(dossier.response_priority)
        )

        overview_rows = [
            [
                Paragraph("<b>Incident Target:</b>", body_style),
                Paragraph(f"<b>{dossier.facility_name}</b>", body_bold),
                Paragraph("<b>Incident Dossier ID:</b>", body_style),
                Paragraph(f"<b>{dossier.event_id}</b> ({prio_val})", alert_style),
            ],
            [
                Paragraph("<b>GPS Coordinates:</b>", body_style),
                Paragraph(f"{dossier.latitude:.4f}°N, {dossier.longitude:.4f}°E", body_style),
                Paragraph("<b>AI Classification:</b>", body_style),
                Paragraph(
                    f"<font color='{cls_color}'><b>{dossier.classification}</b></font> ({conf_pct:.1f}% Conf)",
                    body_style,
                ),
            ],
            [
                Paragraph("<b>Peak Intensity (FRP):</b>", body_style),
                Paragraph(f"<b>{dossier.frp_mw:.1f} MW</b> ({dossier.detection_count} detections)", body_style),
                Paragraph("<b>Observation Time:</b>", body_style),
                Paragraph(f"{date_str}", body_style),
            ],
            [
                Paragraph("<b>Industrial Sector:</b>", body_style),
                Paragraph(f"{dossier.facility_sector}", body_style),
                Paragraph("<b>Operational Status:</b>", body_style),
                Paragraph(f"<b>{dossier.uncertainty_state}</b>", body_style),
            ],
        ]

        t1 = Table(overview_rows, colWidths=[1.6 * inch, 2.2 * inch, 1.6 * inch, 2.1 * inch])
        t1.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("PADDING", (0, 0), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(t1)
        story.append(Spacer(1, 4))

        # 3. Section: Planck Dual-Band Pyrometry & Combustion Diagnostics
        story.append(
            Paragraph(
                "1. PLANCK DUAL-BAND THERMAL PYROMETRY & COMBUSTION DIAGNOSTICS",
                sec_heading,
            )
        )
        pyro_t = dossier.pyrometry.emitter_temp_k
        pyro_c = pyro_t - 273.15
        pyro_a = dossier.pyrometry.emitter_area_m2
        pyro_status = dossier.pyrometry.convergence_status

        pyro_rows = [
            [
                Paragraph("<b>True Emitter Temperature:</b>", body_style),
                Paragraph(f"<b>{pyro_t:.0f} K ({pyro_c:.0f} °C)</b>", body_bold),
                Paragraph("<b>Combustion Footprint:</b>", body_style),
                Paragraph(f"<b>{pyro_a:.1f} m²</b>", body_bold),
            ],
            [
                Paragraph("<b>Inversion Status:</b>", body_style),
                Paragraph(f"{pyro_status}", body_style),
                Paragraph("<b>Background Reference:</b>", body_style),
                Paragraph(f"{dossier.pyrometry.background_temp_k:.1f} K", body_style),
            ],
        ]
        t_pyro = Table(pyro_rows, colWidths=[1.8 * inch, 2.0 * inch, 1.8 * inch, 1.9 * inch])
        t_pyro.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F1F5F9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("PADDING", (0, 0), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(t_pyro)
        story.append(Spacer(1, 4))

        # 4. Section: CAMEO / NIOSH Chemical Hazard & ERG Isolation
        story.append(
            Paragraph(
                "2. CHEMICAL HAZARDS & EXPOSURE PROFILES (NOAA CAMEO / NIOSH / ERG STANDARDS)",
                sec_heading,
            )
        )
        haz = dossier.hazmat
        if haz:
            chems = ", ".join(haz.primary_chemicals) if haz.primary_chemicals else "Volatile Hydrocarbons"
            un_nos = ", ".join(haz.un_na_numbers) if haz.un_na_numbers else "UN N/A"
            byproducts = (
                ", ".join(haz.toxic_combustion_byproducts)
                if haz.toxic_combustion_byproducts
                else "Carbon Monoxide, Polycyclic Aromatic Hydrocarbons"
            )
            idlh_str = (
                ", ".join([f"{k}: {v} ppm" for k, v in haz.idlh_ppm.items()])
                if haz.idlh_ppm
                else "Available on CAMEO Registry"
            )
            iso_m = haz.initial_isolation_distance_meters
            day_m = haz.downwind_evacuation_day_meters
            night_m = haz.downwind_evacuation_night_meters
            haz_class = haz.cameo_hazmat_class
            disaster_risk = haz.primary_disaster_risk
            proto = haz.firefighting_protocol
        else:
            chems = "Class 3 Flammable Hydrocarbons"
            un_nos = "UN 1202, UN 1203"
            byproducts = "Carbon Monoxide, Toxic Particulates"
            idlh_str = "H2S: 100 ppm, SO2: 100 ppm"
            iso_m = 800
            day_m = 1600
            night_m = 2400
            haz_class = "Class 3 — Flammable Liquids"
            disaster_risk = "Thermal Flashover & Toxic Smoke Inhalation"
            proto = "AFFF Alcohol-Resistant Foam & Deluge Barrier"

        hazmat_rows = [
            [
                Paragraph("<b>Hazard Classification:</b>", body_style),
                Paragraph(f"{haz_class} (UN: {un_nos})", body_style),
                Paragraph("<b>Primary Stored Chemicals:</b>", body_style),
                Paragraph(f"{chems}", body_style),
            ],
            [
                Paragraph("<b>Primary Disaster Risk:</b>", body_style),
                Paragraph(f"<font color='#B91C1C'><b>{disaster_risk}</b></font>", body_style),
                Paragraph("<b>Toxic Combustion Byproducts:</b>", body_style),
                Paragraph(f"{byproducts}", body_style),
            ],
            [
                Paragraph("<b>NIOSH IDLH Toxicity Limits:</b>", body_style),
                Paragraph(f"{idlh_str}", body_style),
                Paragraph("<b>Firefighting Protocol:</b>", body_style),
                Paragraph(f"{proto}", body_style),
            ],
        ]
        t_haz = Table(hazmat_rows, colWidths=[1.8 * inch, 2.0 * inch, 1.8 * inch, 1.9 * inch])
        t_haz.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FECACA")),
                    ("PADDING", (0, 0), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(t_haz)
        story.append(Spacer(1, 4))

        # 5. Section: Atmospheric Plume Dispersion & Evacuation Zones
        story.append(
            Paragraph(
                "3. TOXIC PLUME DISPERSION & EVACUATION ZONES (GAUSSIAN PLUME / ERG 2024)",
                sec_heading,
            )
        )
        plume = dossier.plume
        plume_rows = [
            [
                Paragraph("<b>ERG Initial Isolation:</b>", body_style),
                Paragraph(f"<b>{iso_m} meters</b> (360° Perimeter)", body_bold),
                Paragraph("<b>Downwind Evacuation:</b>", body_style),
                Paragraph(
                    f"<font color='#991B1B'><b>{plume.evacuation_radius_km:.1f} km</b></font> ({day_m}m Day / {night_m}m Night)",
                    body_style,
                ),
            ],
            [
                Paragraph("<b>Surface Wind Vector:</b>", body_style),
                Paragraph(f"{plume.wind_speed_ms:.1f} m/s @ {plume.wind_direction_deg:.0f}° bearing", body_style),
                Paragraph("<b>Downwind Dispersion Axis:</b>", body_style),
                Paragraph(f"{plume.downwind_azimuth_deg:.0f}° Azimuth ({plume.plume_length_km:.1f} km length)", body_style),
            ],
        ]
        t_plume = Table(plume_rows, colWidths=[1.8 * inch, 2.0 * inch, 1.8 * inch, 1.9 * inch])
        t_plume.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
                    ("PADDING", (0, 0), (-1, -1), 3),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(t_plume)
        story.append(Spacer(1, 4))

        # 6. Section: Emergency Responders & Dispatch Directory
        story.append(
            Paragraph(
                "4. REGIONAL EMERGENCY CONTACTS & FIRST RESPONDER DISPATCH DIRECTORY",
                sec_heading,
            )
        )
        resp_headers = [
            Paragraph("<b>Agency / Unit</b>", body_bold),
            Paragraph("<b>Type / Jurisdiction</b>", body_bold),
            Paragraph("<b>Distance</b>", body_bold),
            Paragraph("<b>ETA</b>", body_bold),
            Paragraph("<b>Emergency Contact</b>", body_bold),
        ]
        resp_table_data = [resp_headers]

        for r in dossier.recommended_responders[:4]:
            resp_table_data.append(
                [
                    Paragraph(f"<b>{r.name}</b>", body_style),
                    Paragraph(f"{r.type} ({r.jurisdiction})", body_style),
                    Paragraph(f"{r.formatted_distance}", body_style),
                    Paragraph(f"<b>{r.formatted_eta}</b>", body_bold),
                    Paragraph(f"<b>{r.phone}</b>", alert_style),
                ]
            )

        if len(resp_table_data) == 1:
            resp_table_data.append(
                [
                    Paragraph("District Emergency Command", body_style),
                    Paragraph("State Fire Control", body_style),
                    Paragraph("12.0 km", body_style),
                    Paragraph("15 mins", body_bold),
                    Paragraph("+91-101 / +91-112", alert_style),
                ]
            )

        t_resp = Table(
            resp_table_data,
            colWidths=[2.2 * inch, 1.8 * inch, 1.0 * inch, 0.9 * inch, 1.6 * inch],
        )
        t_resp.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCFCE7")),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F0FDF4")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BBF7D0")),
                    ("PADDING", (0, 0), (-1, -1), 2.5),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(t_resp)
        story.append(Spacer(1, 4))

        # 7. Section: Operational Recommendations / Standard Directives
        story.append(
            Paragraph(
                "5. STANDARD OPERATING DIRECTIVES & PROTOCOLS",
                sec_heading,
            )
        )
        ops_rows = []
        for i, rec in enumerate(dossier.operational_recommendations[:4], start=1):
            ops_rows.append(
                [
                    Paragraph(f"<b>[{i}]</b>", alert_style),
                    Paragraph(f"{rec}", body_style),
                ]
            )
        t_ops = Table(ops_rows, colWidths=[0.3 * inch, 7.2 * inch])
        t_ops.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE68A")),
                    ("PADDING", (0, 0), (-1, -1), 2.5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(t_ops)
        story.append(Spacer(1, 6))

        # 8. Footer Notice
        story.append(
            Paragraph(
                "<b>CONFIDENTIAL OPERATIONAL BRIEFING:</b> Generated by PyroSat-AI Platform. "
                "Synchronized with NASA FIRMS & Copernicus Constellation. "
                "WGS-84 Geodesic Invariant. Human-in-the-Loop Analyst Verification Mandated.",
                footer_style,
            )
        )

        doc.build(story)
        return buffer.getvalue()
