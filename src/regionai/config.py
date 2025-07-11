"""
Centralized configuration for the RegionAI system.

This module defines all configurable parameters for the analysis engine,
allowing for easy tuning and different analysis profiles without modifying code.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple
from enum import Enum


class AnalysisProfile(Enum):
    """Predefined analysis profiles for common use cases."""
    FAST = "fast"  # Quick analysis with aggressive widening
    BALANCED = "balanced"  # Default balanced analysis
    PRECISE = "precise"  # More precise but slower analysis
    DEBUG = "debug"  # Maximum information for debugging


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
    
    # Semantic analysis
    track_semantic_patterns: bool = True
    fingerprint_cache_enabled: bool = True
    
    # Output and debugging
    verbose_output: bool = False
    debug_cfg_output: bool = False
    trace_fixpoint_iterations: bool = False
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    
    # Visualization settings
    viz_figure_size: Tuple[int, int] = (10, 10)
    viz_default_color: str = "blue"
    viz_selected_color: str = "red"
    viz_path_colors: List[str] = field(default_factory=lambda: ["orange", "purple", "lightblue", "darkblue", "lightgreen", "darkgreen"])
    viz_path_edge_color: str = "black"
    viz_default_alpha: float = 0.3
    viz_selected_alpha: float = 0.6
    viz_path_alpha: float = 0.7
    viz_grid_alpha: float = 0.3
    viz_line_widths: List[int] = field(default_factory=lambda: [1, 2, 3, 4])
    viz_font_size: int = 10
    viz_font_size_bold: int = 12
    viz_text_box_style: str = "round,pad=0.3"
    viz_text_box_facecolor: str = "white"
    viz_text_box_alpha: float = 0.8
    
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


# Default configuration instance
DEFAULT_CONFIG = RegionAIConfig()

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