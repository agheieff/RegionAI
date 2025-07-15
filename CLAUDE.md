# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RegionAI is an ambitious AI system that discovers computational transformations and algorithms through a region-based neural architecture. It learns to compose primitive operations into complex transformations, ultimately aiming to understand and generate software at a fundamental level.

## Core Architecture

### Region-Based Discovery System
- **Concepts as Regions**: Transformations are represented as regions (volumes) in high-dimensional space, not points
- **Hierarchical Composition**: Complex operations built from primitive transformations
- **Evidence-Based Learning**: Bayesian updates with configurable evidence strengths
- **Key Files**:
  - `src/regionai/discovery/transformation.py` - Core transformation system
  - `src/regionai/discovery/discovery_engine.py` - Unified discovery orchestrator
  - `src/regionai/models/region_encoder.py` - Neural region embeddings

### Abstract Interpretation Framework
- **Sound Static Analysis**: Complete with domains for sign, nullability, ranges
- **Fixpoint Computation**: Loop analysis with widening for termination
- **Interprocedural Analysis**: Cross-function with context sensitivity
- **Key Files**:
  - `src/regionai/analysis/cfg.py` - Control flow graphs
  - `src/regionai/analysis/fixpoint.py` - Fixpoint analysis
  - `src/regionai/analysis/interprocedural.py` - Cross-function analysis

### Symbolic Language Engine
- **Grounded Symbols**: Language as interface, not foundation
- **Lazy Evaluation**: Defer computation until needed
- **Beam Search**: Manage ambiguity with bounded width
- **Key Files**:
  - `src/regionai/language/symbolic.py` - Core symbolic structures
  - `src/regionai/language/candidate_generator.py` - Disambiguation

## Development Commands

This is a Poetry project. All commands should be run with Poetry:

```bash
# Install dependencies
poetry install

# Install with visualization support
poetry install -E visualization

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

# Run demos
poetry run python demo.py all
poetry run python demo.py discovery
poetry run python demo.py language

# Analyze the codebase
poetry run python analyze_codebase.py
```

## High-Level Architecture

### Module Organization

1. **Discovery** (`src/regionai/discovery/`)
   - Transformation primitives and composition
   - Discovery strategies (sequential, conditional, iterative)
   - Abstract domains for program analysis
   - Evidence-based concept learning

2. **Analysis** (`src/regionai/analysis/`)
   - Control flow graph construction
   - Fixpoint analysis with widening
   - Interprocedural and context-sensitive analysis
   - Alias and pointer analysis

3. **Language** (`src/regionai/language/`)
   - Symbolic representation with lazy evaluation
   - Hierarchical parsing and candidate generation
   - Context resolution and reference tracking
   - Natural language to computation bridge

4. **Knowledge** (`src/regionai/knowledge/`)
   - World knowledge graph
   - Concept relationships and queries
   - Specialized services (replacing monolithic KnowledgeHub)
   - Evidence accumulation and Bayesian updates

5. **Reasoning** (`src/regionai/reasoning/`)
   - Multi-step planning and execution
   - Domain-specific heuristics (math, patterns, security)
   - Concept application and validation

### Key Design Patterns

1. **Dependency Injection**: Recent refactoring replaced global singletons
2. **Strategy Pattern**: Pluggable discovery strategies
3. **Circuit Breaker**: Failure management with recovery
4. **Memoization**: Scoped caching for performance
5. **Configuration-Driven**: Extensive use of config.py for all parameters

### Configuration System

The project uses a comprehensive configuration system (`src/regionai/config.py`) with profiles:
- `FAST`: Quick analysis for interactive use
- `BALANCED`: Default, good precision/performance trade-off
- `PRECISE`: Maximum precision for critical analysis
- `DEBUG`: Extended timeouts and verbose output

Key configurable aspects:
- Analysis precision and iteration limits
- Discovery parameters and evidence strengths
- Resource limits and timeouts
- Visualization settings

## Development Philosophy

1. **Discovery Over Implementation**: Focus on how the system learns, not just what it does
2. **Grounded Understanding**: Every concept has executable meaning
3. **Compositional**: Complex behaviors emerge from simple parts
4. **Verifiable**: Can prove properties about discovered programs
5. **Language as Interface**: Natural language bridges to computation, doesn't define it

## Current Development Focus

Based on recent commits:
- Enhanced interprocedural analysis with pointer analysis and heap modeling
- Replacing hardcoded values with configurable parameters
- Breaking up monolithic components into specialized services
- Memory management improvements and error recovery
- Phase XVII implementation (self-improvement capabilities)

## Important Notes

1. **Import Management**: Due to circular dependency concerns, some imports are done locally or use full paths
2. **Test Organization**: Tests mirror source structure in `tests/` directory
3. **Demo Scripts**: Use `demo.py` with different modes to see capabilities
4. **Progress Tracking**: Detailed progress in `progress_notes/` directory
5. **Strategic Vision**: Long-term plans in `docs/strategic/`

## Working with RegionAI

When implementing features:
1. Consider how it enables further discovery
2. Ensure proper configuration integration
3. Add comprehensive tests (unit and integration)
4. Document philosophical implications
5. Use dependency injection patterns
6. Follow the phase-based development approach

The project represents a fundamental shift in how AI systems learn to program - from pattern matching to true computational understanding through first principles.