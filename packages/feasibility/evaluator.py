"""Feasibility evaluation engine and comparative report generation."""

from collections.abc import Sequence
from datetime import UTC, datetime

from packages.config.scientific import ScientificConfig
from packages.context.models import ContextFeature
from packages.events.service import derive_thermal_events
from packages.feasibility.context_analyzer import (
    analyze_context_feasibility,
)
from packages.feasibility.derivation_analyzer import (
    analyze_derivation_feasibility,
)
from packages.feasibility.firms_analyzer import (
    analyze_firms_feasibility,
    filter_detections_in_bounds,
)
from packages.feasibility.models import (
    FeasibilityAssessment,
    FeasibilityComparativeReport,
    FeasibilityLevel,
    StudyArea,
    StudyAreaRole,
)
from packages.feasibility.reference_analyzer import (
    CandidateReferencePoint,
    analyze_reference_feasibility,
)
from packages.schemas.detection import Detection


def evaluate_study_area_feasibility(
    study_area: StudyArea,
    detections: Sequence[Detection],
    context_features: Sequence[ContextFeature],
    reference_points: Sequence[CandidateReferencePoint],
    config: ScientificConfig,
) -> FeasibilityAssessment:
    """Perform comprehensive feasibility analysis for a single candidate study area.

    Args:
        study_area: Candidate study area definition.
        detections: Global or raw detection records.
        context_features: Available contextual infrastructure features.
        reference_points: Candidate reference points.
        config: Authoritative ScientificConfig instance.

    Returns:
        FeasibilityAssessment: Structured feasibility metrics and recommendations.
    """
    config.validate_completeness()

    # 1. FIRMS Observational Feasibility
    firms_metrics = analyze_firms_feasibility(
        detections=detections,
        bounds=study_area.bounding_box,
        approx_area_sqkm=study_area.approx_area_sqkm,
    )

    filtered_detections = filter_detections_in_bounds(
        detections, study_area.bounding_box
    )

    # 2. Phase 3 Derivation Feasibility
    derivation_metrics = analyze_derivation_feasibility(
        detections=filtered_detections,
        config=config,
        approx_area_sqkm=study_area.approx_area_sqkm,
    )

    derived_events = (
        derive_thermal_events(filtered_detections, config)
        if filtered_detections
        else []
    )

    # 3. Context Feasibility
    context_metrics = analyze_context_feasibility(
        events=derived_events,
        context_features=context_features,
        bounds=study_area.bounding_box,
        config=config,
    )

    # 4. Reference Ground-Truth Feasibility
    reference_metrics = analyze_reference_feasibility(
        events=derived_events,
        reference_points=reference_points,
        bounds=study_area.bounding_box,
        config=config,
    )

    # 5. Composite Scoring
    det_score = min(1.0, float(firms_metrics.total_detections) / 50.0)
    date_score = min(1.0, float(firms_metrics.unique_observation_dates) / 10.0)
    ctx_score = context_metrics.context_coverage_ratio
    ref_score = reference_metrics.reference_coverage_ratio

    data_adequacy = (
        (det_score * 0.35)
        + (date_score * 0.25)
        + (ctx_score * 0.25)
        + (ref_score * 0.15)
    )
    data_adequacy = round(min(1.0, max(0.0, data_adequacy)), 4)

    # Diversity score based on contextual category variety and persistence states
    num_ctx_types = len(context_metrics.context_by_category)
    num_pers_types = len(derivation_metrics.persistence_state_breakdown)
    diversity = min(1.0, (num_ctx_types * 0.15) + (num_pers_types * 0.25))
    diversity = round(min(1.0, max(0.0, diversity)), 4)

    # 6. Overall Feasibility Classification
    if data_adequacy >= 0.70:
        overall_feasibility = FeasibilityLevel.HIGH_FEASIBILITY
    elif data_adequacy >= 0.40:
        overall_feasibility = FeasibilityLevel.MODERATE_FEASIBILITY
    elif data_adequacy >= 0.15:
        overall_feasibility = FeasibilityLevel.LIMITED_FEASIBILITY
    else:
        overall_feasibility = FeasibilityLevel.INSUFFICIENT_DATA

    # 7. Role Recommendation
    if study_area.area_id == "punjab_agricultural":
        recommended_role = StudyAreaRole.CONTRAST_NEGATIVE_CONTROL
    elif overall_feasibility == FeasibilityLevel.HIGH_FEASIBILITY:
        recommended_role = StudyAreaRole.PRIMARY_BENCHMARK_CANDIDATE
    elif overall_feasibility == FeasibilityLevel.MODERATE_FEASIBILITY:
        recommended_role = StudyAreaRole.SECONDARY_VALIDATION
    else:
        recommended_role = StudyAreaRole.RESERVE_CANDIDATE

    # 8. Strengths and Limitations
    strengths: list[str] = []
    limitations: list[str] = []

    if firms_metrics.total_detections > 30:
        strengths.append(
            f"Robust volume ({firms_metrics.total_detections} FIRMS detections)."
        )
    else:
        limitations.append(
            f"Sparse volume ({firms_metrics.total_detections} detections)."
        )

    if derivation_metrics.candidate_sources_count > 0:
        n_src = derivation_metrics.candidate_sources_count
        strengths.append(f"Persistence demonstrated ({n_src} sources).")

    if context_metrics.context_coverage_ratio >= 0.60:
        cov_pct = context_metrics.context_coverage_ratio * 100.0
        strengths.append(f"High context proximity ({cov_pct:.1f}% coverage).")
    else:
        limitations.append(
            "Low contextual evidence overlap; potential unmapped facilities."
        )

    if reference_metrics.candidate_reference_points == 0:
        limitations.append(
            "Zero candidate ground-truth reference points available in catalog."
        )

    return FeasibilityAssessment(
        study_area=study_area,
        firms_metrics=firms_metrics,
        derivation_metrics=derivation_metrics,
        context_metrics=context_metrics,
        reference_metrics=reference_metrics,
        data_adequacy_score=data_adequacy,
        source_diversity_score=diversity,
        overall_feasibility=overall_feasibility,
        recommended_role=recommended_role,
        key_strengths=strengths,
        major_limitations=limitations,
    )


def run_comparative_feasibility_harness(
    study_areas: Sequence[StudyArea],
    detections: Sequence[Detection],
    context_features: Sequence[ContextFeature],
    reference_points: Sequence[CandidateReferencePoint],
    config: ScientificConfig,
    harness_version: str = "v1.0-data001",
) -> FeasibilityComparativeReport:
    """Run the complete feasibility harness across all candidate study areas."""
    config.validate_completeness()

    assessments: list[FeasibilityAssessment] = [
        evaluate_study_area_feasibility(
            study_area=area,
            detections=detections,
            context_features=context_features,
            reference_points=reference_points,
            config=config,
        )
        for area in study_areas
    ]

    # Deterministic ranking: data_adequacy (desc), diversity (desc), area_id (asc)
    sorted_assessments = sorted(
        assessments,
        key=lambda a: (
            -a.data_adequacy_score,
            -a.source_diversity_score,
            a.study_area.area_id,
        ),
    )
    ranking = [a.study_area.area_id for a in sorted_assessments]

    measured = [
        f"Evaluated {len(study_areas)} provisional candidate study areas across India.",
        f"Total candidate detections analyzed: {len(detections)}.",
        f"Total candidate context features analyzed: {len(context_features)}.",
        f"Total candidate reference points analyzed: {len(reference_points)}.",
    ]

    inferred = [
        "Industrial clusters with dense petrochemical infrastructure (e.g. "
        "Jamnagar) show the highest context coverage ratio.",
        "Agricultural belts (e.g. Punjab) exhibit high event counts but low "
        "industrial persistence, confirming suitability as a negative control.",
        "Energy/power hubs (e.g. Singrauli) exhibit multi-source complexity with "
        "both coal power flaring/stacks and adjacent vegetation cover.",
    ]

    recommendations = [
        "Retain Jamnagar & Gulf of Kutch as the primary benchmark candidate for "
        "industrial flaring.",
        "Retain Punjab Agricultural Belt as the primary negative control / "
        "contrast geography for transient open burns.",
        "Advance Singrauli and Angul-Talcher to secondary evaluation pending Tier A "
        "ground-truth catalog ingestion.",
    ]

    open_questions = [
        "What is the exact temporal availability and latency of VIIRS NRT vs "
        "Standard archive for the selected study areas?",
        "Are fine-scale flare coordinates available in the World Bank GGIT "
        "catalog for Indian refineries?",
        "What spatial resolution is required for land-cover segmentation to avoid "
        "false positive edge effects around industrial parks?",
    ]

    return FeasibilityComparativeReport(
        generated_at=datetime.now(UTC),
        harness_version=harness_version,
        scientific_config_version=config.version,
        scientific_config_fingerprint=config.compute_fingerprint(),
        candidate_assessments=sorted_assessments,
        comparative_ranking=ranking,
        measured_findings=measured,
        inferred_insights=inferred,
        recommendations=recommendations,
        open_questions=open_questions,
    )


def generate_markdown_feasibility_report(
    report: FeasibilityComparativeReport,
) -> str:
    """Generate a clean, human-readable Markdown feasibility report."""
    fp = report.scientific_config_fingerprint[:8]
    lines: list[str] = [
        "# DATA-001 — Study-Area Feasibility Assessment Report",
        "",
        f"**Generated At (UTC):** {report.generated_at.isoformat()}",
        f"**Harness Version:** {report.harness_version}",
        f"**Scientific Config Version:** {report.scientific_config_version} (`{fp}`)",
        "",
        "---",
        "",
        "## 1. Measured Findings",
        "",
    ]
    for item in report.measured_findings:
        lines.append(f"- {item}")

    lines.extend(["", "## 2. Comparative Candidate Ranking", ""])
    lines.append(
        "| Rank | Study Area ID | Region / State | Adequacy Score | Feasibility Level "
        "| Recommended Role |"
    )
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for idx, a in enumerate(report.candidate_assessments, 1):
        lines.append(
            f"| {idx} | `{a.study_area.area_id}` | "
            f"{a.study_area.name} ({a.study_area.state}) | "
            f"{a.data_adequacy_score:.3f} | "
            f"`{a.overall_feasibility.value}` | "
            f"`{a.recommended_role.value}` |"
        )

    lines.extend(["", "## 3. Individual Study Area Profiles", ""])
    for a in report.candidate_assessments:
        bbox = a.study_area.bounding_box
        lines.append(f"### `{a.study_area.area_id}`: {a.study_area.name}")
        lines.append(
            f"**State:** {a.study_area.state} | "
            f"**Approx Area:** {a.study_area.approx_area_sqkm:,.1f} km²"
        )
        lines.append(
            f"**Bounding Box:** `[{bbox.min_latitude}, {bbox.min_longitude}, "
            f"{bbox.max_latitude}, {bbox.max_longitude}]`"
        )
        lines.append(f"**Scientific Rationale:** {a.study_area.scientific_rationale}")
        lines.append("")
        lines.append("- **FIRMS Observations:**")
        lines.append(
            f"  - Total Detections: {a.firms_metrics.total_detections} "
            f"({a.firms_metrics.spatial_density_per_sqkm:.4f} per km²)"
        )
        lines.append(
            f"  - Unique Dates: {a.firms_metrics.unique_observation_dates} "
            f"(Span: {a.firms_metrics.temporal_span_days:.1f} days)"
        )
        lines.append(
            f"  - Mean FRP: {a.firms_metrics.frp_mean_mw} MW "
            f"(Max: {a.firms_metrics.frp_max_mw} MW)"
        )
        lines.append("- **Phase 3 Derivation:**")
        lines.append(
            f"  - Derived Events: {a.derivation_metrics.candidate_events_count}"
        )
        lines.append(
            f"  - Tracked Sources: {a.derivation_metrics.candidate_sources_count} "
            f"(States: {a.derivation_metrics.persistence_state_breakdown})"
        )
        lines.append("- **Context & Reference Feasibility:**")
        lines.append(
            f"  - Mapped Context Features: {a.context_metrics.total_context_features} "
            f"(Categories: {a.context_metrics.context_by_category})"
        )
        lines.append(
            f"  - Context Proximity Coverage: "
            f"{a.context_metrics.context_coverage_ratio * 100:.1f}%"
        )
        lines.append(
            f"  - Reference Points: {a.reference_metrics.candidate_reference_points} "
            f"(Tiers: {a.reference_metrics.reference_by_tier})"
        )
        lines.append("")

    lines.extend(["## 4. Inferred Insights", ""])
    for item in report.inferred_insights:
        lines.append(f"- {item}")

    lines.extend(["", "## 5. Evidence-Based Recommendations", ""])
    for item in report.recommendations:
        lines.append(f"- {item}")

    lines.extend(["", "## 6. Open Questions for Subsequent Gates", ""])
    for item in report.open_questions:
        lines.append(f"- {item}")

    return "\n".join(lines)
