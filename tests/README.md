# RegionAI Test Suite

This directory contains the comprehensive test suite for RegionAI, organized by functionality across the new 6-brain cognitive architecture.

## Structure

```
tests/
├── test_analysis/          # Static analysis and CFG tests
│   ├── test_abstract_domains.py
│   ├── test_call_graph.py
│   ├── test_context_sensitive_analysis.py
│   ├── test_function_summary.py
│   └── test_semantic_fingerprint.py
├── test_discovery/         # Transformation discovery tests
│   └── test_transformations.py
├── knowledge/              # Knowledge system tests
│   ├── test_action_discoverer.py
│   ├── test_bayesian_updater.py
│   ├── test_discovery.py
│   ├── test_graph.py
│   ├── test_linker.py
│   ├── test_reasoning_graph.py
│   └── test_sequential_analysis.py
├── reasoning/              # Reasoning engine tests
│   ├── heuristics/
│   │   └── test_math_foundations.py
│   ├── test_composed_execution.py
│   ├── test_context_detection.py
│   ├── test_contextual_reasoning.py
│   ├── test_engine.py
│   ├── test_feedback_loop.py
│   ├── test_planner_proof_integration.py
│   ├── test_proof_runner.py
│   ├── test_proof_trace.py
│   ├── test_tactic_executor.py
│   └── test_utility_updater_exponential.py
├── language/               # Language processing tests
│   ├── test_advanced_parsing.py
│   ├── test_caching_performance.py
│   ├── test_candidate_generator.py
│   ├── test_context_resolver.py
│   ├── test_grammar_extractor.py
│   ├── test_lean_ast.py
│   ├── test_lean_parser.py
│   ├── test_learning_mappings.py
│   ├── test_symbolic.py
│   └── test_symbolic_parser.py
├── analysis/               # Analysis context tests
│   └── test_analysis_context.py
├── domain/                 # Domain exception tests
│   └── test_exceptions.py
├── utils/                  # Utility tests
│   ├── test_component_loader.py
│   └── test_text_utils.py
├── verification/           # Verification and validation tests
│   ├── test_alias_analysis_simple.py
│   ├── test_improved_merging.py
│   ├── test_path_sensitivity_direct.py
│   ├── test_path_sensitivity_simple.py
│   ├── test_phase1_complete.py
│   └── test_state_merging.py
└── integration/            # Integration tests
    └── test_end_to_end.py
```

## Running Tests

### Basic Commands

```bash
# Run all tests
poetry run pytest

# Run specific module
poetry run pytest tests/knowledge/
poetry run pytest tests/reasoning/

# Run with verbose output
poetry run pytest -xvs

# Run specific test
poetry run pytest tests/knowledge/test_discovery.py::test_crud_pattern_discovery
```

### Test Commands in CLAUDE.md

All test commands should be run with Poetry:

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run specific test suites
poetry run pytest tests/test_analysis/
poetry run pytest tests/knowledge/
poetry run pytest tests/test_phase2_path_sensitivity.py

# Run tests with specific patterns
poetry run pytest -k "test_concept_variations"
poetry run pytest -k "test_null_safety"

# Run with verbose output and stop on first failure
poetry run pytest -xvs

# Run with coverage
poetry run pytest --cov=regionai
```

## Test Status (Current)

### Passing Test Suites
- **Knowledge Module**: 48 tests passing (action discovery, Bayesian updates, concept discovery, graph operations, knowledge linking, reasoning graph, sequential analysis)
- **Analysis Module**: 17 tests passing (analysis context, fixpoint analysis, null safety checking)
- **Discovery Module**: 14 tests passing (transformation discovery and composition)
- **Core Module**: 15 tests passing, 1 skipped (abstract domains)
- **Domain Module**: 13 tests passing (exception handling)
- **Utils Module**: 22 tests passing (component loading, text utilities)
- **Reasoning Module**: 12+ tests passing (math foundations, proof running, tactic execution)

### Known Issues
- **Circular Import**: 1 test in abstract domains skipped due to circular import
- **Heuristic Registry**: 2 reasoning tests fail due to pytest module resolution conflict
- **Mock Patching**: 2 util tests fail due to patching issues

### Total Test Files: 57

## Test Organization

The test suite has been updated to reflect the new 6-brain cognitive architecture:

1. **Bayesian Brain**: Tests in `knowledge/` for probabilistic reasoning
2. **Utility Brain**: Tests in `reasoning/` for decision-making heuristics  
3. **Logic Brain**: Tests in `test_analysis/` for formal verification
4. **Observer Brain**: Tests in `language/` for perception and parsing
5. **Temporal Brain**: Tests in `verification/` for time-based analysis
6. **Sensorimotor Brain**: Tests in `integration/` for action execution

## Recent Updates

After the codebase reorganization, import paths have been updated:
- `regionai.language` → `regionai.domains.language`
- `regionai.semantic` → `regionai.domains.code.semantic`
- `regionai.geometry` → `regionai.core`
- `regionai.discovery.abstract_domains` → `regionai.core.abstract_domains`

Most import errors have been resolved, and the majority of tests are now passing.

## Adding New Tests

When adding new tests:
1. Place in appropriate brain/module directory
2. Use pytest conventions (test_* functions/classes)
3. Follow the Poetry-based command structure
4. Update imports to use new module paths
5. Add parametrized tests for multiple scenarios
6. Document any special requirements or dependencies