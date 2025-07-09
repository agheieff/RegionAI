"""Unit tests for the Pathfinder module."""

import pytest
from regionai.geometry.box2d import Box2D
from regionai.spaces.concept_space_2d import ConceptSpace2D
from regionai.engine.pathfinder import Pathfinder


@pytest.fixture
def hierarchical_space():
    """Create a concept space with a multi-level hierarchy.
    
    Structure:
    THING (0,0,100,100)
    └── ANIMAL (10,10,90,90)
        └── CAT (20,20,50,50)
            └── SIAMESE (25,25,40,40)
    """
    space = ConceptSpace2D()
    space.add_region("THING", Box2D(0, 0, 100, 100))
    space.add_region("ANIMAL", Box2D(10, 10, 90, 90))
    space.add_region("CAT", Box2D(20, 20, 50, 50))
    space.add_region("SIAMESE", Box2D(25, 25, 40, 40))
    return space


class TestPathfinder:
    """Test suite for the Pathfinder class."""
    
    def test_direct_path(self, hierarchical_space):
        """Test finding a direct parent-child path."""
        path = Pathfinder.find_path("CAT", "ANIMAL", hierarchical_space)
        assert path == ["CAT", "ANIMAL"]
    
    def test_multi_step_path(self, hierarchical_space):
        """Test finding a multi-step path through the hierarchy."""
        path = Pathfinder.find_path("SIAMESE", "THING", hierarchical_space)
        assert path == ["SIAMESE", "CAT", "ANIMAL", "THING"]
    
    def test_failed_path_not_contained(self, hierarchical_space):
        """Test that no path exists when start is not contained in end."""
        # Add a region outside the hierarchy
        hierarchical_space.add_region("PLANT", Box2D(60, 60, 80, 80))
        
        path = Pathfinder.find_path("PLANT", "CAT", hierarchical_space)
        assert path is None
    
    def test_same_start_and_end(self, hierarchical_space):
        """Test path when start and end are the same."""
        path = Pathfinder.find_path("CAT", "CAT", hierarchical_space)
        assert path == ["CAT"]
    
    def test_nonexistent_regions(self, hierarchical_space):
        """Test behavior with non-existent region names."""
        # Non-existent start
        path = Pathfinder.find_path("DOG", "ANIMAL", hierarchical_space)
        assert path is None
        
        # Non-existent end
        path = Pathfinder.find_path("CAT", "DOG", hierarchical_space)
        assert path is None
        
        # Both non-existent
        path = Pathfinder.find_path("DOG", "BIRD", hierarchical_space)
        assert path is None
    
    def test_root_has_no_parent(self, hierarchical_space):
        """Test that root nodes cannot find paths to non-containers."""
        # THING is the root and has no parent
        path = Pathfinder.find_path("THING", "CAT", hierarchical_space)
        assert path is None
    
    def test_sibling_regions(self, hierarchical_space):
        """Test path finding between sibling regions."""
        # Add another cat breed as sibling to SIAMESE
        hierarchical_space.add_region("PERSIAN", Box2D(30, 30, 45, 45))
        
        # Siblings cannot reach each other directly
        path = Pathfinder.find_path("SIAMESE", "PERSIAN", hierarchical_space)
        assert path is None
    
    def test_intermediate_path(self, hierarchical_space):
        """Test finding path that stops at intermediate level."""
        # Path from SIAMESE to CAT (its direct parent)
        path = Pathfinder.find_path("SIAMESE", "CAT", hierarchical_space)
        assert path == ["SIAMESE", "CAT"]
        
        # Path from SIAMESE to ANIMAL (grandparent)
        path = Pathfinder.find_path("SIAMESE", "ANIMAL", hierarchical_space)
        assert path == ["SIAMESE", "CAT", "ANIMAL"]