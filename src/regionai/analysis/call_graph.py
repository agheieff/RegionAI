"""
Call graph construction for interprocedural analysis.
"""
import ast
from typing import Dict, Set, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class FunctionInfo:
    """Information about a function in the program."""
    name: str
    node: ast.FunctionDef
    parameters: List[str]
    calls: Set[str] = field(default_factory=set)  # Functions this function calls
    called_by: Set[str] = field(default_factory=set)  # Functions that call this
    
    def __hash__(self):
        return hash(self.name)


@dataclass
class CallSite:
    """Information about a specific function call."""
    caller: str  # Name of calling function
    callee: str  # Name of called function
    node: ast.Call  # The call AST node
    line_number: int
    arguments: List[ast.AST]  # Actual arguments at call site


class CallGraph:
    """
    Represents the call relationships between functions in a program.
    """
    
    def __init__(self):
        self.functions: Dict[str, FunctionInfo] = {}
        self.call_sites: List[CallSite] = []
        self.entry_points: Set[str] = set()  # Functions not called by others
        
    def add_function(self, func: ast.FunctionDef):
        """Add a function to the call graph."""
        func_info = FunctionInfo(
            name=func.name,
            node=func,
            parameters=[arg.arg for arg in func.args.args]
        )
        self.functions[func.name] = func_info
        
    def add_call(self, caller: str, callee: str, call_node: ast.Call, line: int):
        """Add a function call relationship."""
        if caller in self.functions and callee in self.functions:
            self.functions[caller].calls.add(callee)
            self.functions[callee].called_by.add(caller)
            
        call_site = CallSite(
            caller=caller,
            callee=callee,
            node=call_node,
            line_number=line,
            arguments=call_node.args
        )
        self.call_sites.append(call_site)
    
    def identify_entry_points(self):
        """Identify functions that are not called by any other function."""
        self.entry_points.clear()
        for func_name, func_info in self.functions.items():
            if not func_info.called_by:
                self.entry_points.add(func_name)
    
    def get_call_chain(self, start: str, end: str) -> Optional[List[str]]:
        """Find a call chain from start function to end function."""
        if start not in self.functions or end not in self.functions:
            return None
            
        if start == end:
            return [start]
            
        # BFS to find shortest path
        from collections import deque
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            current, path = queue.popleft()
            
            for callee in self.functions[current].calls:
                if callee == end:
                    return path + [callee]
                    
                if callee not in visited:
                    visited.add(callee)
                    queue.append((callee, path + [callee]))
        
        return None
    
    def get_recursive_functions(self) -> Set[str]:
        """Identify recursive functions (direct or indirect)."""
        recursive = set()
        
        for func_name in self.functions:
            # Check direct recursion
            if func_name in self.functions[func_name].calls:
                recursive.add(func_name)
                continue
                
            # Check indirect recursion using DFS
            visited = set()
            stack = [func_name]
            
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                
                for callee in self.functions.get(current, FunctionInfo("", None, [])).calls:
                    if callee == func_name:
                        recursive.add(func_name)
                        break
                    stack.append(callee)
        
        return recursive
    
    def topological_sort(self) -> List[str]:
        """
        Return functions in topological order (callees before callers).
        Useful for bottom-up analysis.
        """
        # Count incoming edges (called_by)
        in_degree = {}
        for func_name in self.functions:
            in_degree[func_name] = len(self.functions[func_name].called_by)
        
        # Start with functions that have no callers
        queue = [func for func, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            current = queue.pop(0)
            result.append(current)
            
            # Reduce in-degree for functions that call current
            for caller in self.functions[current].called_by:
                in_degree[caller] -= 1
                if in_degree[caller] == 0:
                    queue.append(caller)
        
        # If we didn't process all functions, there's a cycle
        if len(result) != len(self.functions):
            # Add remaining functions (part of cycles)
            for func in self.functions:
                if func not in result:
                    result.append(func)
        
        return result


class CallGraphBuilder(ast.NodeVisitor):
    """Build a call graph from an AST."""
    
    def __init__(self):
        self.call_graph = CallGraph()
        self.current_function: Optional[str] = None
        self.function_stack: List[str] = []
        
    def build(self, tree: ast.AST) -> CallGraph:
        """Build call graph from AST."""
        self.visit(tree)
        self.call_graph.identify_entry_points()
        return self.call_graph
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        # Add function to graph
        self.call_graph.add_function(node)
        
        # Track current function context
        self.function_stack.append(self.current_function)
        self.current_function = node.name
        
        # Visit function body
        self.generic_visit(node)
        
        # Restore previous context
        self.current_function = self.function_stack.pop()
    
    def visit_Call(self, node: ast.Call):
        """Visit function call."""
        # Try to identify the called function
        callee_name = None
        
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Handle method calls (simplified - just use attribute name)
            callee_name = node.func.attr
        
        # Add call relationship if we're in a function and identified callee
        if self.current_function and callee_name:
            line_number = getattr(node, 'lineno', 0)
            self.call_graph.add_call(
                self.current_function, 
                callee_name, 
                node, 
                line_number
            )
        
        self.generic_visit(node)


def build_call_graph(tree: ast.AST) -> CallGraph:
    """Build a call graph from an AST."""
    builder = CallGraphBuilder()
    return builder.build(tree)


def visualize_call_graph(graph: CallGraph) -> str:
    """Create a simple text visualization of the call graph."""
    lines = ["Call Graph:"]
    lines.append("=" * 40)
    
    # Show each function and what it calls
    for func_name in sorted(graph.functions.keys()):
        func_info = graph.functions[func_name]
        calls = sorted(func_info.calls)
        
        if calls:
            lines.append(f"{func_name} calls:")
            for callee in calls:
                lines.append(f"  → {callee}")
        else:
            lines.append(f"{func_name} (leaf function)")
        lines.append("")
    
    # Show entry points
    if graph.entry_points:
        lines.append("Entry points:")
        for entry in sorted(graph.entry_points):
            lines.append(f"  • {entry}")
        lines.append("")
    
    # Show recursive functions
    recursive = graph.get_recursive_functions()
    if recursive:
        lines.append("Recursive functions:")
        for func in sorted(recursive):
            lines.append(f"  ↻ {func}")
    
    return "\n".join(lines)