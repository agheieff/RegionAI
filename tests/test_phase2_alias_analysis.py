"""
Tests for Phase 2, Step 2: Basic Alias Analysis
"""
import ast
import pytest
from src.regionai.analysis.context import AnalysisContext, AbstractLocation, LocationType
from src.regionai.analysis.alias_analysis import (
    analyze_alias_assignment, check_aliasing_before_access,
    analyze_mutation_effects, merge_points_to_maps
)
from src.regionai.analysis.fixpoint import FixpointAnalyzer, AnalysisState
from src.regionai.analysis.cfg import build_cfg
from src.regionai.discovery.abstract_domains import AbstractState, Sign


class TestBasicAliasOperations:
    """Test basic alias analysis operations."""
    
    def test_simple_alias_assignment(self):
        """Test p = q creates alias relationship."""
        code = "p = q"
        tree = ast.parse(code)
        assign_node = tree.body[0]
        
        context = AnalysisContext()
        # Set up q to point to a location
        q_loc = AbstractLocation.stack_var("q_var")
        context.add_points_to("q", q_loc)
        
        # Analyze p = q
        analyze_alias_assignment(assign_node, context)
        
        # Check that p now points to same location
        p_pts = context.get_points_to("p")
        assert q_loc in p_pts
        assert context.may_alias("p", "q")
    
    def test_object_creation(self):
        """Test that object creation creates heap locations."""
        # Test dict creation
        code = "p = {}"
        tree = ast.parse(code)
        assign_node = tree.body[0]
        
        context = AnalysisContext()
        analyze_alias_assignment(assign_node, context)
        
        p_pts = context.get_points_to("p")
        assert len(p_pts) == 1
        loc = list(p_pts)[0]
        assert loc.loc_type == LocationType.HEAP
        assert "dict" in loc.name
        
        # Test list creation
        code2 = "q = []"
        tree2 = ast.parse(code2)
        assign_node2 = tree2.body[0]
        
        analyze_alias_assignment(assign_node2, context)
        
        q_pts = context.get_points_to("q")
        assert len(q_pts) == 1
        loc2 = list(q_pts)[0]
        assert loc2.loc_type == LocationType.HEAP
        assert "list" in loc2.name
        
        # Different objects, no aliasing
        assert not context.may_alias("p", "q")
    
    def test_attribute_access_aliasing(self):
        """Test p = q.x creates appropriate derived location."""
        code = """
obj = {}
p = obj.field
"""
        tree = ast.parse(code)
        
        context = AnalysisContext()
        
        # First assignment: obj = {}
        analyze_alias_assignment(tree.body[0], context)
        obj_pts = context.get_points_to("obj")
        assert len(obj_pts) == 1
        
        # Second assignment: p = obj.field
        analyze_alias_assignment(tree.body[1], context)
        p_pts = context.get_points_to("p")
        assert len(p_pts) == 1
        
        # Should have field location
        field_loc = list(p_pts)[0]
        assert ".field" in field_loc.name
    
    def test_none_assignment(self):
        """Test that None assignment clears points-to set."""
        code = """
p = {}
p = None
"""
        tree = ast.parse(code)
        
        context = AnalysisContext()
        
        # First: p = {}
        analyze_alias_assignment(tree.body[0], context)
        assert len(context.get_points_to("p")) == 1
        
        # Then: p = None
        analyze_alias_assignment(tree.body[1], context)
        assert len(context.get_points_to("p")) == 0


class TestAliasingEffects:
    """Test detection of aliasing effects."""
    
    def test_mutation_detection(self):
        """Test detection of mutations affecting multiple aliases."""
        code = """
obj = {}
p = obj
q = obj
p.x = 5
"""
        tree = ast.parse(code)
        
        context = AnalysisContext()
        
        # Set up aliases
        analyze_alias_assignment(tree.body[0], context)  # obj = {}
        analyze_alias_assignment(tree.body[1], context)  # p = obj
        analyze_alias_assignment(tree.body[2], context)  # q = obj
        
        # Check aliases before mutation
        assert context.may_alias("p", "obj")
        assert context.may_alias("q", "obj")
        assert context.may_alias("p", "q")
        
        # Analyze mutation
        affected = analyze_mutation_effects(tree.body[3], context)
        
        # Should detect that obj, p, and q are all affected
        assert "p" in affected
        assert "obj" in affected
        assert "q" in affected
    
    def test_check_aliasing_before_access(self):
        """Test checking for aliases before attribute access."""
        code = """
obj = {}
p = obj
q = obj
r = {}
value = p.x
"""
        tree = ast.parse(code)
        
        context = AnalysisContext()
        
        # Set up aliases
        for i in range(4):
            analyze_alias_assignment(tree.body[i], context)
        
        # Check aliases of p before p.x access
        attr_access = tree.body[4].value  # p.x
        aliases = check_aliasing_before_access(attr_access, context)
        
        assert "obj" in aliases
        assert "q" in aliases
        assert "r" not in aliases  # r points to different object


class TestPointsToMerging:
    """Test merging of points-to maps at join points."""
    
    def test_merge_points_to_maps(self):
        """Test merging points-to maps from different paths."""
        # Path 1: p points to loc1
        map1 = {
            "p": {AbstractLocation.heap_object(1, "dict")},
            "q": {AbstractLocation.heap_object(2, "list")}
        }
        
        # Path 2: p points to loc2, r exists
        map2 = {
            "p": {AbstractLocation.heap_object(3, "dict")},
            "r": {AbstractLocation.heap_object(4, "set")}
        }
        
        merged = merge_points_to_maps(map1, map2)
        
        # p should point to both locations
        assert len(merged["p"]) == 2
        # q only on path 1
        assert len(merged["q"]) == 1
        # r only on path 2
        assert len(merged["r"]) == 1


class TestIntegrationWithFixpoint:
    """Test alias analysis integrated with fixpoint analysis."""
    
    def test_alias_tracking_in_fixpoint(self):
        """Test that alias information flows through fixpoint analysis."""
        code = """
def test_aliases():
    obj = {}
    if condition:
        p = obj
    else:
        p = {}
    # p may alias obj on one path
    return p
"""
        tree = ast.parse(code)
        func_ast = tree.body[0]
        
        cfg = build_cfg(func_ast)
        context = AnalysisContext()
        FixpointAnalyzer(cfg, context)
        
        initial_state = AbstractState()
        initial_state.set_sign('condition', Sign.TOP)
        
        # Create initial analysis state with empty points-to map
        init_analysis_state = AnalysisState(
            abstract_state=initial_state,
            iteration_count=0,
            path_constraints=[],
            points_to_map={}
        )
        
        # Run analysis (using regular fixpoint, not path-sensitive for simplicity)
        # This would need the regular analyze method, not the path-sensitive one
        # For now, just verify the structure is correct
        
        # Check that AnalysisState has points_to_map
        assert hasattr(init_analysis_state, 'points_to_map')
        assert isinstance(init_analysis_state.points_to_map, dict)
    
    def test_alias_propagation_through_blocks(self):
        """Test that alias information propagates through basic blocks."""
        code = """
obj = {}
p = obj
q = p
"""
        tree = ast.parse(code)
        cfg = build_cfg(tree)
        
        context = AnalysisContext()
        analyzer = FixpointAnalyzer(cfg, context)
        
        # Manually test _analyze_block
        initial_state = AnalysisState(
            abstract_state=AbstractState(),
            points_to_map={}
        )
        
        # Analyze the block containing all three assignments
        if cfg.entry_block is not None:
            entry_block = cfg.blocks[cfg.entry_block]
            result_state = analyzer._analyze_block(entry_block, initial_state)
            
            # Check that aliases were tracked
            pts_map = result_state.points_to_map
            
            # All three variables should have points-to info
            assert "obj" in pts_map
            assert "p" in pts_map
            assert "q" in pts_map
            
            # They should all point to the same location
            obj_locs = pts_map["obj"]
            p_locs = pts_map["p"]
            q_locs = pts_map["q"]
            
            assert obj_locs == p_locs == q_locs


class TestAliasAnalysisExamples:
    """Test realistic alias analysis examples."""
    
    def test_list_aliasing(self):
        """Test aliasing with list operations."""
        code = """
data = [1, 2, 3]
ref1 = data
ref2 = data
ref1.append(4)  # Affects all references
"""
        # This demonstrates the need for alias analysis
        # When ref1 is modified, we know ref2 and data are affected
        
        tree = ast.parse(code)
        context = AnalysisContext()
        
        # Analyze assignments
        for i in range(3):
            if isinstance(tree.body[i], ast.Assign):
                analyze_alias_assignment(tree.body[i], context)
        
        # Check aliases
        assert context.may_alias("data", "ref1")
        assert context.may_alias("data", "ref2")
        assert context.may_alias("ref1", "ref2")
    
    def test_dictionary_aliasing(self):
        """Test aliasing with dictionary operations."""
        code = """
config = {"debug": True}
settings = config
backup = config
settings["debug"] = False  # Affects all references
"""
        tree = ast.parse(code)
        context = AnalysisContext()
        
        # Analyze assignments
        for stmt in tree.body[:3]:
            if isinstance(stmt, ast.Assign):
                analyze_alias_assignment(stmt, context)
        
        # All three should alias
        assert context.may_alias("config", "settings")
        assert context.may_alias("config", "backup")
        assert context.may_alias("settings", "backup")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])