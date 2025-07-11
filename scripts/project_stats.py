#!/usr/bin/env python3
"""
Project statistics script for RegionAI.

This script provides comprehensive statistics about the RegionAI codebase
by properly importing and inspecting the modules rather than using grep.
"""
import os
import sys
import ast
import importlib
import inspect
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple

# Add the src directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Import RegionAI modules
try:
    from regionai.semantic.fingerprint import Behavior
    from regionai.discovery import PRIMITIVE_TRANSFORMATIONS, STRUCTURED_DATA_PRIMITIVES, AST_PRIMITIVES
    from regionai.data import list_curricula
except ImportError as e:
    print(f"Error importing RegionAI modules: {e}")
    print("Make sure you're running this from the project root.")
    sys.exit(1)


def count_lines_of_code(directory: Path, extensions: List[str] = ['.py']) -> Dict[str, int]:
    """Count lines of code in a directory, excluding blank lines and comments."""
    stats = defaultdict(int)
    
    for ext in extensions:
        for file_path in directory.rglob(f"*{ext}"):
            if "__pycache__" in str(file_path) or ".venv" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                # Count total lines
                stats[f"total_lines{ext}"] += len(lines)
                
                # Count non-blank, non-comment lines
                code_lines = 0
                for line in lines:
                    stripped = line.strip()
                    if stripped and not stripped.startswith('#'):
                        code_lines += 1
                stats[f"code_lines{ext}"] += code_lines
                
                # Count files
                stats[f"files{ext}"] += 1
                
            except Exception:
                pass  # Skip files that can't be read
                
    return dict(stats)


def analyze_classes_and_functions(directory: Path) -> Dict[str, int]:
    """Analyze Python files to count classes, functions, and methods."""
    stats = defaultdict(int)
    
    for file_path in directory.rglob("*.py"):
        if "__pycache__" in str(file_path) or ".venv" in str(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
                
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    stats["classes"] += 1
                elif isinstance(node, ast.FunctionDef):
                    # Check if it's a method (inside a class)
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.ClassDef) and node in parent.body:
                            stats["methods"] += 1
                            break
                    else:
                        stats["functions"] += 1
                        
        except Exception:
            pass  # Skip files that can't be parsed
            
    return dict(stats)


def get_test_statistics(test_dir: Path) -> Dict[str, int]:
    """Get statistics about the test suite."""
    stats = defaultdict(int)
    
    for file_path in test_dir.rglob("test_*.py"):
        if "__pycache__" in str(file_path):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
                
            stats["test_files"] += 1
            
            # Count test functions/methods
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                    stats["test_functions"] += 1
                    
        except Exception:
            pass
            
    return dict(stats)


def main():
    """Generate and display comprehensive project statistics."""
    print("=" * 60)
    print("RegionAI Project Statistics")
    print("=" * 60)
    print()
    
    # 1. Semantic Dimensions (Behaviors)
    print("1. Semantic Dimensions (Behaviors):")
    behaviors = [b for b in dir(Behavior) if not b.startswith('_') and b.isupper()]
    print(f"   Total: {len(behaviors)}")
    print("   Examples:")
    for behavior in behaviors[:5]:
        print(f"   - {behavior}")
    print()
    
    # 2. Transformation Primitives
    print("2. Transformation Primitives:")
    print(f"   Basic Primitives: {len(PRIMITIVE_TRANSFORMATIONS)}")
    print(f"   Structured Data Primitives: {len(STRUCTURED_DATA_PRIMITIVES)}")
    print(f"   AST Primitives: {len(AST_PRIMITIVES)}")
    print(f"   Total: {len(PRIMITIVE_TRANSFORMATIONS) + len(STRUCTURED_DATA_PRIMITIVES) + len(AST_PRIMITIVES)}")
    print()
    
    # 3. Curricula
    print("3. Problem Curricula:")
    curricula = list_curricula()
    print(f"   Total Curriculum Types: {len(curricula)}")
    print("   Available curricula:")
    for curriculum in sorted(curricula)[:10]:
        print(f"   - {curriculum}")
    if len(curricula) > 10:
        print(f"   ... and {len(curricula) - 10} more")
    print()
    
    # 4. Code Statistics
    print("4. Code Statistics:")
    src_dir = project_root / "src"
    code_stats = count_lines_of_code(src_dir)
    print(f"   Python Files: {code_stats.get('files.py', 0)}")
    print(f"   Total Lines: {code_stats.get('total_lines.py', 0):,}")
    print(f"   Code Lines (non-blank, non-comment): {code_stats.get('code_lines.py', 0):,}")
    print()
    
    # 5. Code Structure
    print("5. Code Structure:")
    structure_stats = analyze_classes_and_functions(src_dir)
    print(f"   Classes: {structure_stats.get('classes', 0)}")
    print(f"   Functions: {structure_stats.get('functions', 0)}")
    print(f"   Methods: {structure_stats.get('methods', 0)}")
    print()
    
    # 6. Test Suite
    print("6. Test Suite:")
    test_dir = project_root / "tests"
    test_stats = get_test_statistics(test_dir)
    print(f"   Test Files: {test_stats.get('test_files', 0)}")
    print(f"   Test Functions: {test_stats.get('test_functions', 0)}")
    print()
    
    # 7. Module Structure
    print("7. Module Structure:")
    modules = []
    for item in (src_dir / "regionai").iterdir():
        if item.is_dir() and not item.name.startswith("__"):
            modules.append(item.name)
    
    print(f"   Core Modules: {len(modules)}")
    for module in sorted(modules):
        print(f"   - {module}")
    print()
    
    # 8. Configuration Parameters
    print("8. Configuration:")
    try:
        from regionai.config import RegionAIConfig
        config = RegionAIConfig()
        config_fields = [f for f in dir(config) if not f.startswith('_')]
        print(f"   Configuration Parameters: {len(config_fields)}")
        print("   Parameter Categories:")
        print("   - Analysis Settings")
        print("   - Abstract Domains") 
        print("   - Performance & Caching")
        print("   - Error Handling")
        print("   - Discovery Settings")
    except ImportError:
        print("   Unable to load configuration module")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()