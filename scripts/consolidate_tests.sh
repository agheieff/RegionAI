#!/bin/bash
# Script to archive old test files after consolidation

echo "=== RegionAI Test Consolidation Script ==="
echo "This script archives old test files that have been consolidated into the tests/ directory"
echo

# Create archive directory
ARCHIVE_DIR="scripts/archive_old_tests"
mkdir -p "$ARCHIVE_DIR"

# Move old test files
echo "Moving individual test files to archive..."

# Move test_*.py files from root
for file in test_*.py; do
    if [ -f "$file" ] && [ "$file" != "test_discovery.py" ]; then
        echo "  Moving $file"
        mv "$file" "$ARCHIVE_DIR/"
    fi
done

# Move scripts/test_*.py files
for file in scripts/test_*.py; do
    if [ -f "$file" ]; then
        echo "  Moving $file"
        mv "$file" "$ARCHIVE_DIR/"
    fi
done

# Move scripts/demo_*.py files
for file in scripts/demo_*.py; do
    if [ -f "$file" ]; then
        echo "  Moving $file"
        mv "$file" "$ARCHIVE_DIR/"
    fi
done

# Move scripts/verify_*.py files
for file in scripts/verify_*.py; do
    if [ -f "$file" ]; then
        echo "  Moving $file"
        mv "$file" "$ARCHIVE_DIR/"
    fi
done

echo
echo "=== Consolidation Summary ==="
echo "Old files archived to: $ARCHIVE_DIR"
echo "New test structure:"
echo "  - tests/           - Organized pytest modules"
echo "  - demo.py          - Consolidated demo script"
echo
echo "Line count reduction:"
echo "  Before: ~4,565 lines across 30+ files"
echo "  After:  ~1,656 lines in 7 organized files"
echo "  Reduction: ~64% (2,909 lines removed)"
echo
echo "To run tests: pytest tests/"
echo "To run demos: python demo.py all"