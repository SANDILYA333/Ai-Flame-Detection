"""Study-area feasibility assessment harness package for SIH26162 (DATA-001)."""

from packages.feasibility.candidates import (
    ANGUL_TALCHER,
    JAMNAGAR_KUTCH,
    PROVISIONAL_CANDIDATE_AREAS,
    PUNJAB_AGRICULTURAL,
    SINGRAULI_SONBHADRA,
    get_candidate_study_area,
)
from packages.feasibility.context_analyzer import (
    analyze_context_feasibility,
    filter_context_features_in_bounds,
)
from packages.feasibility.derivation_analyzer import (
    analyze_derivation_feasibility,
)
from packages.feasibility.evaluator import (
    evaluate_study_area_feasibility,
    generate_markdown_feasibility_report,
    run_comparative_feasibility_harness,
)
from packages.feasibility.firms_analyzer import (
    analyze_firms_feasibility,
    filter_detections_in_bounds,
)
from packages.feasibility.models import (
    ContextFeasibilityMetrics,
    DerivationFeasibilityMetrics,
    FeasibilityAssessment,
    FeasibilityComparativeReport,
    FeasibilityLevel,
    FirmsFeasibilityMetrics,
    ReferenceFeasibilityMetrics,
    StudyArea,
    StudyAreaRole,
)
from packages.feasibility.reference_analyzer import (
    CandidateReferencePoint,
    analyze_reference_feasibility,
    filter_reference_points_in_bounds,
)

__all__ = [
    "ANGUL_TALCHER",
    "JAMNAGAR_KUTCH",
    "PROVISIONAL_CANDIDATE_AREAS",
    "PUNJAB_AGRICULTURAL",
    "SINGRAULI_SONBHADRA",
    "CandidateReferencePoint",
    "ContextFeasibilityMetrics",
    "DerivationFeasibilityMetrics",
    "FeasibilityAssessment",
    "FeasibilityComparativeReport",
    "FeasibilityLevel",
    "FirmsFeasibilityMetrics",
    "ReferenceFeasibilityMetrics",
    "StudyArea",
    "StudyAreaRole",
    "analyze_context_feasibility",
    "analyze_derivation_feasibility",
    "analyze_firms_feasibility",
    "analyze_reference_feasibility",
    "evaluate_study_area_feasibility",
    "filter_context_features_in_bounds",
    "filter_detections_in_bounds",
    "filter_reference_points_in_bounds",
    "generate_markdown_feasibility_report",
    "get_candidate_study_area",
    "run_comparative_feasibility_harness",
]
