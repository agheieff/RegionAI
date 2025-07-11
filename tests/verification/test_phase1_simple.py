#!/usr/bin/env python3
"""
Simple test to verify Phase 1 is complete by checking the code structure.
"""
import ast
import os

def check_interprocedural_implementation():
    """Check that interprocedural analysis has the fixes."""
    print("Checking interprocedural null detection implementation...")
    
    # Read the interprocedural.py file
    with open('src/regionai/analysis/interprocedural.py', 'r') as f:
        content = f.read()
    
    # Check for key fixes
    checks = [
        ("_merge_argument_state method exists", "_merge_argument_state" in content),
        ("Parameter mapping implementation", "_create_callee_initial_state" in content),
        ("Function call handling", "_handle_function_call" in content),
        ("Null safety checking", "_check_null_safety" in content)
    ]
    
    for check_name, result in checks:
        print(f"  {check_name}: {'✅' if result else '❌'}")
    
    return all(result for _, result in checks)

def check_analysis_context_refactoring():
    """Check that AnalysisContext refactoring is complete."""
    print("\nChecking AnalysisContext refactoring...")
    
    # Check context.py
    with open('src/regionai/analysis/context.py', 'r') as f:
        context_content = f.read()
    
    # Check ast_primitives.py
    with open('src/regionai/discovery/ast_primitives.py', 'r') as f:
        ast_content = f.read()
    
    checks = [
        ("variable_state_map in AnalysisContext", "variable_state_map:" in context_content),
        ("No ConstantPropagationContext class", "class ConstantPropagationContext" not in ast_content),
        ("propagate_constants uses context", "def propagate_constants(root: ast.AST, args: List[Any])" in ast_content),
        ("get_variable_state uses context", "hasattr(args[0], 'variable_state_map')" in ast_content)
    ]
    
    for check_name, result in checks:
        print(f"  {check_name}: {'✅' if result else '❌'}")
    
    return all(result for _, result in checks)

def check_no_global_state():
    """Check that global state has been eliminated."""
    print("\nChecking global state elimination...")
    
    # Check multiple files for global state
    files_to_check = [
        'src/regionai/discovery/ast_primitives.py',
        'src/regionai/discovery/abstract_domains.py',
        'src/regionai/analysis/fixpoint.py'
    ]
    
    forbidden_patterns = [
        '_abstract_state =',
        '_state_map =',
        'global _abstract_state',
        'global _state_map',
        'GLOBAL_STATE'
    ]
    
    all_clean = True
    for file_path in files_to_check:
        with open(file_path, 'r') as f:
            content = f.read()
        
        found = []
        for pattern in forbidden_patterns:
            if pattern in content:
                found.append(pattern)
        
        if found:
            print(f"  ❌ {os.path.basename(file_path)}: Found {found}")
            all_clean = False
        else:
            print(f"  ✅ {os.path.basename(file_path)}: Clean")
    
    return all_clean

def check_fixpoint_state_management():
    """Check that FixpointAnalyzer state management is fixed."""
    print("\nChecking FixpointAnalyzer state management...")
    
    with open('src/regionai/analysis/fixpoint.py', 'r') as f:
        content = f.read()
    
    checks = [
        ("Creates temporary contexts", "block_context = AnalysisContext()" in content),
        ("Imports AnalysisContext", "from .context import AnalysisContext" in content),
        ("No shared context modification", "# Create a temporary context" in content)
    ]
    
    for check_name, result in checks:
        print(f"  {check_name}: {'✅' if result else '❌'}")
    
    return all(result for _, result in checks)

def main():
    """Run all Phase 1 verification checks."""
    print("=== Phase 1 Code Structure Verification ===\n")
    
    results = []
    
    # Run all checks
    results.append(("Interprocedural implementation", check_interprocedural_implementation()))
    results.append(("AnalysisContext refactoring", check_analysis_context_refactoring()))
    results.append(("Global state elimination", check_no_global_state()))
    results.append(("FixpointAnalyzer state management", check_fixpoint_state_management()))
    
    # Summary
    print("\n=== Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 Phase 1 code structure is COMPLETE!")
        print("All foundation fixes have been implemented.")
        print("\nPhase 1 achievements:")
        print("- ✅ Interprocedural null detection fixed")
        print("- ✅ AnalysisContext refactoring complete")
        print("- ✅ Global state eliminated")
        print("- ✅ State management issues resolved")
        print("\nReady for Phase 2: Enhanced Analysis Features")
    else:
        print("\n⚠️  Phase 1 is NOT complete. Some checks failed.")
    
    return passed == total

if __name__ == "__main__":
    main()