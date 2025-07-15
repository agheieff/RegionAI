"""
Strategic planning service for goal-oriented reasoning.

The Planner is responsible for taking high-level goals and creating
concrete execution plans by selecting appropriate heuristics and
targeting relevant code artifacts.
"""

from typing import List, Optional
import logging

from ..knowledge.planning import Goal, PlanStep, ExecutionPlan
from ..knowledge.graph import WorldKnowledgeGraph, Concept
from ..knowledge.models import ReasoningKnowledgeGraph, Heuristic, FunctionArtifact
from ..knowledge.exceptions import ExponentialSearchException
from tier2.linguistics.lean_ast import Theorem, ProofState, Tactic
from .utility_updater import UtilityUpdater
from .context_resolver import ContextResolver
from .proof_runner import ProofRunner
from .proof_trace import ProofTraceRecorder
from .heuristic_registry import heuristic_registry
from ..config import RegionAIConfig


logger = logging.getLogger(__name__)


class Planner:
    """
    Creates execution plans to achieve specified goals.
    
    The Planner bridges the gap between high-level objectives and
    concrete actions by:
    1. Analyzing the goal and its target concepts
    2. Finding relevant code artifacts from the world knowledge
    3. Selecting appropriate heuristics from the reasoning knowledge
    4. Creating a sequence of steps that will achieve the goal
    """
    
    def __init__(self, utility_updater: Optional[UtilityUpdater] = None,
                 context_resolver: Optional[ContextResolver] = None,
                 config: Optional[RegionAIConfig] = None,
                 hub: Optional['KnowledgeHub'] = None):
        """Initialize the planner.
        
        Args:
            utility_updater: Optional utility updater for getting learned utilities.
                           If not provided, uses base utilities only.
            context_resolver: Optional context resolver for determining function contexts.
                            If not provided, creates a default instance.
            config: Optional configuration object
            hub: Optional KnowledgeHub for accessing learned patterns
        """
        self.utility_updater = utility_updater
        self.context_resolver = context_resolver or ContextResolver()
        self.config = config
        self.hub = hub
        
        # Cache for vectorized goal representations
        self._goal_vector_cache = {}
    
    def create_plan(self, goal: Goal, wkg: WorldKnowledgeGraph, 
                   rkg: ReasoningKnowledgeGraph, hub=None) -> ExecutionPlan:
        """
        Create an execution plan to achieve the specified goal.
        
        This implementation uses utility-driven heuristic selection:
        1. Finds all functions related to target concepts
        2. Determines the context of each function
        3. Selects the optimal heuristic based on utility scores
        4. Creates justified steps for each function-heuristic pairing
        
        Args:
            goal: The high-level objective to achieve
            wkg: World knowledge graph containing code artifacts and concepts
            rkg: Reasoning knowledge graph containing heuristics
            
        Returns:
            ExecutionPlan with steps to achieve the goal
        """
        steps = []
        seen_combinations = set()  # Track (function, heuristic) pairs to avoid duplicates
        
        # Collect all unique function artifacts
        all_artifacts = set()
        for concept in goal.target_concepts:
            function_artifacts = self._find_functions_for_concept(concept, wkg, hub)
            all_artifacts.update(function_artifacts)
        
        # For each unique function, apply all applicable heuristics
        for artifact in all_artifacts:
            # Determine the context of this function using centralized resolver
            context = self.context_resolver.determine_function_context(artifact, wkg)
            
            # Get ALL applicable heuristics, not just the best one
            applicable_heuristics = self._get_applicable_heuristics_for_context(
                context, rkg, goal.constraints.get('focus', [])
            )
            
            # Create steps for each applicable heuristic
            for heuristic in applicable_heuristics:
                # Skip if we've already planned this combination
                combo_key = (artifact.function_name, heuristic.name)
                if combo_key in seen_combinations:
                    continue
                seen_combinations.add(combo_key)
                
                # Get effective utility
                effective_utility = self._get_effective_utility(heuristic, context)
                
                # Create a detailed justification
                justification = (
                    f"Selected heuristic '{heuristic.name}' "
                    f"(Utility: {effective_utility:.2f}) "
                    f"for function '{artifact.function_name}' "
                    f"in context '{context}'"
                )
                
                step = PlanStep(
                    heuristic=heuristic,
                    target_artifact=artifact,
                    justification=justification
                )
                steps.append(step)
        
        # If no steps could be created, mark as failed
        if not steps:
            return ExecutionPlan(goal=goal, steps=[], status="FAILED")
        
        # Create and return the execution plan
        return ExecutionPlan(goal=goal, steps=steps, status="PENDING")
    
    def _find_generic_analysis_heuristic(self, rkg: ReasoningKnowledgeGraph) -> Optional[Heuristic]:
        """
        Find a generic heuristic for analyzing functions.
        
        In this initial implementation, we look for a heuristic with
        high utility that can be applied broadly. Future versions will
        select heuristics based on the specific goal.
        
        Args:
            rkg: Reasoning knowledge graph containing heuristics
            
        Returns:
            A suitable heuristic or None if not found
        """
        # Get all heuristics
        all_heuristics = []
        for node in rkg.graph.nodes():
            if isinstance(node, Heuristic):
                all_heuristics.append(node)
        
        # Sort by expected utility and find one suitable for general analysis
        all_heuristics.sort(key=lambda h: h.expected_utility, reverse=True)
        
        # Look for a generic analysis heuristic
        for heuristic in all_heuristics:
            # Check if it's a general-purpose analysis heuristic
            if any(tag in ["analysis", "general", "deep_analysis"] 
                   for tag in heuristic.applicability_conditions):
                return heuristic
            # If no specific analysis heuristic, return the highest utility one
            if heuristic.expected_utility > 0.5:
                return heuristic
        
        # If no suitable heuristic found, return None
        return None if not all_heuristics else all_heuristics[0]
    
    def _find_functions_for_concept(self, concept, wkg: WorldKnowledgeGraph, hub=None) -> List[FunctionArtifact]:
        """
        Find all function artifacts related to a concept.
        
        This searches the world knowledge graph for functions that
        manipulate or are otherwise related to the given concept.
        
        Args:
            concept: The concept to search for
            wkg: World knowledge graph containing artifacts
            
        Returns:
            List of FunctionArtifact objects related to the concept
        """
        related_functions = []
        
        # Get metadata for the concept
        metadata = wkg.get_concept_metadata(concept)
        if metadata and metadata.source_functions:
            # For each source function, find its artifact
            for func_name in metadata.source_functions:
                # Try to get the actual artifact from the hub if available
                if hub and hasattr(hub, 'function_artifacts') and func_name in hub.function_artifacts:
                    artifact = hub.function_artifacts[func_name]
                else:
                    # Create a placeholder artifact as fallback
                    artifact = FunctionArtifact(
                        function_name=func_name,
                        file_path="<unknown>",
                        semantic_fingerprint=None,
                        natural_language_context=None,
                        discovered_concepts=[concept]
                    )
                related_functions.append(artifact)
        
        return related_functions
    
    # Note: _determine_function_context method has been removed.
    # Context determination is now handled by the ContextResolver service
    # to ensure a single source of truth and prevent configuration drift.
    
    def _select_best_heuristic_for_context(self, context: str, 
                                         rkg: ReasoningKnowledgeGraph) -> Optional[Heuristic]:
        """
        Select the best heuristic for a given context based on utility scores.
        
        This method queries the reasoning knowledge graph for heuristics
        applicable to the given context and selects the one with highest utility.
        
        Args:
            context: The context string (e.g., "database-interaction")
            rkg: Reasoning knowledge graph containing heuristics
            
        Returns:
            The best heuristic for the context, or None if none found
        """
        # Get all heuristics from the graph
        all_heuristics = []
        for node in rkg.graph.nodes():
            if isinstance(node, Heuristic):
                all_heuristics.append(node)
        
        # Filter heuristics applicable to this context
        context_heuristics = []
        for heuristic in all_heuristics:
            # Check if the context matches any applicability conditions
            if any(context in condition or condition == context 
                   for condition in heuristic.applicability_conditions):
                context_heuristics.append(heuristic)
        
        # If no context-specific heuristics, look for general ones
        if not context_heuristics:
            for heuristic in all_heuristics:
                if any("general" in condition or "analysis" in condition 
                       for condition in heuristic.applicability_conditions):
                    context_heuristics.append(heuristic)
        
        # Sort by effective utility score and return the best
        if context_heuristics:
            context_heuristics.sort(
                key=lambda h: self._get_effective_utility(h, context), 
                reverse=True
            )
            return context_heuristics[0]
        
        # If still nothing found, return the highest utility heuristic overall
        if all_heuristics:
            all_heuristics.sort(
                key=lambda h: self._get_effective_utility(h, "general"), 
                reverse=True
            )
            return all_heuristics[0]
        
        return None
    
    def _get_effective_utility(self, heuristic: Heuristic, context: str) -> float:
        """
        Get the effective utility of a heuristic for a context.
        
        If a utility updater is available, use its learned utilities.
        Otherwise, use the base utility from the heuristic.
        
        Args:
            heuristic: The heuristic to query
            context: The context to check
            
        Returns:
            The effective utility value
        """
        if self.utility_updater:
            return self.utility_updater.get_effective_utility(heuristic, context)
        return heuristic.expected_utility
    
    def _get_applicable_heuristics_for_context(self, context: str, 
                                              rkg: ReasoningKnowledgeGraph,
                                              focus_areas: list = None) -> List[Heuristic]:
        """
        Get all heuristics applicable to a context, sorted by utility.
        
        Args:
            context: The context string (e.g., "database-interaction")
            rkg: Reasoning knowledge graph containing heuristics
            focus_areas: Optional list of focus areas from goal constraints
            
        Returns:
            List of applicable heuristics sorted by utility
        """
        # Get all heuristics from the graph
        all_heuristics = []
        for node in rkg.graph.nodes():
            if isinstance(node, Heuristic):
                all_heuristics.append(node)
        
        # Filter heuristics applicable to this context or general analysis
        applicable_heuristics = []
        for heuristic in all_heuristics:
            # Check if it matches the context
            context_match = any(context in condition or condition == context 
                              for condition in heuristic.applicability_conditions)
            
            # Check if it's a general analysis heuristic
            general_match = any("general" in condition or "analysis" in condition 
                              for condition in heuristic.applicability_conditions)
            
            # Check if it matches focus areas
            focus_match = True
            if focus_areas:
                focus_match = any(
                    any(focus.lower() in cond.lower() 
                        for cond in heuristic.applicability_conditions)
                    for focus in focus_areas
                )
            
            # Include if any condition is met
            if (context_match or general_match) and focus_match:
                applicable_heuristics.append(heuristic)
        
        # Sort by effective utility
        applicable_heuristics.sort(
            key=lambda h: self._get_effective_utility(h, context),
            reverse=True
        )
        
        return applicable_heuristics
    
    def attempt_proof(self, theorem: Theorem, rkg: ReasoningKnowledgeGraph,
                      trace_recorder: Optional[ProofTraceRecorder] = None) -> ExecutionPlan:
        """
        Attempt to prove a theorem with exponential safety guards.
        
        This method integrates ProofRunner to manage proof attempts safely,
        catching exponential search exceptions and updating heuristic utilities.
        
        Args:
            theorem: The theorem to prove
            rkg: Reasoning knowledge graph containing proof heuristics
            trace_recorder: Optional trace recorder for debugging
            
        Returns:
            ExecutionPlan with proof steps or failure status
        """
        # Create a proof-specific goal
        proof_concept = Concept(f"proof_{theorem.name}")
        goal = Goal(f"Prove {theorem.name}", [proof_concept])
        
        # Create ProofRunner with safety guards
        runner = ProofRunner(trace_recorder=trace_recorder, theorem=theorem)
        
        try:
            with runner:
                # Get proof-specific heuristics
                proof_heuristics = self._get_proof_heuristics(rkg)
                steps = []
                
                # Simulate proof loop (simplified for now)
                proof_state = ProofState(
                    goals=[theorem.statement],
                    hypotheses=theorem.hypotheses
                )
                
                for step_num in range(1000):  # Max iterations
                    # Check abort conditions
                    runner.check_abort()
                    
                    # Select best heuristic for current state
                    best_heuristic = self._select_best_proof_heuristic(
                        proof_state, proof_heuristics
                    )
                    
                    if not best_heuristic:
                        break
                        
                    # Track which heuristic is active
                    runner.set_current_heuristic(best_heuristic.name)
                    
                    # Create a plan step (simplified - real implementation would apply tactics)
                    step = PlanStep(
                        heuristic=best_heuristic,
                        target_artifact=None,  # No specific artifact for proofs
                        justification=f"Apply {best_heuristic.name} at step {step_num}"
                    )
                    steps.append(step)
                    
                    # Update proof state (simplified)
                    runner.update_goal_state(proof_state)
                    
                    # Record step
                    from ..language.lean_ast import Tactic, TacticType
                    dummy_tactic = Tactic(TacticType.APPLY, ["dummy"])
                    runner.record_step(dummy_tactic, success=True)
                    
                    # Check if proof is complete
                    if proof_state.completed:
                        runner.metrics.final_status = 'success'
                        return ExecutionPlan(goal=goal, steps=steps, status="COMPLETED")
                
                # If we exit the loop without completing, it's a failure
                return ExecutionPlan(goal=goal, steps=steps, status="FAILED")
                
        except ExponentialSearchException as e:
            # Log the exponential behavior
            logger.warning(f"Exponential search detected in proof of {theorem.name}: {e}")
            
            # Update utility for the responsible heuristic
            if self.utility_updater and e.context.get('current_heuristic'):
                self.utility_updater.handle_exponential_failure(
                    heuristic_name=e.context['current_heuristic'],
                    context="proof_search",
                    details=str(e)
                )
            
            # Return failed plan with diagnostic info
            return ExecutionPlan(
                goal=goal,
                steps=[],
                status="FAILED",
                failure_reason=f"Exponential search: {e}"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in proof attempt: {e}")
            return ExecutionPlan(
                goal=goal,
                steps=[],
                status="FAILED", 
                failure_reason=str(e)
            )
    
    def _get_proof_heuristics(self, rkg: ReasoningKnowledgeGraph) -> List[Heuristic]:
        """Get heuristics applicable to proof search."""
        proof_heuristics = []
        
        for node in rkg.graph.nodes():
            if isinstance(node, Heuristic):
                # Check if heuristic is applicable to proofs
                if any("proof" in cond or "theorem" in cond or "lean" in cond
                       for cond in node.applicability_conditions):
                    proof_heuristics.append(node)
        
        # Sort by utility
        proof_heuristics.sort(
            key=lambda h: self._get_effective_utility(h, "proof_search"),
            reverse=True
        )
        
        return proof_heuristics
    
    def _select_best_proof_heuristic(self, proof_state: ProofState,
                                   heuristics: List[Heuristic]) -> Optional[Heuristic]:
        """Select the best heuristic for the current proof state."""
        # Simplified selection - in reality would analyze the proof state
        # to determine which heuristic is most appropriate
        
        if not heuristics:
            return None
            
        # For now, just return the highest utility heuristic
        # Future versions will analyze goal structure, available hypotheses, etc.
        return heuristics[0]
    
    def attempt_proof(self, proof_state: ProofState, proof_runner: ProofRunner,
                     max_steps: int = 100) -> bool:
        """
        Attempt to prove a theorem using the given proof state and runner.
        
        This method is designed to work with the bootstrap orchestrator.
        It applies mathematical heuristics to generate tactics and uses
        the proof runner to execute them safely.
        
        Args:
            proof_state: Initial proof state
            proof_runner: ProofRunner instance with tactic executor
            max_steps: Maximum number of proof steps to attempt
            
        Returns:
            True if proof was completed successfully, False otherwise
        """
        # Create a list to track actions
        self.actions = []
        
        for step in range(max_steps):
            # Check if proof is complete
            if proof_state.is_complete:
                logger.info(f"Proof completed in {step} steps!")
                return True
                
            # Clear actions from previous step
            self.actions.clear()
            
            # Create context for heuristics
            context = {
                'proof_state': proof_state,
                'planner': self
            }
            
            # First, try to apply learned multi-step patterns
            learned_pattern_applied = False
            if self.hub:
                learned_patterns = self._find_learned_patterns(proof_state)
                for pattern in learned_patterns:
                    logger.info(f"Trying learned pattern: {pattern.name} - {pattern.description}")
                    proof_runner.set_current_heuristic(pattern.name)
                    
                    success = self._apply_learned_pattern(
                        pattern, proof_state, proof_runner, context
                    )
                    
                    if success:
                        learned_pattern_applied = True
                        logger.info(f"Successfully applied learned pattern: {pattern.name}")
                        break
            
            # Check if we have actions from learned pattern
            if learned_pattern_applied and self.actions:
                # Execute all tactics from the learned pattern
                for action in self.actions:
                    if action['type'] == 'apply_tactic':
                        tactic = action['tactic']
                        logger.info(f"Applying learned tactic: {tactic}")
                        
                        try:
                            # Execute tactic using proof runner
                            proof_state = proof_runner.execute_tactic(proof_state, tactic)
                            
                            # Check if error occurred
                            if proof_state.metadata.get('last_error'):
                                logger.warning(f"Learned tactic failed: {proof_state.metadata['last_error']}")
                                learned_pattern_applied = False
                                break
                                
                            # Check if proof is complete
                            if proof_state.is_complete:
                                logger.info(f"Proof completed by learned pattern!")
                                return True
                                
                        except Exception as e:
                            logger.error(f"Failed to execute learned tactic: {e}")
                            learned_pattern_applied = False
                            break
                
                # If we successfully applied the pattern, continue to next iteration
                if learned_pattern_applied:
                    continue
            
            # If no learned pattern worked, fall back to individual heuristics
            if not learned_pattern_applied:
                # Run all registered math heuristics
                math_heuristics = [
                    # Basic heuristics
                    'math.intro',
                    'math.exact', 
                    'math.apply',
                    # Extended heuristics
                    'math.split',
                    'math.left',
                    'math.right',
                    'math.cases',
                    'math.trivial',
                    'math.simp',
                    # Advanced heuristics
                    'math.and_elim_left',
                    'math.and_elim_right',
                    'math.iff_intro',
                    'math.comm',
                    'math.modus_ponens_direct',
                    'math.classical',
                    'math.rfl',
                    # Specialized heuristics
                    'math.conj_elim_implication',
                    'math.identity_biconditional',
                    'math.impl_as_disj_specialized',
                    'math.by_cases',
                    'math.constructor_identity',
                    'math.exact_hypothesis_projection',
                    'math.assumption',  # Fallback
                ]
                
                heuristic_fired = False
                for heuristic_id in math_heuristics:
                    heuristic_func = heuristic_registry.get(heuristic_id)
                    if heuristic_func:
                        # Set current heuristic in runner
                        proof_runner.set_current_heuristic(heuristic_id)
                        
                        # Execute heuristic
                        try:
                            if heuristic_func(None, context):
                                heuristic_fired = True
                        except Exception as e:
                            logger.error(f"Heuristic {heuristic_id} failed: {e}")
                
                # If no heuristic fired, we're stuck
                if not heuristic_fired or not self.actions:
                    logger.info("No applicable heuristics found")
                    return False
                
            # Sort actions by priority (if specified)
            self.actions.sort(
                key=lambda a: a.get('priority', 0.5),
                reverse=True
            )
            
            # Execute the highest priority action
            action = self.actions[0]
            if action['type'] == 'apply_tactic':
                tactic = action['tactic']
                logger.info(f"Applying tactic: {tactic}")
                
                try:
                    # Execute tactic using proof runner
                    proof_state = proof_runner.execute_tactic(proof_state, tactic)
                    
                    # Check if error occurred
                    if proof_state.metadata.get('last_error'):
                        logger.warning(f"Tactic failed: {proof_state.metadata['last_error']}")
                        
                except Exception as e:
                    logger.error(f"Failed to execute tactic: {e}")
                    # Continue to next iteration
        
        logger.info(f"Proof incomplete after {max_steps} steps")
        return False
    
    def add_action(self, action: dict):
        """
        Add an action to the planner's action list.
        
        This method is called by heuristics to propose actions.
        
        Args:
            action: Dictionary describing the action to take
        """
        if not hasattr(self, 'actions'):
            self.actions = []
        self.actions.append(action)
    
    def _find_learned_patterns(self, proof_state: ProofState) -> List[Heuristic]:
        """
        Find learned patterns that might apply to the current proof state.
        
        This uses geometric similarity to find patterns whose descriptions
        are close to the current goal in the vector space.
        
        Args:
            proof_state: Current proof state
            
        Returns:
            List of applicable learned patterns, sorted by relevance
        """
        if not self.hub:
            return []
        
        # Get the reasoning knowledge graph
        rkg = self.hub.rkg
        if not rkg:
            return []
        
        # Get current goal
        goal = proof_state.current_goal
        if not goal:
            return []
        
        # Find all mined patterns in the graph
        learned_patterns = []
        for node in rkg.graph.nodes():
            if isinstance(node, Heuristic):
                # Get metadata from the graph node
                node_data = rkg.graph.nodes[node]
                metadata = node_data.get('metadata')
                
                if metadata and hasattr(metadata, 'discovery_source') and metadata.discovery_source == 'concept_miner':
                    # Check if this pattern might apply based on the goal structure
                    # Pattern is stored in the heuristic's description
                    if self._pattern_matches_goal(node.description, goal):
                        learned_patterns.append(node)
        
        # Sort by expected utility
        learned_patterns.sort(key=lambda h: h.expected_utility, reverse=True)
        
        logger.debug(f"Found {len(learned_patterns)} potentially applicable learned patterns")
        return learned_patterns[:3]  # Return top 3 patterns
    
    def _pattern_matches_goal(self, pattern: str, goal: str) -> bool:
        """
        Check if a pattern might match the current goal structure.
        
        This is a simplified version - in production, we'd use the
        vectorized representations for similarity comparison.
        
        Args:
            pattern: The pattern string (e.g., "intro <var>; exact <hyp>")
            goal: The current goal
            
        Returns:
            True if the pattern might apply
        """
        # Extract the structure of the pattern
        tactics = pattern.split('; ')
        
        # Check for implication patterns
        if 'intro' in tactics[0] and ('→' in goal or '->' in goal):
            return True
        
        # Check for conjunction patterns
        if 'split' in pattern and ('∧' in goal or '/\\' in goal):
            return True
        
        # Check for disjunction patterns
        if ('left' in pattern or 'right' in pattern) and ('∨' in goal or '\\/' in goal):
            return True
        
        # Default to trying it if we're not sure
        return len(tactics) <= 3  # Only try short patterns
    
    def _apply_learned_pattern(self, pattern: Heuristic, proof_state: ProofState,
                              proof_runner: ProofRunner, context: dict) -> bool:
        """
        Apply a learned multi-step pattern to the current proof state.
        
        Args:
            pattern: The learned pattern heuristic
            proof_state: Current proof state
            proof_runner: Proof runner for executing tactics
            context: Context dictionary
            
        Returns:
            True if the pattern was successfully applied
        """
        # Get the tactic sequence from the pattern description
        # The pattern is encoded in the description after "Pattern: "
        pattern_str = ''
        if 'Pattern: ' in pattern.description:
            pattern_str = pattern.description.split('Pattern: ', 1)[1].strip()
        
        if not pattern_str:
            # Try to extract from the name if it contains the pattern
            if '; ' in pattern.name:
                pattern_str = pattern.name
            else:
                return False
        
        # Parse the pattern into individual tactics
        tactic_strs = pattern_str.split('; ')
        
        logger.info(f"Applying learned pattern with {len(tactic_strs)} steps")
        
        # Clear any existing actions
        self.actions.clear()
        
        # Convert pattern steps to actual tactics
        for tactic_str in tactic_strs:
            tactic = self._pattern_step_to_tactic(tactic_str, proof_state)
            if tactic:
                self.add_action({
                    'type': 'apply_tactic',
                    'tactic': tactic,
                    'heuristic': pattern.name,
                    'reasoning': f"Part of learned pattern: {pattern.description}",
                    'priority': 0.9
                })
        
        # If we successfully generated tactics, mark as successful
        return len(self.actions) > 0
    
    def _pattern_step_to_tactic(self, step: str, proof_state: ProofState) -> Optional[Tactic]:
        """
        Convert a pattern step to an actual tactic.
        
        Args:
            step: Pattern step (e.g., "intro <var>", "exact <hyp>")
            proof_state: Current proof state
            
        Returns:
            A Tactic object or None if conversion fails
        """
        from ..language.lean_ast import Tactic, TacticType
        
        parts = step.split()
        if not parts:
            return None
        
        tactic_name = parts[0]
        
        # Handle intro with variable generation
        if tactic_name == 'intro':
            # Generate a fresh variable name
            existing_names = {h.name for h in proof_state.hypotheses}
            var_name = self._generate_fresh_name('h', existing_names)
            return Tactic(TacticType.INTRO, [var_name])
        
        # Handle exact with hypothesis selection
        elif tactic_name == 'exact':
            if '<hyp>' in step:
                # Try to find a matching hypothesis
                for hyp in proof_state.hypotheses:
                    if hyp.type_expr == proof_state.current_goal:
                        return Tactic(TacticType.EXACT, [hyp.name])
                # If no exact match, try the most recent hypothesis
                if proof_state.hypotheses:
                    return Tactic(TacticType.EXACT, [proof_state.hypotheses[-1].name])
            elif '<expr>' in step:
                # This would need more sophisticated handling
                return None
        
        # Handle other simple tactics
        elif tactic_name == 'constructor':
            return Tactic(TacticType.CONSTRUCTOR, [])
        elif tactic_name == 'assumption':
            return Tactic(TacticType.ASSUMPTION, [])
        elif tactic_name == 'split':
            return Tactic(TacticType.CONSTRUCTOR, [])  # split is constructor in Lean 4
        elif tactic_name == 'simp':
            return Tactic(TacticType.SIMP, [])
        elif tactic_name in ['left', 'right', 'trivial']:
            # Custom tactics
            return Tactic(TacticType.CUSTOM, [], metadata={'raw_line': tactic_name})
        
        # Unknown tactic
        logger.warning(f"Unknown pattern step: {step}")
        return None
    
    def _generate_fresh_name(self, prefix: str, existing: set) -> str:
        """Generate a fresh variable name that doesn't conflict with existing names."""
        if prefix not in existing:
            return prefix
        
        i = 1
        while f"{prefix}{i}" in existing:
            i += 1
        return f"{prefix}{i}"