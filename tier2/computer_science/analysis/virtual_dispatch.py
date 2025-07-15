"""
Virtual method resolution for handling dynamic dispatch.

This module provides class hierarchy analysis and virtual method resolution
to handle polymorphic calls in object-oriented Python code.
"""
import ast
from typing import Dict, Set, Optional, List, Tuple
from dataclasses import dataclass, field

from .pointer_analysis import HeapObject


@dataclass
class ClassInfo:
    """Information about a class definition."""
    name: str
    bases: List[str]  # Direct base classes
    methods: Dict[str, ast.FunctionDef]  # Method name -> AST
    attributes: Set[str]  # Class attributes
    mro: List[str] = field(default_factory=list)  # Method resolution order
    
    def get_method(self, method_name: str) -> Optional[ast.FunctionDef]:
        """Get method following MRO."""
        for cls_name in self.mro:
            if method_name in self.methods:
                return self.methods[method_name]
        return None


class ClassHierarchyAnalyzer:
    """
    Analyzes class hierarchy to support virtual method resolution.
    
    This analyzer builds a class hierarchy graph and computes
    method resolution order (MRO) for each class.
    """
    
    def __init__(self):
        """Initialize class hierarchy analyzer."""
        self.classes: Dict[str, ClassInfo] = {}
        self.inheritance_graph: Dict[str, Set[str]] = {}  # child -> parents
        
    def analyze_module(self, tree: ast.AST):
        """
        Analyze module to extract class hierarchy.
        
        Args:
            tree: AST of the module
        """
        # First pass: collect all classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._analyze_class(node)
        
        # Second pass: compute MROs
        for class_name in self.classes:
            self._compute_mro(class_name)
    
    def _analyze_class(self, class_node: ast.ClassDef):
        """Analyze a single class definition."""
        class_name = class_node.name
        
        # Extract base classes
        bases = []
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                # Handle module.Class style
                bases.append(base.attr)
        
        # Extract methods and attributes
        methods = {}
        attributes = set()
        
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                methods[item.name] = item
            elif isinstance(item, ast.Assign):
                # Class attributes
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.add(target.id)
        
        # Create class info
        class_info = ClassInfo(
            name=class_name,
            bases=bases,
            methods=methods,
            attributes=attributes
        )
        
        self.classes[class_name] = class_info
        self.inheritance_graph[class_name] = set(bases)
    
    def _compute_mro(self, class_name: str):
        """
        Compute method resolution order using C3 linearization.
        
        This is a simplified version that handles basic cases.
        """
        if class_name not in self.classes:
            return
        
        class_info = self.classes[class_name]
        if class_info.mro:  # Already computed
            return
        
        # Simple MRO: class itself, then bases in order, then object
        mro = [class_name]
        
        for base in class_info.bases:
            if base in self.classes:
                self._compute_mro(base)  # Ensure base MRO is computed
                base_mro = self.classes[base].mro
                for cls in base_mro:
                    if cls not in mro:
                        mro.append(cls)
        
        # Add object if not already there
        if 'object' not in mro:
            mro.append('object')
        
        class_info.mro = mro
    
    def get_subclasses(self, class_name: str) -> Set[str]:
        """Get all subclasses of a class."""
        subclasses = set()
        
        for cls, bases in self.inheritance_graph.items():
            if class_name in bases:
                subclasses.add(cls)
                # Recursively add subclasses
                subclasses.update(self.get_subclasses(cls))
        
        return subclasses
    
    def get_class_of_object(self, obj: HeapObject) -> Optional[str]:
        """
        Get the class of a heap object.
        
        Args:
            obj: Heap object
            
        Returns:
            Class name if known, None otherwise
        """
        # Use type information from heap object
        if obj.type_name and obj.type_name in self.classes:
            return obj.type_name
        return None


class VirtualMethodResolver:
    """
    Resolves virtual method calls using class hierarchy and pointer analysis.
    
    This resolver determines which concrete methods may be called
    at each call site based on the possible types of the receiver.
    """
    
    def __init__(self, class_hierarchy: ClassHierarchyAnalyzer,
                 pointer_analysis):
        """
        Initialize virtual method resolver.
        
        Args:
            class_hierarchy: Class hierarchy information
            pointer_analysis: Pointer analysis results
        """
        self.class_hierarchy = class_hierarchy
        self.pointer_analysis = pointer_analysis
        
    def resolve_method_call(self, call_expr: ast.Call,
                           receiver_var: str,
                           method_name: str,
                           current_function: Optional[str] = None) -> Set[Tuple[str, ast.FunctionDef]]:
        """
        Resolve a virtual method call to possible targets.
        
        Args:
            call_expr: The call expression
            receiver_var: Variable name of the receiver object
            method_name: Name of the method being called
            current_function: Current function context
            
        Returns:
            Set of (class_name, method_ast) tuples for possible targets
        """
        # Get objects that receiver may point to
        pointed_objs = self.pointer_analysis.get_pointed_objects(
            receiver_var, current_function
        )
        
        possible_targets = set()
        
        for obj in pointed_objs:
            # Get class of the object
            class_name = self.class_hierarchy.get_class_of_object(obj)
            if not class_name:
                # Unknown type - be conservative
                # Could add all classes with this method
                continue
            
            # Get the method from this class (following MRO)
            class_info = self.class_hierarchy.classes.get(class_name)
            if class_info:
                method = class_info.get_method(method_name)
                if method:
                    # Find which class actually defines this method
                    for cls_name in class_info.mro:
                        if cls_name in self.class_hierarchy.classes:
                            cls = self.class_hierarchy.classes[cls_name]
                            if method_name in cls.methods:
                                possible_targets.add((cls_name, cls.methods[method_name]))
                                break
        
        return possible_targets
    
    def resolve_field_access(self, attr_expr: ast.Attribute,
                           receiver_var: str,
                           field_name: str,
                           current_function: Optional[str] = None) -> Set[Tuple[str, str]]:
        """
        Resolve field access to possible class attributes.
        
        Args:
            attr_expr: Attribute access expression
            receiver_var: Variable name of the receiver
            field_name: Field being accessed
            current_function: Current function context
            
        Returns:
            Set of (class_name, field_type) tuples
        """
        pointed_objs = self.pointer_analysis.get_pointed_objects(
            receiver_var, current_function
        )
        
        possible_fields = set()
        
        for obj in pointed_objs:
            class_name = self.class_hierarchy.get_class_of_object(obj)
            if class_name and class_name in self.class_hierarchy.classes:
                class_info = self.class_hierarchy.classes[class_name]
                
                # Check if field is defined in this class or bases
                for cls_name in class_info.mro:
                    if cls_name in self.class_hierarchy.classes:
                        cls = self.class_hierarchy.classes[cls_name]
                        if field_name in cls.attributes:
                            # Found field definition
                            # Could enhance with type information
                            possible_fields.add((cls_name, "unknown"))
                            break
        
        return possible_fields
    
    def get_possible_receivers(self, method_name: str) -> Set[str]:
        """
        Get all classes that could be receivers of a method.
        
        Args:
            method_name: Method name
            
        Returns:
            Set of class names that have this method
        """
        receivers = set()
        
        for class_name, class_info in self.class_hierarchy.classes.items():
            if any(method_name in self.class_hierarchy.classes.get(cls, ClassInfo("", [], {}, set())).methods
                   for cls in class_info.mro):
                receivers.add(class_name)
        
        return receivers


class EnhancedCallAnalyzer:
    """
    Enhanced call analyzer that handles virtual dispatch.
    
    Integrates with interprocedural analysis to handle
    polymorphic calls precisely.
    """
    
    def __init__(self, virtual_resolver: VirtualMethodResolver):
        """Initialize enhanced call analyzer."""
        self.virtual_resolver = virtual_resolver
        
    def analyze_call(self, call_expr: ast.Call,
                    current_function: Optional[str] = None) -> Set[str]:
        """
        Analyze a call to determine possible targets.
        
        Args:
            call_expr: Call expression
            current_function: Current function context
            
        Returns:
            Set of possible target function names
        """
        if isinstance(call_expr.func, ast.Name):
            # Direct function call
            return {call_expr.func.id}
        
        elif isinstance(call_expr.func, ast.Attribute):
            # Method call: obj.method()
            if isinstance(call_expr.func.value, ast.Name):
                receiver_var = call_expr.func.value.id
                method_name = call_expr.func.attr
                
                # Resolve virtual call
                targets = self.virtual_resolver.resolve_method_call(
                    call_expr, receiver_var, method_name, current_function
                )
                
                # Extract function names
                # Format as ClassName.method_name for disambiguation
                target_names = set()
                for class_name, method_ast in targets:
                    target_names.add(f"{class_name}.{method_name}")
                
                return target_names
        
        # Unknown call type
        return set()