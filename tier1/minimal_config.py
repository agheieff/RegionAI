"""
Minimal configuration that doesn't require heavy dependencies.
"""

from .config import RegionAIConfig, AnalysisProfile

# Re-export the configuration classes
__all__ = ["RegionAIConfig", "AnalysisProfile"]