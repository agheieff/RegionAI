"""
RegionAI Tier 3 - Situational Overlays

Situational overlays that provide context-specific customizations and scenarios.
These overlays adapt the universal reasoning engine (tier1) and domain knowledge
(tier2) to specific situations, users, or world contexts.

Components:
- User Contexts: Personal preferences, user-specific customizations
- World Contexts: Specific world models, scenarios, environments
- Scenarios: Situational reasoning contexts (embodiment, temporal, etc.)

Each overlay provides contextual adaptation without modifying the underlying
universal reasoning capabilities or domain knowledge.
"""

from .situation_manager import SituationManager
from .overlay import SituationalOverlay

__all__ = ["SituationManager", "SituationalOverlay"]