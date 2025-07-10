# RegionAI Test Suite

This directory contains the consolidated test suite for RegionAI, organized by functionality.

## Structure

```
tests/
├── test_analysis/       # Static analysis tests
│   └── test_abstract_domains.py
├── test_discovery/      # Transformation discovery tests
│   └── test_transformations.py
├── test_curriculum/     # Curriculum generation tests
│   └── test_all_curricula.py
├── test_integration/    # End-to-end integration tests
│   └── test_end_to_end.py
├── test_engine/         # Core engine tests
│   └── test_pathfinder.py
└── test_geometry/       # Geometry and region tests
    └── test_region.py
```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run specific category
pytest tests/test_analysis/

# Run with verbose output
pytest tests/ -v

# Run specific test
pytest tests/test_discovery/test_transformations.py::TestPrimitiveTransformations
```

## Test Consolidation

This test suite consolidates ~30+ individual test files into 6 organized test modules:
- **Before**: 4,565 lines across scattered test_*.py, demo_*.py, verify_*.py files
- **After**: 1,656 lines in organized pytest modules (~64% reduction)

Benefits:
- Consistent pytest structure
- Reusable fixtures and parametrization
- Clear organization by functionality
- Easier to maintain and extend

## Demo Script

Use the consolidated `demo.py` script to see RegionAI capabilities:

```bash
# Run all demos
python demo.py all

# Run specific demo
python demo.py discovery
python demo.py analysis
python demo.py optimization
python demo.py interprocedural
```

## Adding New Tests

When adding new tests:
1. Place in appropriate category directory
2. Use pytest conventions (test_* functions/classes)
3. Leverage existing fixtures when possible
4. Add parametrized tests for multiple scenarios
5. Document any special requirements