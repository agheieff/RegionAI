# RegionAI

Region-based AI that learns algorithms through compositional discovery

## Overview

RegionAI is an experimental AI system that learns to discover algorithms by composing primitive operations. Unlike traditional machine learning that memorizes patterns, RegionAI:

- **Discovers algorithms**: Finds general solutions that work on any input
- **Composes primitives**: Builds complex algorithms from simple operations
- **Learns from failure**: Uses unsuccessful attempts to guide discovery
- **Searches intelligently**: Uses heuristics to efficiently explore algorithm space

### Key Achievements

- **True generalization**: Learns algorithms like SUM, REVERSE, SORT from examples
- **Compositional discovery**: Discovers multi-step algorithms (e.g., SORT→REVERSE for descending sort)
- **Intelligent search**: 71% search space reduction through pruning heuristics
- **Complex algorithms**: Learns filtering + aggregation patterns (e.g., "sum all elements > 5")

## Installation

```bash
# Clone the repository
git clone https://github.com/agheieff/RegionAI.git
cd RegionAI

# Install dependencies with Poetry
poetry install

# Activate the virtual environment (optional)
poetry shell
```

## Architecture

The project follows a clean, modular architecture:

- **data/**: Problem definitions and curriculum generation
- **discovery/**: Algorithm discovery engine with BFS search and heuristic pruning
- **engine/**: Reasoning engine that applies discovered algorithms
- **geometry/**: N-dimensional regions for concept representation
- **spaces/**: Concept space management
- **visualization/**: Interactive N-dimensional visualization

## Quick Start

### Running the Learning Loop

```bash
# Run with default curriculum (sum)
python scripts/run_learning_loop.py

# Run with specific curriculum
python scripts/run_learning_loop.py --curriculum reverse
python scripts/run_learning_loop.py --curriculum sort_desc
python scripts/run_learning_loop.py --curriculum sum_large

# See all available options
python scripts/run_learning_loop.py --help
```

### Available Curricula

- **reverse**: Learn to reverse lists
- **sum**: Learn to sum all elements
- **sort_desc**: Learn descending sort (discovers SORT_ASC→REVERSE)
- **sum_large**: Learn to sum elements > 5 (discovers FILTER_GT_5→SUM)

## Example: How It Works

When RegionAI encounters problems it can't solve:

1. **Attempt**: Tries to solve with existing knowledge
2. **Fail**: Records which problems couldn't be solved
3. **Discover**: Searches for algorithm that solves all failures
4. **Learn**: Adds discovered algorithm to knowledge base
5. **Succeed**: Solves previously impossible problems

### Example Discovery Session

```
--- Phase 1: Attempting to solve problems ---
    [FAIL] Problem 'sort_desc_1'
    [FAIL] Problem 'sort_desc_2'

--- Phase 2: Analyzing failures ---
    Searching for a sequence of operations...
    >>> Compositional Solution Found! Sequence: [SORT_ASCENDING -> REVERSE]

--- Phase 3: Re-attempting with new knowledge ---
    [SUCCESS] Problem 'sort_desc_1' solved
    [SUCCESS] Problem 'sort_desc_2' solved
```

## Core Concepts

### Primitive Operations
The system has 9 primitive operations that serve as building blocks:
- **Reordering**: REVERSE, SORT_ASCENDING
- **Arithmetic**: ADD_ONE, SUBTRACT_ONE
- **Selection**: GET_FIRST, GET_LAST
- **Aggregation**: SUM, COUNT
- **Filtering**: FILTER_GT_5

### Compositional Discovery
By combining primitives, the system discovers complex algorithms:
- SORT_DESCENDING = SORT_ASCENDING → REVERSE
- FIND_MAX = SORT_ASCENDING → GET_LAST
- SUM_LARGE = FILTER_GT_5 → SUM

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run ruff format .

# Lint code
poetry run ruff check .

# Run verification scripts
poetry run python scripts/verify_day27_28_search_optimization.py

# Run demos
poetry run python scripts/demo_day25_26_filter_algorithms.py
```

## Project Status

This is an active research project exploring compositional algorithm discovery. Current achievements include:

- ✅ Single-operation discovery
- ✅ Multi-step compositional discovery
- ✅ Intelligent search with pruning
- ✅ Complex filtering + aggregation patterns
- 🚧 Parameterized operations (in progress)
- 🚧 Natural language to algorithm translation
- 🚧 Recursive and conditional algorithms

## License

Copyright © 2024 Arkadiy Agheieff. All rights reserved.

This is proprietary software. Please see the [LICENSE](LICENSE) file for details.

For permission requests, please contact agheieff@pm.me. I am generally open to granting permissions for academic, research, and reasonable commercial use.