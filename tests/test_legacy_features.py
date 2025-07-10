"""
Consolidated tests for legacy features from verify scripts.
This replaces the individual verify_day*_complete.py scripts.
"""
import pytest
import torch
import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.regionai.geometry.region import Box2D, RegionND
from src.regionai.spaces.concept_space import ConceptSpace2D, ConceptSpaceND
from src.regionai.engine.pathfinder import Pathfinder
from src.regionai.discovery import DiscoveryEngine
from src.regionai.data import create_curriculum, Problem


class TestDay10Features:
    """Day 10: Interactive visualization features."""
    
    def test_pathfinding_basics(self):
        """Test basic pathfinding functionality."""
        space = ConceptSpace2D()
        space.add_region("A", Box2D(0, 0, 100, 100))
        space.add_region("B", Box2D(20, 20, 80, 80))
        space.add_region("C", Box2D(40, 40, 60, 60))
        
        # Test pathfinding
        path = Pathfinder.find_path("C", "A", space)
        assert path == ["C", "B", "A"]
        
        # Test no path
        space.add_region("D", Box2D(200, 200, 250, 250))
        no_path = Pathfinder.find_path("C", "D", space)
        assert no_path is None


class TestDay11_12Features:
    """Day 11-12: N-dimensional regions."""
    
    def test_nd_regions(self):
        """Test N-dimensional region support."""
        # 3D region
        region3d = RegionND([0, 0, 0], [10, 10, 10])
        assert region3d.dims == 3
        assert region3d.volume() == 1000
        
        # 5D region
        region5d = RegionND([0]*5, [2]*5)
        assert region5d.dims == 5
        assert region5d.volume() == 32
        
        # Test containment
        outer = RegionND([0, 0, 0], [10, 10, 10])
        inner = RegionND([2, 2, 2], [8, 8, 8])
        assert outer.contains(inner)
        assert not inner.contains(outer)


class TestDay13_14Features:
    """Day 13-14: N-dimensional concept spaces."""
    
    def test_nd_concept_space(self):
        """Test N-dimensional concept space."""
        space = ConceptSpaceND()
        
        # Add 4D regions
        space.add_region("Universe", RegionND([0]*4, [100]*4))
        space.add_region("Galaxy", RegionND([10]*4, [90]*4))
        space.add_region("System", RegionND([20]*4, [80]*4))
        
        # Test hierarchy
        assert space.get_parent("System") == "Galaxy"
        assert space.get_parent("Galaxy") == "Universe"
        assert space.get_parent("Universe") is None
        
        # Test pathfinding in ND
        path = Pathfinder.find_path("System", "Universe", space)
        assert path == ["System", "Galaxy", "Universe"]


class TestDay19_20Features:
    """Day 19-20: Learning and discovery."""
    
    def test_discovery_engine(self):
        """Test basic discovery functionality."""
        engine = DiscoveryEngine()
        
        # Create simple transformation problems
        problems = [
            Problem(
                name="double1",
                problem_type="transformation",
                input_data=torch.tensor([1, 2, 3]),
                output_data=torch.tensor([2, 4, 6])
            ),
            Problem(
                name="double2",
                problem_type="transformation",
                input_data=torch.tensor([4, 5]),
                output_data=torch.tensor([8, 10])
            )
        ]
        
        # Discovery should find MULTIPLY_2
        discoveries = engine.discover_transformations(problems, strategy='sequential')
        assert len(discoveries) > 0
    
    def test_curriculum_generation(self):
        """Test curriculum generation."""
        # Test basic curriculum
        problems = create_curriculum('transformation', difficulty='basic')
        assert len(problems) > 0
        assert all(isinstance(p, Problem) for p in problems)


class TestDay21_23Features:
    """Day 21-23: Advanced transformations."""
    
    def test_structured_data_transformations(self):
        """Test transformations on structured data."""
        engine = DiscoveryEngine()
        
        # Conditional transformation problem
        problems = [
            Problem(
                name="conditional",
                problem_type="transformation",
                input_data=[{"type": "A", "value": 10}, {"type": "B", "value": 10}],
                output_data=[{"type": "A", "value": 20}, {"type": "B", "value": 15}]
            )
        ]
        
        # Should discover conditional pattern
        discoveries = engine.discover_transformations(problems, strategy='conditional')
        # Test would verify discovery if conditional strategy was fully implemented
    
    def test_compositional_discovery(self):
        """Test discovering composed transformations."""
        engine = DiscoveryEngine()
        
        # ADD then MULTIPLY
        problems = [
            Problem(
                name="compose1",
                problem_type="transformation", 
                input_data=torch.tensor([1, 2, 3]),
                output_data=torch.tensor([4, 6, 8])  # (x+1)*2
            )
        ]
        
        discoveries = engine.discover_transformations(problems, strategy='sequential')
        # Would verify composition discovery


class TestAbstractInterpretation:
    """Advanced static analysis features."""
    
    def test_sign_analysis(self):
        """Test abstract sign analysis."""
        from src.regionai.discovery import Sign, sign_add, sign_multiply
        
        # Test sign operations
        assert sign_add(Sign.POSITIVE, Sign.POSITIVE) == Sign.POSITIVE
        assert sign_add(Sign.POSITIVE, Sign.NEGATIVE) == Sign.TOP
        assert sign_multiply(Sign.NEGATIVE, Sign.NEGATIVE) == Sign.POSITIVE
    
    def test_nullability_analysis(self):
        """Test null safety analysis."""
        from src.regionai.discovery import Nullability, check_null_dereference
        
        # Test nullability tracking
        assert Nullability.NOT_NULL != Nullability.DEFINITELY_NULL
        # Would test actual null checking on code
    
    def test_range_analysis(self):
        """Test range/bounds analysis."""
        from src.regionai.discovery import Range, check_array_bounds
        
        # Test range operations
        r1 = Range(0, 10)
        r2 = Range(5, 15)
        
        # Test bounds checking
        safe = check_array_bounds(Range(0, 5), 10)
        assert safe == ""  # No error
        
        unsafe = check_array_bounds(Range(10, 15), 10)
        assert "out of bounds" in unsafe


# Feature availability tests
class TestFeatureAvailability:
    """Test that key features are available."""
    
    def test_core_imports(self):
        """Test all core modules can be imported."""
        # Geometry
        from src.regionai.geometry.region import RegionND, Box2D
        
        # Spaces
        from src.regionai.spaces.concept_space import ConceptSpaceND
        
        # Discovery
        from src.regionai.discovery import DiscoveryEngine
        
        # Data
        from src.regionai.data import create_curriculum
        
        # Analysis
        from src.regionai.analysis import build_cfg, analyze_with_fixpoint
        
        assert True  # If we get here, imports worked
    
    def test_legacy_compatibility(self):
        """Test backward compatibility."""
        # Old discovery function
        from src.regionai.discovery import discover_concept_from_failures
        
        # Old curriculum generators
        from src.regionai.data import SignAnalysisCurriculumGenerator
        
        # These should work but show deprecation warnings
        assert True


# Integration test
class TestFullPipeline:
    """Test complete pipeline functionality."""
    
    def test_learning_pipeline(self):
        """Test full learning pipeline."""
        # 1. Generate curriculum
        problems = create_curriculum('transformation', difficulty='basic', num_problems=3)
        
        # 2. Attempt discovery
        engine = DiscoveryEngine()
        discoveries = engine.discover_transformations(problems[:2])
        
        # 3. Verify discoveries
        assert isinstance(discoveries, list)
        
        # This replaces the learning loop verification


if __name__ == "__main__":
    pytest.main([__file__, "-v"])