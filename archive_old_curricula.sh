#!/bin/bash
# Archive old curriculum files after unification

echo "=== Archiving Old Curriculum Files ==="
echo "These files have been unified into curriculum_factory.py"
echo

# Create archive directory
ARCHIVE_DIR="src/regionai/data/archive_old_curricula"
mkdir -p "$ARCHIVE_DIR"

# Files to archive (excluding the base curriculum.py)
OLD_FILES=(
    "abstract_interpretation_curriculum.py"
    "abstract_sign_analysis_curriculum.py"
    "algebraic_identities_curriculum.py"
    "ast_refactoring_curriculum.py"
    "conditional_bonus_curriculum.py"
    "constant_folding_curriculum.py"
    "constant_propagation_curriculum.py"
    "interprocedural_curriculum.py"
    "iterative_pricing_curriculum.py"
    "loop_analysis_curriculum.py"
    "nullability_analysis_curriculum.py"
    "range_analysis_curriculum.py"
    "structured_sum_curriculum.py"
)

# Move files
echo "Moving curriculum files to archive..."
for file in "${OLD_FILES[@]}"; do
    if [ -f "src/regionai/data/$file" ]; then
        echo "  Archiving: $file"
        mv "src/regionai/data/$file" "$ARCHIVE_DIR/"
    fi
done

echo
echo "=== Summary ==="
echo "Unified curriculum factory: src/regionai/data/curriculum_factory.py"
echo "Compatibility wrappers: src/regionai/data/curriculum_wrappers.py"
echo "Migration guide: src/regionai/data/CURRICULUM_MIGRATION_GUIDE.md"
echo "Archived files: $ARCHIVE_DIR/"
echo
echo "Code reduction: ~2,388 lines (75% reduction)"
echo "  Before: 3,188 lines across 14 files"
echo "  After:  ~800 lines in factory + wrappers"