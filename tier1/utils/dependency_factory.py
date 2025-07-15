"""
Dependency factory for RegionAI components.

This module provides factory functions for creating components with
proper dependency injection, avoiding global state issues.
"""
import logging
from typing import Optional
from pathlib import Path

from .memory_manager_v2 import MemoryManager, create_default_memory_manager
from tier1.knowledge.hub_v2 import KnowledgeHubV2
from tier1.knowledge.storage_service import StorageService
from tier1.knowledge.query_service import QueryService
from tier1.knowledge.reasoning_service import ReasoningService
from tier1.reasoning.engine import ReasoningEngine
from tier1.config import RegionAIConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class DependencyFactory:
    """
    Factory for creating RegionAI components with proper dependency injection.
    
    This class ensures components are created with consistent dependencies
    and avoids global state issues.
    """
    
    def __init__(self, config: Optional[RegionAIConfig] = None):
        """
        Initialize the factory.
        
        Args:
            config: Configuration to use (defaults to DEFAULT_CONFIG)
        """
        self.config = config or DEFAULT_CONFIG
        self._memory_manager: Optional[MemoryManager] = None
        
    @property
    def memory_manager(self) -> MemoryManager:
        """Get or create the memory manager."""
        if self._memory_manager is None:
            self._memory_manager = create_default_memory_manager(
                max_memory_percent=self.config.max_memory_percent,
                critical_memory_percent=self.config.critical_memory_percent,
                check_interval_seconds=self.config.memory_check_interval_seconds
            )
        return self._memory_manager
        
    def create_knowledge_hub(self, storage_dir: Optional[Path] = None) -> KnowledgeHubV2:
        """
        Create a KnowledgeHub with proper dependencies.
        
        Args:
            storage_dir: Optional storage directory
            
        Returns:
            Configured KnowledgeHubV2 instance
        """
        # Create services with memory manager
        storage_service = StorageService(
            storage_dir=storage_dir,
            memory_manager=self.memory_manager
        )
        
        query_service = QueryService()
        
        reasoning_service = ReasoningService(
            utility_updater=None,  # Can be set later if needed
            config=self.config
        )
        
        # Create hub
        hub = KnowledgeHubV2(
            storage_service=storage_service,
            query_service=query_service,
            reasoning_service=reasoning_service
        )
        
        logger.info("Created KnowledgeHub with dependency injection")
        return hub
        
    def create_reasoning_engine(self, hub: Optional[KnowledgeHubV2] = None) -> ReasoningEngine:
        """
        Create a ReasoningEngine with proper dependencies.
        
        Args:
            hub: Optional KnowledgeHub (creates new one if not provided)
            
        Returns:
            Configured ReasoningEngine instance
        """
        if hub is None:
            hub = self.create_knowledge_hub()
            
        engine = ReasoningEngine(
            hub=hub,
            memory_manager=self.memory_manager
        )
        
        logger.info("Created ReasoningEngine with dependency injection")
        return engine
        
    def create_concept_discoverer(self, semantic_db):
        """
        Create a ConceptDiscoverer with proper dependencies.
        
        Args:
            semantic_db: The semantic database to analyze
            
        Returns:
            Configured ConceptDiscoverer instance
        """
        from tier1.knowledge.discovery import ConceptDiscoverer
        
        discoverer = ConceptDiscoverer(
            semantic_db=semantic_db,
            config=self.config,
            memory_manager=self.memory_manager
        )
        
        logger.info("Created ConceptDiscoverer with dependency injection")
        return discoverer


# Convenience function for simple use cases
def create_standard_components(config: Optional[RegionAIConfig] = None):
    """
    Create standard RegionAI components with proper dependencies.
    
    Args:
        config: Optional configuration
        
    Returns:
        Tuple of (knowledge_hub, reasoning_engine, memory_manager)
    """
    factory = DependencyFactory(config)
    hub = factory.create_knowledge_hub()
    engine = factory.create_reasoning_engine(hub)
    
    return hub, engine, factory.memory_manager