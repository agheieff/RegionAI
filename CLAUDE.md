# CLAUDE.md - RegionAI Project Guide

## Project Overview

RegionAI is an ambitious AI system that discovers computational transformations and algorithms through a region-based neural architecture. It learns to compose primitive operations into complex transformations, ultimately aiming to understand and generate software at a fundamental level.

## Core Architecture

### 1. Region-Based Discovery Engine
- **Concept**: Transformations are embedded as regions in high-dimensional space
- **Discovery**: New transformations found by exploring/combining regions
- **Key Files**:
  - `src/regionai/discovery/transformation.py` - Core transformation system
  - `src/regionai/discovery/discovery.py` - Discovery engine
  - `src/regionai/models/region_encoder.py` - Neural region embeddings

### 2. Transformation Hierarchy
- **Primitives**: ADD, MULTIPLY, FILTER, MAP, etc.
- **Compositions**: Combine primitives into complex operations
- **Discovered**: System finds new transformations through curriculum
- **Key Primitives**:
  - Data: MAP_GET, FILTER_BY_VALUE, UPDATE_FIELD
  - Control: IF/ELSE (ConditionalTransformation), FOR_EACH
  - AST: GET_NODE_TYPE, REPLACE_NODE, EVALUATE_NODE

### 3. Abstract Interpretation Engine
- **Sign Domain**: Track positive/negative/zero properties
- **Nullability Domain**: Detect null pointer exceptions
- **Range Domain**: Prevent array bounds violations
- **Fixpoint Analysis**: Sound loop handling with widening

## Development Progress

### Phase 1: Foundation (Days 1-29) ✓
- Basic transformations and compositions
- Neural architecture with attention mechanisms
- Curriculum-driven discovery
- Region-based embeddings

### Phase 1 Extensions (Days 30-33) ✓
- Parameterized primitives
- Structured data (dictionaries/objects)
- Conditional control flow
- Iterative patterns (FOR_EACH)

### Phase 2: Code as Data (Days 34-37) ✓
- AST transformations
- Algebraic optimizations (x+0→x, x*1→x)
- Constant folding and dead code elimination
- Data flow analysis and constant propagation

### Current: Abstract Interpretation ✓
- Fixpoint analysis with CFG construction
- Abstract domains (Sign, Nullability, Range)
- Sound loop analysis with widening
- Industrial-strength bug detection

## Key Technical Concepts

### 1. Curriculum-Driven Discovery
Problems are carefully designed to guide discovery:
```python
# Example: Discover FILTER → MAP → SUM pattern
problems = [
    Problem(input=[{v:1},{v:2},{v:3}], output=6),
    Problem(input=[{v:4},{v:5}], output=9)
]
```

### 2. Region Composition
New regions created by combining existing ones:
```python
# FILTER region + MAP region → FILTER_MAP region
filter_map = compose_regions(filter_region, map_region)
```

### 3. Abstract State Tracking
Track properties through program execution:
```python
# x = 5 → x is POSITIVE
# y = -x → y is NEGATIVE
# z = x * y → z is NEGATIVE
```

### 4. Widening for Termination
Ensure analysis completes for any loop:
```python
# i: [0,1] → [0,2] → [0,3] → [0,+∞] (widened)
```

## Working with Gemini

### Collaboration Pattern
1. **Gemini provides high-level directives** with philosophical context
2. **Claude implements** with attention to technical detail
3. **Test and verify** each implementation works
4. **Report back** with results and insights
5. **Gemini evaluates** and provides next directive

### Communication Style
- Gemini writes detailed, philosophical directives
- Emphasizes the "why" behind each feature
- Often includes metaphors and conceptual frameworks
- Expects thorough implementation and testing

### Example Interaction Flow
```
Gemini: "Implement constant propagation... [philosophical context]"
Claude: [Implements feature, tests it, documents results]
Claude: "Successfully implemented with these key achievements..."
Gemini: "Excellent. Next implement abstract domains..."
```

## Essential Commands

### Testing

This is a Poetry project. Use Poetry to manage dependencies and run tests:

```bash
# Install dependencies
poetry install

# Run specific tests with Poetry
poetry run pytest tests/knowledge/test_linker.py
poetry run pytest tests/test_phase2_path_sensitivity.py

# Run all tests
poetry run pytest

# Run with specific test patterns
poetry run pytest -k "test_concept_variations"

# Run with verbose output
poetry run pytest -xvs

# For legacy test files (if they exist)
poetry run python test_discovery.py
```

### Git Workflow
```bash
# Always commit with detailed messages
git add -A
git commit -m "feat: [description]

[Details about implementation]
[Impact and results]

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

## Project Structure

```
RegionAI/
├── src/regionai/
│   ├── discovery/          # Core discovery engine
│   │   ├── transformation.py
│   │   ├── ast_primitives.py
│   │   └── abstract_domains.py
│   ├── analysis/           # Static analysis
│   │   ├── cfg.py         # Control flow graphs
│   │   └── fixpoint.py    # Fixpoint computation
│   ├── data/              # Curricula
│   │   ├── problem.py
│   │   └── *_curriculum.py
│   └── models/            # Neural components
├── tests/                 # Test files
├── progress_notes/        # Detailed progress documentation
└── docs/strategic/        # Long-term vision documents
```

## Current Capabilities

### What RegionAI Can Do
1. **Discover Transformations**: Learn new operations from examples
2. **Compose Operations**: Build complex from simple
3. **Transform Code**: AST-level program manipulation
4. **Prove Properties**: Verify programs never crash
5. **Detect Bugs**: Find null pointers, bounds violations
6. **Optimize Code**: Constant folding, dead code elimination

### What's Next
1. **Path-Sensitive Analysis**: Track different execution paths
2. **Interprocedural Analysis**: Analyze across functions
3. **Natural Language Bridge**: Map language to operations
4. **Full Code Generation**: From specs to implementation

## Important Implementation Notes

### 1. Global State in Abstract Domains
The abstract domain implementations use global state (_abstract_state) for simplicity. This should be refactored for production use.

### 2. Widening Thresholds
Current threshold is 3 iterations before widening. This balances precision with termination guarantees.

### 3. Path Insensitivity
Current implementation merges all paths at join points. Path-sensitive analysis would increase precision but complexity.

### 4. Import Structure
Due to circular dependency concerns, some imports are done locally or use full paths.

## Debugging Tips

### Common Issues
1. **Import errors**: Check sys.path and relative imports
2. **State not tracked**: Ensure analyze functions are called
3. **Widening too aggressive**: Adjust threshold or widening logic
4. **Tests showing empty results**: Check global state initialization

### Useful Debugging
```python
# Check abstract state
print(_abstract_state.sign_state)
print(_abstract_state.nullability_state)

# Visualize CFG
visualize_cfg(cfg)

# Trace fixpoint iterations
print(f"Iteration {i}: {state}")
```

## Philosophy and Vision

RegionAI represents a fundamental shift in how AI systems learn to program:
- **Bottom-up Discovery**: Start with primitives, discover complexity
- **Grounded Understanding**: Every concept has executable meaning
- **Compositional**: Complex behaviors emerge from simple parts
- **Verifiable**: Can prove properties about discovered programs

The ultimate goal is an AI that doesn't just generate code, but truly understands computation at a deep level - from assembly to architecture.

## Quick Reference

### Key Classes
- `Transformation`: Executable operation with metadata
- `Problem`: Input/output example for learning
- `AnalysisState`: Abstract state during analysis
- `Range`: Interval for bounds checking
- `BasicBlock`: Node in control flow graph

### Key Functions
- `discover_transformations()`: Main discovery loop
- `analyze_with_fixpoint()`: Sound loop analysis
- `check_null_dereference()`: Detect null errors
- `check_array_bounds()`: Detect bounds errors
- `range_widen()`: Ensure analysis termination

## Final Notes

RegionAI is more than a code generator - it's an attempt to create AI that understands software engineering at a fundamental level. Every feature builds toward this goal, from the simplest primitive to the most complex analysis.

When working on RegionAI:
- Think about discovery, not just implementation
- Consider how each feature enables further learning
- Document insights and philosophical implications
- Test thoroughly - this is foundational work

The journey from ADD to abstract interpretation shows what's possible when AI learns from first principles. The next steps toward natural language and full program synthesis build on this solid foundation.