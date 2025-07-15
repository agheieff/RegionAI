"""
Comprehensive tests for call graph construction.
"""
import ast
import pytest
from src.regionai.analysis.call_graph import (
    build_call_graph, visualize_call_graph
)


class TestCallGraphBasics:
    """Test basic call graph construction."""
    
    def test_simple_call_graph(self):
        """Test building a simple call graph."""
        code = """
def foo():
    return 42

def bar():
    x = foo()
    return x + 1

def main():
    result = bar()
    print(result)
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        # Check functions are detected
        assert len(graph.functions) == 3
        assert 'foo' in graph.functions
        assert 'bar' in graph.functions
        assert 'main' in graph.functions
        
        # Check call relationships
        assert 'foo' in graph.functions['bar'].calls
        assert 'bar' in graph.functions['main'].calls
        assert 'print' in graph.functions['main'].calls
        
        # Check reverse relationships
        assert 'bar' in graph.functions['foo'].called_by
        assert 'main' in graph.functions['bar'].called_by
        
        # Check entry points
        assert 'main' in graph.entry_points
        assert 'foo' not in graph.entry_points
        assert 'bar' not in graph.entry_points
    
    def test_multiple_calls(self):
        """Test function that calls multiple functions."""
        code = """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

def calculate(x, y):
    sum_result = add(x, y)
    prod_result = multiply(x, y)
    return add(sum_result, prod_result)
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        # Check calculate calls both add and multiply
        assert 'add' in graph.functions['calculate'].calls
        assert 'multiply' in graph.functions['calculate'].calls
        
        # Check add is called twice
        call_sites = [cs for cs in graph.call_sites if cs.callee == 'add']
        assert len(call_sites) == 2
    
    def test_nested_functions(self):
        """Test handling of nested function definitions."""
        code = """
def outer():
    def inner():
        return 42
    
    result = inner()
    return result

def caller():
    return outer()
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        # Should find all functions including nested ones
        assert 'outer' in graph.functions
        assert 'inner' in graph.functions
        assert 'caller' in graph.functions
        
        # Check relationships
        assert 'inner' in graph.functions['outer'].calls
        assert 'outer' in graph.functions['caller'].calls


class TestRecursion:
    """Test handling of recursive functions."""
    
    def test_direct_recursion(self):
        """Test detection of direct recursion."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def main():
    result = factorial(5)
    print(result)
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        # Check self-call
        assert 'factorial' in graph.functions['factorial'].calls
        
        # Check recursion detection
        recursive = graph.get_recursive_functions()
        assert 'factorial' in recursive
        assert 'main' not in recursive
    
    def test_indirect_recursion(self):
        """Test detection of indirect/mutual recursion."""
        code = """
def is_even(n):
    if n == 0:
        return True
    return is_odd(n - 1)

def is_odd(n):
    if n == 0:
        return False
    return is_even(n - 1)

def check(x):
    return is_even(x)
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        # Check mutual calls
        assert 'is_odd' in graph.functions['is_even'].calls
        assert 'is_even' in graph.functions['is_odd'].calls
        
        # Check both are detected as recursive
        recursive = graph.get_recursive_functions()
        assert 'is_even' in recursive
        assert 'is_odd' in recursive
        assert 'check' not in recursive
    
    def test_complex_recursion(self):
        """Test complex recursion patterns."""
        code = """
def a():
    return b()

def b():
    return c()

def c():
    return a()

def d():
    return a()
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        recursive = graph.get_recursive_functions()
        # All of a, b, c are in a recursive cycle
        assert 'a' in recursive
        assert 'b' in recursive
        assert 'c' in recursive
        # d is not recursive
        assert 'd' not in recursive


class TestCallChains:
    """Test call chain analysis."""
    
    def test_simple_chain(self):
        """Test finding simple call chains."""
        code = """
def a():
    return b()

def b():
    return c()

def c():
    return 42
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        # Find chain from a to c
        chain = graph.get_call_chain('a', 'c')
        assert chain == ['a', 'b', 'c']
        
        # No chain from c to a
        chain = graph.get_call_chain('c', 'a')
        assert chain is None
    
    def test_multiple_paths(self):
        """Test finding shortest path when multiple exist."""
        code = """
def start():
    path1()
    path2()

def path1():
    intermediate()

def path2():
    intermediate()
    extra_step()

def intermediate():
    end()

def extra_step():
    end()

def end():
    pass
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        # Should find shortest path
        chain = graph.get_call_chain('start', 'end')
        # Either ['start', 'path1', 'intermediate', 'end'] or
        # ['start', 'path2', 'intermediate', 'end'] are valid
        assert len(chain) == 4
        assert chain[0] == 'start'
        assert chain[-1] == 'end'


class TestTopologicalSort:
    """Test topological sorting for analysis order."""
    
    def test_simple_topology(self):
        """Test basic topological sort."""
        code = """
def leaf1():
    return 1

def leaf2():
    return 2

def middle():
    return leaf1() + leaf2()

def root():
    return middle()
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        order = graph.topological_sort()
        
        # Leaves should come before their callers
        assert order.index('leaf1') < order.index('middle')
        assert order.index('leaf2') < order.index('middle')
        assert order.index('middle') < order.index('root')
    
    def test_topology_with_cycle(self):
        """Test topological sort with cycles."""
        code = """
def a():
    return b()

def b():
    return a()

def c():
    return a()
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        order = graph.topological_sort()
        
        # Should include all functions
        assert len(order) == 3
        assert 'a' in order
        assert 'b' in order
        assert 'c' in order


class TestCallSiteInformation:
    """Test detailed call site information."""
    
    def test_call_site_details(self):
        """Test that call sites capture detailed information."""
        code = """
def add(a, b):
    return a + b

def main():
    x = add(5, 10)
    y = add(x, 20)
    return y
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        # Find call sites
        add_calls = [cs for cs in graph.call_sites if cs.callee == 'add']
        assert len(add_calls) == 2
        
        # Check call site information
        for cs in add_calls:
            assert cs.caller == 'main'
            assert cs.callee == 'add'
            assert cs.line_number > 0
            assert len(cs.arguments) == 2
    
    def test_method_calls(self):
        """Test handling of method calls."""
        code = """
def process(obj):
    result = obj.method()
    value = obj.attribute
    return result
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        # Should detect method call
        assert 'method' in graph.functions['process'].calls


class TestVisualization:
    """Test call graph visualization."""
    
    def test_visualization(self):
        """Test text visualization of call graph."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def main():
    print(factorial(5))
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        viz = visualize_call_graph(graph)
        
        # Check key elements are present
        assert "Call Graph:" in viz
        assert "factorial calls:" in viz
        assert "→ factorial" in viz  # Self-call
        assert "main calls:" in viz
        assert "Entry points:" in viz
        assert "• main" in viz
        assert "Recursive functions:" in viz
        assert "↻ factorial" in viz


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_program(self):
        """Test empty program."""
        code = ""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        assert len(graph.functions) == 0
        assert len(graph.call_sites) == 0
        assert len(graph.entry_points) == 0
    
    def test_no_function_calls(self):
        """Test program with functions but no calls."""
        code = """
def foo():
    return 42

def bar():
    return 24
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        assert len(graph.functions) == 2
        assert len(graph.call_sites) == 0
        assert len(graph.entry_points) == 2
    
    def test_call_to_undefined(self):
        """Test calls to undefined functions."""
        code = """
def caller():
    result = undefined_function()
    return result
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        # Should still record the call
        assert 'undefined_function' in graph.functions['caller'].calls
        
        # But undefined_function won't be in functions dict
        assert 'undefined_function' not in graph.functions
    
    def test_lambda_calls(self):
        """Test handling of lambda function calls."""
        code = """
def process():
    f = lambda x: x * 2
    result = f(5)
    return result
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        # Lambda calls are harder to track statically
        # For now, just ensure it doesn't crash
        assert 'process' in graph.functions


class TestFunctionInfo:
    """Test FunctionInfo data structure."""
    
    def test_function_info(self):
        """Test FunctionInfo captures correct data."""
        code = """
def add(x, y):
    '''Add two numbers.'''
    return x + y
"""
        tree = ast.parse(code)
        graph = build_call_graph(tree)
        
        func_info = graph.functions['add']
        assert func_info.name == 'add'
        assert func_info.parameters == ['x', 'y']
        assert isinstance(func_info.node, ast.FunctionDef)
        assert func_info.node.name == 'add'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])