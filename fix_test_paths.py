#!/usr/bin/env python3
"""
Fix Python path setup in test files to point to the correct location.
"""

import os
import re
import sys
from pathlib import Path

def fix_path_in_file(file_path):
    """Fix Python path setup in a single test file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace incorrect path setups
        patterns = [
            # Pattern 1: sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
            (r"sys\.path\.insert\(0, os\.path\.join\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\), 'src'\)\)",
             "sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))\n# Add the root directory to path for tier imports"),
            
            # Pattern 2: sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
            (r"sys\.path\.insert\(0, os\.path\.join\(os\.path\.dirname\(__file__\), '\.\.', '\.\.', 'src'\)\)",
             "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))\n# Add the root directory to path for tier imports"),
            
            # Pattern 3: Any other src path
            (r"sys\.path\.insert\(0, [^)]*'src'[^)]*\)",
             "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))\n# Add the root directory to path for tier imports"),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)
        
        # Also fix relative paths that might go too deep
        content = re.sub(
            r"sys\.path\.insert\(0, os\.path\.join\(os\.path\.dirname\(__file__\), '\.\.', '\.\.', '\.\.'\)\)",
            "sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))\n# Add the root directory to path for tier imports",
            content
        )
        
        # Save if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing paths in {file_path}: {e}")
        return False

def main():
    """Fix path setup in all test files."""
    tests_dir = Path("tests")
    
    if not tests_dir.exists():
        print("Tests directory not found!")
        return 1
    
    updated_files = []
    
    # Find all Python files in tests directory
    for file_path in tests_dir.rglob("*.py"):
        if file_path.name.startswith("test_") or file_path.name.endswith("_test.py"):
            try:
                if fix_path_in_file(file_path):
                    updated_files.append(str(file_path))
                    print(f"✓ Fixed paths: {file_path}")
            except Exception as e:
                print(f"✗ Failed: {file_path} - {e}")
    
    print(f"\nFixed paths in {len(updated_files)} files")
    return 0

if __name__ == "__main__":
    sys.exit(main())