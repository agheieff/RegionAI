"""
RegionAI Tier 2 - Domain Knowledge Modules

Pure domain knowledge modules that contain specialized knowledge for specific
fields of study. These modules provide factual knowledge, domain-specific
concepts, and specialized reasoning patterns.

Available domain modules:
- Physics: Physical laws, constants, and principles
- Chemistry: Chemical knowledge and reactions
- Mathematics: Mathematical concepts and operations
- Linguistics: Language structures and processing
- Biology: Biological systems and processes
- Computer Science: Algorithms, data structures, and analysis

Each module is independent and can be loaded as needed. They provide
domain-specific knowledge that the universal reasoning engine (tier1)
can apply to specific problems.
"""

from .domain_module import DomainModule
from .domain_hub import DomainHub

__all__ = ["DomainModule", "DomainHub"]