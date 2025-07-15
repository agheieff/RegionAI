#!/usr/bin/env python3
"""
Update import statements in test files to use new tier structure.
"""

import os
import re
import sys
from pathlib import Path

# Mapping of old imports to new imports
IMPORT_MAPPINGS = {
    # Tier1 imports (universal reasoning)
    'from regionai.config import': 'from tier1.config import',
    'from regionai.core.abstract_domains import': 'from tier1.core.abstract_domains import',
    'from regionai.analysis.': 'from tier1.analysis.',
    'from regionai.discovery.': 'from tier1.discovery.',
    'from regionai.models.': 'from tier1.models.',
    'from regionai.brains.': 'from tier1.brains.',
    
    # Tier2 imports (domain knowledge)
    'from regionai.domains.': 'from tier2.domains.',
    'from regionai.knowledge.': 'from tier2.knowledge.',
    'from regionai.language.': 'from tier2.language.',
    'from regionai.data.': 'from tier2.data.',
    'from regionai.utils.': 'from tier2.utils.',
    
    # Tier3 imports (situational overlays)
    'from regionai.reasoning.': 'from tier3.reasoning.',
    'from regionai.embodiment.': 'from tier3.embodiment.',
    'from regionai.temporal.': 'from tier3.temporal.',
    'from regionai.metacognition.': 'from tier3.metacognition.',
    'from regionai.synthesis.': 'from tier3.synthesis.',
    'from regionai.reporting.': 'from tier3.reporting.',
    'from regionai.integration.': 'from tier3.integration.',
    'from regionai.verification.': 'from tier3.verification.',
}

def update_file_imports(file_path):
    """Update imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        updated = False
        
        # Apply import mappings
        for old_import, new_import in IMPORT_MAPPINGS.items():
            if old_import in content:
                content = content.replace(old_import, new_import)
                updated = True
        
        # Special handling for some common patterns
        # Handle imports that span multiple lines
        content = re.sub(
            r'from regionai\.(\w+)\.(\w+) import \(',
            r'from tier2.\1.\2 import (',
            content
        )
        
        # Save if changes were made
        if updated and content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False

def main():
    """Update all test files."""
    tests_dir = Path("tests")
    
    if not tests_dir.exists():
        print("Tests directory not found!")
        return 1
    
    updated_files = []
    failed_files = []
    
    # Find all Python files in tests directory
    for file_path in tests_dir.rglob("*.py"):
        if file_path.name.startswith("test_") or file_path.name.endswith("_test.py"):
            try:
                if update_file_imports(file_path):
                    updated_files.append(str(file_path))
                    print(f"✓ Updated: {file_path}")
                else:
                    print(f"- No changes: {file_path}")
            except Exception as e:
                failed_files.append(str(file_path))
                print(f"✗ Failed: {file_path} - {e}")
    
    print(f"\nSummary:")
    print(f"Updated: {len(updated_files)} files")
    print(f"Failed: {len(failed_files)} files")
    
    if updated_files:
        print(f"\nUpdated files:")
        for file_path in updated_files[:10]:  # Show first 10
            print(f"  {file_path}")
        if len(updated_files) > 10:
            print(f"  ... and {len(updated_files) - 10} more")
    
    return 0 if not failed_files else 1

if __name__ == "__main__":
    sys.exit(main())