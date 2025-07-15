"""
Meta-Cognitive Monitoring Module.

This module implements the "fourth brain" that monitors the other three brains
(Bayesian World-Model, Utility-Driven Toolkit, Symbolic Logic Engine) and:
- Detects when wrong strategies are being applied
- Identifies confidence calibration issues
- Triggers re-evaluation and boundary adjustments
- Prevents cascading errors between brains

Key components:
- MetaCognitiveMonitor: Observer-controller loop
- BrainStateTracker: Monitors individual brain states
- DisagreementDetector: Identifies conflicts between brains
- StrategySelector: Chooses appropriate reasoning strategies
"""

from .monitor import MetaCognitiveMonitor
from .brain_tracker import BrainStateTracker, BrainState
from .disagreement import DisagreementDetector, Disagreement
from .strategy_selector import StrategySelector, ReasoningStrategy
from .confidence_calibrator import ConfidenceCalibrator

__all__ = [
    "MetaCognitiveMonitor",
    "BrainStateTracker",
    "BrainState",
    "DisagreementDetector", 
    "Disagreement",
    "StrategySelector",
    "ReasoningStrategy",
    "ConfidenceCalibrator",
]