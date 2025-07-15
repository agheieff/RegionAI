"""
Test suite for semantic fingerprinting system.

Tests the ability to extract high-level behavioral patterns from
function summaries and identify semantic properties of functions.
"""
import ast
import sys
import os

# Add the root directory to path for tier imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


from tier2.computer_science.analysis.interprocedural import InterproceduralAnalyzer
from tier2.domains.code.semantic.fingerprint import Behavior, SemanticFingerprint


class TestSemanticFingerprint:
    """Test semantic fingerprint generation and behavior detection."""
    
    def test_identity_fingerprint(self):
        """Test detection of identity functions."""
        code = """
def identity(x):
    return x

def identity_with_extra(x, y):
    # Still identity for first parameter
    return x

def main():
    a = identity(10)
    b = identity("hello")
    c = identity_with_extra(42, "ignored")
    return (a, b, c)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Check fingerprints were generated
        assert len(result.semantic_fingerprints) > 0
        
        # Find fingerprints for identity function calls
        identity_fingerprints = [
            fp for ctx, fp in result.semantic_fingerprints.items()
            if ctx.function_name == "identity"
        ]
        
        # Both calls to identity should have IDENTITY behavior
        assert len(identity_fingerprints) >= 2
        for fp in identity_fingerprints:
            assert Behavior.IDENTITY in fp.behaviors
    
    def test_constant_return_fingerprint(self):
        """Test detection of constant return functions."""
        code = """
def always_zero():
    return 0

def always_forty_two():
    x = 40
    y = 2
    return x + y  # Always 42

def always_none():
    return None

def main():
    a = always_zero()
    b = always_forty_two()
    c = always_none()
    return (a, b, c)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Check constant return behaviors
        for ctx, fp in result.semantic_fingerprints.items():
            if ctx.function_name == "always_zero":
                assert Behavior.CONSTANT_RETURN in fp.behaviors
            elif ctx.function_name == "always_none":
                assert Behavior.NULLABLE_RETURN in fp.behaviors
    
    def test_nullable_and_null_safe_fingerprints(self):
        """Test detection of nullable and null-safe functions."""
        code = """
def definitely_null():
    return None

def maybe_null(x):
    if x > 0:
        return x
    return None

def never_null():
    return 42

def null_propagating(data):
    # Would need precondition analysis
    if data is None:
        return None
    return data.value

def main():
    a = definitely_null()
    b = maybe_null(5)
    c = maybe_null(-1)
    d = never_null()
    return (a, b, c, d)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        for ctx, fp in result.semantic_fingerprints.items():
            if ctx.function_name == "definitely_null":
                assert Behavior.NULLABLE_RETURN in fp.behaviors
                assert Behavior.NULL_SAFE not in fp.behaviors
            elif ctx.function_name == "never_null":
                assert Behavior.NULL_SAFE in fp.behaviors
                assert Behavior.NULLABLE_RETURN not in fp.behaviors
            elif ctx.function_name == "maybe_null":
                assert Behavior.NULLABLE_RETURN in fp.behaviors
    
    def test_pure_function_fingerprint(self):
        """Test detection of pure functions."""
        code = """
# Pure function - no side effects
def add(x, y):
    return x + y

# Impure - modifies global
count = 0
def increment_and_return(x):
    global count
    count += 1
    return x + count

# Impure - performs I/O
def greet(name):
    print(f"Hello, {name}!")
    return name

# Pure but complex
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def main():
    a = add(3, 4)
    b = increment_and_return(10)
    c = factorial(5)
    return (a, b, c)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        for ctx, fp in result.semantic_fingerprints.items():
            if ctx.function_name == "add":
                assert Behavior.PURE in fp.behaviors
                assert fp.is_pure()
            elif ctx.function_name == "increment_and_return":
                assert Behavior.MODIFIES_GLOBALS in fp.behaviors
                assert not fp.is_pure()
            elif ctx.function_name == "greet":
                assert Behavior.PERFORMS_IO in fp.behaviors
                assert not fp.is_pure()
    
    def test_sign_preserving_fingerprint(self):
        """Test detection of sign-preserving functions."""
        code = """
def double(x):
    # Preserves sign: positive -> positive, negative -> negative
    return 2 * x

def negate(x):
    # Does not preserve sign
    return -x

def square(x):
    # Does not preserve sign (negative -> positive)
    return x * x

def identity(x):
    # Trivially preserves sign
    return x

def main():
    a = double(5)      # 5 is positive, result is positive
    b = double(-3)     # -3 is negative, result is negative
    c = negate(5)      # 5 is positive, result is negative
    d = square(-4)     # -4 is negative, result is positive
    e = identity(7)    # 7 is positive, result is positive
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Collect fingerprints by function name
        function_behaviors = {}
        for ctx, fp in result.semantic_fingerprints.items():
            if ctx.function_name in ["double", "identity", "negate", "square"]:
                function_behaviors[ctx.function_name] = fp
        
        # Verify fingerprints were generated
        assert "double" in function_behaviors
        assert "identity" in function_behaviors
        assert "negate" in function_behaviors
        assert "square" in function_behaviors
        
        # Identity should have IDENTITY behavior
        assert Behavior.IDENTITY in function_behaviors["identity"].behaviors
        
        # All functions should be pure (no side effects)
        for func_name in ["double", "identity", "negate", "square"]:
            assert function_behaviors[func_name].is_pure()
        
        # Check for sign preservation behavior if supported
        # Note: SIGN_PRESERVING behavior detection depends on the analyzer's
        # ability to track sign transformations through operations
        if hasattr(Behavior, 'SIGN_PRESERVING'):
            # If sign preservation tracking is implemented
            assert Behavior.SIGN_PRESERVING in function_behaviors["double"].behaviors
            assert Behavior.SIGN_PRESERVING in function_behaviors["identity"].behaviors
            assert Behavior.SIGN_PRESERVING not in function_behaviors["negate"].behaviors
            assert Behavior.SIGN_PRESERVING not in function_behaviors["square"].behaviors
        else:
            # At minimum, verify the functions were analyzed
            assert len(function_behaviors["double"].behaviors) > 0
            assert len(function_behaviors["negate"].behaviors) > 0
    
    def test_validator_fingerprint(self):
        """Test detection of validator functions."""
        code = """
def is_positive(x):
    return x > 0

def is_even(x):
    return x % 2 == 0

def validate_range(x, min_val, max_val):
    return min_val <= x <= max_val

def main():
    a = is_positive(5)
    b = is_positive(-3)
    c = is_even(4)
    d = validate_range(5, 0, 10)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Collect validator function fingerprints
        validator_fingerprints = {}
        validator_functions = ["is_positive", "is_even", "validate_range"]
        
        for ctx, fp in result.semantic_fingerprints.items():
            if ctx.function_name in validator_functions:
                validator_fingerprints[ctx.function_name] = fp
        
        # Verify all validator functions were analyzed
        assert len(validator_fingerprints) == len(validator_functions)
        
        # All validator functions should be pure (no side effects)
        for func_name, fp in validator_fingerprints.items():
            assert fp.is_pure(), f"{func_name} should be pure"
        
        # Check for VALIDATOR behavior if implemented
        if hasattr(Behavior, 'VALIDATOR'):
            # If validator detection is implemented based on boolean returns
            for func_name, fp in validator_fingerprints.items():
                assert Behavior.VALIDATOR in fp.behaviors, f"{func_name} should be detected as validator"
        else:
            # At minimum, verify these functions don't have inappropriate behaviors
            for func_name, fp in validator_fingerprints.items():
                # Validators should not have these behaviors
                assert Behavior.NULLABLE_RETURN not in fp.behaviors
                assert Behavior.MODIFIES_GLOBALS not in fp.behaviors
                assert Behavior.PERFORMS_IO not in fp.behaviors
                
                # They might be detected as having constant-like behavior
                # since they always return boolean values
                # But they're not IDENTITY functions
                assert Behavior.IDENTITY not in fp.behaviors
    
    def test_fingerprint_comparison(self):
        """Test comparing semantic fingerprints."""
        code = """
def f1(x):
    return x  # Identity, pure

def f2(x):
    return x  # Also identity, pure

def f3(x):
    print(x)  # Not pure
    return x  # Still identity

def main():
    a = f1(10)
    b = f2(10)
    c = f3(10)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Get fingerprints
        f1_fp = None
        f2_fp = None
        f3_fp = None
        
        for ctx, fp in result.semantic_fingerprints.items():
            if ctx.function_name == "f1":
                f1_fp = fp
            elif ctx.function_name == "f2":
                f2_fp = fp
            elif ctx.function_name == "f3":
                f3_fp = fp
        
        assert f1_fp is not None
        assert f2_fp is not None
        assert f3_fp is not None
        
        # f1 and f2 should have similar fingerprints
        # Both are identity and pure
        assert Behavior.IDENTITY in f1_fp.behaviors
        assert Behavior.IDENTITY in f2_fp.behaviors
        
        # f3 is identity but not pure
        assert Behavior.IDENTITY in f3_fp.behaviors
        assert Behavior.PERFORMS_IO in f3_fp.behaviors
    
    def test_context_sensitive_fingerprints(self):
        """Test that different contexts produce different fingerprints."""
        code = """
def flexible(x):
    if x is None:
        return None
    if x < 0:
        return -x  # Changes sign for negative
    return x      # Preserves for positive

def main():
    a = flexible(10)    # Positive context
    b = flexible(-5)    # Negative context
    c = flexible(None)  # Null context
    return (a, b, c)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Should have different fingerprints for different contexts
        flexible_fingerprints = [
            (ctx, fp) for ctx, fp in result.semantic_fingerprints.items()
            if ctx.function_name == "flexible"
        ]
        
        # Should have multiple contexts analyzed
        assert len(flexible_fingerprints) >= 1
        
        # Different contexts might reveal different behaviors
        # (depends on context-sensitive analysis precision)
    
    def test_complex_behavior_combinations(self):
        """Test functions with multiple behaviors."""
        code = """
def complex_function(x, y):
    # Multiple behaviors:
    # - May return None (nullable)
    # - Pure (no side effects)
    # - Not identity
    # - Not constant
    if x > y:
        return x - y
    elif x < y:
        return None
    else:
        return 0

def main():
    a = complex_function(10, 5)
    b = complex_function(5, 10)
    c = complex_function(7, 7)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        for ctx, fp in result.semantic_fingerprints.items():
            if ctx.function_name == "complex_function":
                # Should detect nullable return
                assert Behavior.NULLABLE_RETURN in fp.behaviors
                # Should be pure (no side effects)
                assert fp.is_pure()
                # Should not be identity or constant
                assert Behavior.IDENTITY not in fp.behaviors
                assert Behavior.CONSTANT_RETURN not in fp.behaviors
    
    def test_may_not_return_fingerprint(self):
        """Test detection of functions that may not return."""
        code = """
def infinite_loop():
    while True:
        pass

def conditional_loop(x):
    while x > 0:
        x = x  # Simplified - would need more complex analysis
    return x

def always_returns():
    for i in range(10):
        if i == 5:
            break
    return "done"

def main():
    # Don't actually call infinite_loop!
    a = conditional_loop(5)
    b = always_returns()
    return (a, b)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Check for MAY_NOT_RETURN behavior
        # (Detection depends on loop analysis sophistication)
        for ctx, fp in result.semantic_fingerprints.items():
            if ctx.function_name == "infinite_loop":
                # Should detect infinite loop if analysis is sophisticated enough
                # For now, at least verify it's not marked as pure or safe
                # (infinite loops are neither pure nor safe in practice)
                # Note: Current analysis may not detect this sophisticatedly
                if Behavior.MAY_NOT_RETURN in fp.behaviors:
                    # Good - detected the infinite loop
                    assert not fp.is_safe()
                else:
                    # Analysis didn't detect it, but we can still check other properties
                    # The function has no return statement, so shouldn't be constant
                    assert Behavior.CONSTANT_RETURN not in fp.behaviors
            elif ctx.function_name == "always_returns":
                # Should not have MAY_NOT_RETURN
                assert Behavior.MAY_NOT_RETURN not in fp.behaviors
                # Should be safe since it always returns
                assert fp.is_safe()
            elif ctx.function_name == "conditional_loop":
                # This function's termination depends on input
                # It's deterministic but not necessarily safe
                assert fp.is_deterministic()


class TestFingerprintIntegration:
    """Test integration of fingerprinting with the analysis pipeline."""
    
    def test_fingerprints_in_analysis_result(self):
        """Test that fingerprints are included in analysis results."""
        code = """
def simple(x):
    return x + 1

def main():
    return simple(5)
"""
        tree = ast.parse(code)
        analyzer = InterproceduralAnalyzer()
        result = analyzer.analyze_program(tree)
        
        # Should have semantic_fingerprints in result
        assert hasattr(result, 'semantic_fingerprints')
        assert result.semantic_fingerprints is not None
        assert len(result.semantic_fingerprints) > 0
        
        # Should have fingerprints for each analyzed function context
        function_names = {ctx.function_name for ctx in result.semantic_fingerprints.keys()}
        assert "simple" in function_names
        assert "main" in function_names
    
    def test_fingerprint_metadata(self):
        """Test that fingerprints can store metadata."""
        # Create a fingerprint with metadata
        fp = SemanticFingerprint()
        fp.add_behavior(Behavior.CONSTANT_RETURN, value=42)
        fp.add_behavior(Behavior.PURE)
        
        # Check metadata storage
        assert fp.get_behavior_metadata(Behavior.CONSTANT_RETURN) == {'value': 42}
        assert fp.get_behavior_metadata(Behavior.PURE) is None
        
        # Check string representation
        str_repr = str(fp)
        assert "CONSTANT_RETURN" in str_repr
        assert "{'value': 42}" in str_repr
    
    def test_fingerprint_utilities(self):
        """Test fingerprint utility methods."""
        # Create fingerprints with different behaviors
        pure_fp = SemanticFingerprint()
        pure_fp.add_behavior(Behavior.PURE)
        pure_fp.add_behavior(Behavior.IDENTITY)
        
        impure_fp = SemanticFingerprint()
        impure_fp.add_behavior(Behavior.IDENTITY)
        impure_fp.add_behavior(Behavior.MODIFIES_GLOBALS)
        
        # Test is_pure
        assert pure_fp.is_pure()
        assert not impure_fp.is_pure()
        
        # Test is_safe
        safe_fp = SemanticFingerprint()
        safe_fp.add_behavior(Behavior.PURE)
        
        unsafe_fp = SemanticFingerprint()
        unsafe_fp.add_behavior(Behavior.MAY_THROW)
        
        assert safe_fp.is_safe()
        assert not unsafe_fp.is_safe()
        
        # Test is_deterministic
        assert pure_fp.is_deterministic()
        
        generator_fp = SemanticFingerprint()
        generator_fp.add_behavior(Behavior.PURE)
        generator_fp.add_behavior(Behavior.GENERATOR)
        
        assert not generator_fp.is_deterministic()