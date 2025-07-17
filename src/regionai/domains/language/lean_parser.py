"""
Parser for Lean theorem files.

This module provides functionality to parse .lean files and convert
theorem definitions into our internal AST representation.
"""

import re
from pathlib import Path
from typing import List, Optional, Tuple
import logging

try:
    from .lean_ast import Theorem, Hypothesis, Tactic, TacticType
except ImportError:
    # Allow direct module execution
    from lean_ast import Theorem, Hypothesis, Tactic, TacticType


logger = logging.getLogger(__name__)


class LeanParseError(Exception):
    """Raised when parsing a Lean file fails."""


class LeanParser:
    """
    Parser for Lean theorem files.
    
    This parser handles a simplified subset of Lean syntax, focusing on
    theorem definitions. It uses regex-based parsing to extract theorem
    names, hypotheses, and goal statements.
    
    Supported syntax:
    - theorem <name> (<params>) : <statement>
    - theorem <name> : <statement>
    - Comments starting with --
    - Multi-line theorem definitions
    """
    
    def __init__(self):
        """Initialize the Lean parser."""
        # Regex patterns for parsing
        self.theorem_pattern = re.compile(
            r'theorem\s+(\w+)\s*((?:\([^)]+\)\s*)*)\s*:\s*(.+?)(?=\n(?:theorem|def|lemma|example|--)|$)',
            re.DOTALL | re.MULTILINE
        )
        self.param_pattern = re.compile(r'(\w+)\s*:\s*([^,]+)')
        self.comment_pattern = re.compile(r'--.*$', re.MULTILINE)
        
    def parse_file(self, file_path: Path) -> List[Theorem]:
        """
        Parse a .lean file and extract theorem definitions.
        
        Args:
            file_path: Path to the .lean file
            
        Returns:
            List of Theorem objects parsed from the file
            
        Raises:
            LeanParseError: If the file cannot be parsed
            FileNotFoundError: If the file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Lean file not found: {file_path}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise LeanParseError(f"Failed to read file {file_path}: {e}")
            
        return self.parse_content(content, source_file=str(file_path))
    
    def parse_content(self, content: str, source_file: Optional[str] = None) -> List[Theorem]:
        """
        Parse Lean content and extract theorem definitions.
        
        Args:
            content: The Lean source code as a string
            source_file: Optional source file path for metadata
            
        Returns:
            List of Theorem objects parsed from the content
        """
        theorems = []
        
        # Remove comments to simplify parsing
        content_no_comments = self.comment_pattern.sub('', content)
        
        # Find all theorem definitions
        matches = self.theorem_pattern.finditer(content_no_comments)
        
        for match in matches:
            theorem_name = match.group(1)
            params_str = match.group(2) or ""
            statement = match.group(3).strip()
            
            # Parse parameters/hypotheses
            hypotheses = self._parse_parameters(params_str)
            
            # Create theorem object
            theorem = Theorem(
                name=theorem_name,
                statement=statement,
                hypotheses=hypotheses,
                metadata={
                    'source_file': source_file,
                    'raw_definition': match.group(0)
                }
            )
            
            theorems.append(theorem)
            logger.debug(f"Parsed theorem: {theorem_name}")
            
        logger.info(f"Parsed {len(theorems)} theorems from {source_file or 'content'}")
        return theorems
    
    def _parse_parameters(self, params_str: str) -> List[Hypothesis]:
        """
        Parse parameter/hypothesis definitions.
        
        Args:
            params_str: The parameter string, e.g., "(p : Prop) (q : Prop)" or "p : Prop, q : Prop"
            
        Returns:
            List of Hypothesis objects
        """
        hypotheses = []
        
        if not params_str.strip():
            return hypotheses
            
        # Handle parenthetical parameters: (p : Prop) (q : Prop)
        paren_pattern = re.compile(r'\(([^)]+)\)')
        paren_matches = paren_pattern.findall(params_str)
        
        if paren_matches:
            # Parse each parenthetical group
            for param_content in paren_matches:
                param_content = param_content.strip()
                if ':' in param_content:
                    colon_idx = param_content.rfind(':')
                    names_part = param_content[:colon_idx].strip()
                    type_part = param_content[colon_idx+1:].strip()
                    
                    # Split names if multiple (e.g., "p q : Prop")
                    names = names_part.split()
                    
                    for name in names:
                        if name:
                            hyp = Hypothesis(name=name, type_expr=type_part)
                            hypotheses.append(hyp)
                else:
                    # No type annotation, just a name
                    hyp = Hypothesis(name=param_content, type_expr="Type")
                    hypotheses.append(hyp)
            
            return hypotheses
            
        # Handle simple case: multiple variables with same type
        # e.g., "p q : Prop" or "p q r : Prop"
        simple_pattern = re.compile(r'^((?:\w+\s+)+):\s*(.+)$')
        simple_match = simple_pattern.match(params_str.strip())
        
        if simple_match:
            var_names = simple_match.group(1).split()
            var_type = simple_match.group(2).strip()
            
            for var_name in var_names:
                hyp = Hypothesis(name=var_name.strip(), type_expr=var_type)
                hypotheses.append(hyp)
        else:
            # Handle comma-separated parameters
            # Split by commas but be careful of nested structures
            params = self._split_parameters(params_str)
            
            for param in params:
                param = param.strip()
                if not param:
                    continue
                    
                # Check for type annotation
                if ':' in param:
                    # Could be "p : Prop" or "p q : Prop"
                    colon_idx = param.rfind(':')
                    names_part = param[:colon_idx].strip()
                    type_part = param[colon_idx+1:].strip()
                    
                    # Split names if multiple
                    names = names_part.split()
                    
                    for name in names:
                        if name:
                            hyp = Hypothesis(name=name, type_expr=type_part)
                            hypotheses.append(hyp)
                else:
                    # No type annotation, just a name
                    hyp = Hypothesis(name=param, type_expr="Type")
                    hypotheses.append(hyp)
        
        return hypotheses
    
    def _split_parameters(self, params_str: str) -> List[str]:
        """
        Split parameter string by commas, respecting parentheses.
        
        Args:
            params_str: Parameter string to split
            
        Returns:
            List of parameter strings
        """
        params = []
        current = []
        paren_depth = 0
        
        for char in params_str:
            if char == '(' or char == '{' or char == '[':
                paren_depth += 1
            elif char == ')' or char == '}' or char == ']':
                paren_depth -= 1
            elif char == ',' and paren_depth == 0:
                params.append(''.join(current).strip())
                current = []
                continue
                
            current.append(char)
        
        # Don't forget the last parameter
        if current:
            params.append(''.join(current).strip())
            
        return params
    
    def parse_proof(self, proof_str: str) -> List[Tactic]:
        """
        Parse a proof into a list of tactics.
        
        This is a simplified parser that recognizes basic tactic syntax.
        In a full implementation, this would need to handle the complete
        Lean tactic language.
        
        Args:
            proof_str: The proof as a string
            
        Returns:
            List of Tactic objects
        """
        tactics = []
        
        # Remove 'by' keyword if present
        proof_str = proof_str.strip()
        if proof_str.startswith('by'):
            proof_str = proof_str[2:].strip()
        
        # Simple line-based parsing for now
        lines = proof_str.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('--'):
                continue
                
            tactic = self._parse_tactic_line(line)
            if tactic:
                tactics.append(tactic)
                
        return tactics
    
    def _parse_tactic_line(self, line: str) -> Optional[Tactic]:
        """
        Parse a single tactic line.
        
        Args:
            line: A single line containing a tactic
            
        Returns:
            Tactic object or None if not recognized
        """
        line = line.strip()
        
        # Map of tactic names to TacticType
        tactic_map = {
            'intro': TacticType.INTRO,
            'apply': TacticType.APPLY,
            'exact': TacticType.EXACT,
            'rewrite': TacticType.REWRITE,
            'rw': TacticType.REWRITE,
            'simp': TacticType.SIMP,
            'ring': TacticType.RING,
            'norm_num': TacticType.NORM_NUM,
            'assumption': TacticType.ASSUMPTION,
            'constructor': TacticType.CONSTRUCTOR,
            'cases': TacticType.CASES,
            'induction': TacticType.INDUCTION,
            'by_contra': TacticType.BY_CONTRA,
            'use': TacticType.USE,
            'have': TacticType.HAVE,
            'show': TacticType.SHOW,
        }
        
        # Extract tactic name and arguments
        parts = line.split(None, 1)
        if not parts:
            return None
            
        tactic_name = parts[0].lower()
        arguments = parts[1].split() if len(parts) > 1 else []
        
        # Find matching tactic type
        tactic_type = tactic_map.get(tactic_name, TacticType.CUSTOM)
        
        return Tactic(
            tactic_type=tactic_type,
            arguments=arguments,
            metadata={'raw_line': line}
        )


class LeanFileValidator:
    """
    Validator for Lean files to ensure they are well-formed.
    
    This is a simple validator that checks for common syntax issues
    before attempting to parse.
    """
    
    @staticmethod
    def validate_file(file_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate a Lean file for basic syntax correctness.
        
        Args:
            file_path: Path to the Lean file
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return False, [f"Cannot read file: {e}"]
            
        # Check for balanced parentheses
        if not LeanFileValidator._check_balanced_parens(content):
            issues.append("Unbalanced parentheses, brackets, or braces")
            
        # Check for theorem definitions
        if 'theorem' not in content and 'lemma' not in content:
            issues.append("No theorem or lemma definitions found")
            
        # Check for common syntax errors
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for missing colons in theorem definitions
            if line.strip().startswith('theorem') and ':' not in line:
                # Check if colon is missing (not on current line and not on next line)
                next_line_has_colon = False
                if i < len(lines):  # Check if there's a next line
                    next_line_has_colon = ':' in lines[i]  # lines[i] is next line (0-based)
                if not next_line_has_colon:
                    issues.append(f"Line {i}: Theorem definition missing colon")
                    
        return len(issues) == 0, issues
    
    @staticmethod
    def _check_balanced_parens(content: str) -> bool:
        """Check if parentheses, brackets, and braces are balanced."""
        stack = []
        pairs = {'(': ')', '[': ']', '{': '}'}
        
        for char in content:
            if char in pairs:
                stack.append(char)
            elif char in pairs.values():
                if not stack:
                    return False
                if pairs[stack[-1]] != char:
                    return False
                stack.pop()
                
        return len(stack) == 0