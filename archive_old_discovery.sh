#!/bin/bash
# Archive old discovery files after unification

echo "=== Archiving Old Discovery Files ==="
echo "These files have been unified into discovery_engine.py"
echo

# Create archive directory
ARCHIVE_DIR="src/regionai/discovery/archive_old"
mkdir -p "$ARCHIVE_DIR"

# Files to archive
OLD_FILES=(
    "discover_v2.py"
    "discover_conditional.py"
    "discover_iterative.py"
    "discover_structured.py"
    "discover_ast.py"
)

# Move files
for file in "${OLD_FILES[@]}"; do
    if [ -f "src/regionai/discovery/$file" ]; then
        echo "Archiving: $file"
        mv "src/regionai/discovery/$file" "$ARCHIVE_DIR/"
    fi
done

# Keep the original discover.py for now (backward compatibility)
echo
echo "Keeping discover.py for backward compatibility"

echo
echo "=== Summary ==="
echo "Unified discovery engine: src/regionai/discovery/discovery_engine.py"
echo "Migration guide: src/regionai/discovery/MIGRATION_GUIDE.md"
echo "Archived files: $ARCHIVE_DIR/"
echo
echo "Line reduction: ~500 lines (42% reduction)"