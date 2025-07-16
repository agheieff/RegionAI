#!/usr/bin/env python3
"""
Simple test runner for alias analysis
"""
import ast
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# Add the root directory to path for tier imports

from regionai.domains.code.analysis.context import AnalysisContext, AbstractLocation, LocationType
from regionai.domains.code.analysis.alias_analysis import (
    analyze_alias_assignment, analyze_mutation_effects,
    merge_points_to_maps
)


def test_simple_aliasing():
    """Test basic p = q aliasing."""
    print("Testing simple aliasing (p = q)...")
    
    code = "p = q"
    tree = ast.parse(code)
    assign_node = tree.body[0]
    
    context = AnalysisContext()
    
    # Set up q to point to some location
    q_loc = AbstractLocation.stack_var("q_var")
    context.add_points_to("q", q_loc)
    print(f"  Initial: q -> {q_loc}")
    
    # Analyze p = q
    analyze_alias_assignment(assign_node, context)
    
    # Check results
    p_pts = context.get_points_to("p")
    print(f"  After p=q: p -> {p_pts}")
    
    if q_loc in p_pts and context.may_alias("p", "q"):
        print("✅ Simple aliasing works correctly")
        return True
    else:
        print("❌ Simple aliasing failed")
        return False


def test_object_creation():
    """Test object creation creates heap locations."""
    print("\nTesting object creation...")
    
    test_cases = [
        ("p = {}", "dict"),
        ("q = []", "list"),
        ("r = set()", "object")  # Generic object for calls
    ]
    
    context = AnalysisContext()
    results = []
    
    for code, expected_type in test_cases:
        tree = ast.parse(code)
        assign_node = tree.body[0]
        var_name = assign_node.targets[0].id
        
        analyze_alias_assignment(assign_node, context)
        
        pts = context.get_points_to(var_name)
        if len(pts) == 1:
            loc = list(pts)[0]
            if loc.loc_type == LocationType.HEAP:
                print(f"  ✅ {code} creates heap location: {loc}")
                results.append(True)
            else:
                print(f"  ❌ {code} wrong location type: {loc.loc_type}")
                results.append(False)
        else:
            print(f"  ❌ {code} wrong number of locations: {len(pts)}")
            results.append(False)
    
    # Check no aliasing between different objects
    if not context.may_alias("p", "q"):
        print("  ✅ Different objects don't alias")
        results.append(True)
    else:
        print("  ❌ Different objects incorrectly alias")
        results.append(False)
    
    return all(results)


def test_mutation_detection():
    """Test detecting mutations that affect aliases."""
    print("\nTesting mutation detection...")
    
    code = """
obj = {}
p = obj
q = obj
r = {}
"""
    
    tree = ast.parse(code)
    context = AnalysisContext()
    
    # Set up aliases
    for stmt in tree.body:
        analyze_alias_assignment(stmt, context)
    
    # Verify aliases
    print("  Initial aliases:")
    print(f"    p aliases obj: {context.may_alias('p', 'obj')}")
    print(f"    q aliases obj: {context.may_alias('q', 'obj')}")
    print(f"    p aliases q: {context.may_alias('p', 'q')}")
    print(f"    r aliases obj: {context.may_alias('r', 'obj')}")
    
    # Simulate mutation: p.x = 5
    mutation = ast.parse("p.x = 5").body[0]
    affected = analyze_mutation_effects(mutation, context)
    
    print(f"\n  Mutation p.x = 5 affects: {affected}")
    
    if "p" in affected and "obj" in affected and "q" in affected and "r" not in affected:
        print("✅ Mutation detection works correctly")
        return True
    else:
        print("❌ Mutation detection failed")
        return False


def test_merge_points_to():
    """Test merging points-to maps at join points."""
    print("\nTesting points-to map merging...")
    
    # Create two paths with different points-to info
    loc1 = AbstractLocation.heap_object(1, "dict")
    loc2 = AbstractLocation.heap_object(2, "dict")
    loc3 = AbstractLocation.heap_object(3, "list")
    
    # Path 1: p -> loc1, q -> loc3
    map1 = {
        "p": {loc1},
        "q": {loc3}
    }
    
    # Path 2: p -> loc2, r -> loc3
    map2 = {
        "p": {loc2},
        "r": {loc3}
    }
    
    print("  Path 1:", {k: {str(l) for l in v} for k, v in map1.items()})
    print("  Path 2:", {k: {str(l) for l in v} for k, v in map2.items()})
    
    # Merge
    merged = merge_points_to_maps(map1, map2)
    
    print("\n  Merged:", {k: {str(l) for l in v} for k, v in merged.items()})
    
    # Check results
    if (len(merged["p"]) == 2 and  # p points to both loc1 and loc2
        loc1 in merged["p"] and loc2 in merged["p"] and
        len(merged["q"]) == 1 and  # q only from path 1
        len(merged["r"]) == 1):     # r only from path 2
        print("✅ Points-to merging works correctly")
        return True
    else:
        print("❌ Points-to merging failed")
        return False


def test_alias_with_attributes():
    """Test aliasing with attribute access."""
    print("\nTesting attribute access aliasing...")
    
    code = """
obj = {}
p = obj.field
"""
    tree = ast.parse(code)
    context = AnalysisContext()
    
    # First: obj = {}
    analyze_alias_assignment(tree.body[0], context)
    obj_pts = context.get_points_to("obj")
    print(f"  obj -> {obj_pts}")
    
    # Second: p = obj.field
    analyze_alias_assignment(tree.body[1], context)
    p_pts = context.get_points_to("p")
    print(f"  p = obj.field -> {p_pts}")
    
    if len(p_pts) == 1:
        field_loc = list(p_pts)[0]
        if ".field" in str(field_loc):
            print("✅ Attribute access creates field location")
            return True
    
    print("❌ Attribute access failed")
    return False


def main():
    """Run all alias analysis tests."""
    print("=== Alias Analysis Tests ===\n")
    
    results = []
    results.append(("Simple aliasing", test_simple_aliasing()))
    results.append(("Object creation", test_object_creation()))
    results.append(("Mutation detection", test_mutation_detection()))
    results.append(("Points-to merging", test_merge_points_to()))
    results.append(("Attribute aliasing", test_alias_with_attributes()))
    
    print("\n=== Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 Alias analysis is working correctly!")
        print("\nKey features implemented:")
        print("- Points-to analysis for tracking memory locations")
        print("- Alias detection (may-alias queries)")
        print("- Mutation effect analysis")
        print("- Path-sensitive alias tracking")
        print("- Integration with fixpoint analysis")
    else:
        print("\n⚠️ Some alias analysis tests failed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)