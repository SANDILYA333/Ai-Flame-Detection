"""Standard feature catalog and registration for SIH26162 Phase 4 ML.

Defines the approved baseline feature catalog, their physical semantics,
availability lag constraints, missingness handling contracts, and logical
feature groups for ablation studies. Also maintains explicit rejection/blocker
records for disqualified candidate features.
"""

from packages.schemas.ml import (
    FeatureDefinition,
    FeatureEligibilityStatus,
    FeatureGroup,
    FeatureMissingnessHandling,
    FeatureType,
    LeakageRisk,
)
from services.ml.features.registry import FeatureRegistry

STANDARD_FEATURE_VERSION = "feat_v1.0.0"

# ==============================================================================
# 1. APPROVED FEATURE DEFINITIONS
# ==============================================================================

APPROVED_FEATURES: list[FeatureDefinition] = [
    # --------------------------------------------------------------------------
    # Group: THERMAL_CORE (Primary FIRMS Observation Aggregate)
    # --------------------------------------------------------------------------
    FeatureDefinition(
        feature_name="detection_count",
        feature_type=FeatureType.COUNT,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Count of member detections in event cluster knowable as of T_pred."
        ),
        physical_unit="count",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Observation footprint of event cluster.",
        temporal_semantics="Detections strictly <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="frp_mean_mw",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Arithmetic mean of Fire Radiative Power across detections in MW."
        ),
        physical_unit="MW",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Cluster spatial average.",
        temporal_semantics="Mean over detections <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="frp_max_mw",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Peak Fire Radiative Power observed across member detections in MW."
        ),
        physical_unit="MW",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Cluster peak point.",
        temporal_semantics="Maximum over detections <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="frp_min_mw",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Minimum Fire Radiative Power observed across detections in MW."
        ),
        physical_unit="MW",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Cluster minimum point.",
        temporal_semantics="Minimum over detections <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="frp_sum_mw",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Sum of Fire Radiative Power across member detections in MW."
        ),
        physical_unit="MW",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Cluster total integrated intensity.",
        temporal_semantics="Sum over detections <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="frp_std_mw",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Sample standard deviation of FRP across detections in MW."
        ),
        physical_unit="MW",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Cluster FRP variance.",
        temporal_semantics="Std dev over detections <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="duration_hours",
        feature_type=FeatureType.TEMPORAL_SPAN,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Time span from first to latest detection as of prediction time."
        ),
        physical_unit="hours",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Event temporal span.",
        temporal_semantics="Latest detection timestamp - earliest detection timestamp.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="temporal_density",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Detections per observation hour (detection_count / max(duration, 1))."
        ),
        physical_unit="detections/hour",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Rate of detection arrivals in cluster.",
        temporal_semantics="Evaluated strictly <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="brightness_mean_kelvin",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Detection",
        derivation_description=(
            "Mean brightness temperature across member detections in Kelvin."
        ),
        physical_unit="Kelvin",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Cluster mean brightness temperature.",
        temporal_semantics="Mean over detections <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="brightness_max_kelvin",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Detection",
        derivation_description=(
            "Peak brightness temperature across member detections in Kelvin."
        ),
        physical_unit="Kelvin",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Cluster peak brightness temperature.",
        temporal_semantics="Maximum over detections <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="spatial_extent_radius_meters",
        feature_type=FeatureType.GEOSPATIAL_DISTANCE,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Max geodesic distance in meters from centroid to any detection."
        ),
        physical_unit="meters",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Cluster physical radius envelope.",
        temporal_semantics="Computed on detections <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="daynight_ratio",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Detection",
        derivation_description=(
            "Fraction of daytime satellite overpasses among event detections."
        ),
        physical_unit="ratio",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Solar diurnal exposure of cluster.",
        temporal_semantics="Computed on detections <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="satellite_platform_diversity",
        feature_type=FeatureType.COUNT,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Detection",
        derivation_description=(
            "Count of distinct satellite platforms observing event cluster."
        ),
        physical_unit="count",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Multi-platform sensor convergence.",
        temporal_semantics="Evaluated on detections <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="sensor_instrument",
        feature_type=FeatureType.CATEGORICAL,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Detection",
        derivation_description=(
            "Primary sensor instrument type for event ('VIIRS', 'MODIS', 'HYBRID')."
        ),
        physical_unit=None,
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Observing instrument family.",
        temporal_semantics="Determined from detections <= prediction_time.",
        source_version="FIRMS_NRT_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    # --------------------------------------------------------------------------
    # Group: TEMPORAL_HISTORY (Historical Recurrence around Centroid)
    # --------------------------------------------------------------------------
    FeatureDefinition(
        feature_name="prior_event_count_24h",
        feature_type=FeatureType.COUNT,
        feature_group=FeatureGroup.TEMPORAL_HISTORY,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Count of distinct preceding events within radius in past 24 hours."
        ),
        physical_unit="count",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Local spatial neighborhood (e.g. 1500m radius).",
        temporal_semantics="Events with ended_at in [T_pred - 24h, T_pred).",
        source_version="DERIVED_EVENTS_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="prior_event_count_7d",
        feature_type=FeatureType.COUNT,
        feature_group=FeatureGroup.TEMPORAL_HISTORY,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Count of distinct preceding events within radius in past 7 days."
        ),
        physical_unit="count",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Local spatial neighborhood.",
        temporal_semantics="Events with ended_at in [T_pred - 7d, T_pred).",
        source_version="DERIVED_EVENTS_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="prior_event_count_30d",
        feature_type=FeatureType.COUNT,
        feature_group=FeatureGroup.TEMPORAL_HISTORY,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Count of distinct preceding events within radius in past 30 days."
        ),
        physical_unit="count",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Local spatial neighborhood.",
        temporal_semantics="Events with ended_at in [T_pred - 30d, T_pred).",
        source_version="DERIVED_EVENTS_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="time_since_previous_event_hours",
        feature_type=FeatureType.TEMPORAL_SPAN,
        feature_group=FeatureGroup.TEMPORAL_HISTORY,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Event",
        derivation_description=(
            "Elapsed hours since most recent preceding event ended."
        ),
        physical_unit="hours",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.EXPLICIT_INDICATOR,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Local spatial neighborhood.",
        temporal_semantics="prediction_time - previous_event.ended_at.",
        source_version="DERIVED_EVENTS_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    # --------------------------------------------------------------------------
    # Group: PERSISTENCE_SOURCE (Longitudinal Source Characteristics)
    # --------------------------------------------------------------------------
    FeatureDefinition(
        feature_name="persistence_active_days",
        feature_type=FeatureType.COUNT,
        feature_group=FeatureGroup.PERSISTENCE_SOURCE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Source",
        derivation_description=(
            "Count of active calendar days recorded up to prediction time."
        ),
        physical_unit="days",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Persistent source tracking radius.",
        temporal_semantics="Days active strictly <= prediction_time.",
        source_version="DERIVED_SOURCES_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="persistence_total_events",
        feature_type=FeatureType.COUNT,
        feature_group=FeatureGroup.PERSISTENCE_SOURCE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Source",
        derivation_description=(
            "Total count of historical events associated with this source."
        ),
        physical_unit="events",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Persistent source location.",
        temporal_semantics="Historical events strictly <= prediction_time.",
        source_version="DERIVED_SOURCES_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="persistence_recurrence_ratio",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.PERSISTENCE_SOURCE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Source",
        derivation_description=(
            "Observed activity recurrence ratio (active_days / span_days)."
        ),
        physical_unit="ratio",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.EXPLICIT_INDICATOR,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Persistent source location.",
        temporal_semantics="Ratio over historical window <= prediction_time.",
        source_version="DERIVED_SOURCES_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="is_persistent_source",
        feature_type=FeatureType.BOOLEAN,
        feature_group=FeatureGroup.PERSISTENCE_SOURCE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Source",
        derivation_description=(
            "Boolean flag indicating persistent/recurring source state."
        ),
        physical_unit=None,
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Persistent source classification.",
        temporal_semantics="Evaluated on historical data <= prediction_time.",
        source_version="DERIVED_SOURCES_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="persistence_state",
        feature_type=FeatureType.CATEGORICAL,
        feature_group=FeatureGroup.PERSISTENCE_SOURCE,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Source",
        derivation_description=(
            "Classification state (PERSISTENT, RECURRING, TRANSIENT)."
        ),
        physical_unit=None,
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Persistent source classification.",
        temporal_semantics="Evaluated on historical data <= prediction_time.",
        source_version="DERIVED_SOURCES_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    # --------------------------------------------------------------------------
    # Group: SPATIAL_CONTEXT (Infrastructure Proximity & Land Use)
    # --------------------------------------------------------------------------
    FeatureDefinition(
        feature_name="facility_distance_meters",
        feature_type=FeatureType.GEOSPATIAL_DISTANCE,
        feature_group=FeatureGroup.SPATIAL_CONTEXT,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Context",
        derivation_description=(
            "Geodesic distance in meters to nearest industrial facility."
        ),
        physical_unit="meters",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.EXPLICIT_INDICATOR,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Nearest OSM / industrial polygon or point.",
        temporal_semantics="Matched against context valid at prediction_time.",
        source_version="OSM_INFRASTRUCTURE_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="facility_context_type",
        feature_type=FeatureType.CATEGORICAL,
        feature_group=FeatureGroup.SPATIAL_CONTEXT,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Context",
        derivation_description=(
            "Category of nearest facility ('INDUSTRIAL', 'REFINERY', 'POWER_PLANT')."
        ),
        physical_unit=None,
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.EXPLICIT_INDICATOR,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Nearest facility classification.",
        temporal_semantics="Matched against context valid at prediction_time.",
        source_version="OSM_INFRASTRUCTURE_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="is_near_industrial_facility",
        feature_type=FeatureType.BOOLEAN,
        feature_group=FeatureGroup.SPATIAL_CONTEXT,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Context",
        derivation_description=(
            "Boolean flag indicating if centroid is within attribution radius."
        ),
        physical_unit=None,
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Proximity threshold check (e.g. <= 2500m).",
        temporal_semantics="Matched against context valid at prediction_time.",
        source_version="OSM_INFRASTRUCTURE_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="power_plant_distance_meters",
        feature_type=FeatureType.GEOSPATIAL_DISTANCE,
        feature_group=FeatureGroup.SPATIAL_CONTEXT,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Context",
        derivation_description=(
            "Geodesic distance in meters to nearest thermal/hydro power plant."
        ),
        physical_unit="meters",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.EXPLICIT_INDICATOR,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="WRI Global Power Plant database point match.",
        temporal_semantics="Matched against power plants valid at prediction_time.",
        source_version="WRI_POWER_PLANTS_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="landcover_class",
        feature_type=FeatureType.CATEGORICAL,
        feature_group=FeatureGroup.LAND_COVER,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Context",
        derivation_description=(
            "Dominant ESA WorldCover landcover class (e.g. 'CROPLAND', 'TREES')."
        ),
        physical_unit=None,
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.EXPLICIT_INDICATOR,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="10m raster pixel classification at event centroid.",
        temporal_semantics="Pre-event landcover map vintage (not post-event).",
        source_version="ESA_WORLDCOVER_2021",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="is_protected_area",
        feature_type=FeatureType.BOOLEAN,
        feature_group=FeatureGroup.LAND_COVER,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Context",
        derivation_description=(
            "Flag indicating if centroid falls in protected reserve/park."
        ),
        physical_unit=None,
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="WDPA protected area polygon containment.",
        temporal_semantics="Designation status valid at prediction_time.",
        source_version="WDPA_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="water_distance_meters",
        feature_type=FeatureType.GEOSPATIAL_DISTANCE,
        feature_group=FeatureGroup.SPATIAL_CONTEXT,
        eligibility_status=FeatureEligibilityStatus.APPROVED,
        source_entity="Context",
        derivation_description=(
            "Distance in meters to nearest surface water body, river, or coast."
        ),
        physical_unit="meters",
        availability_lag_seconds=0.0,
        missingness_handling=FeatureMissingnessHandling.EXPLICIT_INDICATOR,
        allowed_for_training=True,
        is_model_input=True,
        spatial_semantics="Hydrographic line/polygon distance.",
        temporal_semantics="Matched against water mask valid at prediction_time.",
        source_version="OSM_WATER_v1",
        leakage_risk=LeakageRisk.SAFE,
        version=STANDARD_FEATURE_VERSION,
    ),
]

# ==============================================================================
# 2. DISQUALIFIED / NON-FEATURE CANDIDATE CATALOG (AUDIT RECORD)
# ==============================================================================

DISQUALIFIED_CANDIDATES: list[FeatureDefinition] = [
    FeatureDefinition(
        feature_name="reference_class",
        feature_type=FeatureType.CATEGORICAL,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.LABEL_REFERENCE,
        source_entity="ReferenceLabel",
        derivation_description="Ground-truth annotation class label.",
        missingness_handling=FeatureMissingnessHandling.IMPUTATION_PROHIBITED,
        allowed_for_training=False,
        is_model_input=False,
        leakage_risk=LeakageRisk.DIRECT_LEAKAGE,
        leakage_justification=(
            "Direct target label leakage; reference labels are prohibited."
        ),
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="label_confidence",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.LABEL_REFERENCE,
        source_entity="ReferenceLabel",
        derivation_description="Reference label confidence score.",
        missingness_handling=FeatureMissingnessHandling.IMPUTATION_PROHIBITED,
        allowed_for_training=False,
        is_model_input=False,
        leakage_risk=LeakageRisk.DIRECT_LEAKAGE,
        leakage_justification=(
            "Target metadata leakage; correlates directly with label."
        ),
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="mcd64a1_burned_area",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.LAND_COVER,
        eligibility_status=FeatureEligibilityStatus.VALIDATION_ONLY,
        source_entity="Context",
        derivation_description="Monthly burned area product (MCD64A1).",
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=False,
        is_model_input=False,
        leakage_risk=LeakageRisk.TEMPORAL_LEAKAGE,
        leakage_justification=(
            "Post-event outcome leakage; post-fire burn scars unavailable in NRT."
        ),
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="future_event_duration",
        feature_type=FeatureType.TEMPORAL_SPAN,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.REJECTED,
        source_entity="Event",
        derivation_description="Final duration of the complete future event.",
        missingness_handling=FeatureMissingnessHandling.IMPUTATION_PROHIBITED,
        allowed_for_training=False,
        is_model_input=False,
        leakage_risk=LeakageRisk.TEMPORAL_LEAKAGE,
        leakage_justification=(
            "Temporal hindsight leakage; final duration uses future detections."
        ),
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="final_detection_count",
        feature_type=FeatureType.COUNT,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.REJECTED,
        source_entity="Event",
        derivation_description="Total detection count after event extinction.",
        missingness_handling=FeatureMissingnessHandling.IMPUTATION_PROHIBITED,
        allowed_for_training=False,
        is_model_input=False,
        leakage_risk=LeakageRisk.TEMPORAL_LEAKAGE,
        leakage_justification=(
            "Temporal hindsight leakage; final count counts future observations."
        ),
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="raw_event_id",
        feature_type=FeatureType.CATEGORICAL,
        feature_group=FeatureGroup.THERMAL_CORE,
        eligibility_status=FeatureEligibilityStatus.REJECTED,
        source_entity="Event",
        derivation_description="Unique canonical event identifier string.",
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=False,
        is_model_input=False,
        leakage_risk=LeakageRisk.SAFE,
        leakage_justification=(
            "Identifier memorization shortcut; primary keys must never be features."
        ),
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="raw_source_id",
        feature_type=FeatureType.CATEGORICAL,
        feature_group=FeatureGroup.PERSISTENCE_SOURCE,
        eligibility_status=FeatureEligibilityStatus.REJECTED,
        source_entity="Source",
        derivation_description="Unique persistent source identifier string.",
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=False,
        is_model_input=False,
        leakage_risk=LeakageRisk.SAFE,
        leakage_justification=(
            "Identifier shortcut; source IDs must be reserved for group splitting."
        ),
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="raw_facility_id",
        feature_type=FeatureType.CATEGORICAL,
        feature_group=FeatureGroup.SPATIAL_CONTEXT,
        eligibility_status=FeatureEligibilityStatus.REJECTED,
        source_entity="Context",
        derivation_description="External facility identifier (e.g. OSM way ID).",
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=False,
        is_model_input=False,
        leakage_risk=LeakageRisk.SAFE,
        leakage_justification=(
            "Identifier shortcut; specific facility IDs prevent generalization."
        ),
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="raw_latitude",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.SPATIAL_CONTEXT,
        eligibility_status=FeatureEligibilityStatus.BLOCKED,
        source_entity="Event",
        derivation_description="Raw latitude coordinate in WGS-84 degrees.",
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=False,
        is_model_input=False,
        leakage_risk=LeakageRisk.SPATIAL_LEAKAGE,
        leakage_justification=(
            "Geographic shortcut memorization; models memorize coordinates."
        ),
        version=STANDARD_FEATURE_VERSION,
    ),
    FeatureDefinition(
        feature_name="raw_longitude",
        feature_type=FeatureType.NUMERIC,
        feature_group=FeatureGroup.SPATIAL_CONTEXT,
        eligibility_status=FeatureEligibilityStatus.BLOCKED,
        source_entity="Event",
        derivation_description="Raw longitude coordinate in WGS-84 degrees.",
        missingness_handling=FeatureMissingnessHandling.PRESERVE_NONE,
        allowed_for_training=False,
        is_model_input=False,
        leakage_risk=LeakageRisk.SPATIAL_LEAKAGE,
        leakage_justification=(
            "Geographic shortcut memorization; models memorize coordinates."
        ),
        version=STANDARD_FEATURE_VERSION,
    ),
]


def get_standard_feature_registry() -> FeatureRegistry:
    """Populate a FeatureRegistry with all standard feature definitions."""
    registry = FeatureRegistry()
    for feat in APPROVED_FEATURES:
        registry.register(feat)
    for feat in DISQUALIFIED_CANDIDATES:
        registry.register(feat)
    return registry
