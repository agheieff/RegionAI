"""Unit tests for RegionND implementation."""

import pytest
import torch
from regionai.geometry.region import RegionND, Box2D


class TestRegionNDCreation:
    """Test RegionND creation and initialization."""

    def test_basic_creation_2d(self):
        """Test creating a 2D region."""
        region = RegionND([0, 0], [10, 10])
        assert region.dims == 2
        assert region.min_corner.tolist() == [0, 0]
        assert region.max_corner.tolist() == [10, 10]
        assert region.volume() == 100

    def test_basic_creation_3d(self):
        """Test creating a 3D region."""
        region = RegionND([0, 0, 0], [10, 10, 10])
        assert region.dims == 3
        assert region.min_corner.tolist() == [0, 0, 0]
        assert region.max_corner.tolist() == [10, 10, 10]
        assert region.volume() == 1000

    def test_basic_creation_10d(self):
        """Test creating a 10D region."""
        min_corner = [0] * 10
        max_corner = [2] * 10
        region = RegionND(min_corner, max_corner)
        assert region.dims == 10
        assert region.volume() == 2**10  # 1024

    def test_tensor_input(self):
        """Test creating region with tensor inputs."""
        min_t = torch.tensor([1.0, 2.0, 3.0])
        max_t = torch.tensor([4.0, 5.0, 6.0])
        region = RegionND(min_t, max_t)
        assert region.dims == 3
        assert region.volume() == 3 * 3 * 3  # 27

    def test_from_corners(self):
        """Test creating a region from corner sequences."""
        region = RegionND.from_corners([1, 2, 3, 4], [5, 6, 7, 8])
        assert region.dims == 4
        assert region.min_corner.tolist() == [1, 2, 3, 4]
        assert region.max_corner.tolist() == [5, 6, 7, 8]

    def test_from_center_size(self):
        """Test creating a region from center and size."""
        region = RegionND.from_center_size([5, 5, 5], [4, 6, 8])
        assert region.min_corner.tolist() == [3, 2, 1]
        assert region.max_corner.tolist() == [7, 8, 9]
        assert region.volume() == 4 * 6 * 8  # 192

    def test_invalid_region(self):
        """Test that invalid regions raise ValueError."""
        with pytest.raises(ValueError, match="Invalid region"):
            RegionND([10, 10], [0, 0])  # min > max

    def test_dimension_mismatch(self):
        """Test that mismatched dimensions raise ValueError."""
        with pytest.raises(ValueError, match="Corner dimensions must match"):
            RegionND([0, 0], [1, 1, 1])

    def test_invalid_tensor_shape(self):
        """Test that invalid tensor shapes raise ValueError."""
        with pytest.raises(ValueError, match="Corners must be 1D tensors"):
            RegionND(torch.zeros((2, 2)), torch.ones((2, 2)))

    def test_device_specification(self):
        """Test specifying device for tensors."""
        region = RegionND([0, 0, 0], [1, 1, 1], device="cpu")
        assert region.min_corner.device.type == "cpu"
        assert region.max_corner.device.type == "cpu"


class TestRegionNDProperties:
    """Test RegionND properties and methods."""

    def test_center_2d(self):
        """Test center calculation in 2D."""
        region = RegionND([0, 0], [10, 10])
        assert region.center().tolist() == [5, 5]

    def test_center_3d(self):
        """Test center calculation in 3D."""
        region = RegionND([-5, -3, -1], [5, 3, 1])
        assert region.center().tolist() == [0, 0, 0]

    def test_size_nd(self):
        """Test size calculation in N dimensions."""
        region = RegionND([1, 2, 3, 4], [5, 8, 11, 14])
        assert region.size().tolist() == [4, 6, 8, 10]

    def test_volume_nd(self):
        """Test volume calculation in various dimensions."""
        # 2D - area
        region2d = RegionND([0, 0], [3, 4])
        assert region2d.volume() == 12

        # 3D - volume
        region3d = RegionND([0, 0, 0], [2, 3, 4])
        assert region3d.volume() == 24

        # 5D - hypervolume
        region5d = RegionND([0]*5, [2]*5)
        assert region5d.volume() == 32  # 2^5

        # Zero volume (point)
        point = RegionND([5, 5, 5], [5, 5, 5])
        assert point.volume() == 0


class TestRegionNDContainment:
    """Test containment operations in N dimensions."""

    def test_contains_2d(self):
        """Test containment in 2D."""
        outer = RegionND([0, 0], [10, 10])
        inner = RegionND([2, 2], [8, 8])
        
        assert outer.contains(inner)
        assert not inner.contains(outer)
        assert outer.contains(outer)  # Self-containment

    def test_contains_3d(self):
        """Test containment in 3D."""
        cube_outer = RegionND([0, 0, 0], [10, 10, 10])
        cube_inner = RegionND([2, 2, 2], [8, 8, 8])
        
        assert cube_outer.contains(cube_inner)
        assert not cube_inner.contains(cube_outer)

    def test_contains_high_dim(self):
        """Test containment in high dimensions."""
        # Create nested 5D hypercubes
        outer = RegionND([0]*5, [10]*5)
        middle = RegionND([2]*5, [8]*5)
        inner = RegionND([4]*5, [6]*5)
        
        assert outer.contains(middle)
        assert middle.contains(inner)
        assert outer.contains(inner)
        assert not inner.contains(middle)

    def test_contains_dimension_mismatch(self):
        """Test that comparing different dimensions raises error."""
        region2d = RegionND([0, 0], [10, 10])
        region3d = RegionND([0, 0, 0], [10, 10, 10])
        
        with pytest.raises(ValueError, match="Cannot compare regions of different dimensions"):
            region2d.contains(region3d)


class TestRegionNDOverlap:
    """Test overlap operations in N dimensions."""

    def test_overlaps_2d(self):
        """Test overlap detection in 2D."""
        region1 = RegionND([0, 0], [5, 5])
        region2 = RegionND([3, 3], [8, 8])
        region3 = RegionND([10, 10], [15, 15])
        
        assert region1.overlaps(region2)
        assert region2.overlaps(region1)  # Symmetric
        assert not region1.overlaps(region3)

    def test_overlaps_3d(self):
        """Test overlap detection in 3D."""
        cube1 = RegionND([0, 0, 0], [5, 5, 5])
        cube2 = RegionND([3, 3, 3], [8, 8, 8])
        cube3 = RegionND([10, 10, 10], [15, 15, 15])
        
        assert cube1.overlaps(cube2)
        assert not cube1.overlaps(cube3)

    def test_overlaps_edge_touching(self):
        """Test that edge-touching regions don't overlap."""
        region1 = RegionND([0, 0], [5, 5])
        region2 = RegionND([5, 0], [10, 5])
        
        assert not region1.overlaps(region2)  # Edges touch but don't overlap


class TestRegionNDOperations:
    """Test geometric operations in N dimensions."""

    def test_intersection_2d(self):
        """Test intersection in 2D."""
        region1 = RegionND([0, 0], [5, 5])
        region2 = RegionND([3, 3], [8, 8])
        
        intersection = region1.intersection(region2)
        assert intersection is not None
        assert intersection.min_corner.tolist() == [3, 3]
        assert intersection.max_corner.tolist() == [5, 5]
        assert intersection.volume() == 4

    def test_intersection_3d(self):
        """Test intersection in 3D."""
        cube1 = RegionND([0, 0, 0], [6, 6, 6])
        cube2 = RegionND([3, 3, 3], [9, 9, 9])
        
        intersection = cube1.intersection(cube2)
        assert intersection is not None
        assert intersection.min_corner.tolist() == [3, 3, 3]
        assert intersection.max_corner.tolist() == [6, 6, 6]
        assert intersection.volume() == 27  # 3^3

    def test_no_intersection(self):
        """Test no intersection case."""
        region1 = RegionND([0, 0], [5, 5])
        region2 = RegionND([10, 10], [15, 15])
        
        assert region1.intersection(region2) is None

    def test_union_nd(self):
        """Test union in various dimensions."""
        # 2D union
        region1 = RegionND([0, 0], [5, 5])
        region2 = RegionND([3, 3], [8, 8])
        union = region1.union(region2)
        assert union.min_corner.tolist() == [0, 0]
        assert union.max_corner.tolist() == [8, 8]

        # 4D union
        region3 = RegionND([1, 2, 3, 4], [5, 6, 7, 8])
        region4 = RegionND([3, 4, 5, 6], [7, 8, 9, 10])
        union2 = region3.union(region4)
        assert union2.min_corner.tolist() == [1, 2, 3, 4]
        assert union2.max_corner.tolist() == [7, 8, 9, 10]

    def test_expand_nd(self):
        """Test expansion in N dimensions."""
        # 3D expansion
        cube = RegionND([2, 2, 2], [8, 8, 8])
        double = cube.expand(2.0)
        assert double.center().tolist() == cube.center().tolist()
        assert double.volume() == cube.volume() * 8  # Volume scales with dim^3
        assert double.min_corner.tolist() == [-1, -1, -1]
        assert double.max_corner.tolist() == [11, 11, 11]


class TestRegionNDRepresentation:
    """Test string representations."""

    def test_repr(self):
        """Test __repr__ for debugging."""
        region = RegionND([1.5, 2.5, 3.5], [4.5, 6.5, 8.5])
        repr_str = repr(region)
        assert "RegionND" in repr_str
        assert "dims=3" in repr_str
        assert "min=[1.5, 2.5, 3.5]" in repr_str
        assert "max=[4.5, 6.5, 8.5]" in repr_str
        assert "volume=60.00" in repr_str  # 3 * 4 * 5

    def test_str(self):
        """Test __str__ for human readability."""
        region = RegionND([0, 0, 0, 0], [10, 10, 10, 10])
        str_repr = str(region)
        assert "RegionND" in str_repr
        assert "dims=4" in str_repr
        assert "center=[5.00, 5.00, 5.00, 5.00]" in str_repr
        assert "size=[10.00, 10.00, 10.00, 10.00]" in str_repr

    def test_equality(self):
        """Test equality comparison."""
        region1 = RegionND([0, 0, 0], [10, 10, 10])
        region2 = RegionND([0, 0, 0], [10, 10, 10])
        region3 = RegionND([0, 0, 0], [10, 10, 10.1])
        region4 = RegionND([0, 0], [10, 10])  # Different dims
        
        assert region1 == region2
        assert region1 != region3
        assert region1 != region4
        assert region1 != "not a region"


class TestBox2DBackwardCompatibility:
    """Test that Box2D still works for backward compatibility."""

    def test_box2d_creation(self):
        """Test creating Box2D with old interface."""
        box = Box2D(0, 0, 10, 10)
        assert box.dims == 2
        assert box.min_corner.tolist() == [0, 0]
        assert box.max_corner.tolist() == [10, 10]
        assert box.volume() == 100

    def test_box2d_operations(self):
        """Test Box2D operations still work."""
        box1 = Box2D(0, 0, 5, 5)
        box2 = Box2D(3, 3, 8, 8)
        
        assert box1.overlaps(box2)
        assert not box1.contains(box2)
        
        intersection = box1.intersection(box2)
        assert intersection is not None
        assert intersection.volume() == 4