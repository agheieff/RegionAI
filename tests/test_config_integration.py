#!/usr/bin/env python3
"""
Test suite to verify the centralized configuration system.
"""
import sys
import os
import ast

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from regionai.config import (
    RegionAIConfig, AnalysisProfile, DEFAULT_CONFIG,
    fast_analysis_config, precise_analysis_config, debug_analysis_config
)
from regionai.analysis.context import AnalysisContext
from regionai.analysis.fixpoint import analyze_with_fixpoint
from regionai.pipeline.api import analyze_code, find_pure_functions, build_knowledge_graph


def test_config_creation():
    """Test creating configuration objects."""
    print("Testing configuration creation...")
    
    # Test default config
    config = RegionAIConfig()
    assert config.widening_threshold == 3
    assert config.max_fixpoint_iterations == 100
    assert config.cache_summaries == True
    
    # Test custom config
    custom_config = RegionAIConfig(
        widening_threshold=5,
        max_fixpoint_iterations=200,
        verbose_output=True
    )
    assert custom_config.widening_threshold == 5
    assert custom_config.max_fixpoint_iterations == 200
    assert custom_config.verbose_output == True
    
    print("✓ Configuration creation works correctly")


def test_config_profiles():
    """Test predefined configuration profiles."""
    print("\nTesting configuration profiles...")
    
    # Fast profile
    fast_config = RegionAIConfig.from_profile(AnalysisProfile.FAST)
    assert fast_config.widening_threshold == 1
    assert fast_config.max_fixpoint_iterations == 50
    assert fast_config.context_sensitivity_level == 0
    
    # Precise profile
    precise_config = RegionAIConfig.from_profile(AnalysisProfile.PRECISE)
    assert precise_config.widening_threshold == 10
    assert precise_config.max_fixpoint_iterations == 500
    assert precise_config.enable_path_sensitivity == True
    
    # Debug profile
    debug_config = RegionAIConfig.from_profile(AnalysisProfile.DEBUG)
    assert debug_config.verbose_output == True
    assert debug_config.trace_fixpoint_iterations == True
    assert debug_config.log_level == "DEBUG"
    
    # Convenience functions
    assert fast_analysis_config().widening_threshold == 1
    assert precise_analysis_config().widening_threshold == 10
    assert debug_analysis_config().verbose_output == True
    
    print("✓ Configuration profiles work correctly")


def test_config_overrides():
    """Test configuration override functionality."""
    print("\nTesting configuration overrides...")
    
    base_config = RegionAIConfig()
    
    # Test with_overrides
    overridden = base_config.with_overrides(
        widening_threshold=7,
        custom_param="test_value"
    )
    
    assert overridden.widening_threshold == 7
    assert base_config.widening_threshold == 3  # Original unchanged
    assert overridden.get_param("custom_param") == "test_value"
    assert overridden.get_param("nonexistent", "default") == "default"
    
    print("✓ Configuration overrides work correctly")


def test_config_validation():
    """Test configuration validation."""
    print("\nTesting configuration validation...")
    
    # Valid config
    valid_config = RegionAIConfig()
    issues = valid_config.validate()
    assert len(issues) == 0
    
    # Invalid config
    invalid_config = RegionAIConfig(
        widening_threshold=-1,
        max_fixpoint_iterations=0,
        context_sensitivity_level=5,
        discovery_exploration_rate=1.5
    )
    issues = invalid_config.validate()
    assert len(issues) >= 4
    assert any("widening_threshold" in issue for issue in issues)
    assert any("max_fixpoint_iterations" in issue for issue in issues)
    
    print("✓ Configuration validation works correctly")


def test_context_with_config():
    """Test AnalysisContext using centralized config."""
    print("\nTesting AnalysisContext with config...")
    
    # Create context with custom config
    custom_config = RegionAIConfig(widening_threshold=5)
    context = AnalysisContext(config=custom_config)
    
    assert context.config.widening_threshold == 5
    
    # Create context with default config
    default_context = AnalysisContext()
    assert default_context.config.widening_threshold == DEFAULT_CONFIG.widening_threshold
    
    print("✓ AnalysisContext config integration works correctly")


def test_fixpoint_with_config():
    """Test fixpoint analysis respecting config."""
    print("\nTesting fixpoint analysis with config...")
    
    code = """
i = 0
while i < 10:
    i = i + 1
"""
    tree = ast.parse(code)
    
    # Test with fast config (low widening threshold)
    fast_config = fast_analysis_config()
    fast_context = AnalysisContext(config=fast_config)
    result = analyze_with_fixpoint(tree, context=fast_context)
    
    assert 'final_state' in result
    assert result['context'].config.widening_threshold == 1
    
    # Test with precise config (high widening threshold)
    precise_config = precise_analysis_config()
    precise_context = AnalysisContext(config=precise_config)
    result = analyze_with_fixpoint(tree, context=precise_context)
    
    assert result['context'].config.widening_threshold == 10
    
    print("✓ Fixpoint analysis respects configuration")


def test_api_with_config():
    """Test API functions accepting config parameter."""
    print("\nTesting API functions with config...")
    
    code = '''
def pure_func(x):
    """A pure function."""
    return x * 2

def side_effect_func():
    """Function with side effects."""
    print("Hello")
    return None
'''
    
    # Test analyze_code with config
    config = RegionAIConfig(max_errors_per_function=10)
    result = analyze_code(code, config=config)
    assert result is not None
    
    # Test find_pure_functions with config
    pure_db = find_pure_functions(code, config=config)
    assert pure_db is not None
    
    # Test build_knowledge_graph with config
    kg = build_knowledge_graph(code, config=config)
    assert kg is not None
    
    print("✓ API functions accept configuration correctly")


def test_config_in_analysis_pipeline():
    """Test configuration flowing through analysis pipeline."""
    print("\nTesting config in analysis pipeline...")
    
    code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
    
    # Create config with specific settings
    config = RegionAIConfig(
        max_function_analysis_depth=3,
        cache_summaries=False,
        report_potential_errors=True
    )
    
    # Run analysis
    result = analyze_code(code, config=config)
    
    # The analysis should complete without errors
    assert result is not None
    assert hasattr(result, 'semantic_db')
    
    print("✓ Configuration flows through pipeline correctly")


def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("Configuration Integration Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_config_creation,
        test_config_profiles,
        test_config_overrides,
        test_config_validation,
        test_context_with_config,
        test_fixpoint_with_config,
        test_api_with_config,
        test_config_in_analysis_pipeline
    ]
    
    failed = 0
    for test_func in test_functions:
        try:
            test_func()
        except Exception as e:
            print(f"\n✗ {test_func.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)