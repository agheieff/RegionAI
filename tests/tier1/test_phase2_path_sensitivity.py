"""
Tests for Phase 2, Step 1: Path-Sensitive Analysis
"""
import ast
import pytest
from src.regionai.analysis.fixpoint import PathSensitiveFixpointAnalyzer
from src.regionai.analysis.cfg import build_cfg
from src.regionai.analysis.context import AnalysisContext
from src.regionai.discovery.abstract_domains import AbstractState, Sign


class TestPathSensitiveAnalysis:
    """Test path-sensitive analysis capabilities."""
    
    def test_simple_if_else_path_sensitivity(self):
        """Test that different paths maintain separate states."""
        code = """
def test_func(flag):
    if flag > 0:
        x = 1
    else:
        x = -1
    return x
"""
        tree = ast.parse(code)
        func_ast = tree.body[0]
        
        # Build CFG
        cfg = build_cfg(func_ast)
        
        # Create analyzer
        context = AnalysisContext()
        analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
        
        # Initial state with flag as TOP
        initial_state = AbstractState()
        initial_state.set_sign('flag', Sign.TOP)
        
        # Analyze
        block_states = analyzer.analyze(initial_state)
        
        # The exit block should have multiple states
        exit_states = block_states.get(cfg.exit_block, [])
        assert len(exit_states) >= 2, "Should have at least 2 states at exit (one per path)"
        
        # Check that we have both positive and negative values for x
        x_signs = set()
        for state in exit_states:
            x_sign = state.abstract_state.get_sign('x')
            x_signs.add(x_sign)
        
        assert Sign.POSITIVE in x_signs, "Should have positive x on one path"
        assert Sign.NEGATIVE in x_signs, "Should have negative x on other path"
    
    def test_path_constraints_tracked(self):
        """Test that path constraints are properly tracked."""
        code = """
def test_func(y):
    if y > 0:
        result = y + 1
    else:
        result = 0
    return result
"""
        tree = ast.parse(code)
        func_ast = tree.body[0]
        
        cfg = build_cfg(func_ast)
        context = AnalysisContext()
        analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
        
        initial_state = AbstractState()
        initial_state.set_sign('y', Sign.TOP)
        
        block_states = analyzer.analyze(initial_state)
        
        # Check that states have path constraints
        for block_id, states in block_states.items():
            for state in states:
                if len(state.path_constraints) > 0:
                    # Found a state with constraints
                    constraint = state.path_constraints[0]
                    assert isinstance(constraint.condition, ast.AST)
                    assert isinstance(constraint.is_true, bool)
    
    def test_nested_conditions(self):
        """Test nested if statements with path sensitivity."""
        code = """
def test_func(a, b):
    if a > 0:
        if b > 0:
            x = 1
        else:
            x = 2
    else:
        x = -1
    return x
"""
        tree = ast.parse(code)
        func_ast = tree.body[0]
        
        cfg = build_cfg(func_ast)
        context = AnalysisContext()
        analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
        
        initial_state = AbstractState()
        initial_state.set_sign('a', Sign.TOP)
        initial_state.set_sign('b', Sign.TOP)
        
        block_states = analyzer.analyze(initial_state)
        
        # Should have multiple abstract states at exit
        exit_states = block_states.get(cfg.exit_block, [])
        # In abstract interpretation, x=1 and x=2 are merged to x=POSITIVE
        # So we expect 2 states: one where x is POSITIVE (a>0) and one where x is NEGATIVE (a<=0)
        assert len(exit_states) >= 2, "Should have at least 2 abstract states at exit"
        
        # Check that we have different values of x
        x_values = set()
        a_values = set()
        for state in exit_states:
            # Since we're using sign analysis, we'll check signs
            x_sign = state.abstract_state.get_sign('x')
            a_sign = state.abstract_state.get_sign('a')
            x_values.add(x_sign)
            a_values.add(a_sign)
        
        # We should see both positive and negative x values
        assert Sign.POSITIVE in x_values
        assert Sign.NEGATIVE in x_values
        
        # And we should have tracked that a>0 leads to x>0
        # Find the state where x is positive
        for state in exit_states:
            if state.abstract_state.get_sign('x') == Sign.POSITIVE:
                # In this state, a should be positive (due to path constraint a>0)
                assert state.abstract_state.get_sign('a') == Sign.POSITIVE
    
    def test_path_sensitive_refinement(self):
        """Test that path constraints refine abstract values."""
        code = """
def test_func(z):
    if z > 5:
        # On this path, z is positive
        result = z * 2
    else:
        result = 0
    return result
"""
        tree = ast.parse(code)
        func_ast = tree.body[0]
        
        cfg = build_cfg(func_ast)
        context = AnalysisContext()
        analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
        
        initial_state = AbstractState()
        initial_state.set_sign('z', Sign.TOP)
        
        block_states = analyzer.analyze(initial_state)
        
        # Find states in the then branch
        for block_id, block in cfg.blocks.items():
            states = block_states.get(block_id, [])
            for state in states:
                # If this state has a constraint z > 5 and it's true
                for constraint in state.path_constraints:
                    if (isinstance(constraint.condition, ast.Compare) and 
                        isinstance(constraint.condition.left, ast.Name) and
                        constraint.condition.left.id == 'z' and 
                        constraint.is_true):
                        # z should be refined to positive on this path
                        z_sign = state.abstract_state.get_sign('z')
                        assert z_sign == Sign.POSITIVE, f"z should be positive on path with z > 5, got {z_sign}"
    
    def test_infeasible_paths_eliminated(self):
        """Test that contradictory path constraints eliminate infeasible paths."""
        code = """
def test_func(w):
    if w > 0:
        if w < 0:
            # This path is infeasible
            x = 999
        else:
            x = 1
    else:
        x = -1
    return x
"""
        tree = ast.parse(code)
        func_ast = tree.body[0]
        
        cfg = build_cfg(func_ast)
        context = AnalysisContext()
        analyzer = PathSensitiveFixpointAnalyzer(cfg, context)
        
        initial_state = AbstractState()
        initial_state.set_sign('w', Sign.TOP)
        
        block_states = analyzer.analyze(initial_state)
        
        # Check that x never gets value 999 (from infeasible path)
        # The infeasible path (w > 0 AND w < 0) should be eliminated
        
        # Collect all possible values/signs of x across all states
        x_signs_found = set()
        num_states = 0
        infeasible_path_found = False
        
        for block_id, states in block_states.items():
            for state in states:
                num_states += 1
                if 'x' in state.abstract_state.sign_state:
                    x_sign = state.abstract_state.get_sign('x')
                    x_signs_found.add(x_sign)
                    
                    # Check if this state has contradictory constraints (w > 0 AND w < 0)
                    has_w_positive = False
                    has_w_negative = False
                    
                    for constraint in state.path_constraints:
                        if (isinstance(constraint.condition, ast.Compare) and 
                            isinstance(constraint.condition.left, ast.Name) and
                            constraint.condition.left.id == 'w'):
                            
                            if constraint.is_true:
                                # Check the comparison operator
                                if isinstance(constraint.condition.ops[0], ast.Gt):
                                    has_w_positive = True
                                elif isinstance(constraint.condition.ops[0], ast.Lt):
                                    has_w_negative = True
                    
                    # If we have both constraints, this is the infeasible path
                    if has_w_positive and has_w_negative:
                        infeasible_path_found = True
        
        # Assertions
        assert num_states > 0, "Should have analyzed at least some states"
        assert Sign.POSITIVE in x_signs_found, "Should find x=1 from feasible path (w>0 and w>=0)"
        assert Sign.NEGATIVE in x_signs_found, "Should find x=-1 from feasible path (w<=0)"
        
        # The key assertion: the infeasible path should be eliminated
        # In a proper path-sensitive analysis, we should NOT find states with contradictory constraints
        assert not infeasible_path_found, "Infeasible path (w>0 AND w<0) should be eliminated by path-sensitive analysis"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])