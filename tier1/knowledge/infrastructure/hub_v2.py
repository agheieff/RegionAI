"""
Refactored Knowledge Hub v2.

This is a lightweight coordinator that delegates to specialized services,
replacing the monolithic god object with a clean, modular design.
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from tier1.knowledge.infrastructure.world_graph import WorldKnowledgeGraph, Concept, Relation
from tier1.knowledge.infrastructure.reasoning_graph import ReasoningKnowledgeGraph, Heuristic
from .reasoning_graph_builder import populate_initial_reasoning_graph
from tier1.knowledge.infrastructure.services.storage_service import StorageService
from tier1.knowledge.infrastructure.services.query_service import QueryService
from tier1.knowledge.infrastructure.services.reasoning_service import ReasoningService, ReasoningContext
from tier1.config import RegionAIConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class KnowledgeHubV2:
    """
    Lightweight knowledge hub that coordinates specialized services.
    
    This refactored version delegates responsibilities to focused services:
    - StorageService: Handles persistence
    - QueryService: Handles searches and queries
    - ReasoningService: Handles strategy application
    
    The hub itself only coordinates between services.
    """
    
    def __init__(self, config: RegionAIConfig = None,
                 storage_dir: Optional[Path] = None):
        """
        Initialize the knowledge hub with services.
        
        Args:
            config: Configuration object
            storage_dir: Directory for storage service
        """
        self.config = config or DEFAULT_CONFIG
        
        # Initialize knowledge graphs
        self.wkg = WorldKnowledgeGraph()
        self.rkg = ReasoningKnowledgeGraph()
        
        # Populate reasoning graph with initial concepts
        populate_initial_reasoning_graph(self.rkg)
        
        # Initialize services
        self.storage = StorageService(storage_dir)
        self.query = QueryService(self.wkg, self.rkg)
        self.reasoning = ReasoningService(self.rkg, self.config)
        
        logger.info("KnowledgeHubV2 initialized with specialized services")
        
    # ========================================================================
    # Delegated Operations
    # ========================================================================
    
    def find_concept(self, name: str) -> Optional[Concept]:
        """Find a concept by name (delegates to QueryService)."""
        return self.query.find_concept(name)
        
    def save(self, name: str = "default") -> Dict[str, Path]:
        """Save both knowledge graphs (delegates to StorageService)."""
        paths = {}
        paths['world'] = self.storage.save_world_knowledge(self.wkg, name)
        paths['reasoning'] = self.storage.save_reasoning_knowledge(self.rkg, name)
        return paths
        
    def load(self, name: str = "default") -> bool:
        """Load both knowledge graphs (delegates to StorageService)."""
        wkg = self.storage.load_world_knowledge(name)
        if wkg:
            self.wkg = wkg
            self.query.wkg = wkg  # Update query service
            
        rkg = self.storage.load_reasoning_knowledge(name)
        if rkg:
            self.rkg = rkg
            self.query.rkg = rkg  # Update query service
            self.reasoning.rkg = rkg  # Update reasoning service
            
        return bool(wkg or rkg)
        
    def suggest_reasoning(self, problem: str) -> List[List[Heuristic]]:
        """Suggest reasoning strategies (delegates to ReasoningService)."""
        return self.reasoning.suggest_reasoning_path(problem)
        
    def apply_reasoning(self, problem: str, 
                       target_concepts: Optional[List[Concept]] = None) -> Dict[str, Any]:
        """
        Apply reasoning to a problem.
        
        Args:
            problem: Problem description
            target_concepts: Concepts involved in the problem
            
        Returns:
            Results of reasoning
        """
        # Create context
        context = ReasoningContext(
            problem_description=problem,
            target_concepts=target_concepts or [],
            constraints={},
            available_data={}
        )
        
        # Get suggested heuristics
        heuristics = self.reasoning.select_heuristics(context)
        
        if not heuristics:
            return {
                "status": "no_applicable_strategies",
                "results": []
            }
            
        # Apply top heuristic
        result = self.reasoning.apply_heuristic(heuristics[0], context)
        
        return {
            "status": "completed",
            "strategy": result.strategy_used,
            "success": result.success,
            "discoveries": result.discoveries,
            "explanation": result.explanation
        }
        
    # ========================================================================
    # Convenience Methods
    # ========================================================================
    
    def add_concept(self, concept: Concept, metadata=None) -> None:
        """Add a concept to world knowledge."""
        self.wkg.add_concept(concept, metadata)
        
    def add_relation(self, source: Concept, target: Concept,
                    relation: Relation, **kwargs) -> None:
        """Add a relation to world knowledge."""
        self.wkg.add_relation(source, target, relation, **kwargs)
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics from all services."""
        return {
            "query_stats": self.query.get_statistics(),
            "storage_stats": self.storage.get_storage_stats(),
            "reasoning_effectiveness": {
                h.name: self.reasoning.get_heuristic_effectiveness(h)
                for h in self.reasoning.rkg.get_applicable_heuristics([])[:10]
            }
        }
        
    def __repr__(self) -> str:
        """String representation."""
        stats = self.query.get_statistics()
        return (f"KnowledgeHubV2("
                f"world_concepts={stats['world_knowledge'].get('total_concepts', 0)}, "
                f"reasoning_strategies={stats['reasoning_knowledge'].get('total_heuristics', 0)})")


# ========================================================================
# Migration Helper
# ========================================================================

def migrate_from_v1(old_hub) -> KnowledgeHubV2:
    """
    Migrate from old KnowledgeHub to new architecture.
    
    Args:
        old_hub: Instance of old KnowledgeHub
        
    Returns:
        New KnowledgeHubV2 instance with migrated data
    """
    new_hub = KnowledgeHubV2(config=old_hub.config)
    
    # Migrate graphs
    new_hub.wkg = old_hub.wkg
    new_hub.rkg = old_hub.rkg
    
    # Update services
    new_hub.query.wkg = new_hub.wkg
    new_hub.query.rkg = new_hub.rkg
    new_hub.reasoning.rkg = new_hub.rkg
    
    logger.info("Migrated from KnowledgeHub v1 to v2")
    return new_hub