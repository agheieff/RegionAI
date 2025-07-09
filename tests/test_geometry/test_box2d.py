"""Unit tests for Box2D implementation."""

import pytest
import torch
from regionai.geometry.box2d import Box2D


class TestBox2DCreation:
    """Test Box2D creation and initialization."""
    
    def test_basic_creation(self):
        """Test creating a box with explicit coordinates."""
        box = Box2D(0, 0, 10, 10)
        assert box.min_corner.tolist() == [0, 0]
        assert box.max_corner.tolist() == [10, 10]
        assert box.volume() == 100
    
    def test_from_corners(self):
        """Test creating a box from corner tuples."""
        box = Box2D.from_corners((1, 2), (5, 6))
        assert box.min_corner.tolist() == [1, 2]
        assert box.max_corner.tolist() == [5, 6]
        assert box.volume() == 16  # 4 * 4
    
    def test_from_center_size(self):
        """Test creating a box from center and size."""
        box = Box2D.from_center_size((5, 5), (4, 6))
        assert box.min_corner.tolist() == [3, 2]
        assert box.max_corner.tolist() == [7, 8]
        assert box.volume() == 24  # 4 * 6
    
    def test_invalid_box(self):
        """Test that invalid boxes raise ValueError."""
        with pytest.raises(ValueError, match="Invalid box"):
            Box2D(10, 10, 0, 0)  # min > max
    
    def test_device_specification(self):
        """Test specifying device for tensors."""
        box = Box2D(0, 0, 1, 1, device='cpu')
        assert box.min_corner.device.type == 'cpu'
        assert box.max_corner.device.type == 'cpu'


class TestBox2DProperties:
    """Test Box2D properties and methods."""
    
    def test_center(self):
        """Test center calculation."""
        box = Box2D(0, 0, 10, 10)
        assert box.center().tolist() == [5, 5]
        
        box2 = Box2D(-5, -3, 5, 3)
        assert box2.center().tolist() == [0, 0]
    
    def test_size(self):
        """Test size calculation."""
        box = Box2D(1, 2, 5, 8)
        assert box.size().tolist() == [4, 6]
    
    def test_volume(self):
        """Test volume (area) calculation."""
        box = Box2D(0, 0, 3, 4)
        assert box.volume() == 12
        
        # Test zero volume (point box)
        point_box = Box2D(5, 5, 5, 5)
        assert point_box.volume() == 0
        
        # Test small box
        small_box = Box2D(0, 0, 0.1, 0.1)
        assert pytest.approx(small_box.volume()) == 0.01


class TestBox2DContainment:
    """Test containment operations."""
    
    def test_contains_basic(self):
        """Test basic containment."""
        outer = Box2D(0, 0, 10, 10)
        inner = Box2D(2, 2, 8, 8)
        
        assert outer.contains(inner)
        assert not inner.contains(outer)
    
    def test_contains_edge_cases(self):
        """Test edge cases for containment."""
        box = Box2D(0, 0, 10, 10)
        
        # Box contains itself
        assert box.contains(box)
        
        # Touching edges (inclusive)
        edge_box = Box2D(0, 0, 10, 5)
        assert box.contains(edge_box)
        
        # Partially outside
        partial = Box2D(5, 5, 15, 15)
        assert not box.contains(partial)
        
        # Point box
        point = Box2D(5, 5, 5, 5)
        assert box.contains(point)
    
    def test_hierarchical_containment(self):
        """Test hierarchical containment (THING > ANIMAL > CAT)."""
        thing = Box2D(0, 0, 100, 100)
        animal = Box2D(10, 10, 80, 80)
        cat = Box2D(30, 30, 50, 50)
        
        assert thing.contains(animal)
        assert animal.contains(cat)
        assert thing.contains(cat)
        
        assert not cat.contains(animal)
        assert not animal.contains(thing)


class TestBox2DOverlap:
    """Test overlap operations."""
    
    def test_overlaps_basic(self):
        """Test basic overlap detection."""
        box1 = Box2D(0, 0, 5, 5)
        box2 = Box2D(3, 3, 8, 8)
        box3 = Box2D(10, 10, 15, 15)
        
        assert box1.overlaps(box2)
        assert box2.overlaps(box1)  # Symmetric
        assert not box1.overlaps(box3)
        assert not box3.overlaps(box1)
    
    def test_overlaps_edge_cases(self):
        """Test edge cases for overlap."""
        box = Box2D(0, 0, 10, 10)
        
        # Box overlaps with itself
        assert box.overlaps(box)
        
        # Touching edges (should overlap)
        touching = Box2D(10, 0, 20, 10)
        assert not box.overlaps(touching)  # Edges touching but not overlapping
        
        # One box contains another
        inner = Box2D(2, 2, 8, 8)
        assert box.overlaps(inner)
        assert inner.overlaps(box)
        
        # Corner overlap
        corner = Box2D(9, 9, 11, 11)
        assert box.overlaps(corner)


class TestBox2DOperations:
    """Test geometric operations."""
    
    def test_intersection(self):
        """Test intersection calculation."""
        box1 = Box2D(0, 0, 5, 5)
        box2 = Box2D(3, 3, 8, 8)
        
        intersection = box1.intersection(box2)
        assert intersection is not None
        assert intersection.min_corner.tolist() == [3, 3]
        assert intersection.max_corner.tolist() == [5, 5]
        assert intersection.volume() == 4
        
        # No intersection
        box3 = Box2D(10, 10, 15, 15)
        assert box1.intersection(box3) is None
    
    def test_union(self):
        """Test union (bounding box) calculation."""
        box1 = Box2D(0, 0, 5, 5)
        box2 = Box2D(3, 3, 8, 8)
        
        union = box1.union(box2)
        assert union.min_corner.tolist() == [0, 0]
        assert union.max_corner.tolist() == [8, 8]
        assert union.volume() == 64
        
        # Disjoint boxes
        box3 = Box2D(10, 10, 15, 15)
        union2 = box1.union(box3)
        assert union2.min_corner.tolist() == [0, 0]
        assert union2.max_corner.tolist() == [15, 15]
    
    def test_expand(self):
        """Test box expansion."""
        box = Box2D(2, 2, 8, 8)
        
        # No change
        same = box.expand(1.0)
        assert same.center().tolist() == box.center().tolist()
        assert same.volume() == box.volume()
        
        # Double size
        double = box.expand(2.0)
        assert double.center().tolist() == box.center().tolist()
        assert double.volume() == box.volume() * 4  # Area scales quadratically
        assert double.min_corner.tolist() == [-1, -1]
        assert double.max_corner.tolist() == [11, 11]
        
        # Shrink
        half = box.expand(0.5)
        assert half.center().tolist() == box.center().tolist()
        assert half.volume() == box.volume() / 4


class TestBox2DRepresentation:
    """Test string representations."""
    
    def test_repr(self):
        """Test __repr__ for debugging."""
        box = Box2D(1.5, 2.5, 4.5, 6.5)
        repr_str = repr(box)
        assert "Box2D" in repr_str
        assert "min=[1.5, 2.5]" in repr_str
        assert "max=[4.5, 6.5]" in repr_str
        assert "area=12.00" in repr_str
    
    def test_str(self):
        """Test __str__ for human readability."""
        box = Box2D(0, 0, 10, 10)
        str_repr = str(box)
        assert "Box2D" in str_repr
        assert "center=[5.00, 5.00]" in str_repr
        assert "size=[10.00, 10.00]" in str_repr
    
    def test_equality(self):
        """Test equality comparison."""
        box1 = Box2D(0, 0, 10, 10)
        box2 = Box2D(0, 0, 10, 10)
        box3 = Box2D(0, 0, 10, 10.1)
        
        assert box1 == box2
        assert box1 != box3
        assert box1 != "not a box"