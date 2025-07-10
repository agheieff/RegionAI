#!/bin/bash
# Archive redundant verification scripts

echo "=== Archiving Redundant Verification Scripts ==="
echo "These have been replaced by proper unit tests in tests/test_legacy_features.py"
echo

# Create archive directory
ARCHIVE_DIR="scripts/archive_verify"
mkdir -p "$ARCHIVE_DIR"

# Files to archive
VERIFY_FILES=(
    "verify_day10_complete.py"
    "verify_day11_12_complete.py"
    "verify_day13_complete.py"
    "verify_day14_complete.py"
    "verify_day15_16_complete.py"
    "verify_day19_complete.py"
    "verify_day20_complete.py"
    "verify_day21_complete.py"
    "verify_day22_generalization.py"
    "verify_day23_compositional.py"
    "verify_day25_26_deep_composition.py"
    "verify_day27_28_search_optimization.py"
    "verify_interactive.py"
)

# Move files
echo "Moving verification scripts to archive..."
moved=0
for file in "${VERIFY_FILES[@]}"; do
    if [ -f "scripts/$file" ]; then
        echo "  Archiving: $file"
        mv "scripts/$file" "$ARCHIVE_DIR/"
        ((moved++))
    fi
done

echo
echo "=== Summary ==="
echo "Moved $moved verification scripts to: $ARCHIVE_DIR/"
echo "Replaced by: tests/test_legacy_features.py"
echo "Migration guide: VERIFY_SCRIPTS_MIGRATION.md"
echo
echo "Line reduction: ~1,000+ lines"
echo "  Before: 1,607 lines across 13 verify scripts"
echo "  After:  ~300 lines in consolidated test file"
echo "  Reduction: ~81%"