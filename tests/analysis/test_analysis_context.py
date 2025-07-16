#!/usr/bin/env python3
"""
Comprehensive test suite for AnalysisContext functionality.

This consolidates tests from:
- tests/verification/test_phase1_simple.py
- tests/verification/test_context_simple.py  
- tests/analysis/test_context_refactoring.py
"""
import sys
import os
import ast
import inspect

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from regionai.analysis.context import AnalysisContext
from regionai.config import RegionAIConfig
from regionai.analysis.fixpoint import analyze_with_fixpoint
from regionai.core.abstract_domains import (
    Sign, Nullability, AbstractState, analyze_sign, check_null_dereference,
    prove_property, analyze_assignment
)


class TestAnalysisContextCreation:
    """Test basic AnalysisContext creation and operations."""
    
    def test_basic_state_operations(self):
        """Test creating and using an AnalysisContext."""
        context = AnalysisContext()
        
        # Test basic state operations
        context.abstract_state.update_sign('x', Sign.POSITIVE)
        context.abstract_state.update_nullability('ptr', Nullability.NOT_NULL)
        
        assert context.abstract_state.get_sign('x') == Sign.POSITIVE
        assert context.abstract_state.get_nullability('ptr') == Nullability.NOT_NULL
    
    def test_error_warning_tracking(self):
        """Test error and warning tracking."""
        context = AnalysisContext()
        
        # Test error/warning tracking
        context.add_error("Test error")
        context.add_warning("Test warning")
        
        assert len(context.errors) == 1
        assert len(context.warnings) == 1
        assert context.errors[0] == "Test error"
        assert context.warnings[0] == "Test warning"
    
    def test_context_reset(self):
        """Test resetting context state."""
        context = AnalysisContext()
        
        # Add some state
        context.abstract_state.update_sign('x', Sign.POSITIVE)
        context.add_error("Test error")
        context.add_warning("Test warning")
        
        # Reset
        context.reset()
        assert context.abstract_state.get_sign('x') is None
        assert len(context.errors) == 0
        assert len(context.warnings) == 0
    
    def test_config_usage(self):
        """Test using RegionAIConfig in context."""
        config = RegionAIConfig(
            widening_threshold=5,
            max_fixpoint_iterations=50,
            enable_path_sensitivity=True
        )
        
        context = AnalysisContext(config=config)
        
        assert context.config.widening_threshold == 5
        assert context.config.max_fixpoint_iterations == 50
        assert context.config.enable_path_sensitivity == True


class TestAnalyzeFunctions:
    """Test analyze functions with AnalysisContext."""
    
    def test_analyze_sign_with_context(self):
        """Test the refactored analyze_sign function with context."""
        context = AnalysisContext()
        
        # Test constant
        node = ast.parse("5").body[0].value
        sign = analyze_sign(node, context)
        assert sign == Sign.POSITIVE
        
        # Test variable lookup
        context.abstract_state.update_sign('x', Sign.NEGATIVE)
        node = ast.parse("x").body[0].value
        sign = analyze_sign(node, context)
        assert sign == Sign.NEGATIVE
        
        # Test negation
        node = ast.parse("-5").body[0].value
        sign = analyze_sign(node, context)
        assert sign == Sign.NEGATIVE
    
    def test_analyze_assignment_with_explicit_state(self):
        """Test analyze_assignment with explicit abstract state."""
        # Create AST for x = 5
        assign_node = ast.Assign(
            targets=[ast.Name(id='x', ctx=ast.Store())],
            value=ast.Constant(value=5)
        )
        
        # Create context and abstract state
        context = AnalysisContext()
        abstract_state = AbstractState()
        
        # Call analyze_assignment with explicit state
        analyze_assignment(assign_node, context, abstract_state)
        
        # Check result
        x_sign = abstract_state.get_sign('x')
        assert x_sign == Sign.POSITIVE
    
    def test_analyze_assignment_with_context_state(self):
        """Test analyze_assignment using context's abstract state."""
        # Create AST for y = -10
        assign_node = ast.Assign(
            targets=[ast.Name(id='y', ctx=ast.Store())],
            value=ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=10))
        )
        
        # Create context with its own abstract state
        context = AnalysisContext()
        
        # Call analyze_assignment without explicit state (uses context's)
        analyze_assignment(assign_node, context)
        
        # Check result
        y_sign = context.abstract_state.get_sign('y')
        assert y_sign == Sign.NEGATIVE
    
    def test_analyze_assignment_null_handling(self):
        """Test analyze_assignment with null values."""
        context = AnalysisContext()
        
        # Test sign assignment
        code = "x = 10"
        node = ast.parse(code).body[0]
        analyze_assignment(node, context)
        
        assert context.abstract_state.get_sign('x') == Sign.POSITIVE
        assert context.abstract_state.get_nullability('x') == Nullability.NOT_NULL
        
        # Test null assignment
        code = "ptr = None"
        node = ast.parse(code).body[0]
        analyze_assignment(node, context)
        
        assert context.abstract_state.get_nullability('ptr') == Nullability.DEFINITELY_NULL
    
    def test_analyze_assignment_parameter_signature(self):
        """Verify analyze_assignment accepts abstract_state parameter."""
        # Check that analyze_assignment now accepts abstract_state parameter
        sig = inspect.signature(analyze_assignment)
        params = list(sig.parameters.keys())
        
        assert 'abstract_state' in params, "analyze_assignment should have abstract_state parameter"


class TestNullDereferenceChecking:
    """Test null dereference checking with context."""
    
    def test_definitely_null_access(self):
        """Test detecting definitely null access."""
        context = AnalysisContext()
        context.abstract_state.update_nullability('ptr', Nullability.DEFINITELY_NULL)
        
        code = "ptr.field"
        tree = ast.parse(code)
        errors = check_null_dereference(tree, context)
        
        assert len(errors) == 1
        assert "Null pointer exception" in errors[0]
        assert "ptr" in errors[0]
    
    def test_nullable_access(self):
        """Test detecting potentially null access."""
        context = AnalysisContext()
        context.abstract_state.update_nullability('maybe_null', Nullability.NULLABLE)
        
        code = "maybe_null.field"
        tree = ast.parse(code)
        errors = check_null_dereference(tree, context)
        
        assert len(errors) == 1
        assert "Potential null pointer" in errors[0]
        assert "maybe_null" in errors[0]
    
    def test_safe_access(self):
        """Test safe (not null) access."""
        context = AnalysisContext()
        context.abstract_state.update_nullability('safe', Nullability.NOT_NULL)
        
        code = "safe.field"
        tree = ast.parse(code)
        errors = check_null_dereference(tree, context)
        
        assert len(errors) == 0


class TestPropertyProving:
    """Test property proving with context."""
    
    def test_prove_property_basic(self):
        """Test basic property proving."""
        context = AnalysisContext()
        
        code = """
x = 5
y = -x
z = x + y
"""
        tree = ast.parse(code)
        
        initial_state = {}
        result = prove_property(tree, initial_state, context)
        
        # x should be positive (5)
        assert 'x' in result
        assert result['x'] == True  # Has definite sign
        
        # y should be negative (-5)
        assert 'y' in result
        assert result['y'] == True  # Has definite sign
        
        # z should be TOP (5 + -5 could be any value in abstract interpretation)
        assert 'z' in result
        assert result['z'] == False  # Has TOP sign (not a definite sign)


class TestFixpointAnalysis:
    """Test fixpoint analysis with context."""
    
    def test_fixpoint_analysis_basic(self):
        """Test basic fixpoint analysis with context."""
        code = """
x = 10
while x > 0:
    x = x - 1
"""
        tree = ast.parse(code)
        
        context = AnalysisContext()
        result = analyze_with_fixpoint(tree, context=context)
        
        assert 'final_state' in result
        assert 'cfg' in result
        assert 'loops' in result
        assert result['context'] is context
        
        # Check that we got some analysis results
        final_state = result['final_state']
        if final_state:
            # x should have been analyzed
            x_sign = final_state.get_sign('x')
            assert x_sign is not None


class TestCodeStructureVerification:
    """Verify code structure changes from refactoring."""
    
    def test_interprocedural_implementation(self):
        """Check that interprocedural analysis has the required methods."""
        # Read the interprocedural.py file
        interprocedural_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 
            'src', 'regionai', 'analysis', 'interprocedural.py'
        )
        
        if os.path.exists(interprocedural_path):
            with open(interprocedural_path, 'r') as f:
                content = f.read()
            
            # Check for key methods
            checks = [
                "_collect_functions" in content,
                "_analyze_function" in content,
                "_check_global_errors" in content
            ]
            
            assert all(checks), "Interprocedural analysis missing required methods"
    
    def test_no_global_state(self):
        """Check that global state has been eliminated."""
        # Check multiple files for global state
        src_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'regionai')
        files_to_check = [
            os.path.join(src_dir, 'discovery', 'ast_primitives.py'),
            os.path.join(src_dir, 'discovery', 'abstract_domains.py'),
            os.path.join(src_dir, 'analysis', 'fixpoint.py')
        ]
        
        forbidden_patterns = [
            '_abstract_state =',
            '_state_map =',
            'global _abstract_state',
            'global _state_map',
            'GLOBAL_STATE'
        ]
        
        for file_path in files_to_check:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                
                for pattern in forbidden_patterns:
                    assert pattern not in content, f"Found forbidden pattern '{pattern}' in {os.path.basename(file_path)}"
    
    def test_context_refactoring_complete(self):
        """Check that AnalysisContext refactoring is complete."""
        # Check context.py
        context_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 
            'src', 'regionai', 'analysis', 'context.py'
        )
        
        if os.path.exists(context_path):
            with open(context_path, 'r') as f:
                context_content = f.read()
            
            # Should have variable_state_map
            assert "variable_state_map:" in context_content or "variable_state_map =" in context_content