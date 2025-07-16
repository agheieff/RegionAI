"""
DEPRECATED: This module is being refactored. Please use the modular heuristics from:
- heuristics.ast_heuristics
- heuristics.pattern_heuristics
- heuristics.security_heuristics
- heuristics.quality_heuristics

This file is kept for backward compatibility and will be removed in a future version.
"""
import warnings

warnings.warn(
    "The 'heuristic_implementations' module is deprecated and will be removed in a future version. "
    "Please import heuristics from the 'heuristics' subpackage instead:\n"
    "  - from regionai.reasoning.heuristics.ast_heuristics import method_call_implies_performs\n"
    "  - from regionai.reasoning.heuristics.pattern_heuristics import co_occurrence_implies_related\n"
    "  - from regionai.reasoning.heuristics.security_heuristics import check_insecure_ssl_config\n"
    "  - from regionai.reasoning.heuristics.quality_heuristics import documentation_checker, complexity_analyzer",
    DeprecationWarning,
    stacklevel=2
)

# Import all heuristics from the new modules for backward compatibility
