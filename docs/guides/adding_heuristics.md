# Adding New Heuristics to RegionAI

With the enhanced heuristic registry, adding new heuristics to RegionAI is now simple and modular. The system automatically discovers all registered heuristics without requiring any modifications to the analyzer or other components.

## How to Add a New Heuristic

1. **Implement your heuristic** in one of the heuristic modules under `src/regionai/reasoning/heuristics/`:
   - `ast_heuristics.py` for AST-based heuristics
   - `pattern_heuristics.py` for pattern detection
   - `security_heuristics.py` for security checks
   - `quality_heuristics.py` for code quality
   - `math_foundations.py` for mathematical reasoning

```python
@heuristic_registry.register("your.heuristic.id",
                           description="Brief description of what this heuristic does",
                           applicability_conditions=("condition1", "condition2"),
                           expected_utility=0.85)
def your_heuristic_function(hub: KnowledgeHub, context: Dict[str, Any]) -> Any:
    """
    Detailed documentation about your heuristic.
    
    Args:
        hub: The KnowledgeHub containing both world and reasoning graphs
        context: Additional context including:
            - code: The source code to analyze
            - function_name: Name of the function being analyzed
            - function_artifact: The FunctionArtifact being analyzed
    
    Returns:
        - FixSuggestion for automatically fixable issues
        - Discovery for issues that need manual review
        - bool for knowledge graph building heuristics
        - None if no issues found
    """
    # Your implementation here
    pass
```

2. **That's it!** The heuristic will be automatically:
   - Registered in the HeuristicRegistry
   - Discovered by analyze_codebase.py
   - Added to the ReasoningKnowledgeGraph
   - Applied to all functions during analysis

## Heuristic Types

### Knowledge Discovery Heuristics
These discover relationships and concepts in the code:
- Return `bool` indicating if discoveries were made
- Examples: `ast.method_call_implies_performs`, `pattern.co_occurrence_implies_related`

### Code Quality Heuristics
These identify quality issues:
- Return `Discovery` objects for issues found
- Examples: `COMPLEXITY_ANALYZER`, documentation quality checks

### Security Heuristics
These identify security vulnerabilities:
- Return `FixSuggestion` for automatically fixable issues
- Examples: `security.check_insecure_ssl_config`

## Registration Parameters

- **heuristic_id**: Unique identifier for your heuristic (e.g., "security.sql_injection")
- **description**: Brief description shown in the analyzer output
- **applicability_conditions**: Tuple of tags describing when this heuristic applies
- **expected_utility**: Float 0-1 indicating how useful this heuristic typically is

## Best Practices

1. **Naming Convention**: Use dot notation for IDs (e.g., "category.specific_check")
2. **Return Types**: Be consistent with return types based on heuristic purpose
3. **Error Handling**: Handle parse errors gracefully
4. **Performance**: Keep heuristics fast as they run on every function
5. **Documentation**: Include clear docstrings explaining the heuristic's purpose

## Example: Adding a New Security Heuristic

```python
@heuristic_registry.register("security.hardcoded_credentials",
                           description="Detect hardcoded passwords and API keys",
                           applicability_conditions=("security", "credentials"),
                           expected_utility=0.98)
def check_hardcoded_credentials(hub: KnowledgeHub, context: Dict[str, Any]) -> Optional[FixSuggestion]:
    """
    Detect hardcoded credentials in source code.
    """
    code = context.get('code', '')
    function_artifact = context.get('function_artifact')
    
    # Check for common patterns
    patterns = [
        r'password\s*=\s*["\'].*["\']',
        r'api_key\s*=\s*["\'].*["\']',
        r'secret\s*=\s*["\'].*["\']'
    ]
    
    import re
    for pattern in patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return FixSuggestion(
                vulnerability_id="HARDCODED_CREDENTIALS",
                description="Hardcoded credentials detected",
                target_artifact=function_artifact,
                context_data={"pattern": pattern}
            )
    
    return None
```

After adding this heuristic, it will automatically be included in all future analyses without any other code changes needed!