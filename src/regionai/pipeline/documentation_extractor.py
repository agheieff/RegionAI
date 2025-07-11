"""
Documentation Extractor for the Language Bridge.

This module extracts natural language context from Python functions,
creating the foundational data needed to connect code semantics with
human language understanding.
"""
import ast
import re
from typing import List, Optional, Dict

from ..semantic.fingerprint import NaturalLanguageContext


class DocumentationExtractor(ast.NodeVisitor):
    """
    Extracts docstrings and other natural language elements from function ASTs.
    
    This class forms the first step in building the Language Bridge by creating
    rich natural language contexts that can be paired with semantic fingerprints.
    """
    
    def __init__(self):
        self.comments: List[str] = []
        self.variable_names: List[str] = []
        
    def extract(self, node: ast.FunctionDef) -> NaturalLanguageContext:
        """
        Extract natural language context from a function definition.
        
        Args:
            node: AST node representing a function definition
            
        Returns:
            NaturalLanguageContext with extracted documentation and metadata
        """
        # Reset state for this extraction
        self.comments = []
        self.variable_names = []
        
        # Extract basic information
        function_name = node.name
        docstring = ast.get_docstring(node)
        parameter_names = [arg.arg for arg in node.args.args]
        
        # Extract return description from docstring
        return_description = self._extract_return_description(docstring)
        
        # Visit the function body to extract comments and variable names
        for stmt in node.body:
            self.visit(stmt)
        
        return NaturalLanguageContext(
            function_name=function_name,
            docstring=docstring,
            parameter_names=parameter_names,
            return_description=return_description,
            comments=self.comments.copy(),
            variable_names=self.variable_names.copy()
        )
    
    def _extract_return_description(self, docstring: Optional[str]) -> Optional[str]:
        """
        Extract return value description from docstring.
        
        Looks for common patterns like "Returns:", "Return:", etc.
        """
        if not docstring:
            return None
        
        # Common patterns for return documentation
        patterns = [
            r'Returns?:\s*(.+?)(?:\n\n|\n[A-Z]|\Z)',
            r'@return\s+(.+?)(?:\n\n|\n@|\Z)',
            r'Return\s+(.+?)(?:\n\n|\n[A-Z]|\Z)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, docstring, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        
        return None
    
    def visit_Assign(self, node: ast.Assign):
        """Extract variable names from assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variable_names.append(target.id)
        self.generic_visit(node)
    
    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Extract variable names from annotated assignments."""
        if isinstance(node.target, ast.Name):
            self.variable_names.append(node.target.id)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Don't recurse into nested function definitions."""
        # Only extract from the immediate function, not nested ones
        pass
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Don't recurse into class definitions within functions."""
        pass


class CommentExtractor:
    """
    Extracts comments from source code text.
    
    Since the AST doesn't preserve comments, we need to parse the raw source.
    """
    
    @staticmethod
    def extract_function_comments(source_code: str, function_name: str) -> List[str]:
        """
        Extract comments associated with a specific function.
        
        Args:
            source_code: The complete source code text
            function_name: Name of the function to extract comments for
            
        Returns:
            List of comment strings (without # prefix)
        """
        lines = source_code.split('\n')
        comments = []
        
        # Find the function definition
        func_start = None
        func_indent = None
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(f'def {function_name}('):
                func_start = i
                func_indent = len(line) - len(line.lstrip())
                break
        
        if func_start is None:
            return comments
        
        # Extract comments within the function
        in_function = False
        for i in range(func_start, len(lines)):
            line = lines[i]
            stripped = line.strip()
            
            # Determine if we're still in the function
            if i == func_start:
                in_function = True
            elif stripped and not stripped.startswith('#'):
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= func_indent and stripped.startswith(('def ', 'class ', '@')):
                    # Next function/class definition at same or higher level
                    break
            
            # Extract comments
            if in_function and '#' in line:
                comment_match = re.search(r'#\s*(.+)', line)
                if comment_match:
                    comment_text = comment_match.group(1).strip()
                    if comment_text and comment_text not in comments:
                        comments.append(comment_text)
        
        return comments


class AdvancedDocumentationExtractor:
    """
    Enhanced documentation extractor that combines AST and source analysis.
    
    This provides the most comprehensive extraction of natural language context.
    """
    
    def __init__(self):
        self.ast_extractor = DocumentationExtractor()
        self.comment_extractor = CommentExtractor()
    
    def extract_from_function(self, node: ast.FunctionDef, 
                            source_code: Optional[str] = None) -> NaturalLanguageContext:
        """
        Extract comprehensive documentation from a function.
        
        Args:
            node: Function AST node
            source_code: Optional source code for comment extraction
            
        Returns:
            Complete NaturalLanguageContext with all available information
        """
        # Start with AST-based extraction
        context = self.ast_extractor.extract(node)
        
        # Enhance with source-based comment extraction if available
        if source_code:
            source_comments = self.comment_extractor.extract_function_comments(
                source_code, node.name
            )
            # Merge comments, avoiding duplicates
            all_comments = list(context.comments)
            for comment in source_comments:
                if comment not in all_comments:
                    all_comments.append(comment)
            context.comments = all_comments
        
        return context
    
    def extract_from_module(self, tree: ast.AST, 
                           source_code: Optional[str] = None) -> Dict[str, NaturalLanguageContext]:
        """
        Extract documentation for all functions in a module.
        
        Args:
            tree: Module AST
            source_code: Optional source code for enhanced extraction
            
        Returns:
            Dictionary mapping function names to their natural language contexts
        """
        contexts = {}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                context = self.extract_from_function(node, source_code)
                contexts[node.name] = context
        
        return contexts


class DocumentationAnalyzer:
    """
    Analyzes documentation quality and extracts insights for language bridge training.
    """
    
    @staticmethod
    def analyze_vocabulary(contexts: List[NaturalLanguageContext]) -> Dict[str, int]:
        """
        Analyze the vocabulary used in documentation.
        
        Useful for understanding the language patterns in the codebase.
        """
        word_counts = {}
        
        for context in contexts:
            text = context.get_text_content().lower()
            # Simple word extraction (could be enhanced with proper tokenization)
            words = re.findall(r'\b[a-zA-Z]+\b', text)
            
            for word in words:
                if len(word) > 2:  # Filter out very short words
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        return word_counts
    
    @staticmethod
    def find_common_patterns(contexts: List[NaturalLanguageContext]) -> Dict[str, List[str]]:
        """
        Find common documentation patterns that could be useful for training.
        
        Returns categories of functions based on their documentation patterns.
        """
        patterns = {
            'returns_boolean': [],
            'takes_input': [],
            'modifies_state': [],
            'performs_calculation': [],
            'validates_input': [],
        }
        
        for context in contexts:
            if not context.docstring:
                continue
                
            docstring_lower = context.docstring.lower()
            func_name = context.function_name
            
            # Pattern detection based on common documentation language
            if any(word in docstring_lower for word in ['true', 'false', 'boolean', 'check', 'test']):
                patterns['returns_boolean'].append(func_name)
            
            if any(word in docstring_lower for word in ['input', 'parameter', 'argument', 'takes']):
                patterns['takes_input'].append(func_name)
            
            if any(word in docstring_lower for word in ['modify', 'update', 'change', 'set']):
                patterns['modifies_state'].append(func_name)
            
            if any(word in docstring_lower for word in ['calculate', 'compute', 'sum', 'count']):
                patterns['performs_calculation'].append(func_name)
            
            if any(word in docstring_lower for word in ['validate', 'verify', 'ensure', 'assert']):
                patterns['validates_input'].append(func_name)
        
        return patterns
    
    @staticmethod
    def get_training_candidates(contexts: List[NaturalLanguageContext]) -> List[str]:
        """
        Identify functions that would make good training examples.
        
        Returns function names of well-documented functions suitable for training.
        """
        candidates = []
        
        for context in contexts:
            # Must have meaningful docstring
            if not context.docstring or len(context.docstring.strip()) < 20:
                continue
                
            # Must have meaningful parameter names
            if context.parameter_names:
                meaningful_params = sum(1 for name in context.parameter_names 
                                      if len(name) > 2 and name not in ['x', 'y', 'z'])
                if meaningful_params == 0:
                    continue
            
            # Function name should be descriptive
            if len(context.function_name) < 3 or context.function_name in ['f', 'g', 'h']:
                continue
                
            candidates.append(context.function_name)
        
        return candidates