"""
AST-native primitives for code transformation discovery.
"""
import ast
import copy
from typing import Any, List, Optional, Union, Dict
from ..core.transformation import Transformation


# --- AST Inspection Primitives ---

def get_node_type(node: ast.AST, args: List[Any]) -> str:
    """Returns the type of an AST node as a string."""
    if isinstance(node, ast.AST):
        return node.__class__.__name__
    return "NotANode"


def get_children(node: ast.AST, args: List[Any]) -> List[ast.AST]:
    """Returns all child nodes of an AST node."""
    if isinstance(node, ast.AST):
        children = []
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        children.append(item)
            elif isinstance(value, ast.AST):
                children.append(value)
        return children
    return []


def get_attribute(node: ast.AST, args: List[Any]) -> Any:
    """Gets a specific attribute from an AST node."""
    if isinstance(node, ast.AST) and len(args) > 0:
        attr_name = args[0]
        if hasattr(node, attr_name):
            return getattr(node, attr_name)
    return None


def get_child_at(node: ast.AST, args: List[Any]) -> Optional[ast.AST]:
    """Gets the child at a specific index."""
    if isinstance(node, ast.AST) and len(args) > 0:
        children = get_children(node, [])
        index = args[0]
        if 0 <= index < len(children):
            return children[index]
    return None


# --- AST Evaluation Primitives ---

def _get_binop_handlers() -> Dict[type, Any]:
    """Returns a dictionary mapping AST binary operation types to their handler functions."""
    return {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.FloorDiv: lambda a, b: a // b,
        ast.Mod: lambda a, b: a % b,
        ast.Pow: lambda a, b: a ** b,
        ast.LShift: lambda a, b: int(a) << int(b),
        ast.RShift: lambda a, b: int(a) >> int(b),
    }


def _get_unaryop_handlers() -> Dict[type, Any]:
    """Returns a dictionary mapping AST unary operation types to their handler functions."""
    return {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
        ast.Not: lambda a: not a,
    }


def _get_compare_handlers() -> Dict[type, Any]:
    """Returns a dictionary mapping AST comparison operation types to their handler functions."""
    return {
        ast.Eq: lambda a, b: a == b,
        ast.NotEq: lambda a, b: a != b,
        ast.Lt: lambda a, b: a < b,
        ast.LtE: lambda a, b: a <= b,
        ast.Gt: lambda a, b: a > b,
        ast.GtE: lambda a, b: a >= b,
    }


def evaluate_node(node: ast.AST, args: List[Any]) -> ast.AST:
    """
    Evaluates a node if possible and returns a Constant with the result.
    Only works for pure operations with constant operands.
    """
    if isinstance(node, ast.BinOp):
        # Check if both operands are constants
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            left_val = node.left.value
            right_val = node.right.value
            
            # Get the handler for this operation type
            binop_handlers = _get_binop_handlers()
            op_type = type(node.op)
            
            if op_type in binop_handlers:
                try:
                    handler = binop_handlers[op_type]
                    result = handler(left_val, right_val)
                    return ast.Constant(value=result)
                except (TypeError, ValueError, ZeroDivisionError, OverflowError):
                    return node  # Evaluation failed - return original node
            else:
                return node  # Unknown operation
    
    elif isinstance(node, ast.UnaryOp):
        if isinstance(node.operand, ast.Constant):
            operand_val = node.operand.value
            
            # Get the handler for this operation type
            unaryop_handlers = _get_unaryop_handlers()
            op_type = type(node.op)
            
            if op_type in unaryop_handlers:
                try:
                    handler = unaryop_handlers[op_type]
                    result = handler(operand_val)
                    return ast.Constant(value=result)
                except (TypeError, ValueError, AttributeError):
                    return node  # Evaluation failed - return original node
            else:
                return node  # Unknown operation
    
    elif isinstance(node, ast.Compare):
        # Handle simple comparisons with constants
        if len(node.ops) == 1 and len(node.comparators) == 1:
            if isinstance(node.left, ast.Constant) and isinstance(node.comparators[0], ast.Constant):
                left_val = node.left.value
                right_val = node.comparators[0].value
                op = node.ops[0]
                
                # Get the handler for this comparison type
                compare_handlers = _get_compare_handlers()
                op_type = type(op)
                
                if op_type in compare_handlers:
                    try:
                        handler = compare_handlers[op_type]
                        result = handler(left_val, right_val)
                        return ast.Constant(value=result)
                    except (TypeError, ValueError, AttributeError):
                        return node  # Comparison evaluation failed
                else:
                    return node  # Unknown comparison operation
    
    # Return original node if we can't evaluate
    return node


def is_constant(node: ast.AST, args: List[Any]) -> bool:
    """Checks if a node is a Constant."""
    return isinstance(node, ast.Constant)


def is_constant_false(node: ast.AST, args: List[Any]) -> bool:
    """Checks if a node is Constant(False)."""
    return isinstance(node, ast.Constant) and node.value is False


def is_constant_true(node: ast.AST, args: List[Any]) -> bool:
    """Checks if a node is Constant(True)."""
    return isinstance(node, ast.Constant) and node.value is True


def are_all_constants(nodes: List[ast.AST], args: List[Any]) -> bool:
    """Checks if all nodes in a list are Constants."""
    return all(isinstance(node, ast.Constant) for node in nodes)


# --- AST Pattern Matching ---

def is_binop_with_op(node: ast.AST, args: List[Any]) -> bool:
    """Checks if node is a BinOp with a specific operator."""
    if isinstance(node, ast.BinOp) and len(args) > 0:
        op_name = args[0]
        return node.op.__class__.__name__ == op_name
    return False


def is_constant_value(node: ast.AST, args: List[Any]) -> bool:
    """Checks if node is a Constant with a specific value."""
    if isinstance(node, ast.Constant) and len(args) > 0:
        expected_value = args[0]
        return node.value == expected_value
    return False


def is_power_of_two(node: ast.AST, args: List[Any]) -> bool:
    """Checks if node is a Constant with a power of 2 value."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        value = node.value
        if value > 0 and value == int(value):  # Positive integer
            # Check if it's a power of 2
            return (int(value) & (int(value) - 1)) == 0
    return False


def get_log2(node: ast.AST, args: List[Any]) -> int:
    """Gets the log base 2 of a constant node's value."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        value = int(node.value)
        if value > 0 and (value & (value - 1)) == 0:  # Is power of 2
            # Count trailing zeros (equivalent to log2)
            return (value & -value).bit_length() - 1
    return 0


# --- AST Manipulation Primitives ---

def replace_node(root: ast.AST, args: List[Any]) -> ast.AST:
    """
    Replaces a node in the AST with another node.
    args[0]: node to find and replace
    args[1]: replacement node
    """
    if len(args) < 2:
        return root
    
    target_node = args[0]
    replacement = args[1]
    
    class NodeReplacer(ast.NodeTransformer):
        def visit(self, node):
            if node is target_node:
                return replacement
            return self.generic_visit(node)
    
    replacer = NodeReplacer()
    new_tree = replacer.visit(root)
    return new_tree


def create_name_node(value: Any, args: List[Any]) -> ast.AST:
    """Creates a Name node with the given identifier."""
    if len(args) > 0:
        return ast.Name(id=args[0], ctx=ast.Load())
    return ast.Name(id="unnamed", ctx=ast.Load())


def create_constant_node(value: Any, args: List[Any]) -> ast.AST:
    """Creates a Constant node with the given value."""
    if len(args) > 0:
        return ast.Constant(value=args[0])
    return ast.Constant(value=0)


def create_binop_node(value: Any, args: List[Any]) -> ast.AST:
    """
    Creates a BinOp node with specified operation and operands.
    args[0]: operation type ('Add', 'Mult', 'LShift', etc.)
    args[1]: left operand (AST node)
    args[2]: right operand (AST node)
    """
    if len(args) >= 3:
        op_name = args[0]
        left = args[1]
        right = args[2]
        
        # Map operation names to AST operation classes
        op_map = {
            'Add': ast.Add(),
            'Sub': ast.Sub(),
            'Mult': ast.Mult(),
            'Div': ast.Div(),
            'LShift': ast.LShift(),
            'RShift': ast.RShift(),
        }
        
        if op_name in op_map and isinstance(left, ast.AST) and isinstance(right, ast.AST):
            return ast.BinOp(left=left, op=op_map[op_name], right=right)
    
    # Default fallback
    return ast.BinOp(
        left=ast.Name(id='x', ctx=ast.Load()),
        op=ast.Add(),
        right=ast.Constant(value=0)
    )


def clone_node(node: ast.AST, args: List[Any]) -> ast.AST:
    """Creates a deep copy of an AST node."""
    if isinstance(node, ast.AST):
        return ast.copy_location(copy.deepcopy(node), node)
    return node


def delete_node(root: ast.AST, args: List[Any]) -> ast.AST:
    """
    Deletes a node from the AST.
    args[0]: node to delete
    """
    if len(args) < 1:
        return root
    
    target_node = args[0]
    
    class NodeDeleter(ast.NodeTransformer):
        def visit(self, node):
            # Skip the target node entirely
            if node is target_node:
                return None
            # For nodes with body/orelse, filter out None values
            new_node = self.generic_visit(node)
            if hasattr(new_node, 'body') and isinstance(new_node.body, list):
                new_node.body = [n for n in new_node.body if n is not None]
            if hasattr(new_node, 'orelse') and isinstance(new_node.orelse, list):
                new_node.orelse = [n for n in new_node.orelse if n is not None]
            return new_node
    
    deleter = NodeDeleter()
    new_tree = deleter.visit(root)
    return new_tree


# --- Data Flow Analysis Primitives ---

def get_variable_state(node: ast.AST, args: List[Any]) -> Union[ast.AST, str]:
    """
    Gets the current state of a variable from context.
    Returns a Constant node if the value is known, or "UNKNOWN" otherwise.
    
    Args:
        node: AST node (should be a Name node)
        args: [context] where context is an AnalysisContext with variable_state_map
    """
    if len(args) > 0 and hasattr(args[0], 'variable_state_map'):
        context = args[0]
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            var_name = node.id
            if var_name in context.variable_state_map:
                return context.variable_state_map[var_name]
    return "UNKNOWN"


def update_variable_state(node: ast.AST, args: List[Any]) -> ast.AST:
    """
    Updates the state map after an assignment.
    For Assign nodes, tracks the value if it's a constant.
    
    Args:
        node: AST node (should be an Assign node)
        args: [context] where context is an AnalysisContext with variable_state_map
    """
    if len(args) > 0 and hasattr(args[0], 'variable_state_map'):
        context = args[0]
        if isinstance(node, ast.Assign) and node.targets:
            # Simple case: single target
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                var_name = node.targets[0].id
                
                # Check if the assigned value is a constant
                if isinstance(node.value, ast.Constant):
                    context.variable_state_map[var_name] = node.value
                else:
                    # Mark as unknown if not constant
                    context.variable_state_map[var_name] = "UNKNOWN"
    
    return node


def propagate_constants(root: ast.AST, args: List[Any]) -> ast.AST:
    """
    Main constant propagation transformation.
    Replaces variable references with their known constant values.
    
    Args:
        root: AST root node
        args: [context] where context is an AnalysisContext with variable_state_map
    """
    if len(args) == 0 or not hasattr(args[0], 'variable_state_map'):
        # No context provided, return unchanged
        return root
    
    context = args[0]
    
    class ConstantPropagator(ast.NodeTransformer):
        def __init__(self, context):
            self.context = context
            
        def visit_Assign(self, node):
            # First, propagate in the value expression
            node.value = self.visit(node.value)
            
            # Update state map
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                var_name = node.targets[0].id
                if isinstance(node.value, ast.Constant):
                    self.context.variable_state_map[var_name] = node.value
                else:
                    self.context.variable_state_map[var_name] = "UNKNOWN"
            
            return node
        
        def visit_Name(self, node):
            # Only replace loads, not stores
            if isinstance(node.ctx, ast.Load):
                var_name = node.id
                if var_name in self.context.variable_state_map:
                    state = self.context.variable_state_map[var_name]
                    if isinstance(state, ast.Constant):
                        # Replace with the constant value
                        return ast.copy_location(
                            ast.Constant(value=state.value),
                            node
                        )
            return node
    
    propagator = ConstantPropagator(context)
    return propagator.visit(root)


def is_all_constants_propagated(root: ast.AST, args: List[Any]) -> bool:
    """
    Checks if all possible constants have been propagated.
    Used to verify the optimization is complete.
    """
    class ConstantChecker(ast.NodeVisitor):
        def __init__(self):
            self.has_propagatable = False
            self.known_constants = {}
        
        def visit_Assign(self, node):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                var_name = node.targets[0].id
                if isinstance(node.value, ast.Constant):
                    self.known_constants[var_name] = node.value
            self.generic_visit(node)
        
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                if node.id in self.known_constants:
                    self.has_propagatable = True
    
    checker = ConstantChecker()
    checker.visit(root)
    return not checker.has_propagatable


# --- AST Traversal Primitives ---

def find_all_nodes(root: ast.AST, args: List[Any]) -> List[ast.AST]:
    """
    Finds all nodes of a specific type in the AST.
    args[0]: node type name (e.g., 'BinOp')
    """
    if not isinstance(root, ast.AST) or len(args) == 0:
        return []
    
    target_type = args[0]
    found_nodes = []
    
    class NodeFinder(ast.NodeVisitor):
        def visit(self, node):
            if node.__class__.__name__ == target_type:
                found_nodes.append(node)
            self.generic_visit(node)
    
    finder = NodeFinder()
    finder.visit(root)
    return found_nodes


def get_parent_map(root: ast.AST, args: List[Any]) -> Dict[ast.AST, ast.AST]:
    """Creates a mapping from each node to its parent."""
    parent_map = {}
    
    class ParentMapper(ast.NodeVisitor):
        def visit(self, node, parent=None):
            if parent is not None:
                parent_map[node] = parent
            for child in ast.iter_child_nodes(node):
                self.visit(child, node)
    
    if isinstance(root, ast.AST):
        mapper = ParentMapper()
        mapper.visit(root)
    
    return parent_map


# --- Complex AST Operations ---

def simplify_identity(node: ast.AST, args: List[Any]) -> ast.AST:
    """
    Simplifies identity operations in the AST.
    This is a higher-level primitive that demonstrates what we want to discover.
    """
    if not isinstance(node, ast.AST):
        return node
    
    class IdentitySimplifier(ast.NodeTransformer):
        def visit_BinOp(self, node):
            # First, recursively visit children
            self.generic_visit(node)
            
            # Check for additive identity (x + 0 or 0 + x)
            if isinstance(node.op, ast.Add):
                if isinstance(node.right, ast.Constant) and node.right.value == 0:
                    return node.left
                elif isinstance(node.left, ast.Constant) and node.left.value == 0:
                    return node.right
            
            # Check for multiplicative identity (x * 1 or 1 * x)
            elif isinstance(node.op, ast.Mult):
                if isinstance(node.right, ast.Constant) and node.right.value == 1:
                    return node.left
                elif isinstance(node.left, ast.Constant) and node.left.value == 1:
                    return node.right
            
            return node
    
    simplifier = IdentitySimplifier()
    return simplifier.visit(node)


# Create Transformation objects for the discovery engine
AST_PRIMITIVES = [
    # Evaluation
    Transformation(
        name="EVALUATE_NODE",
        operation=evaluate_node,
        input_type="ast",
        output_type="ast",
        num_args=0
    ),
    Transformation(
        name="IS_CONSTANT",
        operation=is_constant,
        input_type="ast",
        output_type="boolean",
        num_args=0
    ),
    Transformation(
        name="IS_CONSTANT_FALSE",
        operation=is_constant_false,
        input_type="ast",
        output_type="boolean",
        num_args=0
    ),
    Transformation(
        name="IS_CONSTANT_TRUE",
        operation=is_constant_true,
        input_type="ast",
        output_type="boolean",
        num_args=0
    ),
    
    # Inspection
    Transformation(
        name="GET_NODE_TYPE",
        operation=get_node_type,
        input_type="ast",
        output_type="string",
        num_args=0
    ),
    Transformation(
        name="GET_CHILDREN",
        operation=get_children,
        input_type="ast",
        output_type="ast_list",
        num_args=0
    ),
    Transformation(
        name="GET_ATTRIBUTE",
        operation=get_attribute,
        input_type="ast",
        output_type="any",
        num_args=1  # attribute name
    ),
    Transformation(
        name="GET_CHILD_AT",
        operation=get_child_at,
        input_type="ast",
        output_type="ast",
        num_args=1  # index
    ),
    
    # Pattern Matching
    Transformation(
        name="IS_BINOP_WITH_OP",
        operation=is_binop_with_op,
        input_type="ast",
        output_type="boolean",
        num_args=1  # operator name
    ),
    Transformation(
        name="IS_CONSTANT_VALUE",
        operation=is_constant_value,
        input_type="ast",
        output_type="boolean",
        num_args=1  # expected value
    ),
    Transformation(
        name="IS_POWER_OF_TWO",
        operation=is_power_of_two,
        input_type="ast",
        output_type="boolean",
        num_args=0
    ),
    Transformation(
        name="GET_LOG2",
        operation=get_log2,
        input_type="ast",
        output_type="scalar",
        num_args=0
    ),
    
    # Manipulation
    Transformation(
        name="REPLACE_NODE",
        operation=replace_node,
        input_type="ast",
        output_type="ast",
        num_args=2  # target node, replacement
    ),
    Transformation(
        name="CREATE_NAME_NODE",
        operation=create_name_node,
        input_type="any",
        output_type="ast",
        num_args=1  # identifier
    ),
    Transformation(
        name="CREATE_CONSTANT_NODE",
        operation=create_constant_node,
        input_type="any",
        output_type="ast",
        num_args=1  # value
    ),
    Transformation(
        name="CREATE_BINOP_NODE",
        operation=create_binop_node,
        input_type="any",
        output_type="ast",
        num_args=3  # op_name, left, right
    ),
    Transformation(
        name="CLONE_NODE",
        operation=clone_node,
        input_type="ast",
        output_type="ast",
        num_args=0
    ),
    Transformation(
        name="DELETE_NODE",
        operation=delete_node,
        input_type="ast",
        output_type="ast",
        num_args=1  # node to delete
    ),
    
    # Data Flow Analysis - Now accepts context as argument
    Transformation(
        name="GET_VARIABLE_STATE",
        operation=get_variable_state,
        input_type="ast",
        output_type="any",  # Can be Constant or "UNKNOWN"
        num_args=1  # context with variable_state_map
    ),
    Transformation(
        name="UPDATE_VARIABLE_STATE",
        operation=update_variable_state,
        input_type="ast",
        output_type="ast",
        num_args=1  # context with variable_state_map
    ),
    Transformation(
        name="PROPAGATE_CONSTANTS",
        operation=propagate_constants,
        input_type="ast",
        output_type="ast",
        num_args=1  # context with variable_state_map
    ),
    
    # Traversal
    Transformation(
        name="FIND_ALL_NODES",
        operation=find_all_nodes,
        input_type="ast",
        output_type="ast_list",
        num_args=1  # node type
    ),
]
# Export AST primitives
__all__ = ['AST_PRIMITIVES']
