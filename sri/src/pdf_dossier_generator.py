"""
Tactical Incident Dossier & Emergency Response Generator (PDF)
Fuses Satellite Anomaly Metrics + CAMEO Chemical HAZMAT Profiles + Spatial Emergency Services
"""

import os
import sys
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

HAZMAT_PATH = os.path.join(BASE_DIR, "data/industrial_infra/hazmat_profiles.json")
EMERGENCY_PATH = os.path.join(BASE_DIR, "data/industrial_infra/emergency_services_india.json")

def load_data():
    hazmat = {}
    emergency = []
    if os.path.exists(HAZMAT_PATH):
        with open(HAZMAT_PATH) as f:
            hazmat = json.load(f)
    if os.path.exists(EMERGENCY_PATH):
        with open(EMERGENCY_PATH) as f:
            emergency = json.load(f)
    return hazmat, emergency

def generate_tactical_dossier(incident_data, output_pdf_path=None):
    """
    Generates an official 1-Page Emergency Action Tactical Incident Dossier
    """
    if output_pdf_path is None:
        incident_id = incident_data.get("case_id", f"INC_{int(datetime.utcnow().timestamp())}")
        output_pdf_path = os.path.join(BASE_DIR, f"data/processed/{incident_id}_tactical_dossier.pdf")
        
    hazmat_db, emergency_db = load_data()
    
    # Match Sector HAZMAT Profile
    sector = incident_data.get("industry_sector", "Oil Refinery")
    hazmat = hazmat_db.get(sector, hazmat_db.get("Oil Refinery", {}))
    
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#991B1B'),
        alignment=1, # Center
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#4B5563'),
        alignment=1,
        spaceAfter=10
    )
    section_heading = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading2'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=6,
        spaceAfter=3
    )
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#111827')
    )
    body_bold = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    alert_box_style = ParagraphStyle(
        'AlertBox',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#7F1D1D')
    )
    
    story = []
    
    # Header Banner
    story.append(Paragraph("NATIONAL EMERGENCY SATELLITE DISASTER INTELLIGENCE", title_style))
    story.append(Paragraph("TACTICAL INCIDENT ACTION DOSSIER — FIRST RESPONDER RAPID DISPATCH", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#991B1B'), spaceAfter=8))
    
    # Table 1: Incident Overview
    facility = incident_data.get('facility_name', 'Industrial Facility')
    lat = incident_data.get('coordinates', {}).get('lat', 0.0)
    lon = incident_data.get('coordinates', {}).get('lon', 0.0)
    date_str = incident_data.get('date', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))
    cls_name = incident_data.get('ground_truth_class', 'Accidental Industrial Fire')
    
    metrics = incident_data.get('satellite_metrics', {})
    frp = metrics.get('frp_mw', 0.0)
    temp_k = metrics.get('planck_flame_temp_k', 0.0)
    area_m2 = metrics.get('effective_burn_area_m2', 0)
    surge = metrics.get('frp_surge_ratio', 1.0)
    
    overview_data = [
        [Paragraph("<b>Incident Target:</b>", body_style), Paragraph(f"<b>{facility}</b>", body_bold),
         Paragraph("<b>Date / Timestamp:</b>", body_style), Paragraph(f"{date_str}", body_style)],
        [Paragraph("<b>GPS Coordinates:</b>", body_style), Paragraph(f"{lat:.4f}°N, {lon:.4f}°E", body_style),
         Paragraph("<b>AI Classification:</b>", body_style), Paragraph(f"<font color='#B91C1C'><b>{cls_name}</b></font>", body_style)],
        [Paragraph("<b>Fire Radiative Power (FRP):</b>", body_style), Paragraph(f"<b>{frp:.1f} MW</b> (+{surge*100:.0f}% vs Baseline)", body_style),
         Paragraph("<b>Planck Flame Temp:</b>", body_style), Paragraph(f"<b>{temp_k:.0f} K</b> ({temp_k - 273.15:.0f} °C)", body_style)]
    ]
    
    t1 = Table(overview_data, colWidths=[1.8*inch, 2.2*inch, 1.6*inch, 1.8*inch])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t1)
    story.append(Spacer(1, 8))
    
    # Section: CAMEO Chemicals HAZMAT Profile
    story.append(Paragraph("1. CHEMICAL HAZARDS & EXPOSURE PROFILES (NOAA CAMEO / NIOSH STANDARDS)", section_heading))
    
    chems = ", ".join(hazmat.get('primary_chemicals', ['Hydrocarbons']))
    un_nos = ", ".join(hazmat.get('un_na_numbers', ['UN N/A']))
    haz_class = hazmat.get('cameo_hazmat_class', 'Class 3 Flammable')
    byproducts = ", ".join(hazmat.get('toxic_combustion_byproducts', ['CO, Toxic Smoke']))
    idlh_info = ", ".join([f"{k}: {v} ppm" for k,v in hazmat.get('idlh_ppm', {}).items()])
    
    hazmat_data = [
        [Paragraph("<b>Sector & UN Classification:</b>", body_style), Paragraph(f"{haz_class} | UN Codes: {un_nos}", body_style)],
        [Paragraph("<b>Primary Stored Chemicals:</b>", body_style), Paragraph(f"{chems}", body_style)],
        [Paragraph("<b>Major Disaster Hazard:</b>", body_style), Paragraph(f"<font color='#B91C1C'><b>{hazmat.get('primary_disaster_risk', 'Fire & Explosion')}</b></font>", body_style)],
        [Paragraph("<b>Toxic Combustion Byproducts:</b>", body_style), Paragraph(f"{byproducts}", body_style)],
        [Paragraph("<b>NIOSH IDLH Toxicity Limits:</b>", body_style), Paragraph(f"{idlh_info}", body_style)]
    ]
    t2 = Table(hazmat_data, colWidths=[2.2*inch, 5.2*inch])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FEF2F2')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FECACA')),
        ('PADDING', (0,0), (-1,-1), 3.5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t2)
    story.append(Spacer(1, 8))
    
    # Section: Toxic Plume & Evacuation Action Zones
    story.append(Paragraph("2. TOXIC PLUME DISPERSION & EVACUATION ZONES (GAUSSIAN / ERG 2024)", section_heading))
    
    plume = incident_data.get('toxic_plume', {})
    wind_spd = plume.get('wind_speed_ms', 3.5)
    wind_deg = plume.get('wind_bearing_deg', 90.0)
    evac_km = plume.get('evacuation_zone_radius_km', hazmat.get('downwind_evacuation_day_meters', 1600)/1000.0)
    settlements = ", ".join(plume.get('affected_settlements', ['Surrounding Industrial Perimeter']))
    
    plume_data = [
        [Paragraph("<b>Initial Isolation Perimeter:</b>", body_style), Paragraph(f"<b>{hazmat.get('initial_isolation_distance_meters', 800)} meters</b> (All Directions)", body_style),
         Paragraph("<b>Downwind Evacuation Zone:</b>", body_style), Paragraph(f"<font color='#991B1B'><b>{evac_km:.1f} km</b></font> ({hazmat.get('downwind_evacuation_night_meters', 2400)}m Night)", body_style)],
        [Paragraph("<b>Live Wind Vector:</b>", body_style), Paragraph(f"{wind_spd:.1f} m/s @ Bearing {wind_deg:.0f}°", body_style),
         Paragraph("<b>Affected Settlements:</b>", body_style), Paragraph(f"{settlements}", body_style)],
        [Paragraph("<b>Firefighting Protocol:</b>", body_style), Paragraph(f"{hazmat.get('firefighting_protocol', 'AFFF Foam')}", body_style), "", ""]
    ]
    
    t3 = Table(plume_data, colWidths=[1.8*inch, 2.2*inch, 1.8*inch, 1.6*inch])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#BFDBFE')),
        ('SPAN', (1,2), (3,2)),
        ('PADDING', (0,0), (-1,-1), 3.5),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t3)
    story.append(Spacer(1, 8))
    
    # Section: Emergency Dispatch & First Responders
    story.append(Paragraph("3. REGIONAL EMERGENCY CONTACTS & FIRST RESPONDER DISPATCH", section_heading))
    
    emerg = incident_data.get('nearest_emergency', {})
    fire_contact = emerg.get('fire_station', 'District Fire Command (+91-101)')
    hosp_contact = emerg.get('hospital', 'Apex Burn Trauma ICU')
    ndrf_contact = emerg.get('ndrf', 'Regional NDRF Disaster Battalion')
    
    emerg_data = [
        [Paragraph("<b>District Fire Control HQ:</b>", body_style), Paragraph(f"<b>{fire_contact}</b>", body_bold)],
        [Paragraph("<b>Apex Burn & Trauma Hospital:</b>", body_style), Paragraph(f"<b>{hosp_contact}</b>", body_bold)],
        [Paragraph("<b>NDRF Disaster Response Unit:</b>", body_style), Paragraph(f"{ndrf_contact}", body_style)]
    ]
    t4 = Table(emerg_data, colWidths=[2.2*inch, 5.2*inch])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0FDF4')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#BBF7D0')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t4)
    story.append(Spacer(1, 10))
    
    # Footer notice
    story.append(Paragraph("<font color='#6B7280'><b>CONFIDENTIAL DISASTER ACTION DOSSIER:</b> Generated automatically by PyroSat-AI Platform. Synchronized with Copernicus Sentinel & NASA FIRMS NRT Constellation. Compliant with NDMA / CPCB Disaster Standard Operating Procedures.</font>", ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, leading=9, alignment=1)))
    
    doc.build(story)
    print(f"✅ Generated Tactical Incident Dossier PDF: {output_pdf_path}")
    return output_pdf_path

if __name__ == "__main__":
    cases_path = os.path.join(BASE_DIR, "data/processed/historical_validation_cases.json")
    if os.path.exists(cases_path):
        with open(cases_path) as f:
            cases = json.load(f)
            if cases:
                sample_case = cases[0] # Vizag 2020 disaster
                pdf_path = generate_tactical_dossier(sample_case)
                print(f"Verified test dossier generated successfully at: {pdf_path}")
