"""
SemanticDB - A queryable database of semantic fingerprints.

This module provides the core infrastructure for storing and querying
semantic fingerprints, enabling discovery of functionally equivalent
or related code patterns across a codebase.
"""
from dataclasses import dataclass
from typing import Dict, List, Set, NewType, Optional, Tuple
from collections import defaultdict

from ....analysis.summary import CallContext
from .fingerprint import (
    SemanticFingerprint, Behavior, FingerprintComparison, 
    DocumentedFingerprint, DocumentationQuality
)

FunctionName = NewType('FunctionName', str)


@dataclass
class SemanticEntry:
    """
    A single entry in the semantic database.
    
    Represents a function in a specific calling context with its
    associated semantic fingerprint.
    """
    function_name: FunctionName
    context: CallContext
    fingerprint: SemanticFingerprint
    documented_fingerprint: Optional[DocumentedFingerprint] = None
    
    def __str__(self) -> str:
        behaviors = sorted(b.name for b in self.fingerprint.behaviors)
        doc_status = "documented" if self.documented_fingerprint else "undocumented"
        return f"{self.function_name} @ {self.context}: {behaviors} ({doc_status})"


class SemanticDB:
    """
    A queryable database of semantic fingerprints.
    
    Provides efficient storage and retrieval of semantic information
    about functions, supporting various types of semantic queries.
    """
    
    def __init__(self):
        # Primary storage of all entries
        self._entries: List[SemanticEntry] = []
        
        # Indexes for efficient querying
        self._by_function: Dict[FunctionName, List[SemanticEntry]] = defaultdict(list)
        self._by_behavior: Dict[Behavior, List[SemanticEntry]] = defaultdict(list)
        self._by_fingerprint: Dict[frozenset, List[SemanticEntry]] = defaultdict(list)
        
    def add(self, entry: SemanticEntry):
        """Add a new entry to the database."""
        self._entries.append(entry)
        
        # Update indexes
        self._by_function[entry.function_name].append(entry)
        
        # Index by individual behaviors
        for behavior in entry.fingerprint.behaviors:
            self._by_behavior[behavior].append(entry)
            
        # Index by complete fingerprint (using frozenset for hashability)
        fingerprint_key = frozenset(entry.fingerprint.behaviors)
        self._by_fingerprint[fingerprint_key].append(entry)
    
    def find_equivalent(self, target_fingerprint: SemanticFingerprint) -> List[SemanticEntry]:
        """
        Find all entries with exactly matching fingerprints.
        
        Two functions are considered semantically equivalent if they have
        identical sets of behaviors.
        """
        fingerprint_key = frozenset(target_fingerprint.behaviors)
        return self._by_fingerprint.get(fingerprint_key, [])
    
    def find_specializations(self, target_fingerprint: SemanticFingerprint) -> List[SemanticEntry]:
        """
        Find functions whose behaviors are a superset of the target.
        
        These are functions that do everything the target does, and possibly more.
        For example, a function that is both null-safe AND range-preserving
        is a specialization of one that is just null-safe.
        """
        results = []
        target_behaviors = target_fingerprint.behaviors
        
        for entry in self._entries:
            if entry.fingerprint.behaviors.issuperset(target_behaviors):
                results.append(entry)
                
        return results
    
    def find_generalizations(self, target_fingerprint: SemanticFingerprint) -> List[SemanticEntry]:
        """
        Find functions whose behaviors are a subset of the target.
        
        These are simpler versions that do less than the target function.
        For example, a basic identity function is a generalization of
        a null-safe identity function.
        """
        results = []
        target_behaviors = target_fingerprint.behaviors
        
        for entry in self._entries:
            if entry.fingerprint.behaviors.issubset(target_behaviors):
                results.append(entry)
                
        return results
    
    def find_similar(self, target_fingerprint: SemanticFingerprint, 
                    similarity_threshold: float = 0.5) -> List[Tuple[SemanticEntry, float]]:
        """
        Find functions with similar fingerprints based on Jaccard similarity.
        
        Returns entries with their similarity scores, sorted by descending similarity.
        """
        results = []
        
        for entry in self._entries:
            comparison = FingerprintComparison(target_fingerprint, entry.fingerprint)
            similarity = comparison.similarity_score
            
            if similarity >= similarity_threshold:
                results.append((entry, similarity))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def find_by_behavior(self, behavior: Behavior) -> List[SemanticEntry]:
        """Find all functions that exhibit a specific behavior."""
        return self._by_behavior.get(behavior, [])
    
    def find_by_behaviors(self, behaviors: Set[Behavior], 
                         mode: str = 'all') -> List[SemanticEntry]:
        """
        Find functions that exhibit specific behaviors.
        
        Args:
            behaviors: Set of behaviors to search for
            mode: 'all' (must have all behaviors) or 'any' (must have at least one)
        """
        if mode == 'all':
            # Must have all specified behaviors
            results = []
            for entry in self._entries:
                if behaviors.issubset(entry.fingerprint.behaviors):
                    results.append(entry)
            return results
        elif mode == 'any':
            # Must have at least one specified behavior
            seen = set()
            results = []
            for behavior in behaviors:
                for entry in self._by_behavior.get(behavior, []):
                    if id(entry) not in seen:
                        seen.add(id(entry))
                        results.append(entry)
            return results
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'all' or 'any'.")
    
    def find_complementary(self, target_fingerprint: SemanticFingerprint) -> List[SemanticEntry]:
        """
        Find functions that have complementary behaviors.
        
        These are functions that have some overlapping behaviors but also
        unique behaviors that might make them useful together.
        """
        results = []
        target_behaviors = target_fingerprint.behaviors
        
        for entry in self._entries:
            entry_behaviors = entry.fingerprint.behaviors
            
            # Check for overlap but not exact match or subset/superset
            if (entry_behaviors & target_behaviors and  # Has some overlap
                entry_behaviors != target_behaviors and  # Not identical
                not entry_behaviors.issubset(target_behaviors) and  # Not generalization
                not entry_behaviors.issuperset(target_behaviors)):  # Not specialization
                results.append(entry)
                
        return results
    
    def get_behavior_statistics(self) -> Dict[Behavior, int]:
        """
        Get statistics on behavior frequency in the database.
        
        Useful for understanding which behaviors are common or rare.
        """
        stats = {}
        for behavior, entries in self._by_behavior.items():
            stats[behavior] = len(entries)
        return stats
    
    def get_function_variants(self, function_name: FunctionName) -> List[SemanticEntry]:
        """
        Get all context-specific variants of a function.
        
        Shows how a function's behavior changes across different calling contexts.
        """
        return self._by_function.get(function_name, [])
    
    def find_pure_functions(self) -> List[SemanticEntry]:
        """Find all pure functions in the database."""
        return self.find_by_behavior(Behavior.PURE)
    
    def find_identity_functions(self) -> List[SemanticEntry]:
        """Find all identity functions in the database."""
        return self.find_by_behavior(Behavior.IDENTITY)
    
    def find_constant_functions(self) -> List[SemanticEntry]:
        """Find all constant-returning functions in the database."""
        return self.find_by_behavior(Behavior.CONSTANT_RETURN)
    
    def find_documented_functions(self) -> List[SemanticEntry]:
        """Find all functions that have documentation."""
        return [entry for entry in self._entries if entry.documented_fingerprint]
    
    def find_well_documented_functions(self) -> List[SemanticEntry]:
        """Find functions with high-quality documentation suitable for training."""
        return [
            entry for entry in self._entries 
            if (entry.documented_fingerprint and 
                entry.documented_fingerprint.is_well_documented())
        ]
    
    def find_training_candidates(self) -> List[SemanticEntry]:
        """Find functions suitable for language model training."""
        return [
            entry for entry in self._entries
            if (entry.documented_fingerprint and 
                DocumentationQuality.is_suitable_for_training(entry.documented_fingerprint))
        ]
    
    def get_documentation_statistics(self) -> Dict[str, int]:
        """Get statistics on documentation coverage."""
        stats = {
            'total_functions': len(self._entries),
            'documented_functions': 0,
            'well_documented_functions': 0,
            'training_candidates': 0,
        }
        
        for entry in self._entries:
            if entry.documented_fingerprint:
                stats['documented_functions'] += 1
                
                if entry.documented_fingerprint.is_well_documented():
                    stats['well_documented_functions'] += 1
                
                if DocumentationQuality.is_suitable_for_training(entry.documented_fingerprint):
                    stats['training_candidates'] += 1
        
        return stats
    
    def find_by_documentation_pattern(self, pattern: str) -> List[SemanticEntry]:
        """
        Find functions whose documentation contains a specific pattern.
        
        Useful for finding functions that describe similar behaviors.
        """
        results = []
        pattern_lower = pattern.lower()
        
        for entry in self._entries:
            if not entry.documented_fingerprint:
                continue
                
            nl_context = entry.documented_fingerprint.nl_context
            text_content = nl_context.get_text_content().lower()
            
            if pattern_lower in text_content:
                results.append(entry)
        
        return results
    
    def create_language_training_dataset(self) -> List[Tuple[str, str]]:
        """
        Create a dataset suitable for language model training.
        
        Returns pairs of (documentation, semantic_description) for training.
        """
        dataset = []
        
        for entry in self.find_training_candidates():
            doc_fp = entry.documented_fingerprint
            
            # Natural language documentation
            documentation = doc_fp.nl_context.get_text_content()
            
            # Semantic description
            semantic_desc = doc_fp.get_semantic_summary()
            
            if documentation and semantic_desc:
                dataset.append((documentation, semantic_desc))
        
        return dataset
    
    def size(self) -> int:
        """Return the number of entries in the database."""
        return len(self._entries)
    
    def clear(self):
        """Clear all entries from the database."""
        self._entries.clear()
        self._by_function.clear()
        self._by_behavior.clear()
        self._by_fingerprint.clear()
    
    def __len__(self) -> int:
        return self.size()
    
    def __iter__(self):
        return iter(self._entries)
    
    def __str__(self) -> str:
        """Human-readable summary of the database."""
        lines = [f"SemanticDB with {len(self._entries)} entries:"]
        
        # Show behavior statistics
        stats = self.get_behavior_statistics()
        if stats:
            lines.append("\nBehavior frequencies:")
            for behavior, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {behavior.name}: {count}")
        
        # Show unique functions
        unique_functions = len(self._by_function)
        lines.append(f"\nUnique functions: {unique_functions}")
        
        return "\n".join(lines)