# RegionAI Scripts

This directory contains utility scripts for the RegionAI project.

## Scripts

### project_stats.py
A comprehensive statistics script that analyzes the RegionAI codebase and provides:
- Semantic dimensions (Behaviors) count
- Transformation primitives breakdown
- Available curricula
- Lines of code and code structure metrics
- Test suite statistics
- Module structure overview
- Configuration parameters count

**Usage:**
```bash
poetry run python scripts/project_stats.py
```

## Legacy Scripts

The following scripts have been replaced by better alternatives:
- `get_stats.sh` - Replaced by `project_stats.py` which provides more accurate statistics through proper module inspection rather than grep patterns.