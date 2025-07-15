"""
Storage service for knowledge graphs.

This service handles persistence and retrieval of knowledge graphs,
extracted from the monolithic KnowledgeHub.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path
import pickle
import json

from tier1.knowledge.infrastructure.world_graph import WorldKnowledgeGraph
from tier1.knowledge.infrastructure.reasoning_graph import ReasoningKnowledgeGraph
from tier1.utils.memory_manager import get_memory_manager
from tier1.utils.error_handling import with_retry

logger = logging.getLogger(__name__)


class StorageService:
    """
    Handles storage and retrieval of knowledge graphs.
    
    This service is responsible for:
    - Saving knowledge graphs to disk
    - Loading knowledge graphs from disk
    - Managing graph versions
    - Handling storage optimization
    """
    
    def __init__(self, storage_dir: Optional[Path] = None, memory_manager=None):
        """
        Initialize storage service.
        
        Args:
            storage_dir: Directory for storing graphs (defaults to .regionai/storage)
            memory_manager: Optional memory manager for cleanup callbacks
        """
        self.storage_dir = storage_dir or Path.home() / ".regionai" / "storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Register cleanup callback if memory manager provided
        if memory_manager is None:
            # For backward compatibility, try to get from context
            memory_manager = get_memory_manager()
        
        if memory_manager:
            memory_manager.register_cleanup_callback(self._cleanup_old_versions)
            self.memory_manager = memory_manager
        else:
            self.memory_manager = None
        
    @with_retry(max_retries=3)
    def save_world_knowledge(self, wkg: WorldKnowledgeGraph, 
                           name: str = "default") -> Path:
        """
        Save world knowledge graph to disk.
        
        Args:
            wkg: World knowledge graph to save
            name: Name for the saved graph
            
        Returns:
            Path to saved file
        """
        file_path = self.storage_dir / f"wkg_{name}.pkl"
        
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(wkg, f)
            logger.info(f"Saved world knowledge graph to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save world knowledge graph: {e}")
            raise
            
    @with_retry(max_retries=3)
    def load_world_knowledge(self, name: str = "default") -> Optional[WorldKnowledgeGraph]:
        """
        Load world knowledge graph from disk.
        
        Args:
            name: Name of the saved graph
            
        Returns:
            Loaded graph or None if not found
        """
        file_path = self.storage_dir / f"wkg_{name}.pkl"
        
        if not file_path.exists():
            logger.warning(f"World knowledge graph not found: {file_path}")
            return None
            
        try:
            with open(file_path, 'rb') as f:
                wkg = pickle.load(f)
            logger.info(f"Loaded world knowledge graph from {file_path}")
            return wkg
        except Exception as e:
            logger.error(f"Failed to load world knowledge graph: {e}")
            return None
            
    @with_retry(max_retries=3)
    def save_reasoning_knowledge(self, rkg: ReasoningKnowledgeGraph,
                               name: str = "default") -> Path:
        """
        Save reasoning knowledge graph to disk.
        
        Args:
            rkg: Reasoning knowledge graph to save
            name: Name for the saved graph
            
        Returns:
            Path to saved file
        """
        file_path = self.storage_dir / f"rkg_{name}.pkl"
        
        try:
            with open(file_path, 'wb') as f:
                pickle.dump(rkg, f)
            logger.info(f"Saved reasoning knowledge graph to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save reasoning knowledge graph: {e}")
            raise
            
    @with_retry(max_retries=3)
    def load_reasoning_knowledge(self, name: str = "default") -> Optional[ReasoningKnowledgeGraph]:
        """
        Load reasoning knowledge graph from disk.
        
        Args:
            name: Name of the saved graph
            
        Returns:
            Loaded graph or None if not found
        """
        file_path = self.storage_dir / f"rkg_{name}.pkl"
        
        if not file_path.exists():
            logger.warning(f"Reasoning knowledge graph not found: {file_path}")
            return None
            
        try:
            with open(file_path, 'rb') as f:
                rkg = pickle.load(f)
            logger.info(f"Loaded reasoning knowledge graph from {file_path}")
            return rkg
        except Exception as e:
            logger.error(f"Failed to load reasoning knowledge graph: {e}")
            return None
            
    def export_to_json(self, wkg: WorldKnowledgeGraph, 
                      file_path: Optional[Path] = None) -> Path:
        """
        Export world knowledge graph to JSON format.
        
        Args:
            wkg: World knowledge graph to export
            file_path: Output path (defaults to storage_dir/export.json)
            
        Returns:
            Path to exported file
        """
        if file_path is None:
            file_path = self.storage_dir / "export.json"
            
        # Convert graph to serializable format
        data = {
            "concepts": [
                {
                    "name": str(concept),
                    "metadata": wkg.get_concept_metadata(concept).__dict__ if wkg.get_concept_metadata(concept) else {}
                }
                for concept in wkg.get_concepts()
            ],
            "relations": [
                {
                    "source": str(source),
                    "target": str(target),
                    "type": data.get("relation", "unknown"),
                    "metadata": data
                }
                for source, target, data in wkg.graph.edges(data=True)
            ]
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
        logger.info(f"Exported knowledge graph to {file_path}")
        return file_path
        
    def _cleanup_old_versions(self) -> None:
        """Clean up old graph versions to save space."""
        # TODO: Implement version management
        logger.debug("Cleanup of old graph versions not yet implemented")
        
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about stored graphs."""
        pkl_files = list(self.storage_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in pkl_files)
        
        return {
            "storage_dir": str(self.storage_dir),
            "num_graphs": len(pkl_files),
            "total_size_mb": total_size / 1e6,
            "graphs": [f.name for f in pkl_files]
        }