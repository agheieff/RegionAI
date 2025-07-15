"""
Centralized configuration for the RegionAI system.

This module defines all configurable parameters for the analysis engine,
allowing for easy tuning and different analysis profiles without modifying code.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Set
from enum import Enum


class AnalysisProfile(Enum):
    """Predefined analysis profiles for common use cases."""
    FAST = "fast"  # Quick analysis with aggressive widening
    BALANCED = "balanced"  # Default balanced analysis
    PRECISE = "precise"  # More precise but slower analysis
    DEBUG = "debug"  # Maximum information for debugging


@dataclass
class DiscoveryConfig:
    """
    Configuration for concept and action discovery.
    
    Contains all patterns, heuristics, and settings used in the discovery process.
    """
    # CRUD verb patterns for concept discovery
    crud_verbs: Dict[str, List[str]] = field(default_factory=lambda: {
        'create': ['create', 'add', 'insert', 'new', 'make', 'build', 'generate'],
        'read': ['get', 'fetch', 'find', 'read', 'load', 'retrieve', 'search', 'list'],
        'update': ['update', 'edit', 'modify', 'change', 'set', 'save', 'patch'],
        'delete': ['delete', 'remove', 'destroy', 'purge', 'clear', 'drop']
    })
    
    # Relationship patterns in function names
    relationship_patterns: Dict[str, List[str]] = field(default_factory=lambda: {
        'has_many': [r'get_(\w+)_(\w+)s', r'list_(\w+)_(\w+)s'],
        'belongs_to': [r'get_(\w+)_by_(\w+)', r'find_(\w+)_for_(\w+)'],
        'has_one': [r'get_(\w+)_(\w+)(?!s)', r'fetch_(\w+)_(\w+)(?!s)']
    })
    
    # Common action verbs for fallback extraction
    common_action_verbs: Set[str] = field(default_factory=lambda: {
        'get', 'set', 'create', 'update', 'delete', 'save', 'load',
        'send', 'receive', 'process', 'validate', 'check', 'verify',
        'calculate', 'compute', 'filter', 'sort', 'search', 'find',
        'add', 'remove', 'insert', 'append', 'push', 'pop', 'clear',
        'open', 'close', 'read', 'write', 'connect', 'disconnect',
        'start', 'stop', 'run', 'execute', 'trigger', 'handle',
        'parse', 'format', 'encode', 'decode', 'encrypt', 'decrypt',
        'build', 'destroy', 'initialize', 'configure', 'setup'
    })
    
    # Action discovery confidence thresholds
    action_confidence_verb_at_start: float = 0.9
    action_confidence_verb_separated: float = 0.8
    action_confidence_function_name_pattern: float = 0.8  # Good confidence for function name patterns
    action_confidence_common_verb: float = 0.7
    action_confidence_default: float = 0.6
    action_confidence_sequence_threshold: float = 0.6  # Minimum confidence to consider action sequences
    
    # Dependency labels for grammatical patterns
    subject_dependency_labels: Set[str] = field(default_factory=lambda: {'nsubj', 'nsubjpass'})
    object_dependency_labels: Set[str] = field(default_factory=lambda: {'dobj', 'pobj', 'iobj'})
    modifier_dependency_labels: Set[str] = field(default_factory=lambda: {'det', 'amod', 'compound'})
    
    # Evidence strength for Bayesian updates
    concept_evidence_strengths: Dict[str, float] = field(default_factory=lambda: {
        'function_name_mention': 1.5,  # Strong evidence
        'docstring_mention': 1.0,      # Good evidence
        'comment_mention': 0.7,        # Moderate evidence
        'identifier_extraction': 0.5   # Weak evidence
    })
    
    relationship_evidence_strengths: Dict[str, float] = field(default_factory=lambda: {
        'co_occurrence_in_name': 1.2,       # Strong evidence
        'co_occurrence_in_docstring': 0.8,  # Good evidence
        'co_occurrence_in_comment': 0.6,    # Moderate evidence
        'co_occurrence_in_code': 0.5        # Weak evidence
    })
    
    action_evidence_strengths: Dict[str, float] = field(default_factory=lambda: {
        'method_call': 1.5,          # Very strong evidence
        'function_name': 1.2,        # Strong evidence
        'ast_analysis': 1.0,         # Good evidence
        'inferred_pattern': 0.7      # Moderate evidence
    })
    
    sequence_evidence_strengths: Dict[str, float] = field(default_factory=lambda: {
        'sequential_execution': 1.5,      # Very strong evidence
        'control_flow': 1.2,              # Strong evidence
        'pattern_analysis': 0.8,          # Good evidence
        'statistical_inference': 0.6,     # Moderate evidence
        'loop_iteration': 0.8,            # Sequence in loop
        'conditional_sequence': 0.6       # Sequence in conditional
    })
    
    # Concept discovery settings
    concept_frequency_threshold: int = 1  # Minimum mentions to consider a concept
    crud_pattern_min_operations: float = 0.5  # Minimum CRUD completeness (0.5 = 2/4 operations)
    
    # Programming terms to filter out
    programming_terms: Set[str] = field(default_factory=lambda: {
        'function', 'method', 'class', 'variable', 'parameter', 'argument',
        'return', 'value', 'type', 'object', 'instance', 'array', 'list',
        'dict', 'dictionary', 'string', 'integer', 'float', 'boolean',
        'true', 'false', 'none', 'null', 'error', 'exception'
    })
    
    # Auxiliary verbs to skip in grammatical patterns
    auxiliary_verbs: Set[str] = field(default_factory=lambda: {
        "be", "have", "do", "will", "would", "can", "could", "may", "might", "shall", "should"
    })
    
    # Confidence values for grammatical patterns
    grammar_pattern_base_confidence: float = 0.5
    grammar_pattern_confidence_increment: float = 0.25
    grammar_copular_pattern_confidence: float = 0.8
    
    # Determiners for IS_A relationships
    type_determiners: Set[str] = field(default_factory=lambda: {"a", "an"})
    
    # Common prefixes to skip when splitting identifiers
    identifier_skip_words: Set[str] = field(default_factory=lambda: {
        'get', 'set', 'is', 'has', 'create', 'update', 'delete', 'find'
    })
    
    # Default evidence strengths and credibility
    default_evidence_strength: float = 0.5
    default_source_credibility: float = 0.8
    co_occurrence_discovery_factor: float = 0.5  # Factor applied when discovering through co-occurrence
    
    # Initial belief parameters for Bayesian updates
    initial_alpha: float = 1.0
    initial_beta: float = 1.0
    
    # Base evidence weight multiplier
    base_evidence_weight: float = 1.0


@dataclass
class VisualizationConfig:
    """
    Configuration for visualization settings.
    
    Contains all settings related to the InteractivePlotter and other visualization components.
    """
    # Figure settings
    figure_size: Tuple[int, int] = (10, 10)
    
    # Colors
    default_color: str = "blue"
    selected_color: str = "red"
    path_colors: List[str] = field(default_factory=lambda: [
        "orange", "purple", "lightblue", "darkblue", "lightgreen", "darkgreen"
    ])
    path_edge_color: str = "black"
    
    # Alpha (transparency) values
    default_alpha: float = 0.3
    selected_alpha: float = 0.6
    path_alpha: float = 0.7
    grid_alpha: float = 0.3
    text_box_alpha: float = 0.8
    
    # Line widths
    line_widths: List[int] = field(default_factory=lambda: [1, 2, 3, 4])
    
    # Font settings
    font_size: int = 10
    font_size_bold: int = 12
    
    # Text box settings
    text_box_style: str = "round,pad=0.3"
    text_box_facecolor: str = "white"


@dataclass
class RegionAIConfig:
    """
    A container for all configurable parameters of the analysis engine.
    This allows for easy tuning and different analysis profiles.
    """
    # Analysis depth and precision
    widening_threshold: int = 3
    max_fixpoint_iterations: int = 100
    max_function_analysis_depth: int = 10  # For interprocedural analysis
    enable_path_sensitivity: bool = False  # Future feature flag
    enable_flow_sensitivity: bool = True
    max_states_per_point: int = 5  # Maximum states to track at each program point
    
    # Abstract domain precision
    max_range_value: float = 1000000  # Maximum tracked range value
    track_string_values: bool = False  # Whether to track string constants
    null_analysis_enabled: bool = True
    sign_analysis_enabled: bool = True
    range_analysis_enabled: bool = True
    
    # Caching and performance
    cache_summaries: bool = True
    cache_size_limit: int = 1000  # Maximum cached summaries
    parallel_analysis: bool = False  # Future feature
    
    # Error handling and reporting
    max_errors_per_function: int = 50
    max_warnings_per_function: int = 100
    report_potential_errors: bool = True  # Report "may" errors
    strict_null_checking: bool = True
    
    # Loop analysis
    unroll_small_loops: bool = True
    max_loop_unroll_count: int = 3
    use_loop_invariants: bool = True
    
    # Interprocedural analysis
    analyze_library_functions: bool = False
    inline_small_functions: bool = True
    max_inline_size: int = 10  # Max statements for inlining
    context_sensitivity_level: int = 2  # 0=none, 1=basic, 2=full
    
    # Discovery and learning
    discovery_exploration_rate: float = 0.1  # For exploration vs exploitation
    discovery_batch_size: int = 32
    max_discovery_iterations: int = 1000
    heuristic_learning_rate: float = 0.01  # Learning rate for heuristic-based updates
    comment_confidence_multiplier: float = 0.8  # Confidence reduction for comment-based discoveries
    
    # Semantic analysis
    track_semantic_patterns: bool = True
    fingerprint_cache_enabled: bool = True
    
    # Output and debugging
    verbose_output: bool = False
    debug_cfg_output: bool = False
    trace_fixpoint_iterations: bool = False
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    
    # Sub-configurations
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    visualization: VisualizationConfig = field(default_factory=VisualizationConfig)
    
    # Proof search configuration
    max_proof_sec: float = 600.0  # Maximum time for a single proof attempt (seconds)
    
    # Execution timeouts
    lean_executor_timeout: float = 30.0  # Timeout for Lean executor operations
    tactic_executor_timeout: float = 30.0  # Timeout for tactic executor operations
    
    # Buffer sizes and thresholds
    proof_trace_buffer_size: int = 100  # Number of events before flushing proof trace
    symbolic_parser_learning_threshold: float = 0.8  # Only learn from high-confidence resolutions
    synthesizer_pattern_threshold: int = 3  # Minimum occurrences to consider a pattern
    
    # Circuit breaker configuration
    circuit_breaker_failure_threshold: int = 3  # Failures before opening circuit
    circuit_breaker_recovery_timeout: int = 300  # Seconds before attempting recovery
    
    # Process pool configuration
    max_workers: int = 4  # Maximum worker processes for parallel execution
    
    # Custom parameters (for experimentation)
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_profile(cls, profile: AnalysisProfile) -> 'RegionAIConfig':
        """Create a configuration from a predefined profile."""
        if profile == AnalysisProfile.FAST:
            return cls(
                widening_threshold=1,
                max_fixpoint_iterations=50,
                max_function_analysis_depth=5,
                max_states_per_point=3,  # Fewer states for speed
                cache_summaries=True,
                report_potential_errors=False,
                inline_small_functions=False,
                context_sensitivity_level=0
            )
        elif profile == AnalysisProfile.PRECISE:
            return cls(
                widening_threshold=10,
                max_fixpoint_iterations=500,
                max_function_analysis_depth=20,
                max_states_per_point=10,  # More states for precision
                enable_path_sensitivity=True,
                report_potential_errors=True,
                strict_null_checking=True,
                context_sensitivity_level=2,
                unroll_small_loops=True,
                max_loop_unroll_count=5
            )
        elif profile == AnalysisProfile.DEBUG:
            return cls(
                widening_threshold=5,
                max_fixpoint_iterations=200,
                verbose_output=True,
                debug_cfg_output=True,
                trace_fixpoint_iterations=True,
                log_level="DEBUG",
                report_potential_errors=True
            )
        else:  # BALANCED or default
            return cls()
    
    def with_overrides(self, **kwargs) -> 'RegionAIConfig':
        """Create a new config with specific overrides."""
        import copy
        new_config = copy.deepcopy(self)
        for key, value in kwargs.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
            else:
                new_config.custom_params[key] = value
        return new_config
    
    def get_param(self, name: str, default: Any = None) -> Any:
        """Get a parameter value, checking custom params if not found."""
        if hasattr(self, name):
            return getattr(self, name)
        return self.custom_params.get(name, default)
    
    def validate(self) -> List[str]:
        """Validate configuration parameters and return any issues."""
        issues = []
        
        if self.widening_threshold < 0:
            issues.append("widening_threshold must be non-negative")
        
        if self.max_fixpoint_iterations < 1:
            issues.append("max_fixpoint_iterations must be at least 1")
        
        if self.max_function_analysis_depth < 1:
            issues.append("max_function_analysis_depth must be at least 1")
        
        if self.context_sensitivity_level not in [0, 1, 2]:
            issues.append("context_sensitivity_level must be 0, 1, or 2")
        
        if self.discovery_exploration_rate < 0 or self.discovery_exploration_rate > 1:
            issues.append("discovery_exploration_rate must be between 0 and 1")
        
        return issues
    
    def __post_init__(self):
        """Initialize sub-configurations if not provided."""
        if not isinstance(self.discovery, DiscoveryConfig):
            self.discovery = DiscoveryConfig()
        if not isinstance(self.visualization, VisualizationConfig):
            self.visualization = VisualizationConfig()
            
        # Check for environment variable overrides
        if 'REGIONAI_MAX_PROOF_SEC' in os.environ:
            try:
                self.max_proof_sec = float(os.environ['REGIONAI_MAX_PROOF_SEC'])
            except ValueError:
                pass  # Keep default if env var is invalid


# Default configuration instance
DEFAULT_CONFIG = RegionAIConfig()

# Standalone constants for direct access
HEURISTIC_LEARNING_RATE = DEFAULT_CONFIG.heuristic_learning_rate
COMMENT_CONFIDENCE_MULTIPLIER = DEFAULT_CONFIG.comment_confidence_multiplier

# Convenience functions for common profiles
def fast_analysis_config() -> RegionAIConfig:
    """Get configuration for fast analysis."""
    return RegionAIConfig.from_profile(AnalysisProfile.FAST)

def precise_analysis_config() -> RegionAIConfig:
    """Get configuration for precise analysis."""
    return RegionAIConfig.from_profile(AnalysisProfile.PRECISE)

def debug_analysis_config() -> RegionAIConfig:
    """Get configuration for debug analysis."""
    return RegionAIConfig.from_profile(AnalysisProfile.DEBUG)