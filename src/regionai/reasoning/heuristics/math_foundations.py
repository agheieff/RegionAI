"""
Foundational mathematical heuristics for theorem proving.

This module contains the primordial heuristics that generate basic
Lean tactics for mathematical reasoning. These form the foundation
for RegionAI's mathematical problem-solving capabilities.
"""

import logging
from typing import Dict, Any
import re

from ...domains.language.lean_ast import ProofState, Tactic, TacticType
from ..heuristic_registry import heuristic_registry


logger = logging.getLogger(__name__)


# Global state for hypothesis name generation (reset between proofs)
_used_hypothesis_names = set()


def _generate_hypothesis_name(proof_state: ProofState) -> str:
    """
    Generate a fresh hypothesis name.
    
    Args:
        proof_state: The current proof state
        
    Returns:
        A fresh hypothesis name
    """
    global _used_hypothesis_names
    
    # Collect existing hypothesis names
    existing_names = {h.name for h in proof_state.hypotheses}
    existing_names.update(_used_hypothesis_names)
    
    # Try common names first
    for name in ['h', 'p', 'q', 'r', 'x', 'y', 'z']:
        if name not in existing_names:
            _used_hypothesis_names.add(name)
            return name
    
    # Generate numbered names
    for i in range(1, 100):
        name = f"h{i}"
        if name not in existing_names:
            _used_hypothesis_names.add(name)
            return name
    
    return "h_fresh"  # Fallback


@heuristic_registry.register("math.intro",
                           description="Introduce hypothesis from implication goal",
                           applicability_conditions=("math", "implication", "intro"),
                           expected_utility=0.8)
def heuristic_intro(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for the 'intro' tactic.
    
    If the current goal is an implication (p → q), this heuristic
    proposes to introduce the hypothesis p and prove q.
    
    Args:
        hub: The KnowledgeHub (not used for math heuristics)
        context: Context containing:
            - proof_state: Current ProofState
            - planner: The Planner instance to add actions
            
    Returns:
        True if tactic was proposed, False otherwise
    """
    proof_state = context.get('proof_state')
    planner = context.get('planner')
    
    if not isinstance(proof_state, ProofState) or not planner:
        logger.debug("Missing proof_state or planner in context")
        return False
    
    # Check if goal is an implication
    goal = proof_state.current_goal
    if not goal:
        logger.debug("No current goal")
        return False
    
    # Look for implication arrow
    if '→' not in goal and '->' not in goal:
        logger.debug("Goal is not an implication")
        return False
    
    # Generate a fresh hypothesis name
    hyp_name = _generate_hypothesis_name(proof_state)
    
    # Create the intro tactic
    tactic = Tactic(
        tactic_type=TacticType.INTRO,
        arguments=[hyp_name]
    )
    
    # Add action to planner
    planner.add_action({
        'type': 'apply_tactic',
        'tactic': tactic,
        'heuristic': 'math.intro',
        'reasoning': f"Goal is implication, introducing hypothesis '{hyp_name}'"
    })
    
    logger.info(f"Proposed intro tactic with hypothesis '{hyp_name}'")
    return True


def _normalize_expr(expr: str) -> str:
    """
    Normalize an expression for comparison.
    
    Args:
        expr: The expression to normalize
        
    Returns:
        Normalized expression
    """
    # Remove extra whitespace
    expr = ' '.join(expr.split())
    # Normalize arrow notation
    expr = expr.replace('->', '→')
    return expr.strip()


@heuristic_registry.register("math.exact",
                           description="Use hypothesis that matches goal exactly",
                           applicability_conditions=("math", "exact_match", "exact"),
                           expected_utility=1.0)
def heuristic_exact(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for the 'exact' tactic.
    
    If one of the hypotheses exactly matches the current goal,
    this heuristic proposes to use that hypothesis to complete the proof.
    
    Args:
        hub: The KnowledgeHub (not used for math heuristics)
        context: Context containing:
            - proof_state: Current ProofState
            - planner: The Planner instance to add actions
            
    Returns:
        True if tactic was proposed, False otherwise
    """
    proof_state = context.get('proof_state')
    planner = context.get('planner')
    
    if not isinstance(proof_state, ProofState) or not planner:
        logger.debug("Missing proof_state or planner in context")
        return False
    
    # Check if we have a goal
    goal = proof_state.current_goal
    if not goal:
        logger.debug("No current goal")
        return False
    
    # Look for hypothesis that matches the goal
    normalized_goal = _normalize_expr(goal)
    
    for hyp in proof_state.hypotheses:
        if _normalize_expr(hyp.type_expr) == normalized_goal:
            # Found exact match!
            tactic = Tactic(
                tactic_type=TacticType.EXACT,
                arguments=[hyp.name]
            )
            
            # Add action to planner with high priority
            planner.add_action({
                'type': 'apply_tactic',
                'tactic': tactic,
                'heuristic': 'math.exact',
                'reasoning': f"Hypothesis '{hyp.name}' matches goal exactly",
                'priority': 1.0  # Highest priority
            })
            
            logger.info(f"Proposed exact tactic using hypothesis '{hyp.name}'")
            return True
    
    logger.debug("No hypothesis matches the goal exactly")
    return False


@heuristic_registry.register("math.apply",
                           description="Apply implication hypothesis to reduce goal",
                           applicability_conditions=("math", "implication", "apply"),
                           expected_utility=0.7)
def heuristic_apply(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for the 'apply' tactic.
    
    If a hypothesis is an implication A → B and the current goal is B,
    this heuristic proposes to apply that hypothesis, changing the goal to A.
    
    Args:
        hub: The KnowledgeHub (not used for math heuristics)
        context: Context containing:
            - proof_state: Current ProofState
            - planner: The Planner instance to add actions
            
    Returns:
        True if tactic was proposed, False otherwise
    """
    proof_state = context.get('proof_state')
    planner = context.get('planner')
    
    if not isinstance(proof_state, ProofState) or not planner:
        logger.debug("Missing proof_state or planner in context")
        return False
    
    # Check if we have a goal
    goal = proof_state.current_goal
    if not goal:
        logger.debug("No current goal")
        return False
    
    # Normalize goal for comparison
    normalized_goal = _normalize_expr(goal)
    
    # Look for applicable implications
    best_score = 0.0
    best_hypothesis = None
    best_reasoning = "No applicable implications found"
    
    for hyp in proof_state.hypotheses:
        # Check if hypothesis is an implication
        if '→' in hyp.type_expr or '->' in hyp.type_expr:
            parts = re.split(r'→|->',  hyp.type_expr, 1)
            if len(parts) == 2:
                premise = _normalize_expr(parts[0])
                conclusion = _normalize_expr(parts[1])
                
                # Check if conclusion matches our goal
                if conclusion == normalized_goal:
                    # Score based on complexity of premise
                    # Simpler premises get higher scores
                    complexity_score = 1.0 / (1.0 + len(premise.split()))
                    score = 0.7 * complexity_score
                    
                    if score > best_score:
                        best_score = score
                        best_hypothesis = hyp
                        best_reasoning = f"Hypothesis '{hyp.name}' can be applied (conclusion matches goal)"
    
    if best_hypothesis:
        tactic = Tactic(
            tactic_type=TacticType.APPLY,
            arguments=[best_hypothesis.name]
        )
        
        # Add action to planner
        planner.add_action({
            'type': 'apply_tactic',
            'tactic': tactic,
            'heuristic': 'math.apply',
            'reasoning': best_reasoning,
            'priority': best_score
        })
        
        logger.info(f"Proposed apply tactic using hypothesis '{best_hypothesis.name}'")
        return True
    
    logger.debug("No applicable implications found")
    return False


def reset_hypothesis_names():
    """
    Reset the used hypothesis names set.
    
    This should be called between different proof attempts to ensure
    fresh hypothesis naming.
    """
    global _used_hypothesis_names
    _used_hypothesis_names.clear()
    logger.debug("Reset hypothesis name generator")