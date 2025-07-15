"""
RegionAI Tier 1 - Universal Reasoning Engine

The universal reasoning engine that provides the foundational cognitive
capabilities that work across all domains and situations:

- Region Algebra: Geometric operations, containment, overlap, hierarchical regions
- Brains: Six-brain cognitive architecture (Bayesian, Logic, Utility, Observer, Temporal, Sensorimotor)
- Discovery: Universal discovery strategies and search algorithms
- Core: Abstract domains, transformations, and fundamental operations
- Safety: Containment, red-teaming, and security measures

This tier contains the domain-agnostic reasoning capabilities that form
the foundation of all RegionAI operations.
"""

from .config import RegionAIConfig

# Try to import kernel, but don't fail if dependencies are missing
try:
    from .kernel import UniversalReasoningKernel
    __all__ = ["UniversalReasoningKernel", "RegionAIConfig"]
except ImportError:
    # Kernel requires torch and other dependencies
    UniversalReasoningKernel = None
    __all__ = ["RegionAIConfig"]

__version__ = "1.0.0"