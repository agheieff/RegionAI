"""
Utility modules for RegionAI.

This package contains shared utilities and helper functions used across
the RegionAI codebase.
"""

from .text_utils import to_singular, to_plural, is_plural, get_singular_plural_forms

__all__ = ['to_singular', 'to_plural', 'is_plural', 'get_singular_plural_forms']