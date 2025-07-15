# Performance Optimizations in RegionAI

## Single-Pass AST Parsing

One of the key performance optimizations implemented is single-pass AST parsing. This eliminates redundant parsing of the same source code multiple times.

### The Problem

Previously, the analysis pipeline would parse the source code into an AST multiple times:
- Once in `analyze_code()` for semantic analysis
- Once in `build_knowledge_graph()` for documentation extraction
- Again in `build_knowledge_graph()` for extracting function sources
- Multiple times in various other components

This redundant parsing was inefficient, especially for large codebases.

### The Solution

We now parse the AST **once** at the beginning of the analysis and pass the pre-parsed tree to all components:

```python
# In analyze_codebase.py
# Step 1.5: Parse AST once
tree = ast.parse(code)

# Step 2: Build knowledge graph with pre-parsed AST
hub = build_knowledge_graph_with_progress(code, tree)
```

### Implementation Details

1. **New API Functions**: Added `analyze_code_with_tree()` and `build_knowledge_graph_with_tree()` that accept a pre-parsed AST instead of raw code.

2. **Backward Compatibility**: The original functions (`analyze_code()`, `build_knowledge_graph()`) still exist and parse internally, then delegate to the new functions.

3. **Component Updates**: All components that need the AST (documentation extractors, semantic analyzers, etc.) now receive the pre-parsed tree.

### Benefits

- **Performance**: Eliminates redundant parsing overhead
- **Consistency**: All components work with the exact same AST representation
- **Memory**: Reduces memory usage by sharing a single AST instance
- **Architecture**: Cleaner separation of parsing from analysis logic

### Note on Heuristics

Individual heuristics still parse function-level source code independently. This is necessary because:
- Heuristics work on isolated function bodies
- They receive serialized function source through multiprocessing
- The overhead is minimal since they parse small code snippets

This optimization focuses on eliminating the redundant parsing of the entire module/codebase, which provides the most significant performance improvement.

## Unified Action Discovery Parsing

Another optimization addresses redundant parsing in the action discovery module. Previously, `discover_actions` and `discover_action_sequences` would both parse the same function code independently.

### The Problem

The action discovery service had inconsistent abstractions:
- `discover_actions()` parsed the function code to find actions
- `discover_action_sequences()` called `discover_actions()` and parsed again to find sequences
- This caused the same code to be parsed multiple times

### The Solution

We introduced a unified discovery method that parses once and extracts both actions and sequences:

```python
# New unified method
def discover_all_from_function_ast(self, function_node: ast.FunctionDef) -> dict:
    """Parse once, extract everything."""
    actions = self._analyze_function_body(function_node)
    sequences = self._build_action_sequences(actions)
    return {'actions': actions, 'sequences': sequences}
```

### Implementation Details

1. **New Unified Method**: `discover_all_from_function_ast()` takes a pre-parsed AST node and returns both actions and sequences.

2. **Updated Coordinator**: The `ActionCoordinator` now parses once and uses the unified method for discovery.

3. **Backward Compatibility**: The original methods remain for compatibility but now delegate to the unified approach.

### Benefits

- **Efficiency**: Eliminates redundant parsing in action discovery
- **Consistency**: Both actions and sequences are discovered from the same AST traversal
- **Cleaner Architecture**: Single responsibility - one parsing step feeds all analysis

## Centralized Context Resolution

To prevent configuration drift, we centralized the logic for determining function contexts into a dedicated service.

### The Problem

The Planner had its own implementation of context determination logic that could drift from the context rules defined in `context_rules.py`. Having duplicate logic in multiple places is a recipe for bugs and inconsistencies.

### The Solution

We created a `ContextResolver` service that provides a single source of truth for context determination:

```python
class ContextResolver:
    def determine_function_context(self, artifact: FunctionArtifact, 
                                 wkg: WorldKnowledgeGraph) -> str:
        """Single source of truth for context determination."""
        # Centralized logic that considers both concepts and keywords
```

### Implementation Details

1. **Created ContextResolver**: A dedicated service in `context_resolver.py` that encapsulates all context determination logic.

2. **Refactored Planner**: Removed the private `_determine_function_context` method and now uses the injected `ContextResolver`.

3. **Enhanced Logic**: The resolver considers both concept-based matching and keyword rules from `DEFAULT_CONTEXT_RULES`.

### Benefits

- **Prevents Drift**: Single implementation ensures consistency across the system
- **Better Testing**: Context logic can be tested independently
- **Separation of Concerns**: Planner focuses on planning, not context determination
- **Extensibility**: Easy to add new context detection rules in one place