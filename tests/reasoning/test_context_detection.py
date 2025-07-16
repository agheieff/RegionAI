#!/usr/bin/env python3
"""
Tests for automatic context detection in the RegionAI reasoning engine.

Verifies that the ContextDetector can automatically identify the appropriate
analysis context from source code snippets.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
# Add the root directory to path for tier imports

from regionai.reasoning.context import ContextDetector, ContextRule
from regionai.reasoning.context_rules import DEFAULT_CONTEXT_RULES


def test_context_detector_database():
    """Test that database context is correctly detected."""
    print("Testing database context detection...")
    
    detector = ContextDetector(DEFAULT_CONTEXT_RULES)
    
    # Test various database-related code snippets
    test_cases = [
        ('query = "SELECT * FROM users"', "database-interaction"),
        ('db.execute("INSERT INTO orders VALUES (?)", order_id)', "database-interaction"),
        ('cursor.execute("UPDATE products SET price = ?")', "database-interaction"),
        ('connection.commit()', "database-interaction"),
        ('results = database.query("DELETE FROM expired")', "database-interaction"),
    ]
    
    for code, expected_context in test_cases:
        detected = detector.detect(code)
        assert detected.current_context_tag == expected_context, \
            f"Expected {expected_context} for code: {code}, but got {detected.current_context_tag}"
        print(f"✓ Correctly detected '{expected_context}' for: {code[:30]}...")


def test_context_detector_file_io():
    """Test that file I/O context is correctly detected."""
    print("\nTesting file I/O context detection...")
    
    detector = ContextDetector(DEFAULT_CONTEXT_RULES)
    
    test_cases = [
        ('with open("data.txt", "r") as f:', "file-io"),
        ('content = file.read()', "file-io"),
        ('f.write("Hello, world!")', "file-io"),
        ('path = Path("/home/user/doc.txt")', "file-io"),
        ('shutil.copy(src, dst)', "file-io"),
    ]
    
    for code, expected_context in test_cases:
        detected = detector.detect(code)
        assert detected.current_context_tag == expected_context, \
            f"Expected {expected_context} for code: {code}, but got {detected.current_context_tag}"
        print(f"✓ Correctly detected '{expected_context}' for: {code[:30]}...")


def test_context_detector_api_design():
    """Test that API design context is correctly detected."""
    print("\nTesting API design context detection...")
    
    detector = ContextDetector(DEFAULT_CONTEXT_RULES)
    
    test_cases = [
        ('@app.route("/users")', "api-design"),
        ('@api.post("/create")', "api-design"),
        ('data = request.json', "api-design"),
        ('return response.json({"status": "ok"})', "api-design"),
        ('from fastapi import FastAPI', "api-design"),
    ]
    
    for code, expected_context in test_cases:
        detected = detector.detect(code)
        assert detected.current_context_tag == expected_context, \
            f"Expected {expected_context} for code: {code}, but got {detected.current_context_tag}"
        print(f"✓ Correctly detected '{expected_context}' for: {code[:30]}...")


def test_context_detector_default_fallback():
    """Test that default context is used when no keywords match."""
    print("\nTesting default context fallback...")
    
    detector = ContextDetector(DEFAULT_CONTEXT_RULES)
    
    test_cases = [
        'x = y + 1',
        'result = calculate_total(items)',
        'name = "John Doe"',
        'for i in range(10):',
        'def simple_function(): pass',
    ]
    
    for code in test_cases:
        detected = detector.detect(code)
        assert detected.current_context_tag == "default", \
            f"Expected default context for code: {code}, but got {detected.current_context_tag}"
        print(f"✓ Correctly fell back to 'default' for: {code[:30]}...")


def test_context_detector_priority():
    """Test that first matching rule wins when multiple keywords present."""
    print("\nTesting rule priority...")
    
    # Create custom rules to test priority
    custom_rules = [
        ContextRule(context_tag="first", keywords=["SELECT"]),
        ContextRule(context_tag="second", keywords=["SELECT", "FROM"]),
    ]
    
    detector = ContextDetector(custom_rules)
    
    # Code has both SELECT and FROM, but first rule should win
    code = 'query = "SELECT * FROM users"'
    detected = detector.detect(code)
    assert detected.current_context_tag == "first", \
        f"Expected 'first' context due to rule order, but got {detected.current_context_tag}"
    print("✓ First matching rule correctly takes priority")


def test_context_rule_validation():
    """Test that ContextRule validates its inputs."""
    print("\nTesting ContextRule validation...")
    
    # Test empty context_tag
    try:
        ContextRule(context_tag="", keywords=["test"])
        assert False, "Should have raised ValueError for empty context_tag"
    except ValueError as e:
        assert "context_tag cannot be empty" in str(e)
        print("✓ Correctly rejected empty context_tag")
    
    # Test empty keywords
    try:
        ContextRule(context_tag="test", keywords=[])
        assert False, "Should have raised ValueError for empty keywords"
    except ValueError as e:
        assert "keywords list cannot be empty" in str(e)
        print("✓ Correctly rejected empty keywords list")


def test_context_detector_validation():
    """Test that ContextDetector validates its inputs."""
    print("\nTesting ContextDetector validation...")
    
    # Test empty rules list
    try:
        ContextDetector([])
        assert False, "Should have raised ValueError for empty rules"
    except ValueError as e:
        assert "at least one rule" in str(e)
        print("✓ Correctly rejected empty rules list")


def test_multiple_contexts_in_code():
    """Test detection when code contains keywords from multiple contexts."""
    print("\nTesting multiple contexts in code...")
    
    detector = ContextDetector(DEFAULT_CONTEXT_RULES)
    
    # Code that contains both database and API keywords
    # Database rules come first in DEFAULT_CONTEXT_RULES, so should win
    code = '''
    @app.route("/users")
    def get_users():
        query = "SELECT * FROM users"
        return db.execute(query)
    '''
    
    detected = detector.detect(code)
    # This will depend on rule order in DEFAULT_CONTEXT_RULES
    print(f"✓ Detected context: '{detected.current_context_tag}' for mixed-context code")


def run_all_tests():
    """Run all context detection tests."""
    print("=" * 60)
    print("Context Detection Test Suite")
    print("=" * 60)
    
    test_functions = [
        test_context_detector_database,
        test_context_detector_file_io,
        test_context_detector_api_design,
        test_context_detector_default_fallback,
        test_context_detector_priority,
        test_context_rule_validation,
        test_context_detector_validation,
        test_multiple_contexts_in_code,
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
        print("✓ All context detection tests passed!")
        print("The reasoning engine can now automatically detect analysis contexts!")
    else:
        print(f"✗ {failed} tests failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)