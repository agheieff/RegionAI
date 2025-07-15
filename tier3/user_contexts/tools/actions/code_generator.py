"""
Code generation service for autonomous fix creation.

This service transforms FixSuggestions into actual code modifications using
AST-based manipulation. This ensures syntactically correct and safe transformations.
"""

import ast
from typing import Optional, List, Set, Dict, Any

from ..domain.actions import FixSuggestion, GeneratedFix


class SslFixerTransformer(ast.NodeTransformer):
    """
    AST transformer that fixes insecure SSL verification.
    
    This transformer finds calls to HTTP request functions with
    verify=False and changes them to verify=True.
    """
    
    def __init__(self, context_data: dict):
        """Initialize with context data from the fix suggestion."""
        self.context_data = context_data
        self.changes_made = []
    
    def visit_Call(self, node: ast.Call) -> ast.Call:
        """Visit function calls and fix SSL verification issues."""
        # First, recursively process child nodes
        self.generic_visit(node)
        
        # Check if this is a call we care about (e.g., requests.get, session.post, etc.)
        func_name = self._get_function_name(node)
        if func_name and any(method in func_name for method in ['get', 'post', 'put', 'delete', 'request', 'send']):
            # Look for verify parameter
            for i, keyword in enumerate(node.keywords):
                if keyword.arg == 'verify':
                    # Check if it's set to False
                    if (isinstance(keyword.value, ast.Constant) and 
                        keyword.value.value is False):
                        # Change to True
                        node.keywords[i].value = ast.Constant(value=True)
                        self.changes_made.append(
                            f"Changed verify=False to verify=True in {func_name} call"
                        )
                    # Note: ast.NameConstant is deprecated in Python 3.8+
                    # All constant values should use ast.Constant
        
        return node
    
    def _get_function_name(self, node: ast.Call) -> Optional[str]:
        """Extract the function name from a Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Handle chained calls like requests.get or self.session.post
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return '.'.join(reversed(parts))
        return None


class DocstringGeneratorTransformer(ast.NodeTransformer):
    """
    AST transformer that adds missing docstrings to functions.
    
    This transformer finds function definitions without docstrings
    and adds a placeholder docstring that can be filled in later.
    """
    
    def __init__(self, context_data: dict):
        """Initialize with context data from the fix suggestion."""
        self.context_data = context_data
        self.changes_made = []
        self.target_function = context_data.get('function_name')
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit function definitions and add missing docstrings."""
        # First, recursively process child nodes
        self.generic_visit(node)
        
        # Check if this is the target function
        if node.name == self.target_function:
            # Check if it already has a docstring
            if not ast.get_docstring(node):
                # Create a placeholder docstring
                docstring_lines = ['TODO: Add a docstring.']
                
                # Add parameter documentation if there are parameters
                params = self.context_data.get('parameters', [])
                non_self_params = [p for p in params if p != 'self']
                
                if non_self_params:
                    docstring_lines.append('')
                    docstring_lines.append('Args:')
                    for param in non_self_params:
                        docstring_lines.append(f'    {param}: TODO: Describe this parameter.')
                
                # Add return documentation if function has returns
                if self.context_data.get('has_return', False):
                    docstring_lines.append('')
                    docstring_lines.append('Returns:')
                    docstring_lines.append('    TODO: Describe the return value.')
                
                # Create the docstring node
                docstring = '\n'.join(docstring_lines)
                docstring_node = ast.Expr(value=ast.Constant(value=docstring))
                
                # Insert at the beginning of the function body
                node.body.insert(0, docstring_node)
                
                self.changes_made.append(
                    f"Added placeholder docstring to function '{node.name}'"
                )
        
        return node


class FunctionDecomposerTransformer(ast.NodeTransformer):
    """
    Sophisticated AST transformer that refactors complex functions by
    extracting blocks into helper methods.
    
    This transformer analyzes complex functions and extracts cohesive
    blocks of code (like large if statements or loops) into separate
    helper methods, reducing cyclomatic complexity.
    """
    
    def __init__(self, context_data: dict):
        """Initialize with context data from the fix suggestion."""
        self.context_data = context_data
        self.changes_made = []
        self.function_ast = context_data.get('function_ast')
        self.extractable_blocks = context_data.get('extractable_blocks', [])
        self.new_methods = []  # Store new helper methods to add
        self.method_counter = 0
        self.current_class = None  # Track if we're in a class
        self.is_method = False  # Track if the function is a method
    
    def visit_Module(self, node: ast.Module) -> ast.Module:
        """Visit module and add new helper functions at the end."""
        # First, process all child nodes
        self.generic_visit(node)
        
        # Add any new helper functions at the module level
        if self.new_methods and not self.current_class:
            for method in self.new_methods:
                node.body.append(method)
        
        return node
    
    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        """Visit class definitions to track context and add helper methods."""
        # Track that we're in a class
        old_class = self.current_class
        self.current_class = node
        
        # Process the class body
        self.generic_visit(node)
        
        # Add any new helper methods to the class
        if self.new_methods and self.current_class == node:
            for method in self.new_methods:
                node.body.append(method)
            self.new_methods = []  # Clear after adding
        
        # Restore previous class context
        self.current_class = old_class
        
        return node
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        """Visit function definitions and potentially decompose them."""
        # Check if this is our target function
        if (hasattr(self.function_ast, 'name') and 
            node.name == self.function_ast.name and 
            self.extractable_blocks):
            
            # Check if this is a method (has 'self' as first parameter)
            self.is_method = (len(node.args.args) > 0 and 
                            node.args.args[0].arg == 'self')
            
            # Find the best block to extract
            block_to_extract = self._select_block_to_extract(node)
            
            if block_to_extract:
                # Extract the block into a helper method
                self._extract_block_to_helper(node, block_to_extract)
        
        # Process child nodes
        self.generic_visit(node)
        
        return node
    
    def _select_block_to_extract(self, func_node: ast.FunctionDef) -> Optional[Dict[str, Any]]:
        """Select the most suitable block to extract."""
        # Find extractable blocks that are actually in this function
        valid_blocks = []
        
        for block_info in self.extractable_blocks:
            block_node = block_info['node']
            # Check if this block is actually in our function
            for node in ast.walk(func_node):
                if node is block_node:
                    valid_blocks.append(block_info)
                    break
        
        # Select the largest block (by size and complexity contribution)
        if valid_blocks:
            return valid_blocks[0]  # Already sorted by size/complexity
        
        return None
    
    def _extract_block_to_helper(self, func_node: ast.FunctionDef, 
                                block_info: Dict[str, Any]) -> None:
        """Extract a block of code into a helper method."""
        block_node = block_info['node']
        used_vars = block_info.get('used_variables', set())
        assigned_vars = block_info.get('assigned_variables', set())
        
        # Generate a meaningful helper method name
        helper_name = self._generate_helper_name(block_info)
        
        # Determine parameters and return values
        # Parameters: variables used but not assigned in the block
        # (excluding 'self' if it's a method)
        params = list(used_vars - assigned_vars)
        if self.is_method and 'self' in params:
            params.remove('self')
        
        # For variables that are both used and assigned (like 'total'),
        # we need to pass them as parameters if they were defined outside the block
        vars_to_pass = []
        for var in assigned_vars:
            if var in used_vars:
                # This variable is both used and assigned, need to check if it's defined outside
                if self._is_variable_defined_before(func_node, block_node, var):
                    vars_to_pass.append(var)
        params.extend(vars_to_pass)
        params = sorted(list(set(params)))  # Remove duplicates and sort
        
        # Return values: variables assigned in the block that are used later
        returns = self._determine_return_values(func_node, block_node, assigned_vars)
        
        # Create the helper method
        helper_method = self._create_helper_method(
            helper_name, params, returns, block_node
        )
        
        # Replace the original block with a call to the helper
        replacement = self._create_helper_call(helper_name, params, returns)
        
        # Perform the replacement
        self._replace_node_in_function(func_node, block_node, replacement)
        
        # Add the helper method to our list
        self.new_methods.append(helper_method)
        
        # Record the change
        self.changes_made.append(
            f"Extracted {block_info['type']} block (line {block_info.get('line', 'unknown')}) "
            f"into helper method '{helper_name}'"
        )
    
    def _generate_helper_name(self, block_info: Dict[str, Any]) -> str:
        """Generate a descriptive name for the helper method."""
        block_type = block_info['type']
        self.method_counter += 1
        
        # Create descriptive names based on block type
        if block_type == 'if':
            # Try to understand what the condition checks
            node = block_info['node']
            if hasattr(node, 'test'):
                # Simple heuristic based on condition
                test_str = ast.unparse(node.test) if hasattr(ast, 'unparse') else 'condition'
                if 'None' in test_str or 'null' in test_str:
                    return f"_handle_none_case_{self.method_counter}"
                elif 'error' in test_str.lower() or 'exception' in test_str.lower():
                    return f"_handle_error_case_{self.method_counter}"
                elif 'valid' in test_str.lower():
                    return f"_handle_validation_{self.method_counter}"
            return f"_process_condition_{self.method_counter}"
        
        elif block_type == 'for':
            return f"_process_items_{self.method_counter}"
        
        elif block_type == 'while':
            return f"_process_loop_{self.method_counter}"
        
        else:
            return f"_helper_{self.method_counter}"
    
    def _is_variable_defined_before(self, func_node: ast.FunctionDef, 
                                   block_node: ast.AST, var_name: str) -> bool:
        """Check if a variable is defined before the given block."""
        for stmt in func_node.body:
            if stmt is block_node:
                return False
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == var_name:
                        return True
        return False
    
    def _determine_return_values(self, func_node: ast.FunctionDef, 
                               block_node: ast.AST, 
                               assigned_vars: Set[str]) -> List[str]:
        """Determine which assigned variables need to be returned."""
        # Find variables assigned in the block that are used after the block
        vars_used_after = set()
        
        # Find the index of the block in the function body
        block_index = -1
        for i, stmt in enumerate(func_node.body):
            if stmt is block_node:
                block_index = i
                break
        
        if block_index == -1:
            return []
        
        # Check statements after the block
        for stmt in func_node.body[block_index + 1:]:
            for node in ast.walk(stmt):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    if node.id in assigned_vars:
                        vars_used_after.add(node.id)
        
        return sorted(list(vars_used_after))
    
    def _create_helper_method(self, name: str, params: List[str], 
                            returns: List[str], block_node: ast.AST) -> ast.FunctionDef:
        """Create a helper method AST node."""
        # Create parameter list
        args = []
        
        # Add 'self' if this is a method
        if self.is_method:
            args.append(ast.arg(arg='self', annotation=None))
        
        # Add other parameters
        for param in params:
            args.append(ast.arg(arg=param, annotation=None))
        
        # Create the function arguments
        arguments = ast.arguments(
            posonlyargs=[],
            args=args,
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[]
        )
        
        # Extract the body - need to make a deep copy
        import copy
        if isinstance(block_node, ast.If):
            body = copy.deepcopy(block_node.body)
        elif isinstance(block_node, (ast.For, ast.While)):
            body = copy.deepcopy(block_node.body)
        else:
            body = [copy.deepcopy(block_node)]
        
        # Add return statement if needed
        if returns:
            # Check if the last statement is already a return
            has_return = (body and isinstance(body[-1], ast.Return))
            
            if not has_return:
                if len(returns) == 1:
                    # Single return value
                    return_value = ast.Name(id=returns[0], ctx=ast.Load())
                else:
                    # Multiple return values as tuple
                    return_value = ast.Tuple(
                        elts=[ast.Name(id=var, ctx=ast.Load()) for var in returns],
                        ctx=ast.Load()
                    )
                body.append(ast.Return(value=return_value))
        
        # Create the helper function
        helper = ast.FunctionDef(
            name=name,
            args=arguments,
            body=body if body else [ast.Pass()],  # Ensure body is not empty
            decorator_list=[],
            returns=None
        )
        
        # Copy line number from original node if available
        if hasattr(block_node, 'lineno'):
            helper.lineno = block_node.lineno
            helper.col_offset = 0
        
        # Fix missing locations in the helper
        ast.fix_missing_locations(helper)
        
        return helper
    
    def _create_helper_call(self, name: str, params: List[str], 
                          returns: List[str]) -> ast.AST:
        """Create a call to the helper method."""
        # Create the function call
        if self.is_method:
            # Method call: self._helper(...)
            func = ast.Attribute(
                value=ast.Name(id='self', ctx=ast.Load()),
                attr=name,
                ctx=ast.Load()
            )
        else:
            # Function call: _helper(...)
            func = ast.Name(id=name, ctx=ast.Load())
        
        # Create arguments
        args = [ast.Name(id=param, ctx=ast.Load()) for param in params]
        
        # Create the call
        call = ast.Call(func=func, args=args, keywords=[])
        
        # Handle return values
        if not returns:
            # No return values - just the call
            return ast.Expr(value=call)
        elif len(returns) == 1:
            # Single return - assign to variable
            return ast.Assign(
                targets=[ast.Name(id=returns[0], ctx=ast.Store())],
                value=call
            )
        else:
            # Multiple returns - tuple unpacking
            return ast.Assign(
                targets=[ast.Tuple(
                    elts=[ast.Name(id=var, ctx=ast.Store()) for var in returns],
                    ctx=ast.Store()
                )],
                value=call
            )
    
    def _replace_node_in_function(self, func_node: ast.FunctionDef, 
                                old_node: ast.AST, 
                                new_node: ast.AST) -> None:
        """Replace a node in the function body."""
        # Find and replace the node
        for i, stmt in enumerate(func_node.body):
            if stmt is old_node:
                func_node.body[i] = new_node
                return
        
        # If not found at top level, we need a more sophisticated approach
        # For now, we'll log a warning
        print(f"Warning: Could not find node to replace at top level")
    
    def _replace_in_body(self, body: List[ast.AST], 
                       old_node: ast.AST, 
                       new_node: ast.AST) -> None:
        """Replace a node in a body list."""
        for i, stmt in enumerate(body):
            if stmt is old_node:
                body[i] = new_node
                return


class CodeGenerator:
    """
    Service for generating code fixes based on detected vulnerabilities.
    
    This service uses AST-based manipulation to ensure safe and
    syntactically correct code transformations.
    """
    
    def __init__(self):
        """Initialize the code generator."""
        # Map vulnerability IDs to their transformer classes
        self.transformers = {
            "INSECURE_SSL_VERIFICATION": SslFixerTransformer,
            "MISSING_DOCSTRING": DocstringGeneratorTransformer,
            "HIGH_COMPLEXITY": FunctionDecomposerTransformer,
            # Future: Add more transformers here
        }
    
    def generate_fix(self, suggestion: FixSuggestion) -> str:
        """
        Generate a fixed version of the function's source code.
        
        This method takes a FixSuggestion and returns the complete
        modified source code with the vulnerability fixed.
        
        Args:
            suggestion: The fix suggestion containing vulnerability info
            
        Returns:
            The modified source code as a string
            
        Raises:
            ValueError: If the vulnerability type is not supported
            SyntaxError: If the source code cannot be parsed
        """
        # Check if we have a transformer for this vulnerability type
        if suggestion.vulnerability_id not in self.transformers:
            raise ValueError(
                f"No transformer available for vulnerability: {suggestion.vulnerability_id}"
            )
        
        # Get the source code
        source_code = suggestion.target_artifact.source_code
        if not source_code:
            raise ValueError("No source code available in target artifact")
        
        # For HIGH_COMPLEXITY, we need the entire module/class source
        # Not just the function, since we're adding helper methods
        if suggestion.vulnerability_id == "HIGH_COMPLEXITY":
            # Try to get the full module source from the context
            module_source = suggestion.context_data.get('module_source')
            if module_source:
                source_code = module_source
            else:
                # If not provided, we'll work with what we have
                # In a real implementation, we'd need to read the full file
                pass
        
        # Parse the source code into an AST
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            raise SyntaxError(f"Failed to parse source code: {e}")
        
        # Create and apply the appropriate transformer
        transformer_class = self.transformers[suggestion.vulnerability_id]
        transformer = transformer_class(suggestion.context_data)
        
        # Transform the AST
        modified_tree = transformer.visit(tree)
        
        # Fix line numbers and column offsets
        ast.fix_missing_locations(modified_tree)
        
        # Convert back to source code
        try:
            # Try to use ast.unparse (requires Python 3.9+)
            modified_source = ast.unparse(modified_tree)
        except AttributeError:
            # Python 3.9+ is required for ast.unparse
            raise RuntimeError(
                "ast.unparse requires Python 3.9 or higher. "
                "Please upgrade your Python version."
            )
        
        # Create a GeneratedFix object for detailed tracking
        generated_fix = GeneratedFix(
            original_suggestion=suggestion,
            modified_source=modified_source,
            changes_made=transformer.changes_made
        )
        
        # Store the generated fix for reference (could be used for logging)
        self._last_generated_fix = generated_fix
        
        return modified_source
    
    def get_last_fix_summary(self) -> Optional[str]:
        """
        Get a summary of the last generated fix.
        
        Returns:
            Summary string or None if no fix has been generated
        """
        if hasattr(self, '_last_generated_fix'):
            return self._last_generated_fix.get_summary()
        return None