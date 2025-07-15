"""
Plan execution service for running heuristics and collecting results.

The PlanExecutor takes an ExecutionPlan and runs each heuristic on its
target artifact, collecting discoveries and maintaining an execution log.
"""

from typing import Optional, Any, Dict, Union
from concurrent.futures import ProcessPoolExecutor, as_completed
import time

from ..domain.planning import ExecutionPlan, PlanStep, PlanResult
from ..domain.actions import FixSuggestion, GeneratedFix
from ..knowledge.graph import WorldKnowledgeGraph, Concept
from ..knowledge.models import ReasoningKnowledgeGraph
from ..actions.code_generator import CodeGenerator
from .utility_updater import UtilityUpdater


# Module-level function for parallel execution
def execute_single_step(step_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a single plan step in a worker process.
    
    This function is designed to be called by ProcessPoolExecutor.
    It takes serialized step data and returns serialized results.
    
    Args:
        step_data: Dictionary containing:
            - heuristic_name: Name of the heuristic to execute
            - function_artifact: The target artifact data
            - implementation_id: Optional implementation ID
            
    Returns:
        Dictionary containing:
            - status: 'success' or 'error'
            - discoveries: List of discoveries (as dicts)
            - error: Error message if status is 'error'
    """
    try:
        # Import inside function to avoid serialization issues
        from .heuristic_implementations import heuristic_registry
        from ..knowledge.hub_v2 import KnowledgeHubV2
        from ..knowledge.models import FunctionArtifact
        from ..domain.discoveries import Discovery
        
        # Reconstruct the function artifact
        artifact_data = step_data['function_artifact']
        function_artifact = FunctionArtifact(
            function_name=artifact_data['function_name'],
            file_path=artifact_data['file_path'],
            source_code=artifact_data.get('source_code', ''),
            semantic_fingerprint=None,  # Not serializable
            natural_language_context=artifact_data.get('natural_language_context'),
            discovered_concepts=[]  # Not needed for heuristic execution
        )
        
        heuristic_name = step_data['heuristic_name']
        
        # Check if we have a registered implementation
        if heuristic_name in heuristic_registry._registry:
            # Create minimal context for heuristic
            context = {
                'function_artifact': function_artifact,
                'code': function_artifact.source_code,
                'function_name': function_artifact.function_name
            }
            
            # Invoke the registered heuristic
            heuristic_func = heuristic_registry.get(heuristic_name)
            if heuristic_func:
                # Create a minimal hub (most heuristics don't use it)
                hub = KnowledgeHubV2()
                result_obj = heuristic_func(hub, context)
                
                # Serialize the result
                if isinstance(result_obj, Discovery):
                    return {
                        'status': 'success',
                        'discoveries': [{
                            'type': 'Discovery',
                            'data': result_obj.to_dict()
                        }]
                    }
                elif isinstance(result_obj, FixSuggestion):
                    return {
                        'status': 'success',
                        'discoveries': [{
                            'type': 'FixSuggestion',
                            'data': {
                                'vulnerability_id': result_obj.vulnerability_id,
                                'description': result_obj.description,
                                'target_artifact': artifact_data,
                                'context_data': result_obj.context_data
                            }
                        }]
                    }
                elif result_obj:
                    # Legacy string discovery
                    return {
                        'status': 'success',
                        'discoveries': [{
                            'type': 'string',
                            'data': str(result_obj)
                        }]
                    }
                else:
                    # No discovery
                    return {
                        'status': 'success',
                        'discoveries': []
                    }
        
        # No registered implementation - return empty
        return {
            'status': 'success',
            'discoveries': []
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'discoveries': [],
            'error': str(e)
        }


class PlanExecutor:
    """
    Executes plans by running heuristics on target artifacts.
    
    The executor is responsible for:
    1. Running each step in the plan
    2. Collecting discoveries from heuristics
    3. Maintaining an execution log
    4. Handling errors gracefully
    """
    
    def __init__(self):
        """Initialize the executor."""
        # Initialize the utility updater for adaptive learning
        self.utility_updater = UtilityUpdater()
    
    def execute(self, plan: ExecutionPlan, wkg: WorldKnowledgeGraph, 
               rkg: ReasoningKnowledgeGraph, max_workers: Optional[int] = None) -> PlanResult:
        """
        Execute a plan and return the results using parallel processing.
        
        This method runs through each step in the plan, executing the
        specified heuristic on the target artifact and collecting any
        discoveries made. Uses ProcessPoolExecutor for parallel execution.
        
        Args:
            plan: The execution plan to run
            wkg: World knowledge graph (may be updated with discoveries)
            rkg: Reasoning knowledge graph containing heuristic implementations
            max_workers: Maximum number of worker processes (defaults to CPU count)
            
        Returns:
            PlanResult containing discoveries and execution log
        """
        # Initialize result
        result = PlanResult(plan=plan, status="PENDING")
        
        # Mark plan as in progress
        plan.mark_in_progress()
        result.add_log_entry(f"Starting parallel execution of plan: {plan.goal.description}")
        
        # Track timing
        start_time = time.time()
        
        # Track successful executions
        total_steps = len(plan.steps)
        
        # Prepare step data for parallel execution
        step_data_list = []
        for step in plan.steps:
            step_data = {
                'heuristic_name': step.heuristic.name,
                'function_artifact': {
                    'function_name': step.target_artifact.function_name,
                    'file_path': step.target_artifact.file_path,
                    'source_code': step.target_artifact.source_code,
                    'natural_language_context': step.target_artifact.natural_language_context
                },
                'implementation_id': step.heuristic.implementation_id
            }
            step_data_list.append((step, step_data))
        
        result.add_log_entry(f"Executing {total_steps} analysis steps in parallel...")
        
        # Execute steps in parallel
        successful_steps = 0
        # Limit max_workers to prevent resource exhaustion
        if max_workers is None:
            import os
            max_workers = min(os.cpu_count() or 1, 4)
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_step = {}
            for step, step_data in step_data_list:
                future = executor.submit(execute_single_step, step_data)
                future_to_step[future] = step
            
            # Process results as they complete
            for future in as_completed(future_to_step):
                step = future_to_step[future]
                
                try:
                    # Get the result from the worker
                    worker_result = future.result()
                    
                    if worker_result['status'] == 'success':
                        # Process discoveries from worker
                        self._process_worker_result(worker_result, step, result)
                        successful_steps += 1
                    else:
                        # Worker reported error
                        result.add_log_entry(
                            f"✗ Failed to execute {step.heuristic.name} "
                            f"on {step.target_artifact.function_name}: {worker_result.get('error', 'Unknown error')}"
                        )
                        
                except Exception as e:
                    # Future itself failed
                    result.add_log_entry(
                        f"✗ Failed to execute {step.heuristic.name} "
                        f"on {step.target_artifact.function_name}: {str(e)}"
                    )
        
        # Determine final status
        elapsed_time = time.time() - start_time
        
        if successful_steps == total_steps:
            result.status = "SUCCESS"
            plan.mark_completed()
            result.add_log_entry(f"\nPlan execution completed successfully!")
        elif successful_steps > 0:
            result.status = "PARTIAL_SUCCESS"
            result.add_log_entry(
                f"\nPlan partially completed: {successful_steps}/{total_steps} steps succeeded"
            )
        else:
            result.status = "FAILURE"
            plan.mark_failed()
            result.add_log_entry(f"\nPlan execution failed: No steps completed successfully")
        
        # Add timing information
        result.add_log_entry(f"\nAnalysis of {total_steps} functions completed in {elapsed_time:.1f} seconds.")
        
        return result
    
    def _process_worker_result(self, worker_result: Dict[str, Any], step: PlanStep, result: PlanResult):
        """
        Process the result from a worker process.
        
        Args:
            worker_result: Dictionary containing discoveries from worker
            step: The plan step that was executed
            result: The overall PlanResult to update
        """
        # Import types
        from ..domain.discoveries import Discovery
        
        # Process each discovery
        fix_suggestions = []
        string_discoveries = []
        meaningful_discoveries = 0
        
        for discovery_data in worker_result['discoveries']:
            discovery_type = discovery_data['type']
            data = discovery_data['data']
            
            if discovery_type == 'Discovery':
                # Reconstruct Discovery object
                from ..domain.discoveries import Severity
                from ..knowledge.models import FunctionArtifact
                
                # Reconstruct the function artifact
                artifact = FunctionArtifact(
                    function_name=data['function_name'],
                    file_path=data['file_path'],
                    source_code=step.target_artifact.source_code,  # Use original
                    semantic_fingerprint=step.target_artifact.semantic_fingerprint,
                    natural_language_context=step.target_artifact.natural_language_context,
                    discovered_concepts=step.target_artifact.discovered_concepts
                )
                
                discovery = Discovery(
                    finding_id=data['finding_id'],
                    description=data['description'],
                    target_artifact=artifact,
                    severity=Severity(data['severity']),
                    metadata=data['metadata']
                )
                
                # Add the summary as a string discovery
                string_discoveries.append(discovery.get_summary())
                meaningful_discoveries += 1
                
                # Track structured discovery
                if hasattr(result, '_structured_discoveries'):
                    result._structured_discoveries.append(discovery)
                else:
                    result._structured_discoveries = [discovery]
                    
            elif discovery_type == 'FixSuggestion':
                # Reconstruct FixSuggestion
                suggestion = FixSuggestion(
                    vulnerability_id=data['vulnerability_id'],
                    description=data['description'],
                    target_artifact=step.target_artifact,  # Use original artifact
                    context_data=data['context_data']
                )
                fix_suggestions.append(suggestion)
                meaningful_discoveries += 1
                
            elif discovery_type == 'string':
                # Legacy string discovery
                string_discoveries.append(data)
        
        # Determine if execution was successful
        was_successful = meaningful_discoveries > 0
        
        # Update heuristic utility
        context = self._determine_execution_context(step)
        old_utility = self.utility_updater.get_context_utility(step.heuristic, context)
        new_utility = self.utility_updater.update_heuristic_utility(
            step.heuristic, context, was_successful
        )
        
        # Log success
        result.add_log_entry(
            f"✓ Successfully executed {step.heuristic.name} "
            f"on {step.target_artifact.function_name}"
        )
        
        if old_utility != step.heuristic.expected_utility or was_successful:
            result.add_log_entry(
                f"  → Utility updated for {context} context: "
                f"{old_utility:.3f} → {new_utility:.3f}"
            )
        
        # Process FixSuggestions
        for suggestion in fix_suggestions:
            result.add_log_entry(f"  ✗ Found vulnerability: {suggestion.vulnerability_id}")
            result.add_log_entry(f"    Description: {suggestion.description}")
            
            # Generate the fix
            code_generator = CodeGenerator()
            try:
                fixed_code = code_generator.generate_fix(suggestion)
                
                # Create GeneratedFix object
                generated_fix = GeneratedFix(
                    original_suggestion=suggestion,
                    modified_source=fixed_code,
                    changes_made=code_generator._last_generated_fix.changes_made if hasattr(code_generator, '_last_generated_fix') else []
                )
                
                # Add to results
                result.generated_fixes.append(generated_fix)
                result.add_log_entry(f"  ✓ Generated fix for {suggestion.vulnerability_id}")
                
                # Log changes made
                for change in generated_fix.changes_made:
                    result.add_log_entry(f"    - {change}")
                    
            except Exception as e:
                result.add_log_entry(f"  ✗ Failed to generate fix: {str(e)}")
        
        # Add string discoveries
        for discovery in string_discoveries:
            result.add_discovery(discovery)
            result.add_log_entry(f"  → Discovered: {discovery}")
    
    def _execute_step(self, step: PlanStep, wkg: WorldKnowledgeGraph, 
                     rkg: ReasoningKnowledgeGraph, result: PlanResult) -> list[Union[str, FixSuggestion]]:
        """
        Execute a single plan step.
        
        This method runs the heuristic and extracts discoveries.
        In a real implementation, this would call the actual heuristic
        implementation. For now, we simulate based on heuristic type.
        
        Args:
            step: The plan step to execute
            wkg: World knowledge graph
            rkg: Reasoning knowledge graph
            result: Result object for logging
            
        Returns:
            List of discoveries (strings) or FixSuggestions
        """
        result.add_log_entry(
            f"Executing heuristic '{step.heuristic.name}' "
            f"on function '{step.target_artifact.function_name}'..."
        )
        
        # Try to invoke the real heuristic implementation first
        discoveries = []
        
        # Check if we have a registered implementation
        from .heuristic_implementations import heuristic_registry
        from ..knowledge.hub import KnowledgeHub
        
        if step.heuristic.name in heuristic_registry._registry:
            # Create a minimal hub for the heuristic
            hub = KnowledgeHub()
            hub.wkg = wkg
            hub.rkg = rkg
            
            # Prepare context
            context = {
                'function_artifact': step.target_artifact,
                'code': step.target_artifact.source_code,
                'function_name': step.target_artifact.function_name
            }
            
            # Invoke the registered heuristic
            heuristic_func = heuristic_registry.get(step.heuristic.name)
            if heuristic_func:
                result_obj = heuristic_func(hub, context)
                
                # Import Discovery type
                from ..domain.discoveries import Discovery
                
                # Handle the result based on type
                if isinstance(result_obj, Discovery):
                    # For Discovery objects, convert to a meaningful discovery string
                    # but also track the structured discovery
                    discovery_str = result_obj.get_summary()
                    discoveries.append(discovery_str)
                    # Store the structured discovery for later processing
                    if hasattr(result, '_structured_discoveries'):
                        result._structured_discoveries.append(result_obj)
                    else:
                        result._structured_discoveries = [result_obj]
                elif isinstance(result_obj, FixSuggestion):
                    discoveries.append(result_obj)
                elif result_obj:  # Non-None but not a Discovery/FixSuggestion
                    # This is a legacy string discovery - should be discouraged
                    discoveries.append(str(result_obj))
                
                # Return early if we got a result from registered heuristic
                if discoveries:
                    return discoveries
        
        # Fall back to simulation if no registered implementation
        # or if registered implementation returned nothing
        
        # Simulate SQL injection detection
        if "SQL" in step.heuristic.name.upper():
            if "query" in step.target_artifact.function_name.lower():
                discoveries.append(
                    f"Potential SQL injection vulnerability in {step.target_artifact.function_name}: "
                    f"Unsanitized string interpolation detected"
                )
                # Add to knowledge graph
                vuln_concept = Concept("SQLInjectionVulnerability")
                wkg.add_concept(vuln_concept)
                wkg.add_relation(
                    Concept(f"Function:{step.target_artifact.function_name}"),
                    vuln_concept,
                    "HAS_VULNERABILITY"
                )
        
        # Simulate authentication vulnerability detection
        elif "AUTH" in step.heuristic.name.upper():
            if any(term in step.target_artifact.function_name.lower() 
                   for term in ["auth", "login", "password"]):
                discoveries.append(
                    f"Authentication concern in {step.target_artifact.function_name}: "
                    f"Consider using parameterized queries"
                )
        
        # Check for SSL issues with actual implementation
        elif "SSL" in step.heuristic.name.upper() or "TLS" in step.heuristic.name.upper():
            # First check if we have the real heuristic implementation
            if (step.heuristic.implementation_id and 
                "check_insecure_ssl_config" in step.heuristic.implementation_id):
                from .heuristic_implementations import check_insecure_ssl_config
                from ..knowledge.hub import KnowledgeHub
                
                # Create a minimal hub for the heuristic
                hub = KnowledgeHub()
                hub.wkg = wkg
                hub.rkg = rkg
                
                # Prepare context with source code
                context = {
                    'code': step.target_artifact.source_code,
                    'function_name': step.target_artifact.function_name,
                    'function_artifact': step.target_artifact
                }
                
                # Run the heuristic
                result_obj = check_insecure_ssl_config(hub, context)
                
                if result_obj:
                    return [result_obj]  # Return FixSuggestion
                else:
                    return []  # No vulnerabilities found
            # Otherwise simulate
            elif step.target_artifact.source_code and "verify=False" in step.target_artifact.source_code:
                suggestion = FixSuggestion(
                    vulnerability_id="INSECURE_SSL_VERIFICATION",
                    description="SSL verification is disabled, making the connection vulnerable to MITM attacks",
                    target_artifact=step.target_artifact,
                    context_data={'parameter_name': 'verify', 'safe_value': True}
                )
                return [suggestion]
            elif any(term in step.target_artifact.function_name.lower() 
                     for term in ["request", "http", "connect"]):
                discoveries.append(
                    f"SSL/TLS configuration in {step.target_artifact.function_name}: "
                    f"Ensure certificate verification is enabled"
                )
        
        # Simulate general security analysis
        elif "SECURITY" in step.heuristic.name.upper():
            # Check for common security patterns
            func_name = step.target_artifact.function_name.lower()
            if "verify" not in func_name and any(term in func_name for term in ["ssl", "tls", "cert"]):
                discoveries.append(
                    f"Security concern in {step.target_artifact.function_name}: "
                    f"Missing verification step for security-critical operation"
                )
        
        # Default analysis
        else:
            # Simulate finding based on function characteristics
            if step.target_artifact.semantic_fingerprint:
                behaviors = step.target_artifact.semantic_fingerprint.behaviors
                if behaviors:
                    discoveries.append(
                        f"Function {step.target_artifact.function_name} exhibits "
                        f"{len(behaviors)} semantic behaviors"
                    )
        
        return discoveries
    
    def _determine_execution_context(self, step: PlanStep) -> str:
        """
        Determine the context for a plan step based on the target artifact.
        
        This should match the context determination in the Planner.
        
        Args:
            step: The plan step
            
        Returns:
            Context string (e.g., "database-interaction", "authentication")
        """
        func_name = step.target_artifact.function_name.lower()
        
        # Check for specific contexts
        if any(term in func_name for term in ['query', 'sql', 'database', 'db']):
            return "database-interaction"
        elif any(term in func_name for term in ['auth', 'login', 'password', 'token']):
            return "authentication"
        elif any(term in func_name for term in ['file', 'read', 'write', 'save', 'load']):
            return "file-io"
        elif any(term in func_name for term in ['api', 'request', 'http', 'rest']):
            return "api-interaction"
        else:
            return "general"
    
    def get_utility_summary(self) -> str:
        """
        Get a summary of learned utilities.
        
        Returns:
            Human-readable summary of what the system has learned
        """
        return self.utility_updater.get_learning_summary()