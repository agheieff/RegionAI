"""
Advanced mathematical heuristics for complex theorem proving.

This module contains heuristics for handling biconditionals, conjunction
elimination, classical reasoning, and more sophisticated proof patterns.
"""

import logging
from typing import Dict, Any
import re

from ...domains.language.lean_ast import ProofState, Tactic, TacticType
from ..heuristic_registry import heuristic_registry


logger = logging.getLogger(__name__)


def _normalize_expr(expr: str) -> str:
    """Normalize an expression for comparison."""
    expr = ' '.join(expr.split())
    expr = expr.replace('->', '→')
    expr = expr.replace('<->', '↔')
    return expr.strip()


@heuristic_registry.register("math.and_elim_left",
                           description="Extract left side of conjunction hypothesis",
                           applicability_conditions=("math", "conjunction", "elimination"),
                           expected_utility=0.85)
def heuristic_and_elim_left(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for extracting the left side of a conjunction.
    
    If we have a hypothesis of the form p ∧ q and need to prove p,
    use the left projection.
    
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
    
    goal = _normalize_expr(proof_state.current_goal)
    if not goal:
        return False
    
    # Look for conjunction hypotheses
    for hyp in proof_state.hypotheses:
        if '∧' in hyp.type_expr or '/\\' in hyp.type_expr:
            # Split the conjunction
            parts = re.split(r'∧|/\\', hyp.type_expr, 1)
            if len(parts) == 2:
                left_part = _normalize_expr(parts[0])
                
                # Check if the goal matches the left part
                if goal == left_part:
                    # Use custom tactic for left elimination
                    tactic = Tactic(
                        tactic_type=TacticType.CUSTOM,
                        arguments=[],
                        metadata={'raw_line': f'exact {hyp.name}.1'}
                    )
                    
                    planner.add_action({
                        'type': 'apply_tactic',
                        'tactic': tactic,
                        'heuristic': 'math.and_elim_left',
                        'reasoning': f"Goal matches left side of conjunction '{hyp.name}'",
                        'priority': 0.95
                    })
                    
                    logger.info(f"Proposed left conjunction elimination on '{hyp.name}'")
                    return True
    
    return False


@heuristic_registry.register("math.and_elim_right",
                           description="Extract right side of conjunction hypothesis",
                           applicability_conditions=("math", "conjunction", "elimination"),
                           expected_utility=0.85)
def heuristic_and_elim_right(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for extracting the right side of a conjunction.
    
    If we have a hypothesis of the form p ∧ q and need to prove q,
    use the right projection.
    
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
    
    goal = _normalize_expr(proof_state.current_goal)
    if not goal:
        return False
    
    # Look for conjunction hypotheses
    for hyp in proof_state.hypotheses:
        if '∧' in hyp.type_expr or '/\\' in hyp.type_expr:
            # Split the conjunction
            parts = re.split(r'∧|/\\', hyp.type_expr, 1)
            if len(parts) == 2:
                right_part = _normalize_expr(parts[1])
                
                # Check if the goal matches the right part
                if goal == right_part:
                    # Use custom tactic for right elimination
                    tactic = Tactic(
                        tactic_type=TacticType.CUSTOM,
                        arguments=[],
                        metadata={'raw_line': f'exact {hyp.name}.2'}
                    )
                    
                    planner.add_action({
                        'type': 'apply_tactic',
                        'tactic': tactic,
                        'heuristic': 'math.and_elim_right',
                        'reasoning': f"Goal matches right side of conjunction '{hyp.name}'",
                        'priority': 0.95
                    })
                    
                    logger.info(f"Proposed right conjunction elimination on '{hyp.name}'")
                    return True
    
    return False


@heuristic_registry.register("math.iff_intro",
                           description="Prove biconditional by proving both directions",
                           applicability_conditions=("math", "biconditional", "introduction"),
                           expected_utility=0.75)
def heuristic_iff_intro(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for proving biconditionals (p ↔ q).
    
    To prove p ↔ q, we need to prove both p → q and q → p.
    
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
    
    # Check if goal is a biconditional
    if '↔' in goal or '<->' in goal:
        # Use Iff.intro tactic
        tactic = Tactic(
            tactic_type=TacticType.CUSTOM,
            arguments=[],
            metadata={'raw_line': 'apply Iff.intro'}
        )
        
        planner.add_action({
            'type': 'apply_tactic',
            'tactic': tactic,
            'heuristic': 'math.iff_intro',
            'reasoning': "Goal is biconditional, proving both directions",
            'priority': 0.75
        })
        
        logger.info("Proposed Iff.intro for biconditional goal")
        return True
    
    return False


@heuristic_registry.register("math.comm",
                           description="Prove commutativity using rw tactic",
                           applicability_conditions=("math", "commutativity", "rewrite"),
                           expected_utility=0.8)
def heuristic_comm(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for proving commutativity.
    
    Handles goals like p ∧ q = q ∧ p or p ∨ q = q ∨ p.
    
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
    
    # Check for equality patterns suggesting commutativity
    if '=' in goal:
        parts = goal.split('=', 1)
        if len(parts) == 2:
            left = _normalize_expr(parts[0])
            right = _normalize_expr(parts[1])
            
            # Check for and/or commutativity patterns
            and_match_l = re.match(r'(.+)\s*∧\s*(.+)', left)
            and_match_r = re.match(r'(.+)\s*∧\s*(.+)', right)
            
            if and_match_l and and_match_r:
                l1, l2 = and_match_l.groups()
                r1, r2 = and_match_r.groups()
                
                if (_normalize_expr(l1) == _normalize_expr(r2) and 
                    _normalize_expr(l2) == _normalize_expr(r1)):
                    # This is commutativity of ∧
                    tactic = Tactic(
                        tactic_type=TacticType.CUSTOM,
                        arguments=[],
                        metadata={'raw_line': 'rw [and_comm]'}
                    )
                    
                    planner.add_action({
                        'type': 'apply_tactic',
                        'tactic': tactic,
                        'heuristic': 'math.comm',
                        'reasoning': "Goal is conjunction commutativity",
                        'priority': 0.85
                    })
                    
                    logger.info("Proposed and_comm rewrite")
                    return True
            
            # Similar check for disjunction
            or_match_l = re.match(r'(.+)\s*∨\s*(.+)', left)
            or_match_r = re.match(r'(.+)\s*∨\s*(.+)', right)
            
            if or_match_l and or_match_r:
                l1, l2 = or_match_l.groups()
                r1, r2 = or_match_r.groups()
                
                if (_normalize_expr(l1) == _normalize_expr(r2) and 
                    _normalize_expr(l2) == _normalize_expr(r1)):
                    # This is commutativity of ∨
                    tactic = Tactic(
                        tactic_type=TacticType.CUSTOM,
                        arguments=[],
                        metadata={'raw_line': 'rw [or_comm]'}
                    )
                    
                    planner.add_action({
                        'type': 'apply_tactic',
                        'tactic': tactic,
                        'heuristic': 'math.comm',
                        'reasoning': "Goal is disjunction commutativity",
                        'priority': 0.85
                    })
                    
                    logger.info("Proposed or_comm rewrite")
                    return True
    
    return False


@heuristic_registry.register("math.modus_ponens_direct",
                           description="Apply modus ponens when we have p and p → q",
                           applicability_conditions=("math", "implication", "modus_ponens"),
                           expected_utility=0.9)
def heuristic_modus_ponens_direct(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for applying modus ponens directly.
    
    If we have hypotheses p and p → q, and the goal is q,
    apply the implication to the premise.
    
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
    
    goal = _normalize_expr(proof_state.current_goal)
    if not goal:
        return False
    
    # Look for implications in hypotheses
    for impl_hyp in proof_state.hypotheses:
        if '→' in impl_hyp.type_expr or '->' in impl_hyp.type_expr:
            parts = re.split(r'→|->', impl_hyp.type_expr, 1)
            if len(parts) == 2:
                premise = _normalize_expr(parts[0])
                conclusion = _normalize_expr(parts[1])
                
                # Check if conclusion matches our goal
                if conclusion == goal:
                    # Look for the premise in hypotheses
                    for prem_hyp in proof_state.hypotheses:
                        if _normalize_expr(prem_hyp.type_expr) == premise:
                            # We can apply modus ponens!
                            tactic = Tactic(
                                tactic_type=TacticType.CUSTOM,
                                arguments=[],
                                metadata={'raw_line': f'exact {impl_hyp.name} {prem_hyp.name}'}
                            )
                            
                            planner.add_action({
                                'type': 'apply_tactic',
                                'tactic': tactic,
                                'heuristic': 'math.modus_ponens_direct',
                                'reasoning': f"Applying {impl_hyp.name} to {prem_hyp.name} (modus ponens)",
                                'priority': 0.95
                            })
                            
                            logger.info(f"Proposed modus ponens: {impl_hyp.name} {prem_hyp.name}")
                            return True
    
    return False


@heuristic_registry.register("math.classical",
                           description="Use classical reasoning tactics",
                           applicability_conditions=("math", "classical", "negation"),
                           expected_utility=0.7)
def heuristic_classical(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for classical reasoning patterns.
    
    Handles De Morgan's laws, contraposition, and other classical patterns.
    
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
    
    # De Morgan patterns
    if '¬(p ∧ q)' in goal or 'not (p and q)' in goal.lower():
        # Try De Morgan for conjunction
        tactic = Tactic(
            tactic_type=TacticType.CUSTOM,
            arguments=[],
            metadata={'raw_line': 'rw [not_and_or]'}
        )
        
        planner.add_action({
            'type': 'apply_tactic',
            'tactic': tactic,
            'heuristic': 'math.classical',
            'reasoning': "Applying De Morgan's law for conjunction",
            'priority': 0.8
        })
        
        logger.info("Proposed De Morgan's law for negated conjunction")
        return True
    
    if '¬(p ∨ q)' in goal or 'not (p or q)' in goal.lower():
        # Try De Morgan for disjunction
        tactic = Tactic(
            tactic_type=TacticType.CUSTOM,
            arguments=[],
            metadata={'raw_line': 'rw [not_or_and]'}
        )
        
        planner.add_action({
            'type': 'apply_tactic',
            'tactic': tactic,
            'heuristic': 'math.classical',
            'reasoning': "Applying De Morgan's law for disjunction",
            'priority': 0.8
        })
        
        logger.info("Proposed De Morgan's law for negated disjunction")
        return True
    
    # Contraposition pattern
    if ('→' in goal or '->' in goal) and '¬' in goal:
        # Try contraposition
        tactic = Tactic(
            tactic_type=TacticType.CUSTOM,
            arguments=[],
            metadata={'raw_line': 'contrapose'}
        )
        
        planner.add_action({
            'type': 'apply_tactic',
            'tactic': tactic,
            'heuristic': 'math.classical',
            'reasoning': "Goal involves implication with negation, trying contraposition",
            'priority': 0.7
        })
        
        logger.info("Proposed contraposition")
        return True
    
    return False


@heuristic_registry.register("math.rfl",
                           description="Use reflexivity for equality goals",
                           applicability_conditions=("math", "equality", "reflexivity"),
                           expected_utility=1.0)
def heuristic_rfl(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for reflexivity.
    
    If the goal is of the form x = x, use rfl.
    
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
    
    # Check for reflexive equality
    if '=' in goal:
        parts = goal.split('=', 1)
        if len(parts) == 2:
            left = _normalize_expr(parts[0])
            right = _normalize_expr(parts[1])
            
            if left == right:
                tactic = Tactic(
                    tactic_type=TacticType.CUSTOM,
                    arguments=[],
                    metadata={'raw_line': 'rfl'}
                )
                
                planner.add_action({
                    'type': 'apply_tactic',
                    'tactic': tactic,
                    'heuristic': 'math.rfl',
                    'reasoning': "Goal is reflexive equality",
                    'priority': 1.0
                })
                
                logger.info("Proposed rfl for reflexive equality")
                return True
    
    return False