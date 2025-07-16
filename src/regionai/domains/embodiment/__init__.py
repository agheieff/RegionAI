"""
Grounded Sensorimotor Link Module.

This module bridges abstract regions to raw sensory and actuator data,
grounding common sense understanding in physical interaction.

Key concepts:
- Sensory grounding: "Glass is fragile" → breaking force measurements
- Predictive coding: Refine regions via prediction error
- Affordances: What actions are possible with objects
- Embodied simulation: Mental models of physical interaction

Components:
- EmbodimentAdapter: Main interface between abstract and sensory
- SensorStream: Raw sensory data processing
- Actuator: Motor command generation
- PerceptualRegion: Low-level sensory regions
- PredictiveCoder: Prediction error minimization
"""

from .adapter import EmbodimentAdapter
from .sensor_stream import SensorStream, SensorReading
from .actuator import Actuator, MotorCommand
from .perceptual_region import PerceptualRegion, SensoryGrounding
from .predictive_coder import PredictiveCoder, PredictionError
from .affordance import AffordanceDetector, Affordance

__all__ = [
    "EmbodimentAdapter",
    "SensorStream",
    "SensorReading",
    "Actuator",
    "MotorCommand", 
    "PerceptualRegion",
    "SensoryGrounding",
    "PredictiveCoder",
    "PredictionError",
    "AffordanceDetector",
    "Affordance",
]