"""Analysis tools for concept relationships."""

from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from ..spaces.concept_space_2d import ConceptSpace2D
from ..geometry.box2d import Box2D


class RelationshipType(Enum):
    """Types of relationships between regions."""
    
    CONTAINS = "contains"
    CONTAINED_BY = "contained_by"
    OVERLAPS = "overlaps"
    DISJOINT = "disjoint"
    IDENTICAL = "identical"


@dataclass
class Relationship:
    """Represents a relationship between two regions."""
    
    source: str
    target: str
    relationship_type: RelationshipType
    confidence: float = 1.0
    
    def __str__(self):
        return f"{self.source} {self.relationship_type.value} {self.target}"


@dataclass
class HierarchyChain:
    """Represents a hierarchical chain of concepts."""
    
    chain: List[str]
    
    def __str__(self):
        return " > ".join(self.chain)
    
    @property
    def depth(self) -> int:
        """Get the depth of the hierarchy."""
        return len(self.chain)
    
    @property
    def root(self) -> str:
        """Get the root (most general) concept."""
        return self.chain[0] if self.chain else ""
    
    @property
    def leaf(self) -> str:
        """Get the leaf (most specific) concept."""
        return self.chain[-1] if self.chain else ""


@dataclass
class AnalysisResult:
    """Results from relationship analysis."""
    
    relationships: List[Relationship]
    hierarchies: List[HierarchyChain]
    inconsistencies: List[str]
    statistics: Dict[str, float]


class RelationshipAnalyzer:
    """Analyzes relationships between concept regions."""
    
    def __init__(self, space: ConceptSpace2D):
        """Initialize the analyzer.
        
        Args:
            space: The concept space to analyze
        """
        self.space = space
    
    def analyze_all(self) -> AnalysisResult:
        """Perform complete relationship analysis.
        
        Returns:
            AnalysisResult with all findings
        """
        relationships = self.find_all_relationships()
        hierarchies = self.find_hierarchical_chains()
        inconsistencies = self.detect_inconsistencies()
        statistics = self.compute_statistics()
        
        return AnalysisResult(
            relationships=relationships,
            hierarchies=hierarchies,
            inconsistencies=inconsistencies,
            statistics=statistics
        )
    
    def find_all_relationships(self) -> List[Relationship]:
        """Find all pairwise relationships between regions.
        
        Returns:
            List of all relationships
        """
        relationships = []
        region_names = list(self.space.list_regions())
        
        for i, name1 in enumerate(region_names):
            region1 = self.space.get_region(name1)
            
            for name2 in region_names[i+1:]:
                region2 = self.space.get_region(name2)
                
                # Check containment
                if region1.contains(region2):
                    relationships.append(Relationship(
                        name1, name2, RelationshipType.CONTAINS
                    ))
                    relationships.append(Relationship(
                        name2, name1, RelationshipType.CONTAINED_BY
                    ))
                elif region2.contains(region1):
                    relationships.append(Relationship(
                        name2, name1, RelationshipType.CONTAINS
                    ))
                    relationships.append(Relationship(
                        name1, name2, RelationshipType.CONTAINED_BY
                    ))
                elif region1.overlaps(region2):
                    relationships.append(Relationship(
                        name1, name2, RelationshipType.OVERLAPS
                    ))
                    relationships.append(Relationship(
                        name2, name1, RelationshipType.OVERLAPS
                    ))
                else:
                    relationships.append(Relationship(
                        name1, name2, RelationshipType.DISJOINT
                    ))
                    relationships.append(Relationship(
                        name2, name1, RelationshipType.DISJOINT
                    ))
        
        return relationships
    
    def find_hierarchical_chains(self) -> List[HierarchyChain]:
        """Find all hierarchical chains in the concept space.
        
        Returns:
            List of hierarchical chains from most general to most specific
        """
        chains = []
        
        # Build containment graph
        containment = self.space.get_hierarchical_relationships()
        
        # Find roots (regions not contained by any other)
        all_regions = set(self.space.list_regions())
        contained = set()
        for children in containment.values():
            contained.update(children)
        roots = all_regions - contained
        
        # Build chains from each root
        for root in roots:
            self._build_chains_from(root, containment, [], chains)
        
        # Sort by depth (longest first)
        chains.sort(key=lambda c: c.depth, reverse=True)
        
        return chains
    
    def _build_chains_from(self, node: str, containment: Dict[str, List[str]], 
                          current_chain: List[str], chains: List[HierarchyChain]):
        """Recursively build hierarchy chains."""
        current_chain = current_chain + [node]
        children = containment.get(node, [])
        
        if not children:
            # Leaf node - add chain
            chains.append(HierarchyChain(current_chain))
        else:
            # Continue building
            for child in children:
                self._build_chains_from(child, containment, current_chain, chains)
    
    def detect_inconsistencies(self) -> List[str]:
        """Detect logical inconsistencies in relationships.
        
        Returns:
            List of inconsistency descriptions
        """
        inconsistencies = []
        
        # Check for circular containment
        circular = self._find_circular_containment()
        for cycle in circular:
            inconsistencies.append(f"Circular containment: {' -> '.join(cycle + [cycle[0]])}")
        
        # Check for impossible overlaps (A contains B, B overlaps C, A doesn't overlap C)
        region_names = list(self.space.list_regions())
        for a_name in region_names:
            a_region = self.space.get_region(a_name)
            
            for b_name in region_names:
                if a_name == b_name:
                    continue
                    
                b_region = self.space.get_region(b_name)
                if not a_region.contains(b_region):
                    continue
                
                # A contains B
                for c_name in region_names:
                    if c_name in (a_name, b_name):
                        continue
                        
                    c_region = self.space.get_region(c_name)
                    
                    # Check for impossible overlap
                    if b_region.overlaps(c_region) and not a_region.overlaps(c_region):
                        inconsistencies.append(
                            f"Impossible overlap: {a_name} contains {b_name}, "
                            f"{b_name} overlaps {c_name}, but {a_name} doesn't overlap {c_name}"
                        )
        
        return inconsistencies
    
    def _find_circular_containment(self) -> List[List[str]]:
        """Find circular containment relationships."""
        cycles = []
        containment = self.space.get_hierarchical_relationships()
        
        # DFS to find cycles
        visited = set()
        rec_stack = set()
        
        for node in self.space.list_regions():
            if node not in visited:
                path = []
                if self._has_cycle(node, containment, visited, rec_stack, path):
                    cycles.append(path)
        
        return cycles
    
    def _has_cycle(self, node: str, graph: Dict[str, List[str]], 
                   visited: Set[str], rec_stack: Set[str], path: List[str]) -> bool:
        """DFS helper to detect cycles."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)
        
        for child in graph.get(node, []):
            if child not in visited:
                if self._has_cycle(child, graph, visited, rec_stack, path):
                    return True
            elif child in rec_stack:
                # Found cycle
                cycle_start = path.index(child)
                path[:] = path[cycle_start:]
                return True
        
        path.pop()
        rec_stack.remove(node)
        return False
    
    def compute_statistics(self) -> Dict[str, float]:
        """Compute statistics about the concept space.
        
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        # Basic counts
        stats['total_regions'] = len(self.space)
        
        # Relationship counts
        relationships = self.find_all_relationships()
        stats['total_relationships'] = len(relationships)
        
        for rel_type in RelationshipType:
            count = sum(1 for r in relationships if r.relationship_type == rel_type)
            stats[f'{rel_type.value}_count'] = count
        
        # Hierarchy statistics
        hierarchies = self.find_hierarchical_chains()
        if hierarchies:
            stats['max_hierarchy_depth'] = max(h.depth for h in hierarchies)
            stats['avg_hierarchy_depth'] = sum(h.depth for h in hierarchies) / len(hierarchies)
            stats['num_hierarchies'] = len(hierarchies)
        else:
            stats['max_hierarchy_depth'] = 0
            stats['avg_hierarchy_depth'] = 0
            stats['num_hierarchies'] = 0
        
        # Coverage statistics
        total_area = 0
        overlap_area = 0
        
        for name, region in self.space.items():
            total_area += region.volume()
            
            # Calculate overlaps
            for other_name, other_region in self.space.items():
                if name < other_name and region.overlaps(other_region):
                    intersection = region.intersection(other_region)
                    if intersection:
                        overlap_area += intersection.volume()
        
        stats['total_coverage'] = total_area
        stats['overlap_coverage'] = overlap_area
        stats['overlap_percentage'] = (overlap_area / total_area * 100) if total_area > 0 else 0
        
        return stats
    
    def find_conceptual_distance(self, concept1: str, concept2: str) -> Optional[float]:
        """Calculate conceptual distance between two regions.
        
        Args:
            concept1: First concept name
            concept2: Second concept name
            
        Returns:
            Distance metric or None if concepts don't exist
        """
        if concept1 not in self.space or concept2 not in self.space:
            return None
        
        region1 = self.space.get_region(concept1)
        region2 = self.space.get_region(concept2)
        
        # Simple distance metrics
        center1 = region1.center().cpu().numpy()
        center2 = region2.center().cpu().numpy()
        
        # Euclidean distance between centers
        euclidean = ((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)**0.5
        
        # Volume ratio
        volume_ratio = min(region1.volume(), region2.volume()) / max(region1.volume(), region2.volume())
        
        # Containment penalty
        containment_penalty = 0
        if region1.contains(region2) or region2.contains(region1):
            containment_penalty = -0.5
        
        # Overlap bonus
        overlap_bonus = 0
        if region1.overlaps(region2):
            intersection = region1.intersection(region2)
            if intersection:
                overlap_ratio = intersection.volume() / min(region1.volume(), region2.volume())
                overlap_bonus = -overlap_ratio * 0.3
        
        # Combined distance
        distance = euclidean * (1 - volume_ratio) + containment_penalty + overlap_bonus
        
        return max(0, distance)