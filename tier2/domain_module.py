"""
Base class for domain knowledge modules.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass


@dataclass
class DomainKnowledge:
    """Container for domain-specific knowledge."""
    domain_name: str
    concepts: Dict[str, Any]
    relationships: Dict[str, Any]
    rules: List[str]
    facts: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_name": self.domain_name,
            "concepts": self.concepts,
            "relationships": self.relationships,
            "rules": self.rules,
            "facts": self.facts
        }


class DomainModule(ABC):
    """
    Abstract base class for domain knowledge modules.
    
    Each domain module provides specialized knowledge for a specific field
    such as physics, chemistry, mathematics, etc.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._knowledge: Optional[DomainKnowledge] = None
    
    @abstractmethod
    def get_domain_name(self) -> str:
        """Get the name of this domain."""
        pass
    
    @abstractmethod
    def load_knowledge(self) -> DomainKnowledge:
        """Load domain-specific knowledge."""
        pass
    
    @abstractmethod
    def get_dependencies(self) -> Set[str]:
        """Get names of domains this module depends on."""
        pass
    
    def get_knowledge(self) -> DomainKnowledge:
        """Get the loaded domain knowledge."""
        if self._knowledge is None:
            self._knowledge = self.load_knowledge()
        return self._knowledge
    
    def query_concept(self, concept_name: str) -> Optional[Any]:
        """Query a specific concept from this domain."""
        knowledge = self.get_knowledge()
        return knowledge.concepts.get(concept_name)
    
    def query_relationship(self, relationship_name: str) -> Optional[Any]:
        """Query a specific relationship from this domain."""
        knowledge = self.get_knowledge()
        return knowledge.relationships.get(relationship_name)
    
    def get_all_concepts(self) -> List[str]:
        """Get all concept names in this domain."""
        knowledge = self.get_knowledge()
        return list(knowledge.concepts.keys())
    
    def get_all_relationships(self) -> List[str]:
        """Get all relationship names in this domain."""
        knowledge = self.get_knowledge()
        return list(knowledge.relationships.keys())
    
    def __str__(self) -> str:
        return f"DomainModule({self.name})"
    
    def __repr__(self) -> str:
        return f"DomainModule(name='{self.name}')"