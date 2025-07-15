"""Discovery module for concept learning."""

# Simplified discovery interface
from .simple_discovery import SimpleDiscoveryEngine as DiscoveryEngine
from .simple_discovery import SimpleDiscoveryEngine as UnifiedDiscoveryEngine

def discover_transformations(examples):
    """Simple transformation discovery function."""
    engine = DiscoveryEngine()
    return engine.discover_transformations(examples)

# Try to import additional components, but don't fail if they don't exist
try:
    from tier1.region_algebra.transformation import Transformation
    from tier1.region_algebra.abstract_domains import Sign, Nullability
    from .ast_primitives import AST_PRIMITIVES
except ImportError:
    # Create placeholders if components don't exist
    Transformation = None
    Sign = None
    Nullability = None
    AST_PRIMITIVES = []

__all__ = [
    "DiscoveryEngine",
    "UnifiedDiscoveryEngine",
    "discover_transformations",
    "Transformation",
    "Sign",
    "Nullability",
    "AST_PRIMITIVES"
]