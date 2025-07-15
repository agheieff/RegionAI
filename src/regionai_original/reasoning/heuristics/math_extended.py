"""
Extended mathematical heuristics for theorem proving.

This module contains additional heuristics for handling conjunction,
disjunction, negation, and other logical operations that go beyond
the basic intro/exact/apply tactics.
"""

import logging
from typing import Dict, Any
import re

from tier2.linguistics.lean_ast import ProofState, Tactic, TacticType
from ..heuristic_registry import heuristic_registry


logger = logging.getLogger(__name__)


def _normalize_expr(expr: str) -> str:
    """Normalize an expression for comparison."""
    expr = ' '.join(expr.split())
    expr = expr.replace('->', '→')
    return expr.strip()


@heuristic_registry.register("math.split",
                           description="Split conjunction goals into subgoals",
                           applicability_conditions=("math", "conjunction", "split"),
                           expected_utility=0.8)
def heuristic_split(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for the 'split' tactic (constructor in Lean 4).
    
    If the goal is a conjunction (p ∧ q), split it into two subgoals:
    one to prove p and another to prove q.
    
    Args:
        hub: The KnowledgeHub (not used for math heuristics)
        context: Context containing proof_state and planner
        
    Returns:
        True if tactic was proposed, False otherwise
    """
    proof_state = context.get('proof_state')
    planner = context.get('planner')
    
    if not isinstance(proof_state, ProofState) or not planner:
        return False
    
    goal = proof_state.current_goal
    if not goal:
        return False
    
    # Check if goal is a conjunction
    if '∧' in goal or '/\\' in goal:
        # In Lean 4, we use 'constructor' to split conjunctions
        tactic = Tactic(
            tactic_type=TacticType.CONSTRUCTOR,
            arguments=[]
        )
        
        planner.add_action({
            'type': 'apply_tactic',
            'tactic': tactic,
            'heuristic': 'math.split',
            'reasoning': "Goal is conjunction, splitting into subgoals",
            'priority': 0.8
        })
        
        logger.info("Proposed constructor tactic to split conjunction")
        return True
    
    return False


@heuristic_registry.register("math.left",
                           description="Choose left side of disjunction goal",
                           applicability_conditions=("math", "disjunction", "left"),
                           expected_utility=0.6)
def heuristic_left(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for choosing the left side of a disjunction.
    
    If the goal is a disjunction (p ∨ q) and we have evidence for p,
    choose to prove the left side.
    
    Args:
        hub: The KnowledgeHub (not used for math heuristics)
        context: Context containing proof_state and planner
        
    Returns:
        True if tactic was proposed, False otherwise
    """
    proof_state = context.get('proof_state')
    planner = context.get('planner')
    
    if not isinstance(proof_state, ProofState) or not planner:
        return False
    
    goal = proof_state.current_goal
    if not goal:
        return False
    
    # Check if goal is a disjunction
    if '∨' in goal or '\\/' in goal:
        # Extract left and right sides
        parts = re.split(r'∨|\\/', goal, 1)
        if len(parts) == 2:
            left_side = _normalize_expr(parts[0])
            
            # Check if we can prove the left side
            for hyp in proof_state.hypotheses:
                if _normalize_expr(hyp.type_expr) == left_side:
                    # We can prove left side directly
                    # Use custom tactic for left choice
                    tactic = Tactic(
                        tactic_type=TacticType.CUSTOM,
                        arguments=[],
                        metadata={'raw_line': 'left'}
                    )
                    
                    planner.add_action({
                        'type': 'apply_tactic',
                        'tactic': tactic,
                        'heuristic': 'math.left',
                        'reasoning': f"Choosing left side of disjunction (have evidence for {left_side})",
                        'priority': 0.9
                    })
                    
                    logger.info("Proposed left tactic for disjunction")
                    return True
    
    return False


@heuristic_registry.register("math.right",
                           description="Choose right side of disjunction goal",
                           applicability_conditions=("math", "disjunction", "right"),
                           expected_utility=0.6)
def heuristic_right(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for choosing the right side of a disjunction.
    
    If the goal is a disjunction (p ∨ q) and we have evidence for q,
    choose to prove the right side.
    
    Args:
        hub: The KnowledgeHub (not used for math heuristics)
        context: Context containing proof_state and planner
        
    Returns:
        True if tactic was proposed, False otherwise
    """
    proof_state = context.get('proof_state')
    planner = context.get('planner')
    
    if not isinstance(proof_state, ProofState) or not planner:
        return False
    
    goal = proof_state.current_goal
    if not goal:
        return False
    
    # Check if goal is a disjunction
    if '∨' in goal or '\\/' in goal:
        # Extract left and right sides
        parts = re.split(r'∨|\\/', goal, 1)
        if len(parts) == 2:
            right_side = _normalize_expr(parts[1])
            
            # Check if we can prove the right side
            for hyp in proof_state.hypotheses:
                if _normalize_expr(hyp.type_expr) == right_side:
                    # We can prove right side directly
                    # Use custom tactic for right choice
                    tactic = Tactic(
                        tactic_type=TacticType.CUSTOM,
                        arguments=[],
                        metadata={'raw_line': 'right'}
                    )
                    
                    planner.add_action({
                        'type': 'apply_tactic',
                        'tactic': tactic,
                        'heuristic': 'math.right',
                        'reasoning': f"Choosing right side of disjunction (have evidence for {right_side})",
                        'priority': 0.9
                    })
                    
                    logger.info("Proposed right tactic for disjunction")
                    return True
    
    return False


@heuristic_registry.register("math.cases",
                           description="Case analysis on disjunction hypothesis",
                           applicability_conditions=("math", "disjunction", "cases"),
                           expected_utility=0.7)
def heuristic_cases(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for case analysis on a disjunction.
    
    If we have a hypothesis that is a disjunction (p ∨ q),
    we can do case analysis to prove the goal.
    
    Args:
        hub: The KnowledgeHub (not used for math heuristics)
        context: Context containing proof_state and planner
        
    Returns:
        True if tactic was proposed, False otherwise
    """
    proof_state = context.get('proof_state')
    planner = context.get('planner')
    
    if not isinstance(proof_state, ProofState) or not planner:
        return False
    
    # Look for disjunction hypotheses
    for hyp in proof_state.hypotheses:
        if '∨' in hyp.type_expr or '\\/' in hyp.type_expr:
            # Found a disjunction hypothesis
            tactic = Tactic(
                tactic_type=TacticType.CASES,
                arguments=[hyp.name]
            )
            
            planner.add_action({
                'type': 'apply_tactic',
                'tactic': tactic,
                'heuristic': 'math.cases',
                'reasoning': f"Case analysis on disjunction hypothesis '{hyp.name}'",
                'priority': 0.7
            })
            
            logger.info(f"Proposed cases tactic on hypothesis '{hyp.name}'")
            return True
    
    return False


@heuristic_registry.register("math.assumption",
                           description="Try assumption tactic when stuck",
                           applicability_conditions=("math", "general", "assumption"),
                           expected_utility=0.5)
def heuristic_assumption(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for the 'assumption' tactic.
    
    This is a fallback tactic that tries to find a hypothesis
    that matches the goal exactly. It's more general than 'exact'
    as it searches through all hypotheses automatically.
    
    Args:
        hub: The KnowledgeHub (not used for math heuristics)
        context: Context containing proof_state and planner
        
    Returns:
        True if tactic was proposed, False otherwise
    """
    proof_state = context.get('proof_state')
    planner = context.get('planner')
    
    if not isinstance(proof_state, ProofState) or not planner:
        return False
    
    goal = proof_state.current_goal
    if not goal:
        return False
    
    # Only use assumption as a fallback when other tactics haven't fired
    # This prevents it from interfering with more specific tactics
    if hasattr(planner, 'actions') and planner.actions:
        return False
    
    # Try assumption tactic
    tactic = Tactic(
        tactic_type=TacticType.ASSUMPTION,
        arguments=[]
    )
    
    planner.add_action({
        'type': 'apply_tactic',
        'tactic': tactic,
        'heuristic': 'math.assumption',
        'reasoning': "Trying assumption tactic as fallback",
        'priority': 0.3  # Low priority
    })
    
    logger.info("Proposed assumption tactic as fallback")
    return True


@heuristic_registry.register("math.trivial",
                           description="Handle trivial goals like True",
                           applicability_conditions=("math", "trivial", "trivial"),
                           expected_utility=1.0)
def heuristic_trivial(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for trivial goals.
    
    Some goals like 'True' or 'p ∧ True' have trivial proofs.
    
    Args:
        hub: The KnowledgeHub (not used for math heuristics)
        context: Context containing proof_state and planner
        
    Returns:
        True if tactic was proposed, False otherwise
    """
    proof_state = context.get('proof_state')
    planner = context.get('planner')
    
    if not isinstance(proof_state, ProofState) or not planner:
        return False
    
    goal = proof_state.current_goal
    if not goal:
        return False
    
    # Check for trivial goals
    if goal.strip() == "True":
        # Use custom tactic for trivial
        tactic = Tactic(
            tactic_type=TacticType.CUSTOM,
            arguments=[],
            metadata={'raw_line': 'trivial'}
        )
        
        planner.add_action({
            'type': 'apply_tactic',
            'tactic': tactic,
            'heuristic': 'math.trivial',
            'reasoning': "Goal is True, using trivial",
            'priority': 1.0
        })
        
        logger.info("Proposed trivial tactic for True goal")
        return True
    
    return False


@heuristic_registry.register("math.simp",
                           description="Simplify complex expressions",
                           applicability_conditions=("math", "simplification", "simp"),
                           expected_utility=0.6)
def heuristic_simp(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for the 'simp' tactic.
    
    Use simplification for goals involving True, False, or
    complex expressions that can be simplified.
    
    Args:
        hub: The KnowledgeHub (not used for math heuristics)
        context: Context containing proof_state and planner
        
    Returns:
        True if tactic was proposed, False otherwise
    """
    proof_state = context.get('proof_state')
    planner = context.get('planner')
    
    if not isinstance(proof_state, ProofState) or not planner:
        return False
    
    goal = proof_state.current_goal
    if not goal:
        return False
    
    # Use simp for goals involving True/False or identity operations
    simplifiable_patterns = [
        'True', 'False',
        '∧ True', 'True ∧',
        '∨ False', 'False ∨',
        '¬¬',  # Double negation
    ]
    
    for pattern in simplifiable_patterns:
        if pattern in goal:
            tactic = Tactic(
                tactic_type=TacticType.SIMP,
                arguments=[]
            )
            
            planner.add_action({
                'type': 'apply_tactic',
                'tactic': tactic,
                'heuristic': 'math.simp',
                'reasoning': f"Goal contains '{pattern}', attempting simplification",
                'priority': 0.7
            })
            
            logger.info(f"Proposed simp tactic for pattern '{pattern}'")
            return True
    
    return False