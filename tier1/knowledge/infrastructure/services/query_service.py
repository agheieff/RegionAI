"""
Query service for knowledge graphs.

This service handles all query operations on knowledge graphs,
providing a clean interface for searching and retrieving information.
"""

import logging
from typing import Optional, List, Set, Dict, Any, Callable

from tier1.knowledge.infrastructure.world_graph import WorldKnowledgeGraph, Concept
from tier1.knowledge.infrastructure.reasoning_graph import ReasoningKnowledgeGraph, Heuristic
from tier1.utils.cache import memoize_with_limit

logger = logging.getLogger(__name__)


class QueryService:
    """
    Handles queries against knowledge graphs.
    
    This service provides:
    - Concept search and retrieval
    - Relationship queries
    - Pattern matching
    - Semantic search capabilities
    """
    
    def __init__(self, wkg: Optional[WorldKnowledgeGraph] = None,
                 rkg: Optional[ReasoningKnowledgeGraph] = None):
        """
        Initialize query service.
        
        Args:
            wkg: World knowledge graph to query
            rkg: Reasoning knowledge graph to query
        """
        self.wkg = wkg
        self.rkg = rkg
        
    # ========================================================================
    # World Knowledge Queries
    # ========================================================================
    
    def find_concept(self, name: str) -> Optional[Concept]:
        """Find a concept by exact name match."""
        if not self.wkg:
            return None
            
        # Since Concept is NewType('Concept', str), we just check string value
        for node in self.wkg.graph.nodes():
            if node == name:
                return node
        return None
        
    @memoize_with_limit(max_cache_size=100)
    def find_concepts_by_pattern(self, pattern: str) -> List[Concept]:
        """
        Find concepts matching a name pattern.
        
        Args:
            pattern: Regular expression pattern
            
        Returns:
            List of matching concepts
        """
        if not self.wkg:
            return []
            
        import re
        regex = re.compile(pattern, re.IGNORECASE)
        
        matches = []
        for node in self.wkg.graph.nodes():
            if isinstance(node, str) and regex.search(node):
                matches.append(node)
                
        return matches
        
    def get_related_concepts(self, concept: Concept, 
                           relation_type: Optional[str] = None,
                           depth: int = 1) -> Set[Concept]:
        """
        Get concepts related to the given concept.
        
        Args:
            concept: Starting concept
            relation_type: Filter by relation type (optional)
            depth: How many hops to traverse (default 1)
            
        Returns:
            Set of related concepts
        """
        if not self.wkg or concept not in self.wkg.graph:
            return set()
            
        related = set()
        to_explore = [(concept, 0)]
        visited = set()
        
        while to_explore:
            current, current_depth = to_explore.pop(0)
            if current in visited or current_depth > depth:
                continue
                
            visited.add(current)
            
            # Get neighbors
            for neighbor in self.wkg.graph.neighbors(current):
                # All nodes in world knowledge graph should be concepts (strings)
                # Check relation type if specified
                if relation_type:
                    edge_data = self.wkg.graph.get_edge_data(current, neighbor)
                    if edge_data.get("relation") != relation_type:
                        continue
                        
                related.add(neighbor)
                if current_depth < depth:
                    to_explore.append((neighbor, current_depth + 1))
                        
        return related
        
    def find_path(self, source: Concept, target: Concept,
                  max_length: Optional[int] = None) -> Optional[List[Concept]]:
        """
        Find a path between two concepts.
        
        Args:
            source: Starting concept
            target: Target concept  
            max_length: Maximum path length
            
        Returns:
            List of concepts forming the path, or None if no path exists
        """
        if not self.wkg:
            return None
            
        import networkx as nx
        try:
            if max_length:
                path = nx.shortest_path(self.wkg.graph, source, target, 
                                      weight=None, method='dijkstra')
                if len(path) > max_length:
                    return None
                return path
            else:
                return nx.shortest_path(self.wkg.graph, source, target)
        except nx.NetworkXNoPath:
            return None
            
    # ========================================================================
    # Reasoning Knowledge Queries
    # ========================================================================
    
    def find_heuristics_by_context(self, context: str) -> List[Heuristic]:
        """Find heuristics applicable to a given context."""
        if not self.rkg:
            return []
            
        return self.rkg.get_applicable_heuristics([context])
        
    def find_heuristics_by_utility(self, min_utility: float = 0.5) -> List[Heuristic]:
        """Find heuristics with utility above threshold."""
        if not self.rkg:
            return []
            
        heuristics = []
        for node in self.rkg.graph.nodes():
            if isinstance(node, Heuristic) and node.expected_utility >= min_utility:
                heuristics.append(node)
                
        return sorted(heuristics, key=lambda h: h.expected_utility, reverse=True)
        
    # ========================================================================
    # Advanced Queries
    # ========================================================================
    
    def find_concept_clusters(self, min_size: int = 3) -> List[Set[Concept]]:
        """
        Find clusters of highly connected concepts.
        
        Args:
            min_size: Minimum cluster size
            
        Returns:
            List of concept clusters
        """
        if not self.wkg:
            return []
            
        import networkx as nx
        
        # Find connected components
        clusters = []
        for component in nx.connected_components(self.wkg.graph.to_undirected()):
            # All nodes should be concepts (strings)
            concepts = {n for n in component if isinstance(n, str)}
            if len(concepts) >= min_size:
                clusters.append(concepts)
                
        return sorted(clusters, key=len, reverse=True)
        
    def get_concept_importance(self, concept: Concept) -> float:
        """
        Calculate importance score for a concept based on connectivity.
        
        Args:
            concept: Concept to score
            
        Returns:
            Importance score (0-1)
        """
        if not self.wkg or concept not in self.wkg.graph:
            return 0.0
            
        import networkx as nx
        
        # Use PageRank as importance metric
        try:
            pagerank = nx.pagerank(self.wkg.graph, alpha=0.85)
            return pagerank.get(concept, 0.0)
        except:
            # Fallback to degree centrality
            degree = self.wkg.graph.degree(concept)
            max_degree = max(dict(self.wkg.graph.degree()).values()) if self.wkg.graph else 1
            return degree / max_degree if max_degree > 0 else 0.0
            
    def search_by_metadata(self, filter_func: Callable[[Any], bool]) -> List[Concept]:
        """
        Search concepts by metadata properties.
        
        Args:
            filter_func: Function that returns True for matching metadata
            
        Returns:
            List of concepts with matching metadata
        """
        if not self.wkg:
            return []
            
        matches = []
        for concept in self.wkg.get_concepts():
            metadata = self.wkg.get_concept_metadata(concept)
            if metadata and filter_func(metadata):
                matches.append(concept)
                
        return matches
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the knowledge graphs."""
        import networkx as nx
        
        stats = {
            "world_knowledge": {},
            "reasoning_knowledge": {}
        }
        
        if self.wkg:
            stats["world_knowledge"] = {
                "total_concepts": len([n for n in self.wkg.graph.nodes() 
                                     if isinstance(n, str)]),
                "total_relations": self.wkg.graph.number_of_edges(),
                "avg_degree": sum(dict(self.wkg.graph.degree()).values()) / 
                             self.wkg.graph.number_of_nodes() if self.wkg.graph else 0,
                "connected_components": len(list(
                    nx.connected_components(self.wkg.graph.to_undirected())
                )) if self.wkg.graph else 0
            }
            
        if self.rkg:
            heuristics = [n for n in self.rkg.graph.nodes() 
                         if isinstance(n, Heuristic)]
            stats["reasoning_knowledge"] = {
                "total_concepts": len(self.rkg),
                "total_heuristics": len(heuristics),
                "avg_utility": sum(h.expected_utility for h in heuristics) / 
                              len(heuristics) if heuristics else 0
            }
            
        return stats