"""
RegionAI Legacy Compatibility Shim

This module provides backward compatibility for code that imports from
the old src/regionai structure. It re-exports components from the new
three-tier architecture.

⚠️  DEPRECATION WARNING ⚠️
This compatibility shim is deprecated and will be removed in 2 minor releases.
Please migrate to the new three-tier architecture:
- tier1/: Immutable kernel components
- tier2/: Hot-swappable domain modules  
- tier3/: Epistemic workspaces

See docs/design/multi-space.md for migration guide.
"""

import warnings
import sys
from pathlib import Path

# Add tier directories to the Python path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Issue deprecation warning on import
warnings.warn(
    "Importing from 'regionai' package is deprecated. "
    "Please migrate to the new three-tier architecture (tier1/, tier2/, tier3/). "
    "This compatibility shim will be removed in 2 minor releases. "
    "See docs/design/multi-space.md for migration guide.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export core components from tier1 (kernel)
Kernel = None
RegionAIConfig = None
RegionND = None
AbstractDomain = None
AbstractState = None
DiscoveryEngine = None
BayesianBrain = None
LogicBrain = None
UtilityBrain = None
ObserverBrain = None
TemporalBrain = None
SensorimotorBrain = None

try:
    from tier1.kernel import UniversalReasoningKernel as Kernel
    from tier1.config import RegionAIConfig
    from tier1.region_algebra.region import RegionND
    from tier1.region_algebra.abstract_domain_base import AbstractDomain
    from tier1.region_algebra.abstract_domains import AbstractState
    from tier1.discovery.simple_discovery import SimpleDiscoveryEngine as DiscoveryEngine
    from tier1.brains.simple_brains import (
        BayesianBrain, LogicBrain, UtilityBrain, 
        ObserverBrain, TemporalBrain, SensorimotorBrain
    )
except ImportError as e:
    warnings.warn(f"Failed to import tier1 components: {e}", ImportWarning)

# Re-export module management from tier2
ModuleHub = None
DomainModule = None
ModuleBundle = None

try:
    from tier2.domain_hub import DomainHub as ModuleHub
    from tier2.domain_module import DomainModule
    
    # Create a simple ModuleBundle class for backward compatibility
    class ModuleBundle:
        def __init__(self, name, modules=None):
            self.name = name
            self.modules = modules or []
        
        def add_module(self, module):
            self.modules.append(module)
        
        def get_modules(self):
            return self.modules
    
except ImportError as e:
    warnings.warn(f"Failed to import tier2 components: {e}", ImportWarning)

# Re-export workspace management from tier3
SituationManager = None
SituationalOverlay = None
Workspace = None
Morphism = None
MorphismRegistry = None

try:
    from tier3.situation_manager import SituationManager
    from tier3.overlay import SituationalOverlay
    
    # Create simple compatibility classes
    class Workspace:
        def __init__(self, name="default"):
            self.name = name
            self.kernel = None
            self.situation_manager = None
            self.domain_hub = None
        
        def initialize(self):
            if Kernel:
                self.kernel = Kernel(version="1.0.0")
            if SituationManager:
                self.situation_manager = SituationManager()
            if ModuleHub:
                self.domain_hub = ModuleHub()
    
    class Morphism:
        def __init__(self, source, target, transform_func=None):
            self.source = source
            self.target = target
            self.transform_func = transform_func
        
        def apply(self, data):
            if self.transform_func:
                return self.transform_func(data)
            return data
    
    class MorphismRegistry:
        def __init__(self):
            self.morphisms = {}
        
        def register(self, name, morphism):
            self.morphisms[name] = morphism
        
        def get(self, name):
            return self.morphisms.get(name)
    
except ImportError as e:
    warnings.warn(f"Failed to import tier3 components: {e}", ImportWarning)

# Legacy aliases for backward compatibility
try:
    # Common legacy imports
    Region = RegionND  # Will be None if not available
    Config = RegionAIConfig
    
    # Legacy class names
    KnowledgeHub = ModuleHub  # Common legacy name
    
except NameError:
    # If imports failed, create dummy classes to prevent import errors
    class Region:
        def __init__(self, *args, **kwargs):
            raise ImportError("RegionAI components not available")
    
    class Config:
        def __init__(self, *args, **kwargs):
            raise ImportError("RegionAI components not available")

# Create a default legacy workspace for single-space compatibility
_default_workspace = None

def get_default_workspace():
    """
    Get the default legacy workspace.
    
    This provides single-space compatibility for legacy code.
    """
    global _default_workspace
    
    warnings.warn(
        "Using default workspace is deprecated. "
        "Please create explicit workspaces using the new architecture.",
        DeprecationWarning,
        stacklevel=2
    )
    
    if _default_workspace is None:
        try:
            kernel = Kernel(version="1.0.0")
            situation_manager = SituationManager()
            domain_hub = ModuleHub()
            
            # Create a pseudo-workspace using the new architecture
            _default_workspace = {
                "kernel": kernel,
                "situation_manager": situation_manager,
                "domain_hub": domain_hub
            }
            
            # Load common modules for backward compatibility
            try:
                domain_hub.load_domain("mathematics")
                domain_hub.load_domain("physics")
            except Exception:
                pass  # Ignore module loading errors
                
        except Exception as e:
            warnings.warn(f"Failed to create default workspace: {e}", ImportWarning)
    
    return _default_workspace

# Legacy function for creating regions
def create_region(*args, **kwargs):
    """Legacy function for creating regions."""
    warnings.warn(
        "create_region() is deprecated. Use kernel.create_region() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    
    try:
        kernel = Kernel(version="1.0.0")
        return kernel.create_region(*args, **kwargs)
    except Exception as e:
        raise ImportError(f"Failed to create region: {e}")

# Export commonly used items
__all__ = [
    # Core components (tier1)
    "Kernel", "RegionAIConfig",
    
    # Module system (tier2)
    "ModuleHub", "DomainModule", 
    
    # Situation system (tier3)
    "SituationManager", "SituationalOverlay",
    
    # Legacy aliases
    "Region", "Config", "KnowledgeHub",
    
    # Legacy functions
    "get_default_workspace", "create_region",
    
    # Placeholder components (will be None if not available)
    "RegionND", "AbstractDomain", "AbstractState", "DiscoveryEngine",
    "BayesianBrain", "LogicBrain", "UtilityBrain", "ObserverBrain", 
    "TemporalBrain", "SensorimotorBrain",
    "ModuleBundle", "Workspace", "Morphism", "MorphismRegistry"
]

# Print deprecation notice
print("=" * 60)
print("RegionAI Legacy Compatibility Mode")
print("=" * 60)
print("⚠️  WARNING: You are using the deprecated regionai package.")
print("   Please migrate to the new three-tier architecture:")
print("   - tier1/: Immutable kernel components")
print("   - tier2/: Hot-swappable domain modules")
print("   - tier3/: Epistemic workspaces")
print()
print("   See docs/design/multi-space.md for migration guide.")
print("   This compatibility shim will be removed in 2 releases.")
print("=" * 60)