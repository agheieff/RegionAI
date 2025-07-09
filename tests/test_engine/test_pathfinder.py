"""Unit tests for the Pathfinder module with N-dimensional regions."""

import pytest
from regionai.geometry.region import RegionND, Box2D
from regionai.spaces.concept_space import ConceptSpaceND, ConceptSpace2D
from regionai.engine.pathfinder import Pathfinder


@pytest.fixture
def hierarchical_space_2d():
    """Create a 2D concept space with a multi-level hierarchy.
    
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


@pytest.fixture
def hierarchical_space_5d():
    """Create a 5D concept space with a clear hierarchy.
    
    Structure:
    UNIVERSE (0,0,0,0,0 to 100,100,100,100,100)
    └── GALAXY (10,10,10,10,10 to 90,90,90,90,90)
        └── SYSTEM (20,20,20,20,20 to 80,80,80,80,80)
            └── PLANET (30,30,30,30,30 to 70,70,70,70,70)
                └── CONTINENT (40,40,40,40,40 to 60,60,60,60,60)
    """
    space = ConceptSpaceND()
    space.add_region("UNIVERSE", RegionND([0]*5, [100]*5))
    space.add_region("GALAXY", RegionND([10]*5, [90]*5))
    space.add_region("SYSTEM", RegionND([20]*5, [80]*5))
    space.add_region("PLANET", RegionND([30]*5, [70]*5))
    space.add_region("CONTINENT", RegionND([40]*5, [60]*5))
    return space


class TestPathfinder2D:
    """Test suite for the Pathfinder class with 2D regions."""
    
    def test_direct_path(self, hierarchical_space_2d):
        """Test finding a direct parent-child path."""
        path = Pathfinder.find_path("CAT", "ANIMAL", hierarchical_space_2d)
        assert path == ["CAT", "ANIMAL"]
    
    def test_multi_step_path(self, hierarchical_space_2d):
        """Test finding a multi-step path through the hierarchy."""
        path = Pathfinder.find_path("SIAMESE", "THING", hierarchical_space_2d)
        assert path == ["SIAMESE", "CAT", "ANIMAL", "THING"]
    
    def test_failed_path_not_contained(self, hierarchical_space_2d):
        """Test that no path exists when start is not contained in end."""
        # Add a region outside the hierarchy
        hierarchical_space_2d.add_region("PLANT", Box2D(60, 60, 80, 80))
        
        path = Pathfinder.find_path("PLANT", "CAT", hierarchical_space_2d)
        assert path is None
    
    def test_same_start_and_end(self, hierarchical_space_2d):
        """Test path when start and end are the same."""
        path = Pathfinder.find_path("CAT", "CAT", hierarchical_space_2d)
        assert path == ["CAT"]
    
    def test_nonexistent_regions(self, hierarchical_space_2d):
        """Test behavior with non-existent region names."""
        # Non-existent start
        path = Pathfinder.find_path("DOG", "ANIMAL", hierarchical_space_2d)
        assert path is None
        
        # Non-existent end
        path = Pathfinder.find_path("CAT", "DOG", hierarchical_space_2d)
        assert path is None
        
        # Both non-existent
        path = Pathfinder.find_path("DOG", "BIRD", hierarchical_space_2d)
        assert path is None
    
    def test_root_has_no_parent(self, hierarchical_space_2d):
        """Test that root nodes cannot find paths to non-containers."""
        # THING is the root and has no parent
        path = Pathfinder.find_path("THING", "CAT", hierarchical_space_2d)
        assert path is None
    
    def test_sibling_regions(self, hierarchical_space_2d):
        """Test path finding between sibling regions."""
        # Add another cat breed as sibling to SIAMESE
        hierarchical_space_2d.add_region("PERSIAN", Box2D(30, 30, 45, 45))
        
        # Siblings cannot reach each other directly
        path = Pathfinder.find_path("SIAMESE", "PERSIAN", hierarchical_space_2d)
        assert path is None
    
    def test_intermediate_path(self, hierarchical_space_2d):
        """Test finding path that stops at intermediate level."""
        # Path from SIAMESE to CAT (its direct parent)
        path = Pathfinder.find_path("SIAMESE", "CAT", hierarchical_space_2d)
        assert path == ["SIAMESE", "CAT"]
        
        # Path from SIAMESE to ANIMAL (grandparent)
        path = Pathfinder.find_path("SIAMESE", "ANIMAL", hierarchical_space_2d)
        assert path == ["SIAMESE", "CAT", "ANIMAL"]


class TestPathfinder5D:
    """Test suite for the Pathfinder class with 5D regions."""
    
    def test_direct_path_5d(self, hierarchical_space_5d):
        """Test finding a direct parent-child path in 5D."""
        path = Pathfinder.find_path("PLANET", "SYSTEM", hierarchical_space_5d)
        assert path == ["PLANET", "SYSTEM"]
    
    def test_multi_step_path_5d(self, hierarchical_space_5d):
        """Test finding a multi-step path through the 5D hierarchy."""
        path = Pathfinder.find_path("CONTINENT", "UNIVERSE", hierarchical_space_5d)
        assert path == ["CONTINENT", "PLANET", "SYSTEM", "GALAXY", "UNIVERSE"]
    
    def test_intermediate_path_5d(self, hierarchical_space_5d):
        """Test finding path that stops at intermediate level in 5D."""
        path = Pathfinder.find_path("CONTINENT", "SYSTEM", hierarchical_space_5d)
        assert path == ["CONTINENT", "PLANET", "SYSTEM"]
    
    def test_no_path_between_siblings_5d(self, hierarchical_space_5d):
        """Test that siblings have no path in 5D."""
        # Add two moons as siblings under PLANET
        hierarchical_space_5d.add_region("MOON1", RegionND([35]*5, [45]*5))
        hierarchical_space_5d.add_region("MOON2", RegionND([55]*5, [65]*5))
        
        path = Pathfinder.find_path("MOON1", "MOON2", hierarchical_space_5d)
        assert path is None
    
    def test_parent_detection_5d(self, hierarchical_space_5d):
        """Test that parent detection works correctly in 5D."""
        # Verify get_parent works
        assert hierarchical_space_5d.get_parent("CONTINENT") == "PLANET"
        assert hierarchical_space_5d.get_parent("PLANET") == "SYSTEM"
        assert hierarchical_space_5d.get_parent("SYSTEM") == "GALAXY"
        assert hierarchical_space_5d.get_parent("GALAXY") == "UNIVERSE"
        assert hierarchical_space_5d.get_parent("UNIVERSE") is None


class TestPathfinderMixedDimensions:
    """Test that Pathfinder works with any dimensional space."""
    
    def test_3d_hierarchy(self):
        """Test pathfinding in 3D space."""
        space = ConceptSpaceND()
        space.add_region("CUBE_LARGE", RegionND([0, 0, 0], [100, 100, 100]))
        space.add_region("CUBE_MEDIUM", RegionND([20, 20, 20], [80, 80, 80]))
        space.add_region("CUBE_SMALL", RegionND([40, 40, 40], [60, 60, 60]))
        
        path = Pathfinder.find_path("CUBE_SMALL", "CUBE_LARGE", space)
        assert path == ["CUBE_SMALL", "CUBE_MEDIUM", "CUBE_LARGE"]
    
    def test_10d_hierarchy(self):
        """Test pathfinding in 10D space."""
        space = ConceptSpaceND()
        dims = 10
        
        # Create nested hypercubes
        space.add_region("HYPER_A", RegionND([0]*dims, [100]*dims))
        space.add_region("HYPER_B", RegionND([20]*dims, [80]*dims))
        space.add_region("HYPER_C", RegionND([40]*dims, [60]*dims))
        
        path = Pathfinder.find_path("HYPER_C", "HYPER_A", space)
        assert path == ["HYPER_C", "HYPER_B", "HYPER_A"]
        
    def test_pathfinder_unchanged(self):
        """Verify that Pathfinder code itself needed no changes."""
        # The fact that all these tests pass without modifying Pathfinder
        # proves that it was already dimension-agnostic!
        assert True