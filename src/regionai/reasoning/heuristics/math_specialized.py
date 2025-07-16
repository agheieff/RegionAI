"""
Specialized mathematical heuristics for specific theorem patterns.

This module contains highly targeted heuristics for proving specific
types of theorems that require particular proof strategies.
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


@heuristic_registry.register("math.conj_elim_implication",
                           description="Prove conjunction elimination as implication",
                           applicability_conditions=("math", "conjunction", "elimination", "implication"),
                           expected_utility=0.9)
def heuristic_conj_elim_implication(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for proving conjunction elimination as an implication.
    
    To prove p ∧ q → p, we introduce the hypothesis and then extract.
    
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
    
    # Pattern: (p ∧ q) → p or (p ∧ q) → q
    conj_elim_pattern = re.match(r'\((.+)\s*∧\s*(.+)\)\s*→\s*(.+)', goal)
    if not conj_elim_pattern:
        conj_elim_pattern = re.match(r'(.+)\s*∧\s*(.+)\s*→\s*(.+)', goal)
    
    if conj_elim_pattern:
        p, q, conclusion = conj_elim_pattern.groups()
        p = _normalize_expr(p)
        q = _normalize_expr(q)
        conclusion = _normalize_expr(conclusion)
        
        # Check if conclusion is p (left elimination) or q (right elimination)
        if conclusion == p or conclusion == q:
            # First introduce the conjunction hypothesis
            tactic = Tactic(
                tactic_type=TacticType.INTRO,
                arguments=['h']
            )
            
            planner.add_action({
                'type': 'apply_tactic',
                'tactic': tactic,
                'heuristic': 'math.conj_elim_implication',
                'reasoning': f"Introducing conjunction hypothesis to prove elimination",
                'priority': 0.95
            })
            
            logger.info("Proposed intro for conjunction elimination implication")
            return True
    
    return False


@heuristic_registry.register("math.identity_biconditional",
                           description="Prove identity laws using biconditional",
                           applicability_conditions=("math", "identity", "biconditional"),
                           expected_utility=0.85)
def heuristic_identity_biconditional(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for proving identity laws like p ∧ True ↔ p.
    
    These require proving both directions separately.
    
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
    
    # Check for identity patterns with ↔
    identity_patterns = [
        (r'(.+)\s*∧\s*True\s*↔\s*(.+)', 'and_true'),
        (r'True\s*∧\s*(.+)\s*↔\s*(.+)', 'true_and'),
        (r'(.+)\s*∨\s*False\s*↔\s*(.+)', 'or_false'),
        (r'False\s*∨\s*(.+)\s*↔\s*(.+)', 'false_or'),
    ]
    
    for pattern, identity_type in identity_patterns:
        match = re.match(pattern, goal)
        if match:
            # Use Iff.intro to split into two directions
            tactic = Tactic(
                tactic_type=TacticType.CUSTOM,
                arguments=[],
                metadata={'raw_line': 'apply Iff.intro'}
            )
            
            planner.add_action({
                'type': 'apply_tactic',
                'tactic': tactic,
                'heuristic': 'math.identity_biconditional',
                'reasoning': f"Splitting {identity_type} identity into both directions",
                'priority': 0.85
            })
            
            logger.info(f"Proposed Iff.intro for {identity_type} identity")
            return True
    
    return False


@heuristic_registry.register("math.impl_as_disj_specialized",
                           description="Convert implication to disjunction",
                           applicability_conditions=("math", "implication", "disjunction", "conversion"),
                           expected_utility=0.8)
def heuristic_impl_as_disj_specialized(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for converting (p → q) → (¬p ∨ q).
    
    This is a classical tautology that requires specific tactics.
    
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
    
    # Check for the specific pattern: (p → q) → (¬p ∨ q)
    impl_disj_pattern = re.match(r'\((.+)\s*→\s*(.+)\)\s*→\s*\(¬(.+)\s*∨\s*(.+)\)', goal)
    if not impl_disj_pattern:
        impl_disj_pattern = re.match(r'\((.+)\s*→\s*(.+)\)\s*→\s*\(not\s+(.+)\s*∨\s*(.+)\)', goal)
    
    if impl_disj_pattern:
        p1, q1, p2, q2 = impl_disj_pattern.groups()
        
        # Verify it's the same p and q
        if _normalize_expr(p1) == _normalize_expr(p2) and _normalize_expr(q1) == _normalize_expr(q2):
            # Use a classical reasoning tactic
            tactic = Tactic(
                tactic_type=TacticType.CUSTOM,
                arguments=[],
                metadata={'raw_line': 'tauto'}  # Try tautology prover
            )
            
            planner.add_action({
                'type': 'apply_tactic',
                'tactic': tactic,
                'heuristic': 'math.impl_as_disj_specialized',
                'reasoning': "Using tautology prover for implication to disjunction",
                'priority': 0.85
            })
            
            logger.info("Proposed tauto for implication as disjunction")
            return True
    
    return False


@heuristic_registry.register("math.by_cases",
                           description="Use case analysis for complex goals",
                           applicability_conditions=("math", "cases", "analysis"),
                           expected_utility=0.7)
def heuristic_by_cases(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for using case analysis (by_cases) tactic.
    
    Useful for proving statements by considering p and ¬p separately.
    
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
    
    # Use by_cases for goals involving ¬p ∨ q patterns
    if ('¬' in goal or 'not' in goal.lower()) and '∨' in goal:
        # Extract a proposition to do case analysis on
        # For (¬p ∨ q), we want to do cases on p
        neg_or_pattern = re.match(r'¬(.+)\s*∨\s*(.+)', goal)
        if not neg_or_pattern:
            neg_or_pattern = re.match(r'not\s+(.+)\s*∨\s*(.+)', goal)
        
        if neg_or_pattern:
            prop = neg_or_pattern.group(1).strip()
            
            tactic = Tactic(
                tactic_type=TacticType.CUSTOM,
                arguments=[],
                metadata={'raw_line': f'by_cases h : {prop}'}
            )
            
            planner.add_action({
                'type': 'apply_tactic',
                'tactic': tactic,
                'heuristic': 'math.by_cases',
                'reasoning': f"Using case analysis on '{prop}'",
                'priority': 0.7
            })
            
            logger.info(f"Proposed by_cases on '{prop}'")
            return True
    
    return False


@heuristic_registry.register("math.constructor_identity",
                           description="Use constructor for identity proofs",
                           applicability_conditions=("math", "identity", "constructor"),
                           expected_utility=0.8)
def heuristic_constructor_identity(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Heuristic for using constructor in identity proofs.
    
    When proving p → p ∧ True, after intro we need constructor.
    
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
    
    # After intro in identity proofs, we often need constructor
    if '∧ True' in goal or 'True ∧' in goal:
        # Check if we have a hypothesis that matches part of the goal
        for hyp in proof_state.hypotheses:
            hyp_expr = _normalize_expr(hyp.type_expr)
            
            # Check if hypothesis matches the non-True part
            if '∧ True' in goal:
                non_true_part = goal.replace('∧ True', '').strip()
                if hyp_expr == _normalize_expr(non_true_part):
                    tactic = Tactic(
                        tactic_type=TacticType.CONSTRUCTOR,
                        arguments=[]
                    )
                    
                    planner.add_action({
                        'type': 'apply_tactic',
                        'tactic': tactic,
                        'heuristic': 'math.constructor_identity',
                        'reasoning': "Using constructor to split conjunction with True",
                        'priority': 0.85
                    })
                    
                    logger.info("Proposed constructor for identity with True")
                    return True
    
    return False


@heuristic_registry.register("math.exact_hypothesis_projection",
                           description="Use exact with hypothesis projection",
                           applicability_conditions=("math", "exact", "projection"),
                           expected_utility=0.9)
def heuristic_exact_hypothesis_projection(hub: Any, context: Dict[str, Any]) -> bool:
    """
    Enhanced exact heuristic that handles projections.
    
    After intro on p ∧ q → p, we have h : p ∧ q and need to prove p.
    Use exact h.1 or exact h.2.
    
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
            parts = re.split(r'∧|/\\', hyp.type_expr, 1)
            if len(parts) == 2:
                left = _normalize_expr(parts[0])
                right = _normalize_expr(parts[1])
                
                # Check if goal matches either part
                if goal == left:
                    tactic = Tactic(
                        tactic_type=TacticType.CUSTOM,
                        arguments=[],
                        metadata={'raw_line': f'exact {hyp.name}.1'}
                    )
                    
                    planner.add_action({
                        'type': 'apply_tactic',
                        'tactic': tactic,
                        'heuristic': 'math.exact_hypothesis_projection',
                        'reasoning': f"Goal matches left part of conjunction '{hyp.name}'",
                        'priority': 0.95
                    })
                    
                    logger.info(f"Proposed exact {hyp.name}.1")
                    return True
                    
                elif goal == right:
                    tactic = Tactic(
                        tactic_type=TacticType.CUSTOM,
                        arguments=[],
                        metadata={'raw_line': f'exact {hyp.name}.2'}
                    )
                    
                    planner.add_action({
                        'type': 'apply_tactic',
                        'tactic': tactic,
                        'heuristic': 'math.exact_hypothesis_projection',
                        'reasoning': f"Goal matches right part of conjunction '{hyp.name}'",
                        'priority': 0.95
                    })
                    
                    logger.info(f"Proposed exact {hyp.name}.2")
                    return True
    
    return False