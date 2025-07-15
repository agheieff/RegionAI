"""
The Knowledge Hub: Central interface for all knowledge operations.

This module provides a unified entry point for interacting with both
the WorldKnowledgeGraph (domain-specific facts) and the ReasoningKnowledgeGraph
(abstract reasoning tools and heuristics).
"""
from typing import Optional, List, Dict, Any
import logging

from tier1.knowledge.infrastructure.world_graph import WorldKnowledgeGraph, Concept, Relation
from tier1.knowledge.infrastructure.reasoning_graph import ReasoningKnowledgeGraph, ReasoningConcept, Heuristic
from .reasoning_graph_builder import populate_initial_reasoning_graph
from tier1.config import RegionAIConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class KnowledgeHub:
    """
    The central hub for all knowledge-related operations in RegionAI.
    
    This class manages both:
    - WorldKnowledgeGraph (WKG): Domain-specific knowledge about the world
    - ReasoningKnowledgeGraph (RKG): Abstract reasoning strategies and heuristics
    
    In the future, it will coordinate interactions between these two graphs,
    enabling the system to apply abstract reasoning strategies to concrete
    domain knowledge.
    """
    
    def __init__(self, config: RegionAIConfig = None):
        """
        Initialize the Knowledge Hub with both knowledge graphs.
        
        Args:
            config: Configuration object for tuning behavior
        """
        self.config = config or DEFAULT_CONFIG
        
        # Initialize the two knowledge graphs
        self.wkg = WorldKnowledgeGraph()
        self.rkg = ReasoningKnowledgeGraph()
        
        # Populate the reasoning graph with initial concepts and heuristics
        populate_initial_reasoning_graph(self.rkg)
        
        # Future: Cross-graph interaction manager
        self._interaction_cache: Dict[str, Any] = {}
        
        logger.info("KnowledgeHub initialized with WorldKnowledgeGraph and ReasoningKnowledgeGraph")
    
    # ========================================================================
    # World Knowledge Operations (delegating to WKG)
    # ========================================================================
    
    def add_world_concept(self, concept: Concept, metadata=None):
        """Add a concept to the world knowledge graph."""
        return self.wkg.add_concept(concept, metadata)
    
    def add_world_relation(self, source: Concept, target: Concept, 
                          relation: Relation, **kwargs):
        """Add a relationship to the world knowledge graph."""
        return self.wkg.add_relation(source, target, relation, **kwargs)
    
    def get_world_concepts(self) -> List[Concept]:
        """Get all concepts from the world knowledge graph."""
        return self.wkg.get_concepts()
    
    def find_world_concept(self, name: str) -> Optional[Concept]:
        """Find a concept in the world knowledge graph by name."""
        return self.wkg.find_concept(name)
    
    # ========================================================================
    # Reasoning Knowledge Operations (delegating to RKG)
    # ========================================================================
    
    def add_reasoning_concept(self, concept: ReasoningConcept, metadata=None):
        """Add a reasoning concept to the reasoning knowledge graph."""
        return self.rkg.add_concept(concept, metadata)
    
    def get_applicable_heuristics(self, context_tags: List[str]) -> List[Heuristic]:
        """Get heuristics applicable to the given context."""
        return self.rkg.get_applicable_heuristics(context_tags)
    
    # ========================================================================
    # Cross-Graph Operations (Future Functionality)
    # ========================================================================
    
    def apply_reasoning_to_domain(self, reasoning_strategy: str, 
                                 domain_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply a reasoning strategy from RKG to domain knowledge from WKG.
        
        This is a placeholder for future functionality that will enable
        the system to use abstract reasoning strategies to solve concrete
        domain problems.
        
        Args:
            reasoning_strategy: Name of the reasoning concept to apply
            domain_context: Context from the world knowledge graph
            
        Returns:
            Results of applying the reasoning strategy
        """
        # TODO: Implement in future phases
        logger.warning("Cross-graph reasoning not yet implemented")
        return {"status": "not_implemented"}
    
    def suggest_reasoning_for_problem(self, problem_description: str) -> List[Heuristic]:
        """
        Analyze a problem and suggest applicable reasoning strategies.
        
        Future functionality to bridge the gap between domain problems
        and abstract reasoning tools.
        
        Args:
            problem_description: Natural language description of the problem
            
        Returns:
            List of applicable heuristics from the reasoning graph
        """
        # TODO: Implement in future phases
        # For now, return a simple tag-based match
        problem_tags = ["problem_solving"]  # Simplified for now
        return self.rkg.get_applicable_heuristics(problem_tags)
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about both knowledge graphs."""
        return {
            "world_knowledge": {
                "concepts": len(self.wkg.graph.nodes()),
                "relationships": len(self.wkg.graph.edges()),
                # "stats": self.wkg.get_stats()  # TODO: Add this method to WKG
            },
            "reasoning_knowledge": {
                "concepts": len(self.rkg),
                "heuristics": sum(1 for node in self.rkg.graph.nodes() 
                                if isinstance(node, Heuristic))
            }
        }
    
    def __repr__(self) -> str:
        """String representation of the Knowledge Hub."""
        stats = self.get_statistics()
        return (f"KnowledgeHub(world_concepts={stats['world_knowledge']['concepts']}, "
                f"reasoning_concepts={stats['reasoning_knowledge']['concepts']})")
    
    # ========================================================================
    # Backward Compatibility
    # ========================================================================
    
    # These properties provide backward compatibility for code expecting
    # a single KnowledgeGraph object
    
    @property
    def graph(self):
        """Backward compatibility: return the world knowledge graph's networkx graph."""
        return self.wkg.graph
    
    def add_concept(self, concept: Concept, metadata=None):
        """Backward compatibility: add to world knowledge graph."""
        return self.add_world_concept(concept, metadata)
    
    def add_relation(self, source: Concept, target: Concept, 
                    relation: Relation, **kwargs):
        """Backward compatibility: add to world knowledge graph."""
        return self.add_world_relation(source, target, relation, **kwargs)
    
    def get_all_concepts(self) -> List[Concept]:
        """Backward compatibility: get from world knowledge graph."""
        return self.get_world_concepts()
    
    def find_concept(self, name: str) -> Optional[Concept]:
        """Backward compatibility: find in world knowledge graph."""
        return self.find_world_concept(name)
    
    def __contains__(self, concept: Concept) -> bool:
        """Backward compatibility: check in world knowledge graph."""
        return concept in self.wkg