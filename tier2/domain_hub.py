"""
Domain Hub for managing domain knowledge modules.
"""

from typing import Dict, Any, Optional, List, Set
from .domain_module import DomainModule, DomainKnowledge


class DomainLoadError(Exception):
    """Raised when a domain module cannot be loaded."""
    pass


class DomainHub:
    """
    Central hub for managing domain knowledge modules.
    
    Handles loading domain modules, dependency resolution, and knowledge queries.
    """
    
    def __init__(self):
        self._loaded_domains: Dict[str, DomainModule] = {}
        self._available_domains = {
            "physics",
            "chemistry", 
            "mathematics",
            "linguistics",
            "biology",
            "computer_science"
        }
    
    def load_domain(self, domain_name: str) -> DomainModule:
        """
        Load a domain module by name.
        
        Args:
            domain_name: Name of the domain to load
            
        Returns:
            Loaded domain module
            
        Raises:
            DomainLoadError: If domain cannot be loaded
        """
        if domain_name not in self._available_domains:
            raise DomainLoadError(f"Domain '{domain_name}' not available")
        
        if domain_name in self._loaded_domains:
            return self._loaded_domains[domain_name]
        
        # Load the domain module
        domain_module = self._load_domain_class(domain_name)
        
        # Load dependencies first
        for dep_name in domain_module.get_dependencies():
            if dep_name not in self._loaded_domains:
                self.load_domain(dep_name)
        
        # Cache the loaded domain
        self._loaded_domains[domain_name] = domain_module
        return domain_module
    
    def _load_domain_class(self, domain_name: str) -> DomainModule:
        """Load a domain module class by name."""
        try:
            if domain_name == "physics":
                from .physics.physics_module import PhysicsModule
                return PhysicsModule()
            elif domain_name == "chemistry":
                from .chemistry.chemistry_module import ChemistryModule
                return ChemistryModule()
            elif domain_name == "mathematics":
                from .mathematics.mathematics_module import MathematicsModule
                return MathematicsModule()
            elif domain_name == "linguistics":
                from .linguistics.linguistics_module import LinguisticsModule
                return LinguisticsModule()
            elif domain_name == "biology":
                from .biology.biology_module import BiologyModule
                return BiologyModule()
            elif domain_name == "computer_science":
                from .computer_science.computer_science_module import ComputerScienceModule
                return ComputerScienceModule()
            else:
                raise DomainLoadError(f"Unknown domain: {domain_name}")
        except ImportError as e:
            raise DomainLoadError(f"Failed to load domain {domain_name}: {e}")
    
    def get_domain_knowledge(self, domain_name: str) -> DomainKnowledge:
        """Get knowledge from a specific domain."""
        domain = self.load_domain(domain_name)
        return domain.get_knowledge()
    
    def query_concept(self, domain_name: str, concept_name: str) -> Optional[Any]:
        """Query a concept from a specific domain."""
        domain = self.load_domain(domain_name)
        return domain.query_concept(concept_name)
    
    def query_cross_domain(self, concept_name: str) -> Dict[str, Any]:
        """Query a concept across all loaded domains."""
        results = {}
        for domain_name, domain in self._loaded_domains.items():
            result = domain.query_concept(concept_name)
            if result is not None:
                results[domain_name] = result
        return results
    
    def list_available_domains(self) -> List[str]:
        """List all available domain modules."""
        return list(self._available_domains)
    
    def list_loaded_domains(self) -> List[str]:
        """List currently loaded domain modules."""
        return list(self._loaded_domains.keys())
    
    def unload_domain(self, domain_name: str) -> None:
        """Unload a domain module."""
        if domain_name in self._loaded_domains:
            del self._loaded_domains[domain_name]
    
    def clear_all_domains(self) -> None:
        """Clear all loaded domain modules."""
        self._loaded_domains.clear()
    
    def get_domain_info(self, domain_name: str) -> Dict[str, Any]:
        """Get information about a domain."""
        if domain_name not in self._available_domains:
            return {}
        
        is_loaded = domain_name in self._loaded_domains
        info = {
            "name": domain_name,
            "loaded": is_loaded
        }
        
        if is_loaded:
            domain = self._loaded_domains[domain_name]
            knowledge = domain.get_knowledge()
            info.update({
                "concepts": len(knowledge.concepts),
                "relationships": len(knowledge.relationships),
                "rules": len(knowledge.rules),
                "facts": len(knowledge.facts)
            })
        
        return info