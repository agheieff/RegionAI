"""
Consolidated tests for all curriculum generators.
"""
import pytest
import ast

from src.regionai.data.problem import Problem
from src.regionai.data import (
    SignAnalysisCurriculumGenerator,
    NullabilityCurriculumGenerator,
    RangeCurriculumGenerator,
    LoopAnalysisCurriculumGenerator,
    InterproceduralCurriculumGenerator,
    ASTCurriculumGenerator
)


class TestSignCurriculum:
    """Test sign analysis curriculum generation."""
    
    def test_basic_sign_problems(self):
        """Test basic sign tracking problems."""
        gen = SignAnalysisCurriculumGenerator()
        problems = gen.generate_basic_sign_curriculum()
        
        assert len(problems) > 0
        # Check first problem structure
        problem = problems[0]
        assert isinstance(problem.input_data, dict)
        assert 'code' in problem.input_data
        assert isinstance(problem.output_data, dict)
    
    def test_sign_arithmetic_problems(self):
        """Test sign arithmetic problems."""
        gen = SignAnalysisCurriculumGenerator()
        problems = gen.generate_sign_arithmetic_curriculum()
        
        # Verify problems involve arithmetic operations
        for problem in problems:
            code = ast.unparse(problem.input_data['code'])
            assert any(op in code for op in ['+', '-', '*', '/'])


class TestNullabilityCurriculum:
    """Test nullability analysis curriculum."""
    
    def test_basic_null_problems(self):
        """Test basic null detection problems."""
        gen = NullabilityCurriculumGenerator()
        problems = gen.generate_basic_nullability_curriculum()
        
        assert len(problems) > 0
        # Basic problems track nullability states, not errors
        # Check that problems have expected output structure
        for problem in problems:
            assert 'code' in problem.input_data
            assert isinstance(problem.output_data, dict)
    
    def test_safe_null_handling(self):
        """Test problems with safe null handling."""
        gen = NullabilityCurriculumGenerator()
        problems = gen.generate_safe_handling_curriculum()
        
        # Should include if-checks for null
        for problem in problems:
            code = ast.unparse(problem.input_data['code'])
            if 'if' in code and 'None' in code:
                # Found safe handling pattern
                assert problem.output_data.get('errors', 0) == 0
                break


class TestRangeCurriculum:
    """Test range analysis curriculum."""
    
    def test_array_bounds_problems(self):
        """Test array bounds checking problems."""
        gen = RangeCurriculumGenerator()
        problems = gen.generate_array_bounds_curriculum()
        
        assert len(problems) > 0
        # Should include both safe and unsafe array accesses
        has_bounds_error = False
        has_safe_access = False
        
        for problem in problems:
            if problem.output_data.get('errors', 0) > 0:
                has_bounds_error = True
            else:
                has_safe_access = True
        
        assert has_bounds_error and has_safe_access


class TestLoopCurriculum:
    """Test loop analysis curriculum."""
    
    def test_simple_loops(self):
        """Test simple loop analysis problems."""
        gen = LoopAnalysisCurriculumGenerator()
        problems = gen.generate_simple_loop_curriculum()
        
        assert len(problems) > 0
        # All problems should contain loops
        for problem in problems:
            code = ast.unparse(problem.input_data['code'])
            assert 'while' in code or 'for' in code
    
    def test_nested_loops(self):
        """Test nested loop problems."""
        gen = LoopAnalysisCurriculumGenerator()
        problems = gen.generate_nested_loop_curriculum()
        
        # Should have nested structure
        for problem in problems:
            tree = problem.input_data['code']
            # Count loop nesting depth
            loop_depth = self._count_loop_depth(tree)
            assert loop_depth >= 2
    
    def _count_loop_depth(self, tree):
        """Count maximum loop nesting depth."""
        class LoopCounter(ast.NodeVisitor):
            def __init__(self):
                self.max_depth = 0
                self.current_depth = 0
            
            def visit_While(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
            
            def visit_For(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
        
        counter = LoopCounter()
        counter.visit(tree)
        return counter.max_depth


class TestInterproceduralCurriculum:
    """Test interprocedural analysis curriculum."""
    
    def test_basic_interprocedural(self):
        """Test basic function call problems."""
        gen = InterproceduralCurriculumGenerator()
        problems = gen.generate_basic_interprocedural_curriculum()
        
        assert len(problems) > 0
        # Should involve multiple functions
        for problem in problems:
            tree = problem.input_data['code']
            func_count = sum(1 for node in ast.walk(tree) 
                           if isinstance(node, ast.FunctionDef))
            assert func_count >= 2
    
    def test_recursive_problems(self):
        """Test recursive function problems."""
        gen = InterproceduralCurriculumGenerator()
        problems = gen.generate_recursive_curriculum()
        
        # Should include recursive patterns
        for problem in problems:
            code = ast.unparse(problem.input_data['code'])
            # Simple heuristic: function calls itself
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if 'def ' in line:
                    func_name = line.split('def ')[1].split('(')[0]
                    # Check if function calls itself
                    for j in range(i+1, len(lines)):
                        if func_name + '(' in lines[j]:
                            return  # Found recursion
        
        assert False, "No recursive patterns found"


class TestASTCurriculum:
    """Test AST transformation curriculum."""
    
    def test_optimization_problems(self):
        """Test code optimization problems."""
        gen = ASTCurriculumGenerator()
        problems = gen.generate_ast_optimization_curriculum()
        
        assert len(problems) > 0
        # Should include optimizable patterns
        for problem in problems:
            input_code = ast.unparse(problem.input_data)
            # Check for patterns like x + 0, x * 1, etc.
            assert any(pattern in input_code 
                      for pattern in ['+ 0', '* 1', '- 0'])
    
    def test_constant_folding(self):
        """Test constant folding problems."""
        gen = ASTCurriculumGenerator()
        problems = gen.generate_constant_folding_curriculum()
        
        # Should have constant expressions
        for problem in problems:
            input_code = ast.unparse(problem.input_data)
            # Look for constant arithmetic
            assert any(f'{a} {op} {b}' in input_code
                      for a in range(1, 10)
                      for b in range(1, 10)
                      for op in ['+', '*', '-'])


# Parametrized test for all curriculum types
@pytest.mark.parametrize("curriculum_class,method", [
    (SignAnalysisCurriculumGenerator, "generate_basic_sign_curriculum"),
    (NullabilityCurriculumGenerator, "generate_basic_nullability_curriculum"),
    (RangeCurriculumGenerator, "generate_array_bounds_curriculum"),
    (LoopAnalysisCurriculumGenerator, "generate_simple_loop_curriculum"),
    (InterproceduralCurriculumGenerator, "generate_basic_interprocedural_curriculum"),
    (ASTCurriculumGenerator, "generate_ast_optimization_curriculum"),
])
def test_curriculum_structure(curriculum_class, method):
    """Test that all curricula follow expected structure."""
    gen = curriculum_class()
    problems = getattr(gen, method)()
    
    assert isinstance(problems, list)
    assert len(problems) > 0
    
    for problem in problems:
        assert isinstance(problem, Problem)
        assert hasattr(problem, 'name')
        assert hasattr(problem, 'description')
        assert hasattr(problem, 'input_data')
        assert hasattr(problem, 'output_data')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])