"""
Safety Containment - Isolation and restriction mechanisms.

This module provides containment mechanisms to isolate and restrict
potentially dangerous operations or behaviors.
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager
import time
import threading

logger = logging.getLogger(__name__)


class ContainmentLevel(Enum):
    """Levels of containment restriction."""
    NONE = "none"              # No containment
    MONITORING = "monitoring"   # Monitor but don't restrict
    SOFT = "soft"              # Gentle restrictions
    MEDIUM = "medium"          # Moderate restrictions  
    HARD = "hard"              # Strong restrictions
    ISOLATION = "isolation"    # Complete isolation


class ResourceType(Enum):
    """Types of resources that can be limited."""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    TIME = "time"
    API_CALLS = "api_calls"


@dataclass
class ResourceLimit:
    """Limit for a specific resource."""
    resource_type: ResourceType
    limit: float
    current_usage: float = 0.0
    enforcement: str = "soft"  # soft, hard, kill
    
    @property
    def remaining(self) -> float:
        return max(0, self.limit - self.current_usage)
        
    @property
    def is_exceeded(self) -> bool:
        return self.current_usage >= self.limit


@dataclass
class ContainmentPolicy:
    """Policy for containing operations."""
    name: str
    level: ContainmentLevel
    resource_limits: Dict[ResourceType, ResourceLimit]
    blocked_operations: Set[str]
    allowed_modules: Set[str]
    timeout: Optional[float] = None
    callback_on_violation: Optional[Callable] = None


@dataclass
class ContainmentViolation:
    """Record of a containment violation."""
    timestamp: float
    policy_name: str
    violation_type: str
    details: Dict[str, Any]
    action_taken: str


class SafetyContainment:
    """
    Safety containment system for isolating risky operations.
    
    This system provides sandboxing, resource limits, and operation
    restrictions to contain potentially dangerous behaviors.
    """
    
    def __init__(self):
        self.active_policies: Dict[str, ContainmentPolicy] = {}
        self.violations: List[ContainmentViolation] = []
        self.operation_whitelist: Set[str] = self._init_safe_operations()
        self.module_whitelist: Set[str] = self._init_safe_modules()
        self._monitors: Dict[str, threading.Thread] = {}
        self._shutdown = threading.Event()
        
    def _init_safe_operations(self) -> Set[str]:
        """Initialize set of safe operations."""
        return {
            "read", "write_log", "compute", "analyze",
            "transform", "filter", "map", "reduce",
            "sort", "search", "compare", "validate"
        }
        
    def _init_safe_modules(self) -> Set[str]:
        """Initialize set of safe modules."""
        return {
            "math", "statistics", "json", "datetime",
            "collections", "itertools", "functools",
            "typing", "dataclasses", "enum"
        }
        
    def create_policy(self, name: str, level: ContainmentLevel,
                     resource_limits: Optional[Dict[ResourceType, float]] = None,
                     blocked_operations: Optional[Set[str]] = None,
                     allowed_modules: Optional[Set[str]] = None,
                     timeout: Optional[float] = None) -> ContainmentPolicy:
        """
        Create a containment policy.
        
        Args:
            name: Policy name
            level: Containment level
            resource_limits: Resource type to limit mapping
            blocked_operations: Operations to block
            allowed_modules: Modules to allow (None = use defaults)
            timeout: Overall timeout in seconds
            
        Returns:
            Created policy
        """
        # Convert resource limits
        limits = {}
        if resource_limits:
            for rtype, limit in resource_limits.items():
                limits[rtype] = ResourceLimit(rtype, limit)
                
        # Set defaults based on level
        if blocked_operations is None:
            blocked_operations = self._get_default_blocked_ops(level)
            
        if allowed_modules is None:
            allowed_modules = self._get_default_allowed_modules(level)
            
        policy = ContainmentPolicy(
            name=name,
            level=level,
            resource_limits=limits,
            blocked_operations=blocked_operations,
            allowed_modules=allowed_modules,
            timeout=timeout
        )
        
        self.active_policies[name] = policy
        logger.info(f"Created containment policy '{name}' at level {level.value}")
        
        return policy
        
    def activate_policy(self, policy_name: str) -> bool:
        """
        Activate a containment policy.
        
        Args:
            policy_name: Name of policy to activate
            
        Returns:
            Success status
        """
        if policy_name not in self.active_policies:
            logger.error(f"Unknown policy: {policy_name}")
            return False
            
        policy = self.active_policies[policy_name]
        
        # Start resource monitors
        if policy.resource_limits:
            monitor_thread = threading.Thread(
                target=self._monitor_resources,
                args=(policy_name,),
                daemon=True
            )
            monitor_thread.start()
            self._monitors[policy_name] = monitor_thread
            
        logger.info(f"Activated containment policy '{policy_name}'")
        return True
        
    def deactivate_policy(self, policy_name: str) -> bool:
        """Deactivate a containment policy."""
        if policy_name in self._monitors:
            # Signal monitor to stop
            # In production, would need proper thread management
            logger.info(f"Stopping monitor for policy '{policy_name}'")
            
        logger.info(f"Deactivated containment policy '{policy_name}'")
        return True
        
    @contextmanager
    def contained_execution(self, policy_name: str):
        """
        Context manager for contained execution.
        
        Usage:
            with containment.contained_execution("strict_policy"):
                # Potentially dangerous code here
                pass
        """
        if policy_name not in self.active_policies:
            raise ValueError(f"Unknown policy: {policy_name}")
            
        policy = self.active_policies[policy_name]
        start_time = time.time()
        
        # Activate containment
        self.activate_policy(policy_name)
        
        try:
            # Check timeout
            if policy.timeout:
                timer = threading.Timer(
                    policy.timeout,
                    self._handle_timeout,
                    args=(policy_name,)
                )
                timer.start()
                
            yield policy
            
        except Exception as e:
            self._record_violation(
                policy_name,
                "exception",
                {"error": str(e), "type": type(e).__name__},
                "contained"
            )
            raise
            
        finally:
            # Deactivate containment
            self.deactivate_policy(policy_name)
            
            if policy.timeout:
                timer.cancel()
                
            elapsed = time.time() - start_time
            logger.info(f"Contained execution completed in {elapsed:.2f}s")
            
    def check_operation(self, operation: str, policy_name: Optional[str] = None) -> bool:
        """
        Check if an operation is allowed.
        
        Args:
            operation: Operation to check
            policy_name: Specific policy to check against
            
        Returns:
            True if allowed
        """
        # If no policy specified, check all active
        policies_to_check = []
        if policy_name:
            if policy_name in self.active_policies:
                policies_to_check.append(self.active_policies[policy_name])
        else:
            policies_to_check = list(self.active_policies.values())
            
        # Check each policy
        for policy in policies_to_check:
            if operation in policy.blocked_operations:
                self._record_violation(
                    policy.name,
                    "blocked_operation",
                    {"operation": operation},
                    "blocked"
                )
                return False
                
        return True
        
    def check_module(self, module_name: str, policy_name: Optional[str] = None) -> bool:
        """
        Check if a module import is allowed.
        
        Args:
            module_name: Module to check
            policy_name: Specific policy to check against
            
        Returns:
            True if allowed
        """
        # If no policy specified, check all active
        policies_to_check = []
        if policy_name:
            if policy_name in self.active_policies:
                policies_to_check.append(self.active_policies[policy_name])
        else:
            policies_to_check = list(self.active_policies.values())
            
        # Check each policy
        for policy in policies_to_check:
            if module_name not in policy.allowed_modules:
                self._record_violation(
                    policy.name,
                    "blocked_module",
                    {"module": module_name},
                    "blocked"
                )
                return False
                
        return True
        
    def check_resource(self, resource_type: ResourceType, amount: float,
                      policy_name: Optional[str] = None) -> bool:
        """
        Check if resource usage is allowed.
        
        Args:
            resource_type: Type of resource
            amount: Amount to use
            policy_name: Specific policy to check
            
        Returns:
            True if allowed
        """
        policies_to_check = []
        if policy_name:
            if policy_name in self.active_policies:
                policies_to_check.append(self.active_policies[policy_name])
        else:
            policies_to_check = list(self.active_policies.values())
            
        for policy in policies_to_check:
            if resource_type in policy.resource_limits:
                limit = policy.resource_limits[resource_type]
                
                if limit.current_usage + amount > limit.limit:
                    self._record_violation(
                        policy.name,
                        "resource_limit",
                        {
                            "resource": resource_type.value,
                            "requested": amount,
                            "limit": limit.limit,
                            "current": limit.current_usage
                        },
                        "blocked"
                    )
                    
                    if limit.enforcement == "hard":
                        return False
                    elif limit.enforcement == "kill":
                        raise RuntimeError(f"Resource limit exceeded: {resource_type.value}")
                        
        return True
        
    def use_resource(self, resource_type: ResourceType, amount: float,
                    policy_name: Optional[str] = None):
        """Record resource usage."""
        policies = []
        if policy_name and policy_name in self.active_policies:
            policies.append(self.active_policies[policy_name])
        else:
            policies = list(self.active_policies.values())
            
        for policy in policies:
            if resource_type in policy.resource_limits:
                policy.resource_limits[resource_type].current_usage += amount
                
    def create_sandbox(self, level: ContainmentLevel = ContainmentLevel.MEDIUM) -> Dict[str, Any]:
        """
        Create a sandboxed environment.
        
        Args:
            level: Containment level for sandbox
            
        Returns:
            Sandbox configuration
        """
        sandbox = {
            "id": f"sandbox_{int(time.time())}",
            "level": level,
            "globals": self._create_safe_globals(level),
            "locals": {},
            "import_hook": self._create_import_hook(level),
            "resource_monitor": self._create_resource_monitor(level)
        }
        
        logger.info(f"Created sandbox with level {level.value}")
        return sandbox
        
    def execute_in_sandbox(self, code: str, sandbox: Dict[str, Any],
                          timeout: Optional[float] = None) -> Any:
        """
        Execute code in a sandbox.
        
        Args:
            code: Code to execute
            sandbox: Sandbox configuration
            timeout: Execution timeout
            
        Returns:
            Execution result
        """
        # This is a simplified version - real implementation would use
        # proper sandboxing techniques like restricted execution environments
        
        try:
            # Apply restrictions
            restricted_globals = sandbox["globals"].copy()
            restricted_globals["__builtins__"] = self._create_safe_builtins(
                sandbox["level"]
            )
            
            # Execute with timeout
            if timeout:
                # In production, use proper timeout mechanism
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Execution timeout")
                    
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(timeout))
                
            try:
                result = eval(code, restricted_globals, sandbox["locals"])
                return result
            finally:
                if timeout:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                    
        except Exception as e:
            logger.error(f"Sandbox execution failed: {e}")
            raise
            
    def get_violation_report(self, last_n: Optional[int] = None) -> Dict[str, Any]:
        """Get report of containment violations."""
        violations = self.violations[-last_n:] if last_n else self.violations
        
        if not violations:
            return {"total": 0, "violations": []}
            
        # Analyze violations
        by_type = {}
        by_policy = {}
        
        for v in violations:
            by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
            by_policy[v.policy_name] = by_policy.get(v.policy_name, 0) + 1
            
        return {
            "total": len(violations),
            "by_type": by_type,
            "by_policy": by_policy,
            "recent": [
                {
                    "time": v.timestamp,
                    "policy": v.policy_name,
                    "type": v.violation_type,
                    "action": v.action_taken
                }
                for v in violations[-5:]
            ]
        }
        
    def _get_default_blocked_ops(self, level: ContainmentLevel) -> Set[str]:
        """Get default blocked operations for level."""
        blocked = set()
        
        if level >= ContainmentLevel.SOFT:
            blocked.update(["execute_system", "modify_system"])
            
        if level >= ContainmentLevel.MEDIUM:
            blocked.update(["network_access", "file_delete", "process_spawn"])
            
        if level >= ContainmentLevel.HARD:
            blocked.update(["file_write", "import_dynamic", "reflection"])
            
        if level == ContainmentLevel.ISOLATION:
            # Block almost everything except basic computation
            blocked.update(["file_read", "introspection", "state_modification"])
            
        return blocked
        
    def _get_default_allowed_modules(self, level: ContainmentLevel) -> Set[str]:
        """Get default allowed modules for level."""
        if level == ContainmentLevel.NONE:
            return set()  # No restrictions
            
        allowed = self.module_whitelist.copy()
        
        if level >= ContainmentLevel.MEDIUM:
            # Remove some modules
            allowed -= {"os", "sys", "subprocess"}
            
        if level >= ContainmentLevel.HARD:
            # Further restrictions
            allowed -= {"importlib", "inspect", "ast"}
            
        if level == ContainmentLevel.ISOLATION:
            # Minimal set
            allowed = {"math", "statistics"}
            
        return allowed
        
    def _monitor_resources(self, policy_name: str):
        """Monitor resource usage for a policy."""
        policy = self.active_policies[policy_name]
        
        while not self._shutdown.is_set():
            # Check each resource limit
            for rtype, limit in policy.resource_limits.items():
                if limit.is_exceeded:
                    self._handle_resource_violation(policy_name, rtype, limit)
                    
            time.sleep(0.1)  # Check every 100ms
            
    def _handle_timeout(self, policy_name: str):
        """Handle execution timeout."""
        self._record_violation(
            policy_name,
            "timeout",
            {"policy": policy_name},
            "terminated"
        )
        
        # In production, would forcefully terminate execution
        logger.error(f"Execution timeout for policy '{policy_name}'")
        
    def _handle_resource_violation(self, policy_name: str, 
                                 resource_type: ResourceType,
                                 limit: ResourceLimit):
        """Handle resource limit violation."""
        logger.warning(
            f"Resource limit exceeded: {resource_type.value} "
            f"({limit.current_usage}/{limit.limit})"
        )
        
        if limit.enforcement == "kill":
            # Force termination
            raise RuntimeError(f"Resource limit kill: {resource_type.value}")
            
    def _record_violation(self, policy_name: str, violation_type: str,
                        details: Dict[str, Any], action: str):
        """Record a containment violation."""
        violation = ContainmentViolation(
            timestamp=time.time(),
            policy_name=policy_name,
            violation_type=violation_type,
            details=details,
            action_taken=action
        )
        
        self.violations.append(violation)
        
        # Callback if configured
        if policy_name in self.active_policies:
            policy = self.active_policies[policy_name]
            if policy.callback_on_violation:
                policy.callback_on_violation(violation)
                
    def _create_safe_globals(self, level: ContainmentLevel) -> Dict[str, Any]:
        """Create safe global namespace."""
        # Start with minimal safe set
        safe_globals = {
            "abs": abs,
            "len": len,
            "max": max,
            "min": min,
            "sum": sum,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
        }
        
        if level <= ContainmentLevel.MEDIUM:
            # Add more functions
            safe_globals.update({
                "sorted": sorted,
                "reversed": reversed,
                "map": map,
                "filter": filter,
            })
            
        return safe_globals
        
    def _create_safe_builtins(self, level: ContainmentLevel) -> Dict[str, Any]:
        """Create safe builtins."""
        # Very restricted builtins
        safe_builtins = {
            "None": None,
            "True": True,
            "False": False,
            "abs": abs,
            "len": len,
        }
        
        # Block dangerous builtins
        blocked = ["eval", "exec", "compile", "__import__", "open"]
        
        return safe_builtins
        
    def _create_import_hook(self, level: ContainmentLevel) -> Callable:
        """Create import hook for sandbox."""
        allowed = self._get_default_allowed_modules(level)
        
        def import_hook(name, *args, **kwargs):
            if name not in allowed:
                raise ImportError(f"Import of '{name}' is not allowed")
            return __import__(name, *args, **kwargs)
            
        return import_hook
        
    def _create_resource_monitor(self, level: ContainmentLevel) -> Callable:
        """Create resource monitor for sandbox."""
        def monitor(resource_type: str, amount: float):
            # Simple monitoring - in production would track actual usage
            logger.debug(f"Resource usage: {resource_type} = {amount}")
            
        return monitor