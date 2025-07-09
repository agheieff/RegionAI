"""RegionAI: Region-based embeddings for language models."""

from .geometry.region import RegionND, Box2D
from .spaces.concept_space import ConceptSpaceND, ConceptSpace2D
from .engine.pathfinder import Pathfinder
from .visualization.interactive_plotter import InteractivePlotter

__version__ = "0.1.0"

__all__ = [
    "RegionND",
    "Box2D",
    "ConceptSpaceND", 
    "ConceptSpace2D",
    "Pathfinder",
    "InteractivePlotter",
]